"""Eina 1 — cerca semàntica al corpus documental (Qdrant)."""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "distribucions_valles")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "qwen3-embedding:0.6b")


@dataclass
class Passatge:
    text: str
    fitxer: str
    pagina: int
    tipus_document: str
    puntuacio: float

    def cita(self) -> str:
        return f"{self.fitxer}, pàg. {self.pagina}"


def _vector(pregunta: str) -> list[float]:
    r = httpx.post(f"{OLLAMA_URL}/api/embed",
                   json={"model": EMBED_MODEL, "input": pregunta}, timeout=60.0)
    r.raise_for_status()
    return r.json()["embeddings"][0]


def cerca_documents(consulta: str, k: int = 5,
                    tipus_document: str | None = None) -> list[Passatge]:
    """Cerca als manuals, procediments i fitxes de l'empresa.

    Fes-la servir per a polítiques, condicions, terminis, garanties i
    especificacions de producte: tot allò que està escrit en un document i
    no en una base de dades.

    Args:
        consulta: la pregunta o els termes a cercar, en català.
        k: quants fragments recuperar.
        tipus_document: filtre opcional, p. ex. «política de garanties».
    """
    cos: dict = {
        "vector": _vector(consulta),
        "limit": k,
        "with_payload": True,
    }
    if tipus_document:
        cos["filter"] = {"must": [{"key": "tipus_document",
                                   "match": {"value": tipus_document}}]}

    r = httpx.post(f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
                   json=cos, timeout=30.0)
    r.raise_for_status()
    return [
        Passatge(
            text=p["payload"]["text"],
            fitxer=p["payload"]["fitxer"],
            pagina=p["payload"]["pagina"],
            tipus_document=p["payload"]["tipus_document"],
            puntuacio=p["score"],
        )
        for p in r.json()["result"]
    ]
