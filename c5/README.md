# Classe 5 — RAG avançat, avaluació i agents

**Dimecres 16 de setembre de 2026 · 15:30–19:00**

El RAG mínim de la C4 ja respon. Avui l'arreglem per als casos on **no**
respon bé, i aprenem a saber-ho amb números en comptes de per intuïció.

## Blocs

| Hora | Bloc |
|---|---|
| 15:30 – 16:15 | Per què falla un RAG: recuperació, ordre, context i al·lucinació |
| 16:15 – 17:00 | **Millores**: cerca híbrida, reranking, reescriptura de la consulta |
| 17:00 – 17:15 | *Pausa* |
| 17:15 – 18:00 | **Avaluar-ho**: `eval.jsonl`, i mesurar si la millora millora de veritat |
| 18:00 – 19:00 | **Agents**: de «cercar i respondre» a «decidir què fer». LangGraph |

## Materials

| Fitxer | Què és |
|---|---|
| `eval.jsonl` | 30 preguntes amb resposta esperada, i quines fonts calen per a cadascuna |
| `rag_v2.py` | El RAG de la C4 amb híbrid + reranking + reescriptura, activables per flag |
| `evaluate.py` | Executa `eval.jsonl` contra una configuració i en dóna la nota |

## El mètode

Primer mesurar, després tocar. L'ordre invers és com es perd una tarda:

```bash
# 1. línia base: el RAG mínim de la C4
python c5/evaluate.py --sistema c4/rag.py

# 2. una millora cada cop
python c5/evaluate.py --sistema c5/rag_v2.py --hibrid
python c5/evaluate.py --sistema c5/rag_v2.py --hibrid --rerank
python c5/evaluate.py --sistema c5/rag_v2.py --hibrid --rerank --reescriu
```

Si una millora no mou la nota, **fora**: cada peça que hi afegeixes és latència
i una cosa més que es pot espatllar.

## Les quatre millores

| Millora | Quan ajuda | Quan no |
|---|---|---|
| **Cerca híbrida** (vectors + BM25) | Referències exactes, codis, noms propis (`REF-1001`) | Preguntes conceptuals |
| **Reranking** | Recall alt però MRR baix: el fragment bo hi és, però enterrat | Si el recall ja és dolent |
| **Reescriptura de la consulta** | Preguntes col·loquials o el·líptiques | Preguntes ja ben formulades |
| **Filtre per metadades** | Saps el tipus de document que vols | Cerques obertes |

## L'al·lucinació, de cara

```bash
python c5/rag_v2.py "quin preu té la REF-2231?"
```

La `REF-2231` no existeix. El sistema, tot i així, recuperarà els fragments de
tarifa més semblants i el model respondrà sobre **un altre producte** amb tota
la seguretat del món.

Tres defenses, i les tres calen:

1. **Llindar de similitud**: si el millor fragment queda per sota de X, no
   passar-li res al model i respondre que no consta.
2. **Instrucció de negativa** al prompt del sistema, explícita i repetida.
3. **Avaluació amb casos negatius**: a `eval.jsonl` n'hi ha 6. Si el vostre
   sistema no els passa, no és a punt per a un client.

## D'un RAG a un agent

Un RAG fa sempre el mateix: cerca, enganxa, respon. Un agent **decideix**.

La diferència es nota amb una pregunta com «*la comanda 4521 està en garantia?*»:
cap document ho sap, perquè depèn d'una data que és a la base de dades. El RAG
respondrà la política general; l'agent anirà a buscar la data i farà el càlcul.

L'agent complet és a [`demo/rag/agent.py`](../demo/rag/agent.py); avui se'n
llegeix el graf i es toca. Demà, a la C6, s'hi connecten SQL i API de debò.

> Un avís que val la classe sencera: l'agent de la demo fa **dues recuperacions
> deterministes** abans de deixar decidir el model (els documents, i la comanda
> que s'esmenta a la pregunta). No és casualitat. Els models petits, si els
> deixes triar, no obren el document i s'inventen el termini de garantia a
> partir dels mesos transcorreguts. Es veu amb:
>
> ```bash
> python demo/rag/agent.py --sense-precerca --traca \
>   "la comanda 4521 està en garantia?"
> ```
>
> **Deixar decidir el model no és sempre la millor arquitectura.**

## Deures per a la C6

1. La nota de `eval.jsonl` abans i després de les vostres millores.
2. Una pregunta del vostre client que el RAG no pugui respondre **per disseny**
   (perquè la resposta és en una base de dades o en una API). La resolem demà.

> Si et perds amb algun terme, tens el [glossari del curs](../docs/glossari.md).

---

*CIDET · IA en local · Classe 5*
