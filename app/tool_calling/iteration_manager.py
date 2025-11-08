"""Iteration manager for multi-turn tool interactions.

Handles:
- Multiple tool calling iterations
- Conversation state management
- Iteration limits
- Result accumulation
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.logger import logger
from app.tool.base import ToolResult


@dataclass
class IterationState:
    """State for a single iteration."""
    
    iteration_number: int
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: Dict[str, ToolResult] = field(default_factory=dict)
    llm_response: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    
    def has_errors(self) -> bool:
        """Check if iteration has errors."""
        return len(self.errors) > 0
    
    def has_tool_calls(self) -> bool:
        """Check if iteration has tool calls."""
        return len(self.tool_calls) > 0
    
    def add_tool_call(self, name: str, args: Dict[str, Any]):
        """Add a tool call to this iteration."""
        self.tool_calls.append({"name": name, "args": args})
    
    def add_result(self, call_id: str, result: ToolResult):
        """Add a tool result."""
        self.tool_results[call_id] = result
    
    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)


@dataclass
class ConversationState:
    """State for entire tool calling conversation."""
    
    iterations: List[IterationState] = field(default_factory=list)
    max_iterations: int = 5
    current_iteration: int = 0
    final_response: Optional[str] = None
    
    def start_iteration(self) -> IterationState:
        """Start a new iteration.
        
        Returns:
            New IterationState
            
        Raises:
            RuntimeError: If max iterations exceeded
        """
        if self.current_iteration >= self.max_iterations:
            raise RuntimeError(
                f"Maximum iterations ({self.max_iterations}) exceeded"
            )
        
        self.current_iteration += 1
        iteration = IterationState(iteration_number=self.current_iteration)
        self.iterations.append(iteration)
        
        logger.debug(f"Started iteration {self.current_iteration}/{self.max_iterations}")
        
        return iteration
    
    def get_current_iteration(self) -> Optional[IterationState]:
        """Get the current iteration state."""
        if self.iterations:
            return self.iterations[-1]
        return None
    
    def should_continue(self) -> bool:
        """Check if should continue iterating.
        
        Returns:
            True if should continue
        """
        if self.current_iteration >= self.max_iterations:
            logger.warning(f"Reached maximum iterations ({self.max_iterations})")
            return False
        
        # Don't continue if last iteration had no tool calls
        current = self.get_current_iteration()
        if current and not current.has_tool_calls():
            return False
        
        return True
    
    def get_total_tool_calls(self) -> int:
        """Get total number of tool calls across all iterations."""
        return sum(len(it.tool_calls) for it in self.iterations)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of conversation state.
        
        Returns:
            Summary dictionary
        """
        return {
            "total_iterations": self.current_iteration,
            "max_iterations": self.max_iterations,
            "total_tool_calls": self.get_total_tool_calls(),
            "completed": not self.should_continue(),
            "has_final_response": self.final_response is not None,
            "iteration_details": [
                {
                    "iteration": it.iteration_number,
                    "tool_calls": len(it.tool_calls),
                    "errors": len(it.errors),
                    "has_response": it.llm_response is not None
                }
                for it in self.iterations
            ]
        }


class IterationManager:
    """Manage multi-turn tool calling iterations."""
    
    def __init__(self, max_iterations: int = 5):
        """Initialize iteration manager.
        
        Args:
            max_iterations: Maximum number of iterations allowed
        """
        self.max_iterations = max_iterations
        self._active_conversations: Dict[str, ConversationState] = {}
    
    def start_conversation(
        self,
        conversation_id: str,
        max_iterations: Optional[int] = None
    ) -> ConversationState:
        """Start a new conversation.
        
        Args:
            conversation_id: Unique conversation ID
            max_iterations: Override default max iterations
            
        Returns:
            New ConversationState
        """
        max_iter = max_iterations or self.max_iterations
        state = ConversationState(max_iterations=max_iter)
        self._active_conversations[conversation_id] = state
        
        logger.info(f"Started conversation {conversation_id} (max_iterations={max_iter})")
        
        return state
    
    def get_conversation(
        self,
        conversation_id: str
    ) -> Optional[ConversationState]:
        """Get an existing conversation state.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            ConversationState or None
        """
        return self._active_conversations.get(conversation_id)
    
    def end_conversation(
        self,
        conversation_id: str,
        final_response: Optional[str] = None
    ):
        """End a conversation.
        
        Args:
            conversation_id: Conversation ID
            final_response: Optional final response text
        """
        if conversation_id in self._active_conversations:
            state = self._active_conversations[conversation_id]
            state.final_response = final_response
            
            # Log summary
            summary = state.get_summary()
            logger.info(
                f"Ended conversation {conversation_id}: "
                f"{summary['total_iterations']} iterations, "
                f"{summary['total_tool_calls']} tool calls"
            )
            
            # Remove from active conversations
            del self._active_conversations[conversation_id]
    
    def should_continue_iteration(
        self,
        conversation_id: str
    ) -> bool:
        """Check if should continue iterating.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if should continue
        """
        state = self.get_conversation(conversation_id)
        if not state:
            return False
        
        return state.should_continue()
    
    def get_iteration_history(
        self,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """Get iteration history for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of iteration summaries
        """
        state = self.get_conversation(conversation_id)
        if not state:
            return []
        
        return state.get_summary()['iteration_details']
    
    def format_iteration_context(
        self,
        conversation_id: str
    ) -> str:
        """Format iteration context for LLM.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Formatted context string
        """
        state = self.get_conversation(conversation_id)
        if not state:
            return ""
        
        current = state.get_current_iteration()
        if not current:
            return ""
        
        context = f"[Iteration {current.iteration_number}/{state.max_iterations}]\n"
        
        if current.tool_calls:
            context += f"Tools called: {len(current.tool_calls)}\n"
        
        remaining = state.max_iterations - state.current_iteration
        if remaining <= 2:
            context += f"⚠️ Only {remaining} iterations remaining. Please provide a final answer.\n"
        
        return context
    
    def get_active_conversation_count(self) -> int:
        """Get number of active conversations.
        
        Returns:
            Count of active conversations
        """
        return len(self._active_conversations)
    
    def clear_all(self):
        """Clear all active conversations."""
        count = len(self._active_conversations)
        self._active_conversations.clear()
        logger.info(f"Cleared {count} active conversations")


# Global instance
_global_iteration_manager: Optional[IterationManager] = None


def get_iteration_manager() -> IterationManager:
    """Get the global iteration manager.
    
    Returns:
        Global IterationManager
    """
    global _global_iteration_manager
    
    if _global_iteration_manager is None:
        _global_iteration_manager = IterationManager()
    
    return _global_iteration_manager


def set_iteration_manager(manager: IterationManager):
    """Set the global iteration manager.
    
    Args:
        manager: IterationManager instance
    """
    global _global_iteration_manager
    _global_iteration_manager = manager
