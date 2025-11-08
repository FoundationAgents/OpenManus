"""
BrowserRAGHelper - LLM-based semantic page understanding agent.

Replaces embeddings with pure LLM reasoning for:
- Page content understanding and summarization
- Element identification via semantic description
- Form field purpose detection
- Content extraction and comparison
- Interaction suggestions based on semantic understanding

Uses SQLite caching (not vector store) for query→response mapping.
"""

import hashlib
import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.config import config
from app.logger import logger


class SemanticElement(BaseModel):
    """Semantically identified page element."""
    
    xpath: str = Field(description="XPath to element")
    element_type: str = Field(description="Element type (button, input, link, etc.)")
    text: str = Field(description="Element text content")
    semantic_description: str = Field(description="Semantic description from LLM")
    purpose: Optional[str] = Field(None, description="Purpose of this element")
    suggested_interaction: Optional[str] = Field(None, description="How to interact with this element")


class PageSummary(BaseModel):
    """Semantic summary of page content."""
    
    url: str = Field(description="Page URL")
    title: str = Field(description="Page title")
    main_content: str = Field(description="Main page content")
    key_sections: List[str] = Field(description="Key sections identified")
    page_type: str = Field(description="Type of page (e.g., login, product, search results)")
    noise_elements: List[str] = Field(description="Ads, navigation, footer elements to ignore")
    interactive_elements: List[SemanticElement] = Field(description="Key interactive elements")


class ContentUnderstanding(BaseModel):
    """LLM-based understanding of page content."""
    
    query: str = Field(description="Query about page")
    answer: str = Field(description="Answer to query")
    supporting_evidence: str = Field(description="Evidence from page content")
    confidence: float = Field(description="Confidence score (0.0-1.0)")
    reasoning_trace: str = Field(description="LLM reasoning trace")


class BrowserRAGHelper:
    """
    LLM-based semantic browser content understanding.
    
    Features:
    - Page summarization and content extraction
    - Semantic element identification
    - Form field purpose detection
    - Content comparison
    - Query answering about page content
    """
    
    def __init__(self, llm: Optional[Any] = None, cache_dir: Optional[str] = None):
        """
        Initialize BrowserRAGHelper.
        
        Args:
            llm: LLM instance for semantic reasoning
            cache_dir: Directory for cache database
        """
        if llm is None:
            from app.llm import LLM
            self.llm = LLM()
        else:
            self.llm = llm
        self.cache_dir = Path(cache_dir or "./cache/browser")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        self.cache_ttl = getattr(config.browser_config, "rag_cache_ttl", 3600)
        self.semantic_depth = getattr(config.browser_config, "rag_semantic_depth", "normal")
        self.max_summary_length = 500 if self.semantic_depth == "minimal" else (1000 if self.semantic_depth == "normal" else 2000)
        
        self._init_cache_db()
        logger.info(f"Initialized BrowserRAGHelper (depth={self.semantic_depth})")
    
    def _init_cache_db(self):
        """Initialize SQLite cache for RAG responses."""
        cache_db = self.cache_dir / "browser_rag_cache.db"
        
        try:
            conn = sqlite3.connect(str(cache_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rag_cache (
                    cache_key TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    reasoning_trace TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    access_count INTEGER DEFAULT 1,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rag_cache_expires_at 
                ON rag_cache(expires_at)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rag_cache_url 
                ON rag_cache(url)
            """)
            
            conn.commit()
            conn.close()
            logger.debug(f"Initialized RAG cache at {cache_db}")
        except Exception as e:
            logger.error(f"Failed to initialize RAG cache: {e}")
    
    def _get_cache_key(self, url: str, query: str) -> str:
        """Generate cache key from URL and query."""
        key_data = f"{url}:{query}".encode()
        return hashlib.md5(key_data).hexdigest()
    
    def _get_cached_response(self, url: str, query: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached RAG response."""
        try:
            cache_key = self._get_cache_key(url, query)
            cache_db = self.cache_dir / "browser_rag_cache.db"
            
            conn = sqlite3.connect(str(cache_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT response, reasoning_trace, access_count 
                FROM rag_cache 
                WHERE cache_key = ? AND expires_at > ?
            """, (cache_key, datetime.now().isoformat()))
            
            result = cursor.fetchone()
            
            if result:
                response_str, reasoning, access_count = result
                
                # Update access count
                cursor.execute("""
                    UPDATE rag_cache 
                    SET access_count = access_count + 1, 
                        last_accessed = CURRENT_TIMESTAMP 
                    WHERE cache_key = ?
                """, (cache_key,))
                conn.commit()
                
                logger.debug(f"RAG cache hit for: {query[:50]}")
                
                return {
                    "response": json.loads(response_str),
                    "reasoning_trace": reasoning,
                    "cached": True,
                }
            
            conn.close()
            return None
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
            return None
    
    def _cache_response(self, url: str, query: str, response: Dict[str, Any], reasoning: str):
        """Cache a RAG response."""
        try:
            cache_key = self._get_cache_key(url, query)
            cache_db = self.cache_dir / "browser_rag_cache.db"
            expires_at = datetime.now() + timedelta(seconds=self.cache_ttl)
            
            conn = sqlite3.connect(str(cache_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO rag_cache 
                (cache_key, url, query, response, reasoning_trace, expires_at) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cache_key, url, query, json.dumps(response), reasoning, expires_at.isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Cached RAG response for: {query[:50]}")
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")
    
    async def understand_page(
        self,
        url: str,
        page_content: str,
        page_title: str = "",
    ) -> PageSummary:
        """
        Understand page semantically.
        
        Args:
            url: Page URL
            page_content: Page HTML or text content
            page_title: Page title
            
        Returns:
            Semantic understanding of page
        """
        try:
            # Prepare content for LLM
            content_preview = page_content[:self.max_summary_length]
            
            system_prompt = """You are an expert web page analyzer. Analyze the given page content and provide:
1. Main content summary (what is this page about?)
2. Key sections/areas on the page
3. Page type classification (e.g., login, product, search results, blog post)
4. Noise elements (ads, navigation, footer) to filter out
5. Interactive elements (buttons, forms, links) that might be important

Respond in JSON format with these exact keys: main_content, key_sections, page_type, noise_elements, interactive_elements"""
            
            user_prompt = f"""Analyze this page:

URL: {url}
Title: {page_title}

Content:
{content_preview}

Provide your analysis in JSON format."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            
            # Call LLM
            response = await self.llm.ask(messages)
            
            # Parse response
            try:
                analysis = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = {
                        "main_content": response,
                        "key_sections": [],
                        "page_type": "unknown",
                        "noise_elements": [],
                        "interactive_elements": [],
                    }
            
            summary = PageSummary(
                url=url,
                title=page_title,
                main_content=analysis.get("main_content", ""),
                key_sections=analysis.get("key_sections", []),
                page_type=analysis.get("page_type", "unknown"),
                noise_elements=analysis.get("noise_elements", []),
                interactive_elements=[],
            )
            
            return summary
        except Exception as e:
            logger.error(f"Page understanding failed: {e}")
            return PageSummary(
                url=url,
                title=page_title,
                main_content="",
                key_sections=[],
                page_type="error",
                noise_elements=[],
                interactive_elements=[],
            )
    
    async def find_element_by_description(
        self,
        page_content: str,
        description: str,
        dom_tree: Optional[Dict[str, Any]] = None,
    ) -> Optional[SemanticElement]:
        """
        Find a page element by semantic description.
        
        Args:
            page_content: Page content
            description: Semantic description (e.g., "the login button", "email input field")
            dom_tree: Optional DOM tree structure
            
        Returns:
            Identified semantic element or None
        """
        try:
            # Check cache first
            cached = self._get_cached_response(description, description)
            if cached:
                return SemanticElement(**cached.get("response", {}))
            
            system_prompt = f"""You are an expert at finding elements on web pages based on semantic descriptions.
Given a page description and a semantic description of an element, identify:
1. The most likely element (button, input, link, etc.)
2. Its XPath or CSS selector
3. The element's text or label
4. The element's purpose
5. How to interact with it

Respond in JSON format with keys: element_type, xpath, text, purpose, suggested_interaction"""
            
            user_prompt = f"""Find the element matching this description:

Description: {description}

Page content:
{page_content[:1000]}

Provide the element details in JSON format."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            
            response = await self.llm.ask(messages)
            
            try:
                element_data = json.loads(response)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    element_data = json.loads(json_match.group())
                else:
                    return None
            
            element = SemanticElement(
                xpath=element_data.get("xpath", ""),
                element_type=element_data.get("element_type", "unknown"),
                text=element_data.get("text", ""),
                semantic_description=description,
                purpose=element_data.get("purpose"),
                suggested_interaction=element_data.get("suggested_interaction"),
            )
            
            # Cache result
            self._cache_response(description, description, element.model_dump(), response)
            
            return element
        except Exception as e:
            logger.error(f"Element finding failed: {e}")
            return None
    
    async def answer_question_about_page(
        self,
        url: str,
        page_content: str,
        question: str,
    ) -> ContentUnderstanding:
        """
        Answer a question about page content using LLM reasoning.
        
        Args:
            url: Page URL
            page_content: Page content
            question: Question to answer
            
        Returns:
            Answer with reasoning trace
        """
        try:
            # Check cache
            cached = self._get_cached_response(url, question)
            if cached:
                return ContentUnderstanding(**cached.get("response", {}))
            
            system_prompt = """You are an expert at understanding web page content.
Answer the given question based on the page content provided.
Respond in JSON format with keys: answer, supporting_evidence, confidence, reasoning_trace
Confidence should be between 0.0 (not confident) and 1.0 (very confident)."""
            
            user_prompt = f"""Answer this question about the page:

URL: {url}
Question: {question}

Page content:
{page_content[:2000]}

Provide your answer in JSON format."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            
            response = await self.llm.ask(messages)
            
            try:
                answer_data = json.loads(response)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    answer_data = json.loads(json_match.group())
                else:
                    answer_data = {
                        "answer": response,
                        "supporting_evidence": "",
                        "confidence": 0.5,
                        "reasoning_trace": response,
                    }
            
            understanding = ContentUnderstanding(
                query=question,
                answer=answer_data.get("answer", ""),
                supporting_evidence=answer_data.get("supporting_evidence", ""),
                confidence=float(answer_data.get("confidence", 0.5)),
                reasoning_trace=answer_data.get("reasoning_trace", ""),
            )
            
            # Cache result
            self._cache_response(url, question, understanding.model_dump(), understanding.reasoning_trace)
            
            return understanding
        except Exception as e:
            logger.error(f"Question answering failed: {e}")
            return ContentUnderstanding(
                query=question,
                answer=f"Error: {str(e)}",
                supporting_evidence="",
                confidence=0.0,
                reasoning_trace=str(e),
            )
    
    async def suggest_interactions(
        self,
        page_content: str,
        current_goal: str,
    ) -> List[SemanticElement]:
        """
        Suggest elements to interact with based on current goal.
        
        Args:
            page_content: Page content
            current_goal: What user is trying to accomplish
            
        Returns:
            List of suggested interactive elements
        """
        try:
            system_prompt = f"""You are an expert at understanding user goals on web pages.
Given a user's goal, suggest which elements they should interact with.
Respond in JSON format with an array of element suggestions.
Each suggestion should have: element_type, text, purpose, suggested_interaction"""
            
            user_prompt = f"""Based on this goal, suggest elements to interact with:

Goal: {current_goal}

Page content:
{page_content[:1500]}

Provide suggestions as a JSON array of objects."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            
            response = await self.llm.ask(messages)
            
            try:
                suggestions_data = json.loads(response)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    suggestions_data = json.loads(json_match.group())
                else:
                    suggestions_data = []
            
            suggestions = []
            for item in suggestions_data:
                if isinstance(item, dict):
                    suggestions.append(SemanticElement(
                        xpath=item.get("xpath", ""),
                        element_type=item.get("element_type", "unknown"),
                        text=item.get("text", ""),
                        semantic_description=item.get("description", current_goal),
                        purpose=item.get("purpose"),
                        suggested_interaction=item.get("suggested_interaction"),
                    ))
            
            return suggestions
        except Exception as e:
            logger.error(f"Interaction suggestions failed: {e}")
            return []
    
    def clear_cache(self, older_than_seconds: int = 0):
        """
        Clear expired cache entries.
        
        Args:
            older_than_seconds: Clear entries older than this (0 = all expired)
        """
        try:
            cache_db = self.cache_dir / "browser_rag_cache.db"
            
            conn = sqlite3.connect(str(cache_db))
            cursor = conn.cursor()
            
            cutoff_time = datetime.now() - timedelta(seconds=older_than_seconds)
            
            cursor.execute("""
                DELETE FROM rag_cache 
                WHERE created_at < ?
            """, (cutoff_time.isoformat(),))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Cleared {deleted} expired cache entries")
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
