"""UI panel for displaying and managing discovered system resources."""

import json
import asyncio
from typing import Any, Dict, List

try:  # pragma: no cover - UI components skipped in tests
    from PyQt6.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
        QComboBox,
        QLineEdit,
        QTextEdit,
        QGroupBox,
        QMessageBox,
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    PYQT6_AVAILABLE = True
except ImportError:  # pragma: no cover - headless environments
    PYQT6_AVAILABLE = False

from app.resources.catalog import ResourceMetadata, ResourceRequirements, ResourceType, resource_catalog


if PYQT6_AVAILABLE:

    class ResourceCatalogPanel(QWidget):
        """Panel for viewing and managing system resources."""

        def __init__(self):
            super().__init__()
            self._init_ui()
            self.load_resources()

        def _init_ui(self) -> None:
            layout = QVBoxLayout()

            title = QLabel("System Resource Catalog")
            title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            layout.addWidget(title)

            toolbar = QHBoxLayout()
            self.refresh_button = QPushButton("Refresh Catalog")
            self.refresh_button.clicked.connect(self.refresh_resources)
            toolbar.addWidget(self.refresh_button)
            toolbar.addStretch()
            layout.addLayout(toolbar)

            self.table = QTableWidget(0, 8)
            self.table.setHorizontalHeaderLabels(
                [
                    "Name",
                    "Type",
                    "Version",
                    "Install Path",
                    "Capabilities",
                    "Discovery",
                    "Available",
                    "Last Seen",
                ]
            )
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            layout.addWidget(self.table)

            layout.addWidget(self._build_manual_registration_box())
            layout.addStretch()
            self.setLayout(layout)

        def _build_manual_registration_box(self) -> QGroupBox:
            group = QGroupBox("Register Custom Resource")
            form_layout = QVBoxLayout()

            row1 = QHBoxLayout()
            self.name_input = QLineEdit()
            self.name_input.setPlaceholderText("Resource name")
            row1.addWidget(QLabel("Name:"))
            row1.addWidget(self.name_input)

            self.type_combo = QComboBox()
            for resource_type in ResourceType:
                self.type_combo.addItem(resource_type.value.title(), resource_type.value)
            row1.addWidget(QLabel("Type:"))
            row1.addWidget(self.type_combo)
            form_layout.addLayout(row1)

            row2 = QHBoxLayout()
            self.version_input = QLineEdit()
            self.version_input.setPlaceholderText("Version (optional)")
            row2.addWidget(QLabel("Version:"))
            row2.addWidget(self.version_input)

            self.path_input = QLineEdit()
            self.path_input.setPlaceholderText("Install path (optional)")
            row2.addWidget(QLabel("Install Path:"))
            row2.addWidget(self.path_input)
            form_layout.addLayout(row2)

            row3 = QHBoxLayout()
            self.capabilities_input = QLineEdit()
            self.capabilities_input.setPlaceholderText("Capabilities (comma separated)")
            row3.addWidget(QLabel("Capabilities:"))
            row3.addWidget(self.capabilities_input)

            self.discovery_input = QLineEdit()
            self.discovery_input.setPlaceholderText("Discovery source (optional)")
            row3.addWidget(QLabel("Discovery:"))
            row3.addWidget(self.discovery_input)
            form_layout.addLayout(row3)

            self.metadata_input = QTextEdit()
            self.metadata_input.setPlaceholderText("Metadata (JSON object, optional)")
            form_layout.addWidget(QLabel("Metadata:"))
            form_layout.addWidget(self.metadata_input)

            self.register_button = QPushButton("Register Resource")
            self.register_button.clicked.connect(self.register_resource)
            form_layout.addWidget(self.register_button, alignment=Qt.AlignmentFlag.AlignRight)

            group.setLayout(form_layout)
            return group

        def _set_table_row(self, row: int, values: List[str]) -> None:
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, column, item)

        def load_resources(self) -> None:
            try:
                resources = asyncio.run(resource_catalog.get_resources(available_only=False))
            except RuntimeError:
                # If already inside an event loop, schedule via create_task
                resources = []

            self.table.setRowCount(len(resources))
            for index, resource in enumerate(sorted(resources, key=lambda r: r.name.lower())):
                capabilities = ", ".join(resource.capability_tags)
                last_seen = resource.last_seen.isoformat() if resource.last_seen else "-"
                self._set_table_row(
                    index,
                    [
                        resource.name,
                        resource.resource_type.value,
                        resource.version or "-",
                        resource.install_path or "-",
                        capabilities or "-",
                        resource.discovery_source or "-",
                        "Yes" if resource.available else "No",
                        last_seen,
                    ],
                )

        def refresh_resources(self) -> None:
            try:
                asyncio.run(resource_catalog.refresh(force=True))
                self.load_resources()
            except Exception as exc:  # pragma: no cover - user feedback only
                QMessageBox.critical(self, "Resource Catalog", f"Failed to refresh resources: {exc}")

        def _parse_metadata(self) -> Dict[str, Any]:
            text = self.metadata_input.toPlainText().strip()
            if not text:
                return {}
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid metadata JSON: {exc}")
            raise ValueError("Metadata must be a JSON object")

        def register_resource(self) -> None:
            name = self.name_input.text().strip()
            install_path = self.path_input.text().strip() or None
            version = self.version_input.text().strip() or None
            discovery_source = self.discovery_input.text().strip() or "manual"
            capabilities_text = self.capabilities_input.text().strip()
            capability_tags = [tag.strip().lower() for tag in capabilities_text.split(",") if tag.strip()]

            if not name:
                QMessageBox.warning(self, "Resource Catalog", "Resource name is required.")
                return

            try:
                metadata = self._parse_metadata()
                min_requirements = metadata.pop("min_requirements", None)
                max_requirements = metadata.pop("max_requirements", None)

                dependencies = metadata.pop("dependencies", [])
                if dependencies and not isinstance(dependencies, list):
                    raise ValueError("Dependencies must be provided as a list")

                resource_metadata = ResourceMetadata(
                    name=name,
                    resource_type=ResourceType(self.type_combo.currentData()),
                    version=version,
                    install_path=install_path,
                    dependencies=dependencies,
                    min_requirements=ResourceRequirements(**min_requirements) if min_requirements else None,
                    max_requirements=ResourceRequirements(**max_requirements) if max_requirements else None,
                    capability_tags=capability_tags,
                    discovery_source=discovery_source,
                    metadata=metadata,
                )

                asyncio.run(resource_catalog.register_custom_resource(resource_metadata))
                self.load_resources()
                QMessageBox.information(self, "Resource Catalog", "Resource registered successfully.")
                self._reset_form()
            except ValueError as exc:
                QMessageBox.warning(self, "Resource Catalog", str(exc))
            except Exception as exc:  # pragma: no cover
                QMessageBox.critical(self, "Resource Catalog", f"Failed to register resource: {exc}")

        def _reset_form(self) -> None:
            self.name_input.clear()
            self.version_input.clear()
            self.path_input.clear()
            self.capabilities_input.clear()
            self.discovery_input.clear()
            self.metadata_input.clear()

else:  # pragma: no cover - simplified fallback when PyQt6 is unavailable

    class ResourceCatalogPanel:  # type: ignore[override]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("PyQt6 is required for the ResourceCatalogPanel")
