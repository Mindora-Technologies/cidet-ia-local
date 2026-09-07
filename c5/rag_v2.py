#!/usr/bin/env python3
"""RAG avançat — esquelet de la classe 5.

Parteix del RAG mínim de la C4 i hi afegeix, cadascuna activable per flag:

  --hibrid     cerca vectorial + BM25 (fusionades amb RRF)
  --rerank     reordenació dels candidats amb un model de reranking
  --reescriu   reescriptura de la pregunta abans de cercar
  --llindar X  si el millor resultat queda per sota de X, no respon i ho diu

L'objectiu de la classe és implementar-les i MESURAR si cada una millora la
nota de c5/eval.jsonl. Les que no la moguin, fora.

    python c5/rag_v2.py "com es reclama una garantia?"
    python c5/rag_v2.py --hibrid --rerank "preu del trepant percutor"
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import httpx

ARREL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ARREL / "c4"))
from rag import PROMPT, QDRANT_URL, COLLECTION, OLLAMA_URL, MODEL, vector  # noqa: E402

RERANK_MODEL = os.getenv("RERANK_MODEL", "qwen3-reranker:0.6b")


# ---------------------------------------------------------------- utilitats
def tots_els_punts(limit: int = 10_000) -> list[dict]:
    """Baixa la col·lecció sencera. Val per a un corpus de classe; en
    producció, BM25 es fa amb un índex de text de debò (Elasticsearch,
    Tantivy, o l'índex de text complet del mateix Qdrant)."""
    r = httpx.post(f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll",
                   json={"limit": limit, "with_payload": True}, timeout=60)
    r.raise_for_status()
    return r.json()["result"]["points"]


def cerca_vectorial(pregunta: str, k: int) -> list[dict]:
    r = httpx.post(f"{QDRANT_URL}/collections/{COLLECTION}/points/search", timeout=30,
                   json={"vector": vector(pregunta), "limit": k, "with_payload": True})
    r.raise_for_status()
    return r.json()["result"]


def tokenitza(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), re.UNICODE)


def cerca_bm25(pregunta: str, k: int, punts: list[dict]) -> list[dict]:
    """BM25 clàssic. Serveix per al que els vectors fan pitjor: trobar una
    REFERÈNCIA EXACTA. «REF-1001» com a vector s'assembla a «REF-1042»; com a
    text, no."""
    k1, b = 1.5, 0.75
    docs = [tokenitza(p["payload"]["text"]) for p in punts]
    n = len(docs)
    if n == 0:
        return []
    llarg_mitja = sum(len(d) for d in docs) / n

    df: dict[str, int] = defaultdict(int)
    for d in docs:
        for t in set(d):
            df[t] += 1

    consulta = tokenitza(pregunta)
    punts_bm25: list[tuple[float, dict]] = []
    for doc, punt in zip(docs, punts):
        tf: dict[str, int] = defaultdict(int)
        for t in doc:
            tf[t] += 1
        s = 0.0
        for t in consulta:
            if t not in df:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            f = tf[t]
            s += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * len(doc) / llarg_mitja))
        if s > 0:
            punts_bm25.append((s, punt))
    punts_bm25.sort(key=lambda x: -x[0])
    return [dict(p, score=s) for s, p in punts_bm25[:k]]


def rrf(llistes: list[list[dict]], k: int, constant: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion: fusiona rànquings sense haver de normalitzar
    puntuacions que no són comparables (cosinus vs BM25)."""
    acumulat: dict[str, float] = defaultdict(float)
    per_id: dict[str, dict] = {}
    for llista in llistes:
        for rang, p in enumerate(llista, start=1):
            acumulat[str(p["id"])] += 1 / (constant + rang)
            per_id[str(p["id"])] = p
    ordenats = sorted(acumulat.items(), key=lambda x: -x[1])
    return [dict(per_id[i], score=s) for i, s in ordenats[:k]]


def reescriu(pregunta: str) -> str:
    """Passa una pregunta col·loquial a termes del domini.

    «se m'ha trencat el trepant, què faig?» → «procediment de reclamació de
    garantia per a eines elèctriques». Els embeddings troben molt millor la
    segona.
    """
    r = httpx.post(f"{OLLAMA_URL}/api/generate", timeout=120, json={
        "model": MODEL, "stream": False, "options": {"temperature": 0.0},
        "prompt": ("Reescriu aquesta pregunta d'usuari com una consulta de cerca "
                   "documental en català, amb el vocabulari formal que faria "
                   "servir un manual d'empresa. Respon NOMÉS amb la consulta.\n\n"
                   f"Pregunta: {pregunta}\nConsulta:"),
    })
    r.raise_for_status()
    return r.json()["response"].strip().strip('"') or pregunta


def rerank(pregunta: str, punts: list[dict], k: int) -> list[dict]:
    """Reordena els candidats amb un model de reranking (cross-encoder).

    TODO (classe 5): amb `ollama pull qwen3-reranker:0.6b` o un cross-encoder
    de sentence-transformers, puntuar cada parella (pregunta, fragment) i
    reordenar. A diferència dels embeddings, el reranker MIRA LES DUES coses
    alhora: és molt més precís i molt més lent, i per això només se'n passen
    els 20–30 primers candidats, no la col·lecció sencera.
    """
    print("  ⚠ rerank encara no implementat: és l'exercici de la classe 5",
          file=sys.stderr)
    return punts[:k]


# --------------------------------------------------------------------- main
def respon(pregunta: str, k: int, hibrid: bool, fer_rerank: bool,
           fer_reescriure: bool, llindar: float) -> str:
    consulta = reescriu(pregunta) if fer_reescriure else pregunta
    if fer_reescriure:
        print(f"  consulta reescrita: «{consulta}»", file=sys.stderr)

    candidats = k * 4 if fer_rerank else k
    punts = cerca_vectorial(consulta, candidats)
    if hibrid:
        punts = rrf([punts, cerca_bm25(consulta, candidats, tots_els_punts())],
                    candidats)
    if fer_rerank:
        punts = rerank(consulta, punts, k)
    punts = punts[:k]

    if not punts:
        return "No he trobat cap document relacionat amb la pregunta."

    # Defensa 1 contra l'al·lucinació: si el millor resultat no s'assembla prou,
    # no li donem context al model. Sense això, respondrà igualment.
    millor = max(p.get("score", 0) for p in punts)
    if millor < llindar:
        return (f"No tinc informació sobre això als documents de l'empresa. "
                f"(El resultat més semblant puntua {millor:.2f}, per sota del "
                f"llindar de {llindar:.2f}.)")

    context = "\n\n".join(
        f"[{i}] ({p['payload']['fitxer']}, pàg. {p['payload']['pagina']})\n"
        f"{p['payload']['text']}" for i, p in enumerate(punts, start=1))

    r = httpx.post(f"{OLLAMA_URL}/api/generate", timeout=300, json={
        "model": MODEL, "stream": False, "options": {"temperature": 0.1},
        "prompt": PROMPT.format(context=context, pregunta=pregunta),
    })
    r.raise_for_status()
    fonts = "\n".join(
        f"  [{i}] {p['payload']['fitxer']}, pàg. {p['payload']['pagina']} "
        f"({p.get('score', 0):.3f})" for i, p in enumerate(punts, start=1))
    return f"{r.json()['response'].strip()}\n\nFonts consultades:\n{fonts}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pregunta", nargs="+")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--hibrid", action="store_true", help="vectors + BM25 amb RRF")
    ap.add_argument("--rerank", action="store_true", help="reordena amb un reranker")
    ap.add_argument("--reescriu", action="store_true", help="reescriu la pregunta")
    ap.add_argument("--llindar", type=float, default=0.0,
                    help="puntuació mínima per respondre (prova 0.35)")
    args = ap.parse_args()
    print("\n" + respon(" ".join(args.pregunta), args.k, args.hibrid,
                        args.rerank, args.reescriu, args.llindar))


if __name__ == "__main__":
    main()
