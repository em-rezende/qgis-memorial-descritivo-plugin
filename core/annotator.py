# -*- coding: utf-8 -*-
from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsField,
    QgsProject, QgsLayerTreeGroup, QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling, QgsTextFormat, QgsTextBufferSettings,
    QgsExpression, QgsLayerTreeLayer
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QFont

from ..utils.formatters import Formatter


class MapAnnotator:
    def __init__(self, crs_auth_id):
        self.crs_auth_id = crs_auth_id
        self.group_name = "Anotações do Memorial"

    def _get_or_create_group(self, id_imovel=""):
        root = QgsProject.instance().layerTreeRoot()
        group_principal = root.findGroup(self.group_name)
        if not group_principal:
            group_principal = root.addGroup(self.group_name)

        id_str = str(id_imovel).strip() if id_imovel else ""
        if not id_str:
            return group_principal

        subgrupo = group_principal.findGroup(id_str)
        if not subgrupo:
            subgrupo = group_principal.addGroup(id_str)

        return subgrupo

    def remover_anotacoes(self, id_imovel=None):
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup(self.group_name)
        if not group:
            return

        id_str = str(id_imovel).strip() if id_imovel is not None else ""

        if id_str:
            subgrupo = group.findGroup(id_str)
            if subgrupo:
                for child in subgrupo.children():
                    if isinstance(child, QgsLayerTreeLayer):
                        QgsProject.instance().removeMapLayer(child.layerId())
                group.removeChildNode(subgrupo)
        else:
            for child in group.findLayers():
                QgsProject.instance().removeMapLayer(child.layerId())
            root.removeChildNode(group)

        group = root.findGroup(self.group_name)
        if group and len(group.children()) == 0:
            root.removeChildNode(group)

    def criar_camada_pontos(self, vertices, id_imovel=""):
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
        """Cria camada com informações centrais do imóvel."""
        layer = QgsVectorLayer(f"Point?crs={self.crs_auth_id}", "Dados", "memory")
        pr = layer.dataProvider()
        pr.addAttributes([QgsField("info", QVariant.String)])
        layer.updateFields()

        pts = [QgsPointXY(seg.p1_e, seg.p1_n) for seg in dados['segmentos']]
        geom_poly = QgsGeometry.fromPolygonXY([pts])
        pt_centro = geom_poly.centroid().asPoint()

        # Montagem dinâmica com Lote, Quadra e Bairro concatenados
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
        layer.triggerRepaint()

    def _aplicar_rotulo_linha_multilinha(self, layer, campo, size=8, color=QColor("blue")):
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
        layer.triggerRepaint()
        
    def _aplicar_rotulo_centro(self, layer, campo, size=9, color=QColor("black")):
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
        layer.triggerRepaint()

    def _adicionar_ao_projeto(self, layer, id_imovel=""):
        QgsProject.instance().addMapLayer(layer, False)
        group = self._get_or_create_group(id_imovel=id_imovel)
        group.addLayer(layer)
        layer.triggerRepaint()
        