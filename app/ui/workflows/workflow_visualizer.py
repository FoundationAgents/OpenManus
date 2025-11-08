"""Workflow DAG visualization using QGraphicsView"""
from typing import Dict, Optional

try:
    from PyQt6.QtCore import Qt, QPointF, QRectF
    from PyQt6.QtGui import QBrush, QColor, QPen, QPainter, QFont
    from PyQt6.QtWidgets import (
        QGraphicsView,
        QGraphicsScene,
        QGraphicsRectItem,
        QGraphicsTextItem,
        QGraphicsLineItem,
        QGraphicsEllipseItem,
        QWidget,
        QVBoxLayout,
    )
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from app.workflows.dag import WorkflowDAG
from app.workflows.models import NodeStatus, NodeType, WorkflowExecutionState


if PYQT_AVAILABLE:
    class NodeGraphicsItem(QGraphicsRectItem):
        """Graphics item representing a workflow node"""
        
        NODE_WIDTH = 150
        NODE_HEIGHT = 60
        
        # Colors for different node types
        TYPE_COLORS = {
            NodeType.AGENT: QColor(100, 150, 255),
            NodeType.TOOL: QColor(150, 200, 100),
            NodeType.SERVICE: QColor(255, 180, 100),
            NodeType.CONDITION: QColor(255, 200, 150),
            NodeType.LOOP: QColor(200, 150, 255),
            NodeType.PARALLEL: QColor(180, 180, 180),
            NodeType.SEQUENCE: QColor(200, 200, 200),
        }
        
        # Colors for different statuses
        STATUS_COLORS = {
            NodeStatus.PENDING: QColor(220, 220, 220),
            NodeStatus.RUNNING: QColor(100, 200, 255),
            NodeStatus.COMPLETED: QColor(100, 255, 100),
            NodeStatus.FAILED: QColor(255, 100, 100),
            NodeStatus.SKIPPED: QColor(200, 200, 200),
            NodeStatus.RETRYING: QColor(255, 200, 100),
        }
        
        def __init__(self, node_id: str, node_name: str, node_type: NodeType):
            super().__init__(0, 0, self.NODE_WIDTH, self.NODE_HEIGHT)
            
            self.node_id = node_id
            self.node_name = node_name
            self.node_type = node_type
            self.status: Optional[NodeStatus] = None
            
            # Setup appearance
            self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
            self.setPen(QPen(QColor(0, 0, 0), 2))
            self._update_color()
            
            # Add text label
            self.text_item = QGraphicsTextItem(self)
            self.text_item.setPlainText(f"{node_name}\n({node_type.value})")
            self.text_item.setPos(10, 10)
            self.text_item.setDefaultTextColor(QColor(0, 0, 0))
            
            font = QFont()
            font.setPointSize(9)
            font.setBold(True)
            self.text_item.setFont(font)
        
        def set_status(self, status: NodeStatus):
            """Update node status and color"""
            self.status = status
            self._update_color()
        
        def _update_color(self):
            """Update node color based on status or type"""
            if self.status:
                color = self.STATUS_COLORS.get(self.status, QColor(200, 200, 200))
            else:
                color = self.TYPE_COLORS.get(self.node_type, QColor(200, 200, 200))
            
            self.setBrush(QBrush(color))


    class EdgeGraphicsItem(QGraphicsLineItem):
        """Graphics item representing a dependency edge"""
        
        def __init__(self, x1: float, y1: float, x2: float, y2: float):
            super().__init__(x1, y1, x2, y2)
            
            self.setPen(QPen(QColor(80, 80, 80), 2))
            
            # Add arrow head
            self.arrow_head = QGraphicsEllipseItem(-5, -5, 10, 10)
            self.arrow_head.setBrush(QBrush(QColor(80, 80, 80)))
            self.arrow_head.setPen(QPen(QColor(80, 80, 80)))


    class WorkflowVisualizer(QWidget):
        """Widget for visualizing workflow DAG"""
        
        def __init__(self, parent=None):
            super().__init__(parent)
            
            self.dag: Optional[WorkflowDAG] = None
            self.state: Optional[WorkflowExecutionState] = None
            self.node_items: Dict[str, NodeGraphicsItem] = {}
            self.edge_items = []
            
            self._setup_ui()
        
        def _setup_ui(self):
            """Setup UI components"""
            layout = QVBoxLayout(self)
            
            # Graphics view and scene
            self.scene = QGraphicsScene()
            self.view = QGraphicsView(self.scene)
            self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            
            layout.addWidget(self.view)
            
            self.setLayout(layout)
        
        def load_workflow(self, dag: WorkflowDAG):
            """Load and visualize a workflow DAG"""
            self.dag = dag
            self._visualize_dag()
        
        def update_state(self, state: WorkflowExecutionState):
            """Update visualization with execution state"""
            self.state = state
            
            # Update node statuses
            for node_id, result in state.node_results.items():
                if node_id in self.node_items:
                    self.node_items[node_id].set_status(result.status)
            
            # Highlight running nodes
            for node_id in state.current_nodes:
                if node_id in self.node_items:
                    self.node_items[node_id].set_status(NodeStatus.RUNNING)
        
        def _visualize_dag(self):
            """Create visual representation of DAG"""
            if not self.dag:
                return
            
            # Clear existing items
            self.scene.clear()
            self.node_items.clear()
            self.edge_items.clear()
            
            # Get execution order (levels for layout)
            levels = self.dag.get_execution_order()
            
            # Layout constants
            LEVEL_SPACING = 200
            NODE_SPACING = 180
            START_Y = 50
            
            # Position nodes by level
            node_positions: Dict[str, tuple[float, float]] = {}
            
            for level_idx, level_nodes in enumerate(levels):
                y = START_Y + level_idx * LEVEL_SPACING
                
                # Center nodes horizontally
                total_width = len(level_nodes) * NODE_SPACING
                start_x = -total_width / 2 + NODE_SPACING / 2
                
                for node_idx, node_id in enumerate(level_nodes):
                    x = start_x + node_idx * NODE_SPACING
                    node_positions[node_id] = (x, y)
            
            # Create node items
            for node_id, (x, y) in node_positions.items():
                node = self.dag.get_node(node_id)
                
                item = NodeGraphicsItem(node_id, node.name, node.type)
                item.setPos(x, y)
                self.scene.addItem(item)
                self.node_items[node_id] = item
            
            # Create edge items
            for node_id, (x2, y2) in node_positions.items():
                dependencies = self.dag.get_dependencies(node_id)
                
                for dep_id in dependencies:
                    if dep_id in node_positions:
                        x1, y1 = node_positions[dep_id]
                        
                        # Calculate connection points (center bottom to center top)
                        x1_center = x1 + NodeGraphicsItem.NODE_WIDTH / 2
                        y1_bottom = y1 + NodeGraphicsItem.NODE_HEIGHT
                        x2_center = x2 + NodeGraphicsItem.NODE_WIDTH / 2
                        y2_top = y2
                        
                        edge = EdgeGraphicsItem(
                            x1_center, y1_bottom,
                            x2_center, y2_top
                        )
                        self.scene.addItem(edge)
                        self.edge_items.append(edge)
                        
                        # Position arrow head
                        edge.arrow_head.setPos(x2_center, y2_top)
                        self.scene.addItem(edge.arrow_head)
            
            # Fit view to scene
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        
        def zoom_in(self):
            """Zoom in the view"""
            self.view.scale(1.2, 1.2)
        
        def zoom_out(self):
            """Zoom out the view"""
            self.view.scale(1 / 1.2, 1 / 1.2)
        
        def reset_zoom(self):
            """Reset zoom to fit all"""
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

else:
    class WorkflowVisualizer:
        """Placeholder when PyQt6 is not available"""
        def __init__(self, parent=None):
            raise ImportError("PyQt6 is required for WorkflowVisualizer")
