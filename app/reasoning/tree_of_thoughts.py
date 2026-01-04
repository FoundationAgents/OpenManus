"""
Tree-of-Thoughts (ToT) reasoning module for advanced planning.

This module implements the Tree-of-Thoughts reasoning paradigm, which enables:
1. Exploration of multiple planning alternatives in parallel
2. Systematic evaluation of each approach
3. Pruning of low-quality branches to focus computational resources
4. Selection of the optimal path based on cumulative quality scores

Based on the paper "Tree of Thoughts: Deliberate Problem Solving with Large Language Models"
(Yao et al., 2023) and adapted for production agentic systems.

Key improvements over basic chain-of-thought:
- Explores multiple reasoning paths simultaneously (breadth)
- Evaluates intermediate steps, not just final outputs (depth)
- Backtracks from dead ends automatically (pruning)
- Scales to complex multi-step planning tasks (robustness)
"""

import asyncio
import re
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator

from app.logger import logger


class ThoughtNode(BaseModel):
    """
    Represents a single thought/plan node in the tree structure.

    Each node contains:
    - A specific plan or reasoning step (content)
    - Links to parent and children nodes (tree structure)
    - A quality score from LLM evaluation (0.0 to 1.0)
    - Metadata for tracking context and dependencies

    Design rationale:
    - Immutable once created (except score updates) for thread safety
    - Pydantic model for automatic validation and serialization
    - Metadata dict for extensibility without schema changes
    """

    id: str = Field(..., description="Unique identifier for this thought node")
    content: str = Field(
        ..., min_length=1, description="The actual thought/plan content"
    )
    parent_id: Optional[str] = Field(
        None, description="ID of parent node (None for root)"
    )
    children_ids: List[str] = Field(
        default_factory=list, description="IDs of child nodes"
    )
    score: float = Field(0.0, ge=0.0, le=1.0, description="Quality score (0.0-1.0)")
    depth: int = Field(0, ge=0, description="Depth in tree (0 for root)")
    metadata: Dict = Field(
        default_factory=dict, description="Extensible metadata storage"
    )

    @validator("content")
    def content_not_empty(cls, v):
        """Ensure content is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Thought content cannot be empty or whitespace")
        return v.strip()

    class Config:
        """Pydantic configuration."""

        frozen = False  # Allow score updates
        validate_assignment = True  # Validate on attribute changes


class TreeOfThoughts:
    """
    Implements Tree-of-Thoughts reasoning for exploring multiple planning paths.

    This is a production-ready implementation with:
    - Async evaluation for parallel processing
    - Automatic pruning to manage memory
    - Robust error handling and logging
    - Configurable depth and branching limits

    Typical usage:
        tot = TreeOfThoughts(max_depth=3, max_branches=3)
        root = tot.add_thought("Initial task: Build a web app")

        # Generate alternatives
        for alt in ["Use React", "Use Vue", "Use Svelte"]:
            tot.add_thought(alt, parent_id=root.id)

        # Evaluate all nodes
        await tot.evaluate_all_thoughts(llm, evaluation_prompt)

        # Get best path
        best_path = tot.get_best_path()

    Performance considerations:
    - Evaluations run in parallel using asyncio.gather()
    - Pruning happens automatically to prevent memory bloat
    - Max depth prevents infinite recursion
    - Max branches prevents combinatorial explosion
    """

    def __init__(
        self,
        max_depth: int = 3,
        max_branches: int = 3,
        auto_prune_threshold: float = 0.3,
        enable_auto_prune: bool = True,
    ):
        """
        Initialize the tree-of-thoughts reasoner.

        Args:
            max_depth: Maximum depth of the thought tree (default: 3)
                      Typical range: 2-5. Higher = more thorough but slower.
            max_branches: Maximum number of branches per node (default: 3)
                         Typical range: 2-5. Higher = more alternatives explored.
            auto_prune_threshold: Score below which branches are pruned (default: 0.3)
            enable_auto_prune: Whether to automatically prune low-scoring branches

        Design choices:
        - Default max_depth=3 balances thoroughness with performance
        - Default max_branches=3 based on research showing diminishing returns beyond 3-5
        - Auto-pruning enabled by default to prevent memory issues in long-running tasks
        """
        if max_depth < 1:
            raise ValueError("max_depth must be at least 1")
        if max_branches < 1:
            raise ValueError("max_branches must be at least 1")
        if not 0.0 <= auto_prune_threshold <= 1.0:
            raise ValueError("auto_prune_threshold must be between 0.0 and 1.0")

        self.max_depth = max_depth
        self.max_branches = max_branches
        self.auto_prune_threshold = auto_prune_threshold
        self.enable_auto_prune = enable_auto_prune

        self.nodes: Dict[str, ThoughtNode] = {}
        self.root_id: Optional[str] = None

        logger.info(
            f"Initialized TreeOfThoughts: max_depth={max_depth}, "
            f"max_branches={max_branches}, auto_prune={enable_auto_prune}"
        )

    def add_thought(
        self,
        content: str,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        force: bool = False,
    ) -> Optional[ThoughtNode]:
        """
        Add a new thought node to the tree.

        Args:
            content: The thought/plan content (must be non-empty)
            parent_id: ID of the parent node (None for root)
            metadata: Additional metadata (e.g., {"agent": "planner", "step": 1})
            force: If True, bypass depth and branching limits (use with caution)

        Returns:
            The created ThoughtNode, or None if limits exceeded

        Error handling:
        - Returns None if parent doesn't exist (logs warning)
        - Returns None if depth/branch limits exceeded (logs info)
        - Raises ValueError if content is invalid (caught by Pydantic)

        Thread safety:
        - Not thread-safe. Use locks if calling from multiple threads.
        """
        # Validate parent exists
        if parent_id is not None and parent_id not in self.nodes:
            logger.warning(f"Parent node {parent_id} not found. Cannot add thought.")
            return None

        # Check depth limit
        depth = 0
        if parent_id:
            parent = self.nodes[parent_id]
            depth = parent.depth + 1

            if not force and depth > self.max_depth:
                logger.info(
                    f"Max depth {self.max_depth} reached. "
                    f"Skipping thought at depth {depth}."
                )
                return None

            # Check branching limit
            if not force and len(parent.children_ids) >= self.max_branches:
                logger.info(
                    f"Max branches {self.max_branches} reached for parent {parent_id}. "
                    f"Skipping thought."
                )
                return None

        # Generate unique ID
        node_id = f"thought_{len(self.nodes):04d}"

        # Create node
        try:
            node = ThoughtNode(
                id=node_id,
                content=content,
                parent_id=parent_id,
                depth=depth,
                metadata=metadata or {},
            )
        except Exception as e:
            logger.error(f"Failed to create thought node: {e}")
            return None

        # Add to tree
        self.nodes[node_id] = node

        # Update parent's children list
        if parent_id:
            parent = self.nodes[parent_id]
            parent.children_ids.append(node_id)

        # Set as root if first node
        if self.root_id is None:
            self.root_id = node_id
            logger.info(f"Set root node: {node_id}")

        logger.debug(
            f"Added thought node {node_id} at depth {depth} "
            f"(parent: {parent_id or 'None'})"
        )

        return node

    async def evaluate_thought(
        self, node_id: str, llm, evaluation_prompt: str, retry_on_error: bool = True
    ) -> float:
        """
        Evaluate the quality of a thought using an LLM.

        Args:
            node_id: ID of the node to evaluate
            llm: LLM instance with async ask() method
            evaluation_prompt: Prompt template with {thought} placeholder
            retry_on_error: Whether to retry once on LLM errors

        Returns:
            Score between 0.0 and 1.0 (0.5 default on error)

        Evaluation strategy:
        - Asks LLM to rate the thought on a 0-10 scale
        - Normalizes to 0.0-1.0 range
        - Uses regex to extract numeric score from response
        - Falls back to 0.5 (neutral) if parsing fails

        Error handling:
        - Returns 0.0 if node doesn't exist
        - Returns 0.5 on LLM errors (with optional retry)
        - Logs all errors for debugging

        Performance:
        - Async for parallel evaluation of multiple nodes
        - Typical latency: 200-500ms per evaluation (LLM-dependent)
        """
        if node_id not in self.nodes:
            logger.error(f"Node {node_id} not found for evaluation")
            return 0.0

        node = self.nodes[node_id]

        # Create evaluation prompt
        try:
            prompt = evaluation_prompt.format(thought=node.content)
        except KeyError as e:
            logger.error(f"Evaluation prompt missing placeholder: {e}")
            return 0.5

        # Attempt evaluation (with optional retry)
        for attempt in range(2 if retry_on_error else 1):
            try:
                # Get LLM evaluation
                response = await llm.ask(messages=[{"role": "user", "content": prompt}])

                # Parse score from response
                # Expected format: "Score: 7.5" or just "7.5" or "8/10"
                score = self._parse_score_from_response(response)

                # Update node score
                node.score = score

                logger.debug(
                    f"Evaluated node {node_id}: score={score:.2f} "
                    f"(attempt {attempt + 1})"
                )

                return score

            except Exception as e:
                logger.error(
                    f"Error evaluating thought {node_id} (attempt {attempt + 1}): {e}"
                )
                if attempt == 0 and retry_on_error:
                    logger.info("Retrying evaluation...")
                    await asyncio.sleep(0.5)  # Brief delay before retry

        # Default to neutral score on persistent errors
        logger.warning(f"Using default score 0.5 for node {node_id} after errors")
        node.score = 0.5
        return 0.5

    def _parse_score_from_response(self, response: str) -> float:
        """
        Parse a numeric score from LLM response text.

        Handles multiple formats:
        - "Score: 8.5" -> 0.85
        - "8.5" -> 0.85
        - "8/10" -> 0.8
        - "The score is 7 out of 10" -> 0.7

        Returns:
            Normalized score (0.0-1.0), or 0.5 if parsing fails
        """
        if not response:
            return 0.5

        # Try to find "X/10" format first
        fraction_match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", response)
        if fraction_match:
            score = float(fraction_match.group(1))
            return min(max(score / 10.0, 0.0), 1.0)

        # Try to find any decimal number
        number_match = re.search(r"(\d+(?:\.\d+)?)", response)
        if number_match:
            score = float(number_match.group(1))
            # Normalize to 0-1 range (assume 0-10 scale)
            if score > 1.0:
                score = score / 10.0
            return min(max(score, 0.0), 1.0)

        # Parsing failed
        logger.warning(f"Could not parse score from response: {response[:100]}")
        return 0.5

    async def evaluate_all_thoughts(
        self, llm, evaluation_prompt: str, parallel: bool = True
    ) -> Dict[str, float]:
        """
        Evaluate all nodes in the tree.

        Args:
            llm: LLM instance for evaluation
            evaluation_prompt: Prompt template with {thought} placeholder
            parallel: If True, evaluate nodes in parallel (faster)

        Returns:
            Dict mapping node_id to score

        Performance:
        - Parallel mode: ~500ms for 10 nodes (limited by LLM concurrency)
        - Sequential mode: ~5s for 10 nodes (200-500ms per node)
        - Recommend parallel=True for >3 nodes
        """
        if not self.nodes:
            logger.warning("No nodes to evaluate")
            return {}

        logger.info(f"Evaluating {len(self.nodes)} thoughts (parallel={parallel})")

        if parallel:
            # Evaluate all nodes in parallel
            tasks = [
                self.evaluate_thought(node_id, llm, evaluation_prompt)
                for node_id in self.nodes.keys()
            ]
            scores = await asyncio.gather(*tasks, return_exceptions=True)

            # Build result dict (handle exceptions)
            results = {}
            for node_id, score in zip(self.nodes.keys(), scores):
                if isinstance(score, Exception):
                    logger.error(f"Evaluation failed for {node_id}: {score}")
                    results[node_id] = 0.5
                else:
                    results[node_id] = score
        else:
            # Evaluate sequentially
            results = {}
            for node_id in self.nodes.keys():
                score = await self.evaluate_thought(node_id, llm, evaluation_prompt)
                results[node_id] = score

        # Auto-prune if enabled
        if self.enable_auto_prune:
            self.prune_low_scoring_branches(self.auto_prune_threshold)

        logger.info(
            f"Evaluation complete. Avg score: {sum(results.values()) / len(results):.2f}"
        )
        return results

    def get_best_path(self) -> List[ThoughtNode]:
        """
        Get the best path from root to a leaf node based on cumulative scores.

        Returns:
            List of nodes representing the best path (root to leaf)
            Empty list if tree is empty or root is missing

        Algorithm:
        - Uses dynamic programming to compute cumulative scores
        - Selects child with highest cumulative score at each level
        - Time complexity: O(n) where n is number of nodes

        Use case:
        - After evaluation, get the recommended plan to execute
        - The path represents the sequence of decisions/steps
        """
        if not self.root_id or self.root_id not in self.nodes:
            logger.warning("Cannot get best path: no valid root")
            return []

        def get_path_score(node_id: str) -> float:
            """
            Calculate cumulative score for a path ending at this node.

            Cumulative score = node.score + max(children's cumulative scores)
            This favors paths that are good at every step, not just the end.
            """
            if node_id not in self.nodes:
                return 0.0

            node = self.nodes[node_id]

            if not node.children_ids:
                # Leaf node: score is just this node's score
                return node.score

            # Internal node: score + best child path
            child_scores = [get_path_score(child_id) for child_id in node.children_ids]
            return node.score + max(child_scores) if child_scores else node.score

        def build_best_path(node_id: str) -> List[ThoughtNode]:
            """Recursively build the path with highest cumulative score."""
            if node_id not in self.nodes:
                return []

            node = self.nodes[node_id]
            path = [node]

            if node.children_ids:
                # Find child with best cumulative score
                best_child_id = max(
                    node.children_ids, key=lambda cid: get_path_score(cid)
                )
                path.extend(build_best_path(best_child_id))

            return path

        best_path = build_best_path(self.root_id)
        logger.info(
            f"Best path found: {len(best_path)} nodes, "
            f"cumulative score: {sum(n.score for n in best_path):.2f}"
        )
        return best_path

    def get_all_leaves(self) -> List[ThoughtNode]:
        """
        Get all leaf nodes (nodes without children).

        Returns:
            List of leaf nodes, sorted by score (descending)

        Use case:
        - Compare all final outcomes
        - Identify multiple viable alternatives
        """
        leaves = [node for node in self.nodes.values() if not node.children_ids]
        leaves.sort(key=lambda n: n.score, reverse=True)
        return leaves

    def prune_low_scoring_branches(self, threshold: float = 0.3):
        """
        Remove branches with scores below the threshold.

        Args:
            threshold: Minimum score to keep a branch (0.0-1.0)

        Strategy:
        - Removes nodes with score < threshold
        - Also removes all descendants of removed nodes
        - Never removes the root node

        Benefits:
        - Reduces memory usage
        - Focuses computation on promising paths
        - Prevents exploration of clearly bad alternatives

        Caution:
        - Pruning is irreversible
        - May remove paths that could improve later
        - Use conservative thresholds (0.2-0.4) in practice
        """
        if not 0.0 <= threshold <= 1.0:
            logger.error(f"Invalid threshold {threshold}. Must be 0.0-1.0.")
            return

        to_remove = []

        for node_id, node in self.nodes.items():
            if node_id == self.root_id:
                continue  # Never prune root

            if node.score < threshold:
                to_remove.append(node_id)

        if not to_remove:
            logger.debug("No branches to prune")
            return

        # Remove subtrees
        for node_id in to_remove:
            self._remove_subtree(node_id)

        logger.info(
            f"Pruned {len(to_remove)} low-scoring branches "
            f"(threshold={threshold:.2f})"
        )

    def _remove_subtree(self, node_id: str):
        """
        Remove a node and all its descendants.

        This is a recursive operation that:
        1. Removes all children first (depth-first)
        2. Removes the node from parent's children list
        3. Deletes the node from the tree

        Time complexity: O(n) where n is size of subtree
        """
        if node_id not in self.nodes:
            return

        node = self.nodes[node_id]

        # Recursively remove children first
        for child_id in list(
            node.children_ids
        ):  # Copy list to avoid modification during iteration
            self._remove_subtree(child_id)

        # Remove from parent's children list
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if node_id in parent.children_ids:
                parent.children_ids.remove(node_id)

        # Remove the node itself
        del self.nodes[node_id]
        logger.debug(f"Removed node {node_id}")

    def get_tree_stats(self) -> Dict:
        """
        Get statistics about the current tree.

        Returns:
            Dict with keys: total_nodes, max_depth_reached, avg_score,
                           num_leaves, avg_branching_factor

        Use case:
        - Monitoring and debugging
        - Logging for analysis
        """
        if not self.nodes:
            return {
                "total_nodes": 0,
                "max_depth_reached": 0,
                "avg_score": 0.0,
                "num_leaves": 0,
                "avg_branching_factor": 0.0,
            }

        depths = [node.depth for node in self.nodes.values()]
        scores = [node.score for node in self.nodes.values()]
        leaves = self.get_all_leaves()

        # Calculate average branching factor
        internal_nodes = [n for n in self.nodes.values() if n.children_ids]
        avg_branching = (
            sum(len(n.children_ids) for n in internal_nodes) / len(internal_nodes)
            if internal_nodes
            else 0.0
        )

        return {
            "total_nodes": len(self.nodes),
            "max_depth_reached": max(depths),
            "avg_score": sum(scores) / len(scores),
            "num_leaves": len(leaves),
            "avg_branching_factor": avg_branching,
        }
