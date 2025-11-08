"""
Search RAG Helper - LLM-based semantic search refinement agent.

This agent replaces traditional embedding-based RAG with pure LLM reasoning
for semantic understanding, query reformulation, and result ranking.
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.config import config
from app.llm import LLM
from app.logger import logger
from app.tool.search.backends.base import StructuredSearchResult


class QueryReformulation(BaseModel):
    """Query reformulation result."""
    
    original_query: str = Field(description="Original search query")
    reformulated_query: str = Field(description="Reformulated query")
    reformulation_reasoning: str = Field(description="Reasoning behind the reformulation")
    expansion_terms: List[str] = Field(default_factory=list, description="Additional terms for expansion")
    disambiguation_context: Optional[str] = Field(default=None, description="Context for disambiguation")


class ResultRanking(BaseModel):
    """Result ranking with reasoning."""
    
    result_index: int = Field(description="Index of the result in the original list")
    relevance_score: float = Field(description="Relevance score (0.0 to 1.0)")
    ranking_reasoning: str = Field(description="Reasoning for the ranking")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from this result")
    relevance_to_query: str = Field(description="How this result relates to the query")


class SearchRAGResult(BaseModel):
    """RAG-enhanced search result."""
    
    query: str = Field(description="Final query used")
    original_results: List[StructuredSearchResult] = Field(description="Original search results")
    ranked_results: List[StructuredSearchResult] = Field(description="Ranked and refined results")
    reformulations: List[QueryReformulation] = Field(description="Query reformulations performed")
    rankings: List[ResultRanking] = Field(description="Result rankings with reasoning")
    reasoning_trace: List[str] = Field(default_factory=list, description="Complete reasoning trace")
    iteration_count: int = Field(description="Number of iterations performed")
    cache_hits: int = Field(description="Number of cache hits")
    search_metadata: Dict[str, Any] = Field(default_factory=dict, description="Search metadata")


class SearchRAGHelper:
    """LLM-based semantic search refinement agent."""
    
    def __init__(self, llm: Optional[LLM] = None):
        self.llm = llm or LLM()
        self.cache_db_path = "data/search_rag_cache.db"
        self._init_cache_db()
        
        # Load configuration
        self.max_iterations = getattr(config.search_config, "rag_max_iterations", 3)
        self.context_window = getattr(config.search_config, "rag_context_window", 4000)
        self.similarity_threshold = getattr(config.search_config, "rag_similarity_threshold", 0.7)
        self.enable_reasoning_trace = getattr(config.search_config, "rag_enable_reasoning_trace", True)
        
    def _init_cache_db(self):
        """Initialize SQLite cache database."""
        import os
        os.makedirs(os.path.dirname(self.cache_db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                results_json TEXT NOT NULL,
                reformulations_json TEXT,
                rankings_json TEXT,
                reasoning_trace_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                access_count INTEGER DEFAULT 1,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_cache_expires_at 
            ON query_cache(expires_at)
        """)
        
        conn.commit()
        conn.close()
    
    async def search(
        self,
        query: str,
        search_func: callable,
        num_results: int = 10,
        lang: str = "en",
        country: str = "us",
        **kwargs
    ) -> SearchRAGResult:
        """
        Perform RAG-enhanced search.
        
        Args:
            query: Original search query
            search_func: Async function to perform actual search
            num_results: Number of results to return
            lang: Language code
            country: Country code
            **kwargs: Additional search parameters
            
        Returns:
            RAG-enhanced search result
        """
        # Check cache first
        cached_result = await self._get_cached_result(query)
        if cached_result:
            logger.info(f"RAG cache hit for query: {query}")
            return cached_result
        
        reasoning_trace = []
        reformulations = []
        all_results = []
        current_query = query
        
        reasoning_trace.append(f"Starting RAG-enhanced search for query: '{query}'")
        
        # Iterative refinement loop
        for iteration in range(self.max_iterations):
            reasoning_trace.append(f"--- Iteration {iteration + 1} ---")
            
            # Perform search with current query
            search_results = await search_func(
                current_query, 
                num_results=num_results, 
                lang=lang, 
                country=country, 
                **kwargs
            )
            
            if not search_results:
                reasoning_trace.append("No results found, stopping refinement")
                break
            
            all_results.extend(search_results)
            
            # Analyze results and decide if refinement is needed
            analysis = await self._analyze_results(current_query, search_results, reasoning_trace)
            
            if not analysis["needs_refinement"]:
                reasoning_trace.append("Results are satisfactory, stopping refinement")
                break
            
            # Reformulate query based on analysis
            reformulation = await self._reformulate_query(
                current_query, 
                search_results, 
                analysis["insights"]
            )
            
            reformulations.append(reformulation)
            current_query = reformulation.reformulated_query
            
            reasoning_trace.append(
                f"Reformulated query: '{reformulation.reformulated_query}' "
                f"({reformulation.reformulation_reasoning})"
            )
            
            # Avoid infinite loops
            if iteration == self.max_iterations - 1:
                reasoning_trace.append(f"Reached maximum iterations ({self.max_iterations})")
        
        # Rank and finalize results
        ranked_results, rankings = await self._rank_results(query, all_results, reasoning_trace)
        
        # Create final result
        result = SearchRAGResult(
            query=current_query,
            original_results=all_results,
            ranked_results=ranked_results[:num_results],
            reformulations=reformulations,
            rankings=rankings,
            reasoning_trace=reasoning_trace if self.enable_reasoning_trace else [],
            iteration_count=len(reformulations) + 1,
            cache_hits=0,
            search_metadata={
                "total_results_found": len(all_results),
                "final_results_count": len(ranked_results),
                "query_evolution": [query] + [r.reformulated_query for r in reformulations],
            }
        )
        
        # Cache the result
        await self._cache_result(query, result)
        
        logger.info(f"RAG search completed: {len(result.ranked_results)} results after {result.iteration_count} iterations")
        return result
    
    async def _analyze_results(
        self, 
        query: str, 
        results: List[StructuredSearchResult],
        reasoning_trace: List[str]
    ) -> Dict[str, Any]:
        """Analyze search results to determine if refinement is needed."""
        if not results:
            return {"needs_refinement": False, "insights": []}
        
        # Prepare context for LLM analysis
        results_summary = self._prepare_results_summary(results)
        
        prompt = f"""Analyze these search results for the query: "{query}"

Results Summary:
{results_summary}

Determine:
1. Are the results relevant and comprehensive?
2. Are there obvious gaps or missing information?
3. Could the query be improved for better results?
4. What insights do these results provide about the user's intent?

Respond with JSON:
{{
    "needs_refinement": boolean,
    "relevance_score": float (0.0-1.0),
    "insights": [
        "insight 1",
        "insight 2"
    ],
    "gaps_identified": [
        "gap 1",
        "gap 2"
    ],
    "query_intent": "brief description of user intent"
}}"""
        
        try:
            response = await self.llm.generate_response(prompt)
            # Parse JSON response
            analysis = json.loads(response.strip())
            
            reasoning_trace.append(f"Result analysis: relevance={analysis.get('relevance_score', 0):.2f}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing results: {e}")
            reasoning_trace.append(f"Error in analysis: {e}")
            return {"needs_refinement": False, "insights": []}
    
    async def _reformulate_query(
        self, 
        original_query: str, 
        results: List[StructuredSearchResult],
        insights: List[str]
    ) -> QueryReformulation:
        """Reformulate query based on results and insights."""
        results_summary = self._prepare_results_summary(results)
        insights_text = "\n".join(f"- {insight}" for insight in insights)
        
        prompt = f"""Reformulate the search query to get better results.

Original Query: "{original_query}"

Current Results Summary:
{results_summary}

Insights from Analysis:
{insights_text}

Reformulate the query to:
1. Be more specific and targeted
2. Include relevant technical terms
3. Address any ambiguities
4. Focus on the most likely user intent

Respond with JSON:
{{
    "reformulated_query": "improved query",
    "reformulation_reasoning": "explanation of changes",
    "expansion_terms": ["term1", "term2"],
    "disambiguation_context": "context for clarification (if needed)"
}}"""
        
        try:
            response = await self.llm.generate_response(prompt)
            reformulation_data = json.loads(response.strip())
            
            return QueryReformulation(
                original_query=original_query,
                **reformulation_data
            )
            
        except Exception as e:
            logger.error(f"Error reformulating query: {e}")
            # Return original query if reformulation fails
            return QueryReformulation(
                original_query=original_query,
                reformulated_query=original_query,
                reformulation_reasoning="Reformulation failed, using original query",
                expansion_terms=[],
                disambiguation_context=None,
            )
    
    async def _rank_results(
        self, 
        query: str, 
        results: List[StructuredSearchResult],
        reasoning_trace: List[str]
    ) -> Tuple[List[StructuredSearchResult], List[ResultRanking]]:
        """Rank results based on relevance to the query."""
        if not results:
            return [], []
        
        # Remove duplicates
        unique_results = self._deduplicate_results(results)
        
        # Prepare results for ranking
        results_text = self._prepare_results_for_ranking(unique_results)
        
        prompt = f"""Rank these search results by relevance to the query: "{query}"

Results:
{results_text}

For each result, provide:
1. Relevance score (0.0 to 1.0)
2. Reasoning for the score
3. Key insights from this result
4. How it relates to the query

Respond with JSON array:
[
    {{
        "result_index": 0,
        "relevance_score": 0.95,
        "ranking_reasoning": "Highly relevant, directly addresses the query",
        "key_insights": ["insight 1", "insight 2"],
        "relevance_to_query": "Directly answers the question about..."
    }}
]"""
        
        try:
            response = await self.llm.generate_response(prompt)
            rankings_data = json.loads(response.strip())
            
            # Create ranking objects
            rankings = []
            for ranking_data in rankings_data:
                rankings.append(ResultRanking(**ranking_data))
            
            # Sort results by relevance score
            sorted_results = []
            for ranking in sorted(rankings, key=lambda x: x.relevance_score, reverse=True):
                if ranking.result_index < len(unique_results):
                    sorted_results.append(unique_results[ranking.result_index])
            
            reasoning_trace.append(f"Ranked {len(sorted_results)} unique results")
            
            return sorted_results, rankings
            
        except Exception as e:
            logger.error(f"Error ranking results: {e}")
            reasoning_trace.append(f"Error in ranking: {e}")
            # Return original ordering if ranking fails
            return unique_results, []
    
    def _prepare_results_summary(self, results: List[StructuredSearchResult]) -> str:
        """Prepare a summary of results for LLM analysis."""
        summary_parts = []
        
        for i, result in enumerate(results[:5]):  # Limit to first 5 for brevity
            part = f"{i+1}. {result.title}\n"
            part += f"   URL: {result.url}\n"
            part += f"   Description: {result.description[:200]}...\n"
            
            if result.rich_snippet:
                part += f"   Rich Snippet: {result.rich_snippet[:150]}...\n"
            
            if result.structured_data:
                part += f"   Has structured data\n"
            
            summary_parts.append(part)
        
        return "\n".join(summary_parts)
    
    def _prepare_results_for_ranking(self, results: List[StructuredSearchResult]) -> str:
        """Prepare results for ranking analysis."""
        ranking_parts = []
        
        for i, result in enumerate(results):
            part = f"Result {i}:\n"
            part += f"Title: {result.title}\n"
            part += f"URL: {result.url}\n"
            part += f"Description: {result.description}\n"
            
            if result.rich_snippet:
                part += f"Rich Snippet: {result.rich_snippet}\n"
            
            if result.result_type:
                part += f"Type: {result.result_type}\n"
            
            ranking_parts.append(part + "\n")
        
        return "".join(ranking_parts)
    
    def _deduplicate_results(self, results: List[StructuredSearchResult]) -> List[StructuredSearchResult]:
        """Remove duplicate results based on URL."""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            # Normalize URL for comparison
            normalized_url = result.url.split('#')[0].rstrip('/')
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                unique_results.append(result)
        
        return unique_results
    
    async def _get_cached_result(self, query: str) -> Optional[SearchRAGResult]:
        """Get cached result for a query."""
        import hashlib
        
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        # Check for valid cache entry
        cursor.execute("""
            SELECT results_json, reformulations_json, rankings_json, 
                   reasoning_trace_json, access_count
            FROM query_cache 
            WHERE query_hash = ? AND expires_at > ?
        """, (query_hash, datetime.now()))
        
        row = cursor.fetchone()
        
        if row:
            # Update access statistics
            cursor.execute("""
                UPDATE query_cache 
                SET access_count = access_count + 1, last_accessed = ?
                WHERE query_hash = ?
            """, (datetime.now(), query_hash))
            conn.commit()
            
            # Reconstruct result
            try:
                results_data = json.loads(row[0])
                reformulations_data = json.loads(row[1]) if row[1] else []
                rankings_data = json.loads(row[2]) if row[2] else []
                reasoning_trace_data = json.loads(row[3]) if row[3] else []
                
                # Convert back to objects
                original_results = [StructuredSearchResult(**r) for r in results_data]
                reformulations = [QueryReformulation(**r) for r in reformulations_data]
                rankings = [ResultRanking(**r) for r in rankings_data]
                
                result = SearchRAGResult(
                    query=query,
                    original_results=original_results,
                    ranked_results=original_results,  # Use original as ranked for cache
                    reformulations=reformulations,
                    rankings=rankings,
                    reasoning_trace=reasoning_trace_data,
                    iteration_count=1,  # Default value
                    cache_hits=row[4] + 1,
                    search_metadata={"from_cache": True}
                )
                
                conn.close()
                return result
                
            except Exception as e:
                logger.error(f"Error reconstructing cached result: {e}")
        
        conn.close()
        return None
    
    async def _cache_result(self, query: str, result: SearchRAGResult):
        """Cache a search result."""
        import hashlib
        
        query_hash = hashlib.md5(query.encode()).hexdigest()
        expires_at = datetime.now() + timedelta(seconds=getattr(config.search_config, "search_cache_ttl", 3600))
        
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        try:
            # Serialize data
            results_json = json.dumps([r.dict() for r in result.original_results])
            reformulations_json = json.dumps([r.dict() for r in result.reformulations])
            rankings_json = json.dumps([r.dict() for r in result.rankings])
            reasoning_trace_json = json.dumps(result.reasoning_trace)
            
            # Insert or replace
            cursor.execute("""
                INSERT OR REPLACE INTO query_cache 
                (query_hash, query, results_json, reformulations_json, 
                 rankings_json, reasoning_trace_json, expires_at, access_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                query_hash, query, results_json, reformulations_json,
                rankings_json, reasoning_trace_json, expires_at
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error caching result: {e}")
        finally:
            conn.close()
    
    def cleanup_expired_cache(self):
        """Clean up expired cache entries."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM query_cache WHERE expires_at <= ?", (datetime.now(),))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired cache entries")