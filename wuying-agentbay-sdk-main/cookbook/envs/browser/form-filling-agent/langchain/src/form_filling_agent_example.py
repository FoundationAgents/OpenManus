#!/usr/bin/env python3
"""
Example of using LangChain to orchestrate a form filling agent.
This script demonstrates how to use the LangChain agent framework to orchestrate form filling tasks.
"""

import os
import sys
import asyncio

# Add the project root and necessary paths
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'common'))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def main():
    """
    Main function to demonstrate LangChain orchestration of form filling agent.
    """
    print("Creating LangChain form filling agent...")
    
    # Import the agent creator function
    from form_filling_agent import create_langchain_form_filling_agent
    
    # Create the LangChain agent
    agent = create_langchain_form_filling_agent()
    
    # Get the form file path - correctly pointing to common/src/form.html
    form_path = os.path.join(project_root, "common", "src", "form.html")
    
    print(f"Form path: {form_path}")
    
    # Example Using the agent with custom instructions
    print("\n=== Example: Using agent with custom instructions ===")
    try:
        result = agent.invoke({
            "input": f"First analyze the form at {form_path}, then fill it with custom data: John as first name, Smith as last name, john.smith@example.com as email, and finally execute the filling process"
        })
        print("Agent result:")
        print(result)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()