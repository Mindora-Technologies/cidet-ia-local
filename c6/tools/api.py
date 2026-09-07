#!/usr/bin/env python3
"""Eina d'API — esquelet de la classe 6.

L'objectiu: consultar una API externa que ÉS LENTA i que A VEGADES FALLA, sense
que això s'emporti per davant la resposta a l'usuari.

La implementació completa és a demo/rag/tools/api.py.

Per provar-ho de veritat, al demo/.env:
    FAKE_LATENCY_MS=3000
    FAILURE_RATE=0.3
i recrea el contenidor de l'API.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

API_URL = os.getenv("SHIPMENTS_API_URL", "http://localhost:8080")
API_KEY = os.getenv("API_KEY", "")
TIMEOUT = float(os.getenv("API_TIMEOUT", "10"))
REINTENTS = int(os.getenv("API_RETRIES", "3"))


class ErrorAPI(RuntimeError):
    """L'API no ha pogut respondre. L'agent ho ha de DIR, no dissimular-ho."""


@dataclass
class Enviament:
    dades: dict[str, Any]

    def resum(self) -> str:
        # TODO: text llegible amb estat, ubicació, transportista i dates.
        raise NotImplementedError


def _get(cami: str, params: dict | None = None) -> Any:
    """GET amb autenticació, timeout i reintents amb espera exponencial.

    EXERCICI DE LA CLASSE 6:

      · Capçalera X-API-Key amb API_KEY.
      · timeout=TIMEOUT a cada petició. Sense timeout, una API penjada et
        deixa l'agent penjat per sempre.
      · 404 → retorna None. NO és un error: vol dir que no hi és.
      · 401/403 → ErrorAPI immediat. Reintentar una clau dolenta no la
        millora; només fa perdre temps.
      · 5xx, timeout i errors de xarxa → REINTENTA, esperant 0,5 s, 1 s, 2 s.
        Exponencial, no fix: si el servei està saturat, martellejar-lo cada
        mig segon empitjora les coses.
      · Si s'esgoten els reintents → ErrorAPI amb l'últim error.

    Pregunta per pensar a classe: quant ha d'esperar un agent abans de
    rendir-se? Si l'usuari té la pantalla davant, 3 reintents × 3 s de
    latència són 9 segons de no veure res.
    """
    raise NotImplementedError(
        "Implementa _get(). La versió de referència és a demo/rag/tools/api.py.")


def consulta_enviaments(comanda_id: int | None = None,
                        client: str | None = None) -> list[Enviament]:
    """Consulta l'estat d'un enviament a l'API de seguiment."""
    if comanda_id is None and not client:
        raise ValueError("Cal indicar comanda_id o client.")
    if comanda_id is not None:
        d = _get(f"/shipments/{comanda_id}")
        return [Enviament(d)] if d else []
    return [Enviament(x) for x in (_get("/shipments", {"client": client}) or [])]


if __name__ == "__main__":
    print(consulta_enviaments(comanda_id=4521)[0].resum())
