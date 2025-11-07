"""
Enhanced ADE (Agentic Development Environment) flow for complex software development tasks.
Replaces complete human teams with autonomous agent coordination.
"""

import json
import time
from enum import Enum
from typing import Dict, List, Optional, Any

try:
    from pydantic import Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Create dummy Field decorator
    def Field(default=None, **kwargs):
        return default

from app.agent.base import BaseAgent
from app.agent.swe_agent import SWEAgent
from app.flow.base import BaseFlow
from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Message, ToolChoice
from app.local_service import local_service


class TaskType(str, Enum):
    """Types of development tasks."""
    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    ARCHITECTURE_DESIGN = "architecture_design"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DEBUGGING = "debugging"
    DEPLOYMENT = "deployment"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    SECURITY_AUDIT = "security_audit"


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DevelopmentTask:
    """Represents a development task in the ADE."""
    
    def __init__(
        self,
        task_id: str,
        task_type: TaskType,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        dependencies: List[str] = None,
        assignee: Optional[str] = None,
        status: str = "pending",
        created_at: Optional[float] = None
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.description = description
        self.priority = priority
        self.dependencies = dependencies or []
        self.assignee = assignee
        self.status = status
        self.created_at = created_at or time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.result: Optional[str] = None
        self.error: Optional[str] = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "description": self.description,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "assignee": self.assignee,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error
        }


class ADEFlow(BaseFlow):
    """Advanced Agentic Development Environment flow."""
    
    llm: LLM = Field(default_factory=lambda: LLM())
    tasks: Dict[str, DevelopmentTask] = Field(default_factory=dict)
    task_queue: List[str] = Field(default_factory=list)
    completed_tasks: List[str] = Field(default_factory=list)
    current_task: Optional[str] = Field(None)
    project_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Specialized agents
    swe_agent: SWEAgent = Field(default_factory=SWEAgent)
    
    def __init__(self, agents: Dict[str, BaseAgent], **data):
        super().__init__(agents, **data)
        self.project_context["workspace_root"] = str(local_service.workspace_dir)
        self.project_context["start_time"] = time.time()
        
    async def execute(self, input_text: str) -> str:
        """Execute the ADE flow for complex development tasks."""
        try:
            logger.info("Starting ADE execution")
            
            # Phase 1: Task Planning and Analysis
            await self.phase_planning_and_analysis(input_text)
            
            # Phase 2: Task Execution
            await self.phase_task_execution()
            
            # Phase 3: Integration and Testing
            await self.phase_integration_and_testing()
            
            # Phase 4: Documentation and Deployment
            await self.phase_documentation_and_deployment()
            
            # Generate final report
            return await self.generate_final_report()
            
        except Exception as e:
            logger.error(f"ADE execution failed: {e}")
            return f"ADE execution failed: {str(e)}"
            
    async def phase_planning_and_analysis(self, input_text: str):
        """Phase 1: Analyze requirements and create task plan."""
        logger.info("Phase 1: Planning and Analysis")
        
        # Analyze the request and break down into tasks
        planning_prompt = f"""
        Analyze the following development request and break it down into specific, actionable tasks:
        
        Request: {input_text}
        
        Create a comprehensive task plan including:
        1. Requirements analysis
        2. Architecture design
        3. Implementation tasks
        4. Testing requirements
        5. Documentation needs
        6. Deployment considerations
        
        For each task, specify:
        - Task type (requirements_analysis, architecture_design, implementation, testing, etc.)
        - Priority (low, medium, high, critical)
        - Dependencies on other tasks
        - Estimated complexity
        - Required skills/tools
        
        Format as JSON array of task objects.
        """
        
        try:
            response = await self.llm.ask([{"role": "user", "content": planning_prompt}])
            task_data = json.loads(response)
            
            # Create tasks from analysis
            for i, task_info in enumerate(task_data):
                task_id = f"task_{i+1:03d}"
                task = DevelopmentTask(
                    task_id=task_id,
                    task_type=TaskType(task_info.get("task_type", "implementation")),
                    description=task_info.get("description", ""),
                    priority=TaskPriority(task_info.get("priority", "medium")),
                    dependencies=task_info.get("dependencies", [])
                )
                self.tasks[task_id] = task
                self.task_queue.append(task_id)
                
            logger.info(f"Created {len(self.tasks)} tasks for execution")
            
        except Exception as e:
            logger.error(f"Task planning failed: {e}")
            # Fallback: create a single implementation task
            task = DevelopmentTask(
                task_id="task_001",
                task_type=TaskType.IMPLEMENTATION,
                description=input_text,
                priority=TaskPriority.HIGH
            )
            self.tasks[task.id] = task
            self.task_queue.append(task.task_id)
            
    async def phase_task_execution(self):
        """Phase 2: Execute all tasks in dependency order."""
        logger.info("Phase 2: Task Execution")
        
        while self.task_queue:
            # Find tasks that can be executed (dependencies satisfied)
            executable_tasks = []
            for task_id in self.task_queue:
                task = self.tasks[task_id]
                if all(dep in self.completed_tasks for dep in task.dependencies):
                    executable_tasks.append(task_id)
                    
            if not executable_tasks:
                logger.warning("No executable tasks found - checking for circular dependencies")
                break
                
            # Execute tasks in priority order
            for task_id in executable_tasks:
                task = self.tasks[task_id]
                self.current_task = task_id
                
                try:
                    logger.info(f"Executing task {task_id}: {task.description}")
                    task.status = "in_progress"
                    task.started_at = time.time()
                    
                    # Execute task based on type
                    if task.task_type == TaskType.IMPLEMENTATION:
                        result = await self.execute_implementation_task(task)
                    elif task.task_type == TaskType.TESTING:
                        result = await self.execute_testing_task(task)
                    elif task.task_type == TaskType.DEBUGGING:
                        result = await self.execute_debugging_task(task)
                    elif task.task_type == TaskType.REFACTORING:
                        result = await self.execute_refactoring_task(task)
                    elif task.task_type == TaskType.DOCUMENTATION:
                        result = await self.execute_documentation_task(task)
                    elif task.task_type == TaskType.ARCHITECTURE_DESIGN:
                        result = await self.execute_architecture_task(task)
                    elif task.task_type == TaskType.REQUIREMENTS_ANALYSIS:
                        result = await self.execute_requirements_task(task)
                    else:
                        result = await self.execute_general_task(task)
                        
                    task.result = result
                    task.status = "completed"
                    task.completed_at = time.time()
                    self.completed_tasks.append(task_id)
                    self.task_queue.remove(task_id)
                    
                    logger.info(f"Task {task_id} completed successfully")
                    
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {e}")
                    task.error = str(e)
                    task.status = "failed"
                    self.task_queue.remove(task_id)
                    
            self.current_task = None
            
    async def execute_implementation_task(self, task: DevelopmentTask) -> str:
        """Execute implementation task using SWE agent."""
        prompt = f"""
        Implement the following feature/task:
        
        Task: {task.description}
        
        Context:
        - This is part of a larger development project
        - Follow best practices and coding standards
        - Include proper error handling
        - Write clean, maintainable code
        - Consider performance and security implications
        
        Please implement the solution and provide:
        1. Explanation of the approach
        2. Code implementation
        3. Any files created or modified
        4. Testing considerations
        """
        
        return await self.swe_agent.run(prompt)
        
    async def execute_testing_task(self, task: DevelopmentTask) -> str:
        """Execute testing task."""
        prompt = f"""
        Create comprehensive tests for the following:
        
        Testing Task: {task.description}
        
        Please provide:
        1. Test plan and strategy
        2. Unit tests for all components
        3. Integration tests where applicable
        4. Edge case and error handling tests
        5. Performance tests if relevant
        6. Test execution results
        
        Focus on test coverage, reliability, and maintainability.
        """
        
        return await self.swe_agent.run(prompt)
        
    async def execute_debugging_task(self, task: DevelopmentTask) -> str:
        """Execute debugging task."""
        prompt = f"""
        Debug and fix the following issue:
        
        Debugging Task: {task.description}
        
        Please provide:
        1. Problem analysis and root cause identification
        2. Step-by-step debugging process
        3. Solution implementation
        4. Verification that the fix works
        5. Prevention measures for similar issues
        
        Be thorough in your analysis and provide clear explanations.
        """
        
        return await self.swe_agent.run(prompt)
        
    async def execute_refactoring_task(self, task: DevelopmentTask) -> str:
        """Execute refactoring task."""
        prompt = f"""
        Refactor the code according to the following requirements:
        
        Refactoring Task: {task.description}
        
        Please provide:
        1. Analysis of current code issues
        2. Refactoring plan and strategy
        3. Improved code implementation
        4. Explanation of improvements made
        5. Verification that functionality is preserved
        
        Focus on improving code quality, maintainability, and performance.
        """
        
        return await self.swe_agent.run(prompt)
        
    async def execute_documentation_task(self, task: DevelopmentTask) -> str:
        """Execute documentation task."""
        prompt = f"""
        Create comprehensive documentation for:
        
        Documentation Task: {task.description}
        
        Please provide:
        1. Clear and concise documentation
        2. Code examples where applicable
        3. API documentation if relevant
        4. Setup and usage instructions
        5. Architectural overview if needed
        
        Documentation should be user-friendly and technically accurate.
        """
        
        return await self.swe_agent.run(prompt)
        
    async def execute_architecture_task(self, task: DevelopmentTask) -> str:
        """Execute architecture design task."""
        prompt = f"""
        Design architecture for the following:
        
        Architecture Task: {task.description}
        
        Please provide:
        1. System architecture overview
        2. Component design and interactions
        3. Data flow diagrams
        4. Technology stack recommendations
        5. Scalability and performance considerations
        6. Security considerations
        7. Deployment architecture
        
        Consider best practices, scalability, maintainability, and security.
        """
        
        return await self.swe_agent.run(prompt)
        
    async def execute_requirements_task(self, task: DevelopmentTask) -> str:
        """Execute requirements analysis task."""
        prompt = f"""
        Analyze requirements for the following:
        
        Requirements Task: {task.description}
        
        Please provide:
        1. Functional requirements analysis
        2. Non-functional requirements identification
        3. User stories and use cases
        4. Acceptance criteria
        5. Technical constraints and considerations
        6. Risk assessment
        7. Implementation recommendations
        
        Be thorough and consider all aspects of the requirements.
        """
        
        return await self.swe_agent.run(prompt)
        
    async def execute_general_task(self, task: DevelopmentTask) -> str:
        """Execute general development task."""
        prompt = f"""
        Complete the following development task:
        
        Task: {task.description}
        
        Please provide:
        1. Analysis of the requirements
        2. Implementation approach
        3. Code or solution provided
        4. Testing performed
        5. Documentation if needed
        
        Ensure high quality and follow best practices.
        """
        
        return await self.swe_agent.run(prompt)
        
    async def phase_integration_and_testing(self):
        """Phase 3: Integration testing and validation."""
        logger.info("Phase 3: Integration and Testing")
        
        # Analyze all completed tasks
        integration_prompt = f"""
        Review and integrate the results of all completed tasks:
        
        Completed Tasks: {len(self.completed_tasks)}
        Task Results: {[task.to_dict() for task_id, task in self.tasks.items() if task_id in self.completed_tasks]}
        
        Please provide:
        1. Integration analysis
        2. Compatibility checks between components
        3. End-to-end testing strategy
        4. Quality assurance validation
        5. Performance validation
        6. Security validation
        
        Identify any issues that need to be addressed and provide solutions.
        """
        
        try:
            integration_result = await self.llm.ask([{"role": "user", "content": integration_prompt}])
            self.project_context["integration_result"] = integration_result
            logger.info("Integration analysis completed")
        except Exception as e:
            logger.error(f"Integration phase failed: {e}")
            
    async def phase_documentation_and_deployment(self):
        """Phase 4: Final documentation and deployment preparation."""
        logger.info("Phase 4: Documentation and Deployment")
        
        # Generate comprehensive project documentation
        doc_prompt = f"""
        Generate comprehensive project documentation based on all completed work:
        
        Project Context: {self.project_context}
        Completed Tasks: {len(self.completed_tasks)}
        
        Please provide:
        1. Project overview and summary
        2. Architecture documentation
        3. API documentation (if applicable)
        4. Setup and installation instructions
        5. Usage examples
        6. Testing documentation
        7. Deployment guide
        8. Maintenance instructions
        
        Documentation should be complete and production-ready.
        """
        
        try:
            documentation_result = await self.llm.ask([{"role": "user", "content": doc_prompt}])
            self.project_context["documentation"] = documentation_result
            logger.info("Documentation generation completed")
        except Exception as e:
            logger.error(f"Documentation phase failed: {e}")
            
    async def generate_final_report(self) -> str:
        """Generate final execution report."""
        execution_time = time.time() - self.project_context["start_time"]
        
        report = f"""
# ADE Execution Report

## Summary
- **Total Tasks**: {len(self.tasks)}
- **Completed Tasks**: {len(self.completed_tasks)}
- **Failed Tasks**: {len([t for t in self.tasks.values() if t.status == "failed"])}
- **Execution Time**: {execution_time:.2f} seconds

## Task Details
"""
        
        for task in self.tasks.values():
            status_icon = "✅" if task.status == "completed" else "❌" if task.status == "failed" else "⏳"
            report += f"""
### {task.task_id} - {task.task_type.value} {status_icon}
- **Description**: {task.description}
- **Priority**: {task.priority.value}
- **Status**: {task.status}
- **Assignee**: {task.assignee or "Auto-assigned"}
"""
            if task.result:
                report += f"- **Result**: {task.result[:200]}...\n"
            if task.error:
                report += f"- **Error**: {task.error}\n"
                
        report += f"""
## Integration Results
{self.project_context.get('integration_result', 'No integration analysis performed')}

## Documentation
{self.project_context.get('documentation', 'No documentation generated')}

## Files Modified/Created
"""
        
        # List files in workspace
        try:
            files = local_service.list_files(".")
            for file_path in files[:20]:  # Limit to first 20 files
                report += f"- {file_path}\n"
            if len(files) > 20:
                report += f"... and {len(files) - 20} more files\n"
        except Exception as e:
            report += f"Error listing files: {e}\n"
            
        report += f"""
## Next Steps
1. Review all implemented changes
2. Run comprehensive testing
3. Deploy to staging environment
4. Monitor performance and security
5. Gather user feedback

## ADE Execution Complete
This autonomous development task has been completed by the Agentic Development Environment.
The system has successfully replaced traditional human development teams with coordinated AI agents.
"""
        
        return report