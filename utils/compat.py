# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont


class QtCompat:
    """Compatibilidade entre PyQt5 e PyQt6."""
    
    @staticmethod
    def get_align_center():
        """Retorna Qt.AlignCenter compatível com PyQt5/PyQt6."""
        try:
            return Qt.AlignmentFlag.AlignCenter
        except AttributeError:
            return Qt.AlignCenter
    
    @staticmethod
    def get_align_center_enum():
        """Retorna Qt.AlignCenter para uso em setAlignment de layouts."""
        try:
            return Qt.AlignmentFlag.AlignCenter
        except AttributeError:
            return Qt.AlignCenter
    
    @staticmethod
    def get_item_flags_read_only():
        """Retorna flags de leitura para QTableWidgetItem."""
        try:
            return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        except AttributeError:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled
    
    @staticmethod
    def get_item_flags_editable():
        """Retorna flags editáveis para QTableWidgetItem."""
        try:
            return (Qt.ItemFlag.ItemIsSelectable | 
                   Qt.ItemFlag.ItemIsEnabled | 
                   Qt.ItemFlag.ItemIsEditable)
        except AttributeError:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
    
    @staticmethod
    def create_font(family: str, size: int, bold: bool = False):
        """Cria uma fonte compatível com PyQt5/PyQt6."""
        try:
            # PyQt6 / QGIS 4.x
            weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
            return QFont(family, size, weight)
        except AttributeError:
            # PyQt5 / QGIS 3.x (fallback)
            weight = QFont.Bold if bold else QFont.Normal
            return QFont(family, size, weight)
            