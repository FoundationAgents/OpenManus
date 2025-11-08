"""
Low-Level Systems Specialist Agent

Specialized agent for low-level system programming:
- System programming and kernel development
- Embedded systems and microcontrollers
- Assembly language programming
- Memory management and optimization
- Hardware interaction and drivers
- Real-time systems
- Boot loaders and firmware
"""

import re
import time
from typing import Dict, List, Optional, Any
from app.flow.multi_agent_environment import SpecializedAgent, DevelopmentTask, AgentRole, BlackboardMessage, MessageType, TaskPriority
from app.logger import logger


class LowLevelAgent(SpecializedAgent):
    """Low-Level Systems Expert with expertise in system programming and hardware interaction"""
    
    def __init__(self, agent_id: str, blackboard, **kwargs):
        super().__init__(AgentRole.LOW_LEVEL, blackboard, name=agent_id, **kwargs)
        
        self.programming_languages = {
            "C": {"level": "low", "use_cases": ["kernel", "drivers", "embedded"]},
            "C++": {"level": "low-mid", "use_cases": ["systems", "embedded", "performance"]},
            "Assembly": {"level": "lowest", "use_cases": ["boot", "critical-sections", "optimization"]},
            "Rust": {"level": "low-mid", "use_cases": ["systems", "safe-low-level", "embedded"]},
        }
        
        self.architectures = {
            "x86": {"bits": 32, "registers": ["eax", "ebx", "ecx", "edx"], "addressing": "complex"},
            "x86_64": {"bits": 64, "registers": ["rax", "rbx", "rcx", "rdx"], "addressing": "complex"},
            "ARM": {"bits": 32, "registers": ["r0-r15"], "addressing": "load-store"},
            "ARM64": {"bits": 64, "registers": ["x0-x30"], "addressing": "load-store"},
            "RISC-V": {"bits": "32/64", "registers": ["x0-x31"], "addressing": "load-store"},
        }
        
        self.domain_knowledge = {
            "memory_management": [
                "paging",
                "segmentation",
                "virtual-memory",
                "memory-mapping",
                "DMA",
                "cache-optimization"
            ],
            "synchronization": [
                "mutexes",
                "semaphores",
                "spinlocks",
                "atomic-operations",
                "memory-barriers"
            ],
            "hardware_interfaces": [
                "MMIO",
                "port-IO",
                "interrupts",
                "DMA",
                "device-drivers"
            ],
            "optimization": [
                "cache-locality",
                "SIMD",
                "branch-prediction",
                "loop-unrolling",
                "inline-assembly"
            ]
        }
        
        self.embedded_platforms = {
            "Arduino": {"arch": "AVR/ARM", "language": "C/C++"},
            "ESP32": {"arch": "Xtensa", "language": "C/C++"},
            "STM32": {"arch": "ARM Cortex-M", "language": "C/C++"},
            "Raspberry Pi Pico": {"arch": "ARM Cortex-M0+", "language": "C/C++/Python"},
        }
        
        self.kernel_concepts = [
            "process-scheduling",
            "memory-management",
            "file-systems",
            "device-drivers",
            "interrupt-handling",
            "system-calls"
        ]
        
        self.allowed_tools = [
            "bash",
            "python_execute",
            "str_replace_editor",
            "browser",
            "web_search"
        ]
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute low-level systems specific tasks"""
        self.add_thought(f"Analyzing low-level systems task: {task.title}")
        
        task_type = self._classify_task(task)
        self.add_thought(f"Task classified as: {task_type}")
        
        context = await self._gather_domain_context(task, task_type)
        
        if task_type == "kernel_development":
            result = await self._handle_kernel_development(task, context)
        elif task_type == "embedded_systems":
            result = await self._handle_embedded_systems(task, context)
        elif task_type == "driver_development":
            result = await self._handle_driver_development(task, context)
        elif task_type == "memory_optimization":
            result = await self._handle_memory_optimization(task, context)
        elif task_type == "assembly_programming":
            result = await self._handle_assembly_programming(task, context)
        else:
            result = await self._handle_general_low_level(task, context)
        
        self._share_result(task, result)
        
        return f"Low-level systems task completed: {task.title}"
    
    def _classify_task(self, task: DevelopmentTask) -> str:
        """Classify the type of low-level task"""
        description_lower = task.description.lower()
        
        if any(term in description_lower for term in ["kernel", "operating system", "os"]):
            return "kernel_development"
        elif any(term in description_lower for term in ["embedded", "microcontroller", "arduino", "esp32", "firmware"]):
            return "embedded_systems"
        elif any(term in description_lower for term in ["driver", "device", "hardware interface"]):
            return "driver_development"
        elif any(term in description_lower for term in ["memory", "cache", "optimization", "performance"]):
            return "memory_optimization"
        elif any(term in description_lower for term in ["assembly", "asm", "x86", "arm"]):
            return "assembly_programming"
        else:
            return "general"
    
    async def _gather_domain_context(self, task: DevelopmentTask, task_type: str) -> Dict[str, Any]:
        """Gather relevant domain-specific context"""
        self.add_thought(f"Gathering domain context for {task_type}")
        
        query = f"low-level systems {task_type} {task.description}"
        knowledge_items = await self.retrieve_knowledge(query, top_k=5, strategy="balanced")
        
        architecture = await self._get_target_architecture(task)
        performance_reqs = await self._get_performance_requirements(task)
        
        return {
            "task_type": task_type,
            "knowledge_base": knowledge_items,
            "architecture": architecture,
            "performance_requirements": performance_reqs,
            "domain_knowledge": self.domain_knowledge,
            "languages": self.programming_languages
        }
    
    async def _handle_kernel_development(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle kernel development tasks"""
        self.add_thought("Handling kernel development task")
        
        security_collab = await self.collaborate(
            AgentRole.SECURITY,
            f"What security considerations are critical for kernel-level code: {task.description}?"
        )
        
        prompt = f"""
        As a Kernel Development Expert:
        
        Task: {task.description}
        Target Architecture: {context['architecture']}
        Kernel Concepts: {self.kernel_concepts}
        Security Requirements: {security_collab}
        
        Provide:
        1. Kernel module/subsystem design
        2. Data structures and algorithms
        3. Implementation in C (with inline assembly if needed)
        4. Synchronization and locking strategy
        5. Error handling and recovery
        6. Memory management considerations
        7. Performance optimization
        8. Security hardening measures
        9. Testing strategy (kernel debugging)
        10. Documentation and code comments
        
        Follow kernel coding standards (e.g., Linux Kernel coding style).
        Ensure thread-safety and proper resource management.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "kernel_development",
            "implementation": response,
            "subsystems": self._extract_subsystems(response),
            "synchronization": self._extract_synchronization(response),
            "code": self._extract_code_blocks(response)
        }
    
    async def _handle_embedded_systems(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle embedded systems tasks"""
        self.add_thought("Handling embedded systems task")
        
        perf_collab = await self.collaborate(
            AgentRole.PERFORMANCE,
            f"What are the performance constraints for embedded system: {task.description}?"
        )
        
        prompt = f"""
        As an Embedded Systems Expert:
        
        Task: {task.description}
        Target Platform: {self._select_embedded_platform(task.description)}
        Architecture: {context['architecture']}
        Performance Constraints: {perf_collab}
        
        Provide:
        1. Hardware requirements and component selection
        2. Firmware architecture design
        3. Peripheral initialization and configuration
        4. Main control loop implementation
        5. Interrupt service routines (ISRs)
        6. Power management strategy
        7. Memory footprint optimization
        8. Real-time constraints handling
        9. Debugging and testing approach
        10. Code with hardware-specific comments
        
        Optimize for:
        - Low power consumption
        - Small memory footprint
        - Real-time responsiveness
        - Reliability and fault tolerance
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "embedded_systems",
            "implementation": response,
            "platform": self._select_embedded_platform(task.description),
            "peripherals": self._extract_peripherals(response),
            "power_optimization": self._extract_power_info(response)
        }
    
    async def _handle_driver_development(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle driver development tasks"""
        self.add_thought("Handling driver development task")
        
        security_collab = await self.collaborate(
            AgentRole.SECURITY,
            f"What security measures are needed for device driver: {task.description}?"
        )
        
        prompt = f"""
        As a Device Driver Expert:
        
        Task: {task.description}
        Target Architecture: {context['architecture']}
        Hardware Interfaces: {context['domain_knowledge']['hardware_interfaces']}
        Security Requirements: {security_collab}
        
        Provide:
        1. Driver architecture (character/block/network)
        2. Device initialization and probing
        3. File operations implementation (open, read, write, ioctl, close)
        4. Interrupt handling
        5. DMA setup if applicable
        6. Memory mapping for user space
        7. Power management callbacks
        8. Error handling and cleanup
        9. Testing and debugging strategy
        10. Makefile and build configuration
        
        Follow OS-specific driver framework (Linux kernel module, Windows WDM, etc.).
        Ensure proper resource cleanup and error handling.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "driver_development",
            "implementation": response,
            "driver_type": self._extract_driver_type(response),
            "operations": self._extract_operations(response),
            "code": self._extract_code_blocks(response)
        }
    
    async def _handle_memory_optimization(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle memory optimization tasks"""
        self.add_thought("Handling memory optimization task")
        
        perf_collab = await self.collaborate(
            AgentRole.PERFORMANCE,
            f"What are the memory performance targets for: {task.description}?"
        )
        
        prompt = f"""
        As a Memory Optimization Expert:
        
        Task: {task.description}
        Architecture: {context['architecture']}
        Optimization Techniques: {context['domain_knowledge']['optimization']}
        Memory Management: {context['domain_knowledge']['memory_management']}
        Performance Targets: {perf_collab}
        
        Provide:
        1. Memory profiling and analysis strategy
        2. Memory layout optimization
        3. Cache optimization techniques
        4. Memory allocation strategy
        5. Data structure optimization
        6. Memory access pattern optimization
        7. SIMD optimization if applicable
        8. Assembly optimization for hot paths
        9. Before/after performance metrics
        10. Testing and validation approach
        
        Focus on:
        - Cache line alignment
        - Reducing cache misses
        - Memory bandwidth optimization
        - Minimizing TLB misses
        - Structure packing
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "memory_optimization",
            "implementation": response,
            "techniques_applied": self._extract_optimization_techniques(response),
            "performance_impact": self._extract_performance_metrics(response)
        }
    
    async def _handle_assembly_programming(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle assembly programming tasks"""
        self.add_thought("Handling assembly programming task")
        
        reveng_collab = await self.collaborate(
            AgentRole.REVERSE_ENGINEERING,
            f"What assembly techniques are relevant for: {task.description}?"
        )
        
        prompt = f"""
        As an Assembly Programming Expert:
        
        Task: {task.description}
        Target Architecture: {context['architecture']}
        Assembly Insights: {reveng_collab}
        
        Provide:
        1. Assembly implementation with detailed comments
        2. Register allocation strategy
        3. Instruction selection and optimization
        4. Calling convention compliance
        5. Stack frame management
        6. SIMD instructions if applicable
        7. Branch optimization
        8. Inline assembly integration with C/C++
        9. Testing and debugging approach
        10. Performance analysis
        
        Include:
        - Full assembly listing with comments
        - Mixed C and assembly code
        - Explanation of optimization decisions
        - Comparison with compiler-generated code
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "assembly_programming",
            "implementation": response,
            "architecture": context['architecture'],
            "instructions_used": self._extract_instructions(response),
            "code": self._extract_code_blocks(response)
        }
    
    async def _handle_general_low_level(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle general low-level tasks"""
        self.add_thought("Handling general low-level task")
        
        prompt = f"""
        As a Low-Level Systems Expert:
        
        Task: {task.description}
        Context: {context}
        
        Provide a comprehensive low-level implementation following best practices
        for system programming, performance, and reliability.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "general",
            "implementation": response
        }
    
    async def _answer_question(self, question: str) -> str:
        """Answer low-level systems related questions"""
        self.add_thought(f"Answering question: {question}")
        
        prompt = f"""
        As a Low-Level Systems Expert, answer this question: {question}
        
        Provide:
        - Detailed technical explanation
        - Assembly or C code examples
        - Architecture-specific considerations
        - Performance implications
        - Best practices
        - Common pitfalls
        - Hardware considerations
        - References to specifications
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        return response
    
    async def _get_target_architecture(self, task: DevelopmentTask) -> str:
        """Determine target architecture from task"""
        description_lower = task.description.lower()
        
        for arch in self.architectures.keys():
            if arch.lower() in description_lower:
                return arch
        
        if "requirements" in task.requirements and "architecture" in task.requirements["requirements"]:
            return task.requirements["requirements"]["architecture"]
        
        return "x86_64"
    
    async def _get_performance_requirements(self, task: DevelopmentTask) -> str:
        """Get performance requirements"""
        if "performance" in task.requirements:
            return task.requirements["performance"]
        
        return "Standard performance, optimize for reliability and maintainability"
    
    def _share_result(self, task: DevelopmentTask, result: Any):
        """Share task result on blackboard"""
        self.blackboard.post_message(BlackboardMessage(
            id=f"lowlevel_{self.name}_{int(time.time())}",
            type=MessageType.RESULT,
            sender=self.name,
            recipient=None,
            content=result,
            metadata={"type": "low_level_result", "task_id": task.id, "agent_role": self.role.value}
        ))
    
    def _select_embedded_platform(self, description: str) -> str:
        """Select embedded platform based on description"""
        description_lower = description.lower()
        
        for platform in self.embedded_platforms.keys():
            if platform.lower() in description_lower:
                return platform
        
        return "Generic Embedded Platform"
    
    def _extract_code_blocks(self, text: str) -> List[str]:
        """Extract code blocks from response"""
        import re
        code_blocks = re.findall(r'```[\w]*\n(.*?)\n```', text, re.DOTALL)
        return code_blocks
    
    def _extract_subsystems(self, text: str) -> List[str]:
        """Extract kernel subsystems from text"""
        subsystems = []
        for concept in self.kernel_concepts:
            if concept.replace('-', ' ') in text.lower():
                subsystems.append(concept)
        return subsystems
    
    def _extract_synchronization(self, text: str) -> List[str]:
        """Extract synchronization mechanisms"""
        sync_mechs = []
        for mech in self.domain_knowledge['synchronization']:
            if mech.replace('-', ' ') in text.lower():
                sync_mechs.append(mech)
        return sync_mechs
    
    def _extract_peripherals(self, text: str) -> List[str]:
        """Extract peripheral mentions"""
        peripherals = []
        common_peripherals = ['uart', 'spi', 'i2c', 'gpio', 'adc', 'pwm', 'timer', 'usb']
        
        for periph in common_peripherals:
            if periph in text.lower():
                peripherals.append(periph.upper())
        
        return peripherals
    
    def _extract_power_info(self, text: str) -> str:
        """Extract power management information"""
        lines = text.split('\n')
        power_lines = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ['power', 'sleep', 'energy', 'battery']):
                power_lines.append(line)
        
        return '\n'.join(power_lines[:10])
    
    def _extract_driver_type(self, text: str) -> str:
        """Extract driver type"""
        if 'character' in text.lower():
            return "character"
        elif 'block' in text.lower():
            return "block"
        elif 'network' in text.lower():
            return "network"
        else:
            return "generic"
    
    def _extract_operations(self, text: str) -> List[str]:
        """Extract file operations"""
        operations = []
        common_ops = ['open', 'close', 'read', 'write', 'ioctl', 'mmap', 'poll']
        
        for op in common_ops:
            if op in text.lower():
                operations.append(op)
        
        return operations
    
    def _extract_optimization_techniques(self, text: str) -> List[str]:
        """Extract optimization techniques"""
        techniques = []
        all_techniques = self.domain_knowledge['optimization'] + self.domain_knowledge['memory_management']
        
        for tech in all_techniques:
            if tech.replace('-', ' ') in text.lower():
                techniques.append(tech)
        
        return techniques
    
    def _extract_performance_metrics(self, text: str) -> Dict[str, str]:
        """Extract performance metrics"""
        import re
        metrics = {}
        
        metric_pattern = r'(latency|throughput|bandwidth|cache|miss|hit).*?(\d+\.?\d*)\s*(ms|us|ns|MB/s|%)?'
        matches = re.findall(metric_pattern, text.lower())
        
        for metric, value, unit in matches[:10]:
            metrics[metric] = f"{value}{unit}"
        
        return metrics
    
    def _extract_instructions(self, text: str) -> List[str]:
        """Extract assembly instructions mentioned"""
        instructions = []
        common_instructions = [
            'mov', 'add', 'sub', 'mul', 'div', 'push', 'pop', 'jmp', 'call', 'ret',
            'cmp', 'test', 'and', 'or', 'xor', 'shl', 'shr', 'lea'
        ]
        
        for instr in common_instructions:
            if re.search(rf'\b{instr}\b', text.lower()):
                instructions.append(instr.upper())
        
        return list(set(instructions))
