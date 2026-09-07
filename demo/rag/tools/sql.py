"""Eina 2 — consulta a la base de dades, només lectura i només SELECT.

Dues barreres, a propòsit:
  1. `sqlglot` analitza la consulta i rebutja tot el que no sigui un SELECT
     sobre les vistes permeses, ABANS d'enviar-la.
  2. La connexió es fa amb el rol `assistent_ro`, que a la base de dades
     només té GRANT SELECT sobre les vistes.

La primera dóna un missatge d'error útil; la segona és la que et salva quan
la primera falla. Mai en fem servir només una.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras
import sqlglot
from sqlglot import exp

DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://assistent_ro:canvia_aquesta_contrasenya@localhost:5432/distribuidora",
)
LIMIT_FILES = int(os.getenv("SQL_MAX_ROWS", "50"))

# Superfície permesa: només les vistes. Res de taules crues.
VISTES_PERMESES = {
    "v_comandes_client",
    "v_detall_comanda",
    "v_garanties_comanda",
    "v_estoc_disponible",
}

ESQUEMA = """\
Vistes disponibles (només lectura):

v_comandes_client(comanda_id, data_comanda, estat, client_id, client, poblacio,
                  magatzem, import_net, num_linies)
    Una fila per comanda.

v_detall_comanda(comanda_id, data_comanda, estat, client, num_linia, referencia,
                 producte, familia, garantia_mesos, quantitat, preu_unitari,
                 descompte_pct, import_linia)
    Una fila per línia de comanda.

v_garanties_comanda(comanda_id, client, data_comanda, referencia, producte,
                    familia, dies_des_de_la_comanda, mesos_des_de_la_comanda)
    Quin dia es va comprar cada producte i de quina família és.
    ATENCIÓ: el TERMINI de garantia de cada família NO és a la base de dades.
    És al manual de garanties: cal consultar-lo amb cerca_documents.

v_estoc_disponible(referencia, producte, familia, magatzem, unitats, minim,
                   sota_minim)
    Estoc per producte i magatzem.

Estats possibles d'una comanda: 'preparació', 'en trànsit', 'lliurada', 'cancel·lada'.
Famílies: 'eines manuals', 'eines elèctriques', 'consumibles',
          'equips de protecció', 'material elèctric'.
"""


class ConsultaNoPermesa(ValueError):
    """La consulta no ha passat la validació. No s'ha arribat a executar."""


@dataclass
class ResultatSQL:
    consulta: str
    columnes: list[str]
    files: list[dict[str, Any]]

    def markdown(self) -> str:
        if not self.files:
            return "_La consulta no ha retornat cap fila._"
        cap = "| " + " | ".join(self.columnes) + " |"
        sep = "|" + "|".join("---" for _ in self.columnes) + "|"
        cos = [
            "| " + " | ".join(
                "" if f[c] is None else str(f[c]) for c in self.columnes) + " |"
            for f in self.files
        ]
        return "\n".join([cap, sep, *cos])


def valida(consulta: str) -> str:
    """Rebutja tot el que no sigui un SELECT sobre les vistes permeses.

    Retorna la consulta normalitzada i amb LIMIT, o llança ConsultaNoPermesa.
    """
    net = consulta.strip().rstrip(";").strip()
    if not net:
        raise ConsultaNoPermesa("La consulta és buida.")

    try:
        arbres = sqlglot.parse(net, dialect="postgres")
    except Exception as e:
        raise ConsultaNoPermesa(f"No he pogut analitzar la consulta: {e}") from e

    if len(arbres) != 1:
        raise ConsultaNoPermesa(
            "Només s'admet una sentència. Res de consultes encadenades amb ';'.")

    arbre = arbres[0]
    if arbre is None or not isinstance(arbre, (exp.Select, exp.Query)):
        raise ConsultaNoPermesa(
            f"Només s'admeten SELECT. He rebut: {type(arbre).__name__.upper()}.")

    # Res de DML/DDL ni tan sols dins d'una subconsulta o d'un CTE.
    prohibits = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
                 exp.Alter, exp.TruncateTable, exp.Grant, exp.Command)
    for node in arbre.walk():
        if isinstance(node, prohibits):
            raise ConsultaNoPermesa(
                f"Operació no permesa dins de la consulta: "
                f"{type(node).__name__.upper()}.")

    # Els àlies de les CTE són noms interns de la consulta, no taules reals:
    # s'han de permetre, però només si la CTE mateixa llegeix d'una vista permesa.
    ctes = {c.alias_or_name.lower() for c in arbre.find_all(exp.CTE)}

    # Cap taula fora de la llista blanca.
    for taula in arbre.find_all(exp.Table):
        nom = taula.name.lower()
        if nom in ctes:
            continue
        if nom not in VISTES_PERMESES:
            raise ConsultaNoPermesa(
                f"La taula o vista «{nom}» no és consultable. "
                f"Només aquestes: {', '.join(sorted(VISTES_PERMESES))}.")

    # Comentaris i pragmes: fora.
    if re.search(r"(--|/\*|\bpg_sleep\b|\bcopy\b|\bpg_read)", net, re.I):
        raise ConsultaNoPermesa("La consulta conté elements no permesos "
                                "(comentaris, COPY o funcions del sistema).")

    if not arbre.args.get("limit"):
        net = f"{net} LIMIT {LIMIT_FILES}"
    return net


def consulta_sql(consulta: str) -> ResultatSQL:
    """Executa una consulta SELECT sobre les vistes de la base de dades.

    Fes-la servir per a dades concretes: comandes, dates, clients, imports,
    estoc i estat de garantia calculat.

    Args:
        consulta: SQL de PostgreSQL. Només SELECT i només sobre les vistes
            v_comandes_client, v_detall_comanda, v_garanties_comanda i
            v_estoc_disponible.
    """
    segura = valida(consulta)
    with psycopg2.connect(DSN) as conn:
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(segura)
            files = [dict(f) for f in cur.fetchall()]
            columnes = [d[0] for d in cur.description] if cur.description else []
    return ResultatSQL(consulta=segura, columnes=columnes, files=files)
