"""
Retrieval insights panel for displaying knowledge graph and retrieved results.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
        QPushButton, QLabel, QLineEdit, QCheckBox, QGroupBox, QMessageBox,
        QHeaderView, QScrollArea, QTreeWidget, QTreeWidgetItem, QSplitter,
        QDialog, QTextEdit, QComboBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QFont, QColor, QIcon
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    class QWidget:
        pass
    pyqtSignal = None


class RetrievalInsightsPanel(QWidget if PYQT6_AVAILABLE else object):
    """Panel for displaying retrieval results and knowledge graph insights."""
    
    if PYQT6_AVAILABLE:
        result_accepted = pyqtSignal(dict)
        result_rejected = pyqtSignal(dict)
    
    def __init__(self):
        if PYQT6_AVAILABLE:
            super().__init__()
        self.retrieval_context = None
        self.selected_result = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the retrieval insights UI."""
        if not PYQT6_AVAILABLE:
            return
        
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Retrieval Insights & Knowledge Graph"))
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Search controls
        search_layout = QHBoxLayout()
        
        search_layout.addWidget(QLabel("Query:"))
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Enter search query...")
        search_layout.addWidget(self.query_input)
        
        search_layout.addWidget(QLabel("Strategy:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "balanced", "graph_first", "vector_first", "adaptive"
        ])
        search_layout.addWidget(self.strategy_combo)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self._on_search)
        search_layout.addWidget(self.search_button)
        
        self.refine_button = QPushButton("Refine")
        self.refine_button.clicked.connect(self._on_refine)
        search_layout.addWidget(self.refine_button)
        
        layout.addLayout(search_layout)
        
        # Results and Graph splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Results section
        results_group = QGroupBox("Retrieved Results")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Content", "Score", "Graph Score", "Vector Score", "Actions"
        ])
        
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.results_table.itemSelectionChanged.connect(self._on_result_selected)
        results_layout.addWidget(self.results_table)
        
        results_group.setLayout(results_layout)
        splitter.addWidget(results_group)
        
        # Graph section
        graph_group = QGroupBox("Knowledge Graph Structure")
        graph_layout = QVBoxLayout()
        
        self.graph_tree = QTreeWidget()
        self.graph_tree.setHeaderLabels(["Node", "Type", "Relationships"])
        self.graph_tree.itemSelectionChanged.connect(self._on_node_selected)
        graph_layout.addWidget(self.graph_tree)
        
        graph_group.setLayout(graph_layout)
        splitter.addWidget(graph_group)
        
        layout.addWidget(splitter)
        
        # Details section
        details_group = QGroupBox("Selected Item Details")
        details_layout = QVBoxLayout()
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.accept_button = QPushButton("Accept & Inject")
        self.accept_button.clicked.connect(self._on_accept)
        self.accept_button.setEnabled(False)
        action_layout.addWidget(self.accept_button)
        
        self.reject_button = QPushButton("Reject")
        self.reject_button.clicked.connect(self._on_reject)
        self.reject_button.setEnabled(False)
        action_layout.addWidget(self.reject_button)
        
        self.copy_button = QPushButton("Copy to Context")
        self.copy_button.clicked.connect(self._on_copy)
        self.copy_button.setEnabled(False)
        action_layout.addWidget(self.copy_button)
        
        action_layout.addStretch()
        
        self.stats_label = QLabel()
        action_layout.addWidget(self.stats_label)
        
        layout.addLayout(action_layout)
        self.setLayout(layout)
    
    def update_results(self, context):
        """Update the panel with retrieval context."""
        if not PYQT6_AVAILABLE:
            return
        
        self.retrieval_context = context
        
        # Update query display
        self.query_input.setText(context.query)
        self.strategy_combo.setCurrentText(context.strategy_used)
        
        # Clear tables
        self.results_table.setRowCount(0)
        self.graph_tree.clear()
        
        # Populate results table
        for i, result in enumerate(context.results):
            self.results_table.insertRow(i)
            
            # Content
            content_item = QTableWidgetItem(result.content[:50] + "...")
            self.results_table.setItem(i, 0, content_item)
            
            # Score
            score_item = QTableWidgetItem(f"{result.score:.3f}")
            self.results_table.setItem(i, 1, score_item)
            
            # Graph score
            graph_score_item = QTableWidgetItem(f"{result.graph_score:.3f}")
            self.results_table.setItem(i, 2, graph_score_item)
            
            # Vector score
            vector_score_item = QTableWidgetItem(f"{result.vector_score:.3f}")
            self.results_table.setItem(i, 3, vector_score_item)
            
            # Actions
            actions_item = QTableWidgetItem("View")
            self.results_table.setItem(i, 4, actions_item)
        
        # Update stats
        self._update_stats()
    
    def add_graph_node(self, node_id, node_type, content, relationships=None):
        """Add a node to the graph tree."""
        if not PYQT6_AVAILABLE:
            return
        
        root_item = self.graph_tree.invisibleRootItem()
        
        node_item = QTreeWidgetItem([
            node_id,
            node_type,
            str(len(relationships)) if relationships else "0"
        ])
        
        if relationships:
            for rel_type, rel_nodes in relationships.items():
                rel_item = QTreeWidgetItem([rel_type, "", ""])
                for rel_node in rel_nodes:
                    rel_item.addChild(QTreeWidgetItem([rel_node, "", ""]))
                node_item.addChild(rel_item)
        
        root_item.addChild(node_item)
    
    def _on_search(self):
        """Handle search button click."""
        if not PYQT6_AVAILABLE:
            return
        
        try:
            from app.memory import get_retriever_service
            
            query = self.query_input.text()
            strategy = self.strategy_combo.currentText()
            
            service = get_retriever_service()
            context = service.retrieve("ui_agent", query, strategy=strategy)
            
            self.update_results(context)
            
        except Exception as e:
            QMessageBox.critical(self, "Retrieval Error", f"Search failed: {str(e)}")
    
    def _on_refine(self):
        """Handle refine button click."""
        if not PYQT6_AVAILABLE:
            return
        
        try:
            from app.memory import get_retriever_service
            
            if not self.retrieval_context:
                QMessageBox.warning(self, "Warning", "Perform a search first")
                return
            
            query = self.query_input.text()
            service = get_retriever_service()
            contexts = service.retrieve_iterative("ui_agent", query, max_iterations=2)
            
            if contexts:
                self.update_results(contexts[-1])
            
        except Exception as e:
            QMessageBox.critical(self, "Refinement Error", f"Refinement failed: {str(e)}")
    
    def _on_result_selected(self):
        """Handle result selection."""
        if not PYQT6_AVAILABLE:
            return
        
        selected_rows = self.results_table.selectedIndexes()
        if selected_rows:
            row = selected_rows[0].row()
            if self.retrieval_context and row < len(self.retrieval_context.results):
                self.selected_result = self.retrieval_context.results[row]
                self._update_details()
                self.accept_button.setEnabled(True)
                self.reject_button.setEnabled(True)
                self.copy_button.setEnabled(True)
    
    def _on_node_selected(self):
        """Handle graph node selection."""
        if not PYQT6_AVAILABLE:
            return
        
        selected_items = self.graph_tree.selectedItems()
        if selected_items:
            item = selected_items[0]
            text = f"Node: {item.text(0)}\nType: {item.text(1)}\nRelationships: {item.text(2)}"
            self.details_text.setText(text)
    
    def _on_accept(self):
        """Accept and inject selected result."""
        if not PYQT6_AVAILABLE or not self.selected_result:
            return
        
        self.result_accepted.emit(self.selected_result.to_dict())
        QMessageBox.information(self, "Success", "Result accepted and injected into context")
    
    def _on_reject(self):
        """Reject selected result."""
        if not PYQT6_AVAILABLE or not self.selected_result:
            return
        
        self.result_rejected.emit(self.selected_result.to_dict())
        self.selected_result = None
        self.details_text.clear()
        self.accept_button.setEnabled(False)
        self.reject_button.setEnabled(False)
        self.copy_button.setEnabled(False)
    
    def _on_copy(self):
        """Copy result to clipboard."""
        if not PYQT6_AVAILABLE or not self.selected_result:
            return
        
        import json
        from PyQt6.QtWidgets import QApplication
        
        data = self.selected_result.to_dict()
        clipboard = QApplication.clipboard()
        clipboard.setText(json.dumps(data, indent=2))
        QMessageBox.information(self, "Copied", "Result copied to clipboard")
    
    def _update_details(self):
        """Update the details display."""
        if not PYQT6_AVAILABLE or not self.selected_result:
            return
        
        details = f"""
Node ID: {self.selected_result.node_id}
Content: {self.selected_result.content}
Source: {self.selected_result.source}

Scores:
  Composite: {self.selected_result.score:.4f}
  Graph: {self.selected_result.graph_score:.4f}
  Vector: {self.selected_result.vector_score:.4f}

Metadata:
"""
        for key, value in self.selected_result.metadata.items():
            details += f"  {key}: {value}\n"
        
        self.details_text.setText(details)
    
    def _update_stats(self):
        """Update statistics display."""
        if not PYQT6_AVAILABLE or not self.retrieval_context:
            return
        
        stats_text = (
            f"Results: {len(self.retrieval_context.results)} | "
            f"Time: {self.retrieval_context.total_time:.2f}s | "
            f"Strategy: {self.retrieval_context.strategy_used}"
        )
        self.stats_label.setText(stats_text)
