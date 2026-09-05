# -*- coding: utf-8 -*-

def classFactory(iface):
    """Instancia o plugin no QGIS."""
    from .main import MemorialPlugin
    return MemorialPlugin(iface)