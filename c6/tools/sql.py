#!/usr/bin/env python3
"""Eina de SQL — esquelet de la classe 6.

L'objectiu: que el model pugui consultar la base de dades sense poder
espatllar-la. La implementació completa és a demo/rag/tools/sql.py; aquí
s'escriu la vostra.

REGLA DEL DIA: dues barreres, sempre les dues.
  1. Validar la consulta abans d'executar-la  (missatges d'error útils)
  2. Connectar amb un rol de només lectura    (la que et salva de debò)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras
import sqlglot
from sqlglot import exp

DSN = os.getenv("POSTGRES_DSN",
                "postgresql://assistent_ro:CANVIA@localhost:5432/distribuidora")

# Superfície mínima: vistes, mai taules crues.
VISTES_PERMESES: set[str] = {
    "v_comandes_client",
    "v_detall_comanda",
    "v_garanties_comanda",
    "v_estoc_disponible",
}

# L'esquema que es posa al prompt del model. Cada línia es paga en tokens:
# per això vistes i no taules.
ESQUEMA = """\
v_comandes_client(comanda_id, data_comanda, estat, client_id, client, poblacio,
                  magatzem, import_net, num_linies)
v_detall_comanda(comanda_id, data_comanda, estat, client, num_linia, referencia,
                 producte, familia, garantia_mesos, quantitat, preu_unitari,
                 descompte_pct, import_linia)
v_garanties_comanda(comanda_id, client, data_comanda, referencia, producte,
                    familia, dies_des_de_la_comanda, mesos_des_de_la_comanda)
v_estoc_disponible(referencia, producte, familia, magatzem, unitats, minim,
                   sota_minim)
"""


class ConsultaNoPermesa(ValueError):
    """La consulta s'ha rebutjat. NO s'ha arribat a executar."""


@dataclass
class ResultatSQL:
    consulta: str
    columnes: list[str]
    files: list[dict[str, Any]]


def valida(consulta: str) -> str:
    """Rebutja tot el que no sigui un SELECT sobre les vistes permeses.

    EXERCICI DE LA CLASSE 6. Els casos que ha de bloquejar:

        DELETE FROM clients                        → no és un SELECT
        SELECT * FROM clients                      → taula no permesa
        SELECT 1; DROP TABLE clients               → dues sentències
        SELECT * FROM v_comandes_client -- hola    → comentari
        SELECT pg_sleep(60)                        → funció del sistema
        WITH x AS (SELECT * FROM clients) SELECT…  → taula prohibida dins d'una CTE

    I els que ha de PERMETRE:

        SELECT * FROM v_comandes_client WHERE comanda_id = 4521
        SELECT c.*, d.* FROM v_comandes_client c JOIN v_detall_comanda d USING (comanda_id)
        WITH x AS (SELECT * FROM v_detall_comanda) SELECT familia, count(*) FROM x GROUP BY 1

    Pista: sqlglot.parse() dóna una llista (una entrada per sentència);
    arbre.find_all(exp.Table) dóna les taules; els àlies de les CTE
    (arbre.find_all(exp.CTE)) NO són taules i s'han de permetre.

    Retorna la consulta amb LIMIT afegit si no en duia.
    """
    net = consulta.strip().rstrip(";").strip()
    if not net:
        raise ConsultaNoPermesa("La consulta és buida.")

    arbres = sqlglot.parse(net, dialect="postgres")
    if len(arbres) != 1:
        raise ConsultaNoPermesa("Només s'admet una sentència.")

    # TODO 1: comprovar que l'arbre és un SELECT (exp.Select / exp.Query)
    # TODO 2: recórrer l'arbre i rebutjar exp.Insert, exp.Update, exp.Delete,
    #         exp.Drop, exp.Create, exp.Alter, exp.Command…
    # TODO 3: recollir els àlies de les CTE i permetre'ls
    # TODO 4: comprovar que totes les taules són a VISTES_PERMESES
    # TODO 5: rebutjar comentaris (--, /*) i funcions del sistema (pg_sleep…)
    # TODO 6: afegir LIMIT si no en duu

    raise NotImplementedError(
        "Implementa valida(). La versió de referència és a "
        "demo/rag/tools/sql.py — mira-la NOMÉS quan hagis provat la teva.")


def consulta_sql(consulta: str) -> ResultatSQL:
    """Executa un SELECT sobre les vistes.

    La connexió és amb el rol de només lectura, i a més amb la sessió marcada
    com a readonly. És la segona barrera: encara que valida() tingui un forat,
    la base de dades diu que no.
    """
    segura = valida(consulta)
    with psycopg2.connect(DSN) as conn:
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(segura)
            files = [dict(f) for f in cur.fetchall()]
            columnes = [d[0] for d in cur.description] if cur.description else []
    return ResultatSQL(consulta=segura, columnes=columnes, files=files)


if __name__ == "__main__":
    proves = [
        ("SELECT * FROM v_comandes_client WHERE comanda_id = 4521", True),
        ("SELECT * FROM clients", False),
        ("DELETE FROM comandes", False),
        ("SELECT 1; DROP TABLE clients", False),
        ("SELECT * FROM v_comandes_client -- comentari", False),
        ("SELECT pg_sleep(60)", False),
        ("WITH x AS (SELECT * FROM v_detall_comanda) SELECT * FROM x", True),
        ("WITH x AS (SELECT * FROM clients) SELECT * FROM x", False),
    ]
    encerts = 0
    for q, hauria_de_passar in proves:
        try:
            valida(q)
            resultat = True
        except NotImplementedError:
            print("✘ valida() encara no està implementada")
            raise SystemExit(1)
        except ConsultaNoPermesa:
            resultat = False
        marca = "✔" if resultat == hauria_de_passar else "✘"
        encerts += resultat == hauria_de_passar
        print(f"  {marca} {'PERMESA   ' if resultat else 'BLOQUEJADA'} {q[:56]}")
    print(f"\n{encerts}/{len(proves)} correctes")
