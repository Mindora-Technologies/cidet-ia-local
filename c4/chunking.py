#!/usr/bin/env python3
"""Laboratori de fragmentació — classe 4.

Ensenya què li passa al corpus segons com el talles. Sense tocar Qdrant ni
gastar GPU: només fragmenta i explica.

    python c4/chunking.py
    python c4/chunking.py --mides 300 800 1500 --solapaments 0 100
    python c4/chunking.py --document manual-garanties.pdf --mostra
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

ARREL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ARREL / "demo" / "rag"))
from ingest import CAR_PER_TOKEN, CORPUS_DIR, extreu, fragmenta, neteja  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mides", type=int, nargs="+", default=[300, 500, 800, 1200])
    ap.add_argument("--solapaments", type=int, nargs="+", default=[0, 50, 100, 200])
    ap.add_argument("--document", help="només aquest fitxer del corpus")
    ap.add_argument("--mostra", action="store_true", help="ensenya els fragments")
    args = ap.parse_args()

    fitxers = sorted(p for p in CORPUS_DIR.iterdir()
                     if p.suffix.lower() in (".pdf", ".docx"))
    if args.document:
        fitxers = [p for p in fitxers if p.name == args.document]
        if not fitxers:
            raise SystemExit(f"✘ no trobo {args.document} a {CORPUS_DIR}")

    textos = []
    for f in fitxers:
        for _, brut in extreu(f, "pypdf"):
            t = neteja(brut)
            if len(t) > 100:
                textos.append((f.name, t))
    if not textos:
        raise SystemExit("✘ cap text extraïble (recorda que l'acta escanejada no en té)")

    print(f"\n▶ {len(textos)} blocs de text de {len(fitxers)} document(s)\n")
    print(f"{'mida':>6} {'solap.':>7} {'fragments':>10} {'car. mitjans':>13} "
          f"{'~tokens':>9} {'redundància':>12}")
    print("─" * 62)

    base_car = sum(len(t) for _, t in textos)
    for mida in args.mides:
        for solap in args.solapaments:
            if solap >= mida:
                continue
            trossos = [x for _, t in textos
                       for x in fragmenta(t, mida, solap) if len(x) >= 80]
            if not trossos:
                continue
            llargs = [len(x) for x in trossos]
            total = sum(llargs)
            print(f"{mida:>6} {solap:>7} {len(trossos):>10} "
                  f"{statistics.mean(llargs):>13.0f} "
                  f"{statistics.mean(llargs)/CAR_PER_TOKEN:>9.0f} "
                  f"{(total/base_car - 1)*100:>11.0f} %")

    print("""
Com llegir-ho
─────────────
· «redundància» és el text que es repeteix pel solapament. Un 25 % vol dir que
  emmagatzemes i vectoritzes un 25 % més de text: costa memòria i temps.
· Fragments MOLT PETITS (300 tokens): l'embedding és precís però el fragment
  perd context. El model rep «...i 6 mesos per als consumibles» sense saber de
  què parlava el paràgraf.
· Fragments MOLT GRANS (1200+): l'embedding barreja temes i la cerca perd
  punteria. A més omples el context del model amb text que no cal.
· Sense solapament: una frase partida entre dos fragments no es recupera bé mai.
· El punt de partida raonable per a documents de política com aquests és
  ~800 tokens amb 100 de solapament, tallant per frases i no per caràcters.
· Recorda que en CATALÀ els tokens surten més cars: la mateixa mida en
  caràcters són més tokens que en anglès.
""")

    if args.mostra:
        mida, solap = args.mides[0], args.solapaments[0]
        nom, text = textos[0]
        print(f"─── {nom} amb mida={mida} solapament={solap} " + "─" * 20)
        for i, x in enumerate(fragmenta(text, mida, solap)):
            if len(x) < 80:
                continue
            print(f"\n[{i}] ({len(x)} car.)\n{x[:300]}{'…' if len(x) > 300 else ''}")


if __name__ == "__main__":
    main()
