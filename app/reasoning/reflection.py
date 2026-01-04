"""
Reflection Engine for self-improving planning and execution.

This module implements self-reflection capabilities that allow the agent to:
1. Learn from past execution successes and failures
2. Adapt plans based on historical performance
3. Identify recurring error patterns
4. Improve over time through experience accumulation

Based on the "Reflexion" paradigm (Shinn et al., 2023) and production experience
with long-running agentic systems.

Key concepts:
- **Reflection**: Analyzing past actions to extract lessons
- **Memory**: Storing reflections for future reference
- **Adaptation**: Modifying future plans based on past reflections
- **Meta-learning**: Improving the reflection process itself over time
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.logger import logger


class ExecutionRecord(BaseModel):
    """
    Record of a single plan execution attempt.

    Captures:
    - What was attempted (plan_content)
    - What happened (outcome, success)
    - Why it succeeded/failed (error_message, metrics)
    - When it occurred (timestamp)

    Design rationale:
    - Immutable after creation for audit trail integrity
    - Includes both structured (success, metrics) and unstructured (outcome) data
    - Timestamp for temporal analysis and decay of old learnings
    """

    id: str = Field(..., description="Unique execution ID")
    plan_content: str = Field(..., description="The plan that was executed")
    task_description: str = Field(..., description="Original task/goal")
    success: bool = Field(..., description="Whether execution succeeded")
    outcome: str = Field(..., description="Description of what happened")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    metrics: Dict = Field(default_factory=dict, description="Performance metrics")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict = Field(default_factory=dict, description="Additional context")

    class Config:
        frozen = True  # Immutable for audit trail


class Reflection(BaseModel):
    """
    A learned insight from past executions.

    Reflections are higher-level insights extracted from execution records.
    They represent actionable lessons that can improve future planning.

    Examples:
    - "When task involves file I/O, always check file exists first"
    - "API calls to service X often timeout; add retry logic"
    - "Breaking complex tasks into <5 steps improves success rate"

    Design rationale:
    - Separate from raw execution records (abstraction)
    - Includes confidence score (some lessons are stronger than others)
    - Tracks supporting evidence (which executions led to this insight)
    - Can be updated as more evidence accumulates
    """

    id: str = Field(..., description="Unique reflection ID")
    insight: str = Field(..., min_length=10, description="The learned lesson")
    category: str = Field(
        ..., description="Type of insight (e.g., 'error_handling', 'planning')"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in this insight (0-1)"
    )
    supporting_execution_ids: List[str] = Field(
        default_factory=list, description="Evidence"
    )
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    application_count: int = Field(0, ge=0, description="Times applied to new plans")

    class Config:
        frozen = False  # Mutable to update confidence and application_count


class ReflectionEngine:
    """
    Engine for self-reflection and continuous improvement.

    This is the core component that enables agents to learn from experience.
    It maintains:
    - A history of execution records (what happened)
    - A library of reflections (what was learned)
    - Logic to generate new reflections from records
    - Logic to apply reflections to improve future plans

    Production considerations:
    - Persists to disk/DB for long-term memory (not implemented here, but easy to add)
    - Limits memory usage by capping history size
    - Prioritizes recent and high-confidence reflections
    - Provides clear audit trail for debugging

    Typical usage:
        engine = ReflectionEngine(max_history=100)

        # After execution
        record = engine.add_execution_record(
            plan="Step 1: ...",
            task="Build web app",
            success=False,
            outcome="File not found error"
        )

        # Generate insights
        reflections = await engine.generate_reflections(llm)

        # Apply to new plan
        improved_plan = await engine.improve_plan(original_plan, task, llm)
    """

    def __init__(
        self,
        max_history: int = 100,
        min_confidence_threshold: float = 0.6,
        enable_auto_reflection: bool = True,
    ):
        """
        Initialize the reflection engine.

        Args:
            max_history: Maximum number of execution records to keep
                        Typical: 50-200. Higher = more memory, better learning.
            min_confidence_threshold: Minimum confidence to apply a reflection
                                     Typical: 0.5-0.7. Higher = more conservative.
            enable_auto_reflection: Auto-generate reflections after each execution

        Design choices:
        - Default max_history=100 balances memory and learning
        - Default threshold=0.6 filters out weak/uncertain insights
        - Auto-reflection enabled for continuous learning
        """
        if max_history < 1:
            raise ValueError("max_history must be at least 1")
        if not 0.0 <= min_confidence_threshold <= 1.0:
            raise ValueError("min_confidence_threshold must be between 0.0 and 1.0")

        self.max_history = max_history
        self.min_confidence_threshold = min_confidence_threshold
        self.enable_auto_reflection = enable_auto_reflection

        self.execution_history: List[ExecutionRecord] = []
        self.reflections: Dict[str, Reflection] = {}

        logger.info(
            f"Initialized ReflectionEngine: max_history={max_history}, "
            f"min_confidence={min_confidence_threshold}, auto_reflect={enable_auto_reflection}"
        )

    def add_execution_record(
        self,
        plan_content: str,
        task_description: str,
        success: bool,
        outcome: str,
        error_message: Optional[str] = None,
        metrics: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> ExecutionRecord:
        """
        Add a new execution record to the history.

        Args:
            plan_content: The plan that was executed
            task_description: Original task/goal
            success: Whether execution succeeded
            outcome: Description of what happened
            error_message: Error details if failed
            metrics: Performance metrics (e.g., {"duration_sec": 5.2, "steps_completed": 3})
            metadata: Additional context

        Returns:
            The created ExecutionRecord

        Side effects:
        - Adds record to history
        - Trims history if max_history exceeded
        - Logs the addition

        Thread safety:
        - Not thread-safe. Use locks if calling from multiple threads.
        """
        record_id = f"exec_{len(self.execution_history):04d}_{int(datetime.utcnow().timestamp())}"

        record = ExecutionRecord(
            id=record_id,
            plan_content=plan_content,
            task_description=task_description,
            success=success,
            outcome=outcome,
            error_message=error_message,
            metrics=metrics or {},
            metadata=metadata or {},
        )

        self.execution_history.append(record)

        # Trim history if needed (keep most recent)
        if len(self.execution_history) > self.max_history:
            removed = self.execution_history.pop(0)
            logger.debug(f"Trimmed old execution record: {removed.id}")

        logger.info(
            f"Added execution record {record_id}: "
            f"success={success}, task='{task_description[:50]}...'"
        )

        return record

    async def generate_reflections(
        self, llm, focus_on_failures: bool = True, max_new_reflections: int = 5
    ) -> List[Reflection]:
        """
        Generate new reflections from recent execution history.

        Args:
            llm: LLM instance for generating insights
            focus_on_failures: Prioritize learning from failures (recommended)
            max_new_reflections: Maximum number of new reflections to generate

        Returns:
            List of newly generated reflections

        Strategy:
        - Analyzes recent executions (especially failures)
        - Asks LLM to extract patterns and lessons
        - Creates Reflection objects with confidence scores
        - Deduplicates with existing reflections

        Performance:
        - Single LLM call for all recent records (batched)
        - Typical latency: 1-3 seconds
        - Should be called periodically, not after every execution
        """
        if not self.execution_history:
            logger.info("No execution history to reflect on")
            return []

        # Select records to analyze
        records_to_analyze = self.execution_history[-20:]  # Last 20 executions

        if focus_on_failures:
            # Prioritize failures
            failures = [r for r in records_to_analyze if not r.success]
            if failures:
                records_to_analyze = failures[-10:]  # Last 10 failures

        # Build reflection prompt
        records_summary = "\n\n".join(
            [
                f"Execution {i+1}:\n"
                f"Task: {r.task_description}\n"
                f"Plan: {r.plan_content[:200]}...\n"
                f"Success: {r.success}\n"
                f"Outcome: {r.outcome}\n"
                f"Error: {r.error_message or 'N/A'}"
                for i, r in enumerate(records_to_analyze)
            ]
        )

        prompt = f"""Analyze these recent task execution records and extract key learnings:

{records_summary}

Please provide {max_new_reflections} actionable insights that could improve future planning and execution.
For each insight, provide:
1. The insight/lesson (clear and specific)
2. Category (e.g., "error_handling", "planning", "tool_usage", "validation")
3. Confidence (0.0-1.0, how sure you are this insight is valuable)

Format as JSON array:
[
  {{"insight": "...", "category": "...", "confidence": 0.8}},
  ...
]
"""

        try:
            # Get LLM response
            response = await llm.ask(messages=[{"role": "user", "content": prompt}])

            # Parse JSON response
            insights = self._parse_insights_from_response(response)

            # Create Reflection objects
            new_reflections = []
            for insight_data in insights[:max_new_reflections]:
                reflection = self._create_reflection(
                    insight=insight_data.get("insight", ""),
                    category=insight_data.get("category", "general"),
                    confidence=insight_data.get("confidence", 0.5),
                    supporting_records=[r.id for r in records_to_analyze],
                )
                if reflection:
                    new_reflections.append(reflection)

            logger.info(f"Generated {len(new_reflections)} new reflections")
            return new_reflections

        except Exception as e:
            logger.error(f"Error generating reflections: {e}")
            return []

    def _parse_insights_from_response(self, response: str) -> List[Dict]:
        """
        Parse insights from LLM response.

        Handles both JSON and plain text responses.
        Returns empty list if parsing fails.
        """
        try:
            # Try to find JSON array in response
            import re

            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if json_match:
                insights = json.loads(json_match.group(0))
                if isinstance(insights, list):
                    return insights
        except Exception as e:
            logger.warning(f"Failed to parse insights as JSON: {e}")

        # Fallback: treat entire response as single insight
        return [
            {
                "insight": response[:500],  # Truncate if too long
                "category": "general",
                "confidence": 0.5,
            }
        ]

    def _create_reflection(
        self,
        insight: str,
        category: str,
        confidence: float,
        supporting_records: List[str],
    ) -> Optional[Reflection]:
        """
        Create a new reflection and add to library.

        Deduplicates with existing reflections.
        Returns None if insight is too similar to existing one.
        """
        if not insight or len(insight.strip()) < 10:
            logger.warning("Skipping empty or too-short insight")
            return None

        # Check for duplicates (simple string similarity)
        for existing in self.reflections.values():
            if self._is_similar(insight, existing.insight):
                logger.debug(f"Skipping duplicate insight: {insight[:50]}...")
                # Update existing reflection instead
                existing.confidence = max(existing.confidence, confidence)
                existing.supporting_execution_ids.extend(supporting_records)
                existing.last_updated = datetime.utcnow().isoformat()
                return None

        # Create new reflection
        reflection_id = f"reflect_{len(self.reflections):04d}"
        reflection = Reflection(
            id=reflection_id,
            insight=insight.strip(),
            category=category,
            confidence=confidence,
            supporting_execution_ids=supporting_records,
        )

        self.reflections[reflection_id] = reflection
        logger.info(f"Created reflection {reflection_id}: {insight[:50]}...")

        return reflection

    def _is_similar(self, text1: str, text2: str, threshold: float = 0.7) -> bool:
        """
        Check if two texts are similar (simple Jaccard similarity).

        This is a basic implementation. In production, consider:
        - Sentence embeddings (e.g., sentence-transformers)
        - Fuzzy string matching (e.g., fuzzywuzzy)
        - Semantic similarity via LLM
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return False

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        similarity = len(intersection) / len(union)
        return similarity >= threshold

    async def improve_plan(
        self,
        original_plan: str,
        task_description: str,
        llm,
        max_reflections_to_apply: int = 5,
    ) -> Tuple[str, List[str]]:
        """
        Improve a plan by applying relevant reflections.

        Args:
            original_plan: The initial plan to improve
            task_description: The task this plan is for
            llm: LLM instance for generating improved plan
            max_reflections_to_apply: Max number of reflections to consider

        Returns:
            Tuple of (improved_plan, applied_reflection_ids)

        Strategy:
        - Selects most relevant and confident reflections
        - Provides them as context to LLM
        - Asks LLM to revise plan incorporating lessons
        - Tracks which reflections were applied (for metrics)

        Performance:
        - Single LLM call
        - Typical latency: 1-2 seconds
        """
        if not self.reflections:
            logger.info("No reflections available to improve plan")
            return original_plan, []

        # Select relevant reflections
        relevant_reflections = self._select_relevant_reflections(
            task_description, max_count=max_reflections_to_apply
        )

        if not relevant_reflections:
            logger.info("No relevant reflections found for this task")
            return original_plan, []

        # Build improvement prompt
        reflections_text = "\n".join(
            [
                f"{i+1}. [{r.category}] {r.insight} (confidence: {r.confidence:.2f})"
                for i, r in enumerate(relevant_reflections)
            ]
        )

        prompt = f"""You are improving a plan based on past learnings.

Task: {task_description}

Original Plan:
{original_plan}

Relevant Lessons Learned:
{reflections_text}

Please provide an improved version of the plan that incorporates these lessons.
Focus on:
- Addressing potential errors identified in past executions
- Adding validation or error handling steps
- Improving clarity and structure
- Maintaining feasibility and conciseness

Improved Plan:"""

        try:
            # Get improved plan from LLM
            improved_plan = await llm.ask(
                messages=[{"role": "user", "content": prompt}]
            )

            # Update application counts
            applied_ids = []
            for reflection in relevant_reflections:
                reflection.application_count += 1
                applied_ids.append(reflection.id)

            logger.info(
                f"Improved plan using {len(applied_ids)} reflections: "
                f"{[r.id for r in relevant_reflections]}"
            )

            return improved_plan.strip(), applied_ids

        except Exception as e:
            logger.error(f"Error improving plan: {e}")
            return original_plan, []

    def _select_relevant_reflections(
        self, task_description: str, max_count: int = 5
    ) -> List[Reflection]:
        """
        Select most relevant reflections for a task.

        Relevance scoring considers:
        - Confidence (higher is better)
        - Recency (newer is better)
        - Application count (less used = more novel)
        - Keyword overlap with task (simple heuristic)

        Returns reflections sorted by relevance (descending).
        """
        if not self.reflections:
            return []

        # Filter by confidence threshold
        candidates = [
            r
            for r in self.reflections.values()
            if r.confidence >= self.min_confidence_threshold
        ]

        if not candidates:
            return []

        # Score each reflection
        task_words = set(task_description.lower().split())

        def relevance_score(reflection: Reflection) -> float:
            # Confidence component (0-1)
            conf_score = reflection.confidence

            # Recency component (0-1, decays over time)
            # Note: This is simplified; in production, use actual time decay
            recency_score = 0.5  # Placeholder

            # Novelty component (0-1, inversely proportional to application_count)
            novelty_score = 1.0 / (1.0 + reflection.application_count * 0.1)

            # Keyword overlap component (0-1)
            insight_words = set(reflection.insight.lower().split())
            overlap = len(task_words.intersection(insight_words))
            keyword_score = min(overlap / 10.0, 1.0)  # Normalize

            # Weighted combination
            return (
                0.4 * conf_score
                + 0.2 * recency_score
                + 0.2 * novelty_score
                + 0.2 * keyword_score
            )

        # Sort by relevance
        candidates.sort(key=relevance_score, reverse=True)

        return candidates[:max_count]

    def get_stats(self) -> Dict:
        """
        Get statistics about the reflection engine.

        Returns:
            Dict with keys: total_executions, success_rate, total_reflections,
                           avg_confidence, most_applied_reflection
        """
        if not self.execution_history:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "total_reflections": 0,
                "avg_confidence": 0.0,
                "most_applied_reflection": None,
            }

        successes = sum(1 for r in self.execution_history if r.success)
        success_rate = successes / len(self.execution_history)

        if self.reflections:
            avg_conf = sum(r.confidence for r in self.reflections.values()) / len(
                self.reflections
            )
            most_applied = max(
                self.reflections.values(), key=lambda r: r.application_count
            )
        else:
            avg_conf = 0.0
            most_applied = None

        return {
            "total_executions": len(self.execution_history),
            "success_rate": success_rate,
            "total_reflections": len(self.reflections),
            "avg_confidence": avg_conf,
            "most_applied_reflection": most_applied.insight[:100]
            if most_applied
            else None,
        }
