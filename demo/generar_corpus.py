#!/usr/bin/env python3
"""Genera el corpus documental de Distribucions Vallès SL (fictici).

16 documents en català —PDF i Word— que fan de font documental del RAG.
Els preus, referències i famílies surten del MATEIX generador que la base de
dades (demo/db/generar_dades.py), amb la mateixa llavor: el corpus i el SQL
sempre parlen dels mateixos productes.

Regles del corpus:
  · Tot en català, res de lorem ipsum.
  · La referència REF-2231 NO apareix enlloc  ← ganxo de la demo d'al·lucinació.
  · manual-garanties.pdf conté tot el que cal per resoldre el cas de la 4521.
  · Un dels PDF va RASTERITZAT (sense capa de text) perquè a la C4 es vegi
    que sense OCR no se'n treu res.

Ús:  python demo/generar_corpus.py [--out demo/corpus]
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
    TableStyle,
)

sys.path.insert(0, str(Path(__file__).parent / "db"))
from generar_dades import (  # noqa: E402
    LLAVOR, MAGATZEMS, REF_PROHIBIDA, genera_productes,
)
import random  # noqa: E402

# --------------------------------------------------------------- identitat
EMPRESA = "Distribucions Vallès SL"
CIF = "B62145309"
ADRECA = "pol. ind. Can Roqueta, nau 14 · 08202 Sabadell"
WEB = "www.distribucionsvalles.cat"
TEL = "937 45 20 10"
EMAIL_SAT = "sat@distribucionsvalles.cat"
ACCENT = colors.HexColor("#0F6E6A")
GRIS = colors.HexColor("#5C6B6A")
PAPER = colors.HexColor("#FFFFFF")
FILA_ALT = colors.HexColor("#F2F7F6")
AVUI = date(2026, 9, 7)
PEU = "CIDET · IA en local · corpus de demostració (dades fictícies)"

# Política de garanties: HA DE COINCIDIR amb productes.garantia_mesos del SQL.
GARANTIES = [
    ("Eines manuals", 36, "Claus, alicates, martells, tornavisos, cintes mètriques, nivells."),
    ("Eines elèctriques", 24, "Trepants, amoladores, serres, cargoladors, compressors, soldadores."),
    ("Material elèctric", 24, "Cable, magnetotèrmics, diferencials, caixes, endolls industrials."),
    ("Equips de protecció", 12, "Cascs, ulleres, botes, auriculars, arnesos."),
    ("Consumibles", 6, "Discos, broques, paper de vidre, elèctrodes, cargoleria, silicones."),
]


# ------------------------------------------------------------------ estils
def estils():
    ss = getSampleStyleSheet()
    base = dict(fontName="Helvetica", leading=14, textColor=colors.HexColor("#1A1A1A"))
    return {
        "titol": ParagraphStyle("titol", parent=ss["Title"], fontSize=20,
                                textColor=ACCENT, spaceAfter=4, alignment=0,
                                fontName="Helvetica-Bold"),
        "subtitol": ParagraphStyle("subtitol", fontSize=10, textColor=GRIS,
                                   spaceAfter=14, fontName="Helvetica-Oblique"),
        "h1": ParagraphStyle("h1", fontSize=13, textColor=ACCENT, spaceBefore=14,
                             spaceAfter=6, fontName="Helvetica-Bold", **{k: v for k, v in base.items() if k not in ("fontName", "textColor")}),
        "h2": ParagraphStyle("h2", fontSize=11, spaceBefore=10, spaceAfter=4,
                             fontName="Helvetica-Bold",
                             textColor=colors.HexColor("#1A1A1A"), leading=14),
        "p": ParagraphStyle("p", fontSize=9.5, leading=14, spaceAfter=6,
                            alignment=TA_JUSTIFY, fontName="Helvetica",
                            textColor=colors.HexColor("#1A1A1A")),
        "li": ParagraphStyle("li", fontSize=9.5, leading=14, spaceAfter=3,
                             leftIndent=12, bulletIndent=4, fontName="Helvetica",
                             textColor=colors.HexColor("#1A1A1A")),
        "nota": ParagraphStyle("nota", fontSize=8.5, leading=12, textColor=GRIS,
                               fontName="Helvetica-Oblique", spaceBefore=6),
        "cel": ParagraphStyle("cel", fontSize=8.5, leading=11, fontName="Helvetica"),
        "celb": ParagraphStyle("celb", fontSize=8.5, leading=11,
                               fontName="Helvetica-Bold", textColor=PAPER),
    }


S = estils()


def _peu(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRIS)
    canvas.drawString(20 * mm, 12 * mm, f"{EMPRESA} · {PEU}")
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"pàg. {doc.page}")
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(0.6)
    canvas.line(20 * mm, 15 * mm, A4[0] - 20 * mm, 15 * mm)
    canvas.restoreState()


def capcalera(titol: str, codi: str, versio: str = "3.2") -> list:
    return [
        Paragraph(titol, S["titol"]),
        Paragraph(
            f"{EMPRESA} · CIF {CIF} · document {codi} · versió {versio} · "
            f"en vigor des de l'1 de gener de 2026",
            S["subtitol"]),
    ]


def taula(dades: list[list[str]], amples: list[float], aliniar_dreta=()) -> Table:
    files = [[Paragraph(c, S["celb"]) for c in dades[0]]]
    files += [[Paragraph(str(c), S["cel"]) for c in fila] for fila in dades[1:]]
    t = Table(files, colWidths=amples, repeatRows=1)
    estil = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), PAPER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D6D5")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PAPER, FILA_ALT]),
    ]
    for c in aliniar_dreta:
        estil.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(estil))
    return t


def escriu_pdf(cami: Path, flow: list, titol: str) -> None:
    doc = SimpleDocTemplate(
        str(cami), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=22 * mm,
        title=titol, author=EMPRESA, subject="Document intern (fictici)",
    )
    doc.build(flow, onFirstPage=_peu, onLaterPages=_peu)


def P(text: str) -> Paragraph:
    return Paragraph(text, S["p"])


def LI(text: str) -> Paragraph:
    return Paragraph(text, S["li"], bulletText="•")


# =============================================================================
#  1. manual-garanties.pdf   ← EL DOCUMENT CLAU DE LA DEMO
# =============================================================================
def manual_garanties(out: Path) -> None:
    f = capcalera("Manual de garanties", "MG-2026", "4.1")
    f += [
        P(f"Aquest manual recull la política de garantia comercial que "
          f"{EMPRESA} aplica als productes que distribueix. Substitueix "
          f"qualsevol versió anterior i és d'aplicació a totes les comandes "
          f"lliurades a partir de l'1 de gener de 2026."),

        Paragraph("1. Àmbit d'aplicació", S["h1"]),
        P("La garantia comercial cobreix els defectes de fabricació i els vicis "
          "ocults del producte. És addicional i independent de la garantia legal "
          "de conformitat que la normativa vigent reconeix al client, i mai la "
          "substitueix ni la limita."),
        P("Els destinataris són els clients professionals amb compte obert a "
          f"{EMPRESA}. Per a vendes a consumidor final s'aplica, a més, la "
          "normativa de consum que correspongui."),

        Paragraph("2. Terminis per família de producte", S["h1"]),
        P("El termini de garantia es compta <b>des de la data de la comanda</b> "
          "que consta a l'albarà de lliurament. Quan una comanda inclou productes "
          "de famílies diferents, <b>cada línia té el seu propi termini</b>: no "
          "s'aplica el termini més llarg al conjunt."),
        Spacer(1, 4),
        taula(
            [["Família de producte", "Garantia", "Inclou"]]
            + [[fam, f"{m} mesos ({m//12} anys)" if m >= 12 else f"{m} mesos", desc]
               for fam, m, desc in GARANTIES],
            [38 * mm, 30 * mm, 102 * mm]),
        Paragraph(
            "Exemple: una comanda amb un trepant percutor i una caixa de discos de "
            "tall té 24 mesos de garantia per al trepant i 6 mesos per als discos, "
            "comptats tots dos des de la data de la comanda.", S["nota"]),

        Paragraph("3. Què cobreix la garantia", S["h1"]),
        LI("Defectes de fabricació del producte i dels seus components."),
        LI("Avaries per fallada de materials en condicions d'ús normal."),
        LI("Mà d'obra de la reparació al servei tècnic propi o autoritzat."),
        LI("Ports d'anada i tornada quan la reparació es fa al servei tècnic propi."),
        LI("Substitució per una unitat equivalent si la reparació no és viable "
           "en un termini raonable o si el cost supera el 70 % del preu de venda."),

        Paragraph("4. Què NO cobreix", S["h1"]),
        LI("El <b>desgast normal</b> per l'ús: escombretes, corretges, coixinets, "
           "juntes i bateries amb més de 300 cicles de càrrega."),
        LI("Els <b>consumibles consumits</b>: discos gastats, broques desafilades, "
           "paper de vidre usat, elèctrodes fosos."),
        LI("Els danys per <b>ús inadequat</b>: sobrecàrrega continuada, ús de la "
           "màquina fora de les especificacions del fabricant, o ús d'accessoris "
           "no compatibles."),
        LI("Els danys per <b>manca de manteniment</b> quan el manual del producte "
           "en prescriu un de periòdic."),
        LI("Els cops, les caigudes i els danys per transport un cop lliurada la "
           "mercaderia i signat l'albarà sense reserves."),
        LI("Les <b>reparacions fetes per tercers</b> no autoritzats. Obrir la "
           "carcassa d'una eina elèctrica anul·la la garantia."),
        LI("Els danys per <b>xarxa elèctrica defectuosa</b>: sobretensions, "
           "manca de presa de terra o generadors sense regulació."),
        LI("La corrosió per emmagatzematge en ambients humits o salins."),

        Paragraph("5. Procediment de reclamació", S["h1"]),
        P("El procediment és el mateix per a totes les famílies. El termini de "
          "resposta compta des que el servei tècnic rep la unitat, no des de la "
          "comunicació inicial."),
        Spacer(1, 4),
        taula([
            ["Pas", "Qui", "Què cal fer", "Termini"],
            ["1", "Client", "Comunicar la incidència indicant el <b>número de comanda</b>, "
                            "la referència del producte i una descripció de l'avaria. "
                            f"Per correu a {EMAIL_SAT} o des de l'àrea de client.", "—"],
            ["2", "SAT", "Obrir expedient i assignar un número de RMA, que s'ha "
                         "d'indicar a tota la documentació posterior.", "24 h laborables"],
            ["3", "Client", "Enviar la unitat al magatzem central amb el número de RMA "
                            "visible a l'exterior de l'embalatge, amb tots els accessoris.",
             "10 dies naturals des del RMA"],
            ["4", "SAT", "Peritatge tècnic i dictamen: en garantia, fora de garantia "
                         "o pressupost de reparació.", "5 dies laborables"],
            ["5", "SAT", "Reparació, substitució o abonament, segons el dictamen.",
             "15 dies laborables"],
        ], [10 * mm, 20 * mm, 106 * mm, 34 * mm]),

        Paragraph("6. Terminis i condicions particulars", S["h1"]),
        LI("La reclamació s'ha de comunicar <b>dins del període de garantia</b>. "
           "Una comunicació posterior a la data de finalització no s'accepta, "
           "encara que l'avaria s'hagi produït abans."),
        LI("Els <b>defectes aparents</b> i les diferències de quantitat s'han de "
           "fer constar a l'albarà en el moment del lliurament, o comunicar-se "
           "en un termini màxim de 48 hores."),
        LI("La reparació o la substitució <b>no reinicien</b> el termini de "
           "garantia original: la unitat substituïda conserva la data de la "
           "comanda inicial com a inici del còmput."),
        LI("Durant la reparació, i si el client ho demana, es pot facilitar una "
           "<b>unitat de cortesia</b> del mateix segment mentre duri l'expedient, "
           "subjecta a disponibilitat d'estoc."),
        LI("Si el peritatge conclou que l'avaria <b>no està coberta</b>, "
           "s'emet un pressupost de reparació. La no-acceptació comporta un "
           "càrrec de 25 € en concepte de peritatge i el retorn de la unitat."),

        Paragraph("7. Documentació necessària", S["h1"]),
        P("Per tramitar qualsevol expedient de garantia cal, com a mínim:"),
        LI("Número de comanda o còpia de l'albarà de lliurament."),
        LI("Referència del producte (format <font face='Courier'>REF-XXXX</font>)."),
        LI("Descripció de l'avaria i, si és possible, fotografies."),
        LI("Número de sèrie de la màquina, si en té."),
        Paragraph(
            "Sense el número de comanda no es pot determinar la data d'inici del "
            "còmput i l'expedient queda aturat.", S["nota"]),

        Paragraph("8. Contacte del servei tècnic", S["h1"]),
        P(f"Servei d'Assistència Tècnica · {EMAIL_SAT} · {TEL} (ext. 2)<br/>"
          f"{ADRECA}<br/>Horari: de dilluns a divendres, de 8.00 a 17.00 h."),
    ]
    escriu_pdf(out / "manual-garanties.pdf", f, "Manual de garanties")


# =============================================================================
#  2. procediment-devolucions.pdf
# =============================================================================
def procediment_devolucions(out: Path) -> None:
    f = capcalera("Procediment de devolucions", "PD-2026", "2.4")
    f += [
        P("Aquest procediment regula les devolucions de mercaderia que <b>no</b> "
          "responen a un defecte del producte. Les devolucions per avaria o "
          "defecte de fabricació es tramiten pel <i>Manual de garanties</i> "
          "(document MG-2026) i no per aquest procediment."),

        Paragraph("1. Devolucions admeses", S["h1"]),
        taula([
            ["Motiu", "Termini", "Càrrec", "Condicions"],
            ["Error en la comanda del client", "14 dies naturals", "15 % de despeses",
             "Embalatge original intacte, producte sense usar"],
            ["Error de preparació nostre", "30 dies naturals", "Cap",
             "S'accepta sense condicions; els ports van a càrrec nostre"],
            ["Producte no conforme a la comanda", "30 dies naturals", "Cap",
             "Cal fotografia de l'etiqueta rebuda"],
            ["Excés d'estoc del client", "60 dies naturals", "25 % de despeses",
             "Només productes de catàleg vigent i amb rotació"],
            ["Comanda especial o sota comanda", "No s'admet", "—",
             "Els productes que no són de catàleg no es poden retornar"],
        ], [40 * mm, 26 * mm, 26 * mm, 78 * mm]),

        Paragraph("2. Estat de la mercaderia", S["h1"]),
        LI("Embalatge original, complet i en condicions de tornar-se a vendre."),
        LI("Sense etiquetes, adhesius ni retolacions afegides pel client."),
        LI("Amb tots els accessoris, manuals i elements de fixació."),
        LI("Els productes precintats han de conservar el precinte intacte."),

        Paragraph("3. Tramitació", S["h1"]),
        P("Tota devolució necessita una <b>autorització prèvia</b>. El material "
          "que arribi al magatzem sense número d'autorització es retorna al "
          "remitent a ports deguts."),
        LI("Sol·licitud per correu indicant número de comanda, referències i motiu."),
        LI("Emissió del número d'autorització de devolució en 24 hores laborables."),
        LI("Recollida concertada amb el nostre transportista, o entrega directa "
           "al magatzem central."),
        LI("Verificació a recepció i emissió de l'abonament en un màxim de "
           "10 dies laborables."),

        Paragraph("4. Productes exclosos", S["h1"]),
        LI("Productes a mida o fabricats sota comanda."),
        LI("Consumibles amb l'envàs obert."),
        LI("Productes químics i adhesius amb data de caducitat superada."),
        LI("Equips de protecció individual amb el precinte higiènic trencat."),

        Paragraph("5. Abonaments", S["h1"]),
        P("L'abonament s'emet sempre al mateix preu de la factura original, amb "
          "els descomptes que s'hi van aplicar. No es fan devolucions en efectiu: "
          "l'import es compensa amb el següent venciment o, si el client ho demana "
          "per escrit, es transfereix al compte que consti a la fitxa."),
    ]
    escriu_pdf(out / "procediment-devolucions.pdf", f, "Procediment de devolucions")


# =============================================================================
#  3. tarifes-2026.pdf   (amb taules llargues: cas d'estudi de la C4)
# =============================================================================
def tarifes(out: Path, productes) -> None:
    f = capcalera("Tarifa de preus 2026", "TP-2026", "1.0")
    f += [
        P("Preus de venda al públic recomanats, en euros, sense IVA. Els preus "
          "de compte s'obtenen aplicant el descompte pactat a cada client segons "
          "el seu escalat comercial. Vigència: de l'1 de gener al 31 de desembre "
          "de 2026, llevat de revisió per variació del cost de matèria primera."),
        Paragraph("Escalats comercials", S["h1"]),
        taula([
            ["Escalat", "Facturació anual", "Descompte eines", "Descompte consumibles"],
            ["A", "> 60.000 €", "22 %", "30 %"],
            ["B", "25.000 – 60.000 €", "17 %", "24 %"],
            ["C", "8.000 – 25.000 €", "12 %", "18 %"],
            ["D", "< 8.000 €", "7 %", "10 %"],
        ], [22 * mm, 45 * mm, 47 * mm, 56 * mm], aliniar_dreta=(2, 3)),
    ]

    per_familia: dict[str, list] = {}
    for p in productes:
        per_familia.setdefault(p.familia, []).append(p)

    for fam in ["eines elèctriques", "eines manuals", "consumibles",
                "material elèctric", "equips de protecció"]:
        items = sorted(per_familia.get(fam, []), key=lambda p: p.ref)[:26]
        if not items:
            continue
        garantia = dict((g[0].lower(), g[1]) for g in GARANTIES).get(fam, 24)
        f += [
            Paragraph(f"{fam.capitalize()} · garantia {garantia} mesos", S["h1"]),
            taula(
                [["Referència", "Descripció", "PVP (€)", "IVA", "Garantia"]]
                + [[p.ref, p.nom, f"{p.preu:.2f}", f"{p.iva} %",
                    f"{p.garantia_mesos} mesos"] for p in items],
                [26 * mm, 78 * mm, 22 * mm, 16 * mm, 28 * mm],
                aliniar_dreta=(2,)),
        ]

    f += [
        Paragraph("Condicions generals de la tarifa", S["h1"]),
        LI("Preus sense IVA. S'hi aplica el 21 % vigent."),
        LI("Ports pagats per comandes superiors a 250 € nets; per sota, "
           "12,50 € de despeses d'enviament."),
        LI("Els preus poden variar sense avís previ per canvis de cost de "
           "matèria primera; la comanda confirmada manté el preu acceptat."),
        LI("Els productes marcats com a sota comanda tenen un termini de "
           "lliurament de 10 a 15 dies laborables."),
    ]
    escriu_pdf(out / "tarifes-2026.pdf", f, "Tarifa de preus 2026")


# =============================================================================
#  4. fitxa-producte-*.pdf  ×5
# =============================================================================
FITXES = [
    ("Trepant percutor VALFORT PX-1800", "eines elèctriques", [
        ("Potència", "1.100 W"), ("Velocitat en buit", "0–1.100 / 0–3.000 rpm"),
        ("Percussió", "0–48.000 cops/min"), ("Portabroques", "13 mm automàtic"),
        ("Capacitat en formigó", "16 mm"), ("Capacitat en acer", "13 mm"),
        ("Capacitat en fusta", "40 mm"), ("Pes", "2,4 kg"),
        ("Nivell sonor", "94 dB(A)"), ("Vibració", "13,5 m/s²"),
        ("Cable", "4 m"), ("Garantia", "24 mesos"),
    ], [
        "Trepant percutor de doble velocitat per a treballs de perforació en "
        "formigó, obra, acer i fusta. L'embragatge mecànic protegeix el motor i "
        "l'operari en cas de bloqueig de la broca.",
        "Manteniment: comprovar l'estat de les escombretes cada 200 hores de "
        "funcionament. Les escombretes són una peça de desgast i no entren en "
        "garantia.",
    ]),
    ("Amoladora angular TERRAMAX AG-125", "eines elèctriques", [
        ("Potència", "1.000 W"), ("Diàmetre de disc", "125 mm"),
        ("Velocitat en buit", "11.000 rpm"), ("Rosca de l'eix", "M14"),
        ("Arrencada suau", "Sí"), ("Fre d'inèrcia", "Sí, < 2 s"),
        ("Pes", "2,1 kg"), ("Protector", "Sense eines, gir de 360°"),
        ("Garantia", "24 mesos"),
    ], [
        "Amoladora angular de 125 mm amb arrencada suau i fre d'inèrcia. Pensada "
        "per a tall i desbast de metall en taller i obra.",
        "Fer servir sempre el protector i ulleres de seguretat. L'ús de discos "
        "amb velocitat màxima inferior a 11.000 rpm és perillós i anul·la la "
        "garantia.",
    ]),
    ("Soldadora inverter NORBREC IW-200", "eines elèctriques", [
        ("Corrent màxim", "200 A"), ("Tensió d'alimentació", "230 V monofàsica"),
        ("Cicle de treball", "60 % a 160 A"), ("Elèctrodes", "1,6 – 4,0 mm"),
        ("Funció Hot Start", "Sí"), ("Funció Anti-Stick", "Sí"),
        ("Pes", "5,8 kg"), ("Grau de protecció", "IP21S"),
        ("Garantia", "24 mesos"),
    ], [
        "Equip de soldadura per elèctrode revestit amb tecnologia inverter. "
        "Admet generador amb una potència mínima de 7 kVA amb regulació estable.",
        "L'alimentació des d'un generador sense regulació de tensió pot destruir "
        "l'electrònica; aquest dany no està cobert per la garantia.",
    ]),
    ("Joc de claus fixes FERRALT 6-22 mm", "eines manuals", [
        ("Peces", "12"), ("Mides", "6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 19, 22 mm"),
        ("Material", "Acer al crom-vanadi"), ("Acabat", "Cromat mat"),
        ("Norma", "DIN 3113 forma A"), ("Estoig", "Roll-up de lona"),
        ("Pes del joc", "1,9 kg"), ("Garantia", "36 mesos"),
    ], [
        "Joc de claus fixes de dues boques en acer al crom-vanadi forjat. "
        "Toleràncies segons DIN 3113.",
        "Les eines manuals tenen 36 mesos de garantia contra defectes de "
        "fabricació. El desgast de les boques per ús amb allargador o cop de "
        "martell no hi entra.",
    ]),
    ("Botes de seguretat DURACAMP S3", "equips de protecció", [
        ("Categoria", "S3 SRC"), ("Puntera", "Composite, 200 J"),
        ("Plantilla", "Antiperforació tèxtil"), ("Sola", "Poliuretà bidensitat"),
        ("Resistència", "Antiestàtica, absorció d'energia al taló"),
        ("Talles", "de la 38 a la 47"), ("Norma", "EN ISO 20345:2022"),
        ("Garantia", "12 mesos"),
    ], [
        "Bota de seguretat de categoria S3 amb puntera de composite i plantilla "
        "antiperforació tèxtil, sense metall: no activa els detectors ni fa pont "
        "tèrmic.",
        "La garantia de 12 mesos cobreix defectes de fabricació i descosits. "
        "El desgast de la sola per ús no hi entra.",
    ]),
]


def fitxes_producte(out: Path) -> None:
    for i, (nom, familia, specs, textos) in enumerate(FITXES, start=1):
        slug = (nom.lower().replace(" ", "-").replace("·", "")
                .replace("à", "a").replace("è", "e").replace("é", "e")
                .replace("í", "i").replace("ò", "o").replace("ó", "o")
                .replace("ú", "u").replace("ç", "c"))
        f = capcalera(nom, f"FT-{2026}-{i:02d}", "1.0")
        f += [Paragraph(f"Família: {familia}", S["h2"])]
        for t in textos:
            f.append(P(t))
        f += [
            Paragraph("Especificacions tècniques", S["h1"]),
            taula([["Característica", "Valor"]] + [[k, v] for k, v in specs],
                  [65 * mm, 105 * mm]),
            Paragraph("Contingut de la caixa", S["h1"]),
            LI("Unitat principal"),
            LI("Manual d'instruccions i declaració de conformitat CE"),
            LI("Certificat de garantia"),
            Paragraph(
                f"Les condicions de garantia d'aquest producte són les del "
                f"<i>Manual de garanties</i> (MG-2026) per a la família "
                f"«{familia}».", S["nota"]),
        ]
        escriu_pdf(out / f"fitxa-producte-{slug}.pdf", f, nom)


# =============================================================================
#  5. politica-enviaments.pdf
# =============================================================================
def politica_enviaments(out: Path) -> None:
    f = capcalera("Política d'enviaments i lliuraments", "PE-2026", "3.0")
    f += [
        P("Aquest document descriu els terminis, les zones i les condicions de "
          "lliurament de les comandes servides des dels nostres tres magatzems."),
        Paragraph("1. Magatzems", S["h1"]),
        taula([["Magatzem", "Adreça", "Població", "Zona que serveix"]]
              + [[nom, ad, pob, z] for (_, nom, ad, pob, _), z in zip(
                  MAGATZEMS,
                  ["Vallès, Barcelonès, Bages, Osona, Anoia",
                   "Camp de Tarragona, Terres de l'Ebre, Penedès",
                   "Gironès, Empordà, Garrotxa, Selva"])],
              [40 * mm, 55 * mm, 30 * mm, 45 * mm]),

        Paragraph("2. Terminis de lliurament", S["h1"]),
        taula([
            ["Zona", "Comanda abans de", "Lliurament", "Cost"],
            ["Zona 1 — mateixa comarca", "17.00 h", "Dia laborable següent", "Gratuït des de 150 €"],
            ["Zona 2 — resta de Catalunya", "16.00 h", "24–48 h laborables", "Gratuït des de 250 €"],
            ["Zona 3 — resta de la península", "15.00 h", "48–72 h laborables", "Gratuït des de 400 €"],
            ["Illes Balears", "15.00 h", "3–5 dies laborables", "Consultar"],
        ], [45 * mm, 32 * mm, 45 * mm, 48 * mm]),

        Paragraph("3. Estats d'un enviament", S["h1"]),
        P("Cada comanda passa pels estats següents, consultables amb el número "
          "de comanda a l'àrea de client o a través del nostre servei de "
          "seguiment:"),
        taula([
            ["Estat", "Què vol dir"],
            ["preparació", "La comanda és al magatzem, s'estan agrupant les línies."],
            ["en trànsit", "Ha sortit del magatzem i és en mans del transportista."],
            ["lliurada", "Entregada i albarà signat pel client."],
            ["cancel·lada", "Anul·lada abans de sortir del magatzem."],
        ], [35 * mm, 135 * mm]),

        Paragraph("4. Incidències de transport", S["h1"]),
        LI("Els <b>danys visibles</b> a l'embalatge s'han de fer constar a "
           "l'albarà del transportista <b>en el moment del lliurament</b>. Signar "
           "sense reserves fa molt difícil reclamar després."),
        LI("Els <b>danys ocults</b> s'han de comunicar en un màxim de 48 hores "
           "des del lliurament, amb fotografies de l'embalatge i del producte."),
        LI("Els <b>retards</b> imputables al transportista no donen dret a la "
           "cancel·lació de la comanda si no superen els 5 dies laborables "
           "sobre el termini previst."),
        LI("Les <b>absències</b> al lliurament generen un segon intent sense "
           "càrrec. A partir del tercer intent es factura la reexpedició."),

        Paragraph("5. Lliuraments parcials", S["h1"]),
        P("Si una comanda té línies sense estoc, per defecte se serveix el que "
          "hi ha i la resta queda en reserva, sense càrrec addicional de ports "
          "per al segon enviament. El client pot demanar el contrari: esperar a "
          "tenir la comanda completa."),
    ]
    escriu_pdf(out / "politica-enviaments.pdf", f, "Política d'enviaments")


# =============================================================================
#  6. Documents de farciment
# =============================================================================
def farciment(out: Path) -> None:
    # 6.1 Catàleg de serveis
    f = capcalera("Catàleg de serveis tècnics", "CS-2026", "1.2")
    f += [
        P("A banda de la distribució de producte, oferim serveis tècnics "
          "associats que ajuden el client a mantenir el seu parc d'eines."),
        Paragraph("Serveis disponibles", S["h1"]),
        taula([
            ["Servei", "Descripció", "Preu"],
            ["Afilat de broques i fresses", "Recollida setmanal, retorn en 5 dies laborables", "Des de 2,50 €/unitat"],
            ["Revisió anual d'eines elèctriques", "Comprovació elèctrica, canvi d'escombretes i greixatge", "38 €/màquina"],
            ["Calibratge d'instruments de mesura", "Amb certificat traçable", "Des de 45 €"],
            ["Reparació fora de garantia", "Peritatge previ i pressupost tancat", "25 € de peritatge"],
            ["Formació d'ús segur", "Sessió de 2 h a les instal·lacions del client", "180 €/sessió"],
            ["Gestió de residus d'eines", "Retirada i certificat de destrucció", "Gratuït per a escalats A i B"],
        ], [48 * mm, 90 * mm, 32 * mm]),
        Paragraph("Condicions", S["h1"]),
        LI("Els serveis es contracten per l'àrea de client o a través del comercial assignat."),
        LI("Els preus són sense IVA i no admeten els descomptes d'escalat comercial."),
        LI("El termini de recollida a Zona 1 és de 48 hores des de la sol·licitud."),
    ]
    escriu_pdf(out / "cataleg-serveis.pdf", f, "Catàleg de serveis")

    # 6.2 Condicions de pagament
    f = capcalera("Condicions de pagament i crèdit", "CP-2026", "2.1")
    f += [
        P("Condicions econòmiques aplicables als clients amb compte obert."),
        Paragraph("Formes de pagament", S["h1"]),
        taula([
            ["Forma", "Venciment", "Descompte per pagament", "Requisits"],
            ["Rebut domiciliat", "30 dies data factura", "—", "Mandat SEPA signat"],
            ["Rebut domiciliat", "60 dies data factura", "—", "Escalat A o B i 12 mesos d'antiguitat"],
            ["Transferència anticipada", "Abans de l'expedició", "2 %", "—"],
            ["Targeta", "En el moment", "—", "Comandes per sota de 3.000 €"],
            ["Confirming", "Segons acord", "—", "Aprovació prèvia del departament de crèdit"],
        ], [38 * mm, 38 * mm, 40 * mm, 54 * mm]),
        Paragraph("Límit de crèdit", S["h1"]),
        P("Cada client té assignat un límit de crèdit revisable semestralment. "
          "Quan una comanda el supera, el sistema la reté i el departament de "
          "crèdit contacta amb el client en 24 hores laborables per acordar la "
          "forma de pagament."),
        Paragraph("Impagaments", S["h1"]),
        LI("Un rebut retornat genera 12 € de despeses de devolució bancària."),
        LI("A partir del segon rebut retornat, el compte passa a pagament anticipat."),
        LI("Els interessos de demora són els que estableix la normativa de "
           "lluita contra la morositat en operacions comercials."),
    ]
    escriu_pdf(out / "condicions-pagament.pdf", f, "Condicions de pagament")

    # 6.3 Protocol de qualitat de proveïdors
    f = capcalera("Protocol d'homologació de proveïdors", "HP-2026", "1.1")
    f += [
        P("Criteris que ha de complir un fabricant per entrar al nostre catàleg."),
        Paragraph("1. Requisits documentals", S["h1"]),
        LI("Declaració de conformitat CE de cada família de producte."),
        LI("Fitxes tècniques en català o castellà."),
        LI("Certificat ISO 9001 vigent, o auditoria pròpia favorable."),
        LI("Assegurança de responsabilitat civil de producte."),
        Paragraph("2. Requisits de servei", S["h1"]),
        LI("Termini de lliurament compromès inferior a 15 dies laborables."),
        LI("Disponibilitat de recanvis durant 7 anys des de la darrera venda."),
        LI("Servei tècnic amb resposta en 5 dies laborables."),
        Paragraph("3. Avaluació periòdica", S["h1"]),
        P("Cada proveïdor homologat s'avalua anualment sobre quatre indicadors: "
          "compliment de terminis, índex de devolucions per defecte, temps de "
          "resposta del servei tècnic i estabilitat de preus. Una puntuació "
          "inferior a 6 sobre 10 obre un període de sis mesos de millora; si no "
          "es redreça, se'n retira l'homologació."),
        Paragraph("4. Taxa de defectuosos acceptable", S["h1"]),
        taula([
            ["Família", "Màxim admissible", "Actuació si se supera"],
            ["Eines elèctriques", "1,5 % de les unitats servides", "Bloqueig del lot i auditoria"],
            ["Eines manuals", "0,8 %", "Revisió del procés de forja"],
            ["Consumibles", "2,0 %", "Canvi de lot"],
            ["Equips de protecció", "0,2 %", "Retirada immediata del catàleg"],
        ], [40 * mm, 55 * mm, 75 * mm]),
    ]
    escriu_pdf(out / "homologacio-proveidors.pdf", f, "Homologació de proveïdors")

    # 6.4 Preguntes freqüents del SAT
    f = capcalera("Preguntes freqüents del servei tècnic", "FQ-2026", "1.3")
    faqs = [
        ("Quant triga una reparació en garantia?",
         "El dictamen es fa en 5 dies laborables des que la unitat arriba al "
         "magatzem central, i la reparació en 15 dies laborables més. Si es "
         "necessita un recanvi del fabricant, el termini es comunica al client "
         "en el moment del dictamen."),
        ("He perdut l'albarà, puc reclamar igualment?",
         "Sí. N'hi ha prou amb el número de comanda: amb això recuperem la data "
         "de lliurament, que és la que compta per a la garantia. Sense número de "
         "comanda ni albarà, l'expedient queda aturat."),
        ("Les bateries entren en garantia?",
         "Les bateries tenen la garantia de la família d'eines elèctriques, però "
         "la pèrdua de capacitat per ús no es considera defecte. Per sobre de "
         "300 cicles de càrrega es considera desgast normal."),
        ("Puc portar la màquina a un taller de la meva zona?",
         "Només als serveis tècnics autoritzats que consten a l'àrea de client. "
         "Una reparació feta per un tercer no autoritzat anul·la la garantia, "
         "encara que sigui una intervenció menor."),
        ("Què passa si la reparació surt més cara que la màquina?",
         "Si el cost supera el 70 % del preu de venda i l'avaria està coberta, "
         "se substitueix la unitat per una d'equivalent. Si no està coberta, "
         "s'ofereix el pressupost i el client decideix."),
        ("La garantia es reinicia després d'una substitució?",
         "No. La unitat nova conserva la data de la comanda original com a inici "
         "del còmput."),
        ("Serviu recanvis solts?",
         "Sí, per als productes en catàleg i durant 7 anys des de l'última venda. "
         "Els recanvis es demanen amb la referència de la màquina i el número de "
         "posició del despiece."),
        ("Com sé si un producte encara està en garantia?",
         "Amb la data de la comanda i la família del producte. Eines manuals, "
         "36 mesos; eines elèctriques i material elèctric, 24; equips de "
         "protecció, 12; consumibles, 6."),
    ]
    for q, a in faqs:
        f += [KeepTogether([Paragraph(q, S["h2"]), P(a)])]
    escriu_pdf(out / "faq-servei-tecnic.pdf", f, "FAQ del servei tècnic")


# =============================================================================
#  7. Documents Word
# =============================================================================
def _docx_base(titol: str, codi: str):
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10.5)

    h = doc.add_paragraph()
    r = h.add_run(titol)
    r.font.size = Pt(19)
    r.font.bold = True
    r.font.color.rgb = RGBColor(0x0F, 0x6E, 0x6A)

    s = doc.add_paragraph()
    rs = s.add_run(f"{EMPRESA} · CIF {CIF} · document {codi} · "
                   f"en vigor des de l'1 de gener de 2026")
    rs.font.size = Pt(8.5)
    rs.font.italic = True
    rs.font.color.rgb = RGBColor(0x5C, 0x6B, 0x6A)
    return doc


def _docx_peu(doc) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"{EMPRESA} · {PEU}")
    r.font.size = Pt(7.5)
    r.font.color.rgb = RGBColor(0x5C, 0x6B, 0x6A)


def condicions_generals(out: Path) -> None:
    doc = _docx_base("Condicions generals de venda", "CGV-2026")
    seccions = [
        ("1. Objecte i acceptació",
         ["Aquestes condicions regulen les vendes de material que "
          f"{EMPRESA} fa als seus clients professionals. La formalització "
          "d'una comanda implica l'acceptació íntegra d'aquestes condicions, "
          "que prevalen sobre qualsevol condició de compra del client llevat "
          "que s'hagi pactat el contrari per escrit."]),
        ("2. Comandes",
         ["Les comandes es poden fer per l'àrea de client, per correu "
          "electrònic o a través del comercial assignat. Una comanda es "
          "considera acceptada quan se'n confirma la recepció amb el número "
          "de comanda corresponent.",
          "L'import mínim per comanda és de 60 € nets. Per sota d'aquest "
          "import s'aplica un recàrrec de gestió de 9 €.",
          "Les comandes de productes que no són de catàleg (sota comanda) "
          "requereixen confirmació expressa del client i no admeten anul·lació "
          "un cop cursades al fabricant."]),
        ("3. Preus",
         ["Els preus són els de la tarifa vigent en el moment de la comanda, "
          "sense IVA, amb els descomptes de l'escalat comercial del client.",
          "Els preus poden ser revisats per variació del cost de la matèria "
          "primera o del transport. Les comandes ja confirmades mantenen el "
          "preu acceptat."]),
        ("4. Lliurament",
         ["Els terminis de lliurament són orientatius i es compten en dies "
          "laborables des de la confirmació de la comanda. Un retard no dóna "
          "dret a indemnització ni a l'anul·lació de la comanda si no supera "
          "els cinc dies laborables sobre el termini previst.",
          "El risc de la mercaderia es transmet al client en el moment del "
          "lliurament i la signatura de l'albarà."]),
        ("5. Pagament",
         ["Les condicions de pagament són les acordades a la fitxa del client. "
          "L'impagament d'un venciment faculta a suspendre els lliuraments "
          "pendents fins a la regularització del deute.",
          "La mercaderia és propietat del venedor fins al cobrament íntegre "
          "del preu (reserva de domini)."]),
        ("6. Garantia",
         ["La garantia comercial és la que estableix el Manual de garanties "
          "(document MG-2026), amb terminis diferents segons la família de "
          "producte: 36 mesos per a eines manuals, 24 per a eines elèctriques "
          "i material elèctric, 12 per a equips de protecció i 6 per a "
          "consumibles.",
          "Aquesta garantia comercial no limita ni substitueix la garantia "
          "legal de conformitat."]),
        ("7. Devolucions",
         ["Les devolucions es regeixen pel Procediment de devolucions "
          "(document PD-2026) i requereixen autorització prèvia."]),
        ("8. Protecció de dades",
         ["Les dades de contacte facilitades pel client es tracten amb la "
          "finalitat de gestionar la relació comercial, amb base jurídica en "
          "l'execució del contracte, i es conserven mentre duri la relació i "
          "els terminis de prescripció legal."]),
        ("9. Legislació i fur",
         ["Aquestes condicions es regeixen per la legislació espanyola. Per a "
          "qualsevol controvèrsia, les parts se sotmeten als jutjats i "
          "tribunals de Sabadell, amb renúncia expressa a qualsevol altre fur."]),
    ]
    for titol, paragrafs in seccions:
        h = doc.add_paragraph()
        r = h.add_run(titol)
        r.font.bold = True
        r.font.size = Pt(12)
        r.font.color.rgb = RGBColor(0x0F, 0x6E, 0x6A)
        for t in paragrafs:
            doc.add_paragraph(t)
    _docx_peu(doc)
    doc.save(out / "condicions-generals-venda.docx")


def manual_magatzem(out: Path) -> None:
    doc = _docx_base("Manual d'operativa de magatzem", "OM-2026")
    doc.add_paragraph(
        "Manual intern per al personal dels tres magatzems. Descriu la "
        "recepció, la ubicació, la preparació de comandes i l'inventari.")

    seccions = [
        ("1. Recepció de mercaderia", [
            "Comprovar que el nombre de bultos coincideix amb l'albarà del "
            "transportista abans de signar.",
            "Fer constar a l'albarà qualsevol embalatge danyat. Signar sense "
            "reserves impedeix reclamar el dany després.",
            "Verificar referències i quantitats contra la comanda de compra en "
            "un màxim de 24 hores des de la recepció.",
            "Registrar l'entrada al sistema el mateix dia: l'estoc que no consta "
            "no es pot vendre.",
        ]),
        ("2. Ubicació i codificació", [
            "Cada ubicació segueix el format PASSADÍS-PRESTATGE-ALÇADA "
            "(per exemple, A-12-3).",
            "Les eines elèctriques van a alçades 1 i 2 per pes i per risc de "
            "caiguda.",
            "Els consumibles de rotació alta van als passadissos A i B, propers "
            "a la zona de preparació.",
            "Els productes químics i inflamables van a l'armari ventilat de la "
            "zona F, amb les fitxes de seguretat accessibles.",
        ]),
        ("3. Preparació de comandes", [
            "Les comandes es preparen per ordre d'hora de tall: primer les de "
            "Zona 1, que surten el mateix dia.",
            "Cada línia preparada es valida amb lector de codi de barres. La "
            "validació manual només s'admet si l'etiqueta és il·legible, i cal "
            "avisar el responsable.",
            "Les comandes amb línies sense estoc es preparen parcialment i la "
            "resta queda en reserva, llevat que la fitxa del client indiqui el "
            "contrari.",
            "L'embalatge ha de protegir el producte: les eines elèctriques mai "
            "van soltes amb material pesat a sobre.",
        ]),
        ("4. Expedició", [
            "Adjuntar sempre l'albarà a l'exterior del bulto 1.",
            "Fotografiar el palet abans de carregar-lo quan la comanda superi "
            "els 1.000 € nets.",
            "Registrar el número de seguiment del transportista al sistema el "
            "mateix dia de la sortida: és el que veu el client.",
        ]),
        ("5. Devolucions i RMA", [
            "El material retornat sense número d'autorització es deixa a la zona "
            "de quarantena i s'avisa el departament comercial. No s'entra a "
            "l'estoc.",
            "Les unitats amb RMA de garantia van a la zona SAT, mai a l'estoc "
            "venible, encara que semblin correctes.",
        ]),
        ("6. Inventari", [
            "Inventari cíclic setmanal dels productes de rotació alta (classe A).",
            "Inventari general anual amb aturada de l'operativa.",
            "Les diferències superiors al 2 % del valor d'una ubicació s'han de "
            "documentar i comunicar a administració.",
        ]),
        ("7. Seguretat", [
            "L'ús de calçat de seguretat és obligatori a tota la nau.",
            "La carretilla elevadora només la pot fer servir personal amb "
            "formació acreditada i vigent.",
            "Les vies d'evacuació i els extintors han d'estar sempre lliures "
            "d'obstacles.",
        ]),
    ]
    for titol, punts in seccions:
        h = doc.add_paragraph()
        r = h.add_run(titol)
        r.font.bold = True
        r.font.size = Pt(12)
        r.font.color.rgb = RGBColor(0x0F, 0x6E, 0x6A)
        for t in punts:
            doc.add_paragraph(t, style="List Bullet")
    _docx_peu(doc)
    doc.save(out / "manual-magatzem.docx")


# =============================================================================
#  8. Document ESCANEJAT (sense capa de text)  → cas d'estudi d'OCR de la C4
# =============================================================================
def acta_escanejada(out: Path) -> None:
    """Genera un PDF normal i el rasteritza: queda com un escaneig de veritat."""
    import fitz  # PyMuPDF

    tmp = out / ".acta-temporal.pdf"
    f = capcalera("Acta de la reunió de qualitat", "AQ-2026-03", "1.0")
    f += [
        P("Reunió del comitè de qualitat celebrada el 12 de febrer de 2026 a la "
          "sala de reunions del magatzem central. Assistents: direcció "
          "d'operacions, responsable de magatzem, responsable de SAT i "
          "responsable de compres."),
        Paragraph("1. Revisió d'incidències del trimestre", S["h1"]),
        P("S'han registrat 47 expedients de garantia, un 8 % menys que el "
          "trimestre anterior. El 62 % corresponen a la família d'eines "
          "elèctriques, principalment amoladores i trepants. El temps mitjà de "
          "dictamen ha estat de 4,2 dies laborables, dins del compromís de 5."),
        Paragraph("2. Punts crítics detectats", S["h1"]),
        LI("Tretze expedients van arribar sense número de comanda, cosa que va "
           "endarrerir el dictamen una mitjana de 6 dies."),
        LI("Dos casos de reparació per tercers no autoritzats: es va denegar la "
           "garantia i el client ho va acceptar després de la revisió del cas."),
        LI("Un lot de discos de tall va donar una taxa de trencament del 3,1 %, "
           "per sobre del 2 % admissible. S'ha bloquejat el lot i s'ha obert "
           "una reclamació al proveïdor."),
        Paragraph("3. Acords", S["h1"]),
        LI("Incloure el número de comanda com a camp obligatori al formulari de "
           "reclamació de l'àrea de client. Responsable: sistemes. Termini: "
           "31 de març."),
        LI("Revisar el text del certificat de garantia perquè indiqui "
           "explícitament que obrir la carcassa anul·la la cobertura. "
           "Responsable: SAT. Termini: 15 de març."),
        LI("Auditar el proveïdor dels discos de tall abans de tornar a comprar. "
           "Responsable: compres. Termini: 30 d'abril."),
        Paragraph("4. Propera reunió", S["h1"]),
        P("14 de maig de 2026, a les 9.30 h, al magatzem central."),
    ]
    escriu_pdf(tmp, f, "Acta de qualitat")

    # Rasteritzar: cada pàgina passa a imatge → NO queda capa de text.
    src = fitz.open(tmp)
    dst = fitz.open()
    for pagina in src:
        pix = pagina.get_pixmap(dpi=150)          # resolució d'escàner d'oficina
        nova = dst.new_page(width=pagina.rect.width, height=pagina.rect.height)
        nova.insert_image(nova.rect, pixmap=pix)
    dst.set_metadata({"title": "Acta de qualitat (escanejat)", "author": EMPRESA})
    dst.save(out / "acta-qualitat-escanejada.pdf")
    dst.close()
    src.close()
    tmp.unlink()


# =============================================================================
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "corpus")
    args = ap.parse_args()
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    rng = random.Random(LLAVOR)
    # Mateixa llavor i mateix ordre que el generador de la BD → mateixos productes.
    from generar_dades import genera_clients
    genera_clients(rng, 500)
    productes = genera_productes(rng, 300)

    print("Generant el corpus de Distribucions Vallès SL…\n")
    manual_garanties(out);        print("  ✔ manual-garanties.pdf          (el document clau)")
    procediment_devolucions(out); print("  ✔ procediment-devolucions.pdf")
    tarifes(out, productes);      print("  ✔ tarifes-2026.pdf              (amb taules llargues)")
    fitxes_producte(out);         print("  ✔ fitxa-producte-*.pdf          (5 fitxes)")
    politica_enviaments(out);     print("  ✔ politica-enviaments.pdf")
    farciment(out);               print("  ✔ 4 documents de farciment")
    condicions_generals(out);     print("  ✔ condicions-generals-venda.docx")
    manual_magatzem(out);         print("  ✔ manual-magatzem.docx")
    acta_escanejada(out);         print("  ✔ acta-qualitat-escanejada.pdf  (sense capa de text)")

    fitxers = sorted(p for p in out.iterdir() if p.suffix in (".pdf", ".docx"))
    total = sum(p.stat().st_size for p in fitxers)
    print(f"\n{len(fitxers)} documents · {total/1024/1024:.1f} MB · {out}")

    # ------------------------------------------------- comprovacions finals
    from pypdf import PdfReader

    def text_de(p: Path) -> str:
        if p.suffix == ".pdf":
            return "".join((pg.extract_text() or "") for pg in PdfReader(p).pages)
        return " ".join(x.text for x in Document(p).paragraphs)

    problemes: list[str] = []
    for p in fitxers:
        txt = text_de(p)
        if f"REF-{REF_PROHIBIDA}" in txt:
            problemes.append(f"REF-{REF_PROHIBIDA} apareix a {p.name}")
        if p.name == "acta-qualitat-escanejada.pdf":
            if len(txt.strip()) > 50:
                problemes.append("l'acta escanejada té capa de text: no serveix "
                                 "per a la demo d'OCR de la C4")
        elif len(txt.strip()) < 200:
            problemes.append(f"{p.name} amb prou feines té text extraïble")

    if problemes:
        raise SystemExit("✘ " + "\n✘ ".join(problemes))
    print(f"REF-{REF_PROHIBIDA}: absent de tot el corpus ✔")
    print("acta-qualitat-escanejada.pdf: sense capa de text ✔ (cal OCR)")


if __name__ == "__main__":
    main()
