# IA en local: del servidor verge al RAG agèntic

**Formació CIDET · 6 classes · 21 hores · del 7 al 17 de setembre de 2026**
Impartida per [Mindora Technologies](https://mindoratechnologies.com)

---

Aquest repositori conté **tot el material del curs**: guions d'instal·lació, scripts,
plantilles de dimensionament, el corpus de proves i la demo completa d'un assistent
intern que funciona **100 % en local, sense internet i sense enviar cap dada a fora**.

## De què va, això

Muntar un assistent d'IA per a una empresa sense que cap document surti de l'edifici.
Ni OpenAI, ni Azure, ni cap API de tercers: un servidor amb una GPU, models oberts, i
les dades a casa.

Durant les sis classes construïm, de zero, l'assistent intern d'una empresa
**distribuïdora** que respon combinant tres fonts:

- 📄 **Documents** — manuals de garantia, tarifes, procediments (PDF i Word)
- 🗄️ **Base de dades SQL** — clients, comandes, estoc
- 🌐 **API REST** — seguiment d'enviaments

La pregunta que ha de saber respondre al final:

> *«La comanda 4521 de Ferreteria Puig està en garantia? I on és l'enviament?»*

Per contestar-la cal creuar les tres fonts. Cap model sap fer-ho de sèrie: això és el
que aprendrem a construir.

---

## Calendari

| | Data | Tema | Material |
|---|---|---|---|
| **C1** | dl. 7/9 | Fonaments, maquinari i instal·lació del servidor | [`c1/`](c1/) |
| **C2** | dt. 8/9 | Ollama i execució de models en local | [`c2/`](c2/) |
| **C3** | dc. 9/9 | Elecció del model i embeddings | [`c3/`](c3/) |
| **C4** | dt. 15/9 | Ingesta, base de dades vectorial i RAG mínim | [`c4/`](c4/) |
| **C5** | dc. 16/9 | RAG avançat, avaluació i agents | [`c5/`](c5/) |
| **C6** | dj. 17/9 | SQL, API, integració i producció | [`c6/`](c6/) |

Horari: **15:30 – 19:00**

---

## Per on començo?

**Si ets alumne i avui és el primer dia** → [`c1/README.md`](c1/README.md)

**Si has de preparar els USB** → [`docs/preparacio-pendrive.md`](docs/preparacio-pendrive.md)

**Si vols veure la demo funcionant** → [`demo/README.md`](demo/README.md)

```bash
git clone https://github.com/Mindora-Technologies/cidet-ia-local.git
cd cidet-ia-local

# 1. Baixa el material pesat (ISO, driver, imatges Docker, models)
./scripts/00-descarrega-offline.sh

# 2. Instal·la el servidor seguint el guió
less c1/install-server.md

# 3. Models de la propera classe, en segon pla
./c1/pull-models.sh
```

---

## Estructura

```
├── c1/   Fonaments i instal·lació      → hardware-calc.xlsx, install-server.md
├── c2/   Ollama i execució             → Modelfile, benchmarks
├── c3/   Models i embeddings           → banc de proves, avaluació comparativa
├── c4/   Ingesta i RAG mínim           → Qdrant, chunking, rag.py
├── c5/   RAG avançat i agents          → reranking, avaluació, LangGraph
├── c6/   SQL, API i producció          → text-to-SQL, eines, desplegament
├── demo/ L'assistent complet           → corpus, BD, API, RAG i agent
├── docs/ Documentació transversal      → preparació dels USB
└── scripts/ Utilitats                  → descàrrega offline, verificacions
```

---

## Les fórmules del curs

```
VRAM_pesos (GB) ≈ paràmetres (B) × bytes/paràmetre × 1,1

tokens/s ≈ amplada de banda (GB/s) ÷ mida del model (GB)
```

**Bytes per paràmetre:** FP16 = 2 · Q8 = 1 · Q6 = 0,75 · **Q4 = 0,5** · Q3 = 0,4
**Rendiment real:** entre el 60 % i el 80 % del teòric.

Per fer els números sense pensar-hi: [`c1/hardware-calc.xlsx`](c1/hardware-calc.xlsx).

---

## Requisits

| | Mínim | Recomanat |
|---|---|---|
| GPU | 12 GB de VRAM | 16–24 GB |
| RAM | 16 GB | 32 GB |
| Disc | 100 GB lliures | 250 GB (SSD NVMe) |
| SO | Ubuntu Server 24.04 LTS | — |
| Programari | Docker, Ollama, Python 3.11+ | — |

---

## Avís sobre les dades

**Tot el contingut d'aquest repositori és fictici.** L'empresa *Distribucions Vallès SL*,
els seus clients, productes, comandes i enviaments s'han generat expressament per a la
formació. No hi ha cap dada real de CIDET ni de cap dels seus clients.

---

## Llicència

Codi: [MIT](LICENSE). Material didàctic: © 2026 Mindora Technologies — vegeu [`LICENSE`](LICENSE).

---

*CIDET · IA en local · Mindora Technologies*
