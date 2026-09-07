#!/usr/bin/env python3
"""El RAG mínim — classe 4.

Cerca + context + resposta. Res més. Deliberadament curt: tot el que fa falta
per respondre amb documents propis cap en una pantalla, i les classes 5 i 6
consisteixen a arreglar-ne els casos on falla.

    python c4/rag.py "quina garantia tenen les eines elèctriques?"
    python c4/rag.py --k 8 --mostra-context "com es reclama una garantia?"

Requisits: Qdrant amb el corpus ingerit (demo/rag/ingest.py --reset).
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import httpx

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "distribucions_valles")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "qwen3-embedding:0.6b")
MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

PROMPT = """\
Ets l'assistent intern de Distribucions Vallès SL. Respon en català.

Fes servir NOMÉS la informació dels fragments de sota. Si no hi és, digues
clarament que no ho saps: no t'ho inventis. Cita les fonts amb [1], [2]…

FRAGMENTS:
{context}

PREGUNTA: {pregunta}

RESPOSTA:"""


def vector(text: str) -> list[float]:
    r = httpx.post(f"{OLLAMA_URL}/api/embed", timeout=60,
                   json={"model": EMBED_MODEL, "input": text})
    r.raise_for_status()
    return r.json()["embeddings"][0]


def cerca(pregunta: str, k: int) -> list[dict]:
    r = httpx.post(f"{QDRANT_URL}/collections/{COLLECTION}/points/search", timeout=30,
                   json={"vector": vector(pregunta), "limit": k, "with_payload": True})
    r.raise_for_status()
    return r.json()["result"]


def respon(pregunta: str, k: int = 5, mostra_context: bool = False) -> str:
    punts = cerca(pregunta, k)
    if not punts:
        return "No he trobat cap document relacionat amb la pregunta."

    context = "\n\n".join(
        f"[{i}] ({p['payload']['fitxer']}, pàg. {p['payload']['pagina']})\n"
        f"{p['payload']['text']}"
        for i, p in enumerate(punts, start=1))

    if mostra_context:
        print("─── context recuperat " + "─" * 40, file=sys.stderr)
        for i, p in enumerate(punts, start=1):
            print(f"[{i}] {p['score']:.3f}  {p['payload']['fitxer']} "
                  f"p.{p['payload']['pagina']}", file=sys.stderr)
            print(f"    {p['payload']['text'][:180]}…\n", file=sys.stderr)
        print("─" * 61, file=sys.stderr)

    r = httpx.post(f"{OLLAMA_URL}/api/generate", timeout=300, json={
        "model": MODEL, "stream": False,
        "prompt": PROMPT.format(context=context, pregunta=pregunta),
        "options": {"temperature": 0.1},
    })
    r.raise_for_status()
    resposta = r.json()["response"].strip()

    fonts = "\n".join(
        f"  [{i}] {p['payload']['fitxer']}, pàg. {p['payload']['pagina']} "
        f"(rellevància {p['score']:.2f})"
        for i, p in enumerate(punts, start=1))
    return f"{resposta}\n\nFonts consultades:\n{fonts}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pregunta", nargs="+")
    ap.add_argument("--k", type=int, default=5, help="fragments a recuperar")
    ap.add_argument("--mostra-context", action="store_true",
                    help="ensenya què s'ha recuperat, i amb quina puntuació")
    args = ap.parse_args()

    t0 = time.time()
    print("\n" + respon(" ".join(args.pregunta), args.k, args.mostra_context))
    print(f"\n({time.time()-t0:.1f} s · {MODEL} · k={args.k})")


if __name__ == "__main__":
    main()
