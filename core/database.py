# -*- coding: utf-8 -*-
import sqlite3
import json
import os
from typing import Optional, Dict, Any
from qgis.core import QgsPointXY

class Database:
    """Gerencia o banco de dados SQLite do plugin."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Cria a tabela e garante as colunas necessárias."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lotes_cadastrados (
                feature_id TEXT PRIMARY KEY,
                v1_index INTEGER,
                titulo_proj TEXT,
                lote_quadra TEXT,
                lote TEXT,
                quadra TEXT,
                bairro TEXT,
                matricula TEXT,
                cidade TEXT,
                uf TEXT,
                proprietario TEXT,
                resp_tecnico TEXT,
                confrontantes_json TEXT,
                nodes_json TEXT
            )
        """)
        
        # Migração de colunas para bancos existentes
        cursor.execute("PRAGMA table_info(lotes_cadastrados)")
        cols = [col[1] for col in cursor.fetchall()]
        for col_name in ['lote', 'quadra', 'bairro']:
            if col_name not in cols:
                cursor.execute(f"ALTER TABLE lotes_cadastrados ADD COLUMN {col_name} TEXT")

        conn.commit()
        conn.close()

    def salvar(
        self,
        feature_id: str,
        v1_index: int,
        titulo_proj: str,
        lote: str,
        quadra: str,
        bairro: str,
        lote_quadra: str,
        matricula: str,
        cidade: str,
        uf: str,
        proprietario: str,
        resp_tecnico: str,
        confrontantes_salvos: dict,
        raw_nodes: list
    ):
        """Salva ou atualiza os dados do lote."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        conf_json = json.dumps(confrontantes_salvos)
        nodes_list = [{"x": pt.x(), "y": pt.y()} for pt in raw_nodes]
        nodes_json = json.dumps(nodes_list)

        cursor.execute("""
            INSERT OR REPLACE INTO lotes_cadastrados 
            (feature_id, v1_index, titulo_proj, lote, quadra, bairro, lote_quadra, matricula, cidade, uf, proprietario, resp_tecnico, confrontantes_json, nodes_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            feature_id, v1_index, titulo_proj, lote, quadra, bairro, lote_quadra,
            matricula, cidade, uf, proprietario, resp_tecnico,
            conf_json, nodes_json
        ))

        conn.commit()
        conn.close()

    def carregar(self, feature_id: str) -> Optional[Dict[str, Any]]:
        """Carrega os dados do lote pelo feature_id."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT v1_index, titulo_proj, lote, quadra, bairro, lote_quadra, matricula, cidade, uf,
                   proprietario, resp_tecnico, confrontantes_json
            FROM lotes_cadastrados WHERE feature_id = ?
        """, (feature_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        dados = {
            "v1_index": row[0],
            "titulo_proj": row[1],
            "lote": row[2] or "",
            "quadra": row[3] or "",
            "bairro": row[4] or "",
            "lote_quadra": row[5] or "",
            "matricula": row[6],
            "cidade": row[7],
            "uf": row[8],
            "proprietario": row[9],
            "resp_tecnico": row[10],
            "confrontantes": {}
        }

        if row[11]:
            try:
                dados["confrontantes"] = json.loads(row[11])
            except Exception:
                pass

        return dados

    def excluir(self, feature_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lotes_cadastrados WHERE feature_id = ?", (feature_id,))
        conn.commit()
        conn.close()

    def excluir_todos(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS lotes_cadastrados")
        conn.commit()
        conn.close()
        self._init_db()

    def listar_outros_lotes(self, feature_id: str) -> list:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT feature_id, lote_quadra, matricula, proprietario, nodes_json
            FROM lotes_cadastrados WHERE feature_id != ?
        """, (feature_id,))
        resultados = cursor.fetchall()
        conn.close()
        return resultados
        