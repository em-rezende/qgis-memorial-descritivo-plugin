# -*- coding: utf-8 -*-
import math
from typing import List, Dict, Any, Tuple
from qgis.core import QgsPointXY, QgsGeometry


class GeometryCalculator:
    """Calculadora e utilitários geométricos do complemento."""

    @staticmethod
    def calcular_orientacao(nodes: List[QgsPointXY]) -> bool:
        """Retorna True para sentido Horário e False para Anti-Horário (Shoelace formula)."""
        soma = 0.0
        n = len(nodes)
        for i in range(n):
            p1 = nodes[i]
            p2 = nodes[(i + 1) % n]
            soma += (p2.x() - p1.x()) * (p2.y() + p1.y())
        return soma > 0

    @staticmethod
    def reorientar_nodes(nodes: List[QgsPointXY], tornar_horario: bool) -> List[QgsPointXY]:
        """Garante a orientação desejada da lista de nós."""
        atual_horario = GeometryCalculator.calcular_orientacao(nodes)
        if atual_horario != tornar_horario:
            return list(reversed(nodes))
        return list(nodes)

    @staticmethod
    def calcular_area_perimetro(nodes: List[QgsPointXY]) -> Tuple[float, float]:
        """Calcula área em m² e perímetro em metros usando QgsGeometry."""
        if len(nodes) < 3:
            return 0.0, 0.0
        geom = QgsGeometry.fromPolygonXY([nodes + [nodes[0]]])
        return abs(geom.area()), geom.length()

    @staticmethod
    def calcular_azimute(p1: QgsPointXY, p2: QgsPointXY) -> Tuple[float, str]:
        """Calcula o azimute em radianos e formatado em Sexagesimal DMS."""
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        az_rad = math.atan2(dx, dy)
        if az_rad < 0:
            az_rad += 2 * math.pi

        graus_tot = math.degrees(az_rad)
        g = int(graus_tot)
        m = int((graus_tot - g) * 60)
        s = (graus_tot - g - m / 60.0) * 3600.0

        if s >= 59.999:
            s = 0.0
            m += 1
            if m >= 60:
                m = 0
                g = (g + 1) % 360

        dms_str = f'{g:02d}°{m:02d}\'{s:05.2f}"'
        return az_rad, dms_str

    @staticmethod
    def calcular_deflexao(az1_rad: float, az2_rad: float) -> float:
        """Calcula o ângulo de deflexão angular entre dois azimutes consecutivos em graus."""
        diff = math.degrees(az2_rad - az1_rad)
        while diff > 180.0:
            diff -= 360.0
        while diff < -180.0:
            diff += 360.0
        return diff

    @staticmethod
    def processar_segmentos(nodes: List[QgsPointXY],
                            detectar_curvas: bool = True,
                            tol_deflexao: float = 15.0) -> List[Dict[str, Any]]:
        n = len(nodes)
        if n < 3:
            return []

        # Pré-calcula arestas individuais
        arestas = []
        for i in range(n):
            p1 = nodes[i]
            p2 = nodes[(i + 1) % n]
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            dist = math.hypot(dx, dy)
            az_rad, az_str = GeometryCalculator.calcular_azimute(p1, p2)
            arestas.append({
                'idx': i,
                'p1': p1,
                'p2': p2,
                'dist': dist,
                'az_rad': az_rad,
                'az_str': az_str
            })

        segmentos_finais = []

        if not detectar_curvas:
            for i, a in enumerate(arestas):
                segmentos_finais.append({
                    'de': f"V{i + 1}",
                    'para': f"V{1 if i == n - 1 else i + 2}",
                    'p1': a['p1'],
                    'p2': a['p2'],
                    'dist': a['dist'],
                    'az': a['az_str'],
                    'is_curva': False,
                    'raio': 0.0,
                    'arco': 0.0,
                    'corda': 0.0,
                    'sentido_curva': ""
                })
            return segmentos_finais

        i = 0
        v_counter = 1  # Contador sequencial simplificado dos trechos visíveis

        # Primeira passagem: agrupa curvas e determina a lista de segmentos simplificados
        blocos = []
        while i < n:
            bloco_curva = GeometryCalculator._tentar_agrupar_curva(nodes, arestas, i, tol_deflexao)
            if bloco_curva:
                blocos.append(bloco_curva['segmento'])
                i = bloco_curva['proximo_i']
            else:
                a = arestas[i]
                blocos.append({
                    'de': '',
                    'para': '',
                    'p1': a['p1'],
                    'p2': a['p2'],
                    'dist': a['dist'],
                    'az': a['az_str'],
                    'is_curva': False,
                    'raio': 0.0,
                    'arco': 0.0,
                    'corda': 0.0,
                    'sentido_curva': ""
                })
                i += 1

        # Segunda passagem: aplica a numeração estritamente sequencial (V1, V2, V3...)
        total_blocos = len(blocos)
        for idx, seg in enumerate(blocos):
            v_de = f"V{idx + 1}"
            v_para = "V1" if idx == total_blocos - 1 else f"V{idx + 2}"
            
            seg['de'] = v_de
            seg['para'] = v_para
            segmentos_finais.append(seg)

        return segmentos_finais

    @staticmethod
    def _tentar_agrupar_curva(nodes: List[QgsPointXY],
                              arestas: List[Dict[str, Any]],
                              start_idx: int,
                              tol_deflexao: float) -> Any:
        n = len(arestas)
        if start_idx >= n - 1:
            return None

        # Trava 1: Se a sub-aresta for maior que 8.0m, é uma reta e não parte de uma curva discretizada
        if arestas[start_idx]['dist'] > 8.0:
            return None

        deflexao_inicial = GeometryCalculator.calcular_deflexao(
            arestas[start_idx]['az_rad'], arestas[start_idx + 1]['az_rad']
        )

        # Trava 2: Ignora variações insignificantes (< 0.5º) e deflexões acima do limite tolerado
        if abs(deflexao_inicial) > tol_deflexao or abs(deflexao_inicial) < 0.5:
            return None

        sentido = "DIREITA" if deflexao_inicial > 0 else "ESQUERDA"
        indices_curva = [start_idx, start_idx + 1]
        curr_idx = start_idx + 1

        while curr_idx + 1 < n:
            # Trava 3: Se o próximo segmento for uma reta (dist > 8.0m), encerra a curva atual imediatamente
            if arestas[curr_idx + 1]['dist'] > 8.0:
                break

            deflexao_prox = GeometryCalculator.calcular_deflexao(
                arestas[curr_idx]['az_rad'], arestas[curr_idx + 1]['az_rad']
            )

            mesmo_sentido = (deflexao_prox > 0) == (deflexao_inicial > 0)
            
            if mesmo_sentido and 0.5 <= abs(deflexao_prox) <= tol_deflexao:
                indices_curva.append(curr_idx + 1)
                curr_idx += 1
            else:
                break

        if len(indices_curva) < 2:
            return None

        p_inicio = arestas[indices_curva[0]]['p1']
        p_fim = arestas[indices_curva[-1]]['p2']

        dx = p_fim.x() - p_inicio.x()
        dy = p_fim.y() - p_inicio.y()
        corda = math.hypot(dx, dy)
        arco = sum(arestas[k]['dist'] for k in indices_curva)

        az_in = arestas[indices_curva[0]]['az_rad']
        az_out = arestas[indices_curva[-1]]['az_rad']
        deflexao_total_deg = abs(GeometryCalculator.calcular_deflexao(az_in, az_out))
        deflexao_total_rad = math.radians(deflexao_total_deg)

        if deflexao_total_rad > 0.001:
            raio = corda / (2.0 * math.sin(deflexao_total_rad / 2.0))
        else:
            raio = 0.0

        seg_curva = {
            'de': '',
            'para': '',
            'p1': p_inicio,
            'p2': p_fim,
            'dist': arco,
            'az': f"CURVA - R={raio:.2f}m",
            'is_curva': True,
            'raio': raio,
            'arco': arco,
            'corda': corda,
            'sentido_curva': sentido
        }

        return {
            'segmento': seg_curva,
            'indices': indices_curva,
            'proximo_i': indices_curva[-1] + 1
        }
    
    @staticmethod
    def gerar_chave_segmento(p1: QgsPointXY, p2: QgsPointXY) -> str:
        """Gera uma chave única e determinística para o segmento com base nas coordenadas."""
        pts = sorted([(round(p1.x(), 3), round(p1.y(), 3)), (round(p2.x(), 3), round(p2.y(), 3))])
        return f"{pts[0][0]:.3f}_{pts[0][1]:.3f}__{pts[1][0]:.3f}_{pts[1][1]:.3f}"
        