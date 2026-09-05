# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QMessageBox, QFileDialog, QApplication
)
from qgis.PyQt.QtGui import QFont

from ..utils.formatters import Formatter


class PreviewDialog(QDialog):
    """Diálogo de pré-visualização do memorial descritivo."""

    def __init__(self, texto_memorial: str, parent=None):
        super().__init__(parent)
        self.texto_memorial = texto_memorial
        self.parent_dialog = parent
        self.setWindowTitle("Pré-visualização do Memorial Descritivo")
        self.resize(750, 600)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.txt_area = QTextEdit(self)
        self.txt_area.setFont(QFont("Consolas", 10))
        self.txt_area.setPlainText(self.texto_memorial)
        layout.addWidget(self.txt_area)

        btn_layout = QHBoxLayout()

        self.btn_copiar = QPushButton("Copiar para a Área de Transferência", self)
        self.btn_copiar.clicked.connect(self._copiar_texto)
        btn_layout.addWidget(self.btn_copiar)

        self.btn_exportar = QPushButton("Exportar Memorial...", self)
        self.btn_exportar.clicked.connect(self._exportar_arquivo)
        btn_layout.addWidget(self.btn_exportar)

        btn_layout.addStretch()

        self.btn_fechar = QPushButton("Fechar", self)
        self.btn_fechar.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_fechar)

        layout.addLayout(btn_layout)

    def _copiar_texto(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.txt_area.toPlainText())
        QMessageBox.information(self, "Copiado", "Texto copiado com sucesso!")

    def _exportar_arquivo(self):
        conteudo = self.txt_area.toPlainText()
        if not conteudo.strip():
            QMessageBox.warning(self, "Aviso", "Não há texto para exportar.")
            return

        nome_lote = "Descritivo"
        if self.parent_dialog and hasattr(self.parent_dialog, 'txt_lote_quadra'):
            texto = self.parent_dialog.txt_lote_quadra.text().strip()
            if texto:
                nome_lote = Formatter.sanitizar_nome_arquivo(texto)
                nome_lote = "_".join(nome_lote.split())

        caminho, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Memorial Descritivo",
            f"Memorial_{nome_lote}.txt",
            "Arquivo de Texto (*.txt);;Documento Word (*.doc);;Página Web (*.html);;Todos os Arquivos (*)"
        )

        if not caminho:
            return

        try:
            ext = os.path.splitext(caminho)[1].lower()

            if ext in ['.doc', '.html']:
                paragrafos = conteudo.split('\n\n')
                body_html = ""
                for p in paragrafos:
                    if p.strip():
                        p_formatted = p.replace('\n', '<br>')
                        body_html += f"<p style='text-align: justify; text-indent: 30px; line-height: 1.5; font-family: 'Helvetica', serif; font-size: 12pt; margin-bottom: 12px;'>{p_formatted}</p>\n"

                conteudo_saida = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8">
<style>body {{ margin: 2.5cm; padding: 0; }}</style>
</head>
<body>{body_html}</body></html>"""
            else:
                conteudo_saida = conteudo

            with open(caminho, 'w', encoding='utf-8') as f:
                f.write(conteudo_saida)

            QMessageBox.information(self, "Sucesso", f"Memorial salvo em {ext.upper() if ext else 'TXT'}!")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Não foi possível salvar:\n{str(e)}")
            