# -*- coding: utf-8 -*-
import re
from ..utils.formatters import Formatter

# Tenta importar qgis.core para pegar o CRS do projeto ativo como fallback
try:
    from qgis.core import QgsProject
except ImportError:
    QgsProject = None


class MemorialGenerator:
    """Gera o texto do memorial descritivo."""

    @staticmethod
    def _obter_info_src(crs) -> tuple:
        """
        Extrai Datum, Fuso UTM, Meridiano Central e flag indicando se é UTM
        a partir de um objeto QgsCoordinateReferenceSystem.
        Retorna uma tupla: (datum_str, fuso_str, mc_str, is_utm)
        Exemplo de retorno UTM: ("SIRGAS 2000", "19S", "69W", True)
        """
        # Fallback padrão
        datum_str = "SIRGAS 2000"
        fuso_str = "19S"
        mc_str = "69W"
        is_utm = True

        # Tenta pegar o CRS do projeto ativo no QGIS se o informado for Nulo
        if (not crs or not crs.isValid()) and QgsProject is not None:
            try:
                crs = QgsProject.instance().crs()
            except Exception:
                pass

        if not crs or not crs.isValid():
            return datum_str, fuso_str, mc_str, is_utm

        try:
            wkt = crs.toWkt()
            desc = crs.description()  # Ex: "SIRGAS 2000 / UTM zone 19S"
            proj_str = crs.toProj()   # Ex: "+proj=utm +zone=19 +south ..."

            # Verifica se o CRS é UTM
            is_utm = ("UTM" in desc.upper()) or ("+proj=utm" in proj_str.lower())

            # ----------------------------------------------------
            # 1. DATUM
            # ----------------------------------------------------
            if "SIRGAS 2000" in desc.upper() or "SIRGAS_2000" in wkt.upper() or "SIRGAS 2000" in wkt.upper():
                datum_str = "SIRGAS 2000"
            elif "SAD69" in desc.upper() or "SAD_69" in wkt.upper():
                datum_str = "SAD 69"
            elif "WGS 84" in desc.upper() or "WGS_1984" in wkt.upper():
                datum_str = "WGS 84"
            else:
                datum_obj = crs.datum()
                if datum_obj and datum_obj.description():
                    datum_str = datum_obj.description()

            # ----------------------------------------------------
            # 2. FUSO UTM
            # ----------------------------------------------------
            zone_num = None
            hemisferio = "S"

            # Busca zone na descrição (ex: "UTM zone 19S")
            match_zone_desc = re.search(r'UTM\s+zone\s+(\d+)([NS])?', desc, re.IGNORECASE)
            if match_zone_desc:
                zone_num = int(match_zone_desc.group(1))
                if match_zone_desc.group(2):
                    hemisferio = match_zone_desc.group(2).upper()

            # Fallback para proj_str
            if not zone_num and "+zone=" in proj_str:
                match_proj = re.search(r'\+zone=(\d+)', proj_str)
                if match_proj:
                    zone_num = int(match_proj.group(1))
                if "+south" in proj_str:
                    hemisferio = "S"

            if zone_num:
                fuso_str = f"{zone_num}{hemisferio}"

            # ----------------------------------------------------
            # 3. MERIDIANO CENTRAL (MC)
            # ----------------------------------------------------
            # Procura a longitude de origem no WKT
            match_mc_wkt = re.search(r'PARAMETER\["Central_Meridian",\s*(-?\d+\.?\d*)', wkt, re.IGNORECASE)
            if not match_mc_wkt:
                match_mc_wkt = re.search(r'PARAMETER\["Longitude of natural origin",\s*(-?\d+\.?\d*)', wkt, re.IGNORECASE)

            if match_mc_wkt:
                mc_val = abs(float(match_mc_wkt.group(1)))
                mc_str = f"{int(mc_val)}W"
            elif zone_num:
                # Cálculo UTM: MC = (Fuso * 6) - 183
                mc_calc = abs((zone_num * 6) - 183)
                mc_str = f"{mc_calc}W"

        except Exception:
            pass

        return datum_str, fuso_str, mc_str, is_utm

    @classmethod
    def gerar_texto(cls, dados_header: dict, lista_segmentos: list,
                    area_m2: float = 0.0, perim_m: float = 0.0, crs=None) -> str:
        """Gera a narrativa contínua do memorial descritivo."""
        linhas = []

        # Cabeçalho
        linhas.append("MEMORIAL DESCRITIVO\n")
        linhas.append(dados_header.get('titulo_proj', 'Projeto de Retificação de Área'))

        lote_quadra = dados_header.get('lote_quadra', '')
        if lote_quadra:
            linhas.append(lote_quadra)

        matricula = dados_header.get('matricula', '')
        if matricula:
            linhas.append(f"Matrícula: {matricula}")

        cidade = dados_header.get('cidade', '')
        uf = dados_header.get('uf', '')
        if cidade or uf:
            linhas.append(f"Município: {cidade}/{uf}")

        area_ha = area_m2 / 10000.0 if area_m2 else 0.0
        linhas.append(f"Área: {Formatter.formatar_numero_br(area_m2, 2)} m² ({Formatter.formatar_numero_br(area_ha, 4)} ha)")
        linhas.append(f"Perímetro: {Formatter.formatar_numero_br(perim_m, 2)} m\n")

        linhas.append("DESCRIÇÃO PERIMÉTRICA:")

        if not lista_segmentos:
            return "\n".join(linhas)

        # Descrição perimétrica
        p_inicial = lista_segmentos[0]
        texto_desc = (
            f"Inicia-se a descrição deste perímetro no vértice {p_inicial['de']}, "
            f"de coordenadas N:{Formatter.formatar_numero_br(p_inicial['p1_n'], 2)}m "
            f"e E:{Formatter.formatar_numero_br(p_inicial['p1_e'], 2)}m; "
        )

        n_seg = len(lista_segmentos)

        # Obtém parâmetros do CRS (busca no argumento 'crs', no dicionário 'dados_header' ou no Projeto Ativo)
        crs_obj = crs or dados_header.get('crs')
        datum_str, fuso_str, mc_str, is_utm = cls._obter_info_src(crs_obj)

        # Ao construir o texto de cada segmento:
        for idx, seg in enumerate(lista_segmentos):
            is_ultimo = (idx == n_seg - 1)
            ponto_destino = "V1" if is_ultimo else seg['para']
            
            nome_conf = seg.get('confrontante', '').strip()
            confrontante_texto = nome_conf if nome_conf else "ÁREA CONFRONTANTE"
        
            if seg.get('is_curva', False):
                detalhe = (
                    f"deste, segue confrontando com {confrontante_texto}, em curva {seg.get('sentido_curva', '')} "
                    f"com raio de {Formatter.formatar_numero_br(seg['raio'], 2)}m, "
                    f"desenvolvimento de arco de {Formatter.formatar_numero_br(seg['arco'], 2)}m "
                    f"e corda de {Formatter.formatar_numero_br(seg['corda'], 2)}m "
                    f"(azimute da corda {seg['az']}), "
                    f"até o vértice {ponto_destino}"
                )
            else:
                detalhe = (
                    f"deste, segue confrontando com {confrontante_texto}, "
                    f"com azimute {seg['az']} e distância de "
                    f"{Formatter.formatar_numero_br(seg['dist'], 2)}m, "
                    f"até o vértice {ponto_destino}"
                )

            if not is_ultimo:
                detalhe += (
                    f", de coordenadas N:{Formatter.formatar_numero_br(seg['p2_n'], 2)}m "
                    f"e E:{Formatter.formatar_numero_br(seg['p2_e'], 2)}m; "
                )
            else:
                # Construção dinâmica do encerramento
                if is_utm:
                    encerramento_src = (
                        f"Sistema UTM, referenciadas ao Meridiano Central nº {mc_str}, "
                        f"fuso{fuso_str}, tendo como datum o {datum_str}. "
                        f"Todos os azimutes, distâncias e área foram calculados no plano de projeção UTM."
                    )
                else:
                    encerramento_src = (
                        f"Sistema Topográfico Local, tendo como datum o {datum_str}. "
                        f"Todos os azimutes, distâncias e área foram calculados no plano de projeção adotado."
                    )

                detalhe += (
                    f", ponto inicial da descrição deste perímetro. "
                    f"Todas as coordenadas aqui descritas estão georreferenciadas "
                    f"ao Sistema Geodésico Brasileiro, e encontram-se representadas no "
                    f"{encerramento_src}"
                )

            texto_desc += detalhe

        linhas.append(texto_desc)

        # Rodapé
        proprietario = dados_header.get('proprietario', '')
        if proprietario:
            linhas.append(f"\nPROPRIETÁRIO(S):\n")
            linhas.append("__________________________________________________")              
            linhas.append(f"{proprietario}")          

        confrontantes = dados_header.get('confrontantes_bloco', '')
        if confrontantes:
            linhas.append(f"\nCONFRONTANTES:\n\n{confrontantes}")

        resp_tecnico = dados_header.get('resp_tecnico', '')
        if resp_tecnico:
            linhas.append(f"\nRESPONSÁVEL TÉCNICO:\n")
            linhas.append("__________________________________________________")  
            linhas.append(f"{resp_tecnico}")
            
        return "\n".join(linhas)