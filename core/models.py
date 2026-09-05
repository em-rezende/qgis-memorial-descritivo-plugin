# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from qgis.core import QgsPointXY

from ..utils.formatters import Formatter


@dataclass
class Segmento:
    """Representa um segmento do perímetro."""
    seg_key: str
    de: str
    para: str
    p1_n: float
    p1_e: float
    p2_n: float
    p2_e: float
    az: str
    dist: float
    is_curva: bool = False
    raio: float = 0.0
    arco: float = 0.0
    corda: float = 0.0
    sentido_curva: str = ""
    confrontante: str = ""
    requer_assinatura: bool = True
    norte_str: str = ""
    este_str: str = ""

    def __post_init__(self):
        """Formata coordenadas após inicialização."""
        if not self.norte_str:
            self.norte_str = Formatter.formatar_numero_br(self.p1_n, 2)
        if not self.este_str:
            self.este_str = Formatter.formatar_numero_br(self.p1_e, 2)


@dataclass
class DadosImovel:
    """Dados completos do imóvel para geração do memorial."""
    feature_id: str
    v1_index: int = 1
    titulo_proj: str = "Projeto de Retificação de Área"
    lote: str = "Lote 01"
    quadra: str = "Quadra 01"
    bairro: str = "Bairro Centro"
    matricula: str = "00.001"
    cidade: str = "Belo Horizonte"
    uf: str = "MG"
    proprietario: str = ""
    resp_tecnico: str = ""
    confrontantes_bloco: str = ""
    segmentos: List[Segmento] = field(default_factory=list)
    confrontantes_salvos: Dict[str, Dict] = field(default_factory=dict)
    raw_nodes: List[QgsPointXY] = field(default_factory=list)

    @property
    def lote_quadra(self) -> str:
        """Monta a string concatenada para compatibilidade e exibição."""
        partes = [p.strip() for p in [self.lote, self.quadra, self.bairro] if p and p.strip()]
        return " - ".join(partes)


@dataclass
class GeometriaImovel:
    """Dados geométricos calculados do imóvel."""
    area_m2: float = 0.0
    perimetro: float = 0.0
    is_clockwise: bool = True
    num_vertices: int = 0

    @property
    def area_ha(self) -> float:
        return self.area_m2 / 10000.0

    @property
    def area_alq_sp(self) -> float:
        return self.area_m2 / 24200.0
        