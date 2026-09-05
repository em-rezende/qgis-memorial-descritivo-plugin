# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtWidgets import QMessageBox, QAction
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.core import QgsVectorLayer, Qgis, QgsWkbTypes

# Importa o diálogo da nova estrutura
from .ui.memorial_dialog import MemorialDialog


class MemorialPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action_run = None
        self.action_help = None
        self.dlg = None

    def initGui(self):
        # 1. Caminhos dos ícones SVG
        icon_main_path = os.path.join(self.plugin_dir, 'memorial_descritivo.svg')
        icon_help_path = os.path.join(self.plugin_dir, 'memorial_descritivo_help.svg')

        icon_main = QIcon(icon_main_path) if os.path.exists(icon_main_path) else QIcon()
        icon_help = QIcon(icon_help_path) if os.path.exists(icon_help_path) else QIcon()

        # 2. Ação principal (Gerar Memorial Descritivo)
        self.action_run = QAction(icon_main, "Gerar Memorial Descritivo", self.iface.mainWindow())
        self.action_run.setStatusTip("Gerar Memorial Descritivo do polígono selecionado")
        self.action_run.triggered.connect(self.run)

        # 3. Ação de Ajuda
        self.action_help = QAction(icon_help, "Ajuda", self.iface.mainWindow())
        self.action_help.setStatusTip("Abre a documentação do Memorial Descritivo")
        self.action_help.triggered.connect(self.open_help)

        # 4. Adiciona as ações ao Menu "Vetor -> Memorial Descritivo"
        self.iface.addPluginToVectorMenu("&Memorial Descritivo", self.action_run)
        self.iface.addPluginToVectorMenu("&Memorial Descritivo", self.action_help)

        # 5. Criar Toolbar DEDICADA e EXCLUSIVA
        self.toolbar = self.iface.addToolBar("Memorial Descritivo")
        self.toolbar.setObjectName("ToolbarMemorialDescritivo")
        
        # Adiciona a ação principal à nova toolbar
        self.toolbar.addAction(self.action_run)

    def unload(self):
        # Remove do menu Vetor e da toolbar
        if self.action_run:
            self.iface.removePluginVectorMenu("&Memorial Descritivo", self.action_run)
            self.iface.removeToolBarIcon(self.action_run)
        if self.action_help:
            self.iface.removePluginVectorMenu("&Memorial Descritivo", self.action_help)
        
        # Remove a toolbar
        if hasattr(self, 'toolbar'):
            self.iface.mainWindow().removeToolBar(self.toolbar)

    def open_help(self):
        """Abre o arquivo index.html da pasta help no navegador padrão."""
        help_path = os.path.join(self.plugin_dir, 'help', 'index.html')
        if os.path.exists(help_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(help_path))
        else:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Ajuda Não Encontrada",
                f"O arquivo de ajuda não foi localizado em:\n{help_path}"
            )

    def run(self):
        """Executa o plugin com verificações completas da camada e feição."""
        # 1. Obter a camada ativa no painel do QGIS
        layer = self.iface.activeLayer()

        # 2. Verificar se existe uma camada ativa válida
        if not layer or not layer.isValid():
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Camada Não Selecionada",
                "Por favor, selecione uma camada vetorial no painel de camadas antes de executar o plugin."
            )
            return

        # 3. Verificar se a camada é VETORIAL (evita AttributeError em Raster, Mesh, etc.)
        if not isinstance(layer, QgsVectorLayer):
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Tipo de Camada Inválido",
                f"A camada ativa ('{layer.name()}') não é uma camada vetorial.\n\n"
                "O Gerador de Memorial Descritivo requer uma camada VETORIAL de Polígonos."
            )
            return

        # 4. Verificar se a camada é de POLÍGONOS (compatível com QGIS 3.x e QGIS 4.x)
        try:
            is_polygon_layer = (layer.geometryType() == Qgis.GeometryType.Polygon)
        except AttributeError:
            is_polygon_layer = (layer.geometryType() == QgsWkbTypes.PolygonGeometry)

        if not is_polygon_layer:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Geometria Incompatível",
                f"A camada vetorial ('{layer.name()}') não possui geometria do tipo Polígono.\n\n"
                "Por favor, selecione uma camada de Polígonos ou Multipolígonos."
            )
            return

        # 5. Verificar seleção de feições
        selected_features = layer.selectedFeatures()
        if len(selected_features) == 0:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Nenhuma Feição Selecionada",
                f"Nenhum polígono está selecionado na camada '{layer.name()}'.\n\n"
                "Por favor, selecione exatamente UM polígono no mapa."
            )
            return

        if len(selected_features) > 1:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Múltiplas Feições Selecionadas",
                f"Foram selecionados {len(selected_features)} polígonos.\n\n"
                "Por favor, selecione exatamente UM polígono para gerar o memorial descritivo."
            )
            return

        # 6. Validar a geometria da feição selecionada
        feature = selected_features[0]
        geom = feature.geometry()

        if not geom or geom.isEmpty():
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Geometria Inválida",
                "A feição selecionada possui uma geometria vazia ou inválida."
            )
            return

        # 7. Extrair vértices do polígono
        try:
            if geom.isMultipart():
                polygon_geom = geom.asMultiPolygon()[0]
            else:
                polygon_geom = geom.asPolygon()
        except Exception:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Erro de Geometria",
                "Não foi possível extrair a geometria do polígono selecionado."
            )
            return

        if not polygon_geom or len(polygon_geom[0]) < 3:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Geometria Insuficiente",
                "O polígono selecionado possui menos de 3 vértices."
            )
            return

        nodes = polygon_geom[0]
        # Remove o último ponto se for igual ao primeiro (fechamento do polígono)
        if len(nodes) > 1 and nodes[0] == nodes[-1]:
            nodes = nodes[:-1]

        # 8. Obter informações de CRS e ID da feição
        crs = layer.crs()
        crs_name = crs.description() or "SIRGAS 2000"
        crs_auth_id = crs.authid() or "EPSG:31983"
        feature_id = feature.id()

        # 9. Instancia e exibe o diálogo principal do plugin
        self.dlg = MemorialDialog(
            iface=self.iface,
            feature_id=feature_id,
            nodes=nodes,
            crs_name=crs_name,
            crs_auth_id=crs_auth_id,
            parent=self.iface.mainWindow()
        )

        self.dlg.show()
        self.dlg.exec()
