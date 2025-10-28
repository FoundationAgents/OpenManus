#!/usr/bin/env python3
"""
LangChain Auto Testing Agent Module
A testing agent that uses LangChain to orchestrate the testing process.
"""

import os
import sys
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
import json

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from dotenv import load_dotenv

# Add the common directory to sys.path to enable imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'common', 'src'))

from base_auto_testing_agent import BaseTestingAgent

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LangChainTestingAgent(BaseTestingAgent):
    """A testing agent that uses LangChain to orchestrate the auto testing process."""
    
    def generate_test_cases_with_llm(self, project_structure: Dict[str, Any]) -> List[tuple]:
        """
        Generate test cases for the loaded project using LLM.
        
        Args:
            project_structure: Project structure information
            
        Returns:
            List of (filename, test_code) tuples
            
        Raises:
            Exception: If failed to generate or parse test cases
        """
        # Initialize LLM
        llm = ChatOpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model=os.getenv("DASHSCOPE_MODEL", "qwen-plus")
        )
        
        # Format file contents for prompt
        file_contents = []
        for f in project_structure["files"]:
            with open(f["path"], 'r') as file:
                content = file.read()
                file_contents.append(f"File: {f['relative_path']}\n{content}")
        
        file_contents_str = "\n\n" + "\n\n".join(file_contents)
        
        # Create prompt for test case generation
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior Python testing expert. Based on the project structure and code information, generate comprehensive unit tests for all classes and functions.

For each Python file, generate a corresponding test file with comprehensive unit tests.
Only return the test code, nothing else. Make sure to:
1. Import the necessary modules
2. Create a test class that inherits from unittest.TestCase
3. Include tests for all public methods and functions
4. Handle edge cases and error conditions
5. Use descriptive test method names
6. Include proper assertions

I'll provide you with the project structure and the content of each Python file. Please generate tests based on the actual code, not just the structure.

The project structure information:
{file_list}

The file contents are as follows:
{file_contents}

Format your response as separate test files like this:
=== test_filename1.py ===
[content of test file 1]
=== test_filename2.py ===
[content of test file 2]
...
""")
        ])
        
        # Format file list for prompt with code structure information
        file_descriptions = []
        for f in project_structure["files"]:
            desc = f"- {f['relative_path']}"
            
            # 添加类信息
            if f['analysis']['classes']:
                desc += "\n  Classes:"
                for cls in f['analysis']['classes']:
                    desc += f"\n    - {cls['name']}"
                    if cls['methods']:
                        desc += " (methods: " + ", ".join([m['name'] for m in cls['methods']]) + ")"
            
            # 添加函数信息
            if f['analysis']['functions']:
                desc += "\n  Functions: " + ", ".join([func['name'] for func in f['analysis']['functions']])
                
            file_descriptions.append(desc)
        
        file_list_str = "\n".join(file_descriptions)
        
        
        # Generate test cases
        chain = prompt | llm
        response = chain.invoke({
            "project_root": project_structure["root"],
            "file_list": file_list_str,
            "file_contents": file_contents_str
        })
        
        # Parse the LLM response into separate test files using the base class method
        test_cases = self.parse_test_response(response.content, project_structure["files"])
        
        if not test_cases:
            raise Exception("Failed to generate test cases from LLM response")
        
        logger.info(f"Generated {len(test_cases)} test cases using LLM")
        return test_cases
    
    def _clean_code_block(self, content: str) -> str:
        """
        Clean code block markers from content.
        
        Args:
            content: Content that may contain code block markers
            
        Returns:
            Cleaned content without code block markers
        """
        lines = content.split('\n')
        cleaned_lines = []
        
        in_code_block = False
        for line in lines:
            # Check for code block start markers
            if line.strip().startswith('```') and not in_code_block:
                in_code_block = True
                # Check if it's a python code block marker
                if line.strip() in ['```python', '```Python', '```']:
                    continue
                else:
                    # It's a code block with specific language, but not python
                    # We'll still treat it as a code block start
                    continue
            
            # Check for code block end markers
            if line.strip().startswith('```') and in_code_block:
                in_code_block = False
                continue
            
            # Add line if we're in a code block or if it's not a marker
            if in_code_block or not line.strip().startswith('```'):
                cleaned_lines.append(line)
        
        # If we didn't find any code block markers, return original content
        if not in_code_block and len(cleaned_lines) == len(lines):
            return content
            
        return '\n'.join(cleaned_lines)
    
    def execute_tests_in_agent_bay(self, test_cases: List[tuple]) -> List[Dict]:
        """
        Execute test cases in the AgentBay session.
        
        Args:
            test_cases: List of (filename, test_code) tuples to execute
            
        Returns:
            List of execution results
        """
        # Upload project files first
        self.upload_project_files()
        
        # Execute each test file
        results = []
        for filename, test_code in test_cases:
            result = self.execute_test_file(filename, test_code)
            results.append(result)
        
        return results


def create_testing_tools(agent: LangChainTestingAgent) -> List[Tool]:
    """
    Create Langchain tools for the testing agent.
    
    Args:
        agent: LangChainTestingAgent instance
        
    Returns:
        List of Langchain tools
    """
    def scan_project(project_path: str) -> str:
        """Scan a project directory and return its structure."""
        try:
            print(f"Execute tool scan_project: {project_path}")
            agent.load_project(project_path)
            structure = agent.scan_project_structure()
            print("Save structure to agent._structure")
            agent._structure = structure

            # 保存项目结构到data目录
            agent_name = agent.__class__.__name__.lower()
            agent.save_data_to_file(structure, "project_structure.json", agent_name)
            
            # Format the structure as a string
            result = f"Project root: {structure['root']}\n\n"
            result += "Directories:\n"
            for directory in structure['directories']:
                result += f"  {directory['relative_path']}\n"
            
            result += "\nPython files:\n"
            for file in structure['files']:
                result += f"  {file['relative_path']}"
                # Add class information
                if file['analysis']['classes']:
                    result += "\n    Classes:"
                    for cls in file['analysis']['classes']:
                        result += f"\n      - {cls['name']}"
                        if cls['methods']:
                            result += " (methods: " + ", ".join([m['name'] for m in cls['methods']]) + ")"
                
                # Add function information
                if file['analysis']['functions']:
                    result += f"\n    Functions: " + ", ".join([func['name'] for func in file['analysis']['functions']])
            
            return result
        except Exception as e:
            return f"Error scanning project: {str(e)}"
    
    def generate_tests(project_structure_str: str) -> str:
        """Generate test cases for a project based on project structure."""
        try:
            print(f"Execute tool generate_tests")
            # In a real implementation, we would parse the project_structure_str back to dict
            # For now, we'll just re-scan the project to demonstrate the tool chaining concept
            if hasattr(agent, '_structure') and agent._structure:
                print(f"Find pre tools generated project structure in agent._structure")
                structure = agent._structure
            else:
                print(f"Can't find pre tools generated project structure, resacan the project")
                structure = agent.scan_project_structure()

            test_cases = agent.generate_test_cases_with_llm(structure)
            
            # Store test cases for later execution
            agent._generated_test_cases = test_cases
            
            # 保存测试用例到data目录
            agent_name = agent.__class__.__name__.lower()
            agent.save_data_to_file({"test_cases": [filename for filename, _ in test_cases]}, 
                                  "generated_test_cases.json", agent_name)
            
            # Also save the actual test code to files
            # Get the framework directory (langchain) and create test cases directory within its data directory
            current_file_path = os.path.dirname(os.path.abspath(__file__))
            print(f"Current file directory: {current_file_path}")

            framework_dir = os.path.dirname(current_file_path)  # Go up from src to langchain
            print(f"Framework directory: {framework_dir}")
            
            # Create data directory path in a more robust way
            test_cases_dir = Path(framework_dir) / "data" / agent_name / "test_cases"
            
            try:
                test_cases_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created test cases directory: {test_cases_dir}")
            except Exception as e:
                logger.error(f"Failed to create test cases directory: {str(e)}")
                raise
            
            for filename, test_code in test_cases:
                # Use Path for more robust path manipulation
                test_file_path = test_cases_dir / filename
                
                try:
                    # Ensure the directory exists for the test file
                    test_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write test file with proper encoding and newline handling
                    with open(test_file_path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(test_code)
                    logger.info(f"Saved test file: {test_file_path}")
                except Exception as e:
                    logger.error(f"Failed to write test file {filename}: {str(e)}")
                    raise
            
            return f"Generated {len(test_cases)} test case files:\n" + "\n".join([filename for filename, _ in test_cases])
        except Exception as e:
            return f"Error generating tests: {str(e)}"
    
    def execute_tests(test_files_info: str) -> str:
        """Execute tests in AgentBay."""
        try:
            print(f"Execute tool execute_tests: {test_files_info}")
            # Use stored test cases if available, otherwise regenerate
            if hasattr(agent, '_generated_test_cases') and agent._generated_test_cases:
                print(f"Find pre tools generated project test cases in agent._generated_test_cases")
                test_cases = agent._generated_test_cases
            else:
                # Fallback: regenerate tests
                print(f"Can't find pre tools generated project test cases, regenerating tests...")
                structure = agent.scan_project_structure()
                test_cases = agent.generate_test_cases_with_llm(structure)
            
            results = agent.execute_tests_in_agent_bay(test_cases)
            
            # 保存执行结果到data目录
            agent_name = agent.__class__.__name__.lower()
            agent.save_data_to_file(results, "test_execution_results.json", agent_name)
            
            # Format results
            passed = sum(1 for r in results if r['success'])
            total = len(results)
            
            summary = f"Executed {total} tests. {passed} passed, {total - passed} failed.\n\n"
            for result in results:
                summary += f"Test file: {result['test_file']}\n"
                summary += f"Status: {'PASS' if result['success'] else 'FAIL'}\n"
                if result['success']:
                    summary += f"Output:\n{result['result']}\n"
                else:
                    summary += f"Error:\n{result['error']}\n"
                summary += "-" * 40 + "\n"
                
            return summary
        except Exception as e:
            return f"Error executing tests: {str(e)}"
    
    return [
        Tool(
            name="scan_project",
            func=scan_project,
            description="Scan a project directory and return its detailed structure. Input should be the path to the project directory."
        ),
        Tool(
            name="generate_tests",
            func=generate_tests,
            description="Generate test cases for a project based on the project structure. Input should be the project structure string from scan_project."
        ),
        Tool(
            name="execute_tests",
            func=execute_tests,
            description="Execute tests in AgentBay. Input should be information about test files to execute."
        )
    ]


def create_langchain_agent(api_key: Optional[str] = None) -> AgentExecutor:
    """
    Create a Langchain agent for testing.
    
    Args:
        api_key: AgentBay API key
        
    Returns:
        Langchain AgentExecutor
    """
    # Create testing agent
    testing_agent = LangChainTestingAgent(api_key=api_key)
    
    # Create tools
    tools = create_testing_tools(testing_agent)
    
    # Initialize LLM
    llm = ChatOpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model=os.getenv("DASHSCOPE_MODEL", "qwen-plus")
    )
    
    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a testing expert that helps generate and execute tests for Python projects.
        
Available tools:
1. scan_project - Scan a project directory and return its structure. Takes project path as input.
2. generate_tests - Generate test cases for a project. Takes project structure as input.
3. execute_tests - Execute tests in AgentBay. Takes test information as input.

Workflow:
1. First use scan_project to understand the project structure
2. Then use generate_tests to create test cases based on the structure
3. Finally use execute_tests to run the tests in AgentBay

Each tool should be used in sequence, with the output of one tool potentially being used as input for the next tool."""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}")
    ])
    
    # Create agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    return agent_executor