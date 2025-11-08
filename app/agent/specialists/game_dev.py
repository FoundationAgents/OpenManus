"""
Game Development Specialist Agent

Specialized agent for game development tasks including:
- Game engine integration (Unity, Unreal, Godot)
- Graphics programming (shaders, rendering)
- Game design patterns and architecture
- Physics and collision detection
- Performance optimization for real-time applications
"""

import time
from typing import Dict, List, Optional, Any
from app.flow.multi_agent_environment import SpecializedAgent, DevelopmentTask, AgentRole, BlackboardMessage, MessageType, TaskPriority
from app.logger import logger


class GameDevAgent(SpecializedAgent):
    """Game Development Specialist with expertise in game engines and real-time graphics"""
    
    def __init__(self, agent_id: str, blackboard, **kwargs):
        super().__init__(AgentRole.GAME_DEV, blackboard, name=agent_id, **kwargs)
        
        self.game_engines = {
            "unity": {
                "languages": ["C#"],
                "features": ["cross-platform", "2D/3D", "asset-store", "editor-extensions"],
                "docs": "https://docs.unity3d.com"
            },
            "unreal": {
                "languages": ["C++", "Blueprint"],
                "features": ["AAA-graphics", "nanite", "lumen", "metahumans"],
                "docs": "https://docs.unrealengine.com"
            },
            "godot": {
                "languages": ["GDScript", "C#", "C++"],
                "features": ["open-source", "lightweight", "node-based"],
                "docs": "https://docs.godotengine.org"
            }
        }
        
        self.domain_knowledge = {
            "rendering": ["DirectX", "OpenGL", "Vulkan", "Metal", "WebGL"],
            "patterns": ["Entity-Component-System", "Object-Pooling", "State-Machine", "Command-Pattern"],
            "physics": ["collision-detection", "rigid-body-dynamics", "raycasting", "physics-materials"],
            "optimization": ["LOD", "occlusion-culling", "batching", "profiling", "memory-management"]
        }
        
        self.allowed_tools = [
            "bash",
            "python_execute",
            "str_replace_editor",
            "browser",
            "web_search",
            "crawl4ai",
            "http_request"
        ]
        
        self.knowledge_sources = [
            "game-engine-documentation",
            "graphics-programming-patterns",
            "real-time-rendering-techniques",
            "game-design-patterns"
        ]
    
    async def _execute_role_specific_task(self, task: DevelopmentTask) -> str:
        """Execute game development specific tasks"""
        self.add_thought(f"Analyzing game development task: {task.title}")
        
        task_type = self._classify_task(task)
        self.add_thought(f"Task classified as: {task_type}")
        
        context = await self._gather_domain_context(task, task_type)
        
        if task_type == "engine_integration":
            result = await self._handle_engine_integration(task, context)
        elif task_type == "graphics_programming":
            result = await self._handle_graphics_programming(task, context)
        elif task_type == "game_mechanics":
            result = await self._handle_game_mechanics(task, context)
        elif task_type == "performance_optimization":
            result = await self._handle_performance_optimization(task, context)
        else:
            result = await self._handle_general_game_dev(task, context)
        
        self._share_result(task, result)
        
        return f"Game development task completed: {task.title}"
    
    def _classify_task(self, task: DevelopmentTask) -> str:
        """Classify the type of game development task"""
        description_lower = task.description.lower()
        
        if any(engine in description_lower for engine in ["unity", "unreal", "godot", "engine"]):
            return "engine_integration"
        elif any(term in description_lower for term in ["shader", "render", "graphics", "material", "lighting"]):
            return "graphics_programming"
        elif any(term in description_lower for term in ["mechanic", "gameplay", "physics", "collision", "movement"]):
            return "game_mechanics"
        elif any(term in description_lower for term in ["optimize", "performance", "fps", "memory", "profiling"]):
            return "performance_optimization"
        else:
            return "general"
    
    async def _gather_domain_context(self, task: DevelopmentTask, task_type: str) -> Dict[str, Any]:
        """Gather relevant domain-specific context using knowledge retrieval"""
        self.add_thought(f"Gathering domain context for {task_type}")
        
        query = f"{task_type} {task.description}"
        knowledge_items = await self.retrieve_knowledge(query, top_k=5, strategy="balanced")
        
        architecture_msg = await self._get_architecture_context()
        performance_reqs = await self._get_performance_requirements(task)
        
        return {
            "task_type": task_type,
            "knowledge_base": knowledge_items,
            "architecture": architecture_msg,
            "performance_requirements": performance_reqs,
            "engines": self.game_engines,
            "domain_knowledge": self.domain_knowledge
        }
    
    async def _handle_engine_integration(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle game engine integration tasks"""
        self.add_thought("Handling engine integration task")
        
        prompt = f"""
        As a Game Development Expert, implement the following engine integration:
        
        Task: {task.description}
        Architecture Context: {context.get('architecture', 'N/A')}
        Available Engines: {list(self.game_engines.keys())}
        
        Provide:
        1. Recommended game engine and rationale
        2. Project structure and organization
        3. Core systems setup (input, rendering, audio, physics)
        4. Asset pipeline configuration
        5. Build and deployment setup
        6. Code examples for key integrations
        7. Performance considerations
        8. Best practices and common pitfalls
        
        Focus on scalability, maintainability, and performance.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "engine_integration",
            "implementation": response,
            "engine_recommendations": self._extract_engine_recommendations(response),
            "code_samples": self._extract_code_blocks(response)
        }
    
    async def _handle_graphics_programming(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle graphics programming tasks"""
        self.add_thought("Handling graphics programming task")
        
        security_collab = await self.collaborate(
            AgentRole.SECURITY,
            "What security considerations should be included in shader and graphics code?"
        )
        
        prompt = f"""
        As a Graphics Programming Expert, implement the following:
        
        Task: {task.description}
        Rendering APIs: {context['domain_knowledge']['rendering']}
        Performance Requirements: {context.get('performance_requirements', 'Standard')}
        Security Considerations: {security_collab}
        
        Provide:
        1. Shader implementation (vertex, fragment, compute as needed)
        2. Rendering pipeline setup
        3. Material and texture handling
        4. Lighting calculations
        5. Performance optimization techniques
        6. GPU profiling recommendations
        7. Cross-platform compatibility notes
        8. Code with detailed comments
        
        Use modern graphics API best practices.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "graphics_programming",
            "implementation": response,
            "shaders": self._extract_shader_code(response),
            "rendering_setup": self._extract_rendering_setup(response)
        }
    
    async def _handle_game_mechanics(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle game mechanics implementation"""
        self.add_thought("Handling game mechanics task")
        
        designer_collab = await self.collaborate(
            AgentRole.UI_UX_DESIGNER,
            f"What user experience considerations should be included for: {task.description}?"
        )
        
        prompt = f"""
        As a Game Mechanics Expert, implement the following:
        
        Task: {task.description}
        Game Design Patterns: {context['domain_knowledge']['patterns']}
        Physics Systems: {context['domain_knowledge']['physics']}
        UX Considerations: {designer_collab}
        
        Provide:
        1. Core mechanic implementation with design pattern
        2. State management and transitions
        3. Input handling and player feedback
        4. Physics integration if applicable
        5. Edge case handling
        6. Testing strategy for mechanics
        7. Tuning parameters and configuration
        8. Performance impact analysis
        
        Ensure responsive, smooth gameplay feel.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "game_mechanics",
            "implementation": response,
            "patterns_used": self._extract_patterns(response),
            "tuning_parameters": self._extract_parameters(response)
        }
    
    async def _handle_performance_optimization(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle performance optimization tasks"""
        self.add_thought("Handling performance optimization task")
        
        perf_collab = await self.collaborate(
            AgentRole.PERFORMANCE,
            f"What are the target performance metrics for: {task.description}?"
        )
        
        prompt = f"""
        As a Game Performance Optimization Expert, optimize the following:
        
        Task: {task.description}
        Optimization Techniques: {context['domain_knowledge']['optimization']}
        Performance Targets: {perf_collab}
        
        Provide:
        1. Profiling strategy and hotspot identification
        2. CPU optimization techniques
        3. GPU optimization techniques
        4. Memory optimization
        5. Asset optimization (LODs, compression, streaming)
        6. Code-level optimizations
        7. Profiler-specific recommendations
        8. Before/after performance metrics
        9. Monitoring and continuous optimization plan
        
        Target 60 FPS minimum on target platforms.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "performance_optimization",
            "implementation": response,
            "optimization_techniques": self._extract_optimization_techniques(response),
            "profiling_recommendations": self._extract_profiling_info(response)
        }
    
    async def _handle_general_game_dev(self, task: DevelopmentTask, context: Dict[str, Any]) -> str:
        """Handle general game development tasks"""
        self.add_thought("Handling general game development task")
        
        prompt = f"""
        As a Game Development Expert, implement the following:
        
        Task: {task.description}
        Context: {context}
        
        Provide a comprehensive solution following game development best practices,
        considering performance, maintainability, and player experience.
        """
        
        response = await self.llm.ask([{"role": "user", "content": prompt}])
        
        return {
            "type": "general",
            "implementation": response
        }
    
    async def _answer_question(self, question: str) -> str:
        """Answer game development related questions"""
        self.add_thought(f"Answering question: {question}")
        
        prompt = f"""
        As a Game Development Specialist, answer this question: {question}
        
        Provide:
        - Clear technical explanation
        - Game engine specific considerations
        - Code examples if applicable
        - Best practices from industry
        - Common pitfalls and solutions
        - Performance implications
        - Alternative approaches
        
        Reference specific engines (Unity, Unreal, Godot) where relevant.
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
    
    async def _get_performance_requirements(self, task: DevelopmentTask) -> str:
        """Get performance requirements from task or blackboard"""
        if "performance" in task.requirements:
            return task.requirements["performance"]
        
        messages = self.blackboard.get_messages(self.name, since=time.time() - 3600)
        for msg in reversed(messages):
            if msg.metadata.get("type") == "performance_requirements":
                return str(msg.content)
        return "60 FPS target, optimize for memory and GPU usage"
    
    def _share_result(self, task: DevelopmentTask, result: Any):
        """Share task result on blackboard"""
        self.blackboard.post_message(BlackboardMessage(
            id=f"gamedev_{self.name}_{int(time.time())}",
            type=MessageType.RESULT,
            sender=self.name,
            recipient=None,
            content=result,
            metadata={"type": "game_dev_result", "task_id": task.id, "agent_role": self.role.value}
        ))
    
    def _extract_engine_recommendations(self, text: str) -> List[str]:
        """Extract game engine recommendations from text"""
        recommendations = []
        for engine in self.game_engines.keys():
            if engine.lower() in text.lower():
                recommendations.append(engine)
        return recommendations
    
    def _extract_code_blocks(self, text: str) -> List[str]:
        """Extract code blocks from response"""
        import re
        code_blocks = re.findall(r'```[\w]*\n(.*?)\n```', text, re.DOTALL)
        return code_blocks
    
    def _extract_shader_code(self, text: str) -> List[str]:
        """Extract shader code from response"""
        shaders = []
        code_blocks = self._extract_code_blocks(text)
        for block in code_blocks:
            if any(keyword in block.lower() for keyword in ['vertex', 'fragment', 'hlsl', 'glsl', 'shader']):
                shaders.append(block)
        return shaders
    
    def _extract_rendering_setup(self, text: str) -> str:
        """Extract rendering setup information"""
        lines = text.split('\n')
        setup_lines = []
        in_setup = False
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ['rendering', 'pipeline', 'setup', 'configuration']):
                in_setup = True
            if in_setup and line.strip():
                setup_lines.append(line)
                if len(setup_lines) > 20:
                    break
        
        return '\n'.join(setup_lines)
    
    def _extract_patterns(self, text: str) -> List[str]:
        """Extract design patterns from text"""
        patterns = []
        for pattern in self.domain_knowledge['patterns']:
            if pattern.lower().replace('-', ' ') in text.lower():
                patterns.append(pattern)
        return patterns
    
    def _extract_parameters(self, text: str) -> Dict[str, str]:
        """Extract tuning parameters from text"""
        import re
        params = {}
        param_pattern = r'(\w+)\s*[=:]\s*([0-9.]+)'
        matches = re.findall(param_pattern, text)
        for name, value in matches[:10]:
            params[name] = value
        return params
    
    def _extract_optimization_techniques(self, text: str) -> List[str]:
        """Extract optimization techniques from text"""
        techniques = []
        for tech in self.domain_knowledge['optimization']:
            if tech.lower().replace('-', ' ') in text.lower():
                techniques.append(tech)
        return techniques
    
    def _extract_profiling_info(self, text: str) -> str:
        """Extract profiling information"""
        lines = text.split('\n')
        profiling_lines = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ['profil', 'measure', 'metric', 'benchmark']):
                profiling_lines.append(line)
        
        return '\n'.join(profiling_lines[:15])
