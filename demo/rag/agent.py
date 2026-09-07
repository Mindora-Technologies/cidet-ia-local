#!/usr/bin/env python3
"""L'assistent intern de Distribucions Vallès SL.

Orquestra les TRES fonts amb LangGraph i deixa que el model decideixi quines
fa servir i en quin ordre:

    cerca_documents      → Qdrant (manuals, procediments, fitxes)
    consulta_sql         → Postgres, només lectura i només vistes
    consulta_enviaments  → API REST de seguiment

La pregunta canònica del curs necessita encadenar-ne tres:

    «La comanda 4521 de Ferreteria Puig està en garantia? I on és l'enviament?»

    1. SQL       → de quin dia és la comanda i què duia
    2. Documents → quina garantia té aquella família de producte
    3. API       → on és ara l'enviament

Ús:
    python agent.py "la comanda 4521 està en garantia?"
    python agent.py --serve            # API compatible amb OpenAI, per a Open WebUI
    python agent.py --traca "..."      # mostra cada crida d'eina
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import httpx
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))
from tools.api import ErrorAPI, consulta_enviaments          # noqa: E402
from tools.documents import cerca_documents                  # noqa: E402
from tools.sql import ESQUEMA, ConsultaNoPermesa, consulta_sql  # noqa: E402

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
TEMPERATURA = float(os.getenv("TEMPERATURE", "0.1"))   # 0–0,3 per a empresa
MAX_PASSOS = int(os.getenv("MAX_STEPS", "6"))

# ------------------------------------------------------------------ prompt
SISTEMA = f"""\
Ets l'assistent intern de Distribucions Vallès SL, una empresa distribuïdora de
material industrial. Respons als treballadors de l'empresa en CATALÀ.

Tens tres eines i has de triar la que toqui en cada cas:

1. cerca_documents — manuals, procediments, tarifes i fitxes tècniques.
   Per a POLÍTIQUES: terminis de garantia, què cobreix, com es reclama,
   condicions de devolució, terminis d'enviament.

2. consulta_sql — base de dades de l'empresa, només lectura.
   Per a DADES CONCRETES: qui és un client, de quin dia és una comanda, què
   duia, quant va costar, quant estoc queda.
{ESQUEMA}

3. consulta_enviaments — API de seguiment.
   Per saber ON és físicament un enviament i quan arribarà. Aquesta informació
   NO és a la base de dades.

COM HAS DE TREBALLAR

· Sovint caldrà encadenar eines. Cap font sola té la resposta sencera.
· GARANTIES: la base de dades et dóna la data de la comanda, els productes i
  el termini en mesos; però QUÈ COBREIX la garantia, què en queda exclòs i com
  es reclama NOMÉS és als documents. Per a qualsevol pregunta de garantia,
  consulta SEMPRE les dues coses: consulta_sql per al cas concret i
  cerca_documents per a la política aplicable. Una resposta que només mira la
  base de dades és incompleta.
· ENVIAMENTS: on és la mercaderia només ho sap consulta_enviaments. La base de
  dades té l'estat administratiu de la comanda, no la ubicació física.
· La garantia depèn de la FAMÍLIA del producte. Una comanda amb productes de
  famílies diferents pot tenir unes línies en garantia i altres no: digue-ho.
· COM ES DECIDEIX si una línia està en garantia, i no de cap altra manera:
    1. mesos transcorreguts des de la data de la comanda (t'ho dóna el SQL)
    2. mesos de garantia de la seva família (t'ho diu el manual)
    3. si (1) < (2) → EN GARANTIA; si no → FORA DE GARANTIA
  Digues sempre els dos números i la data en què s'acaba. No facis servir cap
  altre criteri: ni la data de lliurament, ni l'entrada en vigor del manual,
  ni res que no siguin aquests dos números.
· Els noms de client de la base de dades porten la forma social («Ferreteria
  Puig SL», no «Ferreteria Puig»). Cerca'ls sempre amb
  `client ILIKE '%Puig%'`, mai amb una igualtat exacta.
· Si una consulta no retorna cap fila, no et rendeixis: torna-hi amb un filtre
  més ample abans de dir que no hi ha dades.
· Cita SEMPRE les fonts amb [1], [2]… i llista-les al final.
· Si les eines no et donen la informació, digues clarament que NO la tens.
  No te la inventis MAI. Una referència de producte que no surt enlloc no
  existeix: no n'inventis el preu ni les característiques.
· Si la pregunta ja porta el número de comanda o el nom del client, FES-LOS
  SERVIR. No demanis mai a l'usuari una dada que ja t'ha donat.
· Respon SEMPRE en català, encara que la pregunta barregi idiomes.
· Respon de manera breu i directa, com ho faria un company de feina.
"""

# ------------------------------------------------------- definició d'eines
EINES = [
    {
        "type": "function",
        "function": {
            "name": "cerca_documents",
            "description": (
                "Cerca als manuals, procediments, tarifes i fitxes tècniques de "
                "l'empresa. Per a polítiques de garantia, devolucions, "
                "enviaments i especificacions de producte."),
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {"type": "string",
                                 "description": "Què cal cercar, en català."},
                    "k": {"type": "integer",
                          "description": "Quants fragments recuperar (per defecte 5)."},
                },
                "required": ["consulta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consulta_sql",
            "description": (
                "Executa un SELECT sobre les vistes de la base de dades per "
                "obtenir dades concretes de clients, comandes, productes i estoc."),
            "parameters": {
                "type": "object",
                "properties": {
                    "consulta": {"type": "string",
                                 "description": "Consulta SELECT de PostgreSQL."},
                },
                "required": ["consulta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consulta_enviaments",
            "description": (
                "Consulta l'estat i la ubicació d'un enviament a l'API de "
                "seguiment. Per saber on és una comanda i quan arribarà."),
            "parameters": {
                "type": "object",
                "properties": {
                    "comanda_id": {"type": "integer",
                                   "description": "Número de comanda."},
                    "client": {"type": "string",
                               "description": "Alternativament, nom del client."},
                },
            },
        },
    },
]


# ------------------------------------------------------------------ estat
@dataclass
class Font:
    """Una font citada a la resposta."""
    etiqueta: str
    detall: str


@dataclass
class Estat:
    """L'estat que va passant pel graf."""
    pregunta: str
    missatges: list[dict[str, Any]] = field(default_factory=list)
    fonts: list[Font] = field(default_factory=list)
    passos: int = 0
    traca: bool = False
    resposta: str = ""


# --------------------------------------------------------- execució d'eines
def _executa_eina(nom: str, args: dict, estat: Estat) -> str:
    """Executa una eina i registra les fonts. Els errors tornen com a text:
    el model ha de poder reaccionar-hi, no petar."""
    t0 = time.time()
    try:
        if nom == "cerca_documents":
            passatges = cerca_documents(args["consulta"], k=int(args.get("k", 5)))
            if not passatges:
                return "Cap document coincideix amb la cerca."
            trossos = []
            for p in passatges:
                estat.fonts.append(Font(p.cita(), p.tipus_document))
                n = len(estat.fonts)
                trossos.append(f"[{n}] ({p.cita()}, rellevància {p.puntuacio:.2f})\n"
                               f"{p.text}")
            return "\n\n".join(trossos)

        if nom == "consulta_sql":
            res = consulta_sql(args["consulta"])
            estat.fonts.append(Font("base de dades", res.consulta))
            n = len(estat.fonts)
            sortida = (f"[{n}] Consulta executada:\n{res.consulta}\n\n"
                       f"{res.markdown()}")
            if not res.files:
                sortida += ("\n\nCap fila. Si has filtrat per nom de client, "
                            "prova amb ILIKE '%paraula%': els noms porten la "
                            "forma social (SL, SA…).")
            return sortida

        if nom == "consulta_enviaments":
            envs = consulta_enviaments(
                comanda_id=args.get("comanda_id"), client=args.get("client"))
            if not envs:
                return "L'API no té cap enviament per a aquesta comanda."
            estat.fonts.append(Font("API d'enviaments",
                                    f"comanda {args.get('comanda_id') or args.get('client')}"))
            n = len(estat.fonts)
            return f"[{n}] " + "\n\n".join(e.resum() for e in envs)

        return f"Eina desconeguda: {nom}"

    except ConsultaNoPermesa as e:
        return (f"La consulta ha estat rebutjada: {e}\n"
                f"Reescriu-la fent servir només les vistes permeses.")
    except ErrorAPI as e:
        return f"L'API d'enviaments no ha respost: {e}"
    except Exception as e:                       # noqa: BLE001
        return f"L'eina ha fallat: {type(e).__name__}: {e}"
    finally:
        if estat.traca:
            print(f"    ↳ {nom} en {time.time()-t0:.2f} s", file=sys.stderr)


# ------------------------------------------------------------------- model
def _crida_model(missatges: list[dict], amb_eines: bool = True) -> dict:
    cos = {
        "model": MODEL,
        "messages": missatges,
        "stream": False,
        "options": {"temperature": TEMPERATURA},
    }
    if amb_eines:
        cos["tools"] = EINES
    r = httpx.post(f"{OLLAMA_URL}/api/chat", json=cos, timeout=300.0)
    if r.status_code == 404:
        raise SystemExit(
            f"✘ el model «{MODEL}» no hi és a Ollama.\n"
            f"  Baixa'l amb:  ollama pull {MODEL}\n"
            f"  O tria'n un altre:  OLLAMA_MODEL=... python agent.py \"...\"")
    r.raise_for_status()
    return r.json()["message"]


# -------------------------------------------------------------------- graf
def construeix_graf():
    """Graf de LangGraph: pensa → (eines → pensa)* → respon.

    És el patró ReAct. LangGraph aporta l'estat explícit i el límit de passos:
    sense això, un model que s'encanta es queda en bucle cridant eines.
    """
    from langgraph.graph import END, StateGraph

    def node_pensa(estat: Estat) -> Estat:
        estat.passos += 1
        msg = _crida_model(estat.missatges, amb_eines=estat.passos <= MAX_PASSOS)
        estat.missatges.append(msg)
        # La resposta s'ha de fixar AQUÍ, en un node. Les mutacions fetes dins
        # de la funció d'enrutament de LangGraph no es propaguen a l'estat.
        if not msg.get("tool_calls"):
            estat.resposta = msg.get("content", "") or ""
        if estat.traca and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                f = tc["function"]
                print(f"  → {f['name']}({json.dumps(f.get('arguments', {}), ensure_ascii=False)[:110]})",
                      file=sys.stderr)
        return estat

    def node_eines(estat: Estat) -> Estat:
        for tc in estat.missatges[-1].get("tool_calls", []):
            f = tc["function"]
            args = f.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            estat.missatges.append({
                "role": "tool",
                "content": _executa_eina(f["name"], args, estat),
            })
        return estat

    def decideix(estat: Estat) -> str:
        """Només enruta: no toca l'estat (LangGraph descartaria els canvis)."""
        ultim = estat.missatges[-1]
        if ultim.get("tool_calls") and estat.passos <= MAX_PASSOS:
            return "eines"
        return END

    g = StateGraph(Estat)
    g.add_node("pensa", node_pensa)
    g.add_node("eines", node_eines)
    g.set_entry_point("pensa")
    g.add_conditional_edges("pensa", decideix, {"eines": "eines", END: END})
    g.add_edge("eines", "pensa")
    return g.compile()


GRAF = None


def _precerca(pregunta: str, estat: Estat, k: int = 4) -> str | None:
    """Recuperació documental SEMPRE activa, abans que el model raoni.

    Per què no ho deixem només a criteri del model: perquè els models petits
    tendeixen a no cridar l'eina de documents quan la base de dades ja els ha
    donat alguna cosa que s'hi assembla, i llavors s'inventen la política. Amb
    el fragment del manual al davant, això no passa.

    És el patró habitual en producció: en un assistent documental, la cerca no
    és opcional. Amb --sense-precerca es pot veure la diferència (C5).
    """
    try:
        passatges = cerca_documents(pregunta, k=k)
    except Exception as e:                        # noqa: BLE001
        if traça := estat.traca:
            print(f"  ! la precerca ha fallat: {e}", file=sys.stderr)
        return None
    if not passatges:
        return None
    trossos = []
    for p in passatges:
        estat.fonts.append(Font(p.cita(), p.tipus_document))
        trossos.append(f"[{len(estat.fonts)}] ({p.cita()})\n{p.text}")
    if estat.traca:
        print(f"  → precerca documental: {len(passatges)} fragments",
              file=sys.stderr)
    return "\n\n".join(trossos)


def _entitats(pregunta: str) -> int | None:
    """Treu el número de comanda de la pregunta, si n'hi ha un d'inequívoc."""
    m = re.search(r"\bcomanda\s+(?:n[uú]m\.?\s*)?(\d{1,5})\b", pregunta, re.I)
    return int(m.group(1)) if m else None


def _precarrega_comanda(comanda_id: int, estat: Estat) -> str | None:
    """Resol la comanda esmentada a la pregunta ABANS de raonar.

    Els models petits fallen d'una manera molt concreta: tenen el número de
    comanda davant dels nassos i tot i així demanen a l'usuari «quina comanda
    és?». Resoldre les entitats de la pregunta de manera determinista abans de
    cridar el model treu aquest error de l'equació, i és el que es fa en
    producció (entity pre-fetch). El model continua podent cridar les eines si
    necessita res més.
    """
    trossos: list[str] = []
    try:
        r = consulta_sql(
            "SELECT client, data_comanda, referencia, producte, familia, "
            "dies_des_de_la_comanda, mesos_des_de_la_comanda "
            f"FROM v_garanties_comanda WHERE comanda_id = {comanda_id}")
        if r.files:
            estat.fonts.append(Font("base de dades", r.consulta))
            trossos.append(f"[{len(estat.fonts)}] Línies de la comanda "
                           f"{comanda_id} (base de dades):\n{r.markdown()}")
    except Exception as e:                        # noqa: BLE001
        if estat.traca:
            print(f"  ! precàrrega SQL fallida: {e}", file=sys.stderr)

    try:
        envs = consulta_enviaments(comanda_id=comanda_id)
        if envs:
            estat.fonts.append(Font("API d'enviaments", f"comanda {comanda_id}"))
            trossos.append(f"[{len(estat.fonts)}] Enviament de la comanda "
                           f"{comanda_id} (API):\n{envs[0].resum()}")
    except Exception as e:                        # noqa: BLE001
        if estat.traca:
            print(f"  ! precàrrega de l'enviament fallida: {e}", file=sys.stderr)

    if trossos and estat.traca:
        print(f"  → precàrrega de la comanda {comanda_id}: "
              f"{len(trossos)} blocs", file=sys.stderr)
    return "\n\n".join(trossos) if trossos else None


def respon(pregunta: str, traca: bool = False,
           precerca: bool = True) -> tuple[str, list[Font]]:
    """Respon una pregunta fent servir les eines que calgui."""
    global GRAF
    if GRAF is None:
        GRAF = construeix_graf()

    estat = Estat(
        pregunta=pregunta,
        missatges=[{"role": "system", "content": SISTEMA}],
        traca=traca,
    )

    if precerca:
        if context := _precerca(pregunta, estat):
            estat.missatges.append({
                "role": "system",
                "content": ("Fragments dels documents de l'empresa que poden ser "
                            "rellevants per a la pregunta. Fes-los servir i "
                            "cita'ls amb el seu número. Si no diuen el que "
                            "necessites, crida cerca_documents amb uns altres "
                            "termes.\n\n" + context),
            })
        if (cid := _entitats(pregunta)) and (dades := _precarrega_comanda(cid, estat)):
            estat.missatges.append({
                "role": "system",
                "content": (f"Dades ja resoltes de la comanda {cid}. NO demanis "
                            f"a l'usuari el número de comanda: ja el tens. "
                            f"Fes servir aquestes dades i cita-les.\n\n" + dades),
            })
    estat.missatges.append({"role": "user", "content": pregunta})
    final = GRAF.invoke(estat)
    if isinstance(final, dict):          # LangGraph retorna dict
        resposta = final.get("resposta") or ""
        fonts = final.get("fonts") or []
    else:
        resposta, fonts = final.resposta, final.fonts
    return resposta, fonts


def formata(resposta: str, fonts: list[Font]) -> str:
    if not resposta.strip():
        resposta = ("(El model no ha arribat a redactar cap resposta. "
                    "Sol passar quan s'esgota el límit de passos: prova de "
                    "pujar MAX_STEPS o de fer servir un model amb millor "
                    "suport d'eines.)")
    if not fonts:
        return resposta
    # Només llistem les fonts que el model ha citat de veritat.
    citades = {int(n) for n in re.findall(r"\[(\d+)\]", resposta)}
    linies = [resposta, "", "Fonts:"]
    for i, f in enumerate(fonts, start=1):
        marca = "" if not citades or i in citades else "  (no citada)"
        linies.append(f"  [{i}] {f.etiqueta} — {f.detall[:90]}{marca}")
    return "\n".join(linies)


# ------------------------------------------------- servidor estil OpenAI
# Els models Pydantic han d'estar a NIVELL DE MÒDUL. Amb
# «from __future__ import annotations» les anotacions són cadenes, i FastAPI
# les resol al namespace del mòdul: si la classe es defineix dins d'una funció
# no la troba, tracta el paràmetre com a query i tota petició torna un 422.
class MissatgeOpenAI(BaseModel):
    role: str
    # Open WebUI pot enviar el contingut com a text o com a llista de parts.
    content: str | list[dict[str, Any]] | None = None

    def text(self) -> str:
        if isinstance(self.content, list):
            return " ".join(p.get("text", "") for p in self.content
                            if isinstance(p, dict))
        return self.content or ""


class PeticioOpenAI(BaseModel):
    # Els clients envien molts més camps dels que fem servir (temperature,
    # max_tokens, metadata, tools…). Els acceptem i els ignorem.
    model_config = {"extra": "allow"}

    model: str = "assistent-valles"
    messages: list[MissatgeOpenAI]
    stream: bool = False


# Els dos models que veu Open WebUI. El segon existeix NOMÉS per ensenyar el
# contrast a classe: la mateixa pregunta, el mateix model de llenguatge, però
# sense documents, sense SQL i sense API. És la diapositiva 5 del curs feta en
# directe: primer es pregunta al model pelat («no en tinc ni idea») i després
# a l'assistent («la 4521 és del 12 de març de 2025…»).
MODEL_AMB_RAG = "assistent-valles"
MODEL_SENSE_RAG = "model-pelat-sense-rag"

SISTEMA_PELAT = """Ets un assistent útil. Respon en català, de manera breu."""


def _passthrough(missatges: list[dict]) -> str:
    """Parla amb el model DIRECTAMENT: sense documents, sense eines, sense res.

    És el mateix model de llenguatge que fa servir l'assistent. L'única
    diferència és que no té accés a la informació de l'empresa -- i per això
    no pot respondre res concret, o s'ho inventa.
    """
    cos = {
        "model": MODEL, "stream": False,
        "options": {"temperature": TEMPERATURA},
        "messages": [{"role": "system", "content": SISTEMA_PELAT}, *missatges],
    }
    r = httpx.post(f"{OLLAMA_URL}/api/chat", json=cos, timeout=300.0)
    r.raise_for_status()
    return r.json()["message"].get("content", "").strip()


def _resposta_openai(model: str, contingut: str) -> dict:
    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": contingut},
            "finish_reason": "stop",
        }],
    }


def _flux_sse(model: str, contingut: str) -> Iterator[str]:
    """Format de streaming d'OpenAI (SSE).

    L'agent no genera en streaming —treballa amb eines i no té la resposta
    fins al final—, però Open WebUI demana stream=true per defecte i es queda
    en blanc si rep un JSON normal. Enviem la resposta en trossos perquè el
    client la vagi pintant.
    """
    creat = int(time.time())
    base = {"id": f"chatcmpl-{creat}", "object": "chat.completion.chunk",
            "created": creat, "model": model}

    yield f"data: {json.dumps({**base, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"
    for i in range(0, len(contingut), 96):
        tros = contingut[i:i + 96]
        yield f"data: {json.dumps({**base, 'choices': [{'index': 0, 'delta': {'content': tros}, 'finish_reason': None}]}, ensure_ascii=False)}\n\n"
    yield f"data: {json.dumps({**base, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
    yield "data: [DONE]\n\n"


def servidor():
    """API compatible amb OpenAI per enganxar l'agent a Open WebUI."""
    from fastapi import FastAPI
    from fastapi.responses import StreamingResponse
    import uvicorn

    api = FastAPI(title="Assistent Distribucions Vallès",
                  description="Agent RAG amb documents, SQL i API. "
                              "Compatible amb el protocol d'OpenAI.")

    @api.get("/v1/models")
    def models() -> dict:
        ara = int(time.time())
        return {"object": "list", "data": [
            {"id": MODEL_AMB_RAG, "object": "model",
             "created": ara, "owned_by": "mindora"},
            {"id": MODEL_SENSE_RAG, "object": "model",
             "created": ara, "owned_by": "mindora"},
        ]}

    @api.post("/v1/chat/completions")
    def completions(p: PeticioOpenAI):
        pregunta = next((m.text() for m in reversed(p.messages)
                         if m.role == "user"), "")
        if not pregunta.strip():
            contingut = "No he rebut cap pregunta."
        elif p.model == MODEL_SENSE_RAG:
            # Model pelat: cap font, cap eina. El contrast de la classe 1.
            contingut = _passthrough(
                [{"role": m.role, "content": m.text()} for m in p.messages
                 if m.role in ("user", "assistant")])
        else:
            text, fonts = respon(pregunta)
            contingut = formata(text, fonts)

        if p.stream:
            return StreamingResponse(
                _flux_sse(p.model, contingut), media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
        return _resposta_openai(p.model, contingut)

    @api.get("/health")
    def health() -> dict:
        return {"estat": "ok", "model": MODEL}

    port = int(os.getenv("AGENT_PORT", "8000"))
    print(f"Assistent escoltant a http://0.0.0.0:{port}  (model {MODEL})")
    print("A Open WebUI: Settings → Connections → OpenAI API → "
          f"http://localhost:{port}/v1")
    uvicorn.run(api, host="0.0.0.0", port=port)


# -------------------------------------------------------------------- CLI
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pregunta", nargs="*", help="la pregunta, en català")
    ap.add_argument("--serve", action="store_true",
                    help="aixeca l'API compatible amb OpenAI")
    ap.add_argument("--traca", action="store_true",
                    help="mostra cada crida d'eina per stderr")
    ap.add_argument("--sense-precerca", action="store_true",
                    help="desactiva la cerca documental automàtica: es veu com "
                         "el model s'inventa la política quan no la té davant")
    args = ap.parse_args()

    if args.serve:
        servidor()
        return

    pregunta = " ".join(args.pregunta).strip()
    if not pregunta:
        ap.error("cal una pregunta (o --serve)")

    t0 = time.time()
    text, fonts = respon(pregunta, traca=args.traca,
                         precerca=not args.sense_precerca)
    print("\n" + formata(text, fonts))
    print(f"\n({time.time()-t0:.1f} s · model {MODEL})")


if __name__ == "__main__":
    main()
