"""
QA Knowledge Graph

Builds and maintains knowledge base of:
- Common anti-patterns in codebase
- Historical issues
- Best practices
- Performance optimization patterns
- Security vulnerability patterns
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict
from app.logger import logger


@dataclass
class KnowledgeEntry:
    """Knowledge base entry"""
    id: str
    category: str  # anti-pattern, best-practice, performance, security, testing
    pattern: str
    description: str
    severity: str
    examples: List[str] = field(default_factory=list)
    fixes: List[str] = field(default_factory=list)
    occurrence_count: int = 0
    last_seen: Optional[str] = None
    related_patterns: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class QAKnowledgeGraph:
    """Manages QA knowledge base"""
    
    def __init__(self, storage_path: str = "cache/qa_knowledge.json"):
        self.storage_path = storage_path
        self.knowledge_base: Dict[str, KnowledgeEntry] = {}
        self.pattern_index: Dict[str, List[str]] = defaultdict(list)
        self.category_index: Dict[str, List[str]] = defaultdict(list)
        self.load()
    
    def load(self):
        """Load knowledge base from storage"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for entry_data in data.get("entries", []):
                    entry = KnowledgeEntry(**entry_data)
                    self.knowledge_base[entry.id] = entry
                    self._update_indices(entry)
                
                logger.info(f"Loaded {len(self.knowledge_base)} knowledge entries")
            
            except Exception as e:
                logger.error(f"Failed to load knowledge base: {e}")
        else:
            # Initialize with default patterns
            self._initialize_default_knowledge()
    
    def save(self):
        """Save knowledge base to storage"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            data = {
                "entries": [entry.to_dict() for entry in self.knowledge_base.values()],
                "updated_at": datetime.now().isoformat()
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved knowledge base with {len(self.knowledge_base)} entries")
        
        except Exception as e:
            logger.error(f"Failed to save knowledge base: {e}")
    
    def add_issue(self, issue: Dict[str, Any]):
        """Learn from a detected issue"""
        issue_type = issue.get("type", "unknown")
        severity = issue.get("severity", "MEDIUM")
        message = issue.get("message", "")
        
        # Create or update knowledge entry
        entry_id = f"kb_{issue_type}"
        
        if entry_id in self.knowledge_base:
            entry = self.knowledge_base[entry_id]
            entry.occurrence_count += 1
            entry.last_seen = datetime.now().isoformat()
            
            # Add example if not already present
            context = issue.get("context", "")
            if context and context not in entry.examples:
                entry.examples.append(context)
                # Keep only last 10 examples
                entry.examples = entry.examples[-10:]
        else:
            # Create new entry
            entry = KnowledgeEntry(
                id=entry_id,
                category=self._categorize_issue(issue_type),
                pattern=issue_type,
                description=message,
                severity=severity,
                examples=[issue.get("context", "")],
                fixes=[issue.get("suggestion", "")],
                occurrence_count=1,
                last_seen=datetime.now().isoformat()
            )
            
            self.knowledge_base[entry_id] = entry
            self._update_indices(entry)
        
        self.save()
    
    def query(self, query: str, category: Optional[str] = None) -> List[KnowledgeEntry]:
        """Query knowledge base"""
        results = []
        
        query_lower = query.lower()
        
        for entry in self.knowledge_base.values():
            if category and entry.category != category:
                continue
            
            # Match against pattern, description, or examples
            if (query_lower in entry.pattern.lower() or
                query_lower in entry.description.lower() or
                any(query_lower in example.lower() for example in entry.examples)):
                results.append(entry)
        
        # Sort by occurrence count
        results.sort(key=lambda x: x.occurrence_count, reverse=True)
        
        return results
    
    def get_top_issues(self, n: int = 10, category: Optional[str] = None) -> List[KnowledgeEntry]:
        """Get top N issues by occurrence"""
        entries = list(self.knowledge_base.values())
        
        if category:
            entries = [e for e in entries if e.category == category]
        
        entries.sort(key=lambda x: x.occurrence_count, reverse=True)
        
        return entries[:n]
    
    def get_related_patterns(self, pattern: str) -> List[KnowledgeEntry]:
        """Get related patterns"""
        entry_id = f"kb_{pattern}"
        
        if entry_id not in self.knowledge_base:
            return []
        
        entry = self.knowledge_base[entry_id]
        related = []
        
        for related_id in entry.related_patterns:
            if related_id in self.knowledge_base:
                related.append(self.knowledge_base[related_id])
        
        return related
    
    def get_best_practices(self, context: str) -> List[KnowledgeEntry]:
        """Get best practices for a context"""
        return self.query(context, category="best-practice")
    
    def get_context_for_llm(self, issue_type: str) -> str:
        """Get context string to inject into LLM prompt"""
        entry_id = f"kb_{issue_type}"
        
        if entry_id not in self.knowledge_base:
            return ""
        
        entry = self.knowledge_base[entry_id]
        
        context = [
            f"Historical context for {entry.pattern}:",
            f"Description: {entry.description}",
            f"Severity: {entry.severity}",
            f"Seen {entry.occurrence_count} times",
        ]
        
        if entry.examples:
            context.append("Common examples:")
            for example in entry.examples[:3]:
                context.append(f"  - {example}")
        
        if entry.fixes:
            context.append("Recommended fixes:")
            for fix in entry.fixes[:3]:
                context.append(f"  - {fix}")
        
        return "\n".join(context)
    
    def _categorize_issue(self, issue_type: str) -> str:
        """Categorize issue type"""
        security_keywords = ["sql_injection", "security", "secret", "password", "injection"]
        performance_keywords = ["performance", "optimization", "slow", "inefficient"]
        testing_keywords = ["test", "coverage", "assert"]
        
        issue_lower = issue_type.lower()
        
        if any(keyword in issue_lower for keyword in security_keywords):
            return "security"
        elif any(keyword in issue_lower for keyword in performance_keywords):
            return "performance"
        elif any(keyword in issue_lower for keyword in testing_keywords):
            return "testing"
        else:
            return "anti-pattern"
    
    def _update_indices(self, entry: KnowledgeEntry):
        """Update search indices"""
        self.category_index[entry.category].append(entry.id)
        
        # Index by pattern keywords
        for word in entry.pattern.split('_'):
            if len(word) > 3:
                self.pattern_index[word.lower()].append(entry.id)
    
    def _initialize_default_knowledge(self):
        """Initialize with common patterns"""
        default_patterns = [
            KnowledgeEntry(
                id="kb_sql_injection",
                category="security",
                pattern="sql_injection",
                description="SQL injection vulnerability from string formatting",
                severity="CRITICAL",
                examples=['cursor.execute(f"SELECT * FROM users WHERE id={user_id}")'],
                fixes=["Use parameterized queries", "Use ORM with proper escaping"],
                related_patterns=["kb_command_injection"]
            ),
            KnowledgeEntry(
                id="kb_bare_except",
                category="anti-pattern",
                pattern="bare_except",
                description="Bare except clause catches all exceptions",
                severity="HIGH",
                examples=["except:", "except: pass"],
                fixes=["Specify exception types", "Use except Exception: for general catch"],
                related_patterns=["kb_silent_exception"]
            ),
            KnowledgeEntry(
                id="kb_magic_number",
                category="anti-pattern",
                pattern="magic_number",
                description="Unexplained numeric constant in code",
                severity="MEDIUM",
                examples=["if len(items) > 100:", "time.sleep(3600)"],
                fixes=["Extract to named constant with explanation"],
                related_patterns=["kb_hardcoded_value"]
            ),
            KnowledgeEntry(
                id="kb_long_function",
                category="anti-pattern",
                pattern="long_function",
                description="Function exceeds recommended length",
                severity="MEDIUM",
                examples=[],
                fixes=["Break into smaller functions", "Extract helper methods"],
                related_patterns=["kb_god_class", "kb_deep_nesting"]
            ),
            KnowledgeEntry(
                id="kb_dependency_injection",
                category="best-practice",
                pattern="dependency_injection",
                description="Pass dependencies as parameters instead of hardcoding",
                severity="LOW",
                examples=["def process(db_conn, logger):", "class Service(config):"],
                fixes=["Use dependency injection pattern"],
                related_patterns=["kb_tight_coupling"]
            ),
            KnowledgeEntry(
                id="kb_transaction_handling",
                category="best-practice",
                pattern="transaction_handling",
                description="Proper database transaction management",
                severity="HIGH",
                examples=["with db.transaction():", "db.commit()", "db.rollback()"],
                fixes=["Use context managers for transactions", "Always handle rollback"],
                related_patterns=["kb_resource_leak"]
            ),
            KnowledgeEntry(
                id="kb_list_comprehension",
                category="performance",
                pattern="list_comprehension",
                description="Use list comprehension instead of loops for simple transformations",
                severity="LOW",
                examples=["[x*2 for x in items]", "[item.name for item in objects]"],
                fixes=["Replace loop with list comprehension"],
                related_patterns=["kb_generator_expression"]
            ),
        ]
        
        for entry in default_patterns:
            self.knowledge_base[entry.id] = entry
            self._update_indices(entry)
        
        self.save()
        logger.info(f"Initialized knowledge base with {len(default_patterns)} default patterns")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        stats = {
            "total_entries": len(self.knowledge_base),
            "by_category": {},
            "by_severity": {},
            "top_patterns": []
        }
        
        for entry in self.knowledge_base.values():
            stats["by_category"][entry.category] = stats["by_category"].get(entry.category, 0) + 1
            stats["by_severity"][entry.severity] = stats["by_severity"].get(entry.severity, 0) + 1
        
        top = self.get_top_issues(5)
        stats["top_patterns"] = [
            {
                "pattern": e.pattern,
                "count": e.occurrence_count,
                "severity": e.severity
            }
            for e in top
        ]
        
        return stats
