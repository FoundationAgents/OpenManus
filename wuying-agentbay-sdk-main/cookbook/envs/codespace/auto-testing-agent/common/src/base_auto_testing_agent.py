#!/usr/bin/env python3
"""
Base Auto Testing Agent Module
Contains shared functionality for both LangChain and direct implementations.
"""

import os
import logging
import ast
from typing import List, Dict, Optional, Any
from pathlib import Path
import json

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CodeAnalyzer(ast.NodeVisitor):
    """Analyze Python code to extract classes, functions and methods."""
    
    def __init__(self):
        self.classes = []
        self.functions = []
        self.current_class = None
    
    def visit_ClassDef(self, node):
        """Visit class definitions."""
        class_info = {
            'name': node.name,
            'docstring': ast.get_docstring(node),
            'methods': []
        }
        
        # Keep track of current class for method association
        self.current_class = class_info
        self.classes.append(class_info)
        
        # Visit child nodes to find methods
        self.generic_visit(node)
        
        # Reset current class
        self.current_class = None
    
    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        function_info = {
            'name': node.name,
            'docstring': ast.get_docstring(node),
            'args': [arg.arg for arg in node.args.args]
        }
        
        if self.current_class:
            # This is a method
            self.current_class['methods'].append(function_info)
        else:
            # This is a standalone function
            self.functions.append(function_info)
        
        self.generic_visit(node)


class BaseTestingAgent:
    """Base class for testing agents with shared functionality."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the base testing agent.
        
        Args:
            api_key: AgentBay API key. If not provided, it will be read from AGENTBAY_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv("AGENTBAY_API_KEY")
        if not self.api_key:
            raise ValueError("AGENTBAY_API_KEY environment variable must be set or api_key must be provided")
        
        self.agent_bay = AgentBay(api_key=self.api_key)
        self.session = None
        self.project_path = None
    
    def load_project(self, project_path: str):
        """
        Load a project for testing.
        
        Args:
            project_path: Path to the project directory to test
        """
        if not os.path.exists(project_path):
            raise FileNotFoundError(f"Project path does not exist: {project_path}")
        
        self.project_path = os.path.abspath(project_path)
        logger.info(f"Loaded project from {self.project_path}")
    
    def analyze_python_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a Python file and extract classes, functions and methods.
        
        Args:
            file_path: Path to the Python file to analyze
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code)
            analyzer = CodeAnalyzer()
            analyzer.visit(tree)
            
            return {
                'classes': analyzer.classes,
                'functions': analyzer.functions
            }
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return {
                'classes': [],
                'functions': []
            }
    
    def scan_project_structure(self) -> Dict[str, Any]:
        """
        Scan the project directory to identify Python files that need testing.
        
        Returns:
            Dictionary containing project structure information
        """
        print("Scanning project structure...")
        if not self.project_path:
            raise ValueError("No project loaded. Please load a project first.")
        
        project_structure = {
            "root": self.project_path,
            "files": [],
            "directories": []
        }
        
        for root, dirs, files in os.walk(self.project_path):
            # Skip hidden directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.endswith('.py') and not file.startswith('.'):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, self.project_path)
                    
                    # Analyze Python file structure
                    analysis = self.analyze_python_file(full_path)
                    
                    project_structure["files"].append({
                        "name": file,
                        "path": full_path,
                        "relative_path": relative_path,
                        "analysis": analysis
                    })
            
            for directory in dirs:
                full_path = os.path.join(root, directory)
                relative_path = os.path.relpath(full_path, self.project_path)
                project_structure["directories"].append({
                    "name": directory,
                    "path": full_path,
                    "relative_path": relative_path
                })
        
        logger.info(f"Scanned project structure: {len(project_structure['files'])} Python files found")
        
        return project_structure
    
    def create_session(self):
        """Create an AgentBay session with the project files."""
        # Create session parameters without context sync
        params = CreateSessionParams(image_id="code_latest")
        
        # Create session
        session_result = self.agent_bay.create(params)
        if session_result.success:
            self.session = session_result.session
            logger.info(f"Session created with ID: {self.session.session_id}")
        else:
            raise Exception(f"Failed to create session: {session_result.error_message}")
    
    def save_results(self, results: List[Dict], output_file: str = "test_results.log"):
        """
        Save test results to a local log file.
        
        Args:
            results: List of test execution results
            output_file: Path to the output log file
        """
        with open(output_file, 'w') as f:
            f.write("Test Execution Results\n")
            f.write("=" * 50 + "\n\n")
            
            for result in results:
                f.write(f"Test File: {result['test_file']}\n")
                f.write(f"  Success: {result['success']}\n")
                if result['success']:
                    f.write(f"  Result:\n{result['result']}\n")
                else:
                    f.write(f"  Error: {result['error']}\n")
                f.write("\n" + "-" * 30 + "\n\n")
        
        logger.info(f"Results saved to {output_file}")
    
    def upload_project_files(self):
        """
        Upload all project Python files to the AgentBay session.
        """
        if not self.session:
            self.create_session()
        
        # Keep track of uploaded files to avoid duplicates
        uploaded_files = set()
        
        # Upload all project Python files that might be needed for testing
        project_files = self.scan_project_structure()
        for file_info in project_files["files"]:
            file_name = file_info["name"]
            file_path = file_info["path"]
            relative_path = file_info["relative_path"]
            
            # Upload Python files (except test files which will be uploaded separately)
            if file_name.endswith('.py') and not file_name.startswith('test_'):
                with open(file_path, "r") as f:
                    file_content = f.read()
                
                # Write file to the same relative path in the AgentBay environment
                # This ensures that the test files can import the modules using the same structure
                output_path = "/tmp/" + relative_path
                write_result = self.session.file_system.write_file(output_path, file_content)
                if write_result.success:
                    uploaded_files.add(relative_path)
                    logger.info(f"Uploaded {relative_path} to AgentBay environment at {relative_path}")
                else:
                    logger.error(f"Failed to write {relative_path}: {write_result.error_message}")
        
        return uploaded_files
    
    def execute_test_file(self, filename: str, test_code: str) -> Dict:
        """
        Execute a single test file in the AgentBay session.
        
        Args:
            filename: Name of the test file
            test_code: Content of the test file
            
        Returns:
            Dictionary with execution results
        """
        if not self.session:
            self.create_session()
            
        logger.info(f"Executing test case {filename}")
        
        # Write test file to session
        test_file_output_path = "/tmp/" + filename
        write_result = self.session.file_system.write_file(test_file_output_path, test_code)
        
        if not write_result.success:
            logger.error(f"Failed to write test file {filename}: {write_result.error_message}")
            return {
                "test_file": filename,
                "success": False,
                "error": f"Failed to write test file: {write_result.error_message}"
            }
        
        # Execute test
        # Directly execute the test file as Python code
        execution_result = self.session.command.execute_command(f"python3 {test_file_output_path}")
        
        # 记录详细的执行输出
        if execution_result.success:
            logger.info(f"Test case {filename} execution succeeded with output:\n{execution_result.output}")
        else:
            logger.error(f"Test case {filename} execution failed with error:\n{execution_result.error_message}")
        
        return {
            "test_file": filename,
            "success": execution_result.success,
            "result": execution_result.output,
            "error": execution_result.error_message
        }
    
    def parse_test_response(self, response_content: str, project_files: List[Dict]) -> List[tuple]:
        """
        Parse the LLM response into separate test files.
        
        Args:
            response_content: The raw response from the LLM
            project_files: List of project files information
            
        Returns:
            List of (filename, test_code) tuples
        """
        test_cases = []
        
        # Look for test files in the response
        lines = response_content.split('\n')
        current_filename = None
        current_content = []
        
        for line in lines:
            # Check if this line indicates a new test file
            if line.startswith('===') and line.endswith('==='):
                # Save previous test file if exists
                if current_filename and current_content:
                    # Remove extra whitespace and newlines at the beginning and end
                    content = '\n'.join(current_content).strip()
                    if content:
                        # Clean code block markers if present
                        content = self.clean_code_block(content)
                        test_cases.append((current_filename, content))
                
                # Start new test file
                current_filename = line.strip('=').strip()
                current_content = []
            elif current_filename:
                # Add line to current test file content
                current_content.append(line)
        
        # Don't forget the last test file
        if current_filename and current_content:
            content = '\n'.join(current_content).strip()
            if content:
                # Clean code block markers if present
                content = self.clean_code_block(content)
                test_cases.append((current_filename, content))
        
        return test_cases
    
    def clean_code_block(self, content: str) -> str:
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
    
    def save_data_to_file(self, data: Any, filename: str, subdir: str = None):
        """
        Save data to a file in the data directory.
        
        Args:
            data: Data to save (will be JSON serialized)
            filename: Name of the file to save
            subdir: Subdirectory within the data directory (optional)
        """
        # Create data directory path within the specific framework directory
        # Get the path of this file (base_testing_agent.py)
        current_file_path = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to common directory, then to the parent of common (testing-agent)
        testing_agent_dir = os.path.dirname(os.path.dirname(current_file_path))
        
        # Determine which framework is calling this method by checking the call stack
        # This allows us to save data in the correct framework's data directory
        import inspect
        frame = inspect.currentframe()
        try:
            # Go back in the call stack to find the calling file
            caller_frame = frame.f_back
            while caller_frame:
                caller_file = caller_frame.f_code.co_filename
                if 'langchain' in caller_file:
                    # Caller is from langchain framework
                    framework_dir = os.path.join(testing_agent_dir, "langchain")
                    break
                # Add other frameworks here as needed
                # elif 'crewai' in caller_file:
                #     framework_dir = os.path.join(testing_agent_dir, "crewai")
                #     break
                # elif 'autogen' in caller_file:
                #     framework_dir = os.path.join(testing_agent_dir, "autogen")
                #     break
                else:
                    caller_frame = caller_frame.f_back
            else:
                # Default to langchain if we can't determine the framework
                framework_dir = os.path.join(testing_agent_dir, "langchain")
        finally:
            del frame
        
        # Create path to data directory within the framework directory
        if subdir:
            data_dir = os.path.join(framework_dir, "data", subdir)
        else:
            data_dir = os.path.join(framework_dir, "data")
            
        os.makedirs(data_dir, exist_ok=True)
        
        # Save data to file
        file_path = os.path.join(data_dir, filename)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved data to {file_path}")