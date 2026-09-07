"""Eina 3 — seguiment d'enviaments (API REST externa)."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

API_URL = os.getenv("SHIPMENTS_API_URL", "http://localhost:8080")
API_KEY = os.getenv("API_KEY", "clau-de-desenvolupament")
TIMEOUT = float(os.getenv("API_TIMEOUT", "10"))
REINTENTS = int(os.getenv("API_RETRIES", "3"))


class ErrorAPI(RuntimeError):
    """L'API d'enviaments no ha pogut respondre."""


@dataclass
class Enviament:
    dades: dict[str, Any]

    def resum(self) -> str:
        d = self.dades
        parts = [
            f"Comanda {d['comanda_id']} · {d['client']}",
            f"Estat: {d['estat']}",
            f"Ubicació actual: {d['ubicacio_actual']}",
            f"Transportista: {d['transportista']} (seguiment {d['numero_seguiment']})",
        ]
        if d.get("data_sortida"):
            parts.append(f"Sortida del magatzem {d['magatzem_origen']}: {d['data_sortida']}")
        if d.get("data_prevista"):
            parts.append(f"Lliurament previst: {d['data_prevista']}")
        if d.get("data_lliurament"):
            parts.append(f"Lliurat el {d['data_lliurament']}")
        if d.get("historial"):
            ultim = d["historial"][-1]
            parts.append(f"Últim moviment: {ultim['data_hora']} — "
                         f"{ultim['descripcio']} ({ultim['ubicacio']})")
        return "\n".join(parts)


def _get(cami: str, params: dict | None = None) -> Any:
    """GET amb reintents i espera exponencial.

    Una API externa falla. Si l'agent no ho contempla, la resposta a l'usuari
    passa a ser «no ho sé» per un 503 que hauria durat mig segon.
    """
    ultim: Exception | None = None
    for intent in range(REINTENTS):
        try:
            r = httpx.get(f"{API_URL}{cami}", params=params,
                          headers={"X-API-Key": API_KEY}, timeout=TIMEOUT)
            if r.status_code == 404:
                return None
            if r.status_code in (401, 403):
                raise ErrorAPI(f"L'API ha rebutjat la clau ({r.status_code}). "
                               f"Revisa la variable API_KEY.")
            r.raise_for_status()
            return r.json()
        except (httpx.TimeoutException, httpx.HTTPStatusError,
                httpx.TransportError) as e:
            ultim = e
            if intent < REINTENTS - 1:
                time.sleep(0.5 * 2 ** intent)     # 0,5 s · 1 s · 2 s
    raise ErrorAPI(f"L'API d'enviaments no respon després de {REINTENTS} "
                   f"intents: {ultim}")


def consulta_enviaments(comanda_id: int | None = None,
                        client: str | None = None) -> list[Enviament]:
    """Consulta l'estat d'un enviament a l'API de seguiment.

    Fes-la servir per saber ON és una comanda i quan arribarà. La informació
    d'enviament NO és a la base de dades: només la té aquesta API.

    Args:
        comanda_id: número de comanda a consultar.
        client: alternativament, nom del client per veure'n els enviaments.
    """
    if comanda_id is None and not client:
        raise ValueError("Cal indicar comanda_id o client.")
    if comanda_id is not None:
        d = _get(f"/shipments/{comanda_id}")
        return [Enviament(d)] if d else []
    return [Enviament(x) for x in (_get("/shipments", {"client": client}) or [])]
