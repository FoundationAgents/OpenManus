"""
Network Engineering Specialist Agent

Specialized agent for network engineering and distributed systems:
- Network protocols (TCP/IP, HTTP, WebSockets, gRPC)
- Distributed systems architecture
- API design and implementation
- Network security and encryption
- Load balancing and scaling
- Network diagnostics and monitoring
"""

import time
from typing import Dict, List, Optional, Any
from app.flow.multi_agent_environment import SpecializedAgent, DevelopmentTask, AgentRole, BlackboardMessage, MessageType, TaskPriority
from app.logger import logger


class NetworkAgent(SpecializedAgent):
    """Network Engineering Specialist with expertise in protocols and distributed systems"""
    
    def __init__(self, agent_id: str, blackboard, **kwargs):
        super().__init__(AgentRole.NETWORK, blackboard, name=agent_id, **kwargs)
        
        self.protocols = {
            "TCP/IP": {
                "layer": "transport",
                "features": ["reliable", "ordered", "connection-oriented"],
                "use_cases": ["web", "file-transfer", "email"]
            },
            "UDP": {
                "layer": "transport",
                "features": ["unreliable", "connectionless", "low-latency"],
                "use_cases": ["streaming", "gaming", "dns"]
            },
            "HTTP": {
                "layer": "application",
                "versions": ["1.1", "2", "3"],
                "features": ["stateless", "request-response"]
            },
            "WebSocket": {
                "layer": "application",
                "features": ["bidirectional", "real-time", "persistent"],
                "use_cases": ["chat", "live-updates", "gaming"]
            },
            "gRPC": {
                "layer": "application",
                "features": ["high-performance", "binary", "streaming"],
                "use_cases": ["microservices", "mobile", "iot"]
            },
            "MQTT": {
                "layer": "application",
                "features": ["pub-sub", "lightweight", "qos"],
                "use_cases": ["iot", "sensors", "telemetry"]
            }
        }
        
        self.domain_knowledge = {
            "network_layers": ["physical", "data-link", "network", "transport", "session", "presentation", "application"],
            "security": ["TLS", "SSL", "IPSec", "VPN", "firewall", "DDoS-protection"],
            "patterns": ["load-balancing", "circuit-breaker", "retry", "timeout", "bulkhead", "rate-limiting"],
            "diagnostics": ["ping", "traceroute", "tcpdump", "wireshark", "netstat", "ss", "iperf"],
            "distributed": ["CAP-theorem", "consensus", "replication", "sharding", "eventual-consistency"]
        }
        
        self.api_styles = {
            "REST": {"protocol": "HTTP", "features": ["stateless", "resource-based", "CRUD"]},
            "GraphQL": {"protocol": "HTTP", "features": ["query-language", "single-endpoint", "type-safe"]},
            "gRPC": {"protocol": "HTTP/2", "features": ["binary", "streaming", "code-generation"]},
            "WebSocket": {"protocol": "WebSocket", "features": ["bidirectional", "real-time", "event-driven"]}
        }
        
        self.cloud_services = {
            "AWS": ["VPC", "ELB", "Route53", "CloudFront", "API Gateway"],
            "Azure": ["Virtual Network", "Load Balancer", "Traffic Manager", "CDN", "API Management"],
            "GCP": ["VPC", "Cloud Load Balancing", "Cloud CDN", "API Gateway"]
        }
        
        self.allowed_tools = [
            "bash",
            "python_execute",
            "str_replace_editor",
            "browser",
            "web_search",
            "http_request",
            "dns_lookup",
            "ping",
            "traceroute"
        ]
        
        self.network_toolkit_integration = {
            "http_client": "HTTPClientWithCaching",
            "websocket": "WebSocketHandler",
            "diagnostics": "NetworkDiagnostics",
            "api_manager": "APIIntegrationManager",
            "guardian": "Guardian"
        }
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute network engineering specific tasks"""
        self.add_thought(f"Analyzing network engineering task: {task.title}")
        
        task_type = self._classify_task(task)
        self.add_thought(f"Task classified as: {task_type}")
        
        context = await self._gather_domain_context(task, task_type)
        
        if task_type == "api_design":
            result = await self._handle_api_design(task, context)
        elif task_type == "protocol_implementation":
            result = await self._handle_protocol_implementation(task, context)
        elif task_type == "distributed_systems":
            result = await self._handle_distributed_systems(task, context)
        elif task_type == "network_security":
            result = await self._handle_network_security(task, context)
        elif task_type == "network_diagnostics":
            result = await self._handle_network_diagnostics(task, context)
        else:
            result = await self._handle_general_networking(task, context)
        
        self._share_result(task, result)
        
        return f"Network engineering task completed: {task.title}"
    
    def _classify_task(self, task: DevelopmentTask) -> str:
        """Classify the type of network engineering task"""
        description_lower = task.description.lower()
        
        if any(term in description_lower for term in ["api", "rest", "graphql", "endpoint"]):
            return "api_design"
        elif any(term in description_lower for term in ["protocol", "tcp", "udp", "websocket", "grpc"]):
            return "protocol_implementation"
        elif any(term in description_lower for term in ["distributed", "microservice", "cluster", "consensus"]):
            return "distributed_systems"
        elif any(term in description_lower for term in ["security", "tls", "encryption", "firewall", "vpn"]):
            return "network_security"
        elif any(term in description_lower for term in ["diagnostic", "debug", "trace", "monitor", "ping"]):
            return "network_diagnostics"
        else:
            return "general"
    
    async def _gather_domain_context(self, task: DevelopmentTask, task_type: str) -> Dict[str, Any]:
        """Gather relevant domain-specific context"""
        self.add_thought(f"Gathering domain context for {task_type}")
        
        query = f"network engineering {task_type} {task.description}"
        knowledge_items = await self.retrieve_knowledge(query, top_k=5, strategy="balanced")
        
        architecture = await self._get_architecture_context()
        security_reqs = await self._get_security_requirements(task)
        
        return {
            "task_type": task_type,
            "knowledge_base": knowledge_items,
            "architecture": architecture,
            "security_requirements": security_reqs,
            "protocols": self.protocols,
            "domain_knowledge": self.domain_knowledge,
            "network_toolkit": self.network_toolkit_integration
        }
    
    async def _handle_api_design(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle API design tasks"""
        self.add_thought("Handling API design task")
        
        security_collab = await self.collaborate(
            AgentRole.SECURITY,
            f"What security measures should be implemented for API: {task.description}?"
        )
        
        architect_collab = await self.collaborate(
            AgentRole.ARCHITECT,
            f"What architectural patterns should guide the API design for: {task.description}?"
        )
        
        prompt = f"""
        As a Network Engineering Expert specializing in API design:
        
        Task: {task.description}
        API Styles: {list(self.api_styles.keys())}
        Security Requirements: {security_collab}
        Architectural Guidance: {architect_collab}
        
        Provide:
        1. Recommended API style (REST/GraphQL/gRPC) with rationale
        2. API specification (OpenAPI/GraphQL schema/Protobuf)
        3. Endpoint design and resource modeling
        4. Authentication and authorization strategy
        5. Request/response format and validation
        6. Error handling and status codes
        7. Rate limiting and throttling
        8. Versioning strategy
        9. Documentation (interactive docs)
        10. Client SDK generation approach
        11. Testing strategy (unit, integration, load)
        12. Monitoring and observability
        
        Include:
        - Complete API specification
        - Sample requests and responses
        - Error scenarios
        - Performance considerations
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "api_design",
            "specification": response,
            "api_style": self._extract_api_style(response),
            "endpoints": self._extract_endpoints(response),
            "security_measures": self._extract_security_measures(response)
        }
    
    async def _handle_protocol_implementation(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle protocol implementation tasks"""
        self.add_thought("Handling protocol implementation task")
        
        low_level_collab = await self.collaborate(
            AgentRole.LOW_LEVEL,
            f"What low-level considerations are needed for protocol: {task.description}?"
        )
        
        prompt = f"""
        As a Network Protocol Expert:
        
        Task: {task.description}
        Available Protocols: {list(self.protocols.keys())}
        Low-Level Considerations: {low_level_collab}
        Network Toolkit: {context['network_toolkit']}
        
        Provide:
        1. Protocol selection and rationale
        2. Protocol state machine design
        3. Message format and framing
        4. Connection management (establishment, keep-alive, termination)
        5. Error handling and recovery
        6. Flow control and congestion management
        7. Implementation in Python (using asyncio/socket)
        8. Client and server implementation
        9. Testing strategy (unit tests, integration tests, protocol compliance)
        10. Performance optimization
        11. Security considerations
        12. Monitoring and debugging
        
        Use the network toolkit components where applicable:
        - HTTPClientWithCaching for HTTP
        - WebSocketHandler for WebSocket
        - NetworkDiagnostics for testing
        
        Include complete, production-ready code with error handling.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "protocol_implementation",
            "implementation": response,
            "protocol": self._extract_protocol(response),
            "state_machine": self._extract_state_machine(response),
            "code": self._extract_code_blocks(response)
        }
    
    async def _handle_distributed_systems(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle distributed systems tasks"""
        self.add_thought("Handling distributed systems task")
        
        architect_collab = await self.collaborate(
            AgentRole.ARCHITECT,
            f"What distributed system patterns should be used for: {task.description}?"
        )
        
        devops_collab = await self.collaborate(
            AgentRole.DEVOPS,
            f"What deployment and orchestration strategy for distributed system: {task.description}?"
        )
        
        prompt = f"""
        As a Distributed Systems Expert:
        
        Task: {task.description}
        Distributed Patterns: {context['domain_knowledge']['distributed']}
        Architecture Patterns: {context['domain_knowledge']['patterns']}
        Architectural Guidance: {architect_collab}
        Deployment Strategy: {devops_collab}
        
        Provide:
        1. System architecture and component design
        2. Communication patterns (sync/async, pub-sub, message queue)
        3. Consistency and availability trade-offs (CAP theorem)
        4. Consensus algorithm if needed (Raft, Paxos)
        5. Data partitioning and replication strategy
        6. Service discovery and registration
        7. Load balancing strategy
        8. Fault tolerance and recovery
        9. Distributed tracing and observability
        10. Implementation approach
        11. Testing distributed system behavior
        12. Scalability and performance optimization
        
        Consider:
        - Network partitions
        - Clock synchronization
        - Eventual consistency
        - Idempotency
        - Circuit breakers and retries
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "distributed_systems",
            "architecture": response,
            "patterns_used": self._extract_patterns(response),
            "consistency_model": self._extract_consistency(response),
            "components": self._extract_components(response)
        }
    
    async def _handle_network_security(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle network security tasks"""
        self.add_thought("Handling network security task")
        
        security_collab = await self.collaborate(
            AgentRole.SECURITY,
            f"Comprehensive security strategy for network system: {task.description}"
        )
        
        prompt = f"""
        As a Network Security Expert:
        
        Task: {task.description}
        Security Technologies: {context['domain_knowledge']['security']}
        Security Strategy: {security_collab}
        Guardian Integration: {context['network_toolkit']['guardian']}
        
        Provide:
        1. Threat model and risk assessment
        2. Network security architecture
        3. Encryption strategy (TLS/SSL configuration)
        4. Authentication and authorization
        5. Firewall rules and network segmentation
        6. DDoS protection and rate limiting
        7. Intrusion detection and prevention
        8. Secure communication channels
        9. Certificate management
        10. Security monitoring and logging
        11. Incident response procedures
        12. Compliance considerations
        
        Integrate with Guardian for:
        - Access control policies
        - Risk assessment
        - Security validation
        
        Include security hardening checklists and configuration examples.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "network_security",
            "security_plan": response,
            "threat_model": self._extract_threats(response),
            "security_measures": self._extract_security_measures(response),
            "configurations": self._extract_configurations(response)
        }
    
    async def _handle_network_diagnostics(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle network diagnostics tasks"""
        self.add_thought("Handling network diagnostics task")
        
        prompt = f"""
        As a Network Diagnostics Expert:
        
        Task: {task.description}
        Diagnostic Tools: {context['domain_knowledge']['diagnostics']}
        Network Toolkit: NetworkDiagnostics (dns_lookup, ping, traceroute)
        
        Provide:
        1. Diagnostic strategy and methodology
        2. Network topology mapping
        3. Connectivity testing approach
        4. Latency and bandwidth measurement
        5. Packet capture and analysis
        6. DNS resolution diagnostics
        7. Route tracing and path analysis
        8. Port scanning and service detection
        9. Performance bottleneck identification
        10. Monitoring and alerting setup
        11. Python implementation using network toolkit
        12. Reporting and visualization
        
        Use NetworkDiagnostics tools:
        - dns_lookup() for DNS resolution
        - ping() for connectivity and latency
        - traceroute() for path analysis
        
        Include scripts for automated diagnostics and monitoring.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "network_diagnostics",
            "diagnostic_plan": response,
            "tools_used": self._extract_tools(response),
            "findings": self._extract_findings(response),
            "code": self._extract_code_blocks(response)
        }
    
    async def _handle_general_networking(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle general networking tasks"""
        self.add_thought("Handling general networking task")
        
        prompt = f"""
        As a Network Engineering Expert:
        
        Task: {task.description}
        Context: {context}
        
        Provide a comprehensive networking solution following industry best
        practices, considering performance, security, scalability, and reliability.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "general",
            "implementation": response
        }
    
    async def _answer_question(self, question: str) -> str:
        """Answer network engineering related questions"""
        self.add_thought(f"Answering question: {question}")
        
        prompt = f"""
        As a Network Engineering Specialist, answer this question: {question}
        
        Provide:
        - Clear technical explanation
        - Protocol details and RFCs where applicable
        - Code examples (Python preferred)
        - Network diagrams description
        - Best practices
        - Common issues and solutions
        - Performance considerations
        - Security implications
        - Tool recommendations
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        return response
    
    async def _get_architecture_context(self) -> str:
        """Get architecture context from blackboard"""
        messages = self.blackboard.get_messages(self.name, since=time.time() - 3600)
        for msg in reversed(messages):
            if msg.metadata.get("type") == "architecture":
                return str(msg.content)
        return "No architecture context available"
    
    async def _get_security_requirements(self, task: DevelopmentTask) -> str:
        """Get security requirements"""
        if "security" in task.requirements:
            return task.requirements["security"]
        return "Standard network security best practices"
    
    def _share_result(self, task: DevelopmentTask, result: Any):
        """Share task result on blackboard"""
        self.blackboard.post_message(BlackboardMessage(
            id=f"network_{self.name}_{int(time.time())}",
            type=MessageType.RESULT,
            sender=self.name,
            recipient=None,
            content=result,
            metadata={"type": "network_result", "task_id": task.id, "agent_role": self.role.value}
        ))
    
    def _extract_api_style(self, text: str) -> str:
        """Extract recommended API style"""
        for style in self.api_styles.keys():
            if style.lower() in text.lower():
                return style
        return "REST"
    
    def _extract_endpoints(self, text: str) -> List[str]:
        """Extract API endpoints"""
        import re
        endpoints = []
        
        endpoint_pattern = r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/[\w/\-{}]+)'
        matches = re.findall(endpoint_pattern, text)
        endpoints.extend(matches)
        
        path_pattern = r'(?:^|\s)(/api/[\w/\-{}]+)'
        matches = re.findall(path_pattern, text)
        endpoints.extend(matches)
        
        return list(set(endpoints))[:20]
    
    def _extract_security_measures(self, text: str) -> List[str]:
        """Extract security measures"""
        measures = []
        for measure in self.domain_knowledge['security']:
            if measure.lower().replace('-', ' ') in text.lower():
                measures.append(measure)
        return measures
    
    def _extract_protocol(self, text: str) -> str:
        """Extract protocol being implemented"""
        for protocol in self.protocols.keys():
            if protocol.lower() in text.lower():
                return protocol
        return "custom"
    
    def _extract_state_machine(self, text: str) -> List[str]:
        """Extract state machine states"""
        states = []
        state_keywords = ['state', 'phase', 'stage']
        
        lines = text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in state_keywords):
                states.append(line.strip())
        
        return states[:15]
    
    def _extract_code_blocks(self, text: str) -> List[str]:
        """Extract code blocks from response"""
        import re
        code_blocks = re.findall(r'```[\w]*\n(.*?)\n```', text, re.DOTALL)
        return code_blocks
    
    def _extract_patterns(self, text: str) -> List[str]:
        """Extract design patterns"""
        patterns = []
        all_patterns = self.domain_knowledge['patterns'] + self.domain_knowledge['distributed']
        
        for pattern in all_patterns:
            if pattern.lower().replace('-', ' ') in text.lower():
                patterns.append(pattern)
        
        return patterns
    
    def _extract_consistency(self, text: str) -> str:
        """Extract consistency model"""
        consistency_models = ['strong', 'eventual', 'causal', 'sequential']
        
        for model in consistency_models:
            if model in text.lower():
                return model
        
        return "undefined"
    
    def _extract_components(self, text: str) -> List[str]:
        """Extract system components"""
        components = []
        component_keywords = ['service', 'component', 'module', 'microservice', 'server', 'client']
        
        lines = text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in component_keywords):
                components.append(line.strip())
        
        return components[:15]
    
    def _extract_threats(self, text: str) -> List[str]:
        """Extract security threats"""
        threats = []
        threat_keywords = ['threat', 'attack', 'vulnerability', 'risk']
        
        lines = text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in threat_keywords):
                threats.append(line.strip())
        
        return threats[:15]
    
    def _extract_configurations(self, text: str) -> List[str]:
        """Extract configuration blocks"""
        configs = []
        code_blocks = self._extract_code_blocks(text)
        
        for block in code_blocks:
            if any(keyword in block.lower() for keyword in ['config', 'settings', 'rules']):
                configs.append(block)
        
        return configs
    
    def _extract_tools(self, text: str) -> List[str]:
        """Extract diagnostic tools mentioned"""
        tools = []
        all_tools = self.domain_knowledge['diagnostics']
        
        for tool in all_tools:
            if tool in text.lower():
                tools.append(tool)
        
        return tools
    
    def _extract_findings(self, text: str) -> List[str]:
        """Extract diagnostic findings"""
        findings = []
        finding_keywords = ['found', 'detected', 'identified', 'discovered', 'issue', 'problem']
        
        lines = text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in finding_keywords):
                findings.append(line.strip())
        
        return findings[:15]
