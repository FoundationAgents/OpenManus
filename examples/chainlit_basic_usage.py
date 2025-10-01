#!/usr/bin/env python
"""Basic usage example for OpenManus Chainlit integration."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.frontend.chainlit_app import ChainlitOpenManus
from app.logger import logger


async def basic_usage_example():
    """Demonstrate basic usage of the Chainlit integration."""

    print("🚀 OpenManus Chainlit Integration - Basic Usage Example\n")

    # Create instance
    chainlit_manus = ChainlitOpenManus()

    try:
        # Initialize agent
        print("📡 Initializing OpenManus agent...")
        agent = await chainlit_manus.initialize_agent()
        print("✅ Agent initialized successfully!\n")

        # Example queries
        queries = [
            "Hello! What can you help me with?",
            "What tools do you have available?",
            "Can you explain how you work?",
        ]

        for i, query in enumerate(queries, 1):
            print(f"Query {i}: {query}")
            print("-" * 50)

            response = await agent.run(query)
            print(f"Response: {response}\n")

            # Add to conversation history
            chainlit_manus.conversation_history.extend(
                [
                    {"role": "user", "content": query},
                    {"role": "assistant", "content": response},
                ]
            )

        # Show conversation history
        print("📜 Conversation History:")
        print("=" * 50)
        for msg in chainlit_manus.conversation_history:
            role = msg["role"].title()
            content = (
                msg["content"][:100] + "..."
                if len(msg["content"]) > 100
                else msg["content"]
            )
            print(f"{role}: {content}\n")

        print("✅ Basic usage example completed successfully!")

    except Exception as e:
        print(f"❌ Error during example: {e}")

    finally:
        # Cleanup
        print("🧹 Cleaning up agent resources...")
        await chainlit_manus.cleanup_agent()
        print("✅ Cleanup completed!")


if __name__ == "__main__":
    asyncio.run(basic_usage_example())
