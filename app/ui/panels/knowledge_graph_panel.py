"""
Knowledge Graph Panel
Displays and interacts with the knowledge graph
"""

from typing import Dict, List, Any, Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
        QLabel, QPushButton, QLineEdit, QTextEdit, QSplitter,
        QGroupBox, QHeaderView, QMessageBox, QComboBox,
        QListWidget, QListWidgetItem
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
    from PyQt6.QtGui import QFont
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

if PYQT6_AVAILABLE:
    from app.system_integration.integration_service import system_integration
    from app.knowledge_graph.knowledge_graph_service import knowledge_graph_service


class KnowledgeGraphWorker(QThread):
    """Worker thread for knowledge graph operations"""
    
    update_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    search_result_signal = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self._running = False
        self._tasks = []
    
    def run(self):
        """Main worker loop"""
        self._running = True
        
        while self._running:
            try:
                # Process any pending tasks
                if self._tasks:
                    task = self._tasks.pop(0)
                    self._process_task(task)
                
                # Regular update every 10 seconds
                import asyncio
                stats = asyncio.run(knowledge_graph_service.get_graph_statistics())
                self.update_signal.emit(stats)
                
                self.msleep(10000)  # 10 seconds
                
            except Exception as e:
                self.error_signal.emit(str(e))
                self.msleep(15000)  # Wait longer on error
    
    def _process_task(self, task: Dict[str, Any]):
        """Process a specific task"""
        task_type = task.get('type')
        
        try:
            import asyncio
            
            if task_type == 'search':
                query = task.get('query', '')
                node_type = task.get('node_type', None)
                results = asyncio.run(knowledge_graph_service.search_nodes(query, node_type))
                self.search_result_signal.emit(results)
            
            elif task_type == 'get_neighbors':
                node_id = task.get('node_id')
                neighbors = asyncio.run(knowledge_graph_service.get_node_neighbors(node_id))
                self.search_result_signal.emit(neighbors)
            
        except Exception as e:
            self.error_signal.emit(f"Error processing task {task_type}: {e}")
    
    def add_task(self, task: Dict[str, Any]):
        """Add a task to the queue"""
        self._tasks.append(task)
    
    def stop(self):
        """Stop the worker"""
        self._running = False


class KnowledgeGraphPanel(QWidget):
    """Knowledge graph panel"""
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.current_node_id = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Knowledge Graph")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Search and controls
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # Search group
        search_group = QGroupBox("Search Nodes")
        search_layout = QVBoxLayout()
        
        # Search input
        search_input_layout = QHBoxLayout()
        search_input_layout.addWidget(QLabel("Query:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search query...")
        search_input_layout.addWidget(self.search_input)
        
        search_layout.addLayout(search_input_layout)
        
        # Node type filter
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        
        self.node_type_filter = QComboBox()
        self.node_type_filter.addItems(["All", "user", "file", "api", "agent", "project"])
        type_layout.addWidget(self.node_type_filter)
        
        search_layout.addLayout(type_layout)
        
        # Search button
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search_nodes)
        search_layout.addWidget(search_btn)
        
        search_group.setLayout(search_layout)
        left_layout.addWidget(search_group)
        
        # Statistics group
        stats_group = QGroupBox("Graph Statistics")
        stats_layout = QVBoxLayout()
        
        self.total_nodes_label = QLabel("Total Nodes: 0")
        self.total_relationships_label = QLabel("Total Relationships: 0")
        self.avg_degree_label = QLabel("Avg Degree: 0.0")
        self.density_label = QLabel("Density: 0.0")
        self.components_label = QLabel("Connected Components: 0")
        
        stats_layout.addWidget(self.total_nodes_label)
        stats_layout.addWidget(self.total_relationships_label)
        stats_layout.addWidget(self.avg_degree_label)
        stats_layout.addWidget(self.density_label)
        stats_layout.addWidget(self.components_label)
        
        stats_group.setLayout(stats_layout)
        left_layout.addWidget(stats_group)
        
        # Node types distribution
        types_group = QGroupBox("Node Types")
        types_layout = QVBoxLayout()
        
        self.node_types_list = QListWidget()
        types_layout.addWidget(self.node_types_list)
        
        types_group.setLayout(types_layout)
        left_layout.addWidget(types_group)
        
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        # Right side - Results and details
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # Results table
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels([
            "Node ID", "Type", "Content", "Similarity"
        ])
        
        # Configure table
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        results_layout.addWidget(self.results_table)
        results_group.setLayout(results_layout)
        right_layout.addWidget(results_group)
        
        # Node details
        details_group = QGroupBox("Node Details")
        details_layout = QVBoxLayout()
        
        self.node_details = QTextEdit()
        self.node_details.setReadOnly(True)
        self.node_details.setMaximumHeight(200)
        
        details_layout.addWidget(self.node_details)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        neighbors_btn = QPushButton("Show Neighbors")
        neighbors_btn.clicked.connect(self.show_neighbors)
        actions_layout.addWidget(neighbors_btn)
        
        related_btn = QPushButton("Find Related")
        related_btn.clicked.connect(self.find_related)
        actions_layout.addWidget(related_btn)
        
        details_layout.addLayout(actions_layout)
        details_group.setLayout(details_layout)
        right_layout.addWidget(details_group)
        
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        # Set splitter sizes
        splitter.setSizes([350, 650])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # Connect table selection
        self.results_table.itemSelectionChanged.connect(self.show_node_details)
        
        # Start monitoring
        self.start_monitoring()
    
    def start_monitoring(self):
        """Start the knowledge graph worker"""
        if not PYQT6_AVAILABLE:
            return
        
        self.worker = KnowledgeGraphWorker()
        self.worker.update_signal.connect(self.update_statistics)
        self.worker.error_signal.connect(self.show_error)
        self.worker.search_result_signal.connect(self.display_search_results)
        self.worker.start()
    
    def stop_monitoring(self):
        """Stop the knowledge graph worker"""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.worker = None
    
    def update_statistics(self, stats: Dict[str, Any]):
        """Update graph statistics"""
        try:
            self.total_nodes_label.setText(f"Total Nodes: {stats.get('total_nodes', 0)}")
            self.total_relationships_label.setText(f"Total Relationships: {stats.get('total_relationships', 0)}")
            self.avg_degree_label.setText(f"Avg Degree: {stats.get('average_degree', 0.0):.2f}")
            self.density_label.setText(f"Density: {stats.get('graph_density', 0.0):.3f}")
            self.components_label.setText(f"Connected Components: {stats.get('connected_components', 0)}")
            
            # Update node types
            self.node_types_list.clear()
            node_types = stats.get('node_types', {})
            for node_type, count in node_types.items():
                item = QListWidgetItem(f"{node_type}: {count}")
                self.node_types_list.addItem(item)
            
        except Exception as e:
            self.show_error(f"Error updating statistics: {e}")
    
    def search_nodes(self):
        """Search for nodes"""
        try:
            query = self.search_input.text().strip()
            if not query:
                return
            
            node_type = self.node_type_filter.currentText()
            node_type = None if node_type == "All" else node_type
            
            # Add search task to worker
            if self.worker:
                self.worker.add_task({
                    'type': 'search',
                    'query': query,
                    'node_type': node_type
                })
            
        except Exception as e:
            self.show_error(f"Error searching nodes: {e}")
    
    def display_search_results(self, results: List[Any]):
        """Display search results in the table"""
        try:
            self.results_table.setRowCount(0)
            
            for i, (node, similarity) in enumerate(results):
                self.results_table.insertRow(i)
                
                self.results_table.setItem(i, 0, QTableWidgetItem(str(node.id)))
                self.results_table.setItem(i, 1, QTableWidgetItem(node.node_type))
                self.results_table.setItem(i, 2, QTableWidgetItem(node.content[:100] + "..." if len(node.content) > 100 else node.content))
                self.results_table.setItem(i, 3, QTableWidgetItem(f"{similarity:.3f}"))
            
        except Exception as e:
            self.show_error(f"Error displaying search results: {e}")
    
    def show_node_details(self):
        """Show details for selected node"""
        try:
            current_row = self.results_table.currentRow()
            if current_row < 0:
                self.node_details.clear()
                return
            
            node_id = int(self.results_table.item(current_row, 0).text())
            self.current_node_id = node_id
            
            # Get node details (this would need to be implemented)
            details = f"""
Node ID: {node_id}
Type: {self.results_table.item(current_row, 1).text()}
Content: {self.results_table.item(current_row, 2).text()}
Similarity: {self.results_table.item(current_row, 3).text()}

Additional details would be shown here...
            """.strip()
            
            self.node_details.setPlainText(details)
            
        except Exception as e:
            self.show_error(f"Error showing node details: {e}")
    
    def show_neighbors(self):
        """Show neighbors for selected node"""
        try:
            if self.current_node_id is None:
                self.show_error("Please select a node first")
                return
            
            # Add get neighbors task to worker
            if self.worker:
                self.worker.add_task({
                    'type': 'get_neighbors',
                    'node_id': self.current_node_id
                })
            
        except Exception as e:
            self.show_error(f"Error showing neighbors: {e}")
    
    def find_related(self):
        """Find related nodes"""
        try:
            if self.current_node_id is None:
                self.show_error("Please select a node first")
                return
            
            # This would implement related node search
            self.show_error("Find related nodes (placeholder)")
            
        except Exception as e:
            self.show_error(f"Error finding related nodes: {e}")
    
    def show_error(self, message: str):
        """Show error message"""
        if PYQT6_AVAILABLE:
            QMessageBox.critical(self, "Error", message)
        else:
            print(f"Knowledge Graph Error: {message}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.stop_monitoring()
        super().closeEvent(event)
