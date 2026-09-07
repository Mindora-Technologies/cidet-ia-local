# Estat del repositori

**Generat el 7 de setembre de 2026** · abans de la classe 1

Aquest document diu **què funciona, què no s'ha provat i què necessita que hi
posis la mà**. És per a Mindora, no per als alumnes.

---

## ✅ Fet i verificat de veritat

Coses que s'han executat i que han donat el resultat esperat.

### Fase 0 — suports físics

| Element | Estat |
|---|---|
| `scripts/00-descarrega-offline.sh` | ✅ Executat. Resol sol la versió de la ISO llegint `SHA256SUMS` (va detectar la **24.04.3**) i la versió del driver NVIDIA des de `latest.txt` |
| `docs/preparacio-pendrive.md` | ✅ Escrit. `dd`, Rufus, balenaEtcher, `docker load`, import de GGUF i checklist de motxilla |

### Fase 1 — classe 1

| Element | Estat |
|---|---|
| `c1/hardware-calc.xlsx` | ✅ Generat i verificat amb `scripts/verifica-xlsx.py`: fórmules reals (no valors), validacions, format condicional de tres estats, fulls `GPUs` i `Referencia` protegits sense contrasenya, cap cel·la desbordada |
| `c1/install-server.md` | ✅ 541 línies. Inclou el recorregut complet de Secure Boot amb MOK i la via offline des del `.run` |
| `c1/pull-models.sh` | ✅ `--list` provat; mode offline implementat |
| `c1/README.md` | ✅ Horaris, materials i deures |

### Fase 2 — la demo

| Element | Estat |
|---|---|
| `demo/db/postgres-init.sql` | ✅ **Carregat en un Postgres 16 real.** 500 clients, 300 productes, 5.000 comandes, 15.035 línies, 683 files d'estoc, 4 vistes. Els invariants (comanda 4521, Ferreteria Puig, absència de `REF-2231`) es comproven dins del mateix `.sql` i el fitxer no carrega si fallen |
| Rol `assistent_ro` | ✅ Provat: veu les vistes, i `SELECT * FROM clients` li dóna `permission denied` |
| `demo/corpus/` | ✅ 16 documents generats. L'acta escanejada té **0 caràcters** extraïbles (comprovat amb `pypdf`); la resta, entre 995 i 10.037 |
| `demo/api/api_enviaments.py` | ✅ Provat: 401 sense clau, 403 amb clau dolenta, 404 per a comandes inexistents, respostes deterministes |
| `demo/rag/ingest.py` | ✅ Ingesta completa: 25 fragments, 1.024 dimensions, a Qdrant |
| `demo/rag/agent.py` | ✅ Respon la pregunta canònica **creuant les tres fonts** |
| `demo/docker-compose.yml` | ✅ Els quatre serveis arriben a `healthy` |
| **`./scripts/demo-up.sh`** | ✅ **Criteri d'acceptació complert**: de zero a la resposta correcta, i comprova que la resposta conté el termini (documents), la data (SQL) i la ubicació (API). Falla amb un missatge clar si no |

### Fase 3 — classes 2 a 6

| Element | Estat |
|---|---|
| `c3/tests.jsonl` | ✅ 42 casos en 6 categories |
| `c3/eval_models.py` | ✅ Executat contra un model real: mesura nota per categoria, t/s i **VRAM real** via `nvidia-smi` |
| `c3/embed_search.py` | ✅ Executat: Recall@3 83 %, MRR 0,68 amb `qwen3-embedding:0.6b` |
| `c5/eval.jsonl` | ✅ 30 casos amb les fonts necessàries anotades |
| `c5/evaluate.py` | ✅ Executat contra `c4/rag.py`: **6,80/10** al subconjunt de documents |
| `c4/rag.py` | ✅ Respon correctament citant el manual |
| `c4/chunking.py` | ✅ Executat: taula comparativa de mides i solapaments |
| `c5/rag_v2.py` | ✅ Cerca híbrida (BM25 + vectors amb RRF) provada i funcionant |

### Higiene del repositori

- ✅ Cap secret, cap `.env` versionat, cap credencial al codi
- ✅ Els 4 scripts de bash passen `bash -n`; els 23 fitxers de Python, `ast.parse`
- ✅ Repositori **públic** a `Mindora-Technologies/cidet-ia-local`
- ✅ Commits atòmics per fase, missatges convencionals en anglès

---

## ⚠️ Fet però NO provat

| Element | Per què no s'ha pogut provar | Risc |
|---|---|---|
| **Obrir el `.xlsx` amb Excel i LibreOffice** | Cap dels dos està instal·lat en aquesta màquina i no hi ha `sudo` sense contrasenya per posar-hi LibreOffice | **Mitjà.** El fitxer s'ha verificat estructuralment (fórmules, validacions, formats, amplades) i s'ha corregit el defecte que va aparèixer a l'aula (la llista del context). Tot i així, **obre'l tu abans de repartir-lo** |
| `install-server.md` de punta a punta | Caldria una màquina sense sistema operatiu | Baix: els passos són estàndard, però el temps real de la classe pot variar |
| El recorregut de **Secure Boot / MOK** | Aquesta màquina no té Secure Boot actiu | Baix–mitjà: està escrit segons el procediment oficial, però no s'ha reproduït aquí |
| Instal·lació del driver des del `.run` | Trencaria el driver d'aquesta màquina | Baix |
| `c1/pull-models.sh` en mode `--offline` | Els GGUF encara s'estan baixant | Baix: la lògica és la mateixa que la documentada |
| `c2/bench.sh` | Necessita els models de la C2 baixats; a més fa servir `jq` | Baix. **Comprova que `jq` està instal·lat al servidor de l'aula** |
| `c3/eval_models.py` amb 3 models alhora | Provat amb un model i 4 casos; el banc sencer amb 3 models són ~2 h de GPU | Baix |
| Open WebUI enganxat a l'agent (`--serve`) | El contenidor arrenca i és `healthy`, però la connexió manual no s'ha fet | Baix |
| `shellcheck` | No està instal·lat i no hi ha `sudo` | Baix: els scripts passen `bash -n` |

---

## ❌ Què ha fallat i com s'ha resolt

| Problema | Causa | Resolució |
|---|---|---|
| **El desplegable de context del `.xlsx` rebutjava tots els valors** (detectat a l'aula) | Una llista literal (`"2048,4096,…"`) es compara com a **text**, però la cel·la conté un **número** — i el format de milers el mostrava com «8.192» | Els contextos són ara un rang numèric a `Referencia!H5:H11` i C10 hi apunta. El verificador comprova aquesta classe d'error perquè no torni |
| La resposta de l'agent sortia **buida** | Assignava la resposta dins de la funció d'enrutament de LangGraph, que **descarta les mutacions** | La resposta es fixa en un node |
| L'agent **s'inventava el termini de garantia** (deia «18 mesos» a partir dels mesos transcorreguts) | Amb la vista SQL calculant la garantia, el model no obria mai el document | La vista dóna la data i la família; el termini viu **només** al manual. A més, recuperació documental sempre activa |
| L'agent **demanava el número de comanda** que ja era a la pregunta | Els models petits fallen així | *Pre-fetch* determinista de la comanda esmentada a la pregunta |
| `scripts/demo-up.sh` no compilava | Un apòstrof dins de `"${VAR:-…l'enviament}"` **obre una cadena** per a bash i desincronitza el parseig de tot el fitxer | Valor per defecte definit a part, amb el comentari corresponent |
| `array+=(…)` a la dreta d'un `||` | Bash hi veu un comandament, no una assignació | Reescrit amb una funció |
| `exp.Subqueryable` no existeix | L'API de `sqlglot` va canviar; ara és `exp.Query` | Corregit |
| Les CTE legítimes es bloquejaven | L'àlies del `WITH` es llegia com una taula no permesa | Els àlies de CTE s'accepten; les CTE que llegeixen taules crues, no |
| Una marca real al catàleg | El generador feia servir el nom d'un fabricant real | Marques inventades (Valfort, Terramax, Norbrec, Ferralt, Duracamp) |

### Una discrepància del brief que has de validar

El brief dóna, alhora, la fórmula del curs i la matriu de la diapositiva 24, i
**no quadren**: amb `paràmetres × bytes/paràmetre × 1,1`, un Qwen3 14B en Q4 amb
8k de context surt a **8,9 GB**, no als ~11 GB de la diapositiva.

No he tocat la fórmula (el brief diu explícitament que no s'inventin les
constants). El full `Exemples` porta **les dues columnes**: la teòrica i la
mesurada a Ollama, amb els veredictes calculats sobre la mesurada —així la
matriu reprodueix la diapositiva— i una nota que explica per què difereixen
(Q4_K_M són ~0,6 bytes/paràmetre reals, no 0,5, i el runtime reserva búfers).

**Decisió teva:** o es queda així (recomanat: ensenya la diferència entre teoria
i pràctica, que és una lliçó del curs), o s'alineen les xifres de la diapositiva
amb la fórmula.

---

## 🔧 Requereix intervenció manual

### Abans de la classe 1 (avui)

1. **Obre `c1/hardware-calc.xlsx` amb Excel i amb LibreOffice.** És l'única
   comprovació que no s'ha pogut fer aquí. Mira els desplegables, el semàfor i
   el veredicte. *(10 min)*
2. **Acaba els USB.** La descàrrega segueix en marxa; segueix
   `docs/preparacio-pendrive.md`. *(30–45 min, en paral·lel)*
3. **Prova d'arrencar almenys un USB** en un dels equips de l'aula. *(10 min)*
4. **Revisa els horaris** de `c1/README.md`: els blocs són una proposta a partir
   del brief (3 blocs, 75 min de pràctica al final). *(5 min)*

### Decisions de contingut que són teves

- **La discrepància de la matriu de VRAM** (a dalt).
- **Logotips i imatge**: no n'hi ha cap. El sistema de disseny (blanc, accent
  `#0F6E6A`, peu «CIDET · IA en local · Classe N») s'aplica al `.xlsx` i als PDF
  del corpus, però **no hi ha cap logotip de Mindora ni de CIDET** enlloc.
- **Captures de pantalla**: cap document en du. Si en vols a
  `install-server.md` (la pantalla de MokManager, l'instal·lador d'Ubuntu),
  s'han de fer a mà.
- **Enllaços de la sessió**: `c1/README.md` enllaça recursos públics reals i el
  repositori. No hi ha cap enllaç a aula virtual, gravació ni contacte: no me'ls
  he inventat.
- **El `.pptx` de la classe 1** no s'ha tocat, tal com demanava el brief.

### Per a les classes següents

- **`c6/tools/sql.py` i `c6/tools/api.py` són esquelets amb `NotImplementedError`
  a posta**: són l'exercici. La versió que funciona és a `demo/rag/tools/`.
  Si prefereixes repartir-los resolts, copia-hi els de `demo/`.
- **`rerank()` a `c5/rag_v2.py` no està implementat** a posta: és l'exercici de
  la C5. Caldrà `ollama pull qwen3-reranker:0.6b` o un cross-encoder.
- **`c5/evaluate.py` amb el banc sencer** triga; llança'l abans de la classe.

---

## ⏱️ Temps estimat del que queda

| Tasca | Temps | Quan |
|---|---|---|
| Obrir i revisar el `.xlsx` a Excel/LibreOffice | 10 min | **Avui, abans de les 15:30** |
| Acabar la descàrrega offline (ISO + models) | 1–3 h de xarxa, desatès | En marxa |
| Gravar i etiquetar els 4 USB | 45 min | **Avui** |
| Provar l'arrencada d'un USB | 10 min | **Avui** |
| Decidir sobre la matriu de VRAM | 10 min | Abans del bloc 2 |
| Afegir logotips i captures | 1–2 h | Abans de la C2 |
| Implementar `rerank()` a `rag_v2.py` | 1–2 h | Abans de la C5 |
| Executar `c3/eval_models.py` amb 3 models | 2 h de GPU, desatès | Abans de la C3 |
| OCR de l'acta escanejada (material de la C4) | 30 min | Abans de la C4 |

**Bloquejant per a avui: només el punt 1 (obrir el full de càlcul) i els USB.**
La resta del material de la classe 1 està verificat.

---

## Com tornar a verificar-ho tot

```bash
.venv/bin/python scripts/verifica-xlsx.py     # el full de càlcul
.venv/bin/python scripts/comprova-fonts.py    # les tres fonts de la demo
./scripts/demo-up.sh                          # la demo de punta a punta
for f in $(git ls-files '*.sh'); do bash -n "$f"; done
```

---

*CIDET · IA en local · Mindora Technologies*
