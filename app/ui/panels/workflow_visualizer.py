"""
Workflow visualizer panel for displaying agent execution flow.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsLineItem,
        QGraphicsTextItem
    )
    from PyQt6.QtCore import Qt, QRect, pyqtSignal
    from PyQt6.QtGui import QColor, QPen, QBrush, QFont
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    class QWidget:
        pass


class WorkflowVisualizerPanel(QWidget):
    """Panel for visualizing workflow DAGs and execution flow."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the workflow visualizer UI."""
        layout = QVBoxLayout()
        
        toolbar_layout = QHBoxLayout()
        
        toolbar_layout.addWidget(QLabel("Workflow Visualization"))
        toolbar_layout.addStretch()
        
        self.refresh_button = QPushButton("Refresh")
        toolbar_layout.addWidget(self.refresh_button)
        
        self.clear_button = QPushButton("Clear")
        toolbar_layout.addWidget(self.clear_button)
        
        layout.addLayout(toolbar_layout)
        
        if PYQT6_AVAILABLE:
            self.scene = QGraphicsScene()
            self.view = QGraphicsView(self.scene)
            self.view.setStyleSheet("QGraphicsView { border: 1px solid #cccccc; }")
            self._add_placeholder_workflow()
            layout.addWidget(self.view)
        else:
            placeholder_label = QLabel("Workflow visualization requires PyQt6")
            layout.addWidget(placeholder_label)
        
        self.setLayout(layout)
        
    def _add_placeholder_workflow(self):
        """Add placeholder workflow nodes and edges."""
        if not PYQT6_AVAILABLE:
            return
            
        node_width = 100
        node_height = 50
        spacing_x = 150
        spacing_y = 100
        
        start_rect = QGraphicsRectItem(0, 0, node_width, node_height)
        start_rect.setBrush(QBrush(QColor("#90EE90")))
        start_rect.setPen(QPen(QColor("#000000"), 1))
        self.scene.addItem(start_rect)
        
        start_text = QGraphicsTextItem("Start")
        start_text.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        start_text.setPos(25, 15)
        self.scene.addItem(start_text)
        
        mid_rect = QGraphicsRectItem(spacing_x, spacing_y, node_width, node_height)
        mid_rect.setBrush(QBrush(QColor("#87CEEB")))
        mid_rect.setPen(QPen(QColor("#000000"), 1))
        self.scene.addItem(mid_rect)
        
        mid_text = QGraphicsTextItem("Process")
        mid_text.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        mid_text.setPos(spacing_x + 20, spacing_y + 15)
        self.scene.addItem(mid_text)
        
        end_rect = QGraphicsRectItem(spacing_x * 2, spacing_y, node_width, node_height)
        end_rect.setBrush(QBrush(QColor("#FFB6C1")))
        end_rect.setPen(QPen(QColor("#000000"), 1))
        self.scene.addItem(end_rect)
        
        end_text = QGraphicsTextItem("End")
        end_text.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        end_text.setPos(spacing_x * 2 + 30, spacing_y + 15)
        self.scene.addItem(end_text)
        
        line1 = QGraphicsLineItem(node_width, 25, spacing_x, spacing_y + 25)
        line1.setPen(QPen(QColor("#000000"), 2))
        self.scene.addItem(line1)
        
        line2 = QGraphicsLineItem(spacing_x + node_width, spacing_y + 25, spacing_x * 2, spacing_y + 25)
        line2.setPen(QPen(QColor("#000000"), 2))
        self.scene.addItem(line2)
        
        self.scene.setSceneRect(-10, -10, spacing_x * 2 + node_width + 20, spacing_y + node_height + 20)
        
    def add_workflow_node(self, node_id: str, label: str, x: int, y: int, color: str = "#87CEEB"):
        """Add a workflow node to the visualization."""
        if not PYQT6_AVAILABLE:
            return
            
        node_width = 100
        node_height = 50
        
        node_rect = QGraphicsRectItem(x, y, node_width, node_height)
        node_rect.setBrush(QBrush(QColor(color)))
        node_rect.setPen(QPen(QColor("#000000"), 1))
        self.scene.addItem(node_rect)
        
        text_item = QGraphicsTextItem(label)
        text_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        text_item.setPos(x + 10, y + 15)
        self.scene.addItem(text_item)
        
    def add_workflow_edge(self, from_x: int, from_y: int, to_x: int, to_y: int):
        """Add a connection between workflow nodes."""
        if not PYQT6_AVAILABLE:
            return
            
        line = QGraphicsLineItem(from_x, from_y, to_x, to_y)
        line.setPen(QPen(QColor("#000000"), 2))
        self.scene.addItem(line)
        
    def clear_workflow(self):
        """Clear the workflow visualization."""
        if PYQT6_AVAILABLE and hasattr(self, 'scene'):
            self.scene.clear()
        
    def update_workflow(self, workflow_data: dict):
        """Update the workflow with new data."""
        self.clear_workflow()
