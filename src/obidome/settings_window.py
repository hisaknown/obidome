"""Settings window for Obidome application."""

import json
from typing import get_args

from pydantic import BaseModel
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from obidome.settings import ObidomeSettings


class SettingsWindow(QDialog):
    """Settings window for Obidome application."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the SettingsWindow."""
        super().__init__(parent)
        self.setWindowTitle("Obidome Settings")
        self._current_settings = ObidomeSettings()
        self.init_ui()

    def generate_widgets[T: BaseModel](
        self, form_layout: QFormLayout, model: type[T], current: T
    ) -> dict[str, QWidget | dict]:
        """Recursively generate widgets for the model fields."""
        ret = {}
        for k, v in model.model_fields.items():
            if v.annotation is None:
                continue

            if v.annotation in (int, float):
                widget = QSpinBox()
                widget.setRange(-1000000, 1000000)
                widget.setValue(getattr(current, k))
                form_layout.addRow(f"{k} ({v.description}):", widget)
            elif v.annotation is str:
                if v.description and "multiline" in v.description.lower():
                    widget = QTextEdit()
                    widget.setPlainText(getattr(current, k))
                    widget.setMinimumHeight(60)
                else:
                    widget = QLineEdit(getattr(current, k))
                form_layout.addRow(f"{k} ({v.description}):", widget)
            elif str(v.annotation).startswith("typing.Literal"):
                widget = QComboBox()
                for option in get_args(v.annotation):
                    widget.addItem(str(option))
                widget.setCurrentText(str(getattr(current, k)))
                form_layout.addRow(f"{k} ({v.description}):", widget)
            elif issubclass(v.annotation, BaseModel):
                # Nested model
                nested_form_layout = QFormLayout()
                form_layout.addRow(f"{k} ({v.description}):", nested_form_layout)
                widget = self.generate_widgets(nested_form_layout, v.annotation, getattr(current, k))
            else:
                continue  # Unsupported type
            ret[k] = widget
        return ret

    def parse_widgets_into_dict(self, widgets: dict[str, QWidget | dict]) -> dict:
        """Recursively parse widget values into a dictionary for model_validate."""
        result = {}
        for k, widget in widgets.items():
            if isinstance(widget, QSpinBox):
                result[k] = widget.value()
            elif isinstance(widget, QLineEdit):
                result[k] = widget.text()
            elif isinstance(widget, QTextEdit):
                result[k] = widget.toPlainText()
            elif isinstance(widget, QComboBox):
                result[k] = widget.currentText()
            elif isinstance(widget, dict):
                result[k] = self.parse_widgets_into_dict(widget)
        return result

    def init_ui(self) -> None:
        """Initialize the UI components."""
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.new_settings_widget = self.generate_widgets(form_layout, ObidomeSettings, self._current_settings)

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)  # type: ignore[arg-type] (Save and Cancel actually exist)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def accept(self) -> None:
        """Accept the changes and save settings."""
        new_settings = ObidomeSettings.model_validate_json(
            json.dumps(self.parse_widgets_into_dict(self.new_settings_widget))
        )
        self._current_settings = new_settings
        self._current_settings.save()
        super().accept()
