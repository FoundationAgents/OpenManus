"""
QA Monitor Panel

UI panel for monitoring QA system status, issues, and metrics.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
        QTableWidgetItem, QProgressBar, QPushButton, QTabWidget,
        QTextEdit, QGroupBox, QScrollArea
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QTimer
    from PyQt6.QtGui import QFont, QColor
    HAS_QT = True
except ImportError:
    HAS_QT = False
    QWidget = object

from typing import Dict, List, Optional, Any
from app.logger import logger


if HAS_QT:
    class QAMonitorPanel(QWidget):
        """QA monitoring panel"""
        
        # Panel metadata for component discovery
        DISPLAY_NAME = "QA Monitor"
        DESCRIPTION = "Monitor QA scans, issues, and code quality metrics"
        DEPENDENCIES = []
        
        def __init__(self, parent=None):
            super().__init__(parent)
            
            self.qa_gate = None
            self.current_scans = {}
            
            self.init_ui()
            
            # Auto-refresh timer
            self.refresh_timer = QTimer(self)
            self.refresh_timer.timeout.connect(self.refresh_data)
            self.refresh_timer.start(5000)  # Refresh every 5 seconds
        
        def init_ui(self):
            """Initialize UI"""
            layout = QVBoxLayout(self)
            
            # Title
            title = QLabel("QA Monitor")
            title_font = QFont()
            title_font.setPointSize(16)
            title_font.setBold(True)
            title.setFont(title_font)
            layout.addWidget(title)
            
            # Tabs
            tabs = QTabWidget()
            
            # Tab 1: Current Scans
            tabs.addTab(self._create_scans_tab(), "Current Scans")
            
            # Tab 2: Issues Dashboard
            tabs.addTab(self._create_issues_tab(), "Issues")
            
            # Tab 3: Auto-Fixes
            tabs.addTab(self._create_fixes_tab(), "Auto-Fixes")
            
            # Tab 4: Production Readiness
            tabs.addTab(self._create_readiness_tab(), "Prod Readiness")
            
            # Tab 5: Metrics
            tabs.addTab(self._create_metrics_tab(), "Metrics")
            
            # Tab 6: Knowledge Base
            tabs.addTab(self._create_knowledge_tab(), "Knowledge Base")
            
            layout.addWidget(tabs)
            
            # Status bar
            self.status_label = QLabel("Status: Ready")
            layout.addWidget(self.status_label)
        
        def _create_scans_tab(self) -> QWidget:
            """Create current scans tab"""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Scan progress
            self.scans_layout = QVBoxLayout()
            layout.addLayout(self.scans_layout)
            
            # Add placeholder
            placeholder = QLabel("No active scans")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.scans_layout.addWidget(placeholder)
            
            layout.addStretch()
            
            return widget
        
        def _create_issues_tab(self) -> QWidget:
            """Create issues dashboard tab"""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Issue breakdown
            breakdown_group = QGroupBox("Issues by Severity")
            breakdown_layout = QHBoxLayout(breakdown_group)
            
            self.critical_label = self._create_severity_widget("CRITICAL", 0, "#DC3545")
            self.high_label = self._create_severity_widget("HIGH", 0, "#FD7E14")
            self.medium_label = self._create_severity_widget("MEDIUM", 0, "#FFC107")
            self.low_label = self._create_severity_widget("LOW", 0, "#28A745")
            
            breakdown_layout.addWidget(self.critical_label)
            breakdown_layout.addWidget(self.high_label)
            breakdown_layout.addWidget(self.medium_label)
            breakdown_layout.addWidget(self.low_label)
            
            layout.addWidget(breakdown_group)
            
            # Issues table
            self.issues_table = QTableWidget()
            self.issues_table.setColumnCount(5)
            self.issues_table.setHorizontalHeaderLabels([
                "Severity", "Type", "File", "Line", "Message"
            ])
            layout.addWidget(self.issues_table)
            
            return widget
        
        def _create_fixes_tab(self) -> QWidget:
            """Create auto-fixes tab"""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Fix statistics
            stats_group = QGroupBox("Auto-Fix Statistics")
            stats_layout = QVBoxLayout(stats_group)
            
            self.fixes_applied_label = QLabel("Fixes Applied: 0")
            self.fixes_failed_label = QLabel("Fixes Failed: 0")
            
            stats_layout.addWidget(self.fixes_applied_label)
            stats_layout.addWidget(self.fixes_failed_label)
            
            layout.addWidget(stats_group)
            
            # Recent fixes
            fixes_group = QGroupBox("Recent Auto-Fixes")
            fixes_layout = QVBoxLayout(fixes_group)
            
            self.fixes_log = QTextEdit()
            self.fixes_log.setReadOnly(True)
            fixes_layout.addWidget(self.fixes_log)
            
            layout.addWidget(fixes_group)
            
            return widget
        
        def _create_readiness_tab(self) -> QWidget:
            """Create production readiness tab"""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Readiness checklist
            self.readiness_layout = QVBoxLayout()
            layout.addLayout(self.readiness_layout)
            
            # Add check button
            check_button = QPushButton("Run Readiness Check")
            check_button.clicked.connect(self.run_readiness_check)
            layout.addWidget(check_button)
            
            # Status
            self.readiness_status = QLabel("Status: Not Checked")
            self.readiness_status.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            layout.addWidget(self.readiness_status)
            
            layout.addStretch()
            
            return widget
        
        def _create_metrics_tab(self) -> QWidget:
            """Create metrics tab"""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Quality score
            score_group = QGroupBox("Code Quality Score")
            score_layout = QVBoxLayout(score_group)
            
            self.quality_score_label = QLabel("Score: --")
            self.quality_score_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            self.quality_score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            score_layout.addWidget(self.quality_score_label)
            
            self.quality_progress = QProgressBar()
            self.quality_progress.setRange(0, 100)
            self.quality_progress.setValue(0)
            score_layout.addWidget(self.quality_progress)
            
            layout.addWidget(score_group)
            
            # Metrics
            metrics_group = QGroupBox("Metrics")
            metrics_layout = QVBoxLayout(metrics_group)
            
            self.reviews_count_label = QLabel("Total Reviews: 0")
            self.issues_per_kloc_label = QLabel("Issues/1000 LOC: 0.00")
            self.auto_fix_rate_label = QLabel("Auto-Fix Rate: 0%")
            self.avg_review_time_label = QLabel("Avg Review Time: 0s")
            
            metrics_layout.addWidget(self.reviews_count_label)
            metrics_layout.addWidget(self.issues_per_kloc_label)
            metrics_layout.addWidget(self.auto_fix_rate_label)
            metrics_layout.addWidget(self.avg_review_time_label)
            
            layout.addWidget(metrics_group)
            
            # Reports
            reports_group = QGroupBox("Reports")
            reports_layout = QVBoxLayout(reports_group)
            
            daily_button = QPushButton("Generate Daily Report")
            daily_button.clicked.connect(self.generate_daily_report)
            reports_layout.addWidget(daily_button)
            
            weekly_button = QPushButton("Generate Weekly Report")
            weekly_button.clicked.connect(self.generate_weekly_report)
            reports_layout.addWidget(weekly_button)
            
            layout.addWidget(reports_group)
            
            layout.addStretch()
            
            return widget
        
        def _create_knowledge_tab(self) -> QWidget:
            """Create knowledge base tab"""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Knowledge stats
            stats_group = QGroupBox("Knowledge Base Statistics")
            stats_layout = QVBoxLayout(stats_group)
            
            self.kb_entries_label = QLabel("Total Patterns: 0")
            self.kb_top_patterns_label = QLabel("Top Patterns: -")
            
            stats_layout.addWidget(self.kb_entries_label)
            stats_layout.addWidget(self.kb_top_patterns_label)
            
            layout.addWidget(stats_group)
            
            # Top patterns table
            patterns_group = QGroupBox("Most Common Issues")
            patterns_layout = QVBoxLayout(patterns_group)
            
            self.patterns_table = QTableWidget()
            self.patterns_table.setColumnCount(3)
            self.patterns_table.setHorizontalHeaderLabels([
                "Pattern", "Occurrences", "Severity"
            ])
            patterns_layout.addWidget(self.patterns_table)
            
            layout.addWidget(patterns_group)
            
            return widget
        
        def _create_severity_widget(self, severity: str, count: int, color: str) -> QWidget:
            """Create severity counter widget"""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            count_label = QLabel(str(count))
            count_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count_label.setStyleSheet(f"color: {color};")
            
            name_label = QLabel(severity)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            layout.addWidget(count_label)
            layout.addWidget(name_label)
            
            widget.count_label = count_label
            
            return widget
        
        def set_qa_gate(self, qa_gate):
            """Set QA gate instance"""
            self.qa_gate = qa_gate
            self.refresh_data()
        
        def refresh_data(self):
            """Refresh all data"""
            if not self.qa_gate:
                return
            
            try:
                # Update metrics
                if hasattr(self.qa_gate, 'metrics'):
                    report = self.qa_gate.metrics.get_daily_report()
                    
                    if "total_reviews" in report:
                        self.reviews_count_label.setText(f"Total Reviews: {report['total_reviews']}")
                        self.issues_per_kloc_label.setText(f"Issues/1000 LOC: {report.get('issues_per_1000_loc', 0):.2f}")
                        self.auto_fix_rate_label.setText(f"Auto-Fix Rate: {report.get('auto_fix_rate', 0):.1f}%")
                        self.avg_review_time_label.setText(f"Avg Review Time: {report.get('average_review_time', 0):.2f}s")
                
                # Update knowledge base
                if hasattr(self.qa_gate, 'knowledge_base'):
                    stats = self.qa_gate.knowledge_base.get_statistics()
                    
                    self.kb_entries_label.setText(f"Total Patterns: {stats['total_entries']}")
                    
                    if stats['top_patterns']:
                        top_text = ", ".join([p['pattern'] for p in stats['top_patterns'][:3]])
                        self.kb_top_patterns_label.setText(f"Top Patterns: {top_text}")
                    
                    # Update patterns table
                    top_patterns = stats['top_patterns']
                    self.patterns_table.setRowCount(len(top_patterns))
                    
                    for i, pattern in enumerate(top_patterns):
                        self.patterns_table.setItem(i, 0, QTableWidgetItem(pattern['pattern']))
                        self.patterns_table.setItem(i, 1, QTableWidgetItem(str(pattern['count'])))
                        self.patterns_table.setItem(i, 2, QTableWidgetItem(pattern['severity']))
                
                self.status_label.setText(f"Status: Updated at {QTimer().remainingTime()}")
            
            except Exception as e:
                logger.error(f"Error refreshing QA monitor: {e}")
        
        def update_issues(self, issues: List[Dict[str, Any]]):
            """Update issues display"""
            # Count by severity
            severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for issue in issues:
                severity = issue.get("severity", "MEDIUM")
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Update counters
            self.critical_label.count_label.setText(str(severity_counts["CRITICAL"]))
            self.high_label.count_label.setText(str(severity_counts["HIGH"]))
            self.medium_label.count_label.setText(str(severity_counts["MEDIUM"]))
            self.low_label.count_label.setText(str(severity_counts["LOW"]))
            
            # Update table
            self.issues_table.setRowCount(len(issues))
            
            for i, issue in enumerate(issues):
                self.issues_table.setItem(i, 0, QTableWidgetItem(issue.get("severity", "MEDIUM")))
                self.issues_table.setItem(i, 1, QTableWidgetItem(issue.get("type", "unknown")))
                self.issues_table.setItem(i, 2, QTableWidgetItem(issue.get("file_path", "unknown")))
                self.issues_table.setItem(i, 3, QTableWidgetItem(str(issue.get("line_number", 0))))
                self.issues_table.setItem(i, 4, QTableWidgetItem(issue.get("message", "")))
        
        def add_auto_fix(self, fix_info: str):
            """Add auto-fix to log"""
            self.fixes_log.append(fix_info)
        
        def run_readiness_check(self):
            """Run production readiness check"""
            # This would be connected to actual QA gate
            self.readiness_status.setText("Status: Checking...")
            # TODO: Implement actual check
        
        def generate_daily_report(self):
            """Generate daily report"""
            if not self.qa_gate:
                return
            
            report = self.qa_gate.metrics.get_daily_report()
            logger.info(f"Daily QA Report: {report}")
        
        def generate_weekly_report(self):
            """Generate weekly report"""
            if not self.qa_gate:
                return
            
            report = self.qa_gate.metrics.get_weekly_report()
            logger.info(f"Weekly QA Report: {report}")

else:
    # Fallback when Qt is not available
    class QAMonitorPanel:
        """Fallback QA monitor (no UI)"""
        
        DISPLAY_NAME = "QA Monitor"
        DESCRIPTION = "Monitor QA scans (UI not available)"
        DEPENDENCIES = []
        
        def __init__(self, parent=None):
            logger.warning("QA Monitor UI not available (PyQt6 not installed)")
        
        def set_qa_gate(self, qa_gate):
            pass
        
        def refresh_data(self):
            pass
        
        def update_issues(self, issues):
            pass
        
        def add_auto_fix(self, fix_info):
            pass
