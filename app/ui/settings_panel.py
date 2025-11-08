"""
Settings & Preferences Panel.

GUI for configuring all application settings without editing config files.
"""

import logging
from pathlib import Path
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
        QGroupBox, QScrollArea, QFileDialog, QTabWidget, QFormLayout
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QWidget = object

from app.config import config
from app.ui.state_manager import get_state_manager
from app.ui.message_bus import get_message_bus, EventTypes

logger = logging.getLogger(__name__)


class SettingsPanel(QWidget):
    """
    Settings and preferences panel.
    
    Provides GUI for all application settings.
    """
    
    DISPLAY_NAME = "Settings"
    DESCRIPTION = "Application settings and preferences"
    DEPENDENCIES = []
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.state_manager = get_state_manager()
        self.message_bus = get_message_bus()
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the settings UI."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("<h2>Settings & Preferences</h2>")
        layout.addWidget(title)
        
        # Tabs for different settings categories
        self.tabs = QTabWidget()
        
        # General settings
        self.tabs.addTab(self._create_general_tab(), "General")
        
        # Appearance settings
        self.tabs.addTab(self._create_appearance_tab(), "Appearance")
        
        # LLM settings
        self.tabs.addTab(self._create_llm_tab(), "LLM")
        
        # Component settings
        self.tabs.addTab(self._create_component_tab(), "Components")
        
        # Advanced settings
        self.tabs.addTab(self._create_advanced_tab(), "Advanced")
        
        layout.addWidget(self.tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self.reset_settings)
        button_layout.addWidget(self.reset_button)
        
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_button)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _create_general_tab(self) -> QWidget:
        """Create general settings tab."""
        widget = QWidget()
        layout = QFormLayout()
        
        # Workspace directory
        workspace_layout = QHBoxLayout()
        self.workspace_edit = QLineEdit()
        workspace_layout.addWidget(self.workspace_edit)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_workspace)
        workspace_layout.addWidget(browse_button)
        
        layout.addRow("Workspace:", workspace_layout)
        
        # Auto-save
        self.autosave_check = QCheckBox("Auto-save files")
        layout.addRow("", self.autosave_check)
        
        widget.setLayout(layout)
        return widget
    
    def _create_appearance_tab(self) -> QWidget:
        """Create appearance settings tab."""
        widget = QWidget()
        layout = QFormLayout()
        
        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        layout.addRow("Theme:", self.theme_combo)
        
        # Font family
        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems([
            "Courier New", "Consolas", "Monaco", "Menlo",
            "DejaVu Sans Mono", "Liberation Mono"
        ])
        layout.addRow("Font Family:", self.font_family_combo)
        
        # Font size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setSuffix(" pt")
        layout.addRow("Font Size:", self.font_size_spin)
        
        # Show line numbers
        self.line_numbers_check = QCheckBox("Show line numbers")
        layout.addRow("", self.line_numbers_check)
        
        # Syntax highlighting
        self.syntax_highlight_check = QCheckBox("Enable syntax highlighting")
        layout.addRow("", self.syntax_highlight_check)
        
        widget.setLayout(layout)
        return widget
    
    def _create_llm_tab(self) -> QWidget:
        """Create LLM settings tab."""
        widget = QWidget()
        layout = QFormLayout()
        
        # Model
        self.model_edit = QLineEdit()
        layout.addRow("Model:", self.model_edit)
        
        # API Base URL
        self.base_url_edit = QLineEdit()
        layout.addRow("Base URL:", self.base_url_edit)
        
        # API Key
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("API Key:", self.api_key_edit)
        
        # Temperature
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        layout.addRow("Temperature:", self.temperature_spin)
        
        # Max tokens
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 100000)
        self.max_tokens_spin.setSingleStep(100)
        layout.addRow("Max Tokens:", self.max_tokens_spin)
        
        widget.setLayout(layout)
        return widget
    
    def _create_component_tab(self) -> QWidget:
        """Create component settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        label = QLabel("Select components to load at startup:")
        layout.addWidget(label)
        
        # Get all components from state manager
        self.component_checks = {}
        components = self.state_manager.get_all_components()
        
        for comp_name, comp_state in components.items():
            check = QCheckBox(comp_state.name)
            check.setChecked(comp_state.enabled)
            layout.addWidget(check)
            self.component_checks[comp_name] = check
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_advanced_tab(self) -> QWidget:
        """Create advanced settings tab."""
        widget = QWidget()
        layout = QFormLayout()
        
        # Log level
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        layout.addRow("Log Level:", self.log_level_combo)
        
        # Max history
        self.max_history_spin = QSpinBox()
        self.max_history_spin.setRange(10, 1000)
        layout.addRow("Max History:", self.max_history_spin)
        
        widget.setLayout(layout)
        return widget
    
    def _browse_workspace(self):
        """Browse for workspace directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Workspace Directory")
        if directory:
            self.workspace_edit.setText(directory)
    
    def load_settings(self):
        """Load current settings from config."""
        try:
            # General
            self.workspace_edit.setText(config.local_service.workspace_directory)
            
            # Appearance
            prefs = self.state_manager.get_preferences()
            self.theme_combo.setCurrentText(prefs.theme.title())
            self.font_family_combo.setCurrentText(prefs.font_family)
            self.font_size_spin.setValue(prefs.font_size)
            self.line_numbers_check.setChecked(prefs.show_line_numbers)
            self.syntax_highlight_check.setChecked(prefs.enable_syntax_highlighting)
            self.autosave_check.setChecked(prefs.auto_save)
            
            # LLM
            self.model_edit.setText(config.llm.model)
            self.base_url_edit.setText(config.llm.base_url)
            if config.llm.api_key:
                self.api_key_edit.setText(config.llm.api_key)
            self.temperature_spin.setValue(config.llm.temperature)
            self.max_tokens_spin.setValue(config.llm.max_tokens)
            
            logger.debug("Settings loaded")
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    
    def apply_settings(self):
        """Apply settings without saving."""
        try:
            # Update preferences
            self.state_manager.update_preferences(
                theme=self.theme_combo.currentText().lower(),
                font_family=self.font_family_combo.currentText(),
                font_size=self.font_size_spin.value(),
                show_line_numbers=self.line_numbers_check.isChecked(),
                enable_syntax_highlighting=self.syntax_highlight_check.isChecked(),
                auto_save=self.autosave_check.isChecked()
            )
            
            # Update workspace
            config.local_service.workspace_directory = self.workspace_edit.text()
            
            # Update LLM settings
            config.llm.model = self.model_edit.text()
            config.llm.base_url = self.base_url_edit.text()
            if self.api_key_edit.text():
                config.llm.api_key = self.api_key_edit.text()
            config.llm.temperature = self.temperature_spin.value()
            config.llm.max_tokens = self.max_tokens_spin.value()
            
            # Update component settings
            enabled_components = set()
            for comp_name, check in self.component_checks.items():
                if check.isChecked():
                    enabled_components.add(comp_name)
            
            self.state_manager.update_preferences(
                enabled_components=enabled_components
            )
            
            logger.info("Settings applied")
            self.settings_changed.emit({})
            
        except Exception as e:
            logger.error(f"Error applying settings: {e}")
    
    def save_settings(self):
        """Apply and save settings."""
        self.apply_settings()
        
        try:
            # Save state
            config_dir = Path.home() / ".openmanus"
            config_dir.mkdir(parents=True, exist_ok=True)
            
            state_file = config_dir / "state.json"
            self.state_manager.save_state(state_file)
            
            logger.info(f"Settings saved to {state_file}")
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
    
    def reset_settings(self):
        """Reset settings to defaults."""
        # TODO: Implement reset to defaults
        logger.info("Reset to defaults not yet implemented")


class SettingsPanelDock:
    """Factory for creating settings panel in a dock widget."""
    
    @staticmethod
    def create():
        """Create settings panel."""
        return SettingsPanel()
