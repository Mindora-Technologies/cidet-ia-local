#!/usr/bin/env python3
"""API de seguiment d'enviaments de Distribucions Vallès SL (fictícia).

És la TERCERA font de l'assistent del curs, al costat dels documents i del SQL.
Un sol fitxer, a propòsit: a la C6 s'hi afegeixen coses i ha de cabre a la pantalla.

Trets pensats per a la classe:
  · autenticació per capçalera X-API-Key  → la primera cosa que s'oblida en integrar
  · FAKE_LATENCY_MS  → per practicar timeouts
  · FAILURE_RATE     → per practicar reintents amb backoff
  · l'enviament de la comanda 4521 sempre existeix i sempre diu el mateix

Executar:
    export API_KEY=clau-de-desenvolupament
    uvicorn api_enviaments:app --host 0.0.0.0 --port 8080 --reload

Documentació navegable a  http://localhost:8080/docs
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import random
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

# ------------------------------------------------------------- configuració
API_KEY = os.getenv("API_KEY", "clau-de-desenvolupament")
FAKE_LATENCY_MS = int(os.getenv("FAKE_LATENCY_MS", "0"))
FAILURE_RATE = float(os.getenv("FAILURE_RATE", "0"))
LLAVOR = int(os.getenv("SEED", "20260907"))
AVUI = date.fromisoformat(os.getenv("DATA_AVUI", "2026-09-07"))

TRANSPORTISTES = [
    ("Transports Vallès Express", "TVE"),
    ("Logística Camp de Tarragona", "LCT"),
    ("MRW Girona", "MRG"),
    ("Repartiments Bages", "RBA"),
]
CIUTATS_RUTA = [
    "Sabadell", "Barcelona", "Granollers", "Terrassa", "Mataró", "Vic",
    "Manresa", "Tarragona", "Reus", "Girona", "Lleida", "Igualada",
]


class EstatEnviament(str, Enum):
    """Estats pels quals passa un enviament."""
    PREPARACIO = "preparació"
    RECOLLIT = "recollit pel transportista"
    EN_TRANSIT = "en trànsit"
    EN_REPARTIMENT = "en repartiment"
    LLIURAT = "lliurat"
    INCIDENCIA = "incidència"
    CANCELLAT = "cancel·lat"


# ---------------------------------------------------------------- models
class Esdeveniment(BaseModel):
    """Una fita del recorregut de l'enviament."""
    data_hora: datetime = Field(..., description="Moment de l'esdeveniment")
    estat: EstatEnviament = Field(..., description="Estat en aquell moment")
    ubicacio: str = Field(..., description="Població on va passar")
    descripcio: str = Field(..., description="Descripció llegible per una persona")


class Enviament(BaseModel):
    """Estat complet del seguiment d'una comanda."""
    comanda_id: int = Field(..., description="Número de comanda", examples=[4521])
    client: str = Field(..., description="Nom del client destinatari")
    estat: EstatEnviament = Field(..., description="Estat actual")
    transportista: str
    codi_transportista: str
    numero_seguiment: str = Field(..., description="Codi de seguiment del transportista")
    magatzem_origen: str
    poblacio_desti: str
    data_sortida: date | None = Field(None, description="Data de sortida del magatzem")
    data_prevista: date | None = Field(None, description="Data estimada de lliurament")
    data_lliurament: date | None = Field(None, description="Data real, si ja s'ha lliurat")
    ubicacio_actual: str = Field(..., description="On és ara mateix la mercaderia")
    bultos: int
    pes_kg: float
    historial: list[Esdeveniment] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "comanda_id": 4521,
                "client": "Ferreteria Puig SL",
                "estat": "en trànsit",
                "transportista": "Transports Vallès Express",
                "numero_seguiment": "TVE-2026-0004521",
                "ubicacio_actual": "Centre de distribució de Granollers",
            }]
        }
    }


class Salut(BaseModel):
    estat: str
    servei: str
    versio: str
    latencia_simulada_ms: int
    taxa_error_simulada: float


# ----------------------------------------------------------- dades fictícies
def _rng(comanda_id: int) -> random.Random:
    """Generador determinista per comanda: la mateixa comanda dóna sempre el mateix."""
    llavor = int(hashlib.sha256(f"{LLAVOR}:{comanda_id}".encode()).hexdigest()[:8], 16)
    return random.Random(llavor)


# Els enviaments fixos de la demo. La 4521 ha de dir sempre el mateix:
# és la que es fa servir a la pregunta canònica del curs.
ENVIAMENTS_FIXOS: dict[int, dict] = {
    4521: {
        "client": "Ferreteria Puig SL",
        "estat": EstatEnviament.EN_TRANSIT,
        "transportista": "Transports Vallès Express",
        "codi_transportista": "TVE",
        "numero_seguiment": "TVE-2026-0004521",
        "magatzem_origen": "Central Sabadell",
        "poblacio_desti": "Granollers",
        "data_sortida": date(2026, 9, 5),
        "data_prevista": date(2026, 9, 8),
        "data_lliurament": None,
        "ubicacio_actual": "Centre de distribució de Granollers",
        "bultos": 2,
        "pes_kg": 14.6,
        "historial": [
            (datetime(2026, 9, 4, 16, 20), EstatEnviament.PREPARACIO, "Sabadell",
             "Comanda preparada al magatzem central. 2 bultos, 14,6 kg."),
            (datetime(2026, 9, 5, 8, 45), EstatEnviament.RECOLLIT, "Sabadell",
             "Recollida pel transportista Transports Vallès Express."),
            (datetime(2026, 9, 5, 19, 10), EstatEnviament.EN_TRANSIT, "Barcelona",
             "Arribada a la plataforma de Barcelona i classificació."),
            (datetime(2026, 9, 6, 7, 30), EstatEnviament.EN_TRANSIT, "Granollers",
             "Arribada al centre de distribució de Granollers."),
            (datetime(2026, 9, 6, 18, 0), EstatEnviament.EN_TRANSIT, "Granollers",
             "En espera de ruta de repartiment. Lliurament previst el 8 de setembre."),
        ],
    },
}


def _historial_sintetic(rng, estat, origen, desti, sortida, prevista, lliurament):
    ev: list[tuple] = []
    t = datetime.combine(sortida, datetime.min.time()) + timedelta(
        hours=rng.randint(8, 17))
    ev.append((t - timedelta(hours=rng.randint(4, 20)),
               EstatEnviament.PREPARACIO, origen,
               "Comanda preparada al magatzem."))
    ev.append((t, EstatEnviament.RECOLLIT, origen,
               "Recollida pel transportista."))
    if estat in (EstatEnviament.EN_TRANSIT, EstatEnviament.EN_REPARTIMENT,
                 EstatEnviament.LLIURAT, EstatEnviament.INCIDENCIA):
        parada = rng.choice(CIUTATS_RUTA)
        ev.append((t + timedelta(hours=rng.randint(6, 14)),
                   EstatEnviament.EN_TRANSIT, parada,
                   f"Arribada a la plataforma de {parada} i classificació."))
    if estat in (EstatEnviament.EN_REPARTIMENT, EstatEnviament.LLIURAT):
        ev.append((t + timedelta(hours=rng.randint(18, 30)),
                   EstatEnviament.EN_REPARTIMENT, desti,
                   "En ruta de repartiment."))
    if estat == EstatEnviament.LLIURAT and lliurament:
        ev.append((datetime.combine(lliurament, datetime.min.time())
                   + timedelta(hours=rng.randint(9, 18)),
                   EstatEnviament.LLIURAT, desti,
                   "Lliurat i albarà signat pel client."))
    if estat == EstatEnviament.INCIDENCIA:
        ev.append((t + timedelta(hours=rng.randint(20, 40)),
                   EstatEnviament.INCIDENCIA, desti,
                   "Destinatari absent. Es reintentarà el següent dia laborable."))
    return [Esdeveniment(data_hora=d, estat=e, ubicacio=u, descripcio=x)
            for d, e, u, x in sorted(ev, key=lambda x: x[0])]


def construeix_enviament(comanda_id: int) -> Enviament | None:
    """Genera (o recupera) l'enviament d'una comanda. Determinista."""
    if comanda_id in ENVIAMENTS_FIXOS:
        d = dict(ENVIAMENTS_FIXOS[comanda_id])
        d["historial"] = [
            Esdeveniment(data_hora=dh, estat=e, ubicacio=u, descripcio=x)
            for dh, e, u, x in d["historial"]
        ]
        return Enviament(comanda_id=comanda_id, **d)

    if not 1 <= comanda_id <= 5000:
        return None

    rng = _rng(comanda_id)
    transportista, codi = rng.choice(TRANSPORTISTES)
    desti = rng.choice(CIUTATS_RUTA)
    origen = rng.choice(["Central Sabadell", "Delegació Tarragona", "Delegació Girona"])

    estat = rng.choices(
        [EstatEnviament.LLIURAT, EstatEnviament.EN_TRANSIT,
         EstatEnviament.PREPARACIO, EstatEnviament.INCIDENCIA,
         EstatEnviament.CANCELLAT],
        weights=[72, 12, 8, 5, 3])[0]

    sortida = AVUI - timedelta(days=rng.randint(1, 900))
    prevista = sortida + timedelta(days=rng.randint(1, 4))
    lliurament = prevista if estat == EstatEnviament.LLIURAT else None

    ubicacio = {
        EstatEnviament.LLIURAT: f"Lliurat a {desti}",
        EstatEnviament.EN_TRANSIT: f"Centre de distribució de {rng.choice(CIUTATS_RUTA)}",
        EstatEnviament.PREPARACIO: f"Magatzem {origen}",
        EstatEnviament.INCIDENCIA: f"Delegació de {desti}",
        EstatEnviament.CANCELLAT: "—",
    }[estat]

    return Enviament(
        comanda_id=comanda_id,
        client=f"Client {comanda_id}",
        estat=estat,
        transportista=transportista,
        codi_transportista=codi,
        numero_seguiment=f"{codi}-{sortida.year}-{comanda_id:07d}",
        magatzem_origen=origen,
        poblacio_desti=desti,
        data_sortida=sortida if estat != EstatEnviament.PREPARACIO else None,
        data_prevista=prevista if estat != EstatEnviament.CANCELLAT else None,
        data_lliurament=lliurament,
        ubicacio_actual=ubicacio,
        bultos=rng.randint(1, 6),
        pes_kg=round(rng.uniform(0.8, 85.0), 1),
        historial=_historial_sintetic(rng, estat, origen, desti, sortida,
                                      prevista, lliurament),
    )


# ------------------------------------------------------------- dependències
async def comprova_clau(
    x_api_key: Annotated[str | None, Header(
        alias="X-API-Key",
        description="Clau d'API. Valor per defecte en desenvolupament: "
                    "el que hi hagi a la variable d'entorn API_KEY.",
    )] = None,
) -> None:
    """Autenticació per capçalera. Simple a propòsit: és una demo, no producció."""
    if x_api_key is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Falta la capçalera X-API-Key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    if x_api_key != API_KEY:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Clau d'API incorrecta.")


async def simula_xarxa() -> None:
    """Latència i errors artificials: la xarxa real no és perfecta i cal notar-ho."""
    if FAKE_LATENCY_MS > 0:
        await asyncio.sleep(FAKE_LATENCY_MS / 1000)
    if FAILURE_RATE > 0 and random.random() < FAILURE_RATE:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servei de seguiment no està disponible temporalment. "
                   "Torna-ho a provar.",
            headers={"Retry-After": "2"},
        )


# ------------------------------------------------------------------- app
app = FastAPI(
    title="API de seguiment d'enviaments",
    description=(
        "Servei de seguiment d'enviaments de **Distribucions Vallès SL**.\n\n"
        "Totes les dades són **fictícies**: forma part del material del curs "
        "*CIDET · IA en local*. És la tercera font de l'assistent, al costat "
        "dels documents i de la base de dades SQL.\n\n"
        "Autenticació: capçalera `X-API-Key`."
    ),
    version="1.0.0",
    contact={"name": "Mindora Technologies", "url": "https://mindoratechnologies.com"},
)


@app.get("/health", response_model=Salut, tags=["servei"],
         summary="Comprovació de salut")
async def health() -> Salut:
    """No demana autenticació: l'ha de poder consultar el healthcheck de Docker."""
    return Salut(
        estat="ok",
        servei="api-enviaments",
        versio=app.version,
        latencia_simulada_ms=FAKE_LATENCY_MS,
        taxa_error_simulada=FAILURE_RATE,
    )


@app.get("/shipments/{order_id}", response_model=Enviament, tags=["enviaments"],
         summary="Seguiment d'una comanda",
         dependencies=[Depends(comprova_clau), Depends(simula_xarxa)],
         responses={404: {"description": "No hi ha cap enviament per a la comanda"}})
async def enviament(order_id: int) -> Enviament:
    """Retorna l'estat, el transportista, les dates i l'historial d'un enviament.

    La comanda **4521** és la del cas d'estudi del curs i sempre respon el mateix.
    """
    env = construeix_enviament(order_id)
    if env is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"No consta cap enviament per a la comanda {order_id}.")
    return env


@app.get("/shipments", response_model=list[Enviament], tags=["enviaments"],
         summary="Enviaments d'un client",
         dependencies=[Depends(comprova_clau), Depends(simula_xarxa)])
async def enviaments_client(
    client: Annotated[str, Query(
        description="Nom del client (cerca parcial, sense distingir majúscules)",
        examples=["Ferreteria Puig"])],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[Enviament]:
    """Cerca els enviaments d'un client pel nom.

    En una implementació real això consultaria la base de dades. Aquí es
    resol sobre els enviaments coneguts, que és el que necessita la demo.
    """
    agulla = client.strip().lower()
    if not agulla:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="El paràmetre 'client' no pot ser buit.")
    trobats = [
        env for cid in ENVIAMENTS_FIXOS
        if (env := construeix_enviament(cid)) and agulla in env.client.lower()
    ]
    return trobats[:limit]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
