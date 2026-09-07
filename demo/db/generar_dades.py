#!/usr/bin/env python3
"""Genera demo/db/postgres-init.sql — esquema i dades de Distribucions Vallès SL.

Tot és FICTICI i DETERMINISTA (llavor fixa): dues execucions donen el mateix
fitxer, i el .sql resultant es versiona al repositori.

Invariants que la demo del curs necessita:
  · existeix el client «Ferreteria Puig SL»
  · existeix la comanda 4521, d'aquest client, amb productes de la família
    «eines elèctriques» (2 anys de garantia) i data dins del període de garantia
  · la referència REF-2231 NO existeix enlloc  ← ganxo de la demo d'al·lucinació

Ús:  python demo/db/generar_dades.py [--out demo/db/postgres-init.sql]
"""
from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

LLAVOR = 20260907
AVUI = date(2026, 9, 7)          # dia de la classe 1
REF_PROHIBIDA = 2231             # la referència que no ha d'existir

# --------------------------------------------------------------- vocabulari
NOMS_COMERC = [
    "Ferreteria", "Subministraments", "Indústries", "Tallers", "Magatzems",
    "Comercial", "Instal·lacions", "Serveis Tècnics", "Construccions",
    "Manteniments", "Bricolatge", "Distribucions",
]
COGNOMS = [
    "Puig", "Ferrer", "Soler", "Vilà", "Roca", "Serra", "Camps", "Mas",
    "Bosch", "Riera", "Prat", "Solé", "Farré", "Bonet", "Comas", "Fontanals",
    "Estruch", "Grau", "Ribas", "Casals", "Miralles", "Vendrell", "Pujades",
    "Alsina", "Castellet", "Torrents", "Badia", "Gassó", "艾", "Miró",
    "Sabaté", "Rovira", "Colomer", "Bertran", "Llobet", "Cardona", "Oliva",
    "Xifré", "Nogués", "Feliu", "Batlle", "Trias", "Gispert", "Rigau",
]
COGNOMS = [c for c in COGNOMS if c.isascii() or all(ord(ch) < 0x2000 for ch in c)]
SUFIXOS = ["SL", "SA", "SLU", "SCP", "SL", "SL"]
POBLES = [
    ("Sabadell", "08201"), ("Terrassa", "08221"), ("Granollers", "08400"),
    ("Mataró", "08301"), ("Vic", "08500"), ("Manresa", "08240"),
    ("Igualada", "08700"), ("Vilafranca del Penedès", "08720"),
    ("Barcelona", "08013"), ("Badalona", "08911"), ("Rubí", "08191"),
    ("Sant Cugat del Vallès", "08172"), ("Mollet del Vallès", "08100"),
    ("Cerdanyola del Vallès", "08290"), ("Reus", "43201"), ("Tarragona", "43003"),
    ("Valls", "43800"), ("Lleida", "25001"), ("Girona", "17001"),
    ("Figueres", "17600"), ("Olot", "17800"), ("Vilanova i la Geltrú", "08800"),
    ("Martorell", "08760"), ("Sitges", "08870"), ("Berga", "08600"),
]
CARRERS = [
    "c. Indústria", "av. Catalunya", "c. Major", "pol. ind. Can Roqueta",
    "c. Ferrers", "av. Onze de Setembre", "c. del Comerç", "ctra. de Barcelona",
    "c. Sant Jordi", "pol. ind. Els Dolors", "c. Progrés", "av. Vallès",
    "c. Tallers", "c. de la Fusta", "pol. ind. Riu Clar",
]
SECTORS = ["ferreteria", "indústria", "taller mecànic", "construcció",
           "instal·lacions", "manteniment industrial", "fusteria"]

# Marques FICTÍCIES. No es fa servir cap marca real enlloc del repositori.
MARQUES = ["Valfort", "Terramax", "Norbrec", "Ferralt", "Duracamp", "Vallès Pro"]

# ------------------------------------------------------------- catàleg
# (família, garantia_mesos, [(nom_base, [variants], preu_min, preu_max)])
FAMILIES = {
    "eines manuals": (36, [
        ("Joc de claus fixes", ["6-22 mm", "8-19 mm", "10-32 mm"], 24.0, 89.0),
        ("Alicates universals", ["160 mm", "180 mm", "200 mm"], 9.5, 27.0),
        ("Martell de pena", ["300 g", "500 g", "1000 g"], 11.0, 34.0),
        ("Tornavís pla", ["3x100", "5.5x125", "8x150"], 3.2, 9.8),
        ("Tornavís d'estrella", ["PH1", "PH2", "PH3"], 3.5, 10.5),
        ("Clau anglesa", ["8\"", "10\"", "12\""], 14.0, 42.0),
        ("Serra d'arquet", ["300 mm"], 12.0, 29.0),
        ("Cinta mètrica", ["3 m", "5 m", "8 m"], 6.0, 22.0),
        ("Nivell de bombolla", ["40 cm", "60 cm", "100 cm"], 12.0, 48.0),
        ("Joc de claus Allen", ["1.5-10 mm", "2-12 mm"], 9.0, 31.0),
        ("Cisalla", ["250 mm", "350 mm"], 19.0, 58.0),
        ("Enformador", ["12 mm", "20 mm", "26 mm"], 7.5, 24.0),
    ]),
    "eines elèctriques": (24, [
        ("Trepant percutor", ["650 W", "800 W", "1100 W"], 79.0, 249.0),
        ("Amoladora angular", ["115 mm", "125 mm", "230 mm"], 59.0, 219.0),
        ("Serra circular", ["1200 W", "1600 W"], 129.0, 329.0),
        ("Caladora pendular", ["600 W", "750 W"], 69.0, 189.0),
        ("Cargolador d'impacte", ["18 V", "18 V 2x5Ah"], 149.0, 399.0),
        ("Trepant de columna", ["500 W", "750 W"], 219.0, 649.0),
        ("Polidora orbital", ["300 W", "430 W"], 65.0, 179.0),
        ("Martell demolidor", ["1500 W", "1700 W"], 289.0, 899.0),
        ("Fresadora", ["1200 W", "1800 W"], 159.0, 449.0),
        ("Aspirador de taller", ["20 l", "30 l", "50 l"], 89.0, 289.0),
        ("Soldadora inverter", ["160 A", "200 A"], 179.0, 529.0),
        ("Compressor", ["24 l", "50 l", "100 l"], 129.0, 549.0),
    ]),
    "consumibles": (6, [
        ("Disc de tall metall", ["115x1", "125x1", "230x2"], 1.2, 4.8),
        ("Broca HSS", ["3 mm", "6 mm", "10 mm", "13 mm"], 0.9, 6.5),
        ("Broca widia", ["6 mm", "8 mm", "12 mm"], 1.4, 7.9),
        ("Paper de vidre", ["gra 80", "gra 120", "gra 240"], 0.5, 2.4),
        ("Fulla de serra", ["24 dents", "40 dents", "60 dents"], 8.0, 34.0),
        ("Elèctrode de soldadura", ["2.5 mm", "3.2 mm"], 12.0, 39.0),
        ("Cargol autoroscant", ["4x30 (100 u)", "5x40 (100 u)"], 4.5, 14.0),
        ("Silicona neutra", ["280 ml"], 3.9, 8.9),
        ("Guants de treball", ["talla 9", "talla 10", "talla 11"], 2.5, 9.5),
        ("Cinta aïllant", ["19 mm x 20 m"], 0.8, 2.9),
    ]),
    "equips de protecció": (12, [
        ("Casc de seguretat", ["blanc", "groc", "blau"], 9.0, 34.0),
        ("Ulleres de protecció", ["transparents", "fosques"], 4.5, 19.0),
        ("Botes de seguretat", ["S3 talla 41", "S3 talla 43", "S3 talla 45"], 39.0, 119.0),
        ("Auriculars antisoroll", ["SNR 27", "SNR 33"], 12.0, 49.0),
        ("Arnès anticaigudes", ["2 punts", "4 punts"], 59.0, 189.0),
    ]),
    "material elèctric": (24, [
        ("Cable unipolar", ["1.5 mm² 100 m", "2.5 mm² 100 m"], 39.0, 129.0),
        ("Magnetotèrmic", ["10 A", "16 A", "25 A"], 8.0, 29.0),
        ("Diferencial", ["30 mA 2P", "30 mA 4P"], 39.0, 119.0),
        ("Caixa de derivació", ["100x100", "150x150"], 3.5, 14.0),
        ("Endoll industrial", ["16 A 3P", "32 A 3P"], 9.0, 39.0),
    ]),
}

MAGATZEMS = [
    (1, "Central Sabadell", "pol. ind. Can Roqueta, nau 14", "Sabadell", "08202"),
    (2, "Delegació Tarragona", "pol. ind. Riu Clar, c. Coure 8", "Tarragona", "43006"),
    (3, "Delegació Girona", "c. de la Indústria 22", "Girona", "17005"),
]

ESTATS = ["lliurada", "lliurada", "lliurada", "lliurada", "en trànsit",
          "preparació", "cancel·lada"]


@dataclass
class Client:
    id: int
    nom: str
    cif: str
    sector: str
    adreca: str
    poblacio: str
    cp: str
    email: str
    telefon: str
    alta: date


@dataclass
class Producte:
    id: int
    ref: str
    nom: str
    familia: str
    garantia_mesos: int
    preu: float
    iva: int


@dataclass
class Comanda:
    id: int
    client_id: int
    data: date
    estat: str
    magatzem_id: int
    observacions: str


def cif(rng: random.Random) -> str:
    return f"B{rng.randint(10_000_000, 99_999_999)}"


def genera_clients(rng: random.Random, n: int) -> list[Client]:
    clients: list[Client] = []
    vistos: set[str] = set()

    # El client de la demo, sempre el primer i sempre igual.
    clients.append(Client(
        id=1, nom="Ferreteria Puig SL", cif="B61204488", sector="ferreteria",
        adreca="c. Major 47", poblacio="Granollers", cp="08401",
        email="comandes@ferreteriapuig.cat", telefon="938 70 12 44",
        alta=date(2016, 4, 18),
    ))
    vistos.add("Ferreteria Puig SL")

    while len(clients) < n:
        nom = f"{rng.choice(NOMS_COMERC)} {rng.choice(COGNOMS)} {rng.choice(SUFIXOS)}"
        if nom in vistos:
            continue
        vistos.add(nom)
        poble, cp = rng.choice(POBLES)
        slug = nom.split()[1].lower().replace("·", "")
        i = len(clients) + 1
        clients.append(Client(
            id=i, nom=nom, cif=cif(rng), sector=rng.choice(SECTORS),
            adreca=f"{rng.choice(CARRERS)} {rng.randint(1, 180)}",
            poblacio=poble, cp=cp,
            email=f"info@{slug}{i}.cat",
            telefon=f"9{rng.randint(3,7)}{rng.randint(1,9)} {rng.randint(10,99)} "
                    f"{rng.randint(10,99)} {rng.randint(10,99)}",
            alta=date(2015, 1, 1) + timedelta(days=rng.randint(0, 3900)),
        ))
    return clients


def genera_productes(rng: random.Random, n: int) -> list[Producte]:
    productes: list[Producte] = []
    refs_usades: set[int] = {REF_PROHIBIDA}   # blindatge: mai s'assigna
    ref_num = 1000

    def nova_ref() -> str:
        nonlocal ref_num
        ref_num += 1
        while ref_num in refs_usades:
            ref_num += 1
        refs_usades.add(ref_num)
        return f"REF-{ref_num}"

    # Producte concret de la comanda 4521: eina elèctrica, garantia 24 mesos.
    productes.append(Producte(
        id=1, ref=nova_ref(), nom="Trepant percutor VALFORT PX-1800 (18 V)",
        familia="eines elèctriques", garantia_mesos=24, preu=189.90, iva=21,
    ))

    plantilles = [
        (fam, gar, base, var, pmin, pmax)
        for fam, (gar, items) in FAMILIES.items()
        for base, variants, pmin, pmax in items
        for var in variants
    ]
    rng.shuffle(plantilles)

    i = 2
    while len(productes) < n:
        fam, gar, base, var, pmin, pmax = plantilles[(i - 2) % len(plantilles)]
        preu = round(rng.uniform(pmin, pmax), 2)
        marca = MARQUES[(i + len(base)) % len(MARQUES)]
        productes.append(Producte(
            id=i, ref=nova_ref(), nom=f"{base} {marca} {var}", familia=fam,
            garantia_mesos=gar, preu=preu, iva=21,
        ))
        i += 1
    return productes


def genera_comandes(rng: random.Random, clients, productes, n: int):
    """Retorna (comandes, linies). La 4521 es construeix a mà."""
    per_familia: dict[str, list[Producte]] = {}
    for p in productes:
        per_familia.setdefault(p.familia, []).append(p)

    comandes: list[Comanda] = []
    linies: list[tuple] = []
    linia_id = 0

    def afegeix_linies(com_id: int, prods: list[tuple[Producte, int]]) -> None:
        nonlocal linia_id
        for n_linia, (p, qty) in enumerate(prods, start=1):
            linia_id += 1
            desc = rng.choice([0, 0, 0, 5, 10])
            linies.append((linia_id, com_id, n_linia, p.id, qty,
                           p.preu, desc))

    inici = AVUI - timedelta(days=3 * 365)
    for cid in range(1, n + 1):
        if cid == 4521:
            continue   # es construeix després
        data = inici + timedelta(days=rng.randint(0, 3 * 365 - 1))
        estat = rng.choice(ESTATS)
        if (AVUI - data).days < 5 and estat == "lliurada":
            estat = "en trànsit"
        c = Comanda(
            id=cid,
            client_id=rng.randint(1, len(clients)),
            data=data,
            estat=estat,
            magatzem_id=rng.choice([1, 1, 1, 2, 3]),
            observacions="",
        )
        comandes.append(c)
        tria = []
        for _ in range(rng.randint(1, 5)):
            fam = rng.choice(list(per_familia))
            tria.append((rng.choice(per_familia[fam]), rng.randint(1, 12)))
        afegeix_linies(cid, tria)

    # ------------------------------------------------ LA COMANDA DE LA DEMO
    # 12/03/2025: fa 18 mesos. Eina elèctrica = 24 mesos de garantia
    # → ENCARA EN GARANTIA el 07/09/2026, amb 6 mesos de marge.
    data_4521 = date(2025, 3, 12)
    assert (AVUI - data_4521).days < 24 * 30, "la 4521 ha de quedar en garantia"
    c4521 = Comanda(
        id=4521, client_id=1, data=data_4521, estat="en trànsit",
        magatzem_id=1,
        observacions="Substitució en garantia del trepant percutor. "
                     "Recollida de la unitat avariada a la mateixa entrega.",
    )
    comandes.append(c4521)
    trepant = productes[0]
    discos = next(p for p in per_familia["consumibles"] if "Disc de tall" in p.nom)
    guants = next(p for p in per_familia["consumibles"] if "Guants" in p.nom)
    afegeix_linies(4521, [(trepant, 1), (discos, 25), (guants, 4)])

    comandes.sort(key=lambda c: c.id)
    return comandes, linies


def genera_estoc(rng: random.Random, productes) -> list[tuple]:
    files = []
    for p in productes:
        for m_id, *_ in MAGATZEMS:
            if m_id != 1 and rng.random() < 0.35:
                continue
            base = rng.randint(0, 240) if m_id == 1 else rng.randint(0, 80)
            files.append((p.id, m_id, base, max(5, base // 4)))
    return files


# ----------------------------------------------------------------- SQL
def q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def bloc_esquema() -> str:
    return """\
-- =============================================================================
--  Distribucions Vallès SL — base de dades de demostració
--  CIDET · IA en local · material del curs
--
--  TOTES LES DADES SÓN FICTÍCIES. Generat per demo/db/generar_dades.py.
--  No editis aquest fitxer a mà: torna a executar el generador.
-- =============================================================================

BEGIN;

DROP VIEW IF EXISTS v_comandes_client, v_detall_comanda,
                    v_estoc_disponible, v_garanties_comanda CASCADE;
DROP TABLE IF EXISTS linies_comanda, comandes, estoc, productes,
                     clients, magatzems CASCADE;

-- ------------------------------------------------------------------ taules
CREATE TABLE clients (
    id          INTEGER PRIMARY KEY,
    nom         TEXT        NOT NULL,
    cif         VARCHAR(12) NOT NULL UNIQUE,
    sector      TEXT        NOT NULL,
    adreca      TEXT        NOT NULL,
    poblacio    TEXT        NOT NULL,
    codi_postal VARCHAR(5)  NOT NULL,
    email       TEXT        NOT NULL,
    telefon     TEXT        NOT NULL,
    data_alta   DATE        NOT NULL
);
COMMENT ON TABLE  clients     IS 'Clients de la distribuïdora: ferreteries, indústries i tallers.';
COMMENT ON COLUMN clients.cif IS 'CIF fictici. No correspon a cap empresa real.';

CREATE TABLE magatzems (
    id          INTEGER PRIMARY KEY,
    nom         TEXT NOT NULL,
    adreca      TEXT NOT NULL,
    poblacio    TEXT NOT NULL,
    codi_postal VARCHAR(5) NOT NULL
);
COMMENT ON TABLE magatzems IS 'Els tres magatzems des dels quals se serveixen les comandes.';

CREATE TABLE productes (
    id             INTEGER PRIMARY KEY,
    referencia     VARCHAR(12) NOT NULL UNIQUE,
    nom            TEXT        NOT NULL,
    familia        TEXT        NOT NULL,
    garantia_mesos INTEGER     NOT NULL CHECK (garantia_mesos > 0),
    preu           NUMERIC(10,2) NOT NULL CHECK (preu > 0),
    iva            INTEGER     NOT NULL DEFAULT 21
);
COMMENT ON TABLE  productes                IS 'Catàleg. La garantia depèn de la família (vegeu manual-garanties.pdf).';
COMMENT ON COLUMN productes.familia        IS 'eines manuals | eines elèctriques | consumibles | equips de protecció | material elèctric';
COMMENT ON COLUMN productes.garantia_mesos IS 'Mesos de garantia comercial des de la data de lliurament.';

CREATE TABLE comandes (
    id            INTEGER PRIMARY KEY,
    client_id     INTEGER NOT NULL REFERENCES clients(id),
    data_comanda  DATE    NOT NULL,
    estat         TEXT    NOT NULL
                  CHECK (estat IN ('preparació','en trànsit','lliurada','cancel·lada')),
    magatzem_id   INTEGER NOT NULL REFERENCES magatzems(id),
    observacions  TEXT    NOT NULL DEFAULT ''
);
COMMENT ON TABLE comandes IS 'Comandes dels darrers 3 anys. La data_comanda és l''inici del còmput de garantia.';

CREATE TABLE linies_comanda (
    id            INTEGER PRIMARY KEY,
    comanda_id    INTEGER NOT NULL REFERENCES comandes(id) ON DELETE CASCADE,
    num_linia     INTEGER NOT NULL,
    producte_id   INTEGER NOT NULL REFERENCES productes(id),
    quantitat     INTEGER NOT NULL CHECK (quantitat > 0),
    preu_unitari  NUMERIC(10,2) NOT NULL,
    descompte_pct INTEGER NOT NULL DEFAULT 0 CHECK (descompte_pct BETWEEN 0 AND 100),
    UNIQUE (comanda_id, num_linia)
);

CREATE TABLE estoc (
    producte_id INTEGER NOT NULL REFERENCES productes(id),
    magatzem_id INTEGER NOT NULL REFERENCES magatzems(id),
    unitats     INTEGER NOT NULL CHECK (unitats >= 0),
    minim       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (producte_id, magatzem_id)
);

-- ----------------------------------------------------------------- índexs
CREATE INDEX idx_comandes_client   ON comandes (client_id);
CREATE INDEX idx_comandes_data     ON comandes (data_comanda DESC);
CREATE INDEX idx_comandes_estat    ON comandes (estat);
CREATE INDEX idx_linies_comanda    ON linies_comanda (comanda_id);
CREATE INDEX idx_linies_producte   ON linies_comanda (producte_id);
CREATE INDEX idx_productes_familia ON productes (familia);
CREATE INDEX idx_clients_nom       ON clients (lower(nom));
CREATE INDEX idx_estoc_magatzem    ON estoc (magatzem_id);

"""


def bloc_vistes() -> str:
    return """
-- ------------------------------------------------------------------ vistes
-- Les vistes existeixen per al text-to-SQL de la C6: donen a l'agent una
-- superfície petita, estable i ja unida, en comptes de sis taules crues.

CREATE VIEW v_comandes_client AS
SELECT c.id                AS comanda_id,
       c.data_comanda,
       c.estat,
       cl.id               AS client_id,
       cl.nom              AS client,
       cl.poblacio,
       m.nom               AS magatzem,
       ROUND(SUM(l.quantitat * l.preu_unitari * (1 - l.descompte_pct/100.0)), 2) AS import_net,
       COUNT(l.id)         AS num_linies
FROM comandes c
JOIN clients   cl ON cl.id = c.client_id
JOIN magatzems m  ON m.id  = c.magatzem_id
LEFT JOIN linies_comanda l ON l.comanda_id = c.id
GROUP BY c.id, c.data_comanda, c.estat, cl.id, cl.nom, cl.poblacio, m.nom;
COMMENT ON VIEW v_comandes_client IS
  'Una fila per comanda amb el client, el magatzem i l''import net. Punt d''entrada habitual.';

CREATE VIEW v_detall_comanda AS
SELECT c.id            AS comanda_id,
       c.data_comanda,
       c.estat,
       cl.nom          AS client,
       l.num_linia,
       p.referencia,
       p.nom           AS producte,
       p.familia,
       p.garantia_mesos,
       l.quantitat,
       l.preu_unitari,
       l.descompte_pct,
       ROUND(l.quantitat * l.preu_unitari * (1 - l.descompte_pct/100.0), 2) AS import_linia
FROM comandes c
JOIN clients        cl ON cl.id = c.client_id
JOIN linies_comanda l  ON l.comanda_id = c.id
JOIN productes      p  ON p.id = l.producte_id;
COMMENT ON VIEW v_detall_comanda IS
  'Línia a línia: què duia cada comanda, amb la família i els mesos de garantia del producte.';

CREATE VIEW v_garanties_comanda AS
SELECT c.id                AS comanda_id,
       cl.nom              AS client,
       c.data_comanda,
       p.referencia,
       p.nom               AS producte,
       p.familia,
       p.garantia_mesos,
       (c.data_comanda + (p.garantia_mesos || ' months')::INTERVAL)::DATE AS fi_garantia,
       ((c.data_comanda + (p.garantia_mesos || ' months')::INTERVAL)::DATE >= CURRENT_DATE)
                           AS en_garantia,
       ((c.data_comanda + (p.garantia_mesos || ' months')::INTERVAL)::DATE - CURRENT_DATE)
                           AS dies_restants
FROM comandes c
JOIN clients        cl ON cl.id = c.client_id
JOIN linies_comanda l  ON l.comanda_id = c.id
JOIN productes      p  ON p.id = l.producte_id
WHERE c.estat <> 'cancel·lada';
COMMENT ON VIEW v_garanties_comanda IS
  'Estat de garantia calculat per producte i comanda. La política per família és al manual-garanties.pdf.';

CREATE VIEW v_estoc_disponible AS
SELECT p.referencia,
       p.nom      AS producte,
       p.familia,
       m.nom      AS magatzem,
       e.unitats,
       e.minim,
       (e.unitats <= e.minim) AS sota_minim
FROM estoc e
JOIN productes  p ON p.id = e.producte_id
JOIN magatzems  m ON m.id = e.magatzem_id;
COMMENT ON VIEW v_estoc_disponible IS
  'Estoc per producte i magatzem, amb marca de sota mínim.';

-- --------------------------------------------------- usuari de només lectura
-- L'agent de la C6 es connecta AMB AQUEST ROL i només veu les vistes.
-- Encara que el text-to-SQL generi un DELETE, la base de dades el rebutja.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'assistent_ro') THEN
        CREATE ROLE assistent_ro LOGIN PASSWORD 'canvia_aquesta_contrasenya';
    END IF;
END $$;

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM assistent_ro;
GRANT  USAGE ON SCHEMA public TO assistent_ro;
GRANT  SELECT ON v_comandes_client, v_detall_comanda,
                 v_garanties_comanda, v_estoc_disponible TO assistent_ro;
ALTER  DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM assistent_ro;

COMMIT;

-- ---------------------------------------------------------- comprovacions
-- Invariants que la demo del curs necessita. Si algun falla, l'error surt
-- en carregar el fitxer i no a mitja classe.
DO $$
DECLARE n INTEGER; d DATE; g BOOLEAN;
BEGIN
    SELECT COUNT(*) INTO n FROM productes WHERE referencia = 'REF-2231';
    IF n > 0 THEN RAISE EXCEPTION 'REF-2231 no pot existir: és el ganxo de la demo d''al·lucinació'; END IF;

    SELECT COUNT(*) INTO n FROM clients WHERE nom = 'Ferreteria Puig SL';
    IF n <> 1 THEN RAISE EXCEPTION 'falta el client Ferreteria Puig SL'; END IF;

    SELECT c.data_comanda INTO d FROM comandes c WHERE c.id = 4521;
    IF d IS NULL THEN RAISE EXCEPTION 'falta la comanda 4521'; END IF;

    SELECT bool_or(en_garantia) INTO g FROM v_garanties_comanda
     WHERE comanda_id = 4521 AND familia = 'eines elèctriques';
    IF NOT COALESCE(g, FALSE) THEN
        RAISE EXCEPTION 'la comanda 4521 ha de tenir una eina elèctrica EN garantia';
    END IF;

    RAISE NOTICE 'Distribucions Vallès SL: dades carregades i invariants OK.';
END $$;
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).parent / "postgres-init.sql")
    ap.add_argument("--clients", type=int, default=500)
    ap.add_argument("--productes", type=int, default=300)
    ap.add_argument("--comandes", type=int, default=5000)
    args = ap.parse_args()

    rng = random.Random(LLAVOR)
    clients = genera_clients(rng, args.clients)
    productes = genera_productes(rng, args.productes)
    comandes, linies = genera_comandes(rng, clients, productes, args.comandes)
    estoc = genera_estoc(rng, productes)

    # blindatge final
    assert all(p.ref != f"REF-{REF_PROHIBIDA}" for p in productes)

    parts: list[str] = [bloc_esquema()]

    parts.append("-- ------------------------------------------------------------------ dades\n")
    parts.append("INSERT INTO magatzems (id, nom, adreca, poblacio, codi_postal) VALUES\n")
    parts.append(",\n".join(
        f"  ({i}, {q(nom)}, {q(ad)}, {q(pob)}, {q(cp)})"
        for i, nom, ad, pob, cp in MAGATZEMS) + ";\n\n")

    parts.append("INSERT INTO clients (id, nom, cif, sector, adreca, poblacio, "
                 "codi_postal, email, telefon, data_alta) VALUES\n")
    parts.append(",\n".join(
        f"  ({c.id}, {q(c.nom)}, {q(c.cif)}, {q(c.sector)}, {q(c.adreca)}, "
        f"{q(c.poblacio)}, {q(c.cp)}, {q(c.email)}, {q(c.telefon)}, '{c.alta}')"
        for c in clients) + ";\n\n")

    parts.append("INSERT INTO productes (id, referencia, nom, familia, "
                 "garantia_mesos, preu, iva) VALUES\n")
    parts.append(",\n".join(
        f"  ({p.id}, {q(p.ref)}, {q(p.nom)}, {q(p.familia)}, {p.garantia_mesos}, "
        f"{p.preu:.2f}, {p.iva})" for p in productes) + ";\n\n")

    parts.append("INSERT INTO comandes (id, client_id, data_comanda, estat, "
                 "magatzem_id, observacions) VALUES\n")
    parts.append(",\n".join(
        f"  ({c.id}, {c.client_id}, '{c.data}', {q(c.estat)}, {c.magatzem_id}, "
        f"{q(c.observacions)})" for c in comandes) + ";\n\n")

    parts.append("INSERT INTO linies_comanda (id, comanda_id, num_linia, "
                 "producte_id, quantitat, preu_unitari, descompte_pct) VALUES\n")
    parts.append(",\n".join(
        f"  ({i}, {cid}, {nl}, {pid}, {qt}, {pu:.2f}, {desc})"
        for i, cid, nl, pid, qt, pu, desc in linies) + ";\n\n")

    parts.append("INSERT INTO estoc (producte_id, magatzem_id, unitats, minim) VALUES\n")
    parts.append(",\n".join(
        f"  ({pid}, {mid}, {u}, {mn})" for pid, mid, u, mn in estoc) + ";\n")

    parts.append(bloc_vistes())

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(parts), encoding="utf-8")

    trepant = productes[0]
    print(f"escrit: {args.out}  ({args.out.stat().st_size/1024/1024:.1f} MB)")
    print(f"  clients:   {len(clients):>6}   (id 1 = {clients[0].nom})")
    print(f"  productes: {len(productes):>6}   (id 1 = {trepant.ref} · {trepant.nom})")
    print(f"  comandes:  {len(comandes):>6}   (4521 = {[c.data for c in comandes if c.id==4521][0]})")
    print(f"  línies:    {len(linies):>6}")
    print(f"  estoc:     {len(estoc):>6}")
    print(f"  REF-{REF_PROHIBIDA}: absent ✔")


if __name__ == "__main__":
    main()
