#!/usr/bin/env python3
"""Compara models d'EMBEDDINGS sobre el corpus del curs.

Indexa el mateix corpus amb 2–3 models i mesura quin recupera millor. La
pregunta que es respon és: «per a documents en català, quin model d'embeddings
val la pena?».

    python c3/embed_search.py
    python c3/embed_search.py --models qwen3-embedding:0.6b nomic-embed-text
    python c3/embed_search.py --k 3

Mètriques:
  Recall@k  — de les consultes, en quina proporció el document correcte surt
              entre els k primers. És la mètrica que importa en un RAG: si el
              fragment bo no es recupera, el model no el pot fer servir.
  MRR       — Mean Reciprocal Rank. Premia que surti el PRIMER, no només que hi
              sigui. Un recall alt amb MRR baix vol dir que caldrà un reranker.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

ARREL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ARREL / "demo" / "rag"))
OLLAMA_URL = "http://localhost:11434"

# Consultes de prova amb el document que HAURIA de sortir. En català, i amb
# vocabulari diferent del document a posta: si es fes servir la mateixa
# paraula, qualsevol cerca per text la trobaria i no mesuraríem res.
CONSULTES: list[tuple[str, str]] = [
    ("quant de temps puc reclamar si es trenca un trepant", "manual-garanties.pdf"),
    ("les escombretes gastades entren a la cobertura?", "manual-garanties.pdf"),
    ("què he de fer per obrir un expedient al servei tècnic", "manual-garanties.pdf"),
    ("puc tornar material que he demanat per error", "procediment-devolucions.pdf"),
    ("em cobren alguna cosa si retorno estoc que no em cabia", "procediment-devolucions.pdf"),
    ("quant costa un joc de claus", "tarifes-2026.pdf"),
    ("quin descompte tinc si facturo molt", "tarifes-2026.pdf"),
    ("quan arribarà la mercaderia a Girona", "politica-enviaments.pdf"),
    ("m'han deixat el paquet trencat, què faig", "politica-enviaments.pdf"),
    ("quina potència té l'amoladora de 125", "fitxa-producte-amoladora-angular-terramax-ag-125.pdf"),
    ("es pot soldar amb un generador?", "fitxa-producte-soldadora-inverter-norbrec-iw-200.pdf"),
    ("les botes porten metall a la puntera?", "fitxa-producte-botes-de-seguretat-duracamp-s3.pdf"),
    ("com es col·loca el material a les prestatgeries", "manual-magatzem.docx"),
    ("qui es queda la mercaderia si encara no l'he pagada", "condicions-generals-venda.docx"),
    ("quan em passaran el rebut", "condicions-pagament.pdf"),
    ("què demaneu a un fabricant per treballar amb ell", "homologacio-proveidors.pdf"),
    ("afileu broques?", "cataleg-serveis.pdf"),
    ("he perdut l'albarà, encara puc reclamar?", "faq-servei-tecnic.pdf"),
]


@dataclass
class Fragment:
    text: str
    fitxer: str
    pagina: int


def carrega_corpus(chunk: int, overlap: int) -> list[Fragment]:
    from ingest import CORPUS_DIR, extreu, fragmenta, neteja
    fragments: list[Fragment] = []
    for f in sorted(p for p in CORPUS_DIR.iterdir()
                    if p.suffix.lower() in (".pdf", ".docx")):
        for pagina, brut in extreu(f, "pypdf"):
            for tros in fragmenta(neteja(brut), chunk, overlap):
                if len(tros) >= 80:
                    fragments.append(Fragment(tros, f.name, pagina))
    return fragments


def vectors(model: str, textos: list[str]) -> list[list[float]]:
    client = httpx.Client(timeout=120.0)
    out = []
    for i, t in enumerate(textos):
        sys.stdout.write(f"\r    vectoritzant {i+1}/{len(textos)}")
        sys.stdout.flush()
        r = client.post(f"{OLLAMA_URL}/api/embed", json={"model": model, "input": t})
        r.raise_for_status()
        out.append(r.json()["embeddings"][0])
    sys.stdout.write("\r" + " " * 40 + "\r")
    return out


def cosinus(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return num / (na * nb) if na and nb else 0.0


def avalua(model: str, fragments: list[Fragment], k: int) -> dict:
    print(f"\n── {model}")
    t0 = time.time()
    vecs_doc = vectors(model, [f.text for f in fragments])
    t_index = time.time() - t0
    dim = len(vecs_doc[0])

    t0 = time.time()
    vecs_q = vectors(model, [q for q, _ in CONSULTES])
    t_consulta = (time.time() - t0) / len(CONSULTES)

    encerts = 0
    rangs: list[float] = []
    fallades: list[tuple[str, str, str]] = []
    for (consulta, esperat), vq in zip(CONSULTES, vecs_q):
        punts = sorted(
            ((cosinus(vq, vd), fr) for vd, fr in zip(vecs_doc, fragments)),
            key=lambda x: -x[0])[:k]
        fitxers = [fr.fitxer for _, fr in punts]
        if esperat in fitxers:
            encerts += 1
            rangs.append(1 / (fitxers.index(esperat) + 1))
        else:
            rangs.append(0.0)
            fallades.append((consulta, esperat, fitxers[0]))

    recall = encerts / len(CONSULTES)
    mrr = statistics.mean(rangs)
    print(f"    dim {dim} · Recall@{k} {recall:.0%} · MRR {mrr:.2f} · "
          f"índex {t_index:.1f} s · consulta {t_consulta*1000:.0f} ms")
    for c, esperat, obtingut in fallades[:4]:
        print(f"      ✘ «{c[:44]}» → {obtingut} (esperava {esperat})")
    return {"model": model, "dim": dim, "recall": recall, "mrr": mrr,
            "t_index": t_index, "t_consulta": t_consulta, "fallades": len(fallades)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+",
                    default=["qwen3-embedding:0.6b", "nomic-embed-text",
                             "mxbai-embed-large"])
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--chunk-size", type=int, default=800)
    ap.add_argument("--overlap", type=int, default=100)
    args = ap.parse_args()

    disponibles = {m["name"] for m in httpx.get(f"{OLLAMA_URL}/api/tags").json()["models"]}
    models = [m for m in args.models if m in disponibles or f"{m}:latest" in disponibles]
    for m in set(args.models) - set(models):
        print(f"⚠ salto «{m}»: no està baixat (ollama pull {m})", file=sys.stderr)
    if not models:
        raise SystemExit("✘ cap model d'embeddings disponible")

    print(f"\n▶ Comparativa d'embeddings · {len(CONSULTES)} consultes · k={args.k}")
    fragments = carrega_corpus(args.chunk_size, args.overlap)
    print(f"  corpus: {len(fragments)} fragments")

    resultats = [avalua(m, fragments, args.k) for m in models]

    print(f"\n| Model | Dim | Recall@{args.k} | MRR | Índex | Consulta |")
    print("|---|---|---|---|---|---|")
    for r in sorted(resultats, key=lambda x: (-x["recall"], -x["mrr"])):
        print(f"| **{r['model']}** | {r['dim']} | {r['recall']:.0%} | "
              f"{r['mrr']:.2f} | {r['t_index']:.1f} s | {r['t_consulta']*1000:.0f} ms |")

    print("\nCom llegir-ho:")
    print("· Recall diu si el document bo hi és; MRR, si surt el primer.")
    print("· Recall alt amb MRR baix = el fragment bo es recupera però queda")
    print("  enterrat: és el cas on un reranker (C5) compensa de veritat.")
    print("· Una dimensió més gran no vol dir millor: costa més memòria i més")
    print("  temps de cerca, i en català sovint no compensa.")
    print("· Si canvies de model d'embeddings, has de TORNAR A INDEXAR-HO tot:")
    print("  els vectors de models diferents no es poden comparar entre ells.\n")


if __name__ == "__main__":
    main()
