"""
Specialized Agent Implementations for Multi-Agent Environment
Each agent has specific capabilities and domain expertise
"""

import json
import time
from typing import Dict, List, Optional, Any
from app.flow.multi_agent_environment import SpecializedAgent, DevelopmentTask, AgentRole
from app.llm import LLM
from app.logger import logger


class ArchitectAgent(SpecializedAgent):
    """Software Architecture Specialist"""
    
    def __init__(self, agent_id: str, blackboard, **kwargs):
        super().__init__(AgentRole.ARCHITECT, blackboard, name=agent_id, **kwargs)
        self.architecture_patterns = [
            "Microservices", "Event-Driven", "Layered", "Hexagonal", 
            "Clean Architecture", "Serverless", "Monolith", "Hybrid"
        ]
        self.design_principles = [
            "SOLID", "DRY", "KISS", "YAGNI", "Separation of Concerns",
            "Single Responsibility", "Open/Closed", "Liskov Substitution"
        ]
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute architecture-specific tasks"""
        self.add_thought(f"Designing architecture for: {task.description}")
        
        # Collaborate with product manager for requirements
        requirements = await self.collaborate(AgentRole.PRODUCT_MANAGER, 
            "What are the key functional and non-functional requirements?")
        
        # Collaborate with security for security considerations
        security_reqs = await self.collaborate(AgentRole.SECURITY,
            "What security considerations should be incorporated?")
        
        # Design architecture
        architecture_prompt = f"""
        Design a comprehensive system architecture for the following:
        
        Project Description: {task.description}
        Requirements: {requirements}
        Security Considerations: {security_reqs}
        
        Provide:
        1. High-level architecture overview
        2. Component design and interactions
        3. Data flow and persistence strategy
        4. Technology stack recommendations
        5. Scalability and performance considerations
        6. Security architecture
        7. Deployment and infrastructure design
        8. Risk assessment and mitigation strategies
        
        Consider modern best practices and industry standards.
        """
        
        response = await self.llm.ask([{"role": "user", "content": architecture_prompt}])
        
        # Parse and structure the architecture
        architecture_design = self._parse_architecture_response(response)
        
        # Share architecture with development team
        self.blackboard.post_message(self._create_message(
            "architecture_design", 
            architecture_design,
            metadata={"type": "architecture", "task_id": task.id}
        ))
        
        return f"Architecture designed and shared with team: {len(architecture_design.get('components', []))} components"
    
    async def _answer_question(self, question: str) -> str:
        """Answer architecture-related questions"""
        answer_prompt = f"""
        As a Software Architect, answer this question: {question}
        
        Provide a comprehensive, well-structured answer considering:
        - Architectural principles and patterns
        - Best practices and trade-offs
        - Scalability and maintainability
        - Technical feasibility
        """
        
        response = await self.llm.ask([{"role": "user", "content": answer_prompt}])
        return response
    
    def _parse_architecture_response(self, response: str) -> Dict[str, Any]:
        """Parse architecture design response"""
        return {
            "design": response,
            "components": self._extract_components(response),
            "patterns": self._extract_patterns(response),
            "technologies": self._extract_technologies(response),
            "timestamp": time.time()
        }
    
    def _extract_components(self, text: str) -> List[str]:
        """Extract component names from architecture text"""
        # Simple extraction - could be enhanced with NLP
        components = []
        lines = text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['component', 'service', 'module']):
                components.append(line.strip())
        return components[:10]  # Limit to top 10
    
    def _extract_patterns(self, text: str) -> List[str]:
        """Extract architecture patterns from text"""
        patterns = []
        for pattern in self.architecture_patterns:
            if pattern.lower() in text.lower():
                patterns.append(pattern)
        return patterns
    
    def _extract_technologies(self, text: str) -> List[str]:
        """Extract technology stack from text"""
        tech_keywords = ['react', 'vue', 'angular', 'node', 'python', 'java', 'docker', 'kubernetes', 
                        'aws', 'azure', 'gcp', 'postgresql', 'mongodb', 'redis', 'nginx']
        technologies = []
        for tech in tech_keywords:
            if tech.lower() in text.lower():
                technologies.append(tech)
        return technologies
    
    def _create_message(self, msg_type: str, content: Any, metadata: Dict[str, Any] = None):
        """Create a blackboard message"""
        from app.flow.multi_agent_environment import BlackboardMessage, MessageType
        return BlackboardMessage(
            id=f"arch_{self.name}_{int(time.time())}",
            type=MessageType.RESULT,
            sender=self.name,
            recipient=None,
            content=content,
            metadata=metadata or {}
        )


class DeveloperAgent(SpecializedAgent):
    """Senior Software Developer"""
    
    def __init__(self, agent_id: str, blackboard, **kwargs):
        super().__init__(AgentRole.DEVELOPER, blackboard, name=agent_id, **kwargs)
        self.programming_languages = ['Python', 'JavaScript', 'TypeScript', 'Java', 'Go', 'Rust']
        self.frameworks = ['React', 'Vue', 'Angular', 'Django', 'Flask', 'FastAPI', 'Express']
        self.code_quality_metrics = ['complexity', 'coverage', 'maintainability', 'performance']
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute development tasks"""
        self.add_thought(f"Implementing: {task.title}")
        
        # Get architecture design if available
        architecture = await self._get_architecture_context()
        
        # Get security requirements
        security_reqs = await self.collaborate(AgentRole.SECURITY,
            "What security measures should I implement in this feature?")
        
        # Implementation prompt
        impl_prompt = f"""
        Implement the following feature following best practices:
        
        Task: {task.description}
        Architecture Context: {architecture}
        Security Requirements: {security_reqs}
        
        Provide:
        1. Detailed implementation plan
        2. Code implementation with proper error handling
        3. Unit tests
        4. Integration considerations
        5. Performance optimizations
        6. Security implementations
        
        Follow clean code principles and include comprehensive documentation.
        """
        
        response = await self.llm.ask([{"role": "user", "content": impl_prompt}])
        
        # Parse implementation
        implementation = self._parse_implementation_response(response)
        
        # Request code review
        review_request = f"Please review this implementation for: {task.title}\n{response}"
        review = await self.collaborate(AgentRole.CODE_REVIEWER, review_request)
        
        # Share implementation
        self.blackboard.post_message(self._create_message(
            "implementation",
            {
                "code": implementation['code'],
                "tests": implementation['tests'],
                "documentation": implementation['documentation'],
                "review": review
            },
            metadata={"type": "implementation", "task_id": task.id}
        ))
        
        return f"Implementation completed for: {task.title}"
    
    async def _answer_question(self, question: str) -> str:
        """Answer development-related questions"""
        answer_prompt = f"""
        As a Senior Software Developer, answer this technical question: {question}
        
        Provide:
        - Clear technical explanation
        - Code examples if applicable
        - Best practices
        - Potential pitfalls and how to avoid them
        - Alternative approaches
        """
        
        response = await self.llm.ask([{"role": "user", "content": answer_prompt}])
        return response
    
    async def _get_architecture_context(self) -> str:
        """Get architecture context from blackboard"""
        messages = self.blackboard.get_messages(self.name, since=time.time() - 3600)
        for msg in reversed(messages):
            if msg.metadata.get("type") == "architecture":
                return str(msg.content)
        return "No specific architecture context available"
    
    def _parse_implementation_response(self, response: str) -> Dict[str, Any]:
        """Parse implementation response"""
        return {
            "code": self._extract_code_blocks(response),
            "tests": self._extract_test_code(response),
            "documentation": self._extract_documentation(response),
            "timestamp": time.time()
        }
    
    def _extract_code_blocks(self, text: str) -> List[str]:
        """Extract code blocks from response"""
        import re
        code_blocks = re.findall(r'```[\w]*\n(.*?)\n```', text, re.DOTALL)
        return code_blocks
    
    def _extract_test_code(self, text: str) -> List[str]:
        """Extract test code from response"""
        test_blocks = []
        for block in self._extract_code_blocks(text):
            if any(keyword in block.lower() for keyword in ['test', 'spec', 'describe', 'it(']):
                test_blocks.append(block)
        return test_blocks
    
    def _extract_documentation(self, text: str) -> str:
        """Extract documentation from response"""
        lines = text.split('\n')
        doc_lines = []
        in_doc = False
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ['documentation', 'readme', 'api doc']):
                in_doc = True
            if in_doc and line.strip():
                doc_lines.append(line)
            if in_doc and line.startswith('```'):
                break
                
        return '\n'.join(doc_lines)
    
    def _create_message(self, msg_type: str, content: Any, metadata: Dict[str, Any] = None):
        """Create a blackboard message"""
        from app.flow.multi_agent_environment import BlackboardMessage, MessageType
        return BlackboardMessage(
            id=f"dev_{self.name}_{int(time.time())}",
            type=MessageType.RESULT,
            sender=self.name,
            recipient=None,
            content=content,
            metadata=metadata or {}
        )


class TesterAgent(SpecializedAgent):
    """Quality Assurance and Testing Specialist"""
    
    def __init__(self, agent_id: str, blackboard, **kwargs):
        super().__init__(AgentRole.TESTER, blackboard, name=agent_id, **kwargs)
        self.testing_types = ['unit', 'integration', 'e2e', 'performance', 'security', 'usability']
        self.test_frameworks = ['pytest', 'jest', 'cypress', 'jmeter', 'selenium']
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute testing tasks"""
        self.add_thought(f"Designing tests for: {task.title}")
        
        # Get implementation details
        implementations = await self._get_implementations()
        
        # Get performance requirements
        perf_reqs = await self.collaborate(AgentRole.PERFORMANCE,
            "What are the performance requirements and benchmarks?")
        
        # Testing strategy prompt
        test_prompt = f"""
        Design comprehensive testing strategy for:
        
        Feature: {task.description}
        Implementations: {implementations}
        Performance Requirements: {perf_reqs}
        
        Provide:
        1. Test strategy and plan
        2. Unit test cases with expected outcomes
        3. Integration test scenarios
        4. End-to-end test cases
        5. Performance test plan
        6. Security test cases
        7. Test data requirements
        8. Automation recommendations
        9. Test execution results and coverage report
        
        Focus on edge cases, error scenarios, and user experience.
        """
        
        response = await self.llm.ask([{"role": "user", "content": test_prompt}])
        
        # Execute tests (simulated)
        test_results = await self._execute_tests(response)
        
        # Share test results
        self.blackboard.post_message(self._create_message(
            "test_results",
            {
                "strategy": response,
                "results": test_results,
                "coverage": test_results.get('coverage', 85),
                "passed": test_results.get('passed', 0),
                "failed": test_results.get('failed', 0)
            },
            metadata={"type": "testing", "task_id": task.id}
        ))
        
        return f"Testing completed: {test_results.get('passed', 0)} passed, {test_results.get('failed', 0)} failed"
    
    async def _answer_question(self, question: str) -> str:
        """Answer testing-related questions"""
        answer_prompt = f"""
        As a QA Engineer, answer this testing question: {question}
        
        Provide:
        - Testing best practices
        - Test design strategies
        - Automation recommendations
        - Quality assurance processes
        - Risk assessment
        """
        
        response = await self.llm.ask([{"role": "user", "content": answer_prompt}])
        return response
    
    async def _get_implementations(self) -> str:
        """Get implementation details from blackboard"""
        messages = self.blackboard.get_messages(self.name, since=time.time() - 3600)
        implementations = []
        
        for msg in reversed(messages):
            if msg.metadata.get("type") == "implementation":
                implementations.append(str(msg.content))
                
        return '\n'.join(implementations[-3:]) if implementations else "No implementations available"
    
    async def _execute_tests(self, test_strategy: str) -> Dict[str, Any]:
        """Simulate test execution"""
        # Simulate test execution based on strategy complexity
        strategy_lines = len(test_strategy.split('\n'))
        
        # Simulate test results
        total_tests = max(10, strategy_lines // 5)
        passed_tests = int(total_tests * 0.85)  # 85% pass rate
        failed_tests = total_tests - passed_tests
        
        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "coverage": min(95, 75 + (strategy_lines // 20)),
            "execution_time": strategy_lines * 0.1,
            "timestamp": time.time()
        }
    
    def _create_message(self, msg_type: str, content: Any, metadata: Dict[str, Any] = None):
        """Create a blackboard message"""
        from app.flow.multi_agent_environment import BlackboardMessage, MessageType
        return BlackboardMessage(
            id=f"test_{self.name}_{int(time.time())}",
            type=MessageType.RESULT,
            sender=self.name,
            recipient=None,
            content=content,
            metadata=metadata or {}
        )


class DevOpsAgent(SpecializedAgent):
    """DevOps and Infrastructure Specialist"""
    
    def __init__(self, agent_id: str, blackboard, **kwargs):
        super().__init__(AgentRole.DEVOPS, blackboard, name=agent_id, **kwargs)
        self.technologies = ['docker', 'kubernetes', 'jenkins', 'github-actions', 'terraform', 'ansible']
        self.cloud_providers = ['aws', 'azure', 'gcp', 'digitalocean']
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute DevOps tasks"""
        self.add_thought(f"Setting up deployment infrastructure for: {task.title}")
        
        # Get architecture for infrastructure needs
        architecture = await self._get_architecture_context()
        
        # Get security requirements
        security_reqs = await self.collaborate(AgentRole.SECURITY,
            "What security measures are needed for deployment infrastructure?")
        
        # DevOps strategy prompt
        devops_prompt = f"""
        Design comprehensive DevOps and deployment strategy:
        
        Project: {task.description}
        Architecture: {architecture}
        Security Requirements: {security_reqs}
        
        Provide:
        1. Infrastructure design and provisioning
        2. Containerization strategy (Docker files)
        3. CI/CD pipeline configuration
        4. Deployment automation
        5. Monitoring and logging setup
        6. Backup and disaster recovery
        7. Security hardening
        8. Scaling strategies
        9. Cost optimization
        10. Environment management (dev/staging/prod)
        
        Include specific configuration files and scripts.
        """
        
        response = await self.llm.ask([{"role": "user", "content": devops_prompt}])
        
        # Parse DevOps configuration
        devops_config = self._parse_devops_response(response)
        
        # Share deployment configuration
        self.blackboard.post_message(self._create_message(
            "deployment_config",
            devops_config,
            metadata={"type": "devops", "task_id": task.id}
        ))
        
        return f"Deployment infrastructure configured: {len(devops_config.get('configs', []))} configurations"
    
    async def _answer_question(self, question: str) -> str:
        """Answer DevOps-related questions"""
        answer_prompt = f"""
        As a DevOps Engineer, answer this infrastructure/DevOps question: {question}
        
        Provide:
        - Infrastructure best practices
        - Automation strategies
        - Security considerations
        - Performance optimization
        - Cost management
        - Monitoring and alerting
        """
        
        response = await self.llm.ask([{"role": "user", "content": answer_prompt}])
        return response
    
    async def _get_architecture_context(self) -> str:
        """Get architecture context from blackboard"""
        messages = self.blackboard.get_messages(self.name, since=time.time() - 3600)
        for msg in reversed(messages):
            if msg.metadata.get("type") == "architecture":
                return str(msg.content)
        return "No architecture context available"
    
    def _parse_devops_response(self, response: str) -> Dict[str, Any]:
        """Parse DevOps configuration response"""
        return {
            "infrastructure": self._extract_section(response, "infrastructure"),
            "docker": self._extract_section(response, "docker"),
            "kubernetes": self._extract_section(response, "kubernetes"),
            "cicd": self._extract_section(response, "pipeline"),
            "monitoring": self._extract_section(response, "monitoring"),
            "configs": self._extract_config_files(response),
            "timestamp": time.time()
        }
    
    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract a specific section from the response"""
        lines = text.split('\n')
        section_lines = []
        in_section = False
        
        for line in lines:
            if section_name.lower() in line.lower():
                in_section = True
            if in_section and line.strip():
                section_lines.append(line)
            if in_section and line.startswith('#') and section_name.lower() not in line.lower():
                break
                
        return '\n'.join(section_lines)
    
    def _extract_config_files(self, text: str) -> List[Dict[str, str]]:
        """Extract configuration files from response"""
        import re
        configs = []
        
        # Extract code blocks that look like config files
        code_blocks = re.findall(r'```(\w*)\n(.*?)\n```', text, re.DOTALL)
        
        for lang, code in code_blocks:
            if lang in ['yaml', 'yml', 'json', 'dockerfile', 'docker', 'bash', 'sh']:
                configs.append({
                    "type": lang,
                    "content": code
                })
        
        return configs
    
    def _create_message(self, msg_type: str, content: Any, metadata: Dict[str, Any] = None):
        """Create a blackboard message"""
        from app.flow.multi_agent_environment import BlackboardMessage, MessageType
        return BlackboardMessage(
            id=f"devops_{self.name}_{int(time.time())}",
            type=MessageType.RESULT,
            sender=self.name,
            recipient=None,
            content=content,
            metadata=metadata or {}
        )


class SecurityAgent(SpecializedAgent):
    """Security Specialist"""
    
    def __init__(self, agent_id: str, blackboard, **kwargs):
        super().__init__(AgentRole.SECURITY, blackboard, name=agent_id, **kwargs)
        self.security_areas = ['authentication', 'authorization', 'encryption', 'input_validation', 
                              'api_security', 'infrastructure_security', 'data_protection']
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute security tasks"""
        self.add_thought(f"Implementing security measures for: {task.title}")
        
        # Get architecture and implementations
        architecture = await self._get_architecture_context()
        implementations = await self._get_implementations()
        
        # Security analysis prompt
        security_prompt = f"""
        Conduct comprehensive security analysis and implementation:
        
        Feature: {task.description}
        Architecture: {architecture}
        Implementations: {implementations}
        
        Provide:
        1. Security threat analysis
        2. Vulnerability assessment
        3. Security controls implementation
        4. Authentication and authorization design
        5. Data protection measures
        6. API security implementation
        7. Infrastructure hardening
        8. Security testing procedures
        9. Compliance considerations
        10. Security monitoring setup
        
        Include specific security code implementations and configurations.
        """
        
        response = await self.llm.ask([{"role": "user", "content": security_prompt}])
        
        # Parse security implementation
        security_impl = self._parse_security_response(response)
        
        # Share security measures
        self.blackboard.post_message(self._create_message(
            "security_implementation",
            security_impl,
            metadata={"type": "security", "task_id": task.id}
        ))
        
        return f"Security measures implemented: {len(security_impl.get('controls', []))} controls"
    
    async def _answer_question(self, question: str) -> str:
        """Answer security-related questions"""
        answer_prompt = f"""
        As a Security Engineer, answer this security question: {question}
        
        Provide:
        - Security best practices
        - Threat analysis
        - Vulnerability mitigation
        - Compliance requirements
        - Security architecture recommendations
        """
        
        response = await self.llm.ask([{"role": "user", "content": answer_prompt}])
        return response
    
    async def _get_architecture_context(self) -> str:
        """Get architecture context from blackboard"""
        messages = self.blackboard.get_messages(self.name, since=time.time() - 3600)
        for msg in reversed(messages):
            if msg.metadata.get("type") == "architecture":
                return str(msg.content)
        return "No architecture context available"
    
    async def _get_implementations(self) -> str:
        """Get implementation details from blackboard"""
        messages = self.blackboard.get_messages(self.name, since=time.time() - 3600)
        implementations = []
        
        for msg in reversed(messages):
            if msg.metadata.get("type") == "implementation":
                implementations.append(str(msg.content))
                
        return '\n'.join(implementations[-2:]) if implementations else "No implementations available"
    
    def _parse_security_response(self, response: str) -> Dict[str, Any]:
        """Parse security implementation response"""
        return {
            "threat_analysis": self._extract_section(response, "threat"),
            "vulnerabilities": self._extract_section(response, "vulnerability"),
            "controls": self._extract_security_controls(response),
            "implementations": self._extract_code_blocks(response),
            "compliance": self._extract_section(response, "compliance"),
            "timestamp": time.time()
        }
    
    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract a specific section from the response"""
        lines = text.split('\n')
        section_lines = []
        in_section = False
        
        for line in lines:
            if section_name.lower() in line.lower():
                in_section = True
            if in_section and line.strip():
                section_lines.append(line)
            if in_section and line.startswith('#') and section_name.lower() not in line.lower():
                break
                
        return '\n'.join(section_lines)
    
    def _extract_security_controls(self, text: str) -> List[str]:
        """Extract security controls from response"""
        controls = []
        lines = text.split('\n')
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ['control', 'measure', 'safeguard', 'protection']):
                if line.strip().startswith('-') or line.strip().startswith('*'):
                    controls.append(line.strip())
        
        return controls[:15]  # Limit to top 15
    
    def _extract_code_blocks(self, text: str) -> List[str]:
        """Extract code blocks from response"""
        import re
        code_blocks = re.findall(r'```[\w]*\n(.*?)\n```', text, re.DOTALL)
        return code_blocks
    
    def _create_message(self, msg_type: str, content: Any, metadata: Dict[str, Any] = None):
        """Create a blackboard message"""
        from app.flow.multi_agent_environment import BlackboardMessage, MessageType
        return BlackboardMessage(
            id=f"sec_{self.name}_{int(time.time())}",
            type=MessageType.RESULT,
            sender=self.name,
            recipient=None,
            content=content,
            metadata=metadata or {}
        )


# Other specialized agents (simplified implementations for brevity)

class ProductManagerAgent(SpecializedAgent):
    """Product Management Specialist"""
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute product management tasks"""
        self.add_thought(f"Analyzing requirements for: {task.description}")
        
        prompt = f"""
        As a Product Manager, analyze and plan: {task.description}
        
        Provide:
        1. Requirements analysis
        2. User stories and acceptance criteria
        3. Feature prioritization
        4. User experience considerations
        5. Market analysis
        6. Success metrics
        7. Roadmap recommendations
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        return f"Product analysis completed: {len(response.split())} words of analysis"
    
    async def _answer_question(self, question: str) -> str:
        """Answer product management questions"""
        response = await self.llm.ask([{"role": "user", "content": f"Product Manager answer: {question}"}])
        return response


class UIUXDesignerAgent(SpecializedAgent):
    """UI/UX Design Specialist"""
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute UI/UX design tasks"""
        self.add_thought(f"Designing user interface for: {task.title}")
        
        prompt = f"""
        As a UI/UX Designer, design interfaces for: {task.description}
        
        Provide:
        1. User flow design
        2. Wireframe descriptions
        3. UI component specifications
        4. Accessibility considerations
        5. Responsive design strategy
        6. Design system recommendations
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        return f"UI/UX design completed: {len(response.split())} words of design specifications"
    
    async def _answer_question(self, question: str) -> str:
        """Answer UI/UX design questions"""
        response = await self.llm.ask([{"role": "user", "content": f"UI/UX Designer answer: {question}"}])
        return response


class DataAnalystAgent(SpecializedAgent):
    """Data Analysis Specialist"""
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute data analysis tasks"""
        self.add_thought(f"Analyzing data for: {task.title}")
        
        prompt = f"""
        As a Data Analyst, analyze requirements for: {task.description}
        
        Provide:
        1. Data requirements analysis
        2. Data modeling recommendations
        3. Analytics implementation plan
        4. Data visualization strategy
        5. Performance metrics definition
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        return f"Data analysis completed: {len(response.split())} words of analysis"
    
    async def _answer_question(self, question: str) -> str:
        """Answer data analysis questions"""
        response = await self.llm.ask([{"role": "user", "content": f"Data Analyst answer: {question}"}])
        return response


class DocumentationAgent(SpecializedAgent):
    """Technical Documentation Specialist"""
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute documentation tasks"""
        self.add_thought(f"Creating documentation for: {task.title}")
        
        prompt = f"""
        As a Technical Writer, create documentation for: {task.description}
        
        Provide:
        1. API documentation
        2. User guides
        3. Developer documentation
        4. Installation guides
        5. Troubleshooting guides
        6. Code examples
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        return f"Documentation created: {len(response.split())} words of documentation"
    
    async def _answer_question(self, question: str) -> str:
        """Answer documentation questions"""
        response = await self.llm.ask([{"role": "user", "content": f"Technical Writer answer: {question}"}])
        return response


class PerformanceAgent(SpecializedAgent):
    """Performance Optimization Specialist"""
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute performance optimization tasks"""
        self.add_thought(f"Optimizing performance for: {task.title}")
        
        prompt = f"""
        As a Performance Engineer, optimize: {task.description}
        
        Provide:
        1. Performance analysis
        2. Bottleneck identification
        3. Optimization strategies
        4. Caching implementation
        5. Database optimization
        6. Monitoring setup
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        return f"Performance optimization completed: {len(response.split())} words of analysis"
    
    async def _answer_question(self, question: str) -> str:
        """Answer performance questions"""
        response = await self.llm.ask([{"role": "user", "content": f"Performance Engineer answer: {question}"}])
        return response


class CodeReviewerAgent(SpecializedAgent):
    """Code Review Specialist"""
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute code review tasks"""
        self.add_thought(f"Reviewing code for: {task.title}")
        
        prompt = f"""
        As a Code Reviewer, review this implementation: {task.description}
        
        Provide:
        1. Code quality assessment
        2. Best practices compliance
        3. Security analysis
        4. Performance considerations
        5. Maintainability assessment
        6. Recommendations for improvement
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        return f"Code review completed: {len(response.split())} words of review"
    
    async def _answer_question(self, question: str) -> str:
        """Answer code review questions"""
        response = await self.llm.ask([{"role": "user", "content": f"Code Reviewer answer: {question}"}])
        return response


class ResearcherAgent(SpecializedAgent):
    """Technical Research Specialist"""
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute research tasks"""
        self.add_thought(f"Researching solutions for: {task.title}")
        
        prompt = f"""
        As a Technical Researcher, research solutions for: {task.description}
        
        Provide:
        1. Technology analysis
        2. Solution comparison
        3. Best practices research
        4. Industry standards review
        5. Implementation recommendations
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        return f"Research completed: {len(response.split())} words of research"
    
    async def _answer_question(self, question: str) -> str:
        """Answer research questions"""
        response = await self.llm.ask([{"role": "user", "content": f"Researcher answer: {question}"}])
        return response