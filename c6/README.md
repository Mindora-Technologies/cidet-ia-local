# Classe 6 — SQL, API, integració i producció

**Dijous 17 de setembre de 2026 · 15:30–19:00**

Última classe. Els documents ja funcionen; avui connectem les **altres dues
fonts** i posem el conjunt en condicions d'ensenyar-lo a un client.

## Blocs

| Hora | Bloc |
|---|---|
| 15:30 – 16:15 | **Text-to-SQL**: com fer-ho sense que et buidin la base de dades |
| 16:15 – 17:00 | **Eines d'API**: timeouts, reintents i què fer quan la font externa cau |
| 17:00 – 17:15 | *Pausa* |
| 17:15 – 18:15 | Integració: l'agent amb les tres eines. Open WebUI |
| 18:15 – 19:00 | **Producció**: seguretat, còpies, monitoratge i el que et trucaran a preguntar |

## Materials

| Fitxer | Què és |
|---|---|
| `tools/sql.py` | Esquelet de l'eina de SQL, amb la validació per fer |
| `tools/api.py` | Esquelet de l'eina d'API, amb els reintents per fer |
| `checklist-entrega.md` | El que has de repassar abans de donar això per entregat |

La implementació completa i funcionant és a
[`demo/rag/tools/`](../demo/rag/tools/): a classe s'escriu la vostra i es
compara.

## Text-to-SQL sense fer-se mal

Deixar que un model escrigui SQL contra la base de dades d'un client fa por, i
amb raó. **Dues barreres, sempre les dues:**

1. **Validació sintàctica** (`sqlglot`): analitzar la consulta i rebutjar tot
   el que no sigui un `SELECT` sobre les vistes permeses, **abans** d'enviar-la.
   Dóna un error útil que el model pot corregir tot sol.
2. **Permisos de la base de dades**: connectar amb un rol `assistent_ro` que
   només té `GRANT SELECT` sobre les vistes. Encara que la validació falli, la
   base de dades diu que no.

La primera dóna bons missatges d'error. La segona és **la que et salva**. Amb
una de sola no n'hi ha prou: la validació és codi teu i pot tenir forats; els
permisos són la barrera de veritat.

```bash
# provar-ho:
python -c "
import sys; sys.path.insert(0,'demo/rag')
from tools.sql import valida
for q in ['SELECT * FROM clients', 'DELETE FROM comandes',
          'SELECT * FROM v_comandes_client WHERE comanda_id=4521']:
    try: print('PERMESA   ', valida(q))
    except Exception as e: print('BLOQUEJADA', q, '→', e)
"
```

**Vistes, no taules.** L'agent només veu quatre vistes. És menys superfície per
protegir, menys esquema per posar al prompt (i el prompt es paga en tokens), i
pots canviar les taules de sota sense tocar l'agent.

## Quan la font externa falla

Una API cau, va lenta, o retorna un 503. Si l'agent no ho contempla, la
resposta a l'usuari passa a ser «no ho sé» per un error que hauria durat mig
segon.

Al `demo/.env`:

```bash
FAKE_LATENCY_MS=3000
FAILURE_RATE=0.3
```

```bash
docker compose -f demo/docker-compose.yml up -d --force-recreate api
python demo/rag/agent.py "on és l'enviament de la comanda 4521?"
```

Es veuen els reintents amb espera exponencial (0,5 s · 1 s · 2 s). I es veu
també el cas dolent: quan els reintents s'esgoten, l'agent **ho ha de dir**,
no inventar-se l'estat de l'enviament.

## Posar-ho en producció

- **Ollama no té autenticació.** Qui arribi al port 11434 fa servir els teus
  models. Proxy amb clau al davant, i `ufw` només per a la subxarxa que toca.
- **Res de credencials al codi.** `.env` fora del control de versions, i el rol
  de base de dades amb els mínims privilegis.
- **Còpies**: el volum de Qdrant i el de Postgres. La col·lecció de vectors es
  pot reconstruir des dels documents, però triga; la base de dades, no.
- **Monitoratge**: `nvtop` no és monitoratge. Com a mínim, alerta si el servei
  d'Ollama cau i si el disc s'omple (els models creixen).
- **Registre de preguntes i respostes**: sense això no es pot millorar res, i
  el client acabarà preguntant per què va contestar allò. Compte amb el RGPD:
  registrar preguntes d'usuaris és tractar dades.
- **Actualitzacions**: un `apt upgrade` amb nucli nou et pot deixar sense
  driver NVIDIA. Programa-ho i prova-ho, no ho facis un divendres.

## Checklist d'entrega

[`checklist-entrega.md`](checklist-entrega.md) — repassa-la abans de donar
res per acabat a casa d'un client.

---

*CIDET · IA en local · Classe 6*
