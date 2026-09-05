# -*- coding: utf-8 -*-
from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QCheckBox

# Importar compatibilidade
from ..utils.compat import QtCompat


class CheckBoxWidget(QWidget):
    """Widget com checkbox centralizado para uso em tabelas."""

    def __init__(self, checked: bool = True, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCompat.get_align_center_enum())

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(checked)
        layout.addWidget(self.checkbox)

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()

    def set_checked(self, checked: bool):
        self.checkbox.setChecked(checked)