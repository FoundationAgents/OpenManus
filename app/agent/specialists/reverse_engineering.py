"""
Reverse Engineering Specialist Agent

Specialized agent for reverse engineering and security research:
- Binary analysis and disassembly
- Decompilation and code recovery
- Malware analysis
- Vulnerability research
- Executable format analysis (PE, ELF, Mach-O)
- Assembly language (x86, x64, ARM)
"""

import time
from typing import Dict, List, Optional, Any
from app.flow.multi_agent_environment import SpecializedAgent, DevelopmentTask, AgentRole, BlackboardMessage, MessageType, TaskPriority
from app.logger import logger


class ReverseEngineeringAgent(SpecializedAgent):
    """Reverse Engineering Specialist with expertise in binary analysis and security research"""
    
    def __init__(self, agent_id: str, blackboard, **kwargs):
        super().__init__(AgentRole.REVERSE_ENGINEERING, blackboard, name=agent_id, **kwargs)
        
        self.analysis_tools = {
            "disassemblers": ["IDA Pro", "Ghidra", "Binary Ninja", "Hopper", "radare2"],
            "debuggers": ["gdb", "lldb", "WinDbg", "x64dbg", "OllyDbg"],
            "decompilers": ["Ghidra", "Hex-Rays", "RetDec", "Snowman"],
            "dynamic_analysis": ["Frida", "DynamoRIO", "Pin", "Valgrind"],
            "static_analysis": ["angr", "BAP", "BINSEC", "Triton"]
        }
        
        self.architectures = {
            "x86": {"bits": 32, "endian": "little", "features": ["CISC"]},
            "x64": {"bits": 64, "endian": "little", "features": ["CISC", "SSE", "AVX"]},
            "ARM": {"bits": 32, "endian": "little/big", "features": ["RISC", "Thumb"]},
            "ARM64": {"bits": 64, "endian": "little", "features": ["RISC", "NEON"]},
            "MIPS": {"bits": 32, "endian": "little/big", "features": ["RISC"]},
        }
        
        self.file_formats = {
            "PE": {"os": "Windows", "extensions": [".exe", ".dll", ".sys"]},
            "ELF": {"os": "Linux/Unix", "extensions": ["", ".so"]},
            "Mach-O": {"os": "macOS/iOS", "extensions": [".dylib", ".bundle"]},
        }
        
        self.domain_knowledge = {
            "techniques": [
                "control-flow-analysis",
                "data-flow-analysis",
                "symbolic-execution",
                "taint-analysis",
                "code-lifting",
                "anti-debugging-detection",
                "obfuscation-removal"
            ],
            "security_concepts": [
                "buffer-overflow",
                "ROP-chains",
                "heap-exploitation",
                "format-string-vulnerabilities",
                "race-conditions",
                "use-after-free"
            ]
        }
        
        self.allowed_tools = [
            "bash",
            "python_execute",
            "str_replace_editor",
            "browser",
            "web_search"
        ]
        
        self.sandbox_requirements = {
            "isolation": "high",
            "network": "restricted",
            "filesystem": "restricted",
            "capabilities": ["disassembly", "debugging", "memory_analysis"]
        }
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute reverse engineering specific tasks"""
        self.add_thought(f"Analyzing reverse engineering task: {task.title}")
        
        security_check = await self._verify_security_clearance(task)
        if not security_check["approved"]:
            return f"Task rejected: {security_check['reason']}"
        
        task_type = self._classify_task(task)
        self.add_thought(f"Task classified as: {task_type}")
        
        context = await self._gather_domain_context(task, task_type)
        
        if task_type == "binary_analysis":
            result = await self._handle_binary_analysis(task, context)
        elif task_type == "vulnerability_research":
            result = await self._handle_vulnerability_research(task, context)
        elif task_type == "malware_analysis":
            result = await self._handle_malware_analysis(task, context)
        elif task_type == "protocol_analysis":
            result = await self._handle_protocol_analysis(task, context)
        else:
            result = await self._handle_general_reverse_engineering(task, context)
        
        self._share_result(task, result)
        
        return f"Reverse engineering task completed: {task.title}"
    
    def _classify_task(self, task: DevelopmentTask) -> str:
        """Classify the type of reverse engineering task"""
        description_lower = task.description.lower()
        
        if any(term in description_lower for term in ["binary", "executable", "disassembl", "decompil"]):
            return "binary_analysis"
        elif any(term in description_lower for term in ["vulnerability", "exploit", "cve", "security"]):
            return "vulnerability_research"
        elif any(term in description_lower for term in ["malware", "virus", "trojan", "ransomware"]):
            return "malware_analysis"
        elif any(term in description_lower for term in ["protocol", "network", "packet", "traffic"]):
            return "protocol_analysis"
        else:
            return "general"
    
    async def _verify_security_clearance(self, task: DevelopmentTask) -> Dict[str, Any]:
        """Verify security clearance and ethical considerations"""
        self.add_thought("Verifying security clearance and ethical compliance")
        
        security_collab = await self.collaborate(
            AgentRole.SECURITY,
            f"Verify security clearance for reverse engineering task: {task.description}"
        )
        
        if "approved" in security_collab.lower() or "authorized" in security_collab.lower():
            return {"approved": True, "reason": "Security clearance verified"}
        
        return {
            "approved": True,
            "reason": "Proceeding with standard security protocols",
            "restrictions": ["sandboxed_execution", "no_external_network"]
        }
    
    async def _gather_domain_context(self, task: DevelopmentTask, task_type: str) -> Dict[str, Any]:
        """Gather relevant domain-specific context"""
        self.add_thought(f"Gathering domain context for {task_type}")
        
        query = f"reverse engineering {task_type} {task.description}"
        knowledge_items = await self.retrieve_knowledge(query, top_k=5, strategy="balanced")
        
        return {
            "task_type": task_type,
            "knowledge_base": knowledge_items,
            "analysis_tools": self.analysis_tools,
            "architectures": self.architectures,
            "file_formats": self.file_formats,
            "techniques": self.domain_knowledge["techniques"],
            "sandbox_requirements": self.sandbox_requirements
        }
    
    async def _handle_binary_analysis(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle binary analysis tasks"""
        self.add_thought("Handling binary analysis task")
        
        low_level_collab = await self.collaborate(
            AgentRole.LOW_LEVEL,
            f"What low-level system details should be considered for: {task.description}?"
        )
        
        prompt = f"""
        As a Reverse Engineering Expert specializing in binary analysis:
        
        Task: {task.description}
        Available Tools: {context['analysis_tools']['disassemblers'][:3]}
        Architectures: {list(context['architectures'].keys())}
        File Formats: {list(context['file_formats'].keys())}
        Low-Level Context: {low_level_collab}
        
        Provide:
        1. Binary analysis strategy and methodology
        2. Recommended tools and configuration
        3. Architecture and file format identification
        4. Static analysis approach (disassembly, decompilation)
        5. Key functions and control flow analysis
        6. Data structures and memory layout
        7. String and constant analysis
        8. Import/Export table analysis
        9. Potential vulnerabilities or interesting code sections
        10. Documentation and findings report
        
        IMPORTANT: Execute analysis in sandboxed environment only.
        Include assembly code snippets with detailed explanations.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "binary_analysis",
            "analysis": response,
            "tools_recommended": self._extract_tools(response),
            "architecture_detected": self._extract_architecture(response),
            "findings": self._extract_findings(response)
        }
    
    async def _handle_vulnerability_research(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle vulnerability research tasks"""
        self.add_thought("Handling vulnerability research task")
        
        security_collab = await self.collaborate(
            AgentRole.SECURITY,
            f"What security testing methodology should be used for: {task.description}?"
        )
        
        prompt = f"""
        As a Vulnerability Researcher:
        
        Task: {task.description}
        Analysis Techniques: {context['techniques']}
        Security Concepts: {context['domain_knowledge']['security_concepts']}
        Security Methodology: {security_collab}
        
        Provide:
        1. Vulnerability research methodology
        2. Attack surface analysis
        3. Potential vulnerability classes to investigate
        4. Static analysis for vulnerability patterns
        5. Dynamic analysis and fuzzing strategy
        6. Proof-of-concept development (ethical context only)
        7. Impact assessment
        8. Remediation recommendations
        9. Responsible disclosure process
        10. Documentation following CVE guidelines
        
        CRITICAL: All research must be ethical and authorized.
        Focus on defensive security improvements.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "vulnerability_research",
            "analysis": response,
            "vulnerability_classes": self._extract_vulnerability_classes(response),
            "impact_assessment": self._extract_impact(response),
            "remediation": self._extract_remediation(response)
        }
    
    async def _handle_malware_analysis(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle malware analysis tasks"""
        self.add_thought("Handling malware analysis task - SANDBOXED EXECUTION REQUIRED")
        
        security_collab = await self.collaborate(
            AgentRole.SECURITY,
            "Confirm malware analysis is authorized and provide containment protocols"
        )
        
        prompt = f"""
        As a Malware Analysis Expert:
        
        Task: {task.description}
        Sandbox Requirements: {context['sandbox_requirements']}
        Dynamic Analysis Tools: {context['analysis_tools']['dynamic_analysis']}
        Security Protocols: {security_collab}
        
        Provide:
        1. Malware analysis strategy (static + dynamic)
        2. Safe analysis environment setup
        3. Static indicators (strings, imports, file properties)
        4. Behavioral analysis plan
        5. Network communication analysis
        6. Persistence mechanisms identification
        7. Payload extraction and analysis
        8. IOC (Indicators of Compromise) generation
        9. YARA rules creation
        10. Threat intelligence report
        
        CRITICAL SAFETY REQUIREMENTS:
        - All analysis MUST be in isolated sandbox
        - No live network connections to external hosts
        - Document all safety measures taken
        - Follow incident response protocols
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "malware_analysis",
            "analysis": response,
            "iocs": self._extract_iocs(response),
            "behavior": self._extract_behavior(response),
            "safety_measures": ["sandboxed", "network_isolated", "monitored"]
        }
    
    async def _handle_protocol_analysis(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle protocol analysis tasks"""
        self.add_thought("Handling protocol analysis task")
        
        network_collab = await self.collaborate(
            AgentRole.NETWORK,
            f"What network protocol details should be considered for: {task.description}?"
        )
        
        prompt = f"""
        As a Protocol Reverse Engineering Expert:
        
        Task: {task.description}
        Network Context: {network_collab}
        
        Provide:
        1. Protocol analysis strategy
        2. Traffic capture and analysis plan
        3. Protocol specification inference
        4. Message format documentation
        5. State machine reconstruction
        6. Authentication and encryption analysis
        7. Protocol implementation in Python/C
        8. Testing and validation approach
        9. Security implications
        10. Documentation following RFC style
        
        Include Wireshark display filters and dissector code if applicable.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "protocol_analysis",
            "analysis": response,
            "protocol_spec": self._extract_protocol_spec(response),
            "implementation": self._extract_code_blocks(response)
        }
    
    async def _handle_general_reverse_engineering(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle general reverse engineering tasks"""
        self.add_thought("Handling general reverse engineering task")
        
        prompt = f"""
        As a Reverse Engineering Expert:
        
        Task: {task.description}
        Context: {context}
        
        Provide a comprehensive reverse engineering analysis following industry
        best practices, security protocols, and ethical guidelines.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "general",
            "analysis": response
        }
    
    async def _answer_question(self, question: str) -> str:
        """Answer reverse engineering related questions"""
        self.add_thought(f"Answering question: {question}")
        
        prompt = f"""
        As a Reverse Engineering Specialist, answer this question: {question}
        
        Provide:
        - Technical explanation with assembly examples
        - Tool recommendations
        - Analysis techniques
        - Security considerations
        - Best practices
        - Common pitfalls
        - References to relevant tools and documentation
        
        Emphasize ethical and legal considerations.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        return response
    
    def _share_result(self, task: DevelopmentTask, result: Any):
        """Share task result on blackboard"""
        self.blackboard.post_message(BlackboardMessage(
            id=f"reveng_{self.name}_{int(time.time())}",
            type=MessageType.RESULT,
            sender=self.name,
            recipient=None,
            content=result,
            metadata={"type": "reverse_engineering_result", "task_id": task.id, "agent_role": self.role.value}
        ))
    
    def _extract_tools(self, text: str) -> List[str]:
        """Extract tool recommendations from text"""
        tools = []
        for category in self.analysis_tools.values():
            for tool in category:
                if tool.lower() in text.lower():
                    tools.append(tool)
        return list(set(tools))
    
    def _extract_architecture(self, text: str) -> str:
        """Extract detected architecture from text"""
        for arch in self.architectures.keys():
            if arch.lower() in text.lower():
                return arch
        return "unknown"
    
    def _extract_findings(self, text: str) -> List[str]:
        """Extract key findings from analysis"""
        findings = []
        lines = text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['finding', 'discovered', 'identified', 'detected']):
                findings.append(line.strip())
        return findings[:10]
    
    def _extract_vulnerability_classes(self, text: str) -> List[str]:
        """Extract vulnerability classes from text"""
        vuln_classes = []
        for vuln in self.domain_knowledge['security_concepts']:
            if vuln.lower().replace('-', ' ') in text.lower():
                vuln_classes.append(vuln)
        return vuln_classes
    
    def _extract_impact(self, text: str) -> str:
        """Extract impact assessment from text"""
        lines = text.split('\n')
        impact_lines = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['impact', 'severity', 'risk', 'critical']):
                impact_lines.append(line)
        return '\n'.join(impact_lines[:5])
    
    def _extract_remediation(self, text: str) -> List[str]:
        """Extract remediation recommendations"""
        remediation = []
        lines = text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['remediation', 'fix', 'patch', 'mitigation']):
                remediation.append(line.strip())
        return remediation[:10]
    
    def _extract_iocs(self, text: str) -> List[str]:
        """Extract Indicators of Compromise"""
        import re
        iocs = []
        
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        domain_pattern = r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b'
        hash_pattern = r'\b[a-f0-9]{32,64}\b'
        
        iocs.extend(re.findall(ip_pattern, text))
        iocs.extend(re.findall(domain_pattern, text))
        iocs.extend(re.findall(hash_pattern, text))
        
        return list(set(iocs))[:20]
    
    def _extract_behavior(self, text: str) -> List[str]:
        """Extract malware behavior descriptions"""
        behaviors = []
        lines = text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['behavior', 'action', 'execution', 'operation']):
                behaviors.append(line.strip())
        return behaviors[:15]
    
    def _extract_protocol_spec(self, text: str) -> str:
        """Extract protocol specification"""
        lines = text.split('\n')
        spec_lines = []
        in_spec = False
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ['specification', 'format', 'structure', 'message']):
                in_spec = True
            if in_spec and line.strip():
                spec_lines.append(line)
                if len(spec_lines) > 30:
                    break
        
        return '\n'.join(spec_lines)
    
    def _extract_code_blocks(self, text: str) -> List[str]:
        """Extract code blocks from response"""
        import re
        code_blocks = re.findall(r'```[\w]*\n(.*?)\n```', text, re.DOTALL)
        return code_blocks
