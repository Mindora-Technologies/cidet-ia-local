#!/usr/bin/env python3
"""Comprova que les tres fonts de la demo responen.

Es fa servir des de scripts/demo-up.sh, però també va bé sol quan alguna cosa
no rutlla i vols saber QUINA de les tres és.

Ús:  python scripts/comprova-fonts.py
Surt amb codi 1 si alguna font falla.
"""
from __future__ import annotations

import sys
from pathlib import Path

ARREL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ARREL / "demo" / "rag"))

problemes: list[str] = []


def prova(nom: str, fn) -> None:
    try:
        detall = fn()
        print(f"  ✔ {nom:<12} {detall}")
    except Exception as e:                        # noqa: BLE001
        problemes.append(f"{nom}: {type(e).__name__}: {e}")
        print(f"  ✘ {nom:<12} {type(e).__name__}: {e}")


def documents() -> str:
    from tools.documents import cerca_documents
    p = cerca_documents("quina garantia tenen les eines elèctriques", k=3)
    if not p:
        raise RuntimeError("la cerca no retorna cap fragment "
                           "(has executat demo/rag/ingest.py --reset?)")
    return f"{len(p)} fragments · el millor: {p[0].cita()} ({p[0].puntuacio:.2f})"


def sql() -> str:
    from tools.sql import consulta_sql
    r = consulta_sql(
        "SELECT referencia, familia, data_comanda, dies_des_de_la_comanda "
        "FROM v_garanties_comanda WHERE comanda_id = 4521")
    if not r.files:
        raise RuntimeError("la comanda 4521 no surt a la base de dades")
    f = r.files[0]
    return (f"{len(r.files)} línies a la comanda 4521 · "
            f"del {f['data_comanda']} ({f['dies_des_de_la_comanda']} dies)")


def api() -> str:
    from tools.api import consulta_enviaments
    e = consulta_enviaments(comanda_id=4521)
    if not e:
        raise RuntimeError("l'API no té cap enviament per a la comanda 4521")
    d = e[0].dades
    return f"{d['estat']} · {d['ubicacio_actual']}"


def main() -> int:
    print("\n▶ Comprovació de les tres fonts\n")
    prova("documents", documents)
    prova("SQL", sql)
    prova("API", api)
    if problemes:
        print("\n✘ Hi ha fonts que no responen:")
        for p in problemes:
            print(f"   · {p}")
        print("\n  Repassa:  docker compose -f demo/docker-compose.yml ps")
        return 1
    print("\n✔ Les tres fonts responen.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
