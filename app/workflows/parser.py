"""Parser for workflow definitions from YAML/JSON"""
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Union

from app.workflows.models import (
    Condition,
    LoopConfig,
    NodeType,
    RetryPolicy,
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowNode,
)


class WorkflowParser:
    """Parse workflow definitions from YAML or JSON"""
    
    @staticmethod
    def parse_file(file_path: Union[str, Path]) -> WorkflowDefinition:
        """Parse workflow from file"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Determine file type and parse
        if file_path.suffix in ['.yaml', '.yml']:
            data = yaml.safe_load(content)
        elif file_path.suffix == '.json':
            data = json.loads(content)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        return WorkflowParser.parse_dict(data)
    
    @staticmethod
    def parse_dict(data: Dict[str, Any]) -> WorkflowDefinition:
        """Parse workflow from dictionary"""
        # Parse metadata
        metadata_data = data.get('metadata', {})
        metadata = WorkflowMetadata(
            name=metadata_data.get('name', 'Unnamed Workflow'),
            description=metadata_data.get('description'),
            version=metadata_data.get('version', '1.0.0'),
            author=metadata_data.get('author'),
            tags=metadata_data.get('tags', [])
        )
        
        # Parse nodes
        nodes = []
        for node_data in data.get('nodes', []):
            node = WorkflowParser._parse_node(node_data)
            nodes.append(node)
        
        # Parse workflow-level settings
        start_node = data.get('start_node')
        if not start_node:
            raise ValueError("Workflow must specify a start_node")
        
        end_nodes = data.get('end_nodes', [])
        global_timeout = data.get('global_timeout')
        variables = data.get('variables', {})
        
        return WorkflowDefinition(
            metadata=metadata,
            nodes=nodes,
            start_node=start_node,
            end_nodes=end_nodes,
            global_timeout=global_timeout,
            variables=variables
        )
    
    @staticmethod
    def _parse_node(node_data: Dict[str, Any]) -> WorkflowNode:
        """Parse a single workflow node"""
        node_id = node_data.get('id')
        if not node_id:
            raise ValueError("Node must have an 'id' field")
        
        # Parse node type
        node_type_str = node_data.get('type', 'agent')
        try:
            node_type = NodeType(node_type_str)
        except ValueError:
            raise ValueError(f"Invalid node type: {node_type_str}")
        
        # Parse retry policy
        retry_policy = None
        if 'retry_policy' in node_data:
            retry_data = node_data['retry_policy']
            retry_policy = RetryPolicy(
                max_attempts=retry_data.get('max_attempts', 3),
                backoff_factor=retry_data.get('backoff_factor', 2.0),
                initial_delay=retry_data.get('initial_delay', 1.0),
                max_delay=retry_data.get('max_delay', 60.0),
                retry_on_errors=retry_data.get('retry_on_errors')
            )
        
        # Parse condition
        condition = None
        if 'condition' in node_data:
            cond_data = node_data['condition']
            if isinstance(cond_data, str):
                condition = Condition(expression=cond_data)
            else:
                condition = Condition(
                    expression=cond_data.get('expression'),
                    context_vars=cond_data.get('context_vars', [])
                )
        
        # Parse loop configuration
        loop = None
        if 'loop' in node_data:
            loop_data = node_data['loop']
            loop = LoopConfig(
                type=loop_data.get('type'),
                items=loop_data.get('items'),
                condition=loop_data.get('condition'),
                max_iterations=loop_data.get('max_iterations', 100),
                item_var=loop_data.get('item_var', 'item')
            )
        
        return WorkflowNode(
            id=node_id,
            type=node_type,
            name=node_data.get('name', node_id),
            description=node_data.get('description'),
            target=node_data.get('target'),
            params=node_data.get('params', {}),
            depends_on=node_data.get('depends_on', []),
            condition=condition,
            loop=loop,
            retry_policy=retry_policy,
            on_failure=node_data.get('on_failure'),
            timeout=node_data.get('timeout')
        )
    
    @staticmethod
    def to_dict(definition: WorkflowDefinition) -> Dict[str, Any]:
        """Convert workflow definition to dictionary"""
        return {
            'metadata': {
                'name': definition.metadata.name,
                'description': definition.metadata.description,
                'version': definition.metadata.version,
                'author': definition.metadata.author,
                'tags': definition.metadata.tags
            },
            'nodes': [
                WorkflowParser._node_to_dict(node)
                for node in definition.nodes
            ],
            'start_node': definition.start_node,
            'end_nodes': definition.end_nodes,
            'global_timeout': definition.global_timeout,
            'variables': definition.variables
        }
    
    @staticmethod
    def _node_to_dict(node: WorkflowNode) -> Dict[str, Any]:
        """Convert node to dictionary"""
        result = {
            'id': node.id,
            'type': node.type.value,
            'name': node.name,
            'description': node.description,
            'target': node.target,
            'params': node.params,
            'depends_on': node.depends_on,
            'timeout': node.timeout,
            'on_failure': node.on_failure
        }
        
        if node.condition:
            result['condition'] = {
                'expression': node.condition.expression,
                'context_vars': node.condition.context_vars
            }
        
        if node.loop:
            result['loop'] = {
                'type': node.loop.type,
                'items': node.loop.items,
                'condition': node.loop.condition,
                'max_iterations': node.loop.max_iterations,
                'item_var': node.loop.item_var
            }
        
        if node.retry_policy:
            result['retry_policy'] = {
                'max_attempts': node.retry_policy.max_attempts,
                'backoff_factor': node.retry_policy.backoff_factor,
                'initial_delay': node.retry_policy.initial_delay,
                'max_delay': node.retry_policy.max_delay,
                'retry_on_errors': node.retry_policy.retry_on_errors
            }
        
        return result
    
    @staticmethod
    def to_yaml(definition: WorkflowDefinition) -> str:
        """Convert workflow definition to YAML string"""
        data = WorkflowParser.to_dict(definition)
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
    
    @staticmethod
    def to_json(definition: WorkflowDefinition, indent: int = 2) -> str:
        """Convert workflow definition to JSON string"""
        data = WorkflowParser.to_dict(definition)
        return json.dumps(data, indent=indent)
