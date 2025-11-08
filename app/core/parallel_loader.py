"""
Parallel Component Loader
Load independent components in parallel for faster startup.
"""

import asyncio
import concurrent.futures
import threading
import time
from typing import Callable, Dict, List, Optional, Set

from app.core.component_registry import ComponentMetadata, get_component_registry
from app.core.lazy_loader import get_lazy_loader
from app.logger import logger


class ParallelLoader:
    """
    Load independent components in parallel to optimize startup time.
    Respects dependencies and loads components in optimal order.
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.registry = get_component_registry()
        self.lazy_loader = get_lazy_loader()
        self._lock = threading.RLock()
    
    def load_components_parallel(
        self,
        component_names: List[str],
        on_progress: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, tuple]:
        """
        Load components in parallel where possible.
        
        Args:
            component_names: List of component names to load
            on_progress: Progress callback (component_name, progress_percent)
        
        Returns:
            Dict mapping component name to (success, instance, error) tuple
        """
        start_time = time.time()
        results: Dict[str, tuple] = {}
        
        # Build dependency graph
        dep_graph = self._build_dependency_graph(component_names)
        
        # Get loading order (topological sort)
        load_order = self._topological_sort(dep_graph)
        
        logger.info(f"Loading {len(component_names)} components in parallel")
        logger.debug(f"Load order: {load_order}")
        
        # Load components level by level
        loaded: Set[str] = set()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for level in load_order:
                if not level:
                    continue
                
                # Submit all components in this level for parallel loading
                futures = {}
                for component_name in level:
                    if component_name not in component_names:
                        continue
                    
                    future = executor.submit(
                        self.lazy_loader.load_component,
                        component_name,
                        False,
                        on_progress
                    )
                    futures[future] = component_name
                
                # Wait for all components in this level to complete
                for future in concurrent.futures.as_completed(futures):
                    component_name = futures[future]
                    try:
                        success, instance, error = future.result()
                        results[component_name] = (success, instance, error)
                        
                        if success:
                            loaded.add(component_name)
                            logger.debug(f"Loaded component: {component_name}")
                        else:
                            logger.error(f"Failed to load component: {component_name}")
                    
                    except Exception as e:
                        logger.error(f"Exception loading component '{component_name}': {e}")
                        results[component_name] = (False, None, e)
        
        load_time = time.time() - start_time
        success_count = sum(1 for s, _, _ in results.values() if s)
        
        logger.info(
            f"Parallel loading completed in {load_time:.2f}s: "
            f"{success_count}/{len(component_names)} successful"
        )
        
        return results
    
    async def load_components_parallel_async(
        self,
        component_names: List[str],
        on_progress: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, tuple]:
        """
        Load components in parallel asynchronously.
        
        Args:
            component_names: List of component names to load
            on_progress: Progress callback (component_name, progress_percent)
        
        Returns:
            Dict mapping component name to (success, instance, error) tuple
        """
        start_time = time.time()
        results: Dict[str, tuple] = {}
        
        # Build dependency graph
        dep_graph = self._build_dependency_graph(component_names)
        
        # Get loading order (topological sort)
        load_order = self._topological_sort(dep_graph)
        
        logger.info(f"Loading {len(component_names)} components in parallel (async)")
        logger.debug(f"Load order: {load_order}")
        
        # Load components level by level
        loaded: Set[str] = set()
        
        for level in load_order:
            if not level:
                continue
            
            # Create tasks for all components in this level
            tasks = []
            task_names = []
            
            for component_name in level:
                if component_name not in component_names:
                    continue
                
                task = asyncio.create_task(
                    self.lazy_loader.load_component_async(
                        component_name,
                        False,
                        on_progress
                    )
                )
                tasks.append(task)
                task_names.append(component_name)
            
            # Wait for all tasks in this level to complete
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for component_name, result in zip(task_names, task_results):
                if isinstance(result, Exception):
                    logger.error(f"Exception loading component '{component_name}': {result}")
                    results[component_name] = (False, None, result)
                else:
                    success, instance, error = result
                    results[component_name] = (success, instance, error)
                    
                    if success:
                        loaded.add(component_name)
                        logger.debug(f"Loaded component: {component_name}")
                    else:
                        logger.error(f"Failed to load component: {component_name}")
        
        load_time = time.time() - start_time
        success_count = sum(1 for s, _, _ in results.values() if s)
        
        logger.info(
            f"Parallel loading (async) completed in {load_time:.2f}s: "
            f"{success_count}/{len(component_names)} successful"
        )
        
        return results
    
    def _build_dependency_graph(self, component_names: List[str]) -> Dict[str, Set[str]]:
        """
        Build dependency graph for components.
        
        Returns:
            Dict mapping component name to set of dependencies
        """
        graph = {}
        
        for name in component_names:
            component = self.registry.get_component(name)
            if component:
                graph[name] = set(component.dependencies)
            else:
                graph[name] = set()
        
        return graph
    
    def _topological_sort(self, dep_graph: Dict[str, Set[str]]) -> List[List[str]]:
        """
        Topological sort of dependency graph to determine loading order.
        Returns list of levels where each level can be loaded in parallel.
        
        Args:
            dep_graph: Dict mapping component to its dependencies
        
        Returns:
            List of levels, where each level is a list of components
        """
        # Calculate in-degree for each component
        in_degree = {name: len(deps) for name, deps in dep_graph.items()}
        
        levels: List[List[str]] = []
        processed: Set[str] = set()
        
        while len(processed) < len(dep_graph):
            # Find all components with no unprocessed dependencies
            current_level = []
            for name, degree in in_degree.items():
                if name not in processed and degree == 0:
                    current_level.append(name)
            
            if not current_level:
                # Circular dependency or isolated components
                logger.warning("Circular dependency detected or isolated components")
                # Add remaining components to final level
                remaining = [name for name in dep_graph if name not in processed]
                if remaining:
                    levels.append(remaining)
                break
            
            levels.append(current_level)
            
            # Mark current level as processed
            for name in current_level:
                processed.add(name)
            
            # Update in-degrees
            for name in dep_graph:
                if name not in processed:
                    # Count how many dependencies are still unprocessed
                    unprocessed_deps = [dep for dep in dep_graph[name] if dep not in processed]
                    in_degree[name] = len(unprocessed_deps)
        
        return levels
    
    def get_load_plan(self, component_names: List[str]) -> Dict[str, any]:
        """
        Get a detailed load plan for components.
        
        Args:
            component_names: List of component names
        
        Returns:
            Dict with load plan details
        """
        dep_graph = self._build_dependency_graph(component_names)
        load_order = self._topological_sort(dep_graph)
        
        # Calculate estimated time per level (assuming parallel execution)
        estimated_times = []
        for level in load_order:
            level_components = [
                self.registry.get_component(name)
                for name in level
                if name in component_names
            ]
            # Estimate based on resource requirements (rough heuristic)
            max_time = max(
                (c.resource_requirement_mb / 100.0 for c in level_components if c),
                default=0.5
            )
            estimated_times.append(max_time)
        
        total_estimated_time = sum(estimated_times)
        
        return {
            "component_count": len(component_names),
            "level_count": len(load_order),
            "load_order": load_order,
            "estimated_time_seconds": total_estimated_time,
            "parallelization_factor": len(component_names) / len(load_order) if load_order else 1,
            "dependency_graph": dep_graph
        }
    
    def format_load_plan(self, component_names: List[str]) -> str:
        """Format load plan as human-readable string."""
        plan = self.get_load_plan(component_names)
        
        lines = [
            f"Load Plan for {plan['component_count']} components:",
            f"Estimated time: {plan['estimated_time_seconds']:.1f}s",
            f"Parallelization factor: {plan['parallelization_factor']:.1f}x",
            "",
            "Loading sequence:"
        ]
        
        for i, level in enumerate(plan['load_order'], 1):
            if level:
                lines.append(f"  Level {i} (parallel):")
                for component_name in level:
                    component = self.registry.get_component(component_name)
                    if component:
                        lines.append(
                            f"    - {component_name} "
                            f"({component.resource_requirement_mb}MB, "
                            f"deps: {', '.join(component.dependencies) if component.dependencies else 'none'})"
                        )
        
        return "\n".join(lines)


# Global singleton
_parallel_loader = None


def get_parallel_loader() -> ParallelLoader:
    """Get the global parallel loader singleton."""
    global _parallel_loader
    if _parallel_loader is None:
        _parallel_loader = ParallelLoader()
    return _parallel_loader
