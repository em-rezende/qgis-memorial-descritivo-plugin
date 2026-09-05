# -*- coding: utf-8 -*-
from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsField,
    QgsProject, QgsPalLayerSettings, QgsVectorLayerSimpleLabeling,
    QgsTextFormat, QgsTextBufferSettings, QgsLayerTreeLayer
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QFont

from ..utils.formatters import Formatter


class MapAnnotator:
    def __init__(self, crs_auth_id):
        self.crs_auth_id = crs_auth_id
        self.group_name = "Anotações do Memorial"

    def remover_anotacoes(self, id_imovel=None):
        """Remove todas as anotações do imóvel especificado."""
        project = QgsProject.instance()
        root = project.layerTreeRoot()

        id_str = str(id_imovel).strip() if id_imovel is not None else ""

        # Procura TODOS os grupos com o nome "Anotações do Memorial"
        grupos_para_remover = []
        self._encontrar_grupos_por_nome(root, self.group_name, grupos_para_remover)

        if not grupos_para_remover:
            return

        layers_to_remove = []

        for grupo in grupos_para_remover:
            if id_str:
                # Procura o subgrupo específico dentro deste grupo
                subgrupo = grupo.findGroup(id_str)
                if subgrupo:
                    # Coleta todas as camadas do subgrupo
                    self._coletar_todas_camadas(subgrupo, layers_to_remove)
                    # Remove o subgrupo
                    grupo.removeChildNode(subgrupo)
            else:
                # Remove todo o grupo
                self._coletar_todas_camadas(grupo, layers_to_remove)
                root.removeChildNode(grupo)

        # Remove as camadas do projeto
        if layers_to_remove:
            project.removeMapLayers(layers_to_remove)

        # Limpa grupos vazios
        self._limpar_grupos_vazios(root)

    def _encontrar_grupos_por_nome(self, node, nome, lista_grupos):
        """Encontra recursivamente todos os grupos com um determinado nome."""
        for child in node.children():
            if isinstance(child, QgsLayerTreeLayer):
                continue
            elif child.name() == nome:
                lista_grupos.append(child)
            else:
                self._encontrar_grupos_por_nome(child, nome, lista_grupos)

    def _coletar_todas_camadas(self, node, layer_ids):
        """Coleta recursivamente todos os IDs das camadas em um nó."""
        for child in node.children():
            if isinstance(child, QgsLayerTreeLayer):
                layer_id = child.layerId()
                if layer_id:
                    layer_ids.append(layer_id)
            else:
                self._coletar_todas_camadas(child, layer_ids)

    def _limpar_grupos_vazios(self, node):
        """Remove recursivamente todos os grupos vazios."""
        filhos_para_remover = []
        for child in node.children():
            if not isinstance(child, QgsLayerTreeLayer):
                self._limpar_grupos_vazios(child)
                if len(child.children()) == 0:
                    filhos_para_remover.append(child)

        for child in filhos_para_remover:
            node.removeChildNode(child)

    def _limpar_grupo(self, group):
        """Remove todas as camadas de um grupo sem remover o grupo."""
        if not group:
            return

        project = QgsProject.instance()
        layers_to_remove = []

        # Coleta todas as camadas do grupo
        self._coletar_todas_camadas(group, layers_to_remove)

        # Remove as camadas do projeto
        if layers_to_remove:
            project.removeMapLayers(layers_to_remove)

    def _get_or_create_group(self, id_imovel=""):
        """Obtém ou cria o grupo/subgrupo para o imóvel."""
        root = QgsProject.instance().layerTreeRoot()

        # Primeiro, limpa grupos duplicados
        grupos_existentes = []
        self._encontrar_grupos_por_nome(root, self.group_name, grupos_existentes)

        # Remove grupos duplicados (mantém apenas o primeiro)
        for i in range(1, len(grupos_existentes)):
            grupo = grupos_existentes[i]
            layers_to_remove = []
            self._coletar_todas_camadas(grupo, layers_to_remove)
            if layers_to_remove:
                QgsProject.instance().removeMapLayers(layers_to_remove)
            root.removeChildNode(grupo)

        # Agora procura ou cria o grupo principal
        group_principal = root.findGroup(self.group_name)
        if not group_principal:
            group_principal = root.addGroup(self.group_name)

        id_str = str(id_imovel).strip() if id_imovel else ""
        if not id_str:
            return group_principal

        # Procura ou cria o subgrupo
        subgrupo = group_principal.findGroup(id_str)
        if not subgrupo:
            subgrupo = group_principal.addGroup(id_str)

        return subgrupo

    def _adicionar_ao_projeto(self, layer, id_imovel=""):
        """Adiciona uma camada ao projeto dentro do grupo/subgrupo correto."""
        project = QgsProject.instance()

        # Obtém o grupo alvo (isso já limpa duplicatas)
        group_alvo = self._get_or_create_group(id_imovel=id_imovel)

        # Remove a camada existente com o mesmo nome no grupo
        for child in group_alvo.children():
            if isinstance(child, QgsLayerTreeLayer):
                existing_layer = child.layer()
                if existing_layer and existing_layer.name() == layer.name():
                    project.removeMapLayer(existing_layer.id())
                    break

        # Adiciona a camada ao projeto (sem adicionar na raiz)
        project.addMapLayer(layer, False)

        # Adiciona a camada ao grupo
        group_alvo.addLayer(layer)
        layer.triggerRepaint()

    def criar_camada_pontos(self, vertices, id_imovel=""):
        """Cria a camada de vértices."""
        layer = QgsVectorLayer(f"Point?crs={self.crs_auth_id}", "Vértices", "memory")
        pr = layer.dataProvider()
        pr.addAttributes([QgsField("nome", QVariant.String)])
        layer.updateFields()

        features = []
        for v in vertices:
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(v['x'], v['y'])))
            feat.setAttributes([v['nome']])
            features.append(feat)

        pr.addFeatures(features)
        layer.updateExtents()

        self._aplicar_rotulo_ponto(layer, "nome", size=9, color=QColor(180, 0, 0), bold=True)
        self._adicionar_ao_projeto(layer, id_imovel=id_imovel)
        return layer

    def criar_camada_segmentos(self, segmentos, id_imovel=""):
        """Cria a camada de segmentos com azimutes e distâncias."""
        layer = QgsVectorLayer(f"LineString?crs={self.crs_auth_id}", "Azimute e Distância", "memory")
        pr = layer.dataProvider()
        pr.addAttributes([QgsField("texto_completo", QVariant.String)])
        layer.updateFields()

        features = []
        for seg in segmentos:
            feat = QgsFeature()
            geom = QgsGeometry.fromPolylineXY([
                QgsPointXY(seg.p1_e, seg.p1_n),
                QgsPointXY(seg.p2_e, seg.p2_n)
            ])
            feat.setGeometry(geom)
            
            if seg.is_curva:
                raio_str = Formatter.formatar_numero_br(seg.raio, 2)
                texto = f"CURVA\nR={raio_str}m"
            else:
                az_text = seg.az if seg.az and str(seg.az).strip() else "00º00'00.00\""
                dist_text = Formatter.formatar_numero_br(seg.dist, 2)
                texto = f"Az={az_text}\nDist={dist_text}m"
            
            feat.setAttributes([texto])
            features.append(feat)

        pr.addFeatures(features)
        layer.updateExtents()

        self._aplicar_rotulo_linha_multilinha(layer, "texto_completo", size=8, color=QColor(15, 45, 120))
        self._adicionar_ao_projeto(layer, id_imovel=id_imovel)
        return layer

    def criar_camada_centro(self, dados, geometria, id_imovel=""):
        """Cria a camada de dados centrais do imóvel."""
        layer = QgsVectorLayer(f"Point?crs={self.crs_auth_id}", "Dados", "memory")
        pr = layer.dataProvider()
        pr.addAttributes([QgsField("info", QVariant.String)])
        layer.updateFields()

        pts = [QgsPointXY(seg.p1_e, seg.p1_n) for seg in dados['segmentos']]
        if len(pts) < 3:
            # Se não houver pontos suficientes, usa o primeiro ponto
            pt_centro = pts[0] if pts else QgsPointXY(0, 0)
        else:
            geom_poly = QgsGeometry.fromPolygonXY([pts])
            pt_centro = geom_poly.centroid().asPoint()

        loc_str = dados.get('lote_quadra', '')

        info = (
            f"IMÓVEL: {dados['titulo_proj']}\n"
            f"LOCALIZAÇÃO: {loc_str}\n"
            f"MATRÍCULA: {dados['matricula']}\n"
            f"ÁREA: {Formatter.formatar_numero_br(geometria.area_m2, 2)} m² "
            f"({Formatter.formatar_numero_br(geometria.area_ha, 4)} ha)\n"
            f"PERÍMETRO: {Formatter.formatar_numero_br(geometria.perimetro, 2)} m\n"
            f"MUNICÍPIO: {dados['cidade']}/{dados['uf']}"
        )

        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPointXY(pt_centro))
        feat.setAttributes([info])
        pr.addFeatures([feat])
        layer.updateExtents()

        self._aplicar_rotulo_centro(layer, "info", size=9, color=QColor(0, 0, 0))
        self._adicionar_ao_projeto(layer, id_imovel=id_imovel)
        return layer

    def _aplicar_rotulo_ponto(self, layer, campo, size=8, color=QColor("black"), bold=False):
        """Aplica rótulos para camadas de ponto."""
        settings = QgsPalLayerSettings()
        settings.fieldName = campo
        settings.enabled = True
        settings.displayAll = True
        
        try:
            settings.placement = QgsPalLayerSettings.AroundPoint
        except AttributeError:
            settings.placement = QgsPalLayerSettings.OverPoint

        settings.xOffset = 0
        settings.yOffset = 0

        fmt = QgsTextFormat()
        try:
            weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
            font = QFont("Arial", size, weight)
        except AttributeError:
            font = QFont("Arial", size, QFont.Bold if bold else QFont.Normal)
        
        fmt.setFont(font)
        fmt.setColor(color)
        fmt.setSize(size)

        buffer = QgsTextBufferSettings()
        buffer.setEnabled(True)
        buffer.setSize(1.0)
        buffer.setColor(QColor(255, 255, 255, 200))
        fmt.setBuffer(buffer)

        settings.setFormat(fmt)
        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.setLabelsEnabled(True)

    def _aplicar_rotulo_linha_multilinha(self, layer, campo, size=8, color=QColor("blue")):
        """Aplica rótulos multilinha para camadas de linha."""
        settings = QgsPalLayerSettings()
        settings.isExpression = True
        settings.fieldName = f"replace(\"{campo}\", '\\n', '\n\n')"
        settings.enabled = True
        settings.displayAll = True
        settings.placement = QgsPalLayerSettings.Line

        try:
            from qgis.core import QgsLabelLineSettings
            line_settings = settings.lineSettings()
            line_settings.setPlacementFlags(QgsLabelLineSettings.OnLine)
            line_settings.setAnchorPoint(QgsLabelLineSettings.AnchorCenter)
            settings.setLineSettings(line_settings)
        except (ImportError, AttributeError):
            try:
                settings.placementFlags = QgsPalLayerSettings.OnLine
                settings.anchorPoint = QgsPalLayerSettings.AnchorCenter
            except AttributeError:
                pass

        settings.dist = 0.0
        settings.xOffset = 0.0
        settings.yOffset = 0.0

        try:
            settings.repeatDistance = 0
        except AttributeError:
            pass

        try:
            settings.multilineAlign = QgsPalLayerSettings.MultiLineAlign.Center
        except AttributeError:
            try:
                settings.multilineAlign = QgsPalLayerSettings.Center
            except AttributeError:
                pass

        fmt = QgsTextFormat()
        try:
            font = QFont("Arial", size, QFont.Weight.Bold)
        except AttributeError:
            font = QFont("Arial", size, QFont.Bold)
        
        fmt.setFont(font)
        fmt.setColor(color)
        fmt.setSize(size)

        buffer = QgsTextBufferSettings()
        buffer.setEnabled(True)
        buffer.setSize(1.2)
        buffer.setColor(QColor(255, 255, 255, 230))
        fmt.setBuffer(buffer)

        settings.setFormat(fmt)
        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.setLabelsEnabled(True)

    def _aplicar_rotulo_centro(self, layer, campo, size=9, color=QColor("black")):
        """Aplica rótulos para camada de centro."""
        settings = QgsPalLayerSettings()
        settings.fieldName = campo
        settings.enabled = True
        settings.displayAll = True
        
        try:
            settings.placement = QgsPalLayerSettings.AroundPoint
        except AttributeError:
            settings.placement = QgsPalLayerSettings.OverPoint

        settings.xOffset = 0
        settings.yOffset = 0
        
        try:
            settings.multilineAlign = QgsPalLayerSettings.MultiLineAlign.Center
        except AttributeError:
            try:
                settings.multilineAlign = QgsPalLayerSettings.Center
            except AttributeError:
                pass

        fmt = QgsTextFormat()
        try:
            font = QFont("Arial", size, QFont.Weight.Bold)
        except AttributeError:
            font = QFont("Arial", size, QFont.Bold)
        
        fmt.setFont(font)
        fmt.setColor(color)
        fmt.setSize(size)

        buffer = QgsTextBufferSettings()
        buffer.setEnabled(True)
        buffer.setSize(1.5)
        buffer.setColor(QColor(255, 255, 255, 230))
        fmt.setBuffer(buffer)

        settings.setFormat(fmt)
        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.setLabelsEnabled(True)
        