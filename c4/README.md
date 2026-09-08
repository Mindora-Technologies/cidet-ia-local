# Classe 4 — Ingesta, base de dades vectorial i RAG mínim

**Dimarts 15 de setembre de 2026 · 15:30–19:00**

Avui els documents del client entren al sistema. És la classe amb més feina
bruta i la que més determina si el RAG final funcionarà: **el 80 % dels
problemes d'un RAG són problemes d'ingesta**, no del model.

## Blocs

| Hora | Bloc |
|---|---|
| 15:30 – 16:15 | Extracció: `pypdf` vs `docling`. Taules, columnes i el desastre dels PDF |
| 16:15 – 17:00 | **OCR**: el document escanejat que no entra al RAG |
| 17:00 – 17:15 | *Pausa* |
| 17:15 – 18:00 | Fragmentació: mida, solapament, i per què tallar per frases |
| 18:00 – 19:00 | Qdrant i el primer RAG que respon: `rag.py` |

## Materials

| Fitxer | Què és |
|---|---|
| `docker-compose.qdrant.yml` | Qdrant sol, per començar de zero |
| `rag.py` | El RAG mínim: cerca + context + resposta. ~80 línies |
| `chunking.py` | Laboratori de fragmentació per veure l'efecte de cada paràmetre |

## Els dos casos d'estudi

### 1. Taules: `tarifes-2026.pdf`

```bash
python demo/rag/ingest.py --extractor pypdf   --dry-run --limit 16 | grep -A3 tarifes
python demo/rag/ingest.py --extractor docling --dry-run --limit 16 | grep -A3 tarifes
```

`pypdf` és ràpid i converteix la taula en una sopa de números sense capçalera:
el model llegirà «REF-1042 24.50 21 36» i no sabrà quin número és el preu.
`docling` la converteix en Markdown amb les columnes, i **el model l'entén**.

El preu és el temps: `docling` triga molt més i baixa models la primera vegada.
La decisió no és «quin és millor» sinó **on necessites qualitat**.

### 2. Escanejos: `acta-qualitat-escanejada.pdf`

```bash
python demo/rag/ingest.py --dry-run
# ⚠ sense text extraïble: acta-qualitat-escanejada.pdf
```

Aquell PDF és una imatge. Té zero caràcters extraïbles i, per tant, **no entra
al RAG**: l'usuari el veu perfectament en obrir-lo, però l'assistent jura que
no en sap res. A casa de qualsevol client n'hi haurà.

Es resol amb OCR (`ocrmypdf`, `tesseract` amb `-l cat`), i a classe es fa.

## Fragmentació

```bash
python c4/chunking.py --mides 300 500 800 1200 --solapaments 0 50 100 200
```

Els paràmetres tenen conseqüències reals:

- **Massa petit**: el fragment perd el context i el model no sap de què parla.
- **Massa gran**: el fragment du massa temes i l'embedding queda difús.
- **Sense solapament**: una frase partida per la meitat es perd per sempre.

Per defecte fem servir ~800 tokens amb 100 de solapament, tallant per frases.
No és màgia: és el que va bé amb documents de política com aquests.

## El RAG mínim

```bash
python c4/rag.py "quina garantia tenen les eines elèctriques?"
```

Vuitanta línies: vectoritzar la pregunta, cercar k fragments, enganxar-los al
prompt, i respondre. Res més. Funciona sorprenentment bé, i les classes 5 i 6
consisteixen a arreglar-ne els casos on no.

## Deures per a la C5

1. Ingerir **documents reals d'un client vostre** (anonimitzats).
2. Trobar **dues preguntes** que el RAG mínim respongui malament. Les arreglem a la C5.

> Si et perds amb algun terme, tens el [glossari del curs](../docs/glossari.md).

---

*CIDET · IA en local · Classe 4*
