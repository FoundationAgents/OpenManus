import os
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from langchain.agents import AgentExecutor, create_tool_calling_agent

from common.src.form_filler import FormFiller, get_default_form_instructions

# Load environment variables
load_dotenv()


class LangChainFormFillingAgent:
    """
    LangChain-specific implementation of the form filling agent.
    This class wraps the core FormFiller functionality in a LangChain-compatible interface.
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the LangChain form filling agent
        
        Args:
            api_key (str): Agent-Bay API key. If not provided, will be read from environment variables.
        """
        self.api_key = api_key or os.getenv("AGENTBAY_API_KEY")
        self.form_filler = FormFiller(self.api_key)
        self.field_instructions = None
    
    async def run(self, form_file_path, field_instructions=None):
        """
        Run the form filling agent
        
        Args:
            form_file_path (str): Path to the form HTML file
            field_instructions (list): List of instructions for filling form fields.
                                     If not provided, default instructions will be used.
        
        Returns:
            bool: True if the form was filled successfully
        """
        if field_instructions is None:
            field_instructions = get_default_form_instructions()
        
        self.field_instructions = field_instructions
        
        try:
            # Create session
            await self.form_filler.create_session()
            
            # Upload form file
            form_path_in_session = self.form_filler.upload_form_file(form_file_path)
            
            # Open form in browser
            await self.form_filler.open_form_in_browser(form_path_in_session)
            
            # Wait a bit for the page to load completely
            await self.form_filler.page.wait_for_timeout(2000)
            
            # Fill form
            result = await self.form_filler.fill_form_fields(field_instructions)
            
            # Wait to see the result
            await self.form_filler.page.wait_for_timeout(3000)

            current_file_path = os.path.dirname(os.path.abspath(__file__))
            framework_dir = os.path.dirname(current_file_path)  # Go up from src to langchain
            # Create data directory path in a more robust way
            data_dir = Path(framework_dir) / "data"
            data_dir.mkdir(parents=True, exist_ok=True)  # Ensure the data directory exists

            filled_page_screenshot_fn = os.path.join(data_dir, "filled_page_screenshot.png")

            self.form_filler.capture_screenshot(filled_page_screenshot_fn)
            
            print("Form filling agent completed successfully!")
            return result
            
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    async def cleanup(self):
        """Clean up resources"""
        await self.form_filler.close()


def create_form_filling_tools(agent: LangChainFormFillingAgent) -> List[Tool]:
    """
    Create LangChain tools for the form filling agent.
    
    Args:
        agent: LangChainFormFillingAgent instance
        
    Returns:
        List of LangChain tools
    """
    def analyze_form(form_path: str) -> str:
        """Analyze a form and suggest filling instructions."""
        try:
            # In a real implementation, we would analyze the form
            # For now, we'll just return a message indicating what would be done
            print(f"Execute tool analyze_form: {form_path}")
            return f"Form at {form_path} has been analyzed. Recommended instructions: {get_default_form_instructions()}"
        except Exception as e:
            return f"Error analyzing form: {str(e)}"
    
    def fill_form_fields(instructions: str) -> str:
        """Fill form fields with provided instructions."""
        try:
            print(f"Execute tool fill_form_fields: {instructions}")
            # Parse instructions from string to list
            instruction_list = [instr.strip() for instr in instructions.split(';') if instr.strip()]
            
            # Store instructions for later use
            agent.field_instructions = instruction_list
            
            return f"Prepared to fill form with {len(instruction_list)} instructions: {instruction_list}"
        except Exception as e:
            return f"Error preparing form filling: {str(e)}"
    
    def execute_form_filling(form_path: str) -> str:
        """Execute the form filling process."""
        try:
            print(f"Execute tool execute_form_filling: {form_path}, {agent.field_instructions}")
            # Run the agent with stored instructions
            result = asyncio.run(agent.run(form_path, agent.field_instructions))
            
            if result:
                return "Form filling completed successfully!"
            else:
                return "Form filling failed. Check logs for details."
        except Exception as e:
            return f"Error executing form filling: {str(e)}"
    
    return [
        Tool(
            name="analyze_form",
            func=analyze_form,
            description="Analyze a form and suggest filling instructions. Input should be the path to the form HTML file."
        ),
        Tool(
            name="fill_form_fields",
            func=fill_form_fields,
            description="Prepare to fill form fields with provided instructions. Input should be a semicolon-separated list of natural language instructions."
        ),
        Tool(
            name="execute_form_filling",
            func=execute_form_filling,
            description="Execute the form filling process. Input should be the path to the form HTML file."
        )
    ]


def create_langchain_form_filling_agent(api_key: str = None) -> AgentExecutor:
    """
    Create a LangChain agent for form filling.
    
    Args:
        api_key: Agent-Bay API key
        
    Returns:
        LangChain AgentExecutor
    """
    # Create form filling agent
    form_filling_agent = LangChainFormFillingAgent(api_key=api_key)
    
    # Create tools
    tools = create_form_filling_tools(form_filling_agent)
    
    # Initialize LLM
    llm = ChatOpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model=os.getenv("DASHSCOPE_MODEL", "qwen-plus")
    )
    
    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a form filling expert that helps users automatically fill web forms.
        
Available tools:
1. analyze_form - Analyze a form and suggest filling instructions. Takes form path as input.
2. fill_form_fields - Prepare to fill form fields with provided instructions. Takes semicolon-separated instructions.
3. execute_form_filling - Execute the form filling process. Takes form path as input.

Workflow:
1. First use analyze_form to understand the form structure
2. Then use fill_form_fields to set the filling instructions
3. Finally use execute_form_filling to run the form filling process

Each tool should be used in sequence, with the output of one tool potentially being used as input for the next tool."""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}")
    ])
    
    # Create agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    return agent_executor