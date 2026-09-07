# Classe 3 — Elecció del model i embeddings

**Dimecres 9 de setembre de 2026 · 15:30–19:00**

Ahir vam mesurar velocitat. Avui mesurem **qualitat**, que és molt més difícil
i molt més important. La pregunta del dia: *«com sé quin model és millor per al
MEU cas?»*. La resposta no és mirar rànquings d'internet.

## Blocs

| Hora | Bloc |
|---|---|
| 15:30 – 16:15 | Famílies de models oberts. Per què un rànquing general no et serveix |
| 16:15 – 17:00 | **Construir un banc de proves del teu domini**: `tests.jsonl` |
| 17:00 – 17:15 | *Pausa* |
| 17:15 – 18:00 | **Avaluació automàtica** amb model jutge: `eval_models.py` |
| 18:00 – 19:00 | **Embeddings**: què són, quin triar, i per què el català complica les coses |

## Materials

| Fitxer | Què és |
|---|---|
| `tests.jsonl` | 42 casos del domini de la distribuïdora, en 6 categories |
| `eval_models.py` | Executa el banc contra N models i els puntua amb un jutge |
| `embed_search.py` | Compara models d'embeddings per recall i MRR |

## El banc de proves

```bash
head -3 c3/tests.jsonl
```

Sis categories, i cada una mesura una cosa diferent:

| Categoria | Casos | Què mesura |
|---|---|---|
| `fets` | 15 | Recuperar un fet concret del corpus |
| `raonament` | 8 | Encadenar dos fets (data + termini → veredicte) |
| `format` | 5 | Complir el format demanat (taula, JSON, N paraules) |
| `instruccions` | 4 | Fer cas de restriccions («sense fer servir la paraula X») |
| `català` | 4 | Llengua correcta, sense castellanismes |
| `negativa` | 6 | **Dir «no ho sé»** en comptes d'inventar-se una dada |

La categoria `negativa` és la que separa de veritat els models. Un model que
puntua 8 de mitjana però 2 en negatives **no el vols** en un assistent
d'empresa: se t'inventarà preus davant d'un client.

## Avaluar

```bash
python c3/eval_models.py --models qwen3:4b qwen3:8b qwen3:14b --jutge qwen3:14b
```

Surten una taula en Markdown i un CSV a `c3/resultats/`. El CSV du la resposta
sencera de cada model: **llegiu-ne unes quantes a mà**. La nota del jutge
orienta, però no substitueix mirar-s'ho.

> ⚠️ El jutge ha de ser més gran que els models avaluats, i **mai el mateix**:
> un model que es puntua a si mateix es posa bona nota.

## Embeddings

```bash
python c3/embed_search.py --k 5
```

Dues mètriques i no una:

- **Recall@k** — el document bo, hi és entre els k primers?
- **MRR** — hi és *el primer*?

Un recall alt amb un MRR baix vol dir que el fragment correcte es recupera però
queda enterrat sota altres. Aquest és exactament el cas on un **reranker**
(classe 5) val la pena; si el recall ja és baix, un reranker no t'ajudarà.

## El detall del català

El català **tokenitza pitjor** que l'anglès: el mateix text ocupa un 25–35 % més
de tokens. Conseqüències pràctiques:

- El context se't consumeix més de pressa: 8k de context donen per menys text.
- Va més lent: més tokens per generar el mateix.
- Els embeddings entrenats sobretot en anglès **recuperen pitjor** en català.

Per això el banc de proves és en català: un model que puntua molt bé en anglès
pot caure en picat aquí, i és millor descobrir-ho ara que a casa del client.

## Deures per a la C4

1. Executar `eval_models.py` amb almenys dos models i portar la taula.
2. Afegir **5 casos vostres** a `tests.jsonl`, del domini del vostre client.

---

*CIDET · IA en local · Classe 3*
