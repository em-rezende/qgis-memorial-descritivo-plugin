# -*- coding: utf-8 -*-
import math
import re


class Formatter:
    """Classe com funções de formatação reutilizáveis."""

    @staticmethod
    def formatar_numero_br(val, dec=2):
        """Formata números no padrão brasileiro (1.234,56)."""
        if val is None:
            return "0,00"
        if isinstance(val, str):
            return val
        fmt = f"{{:,.{dec}f}}"
        return fmt.format(float(val)).replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def formatar_azimute_gms(az):
        """Converte azimute decimal para graus, minutos e segundos."""
        az = float(az) % 360
        d = int(az)
        m = int((az - d) * 60)
        s = round((((az - d) * 60) - m) * 60, 2)
        return f"{d:02d}º{m:02d}'{s:05.2f}\""

    @staticmethod
    def formatar_area(area_m2):
        """Retorna área formatada em m², ha e alqueires (SP)."""
        return {
            "m2": Formatter.formatar_numero_br(area_m2, 2),
            "ha": Formatter.formatar_numero_br(area_m2 / 10000.0, 4),
            "alq_sp": Formatter.formatar_numero_br(area_m2 / 24200.0, 2)
        }

    @staticmethod
    def sanitizar_nome_arquivo(nome: str) -> str:
        """Remove caracteres inválidos para nomes de arquivos no sistema operacional."""
        if not nome:
            return "Descritivo"
        # Remove caracteres proibidos no Windows / Linux / macOS
        return re.sub(r'[\\/*?:"<>|]', "", nome).strip()
        