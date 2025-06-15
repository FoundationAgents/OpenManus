import asyncio
import unittest
from app.agent.base import BaseAgent, AgentState
from app.schema import Message, ROLE_TYPE # For potential memory checks, and Message type hinting
from app.llm import LLM # BaseAgent has an LLM field
from app.memory import Memory # BaseAgent has a Memory field


# Define a Mock Agent Class for testing feedback pausing
class MockPausingAgent(BaseAgent):
    name: str = "MockPausingAgent" # Provide a default name

    async def step(self) -> str:
        """Simulates a step execution."""
        # self.current_step is incremented by BaseAgent.run before step() is called
        return f"Step {self.current_step} executed."

    async def should_request_feedback(self) -> bool:
        """Requests feedback when current_step equals max_steps."""
        if self.current_step == self.max_steps:
            # This condition means feedback is requested *after* the step defined by max_steps has run.
            # BaseAgent.run increments current_step, then calls should_request_feedback.
            # So if max_steps = 2, feedback is requested when current_step is 2.
            return True
        return False

    # Override other abstract methods if BaseAgent becomes fully abstract
    # For now, only step and should_request_feedback are abstract in the problem context

class TestBaseAgentFeedbackPausing(unittest.IsolatedAsyncioTestCase):

    async def test_agent_pauses_for_feedback_at_max_steps(self):
        """
        Tests that the agent pauses (enters AWAITING_USER_FEEDBACK state)
        when should_request_feedback returns True.
        """
        test_max_steps = 2
        agent = MockPausingAgent(
            name="TestPausingAgentInstance", # Instance specific name
            max_steps=test_max_steps,
            # LLM and Memory will use default_factory from BaseAgent
            # No need for real LLM or complex memory for this specific test
        )

        # Initial request to start the agent's run cycle
        initial_request = "Test initial task"
        await agent.run(request=initial_request)

        # 1. Assert the final state
        # The agent should pause because should_request_feedback returns True at current_step == max_steps
        self.assertEqual(agent.state, AgentState.AWAITING_USER_FEEDBACK)

        # 2. Assert the number of steps taken
        # The agent should have executed exactly max_steps.
        # BaseAgent's run loop:
        # - current_step starts at 0
        # - Loop 1: current_step becomes 1, should_request_feedback (returns False if max_steps=2), step()
        # - Loop 2: current_step becomes 2, should_request_feedback (returns True if max_steps=2), loop breaks
        # So, step() is called for current_step = 1 and current_step = 2.
        self.assertEqual(agent.current_step, test_max_steps)
        
        # 3. Optional: Check memory for initial user message (demonstrates run started)
        self.assertTrue(any(msg.content == initial_request and msg.role == ROLE_TYPE.USER for msg in agent.memory.messages))


if __name__ == '__main__':
    unittest.main()
