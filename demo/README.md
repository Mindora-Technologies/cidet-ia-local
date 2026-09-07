# La demo: l'assistent intern de Distribucions Vallès SL

> Aquesta és la demostració d'obertura del curs. Es projecta el **primer dia**,
> abans de la primera línia de teoria, perquè es vegi el destí abans de fer el camí.
> A la classe 6 els alumnes n'hauran construït una de pròpia.

---

## Què fa

Respon preguntes creuant **tres fonts que no es parlen entre elles**:

| Font | Què hi ha | Què NO hi ha |
|---|---|---|
| 📄 **Documents** (Qdrant) | La política: quina garantia té cada família, què cobreix, com es reclama | Cap dada del client concret |
| 🗄️ **SQL** (PostgreSQL) | El fet: quin dia es va comprar, què duia la comanda, quant va costar | Cap política; ni tan sols el termini de garantia |
| 🌐 **API REST** | On és físicament l'enviament i quan arribarà | Res del que hi ha a les altres dues |

Aquesta separació és **deliberada**. La pregunta canònica del curs no la pot
respondre cap font sola:

> **«La comanda 4521 de Ferreteria Puig està en garantia? I on és l'enviament?»**

Per contestar-la fa falta:

1. **SQL** → la comanda 4521 és del **12 de març de 2025** i duia un trepant
   percutor de la família *eines elèctriques*, més consumibles.
2. **Documents** → el manual de garanties diu que les *eines elèctriques* tenen
   **24 mesos** i els *consumibles*, **6**.
3. **Aritmètica** → han passat 17,9 mesos: el trepant **sí** que està en
   garantia (fins al 12/03/2027); els consumibles, **no**.
4. **API** → l'enviament és **en trànsit**, al centre de distribució de
   **Granollers**, amb lliurament previst el **8 de setembre**.

Fixa't que la resposta correcta és **matisada**: una part de la comanda està en
garantia i una altra no. Un assistent que respongui «sí» o «no» a seques
s'equivoca, encara que encerti la meitat.

---

## Arrencar-ho de zero

Cal **Docker** i **Ollama** amb GPU (vegeu [`../c1/install-server.md`](../c1/install-server.md)).

```bash
# 1. dependències de Python
python3 -m venv .venv && .venv/bin/pip install -r demo/requirements.txt

# 2. models (si no els tens)
ollama pull qwen3:8b
ollama pull qwen3-embedding:0.6b

# 3. tot: contenidors, dades, ingesta i verificació
./scripts/demo-up.sh
```

El script fa la feina sencera i acaba **llançant la pregunta canònica** i
comprovant que la resposta conté les tres fonts. Si passa, imprimeix:

```
╔════════════════════════════════════════════════════════════════════╗
║  La demo respon creuant les TRES fonts: documents + SQL + API.      ║
╚════════════════════════════════════════════════════════════════════╝
```

Després:

| | |
|---|---|
| Open WebUI | <http://localhost:3000> |
| Consola de Qdrant | <http://localhost:6333/dashboard> |
| API i documentació | <http://localhost:8080/docs> |
| Agent per línia d'ordres | `.venv/bin/python demo/rag/agent.py "…"` |

Per aturar-ho tot: `docker compose -f demo/docker-compose.yml down`
(afegeix `-v` per esborrar també les dades).

---

## Les peces

```
demo/
├── corpus/              16 documents en català (PDF i Word), generats
│   └── …                  · manual-garanties.pdf ← el que resol el cas 4521
│                          · tarifes-2026.pdf ← taules, per a la C4
│                          · acta-qualitat-escanejada.pdf ← sense capa de text
├── generar_corpus.py    genera el corpus (reproduïble, mateixa llavor que la BD)
├── db/
│   ├── generar_dades.py generador determinista
│   └── postgres-init.sql 500 clients · 300 productes · 5.000 comandes
├── api/
│   └── api_enviaments.py FastAPI amb X-API-Key, latència i errors simulables
├── rag/
│   ├── ingest.py        extracció → fragmentació → embeddings → Qdrant
│   ├── agent.py         l'agent LangGraph que ho orquestra tot
│   └── tools/           les tres eines: documents, sql, api
├── docker-compose.yml   Qdrant + Postgres + API + Open WebUI
└── .env.example         totes les variables, documentades
```

---

## Provar-ho a mà

```bash
# la pregunta del curs, amb traça de les crides d'eina
.venv/bin/python demo/rag/agent.py --traca \
  "La comanda 4521 de Ferreteria Puig està en garantia? I on és l'enviament?"

# només documents
.venv/bin/python demo/rag/agent.py "què cobreix la garantia d'una amoladora?"

# només SQL
.venv/bin/python demo/rag/agent.py "quantes comandes té Ferreteria Puig?"

# només API
.venv/bin/python demo/rag/agent.py "on és l'enviament de la comanda 4521?"

# comprovar quina font falla, si alguna cosa no rutlla
.venv/bin/python scripts/comprova-fonts.py
```

Per enganxar-lo a Open WebUI com un model més:

```bash
.venv/bin/python demo/rag/agent.py --serve
# Open WebUI → Settings → Connections → OpenAI API → http://localhost:8000/v1
```

---

## Els dos casos d'estudi que s'ensenyen amb això

### 1. L'al·lucinació de la `REF-2231`

```bash
.venv/bin/python demo/rag/agent.py "Quin preu té la referència REF-2231?"
```

La `REF-2231` **no existeix**: no és a la base de dades ni a cap document, i
està exclosa per construcció (el generador té una comprovació que ho impedeix).

El model, però, no diu «no ho sé». Agafa el fragment de tarifa que més s'hi
assembla i respon amb tota la seguretat del món sobre **un altre producte**.

És el moment més útil de la primera classe: no és que el model menteixi, és que
està fent exactament el que sap fer —continuar text plausible— i això, sense
control, **s'assembla molt a saber**.

Es tracta a la C5 amb: instruccions de negativa, llindar de similitud, i
avaluació amb casos que el model **ha** de rebutjar (`c5/eval.jsonl`).

### 2. El document escanejat

```bash
.venv/bin/python demo/rag/ingest.py --dry-run
```

Surt aquest avís:

```
⚠ sense text extraïble: acta-qualitat-escanejada.pdf
```

Aquell PDF és una **imatge**: no té capa de text. `pypdf` en treu zero
caràcters, i per tant **no entra al RAG**. El contingut hi és, l'usuari el veu
en obrir-lo, i tot i així l'assistent jura que no en sap res.

A qualsevol client hi haurà documents així. Es resol amb OCR a la C4.

---

## Per a la classe 6: latència i errors

L'API de seguiment simula una xarxa real. Al `.env`:

```bash
FAKE_LATENCY_MS=3000    # cada petició triga 3 segons
FAILURE_RATE=0.3        # una de cada tres peticions torna un 503
```

```bash
docker compose -f demo/docker-compose.yml up -d --force-recreate api
.venv/bin/python demo/rag/agent.py "on és l'enviament de la comanda 4521?"
```

L'eina de l'agent (`rag/tools/api.py`) ja porta reintents amb espera
exponencial (0,5 s · 1 s · 2 s). Amb aquests valors es veu treballar, i es veu
també què passa quan els reintents no basten: l'agent ho ha de dir, no
inventar-se l'estat de l'enviament.

---

## Regenerar les dades

Tot és determinista: la mateixa llavor dóna sempre els mateixos clients,
productes i comandes.

```bash
.venv/bin/python demo/db/generar_dades.py     # → postgres-init.sql
.venv/bin/python demo/generar_corpus.py       # → corpus/
.venv/bin/python demo/rag/ingest.py --reset   # → Qdrant
```

Els dos generadors comparteixen llavor, així que el corpus i la base de dades
sempre parlen dels mateixos productes. Si en canvies un, torna a executar
l'altre.

---

## Avís

**Totes les dades són fictícies.** *Distribucions Vallès SL*, els seus clients,
productes, comandes i enviaments s'han generat per a la formació. Les marques
dels productes són inventades. No hi ha cap dada real de CIDET ni de cap client.

---

*CIDET · IA en local · demo del curs*
