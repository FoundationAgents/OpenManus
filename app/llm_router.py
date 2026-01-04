import threading
from typing import Dict, List, Optional, Union

from app.config import LLMSettings, config
from app.llm import LLM
from app.schema import Message


class LLMRouter:
    """
    FreEco.ai Multi-Model LLM Router.

    Orchestrates multiple LLM models based on task type for optimal performance.
    Part of Enhancement #1: Multi-Model LLM Orchestration.

    Manages a pool of LLM instances, each configured for specific tasks:
    - 'planning': High-capability model for complex reasoning (e.g., Claude 3.5 Sonnet)
    - 'executor': Fast, reliable model for task execution (e.g., GPT-4o-mini)
    - 'default': Fallback model for general use

    Part of the FreEco.ai Platform.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton implementation for LLMRouter."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    # Initialize LLM instances from the global config
                    self.models: Dict[str, LLM] = {}
                    llm_configs: Dict[str, LLMSettings] = config.llm

                    for name, llm_config in llm_configs.items():
                        # The existing LLM class is a singleton that uses a config_name
                        # We initialize it here to ensure all configured models are ready
                        # We pass the config_name to the LLM class to ensure it uses the correct settings
                        self.models[name] = LLM(config_name=name, llm_config=llm_config)

                    self._initialized = True

    def select_model(self, task_type: str) -> LLM:
        """
        Selects the appropriate LLM instance based on the task type.

        Args:
            task_type: The type of task (e.g., 'planning', 'execution', 'default').

        Returns:
            An initialized LLM instance.
        """
        # Simple routing logic:
        # 1. Try to find a model with a name matching the task_type (e.g., 'planning' model)
        # 2. Fallback to the 'default' model
        # 3. If 'default' is not found, raise an error

        if task_type in self.models:
            return self.models[task_type]

        if "default" in self.models:
            return self.models["default"]

        raise ValueError(
            f"No model found for task type '{task_type}' and no 'default' model is configured."
        )

    def route(
        self,
        task_type: str,
        messages: List[Union[dict, Message]],
        system_msgs: Optional[List[Union[dict, Message]]] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Routes the request to the appropriate LLM and gets the response.

        Args:
            task_type: The type of task (e.g., 'planning', 'execution').
            messages: List of conversation messages.
            system_msgs: Optional system messages to prepend.
            temperature: Sampling temperature for the response.

        Returns:
            The generated response string.
        """
        model = self.select_model(task_type)
        # Use the synchronous wrapper we added to the LLM class
        return model.ask_sync(
            messages=messages, system_msgs=system_msgs, temperature=temperature
        )


# Global instance of the router for easy access
llm_router = LLMRouter()
