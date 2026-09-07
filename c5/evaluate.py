#!/usr/bin/env python3
"""Avalua un sistema de RAG contra c5/eval.jsonl — classe 5.

Mesura ABANS de tocar res, i torna a mesurar després. Una millora que no mou la
nota és latència i codi de més.

    python c5/evaluate.py --sistema c4/rag.py
    python c5/evaluate.py --sistema c5/rag_v2.py --args --hibrid --rerank
    python c5/evaluate.py --sistema demo/rag/agent.py --categoria combinada
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

ARREL = Path(__file__).resolve().parents[1]
OLLAMA_URL = "http://localhost:11434"

PROMPT_JUTGE = """\
Avalua si la RESPOSTA DEL SISTEMA contesta bé la pregunta, comparant-la amb la
RESPOSTA ESPERADA. Puntua de 0 a 10.

· Si la categoria és «negativa», la resposta correcta és admetre que no se sap.
  Si el sistema s'inventa una dada, la nota és 0, encara que soni bé.
· Si la categoria és «combinada», la resposta ha de cobrir TOTS els punts de
  l'esperada. Si en cobreix la meitat, la nota màxima és 5.
· Els números i les dates han de coincidir. Un termini equivocat és un error greu.

PREGUNTA: {pregunta}
CATEGORIA: {categoria}
RESPOSTA ESPERADA: {esperada}
RESPOSTA DEL SISTEMA: {obtinguda}

Respon NOMÉS amb JSON: {{"nota": <0-10>, "motiu": "<una frase en català>"}}
"""


def executa(sistema: Path, pregunta: str, extra: list[str], timeout: int) -> str:
    r = subprocess.run(
        [sys.executable, str(sistema), *extra, pregunta],
        capture_output=True, text=True, timeout=timeout, cwd=ARREL)
    return (r.stdout or r.stderr).strip()


def puntua(jutge: str, cas: dict, resposta: str) -> tuple[float, str]:
    r = httpx.post(f"{OLLAMA_URL}/api/generate", timeout=300, json={
        "model": jutge, "stream": False, "options": {"temperature": 0.0},
        "prompt": PROMPT_JUTGE.format(
            pregunta=cas["pregunta"], categoria=cas["categoria"],
            esperada=cas["resposta_esperada"],
            obtinguda=resposta[:4000] or "(cap resposta)"),
    })
    r.raise_for_status()
    m = re.search(r"\{.*?\}", r.json()["response"], re.S)
    if not m:
        return 0.0, "el jutge no ha retornat JSON"
    try:
        d = json.loads(m.group(0))
        return float(d.get("nota", 0)), str(d.get("motiu", ""))[:150]
    except (json.JSONDecodeError, ValueError):
        return 0.0, "JSON del jutge il·legible"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sistema", type=Path, default=ARREL / "c4" / "rag.py")
    ap.add_argument("--eval", type=Path, default=ARREL / "c5" / "eval.jsonl")
    ap.add_argument("--jutge", default="qwen3:14b")
    ap.add_argument("--categoria")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--args", nargs=argparse.REMAINDER, default=[],
                    help="arguments extra per al sistema (posa'ls al final)")
    args = ap.parse_args()

    casos = [json.loads(l) for l in args.eval.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.categoria:
        casos = [c for c in casos if c["categoria"] == args.categoria]
    if args.limit:
        casos = casos[:args.limit]
    if not casos:
        raise SystemExit("✘ cap cas seleccionat")

    print(f"\n▶ {args.sistema.name} {' '.join(args.args)} · {len(casos)} casos "
          f"· jutge {args.jutge}\n")

    notes: dict[str, list[float]] = defaultdict(list)
    fluixos: list[tuple[str, float, str]] = []
    t0 = time.time()

    for i, cas in enumerate(casos, start=1):
        print(f"  [{i:>2}/{len(casos)}] {cas['categoria']:<11} "
              f"{cas['pregunta'][:48]:<48}", end="", flush=True)
        try:
            resposta = executa(args.sistema, cas["pregunta"], args.args, args.timeout)
        except subprocess.TimeoutExpired:
            resposta = ""
            print(" TIMEOUT", end="")
        nota, motiu = puntua(args.jutge, cas, resposta)
        notes[cas["categoria"]].append(nota)
        if nota < 6:
            fluixos.append((cas["pregunta"], nota, motiu))
        print(f" {nota:>4.1f}")

    totes = [n for v in notes.values() for n in v]
    print(f"\n{'─'*62}\n  NOTA GLOBAL: {statistics.mean(totes):.2f}/10 "
          f"({len(totes)} casos, {time.time()-t0:.0f} s)\n")
    for cat, v in sorted(notes.items()):
        barra = "█" * int(statistics.mean(v)) + "·" * (10 - int(statistics.mean(v)))
        print(f"  {cat:<12} {statistics.mean(v):>5.2f}  {barra}  ({len(v)} casos)")

    if fluixos:
        print(f"\n  {len(fluixos)} casos per sota de 6:")
        for p, n, motiu in fluixos[:10]:
            print(f"    {n:>4.1f}  {p[:52]}")
            print(f"          → {motiu}")
    print()


if __name__ == "__main__":
    main()
