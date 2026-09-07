#!/usr/bin/env python3
"""Genera c3/tests.jsonl i c5/eval.jsonl a partir de les dades reals de la demo."""
import json, sys
from pathlib import Path

ARREL = Path("/home/miquelonis/projects/mindora/cidet-ia-local")

# ---------------------------------------------------------------- C3: tests
# Banc de proves per comparar MODELS. No necessita RAG: es respon amb el context
# que se li dóna al model o amb coneixement general del domini.
C3 = [
 # --- fets del corpus
 ("fets", "Quants mesos de garantia tenen les eines elèctriques a Distribucions Vallès?",
  "24 mesos (2 anys).", "manual-garanties.pdf"),
 ("fets", "I les eines manuals?", "36 mesos (3 anys).", "manual-garanties.pdf"),
 ("fets", "Quina garantia tenen els consumibles?", "6 mesos.", "manual-garanties.pdf"),
 ("fets", "Quina garantia tenen els equips de protecció individual?", "12 mesos.", "manual-garanties.pdf"),
 ("fets", "Des de quin moment es compta el termini de garantia?",
  "Des de la data de la comanda que consta a l'albarà de lliurament.", "manual-garanties.pdf"),
 ("fets", "Quantes hores laborables té el SAT per obrir un expedient i assignar un RMA?",
  "24 hores laborables.", "manual-garanties.pdf"),
 ("fets", "Quants dies laborables triga el peritatge tècnic?", "5 dies laborables.", "manual-garanties.pdf"),
 ("fets", "Quin càrrec s'aplica si el client no accepta el pressupost de reparació?",
  "25 euros en concepte de peritatge.", "manual-garanties.pdf"),
 ("fets", "En quin percentatge del preu de venda es substitueix la unitat en comptes de reparar-la?",
  "Quan el cost de la reparació supera el 70 % del preu de venda.", "manual-garanties.pdf"),
 ("fets", "Quants magatzems té Distribucions Vallès i on són?",
  "Tres: el central a Sabadell i delegacions a Tarragona i Girona.", "politica-enviaments.pdf"),
 ("fets", "A partir de quin import són gratuïts els ports a la zona 2?",
  "A partir de 250 euros nets.", "politica-enviaments.pdf"),
 ("fets", "Quin descompte té l'escalat comercial A en consumibles?", "30 %.", "tarifes-2026.pdf"),
 ("fets", "Quin és l'import mínim per comanda?",
  "60 euros nets; per sota s'aplica un recàrrec de gestió de 9 euros.", "condicions-generals-venda.docx"),
 ("fets", "Quants dies té el client per retornar mercaderia per error propi?",
  "14 dies naturals, amb un càrrec del 15 % de despeses.", "procediment-devolucions.pdf"),
 ("fets", "Quin és el format de les ubicacions del magatzem?",
  "PASSADÍS-PRESTATGE-ALÇADA, per exemple A-12-3.", "manual-magatzem.docx"),

 # --- raonament (cal encadenar dos fets)
 ("raonament", "Un client va comprar una amoladora el 15 de gener de 2025. Avui és 7 de setembre de 2026. Està en garantia?",
  "Sí. És una eina elèctrica (24 mesos) i la garantia arriba fins al 15 de gener de 2027.", "manual-garanties.pdf"),
 ("raonament", "Un client va comprar discos de tall el març de 2025 i se li han trencat ara, el setembre de 2026. Els cobreix la garantia?",
  "No. Els consumibles tenen 6 mesos de garantia i ja han passat 18 mesos.", "manual-garanties.pdf"),
 ("raonament", "Una comanda du un trepant i una caixa de broques. Quina garantia té la comanda?",
  "No en té una de sola: el trepant té 24 mesos com a eina elèctrica i les broques 6 com a consumible. Cada línia té el seu termini.", "manual-garanties.pdf"),
 ("raonament", "Un client obre una amoladora per canviar-li les escombretes ell mateix i després reclama la garantia. Què li diries?",
  "Que obrir la carcassa anul·la la garantia, i que a més les escombretes són una peça de desgast que no hi entra.", "manual-garanties.pdf"),
 ("raonament", "Es reparen unes botes de seguretat en garantia el juny de 2026. Fins quan cobreix la garantia de la unitat reparada?",
  "Fins als 12 mesos de la comanda original: la reparació no reinicia el termini.", "manual-garanties.pdf"),
 ("raonament", "Un client vol retornar un producte fabricat sota comanda. Es pot?",
  "No. Els productes sota comanda o fets a mida no admeten devolució.", "procediment-devolucions.pdf"),
 ("raonament", "Una soldadora inverter s'ha cremat perquè el client la connectava a un generador sense regulació. Entra en garantia?",
  "No. Els danys per xarxa elèctrica o generador sense regulació estan exclosos.", "fitxa-producte / manual-garanties.pdf"),
 ("raonament", "Un client factura 30.000 € l'any. Quin descompte té en eines?",
  "És escalat B (25.000–60.000 €): 17 % en eines.", "tarifes-2026.pdf"),

 # --- format
 ("format", "Llista els terminis de garantia de totes les famílies en una taula amb dues columnes: família i mesos.",
  "Una taula amb: eines manuals 36, eines elèctriques 24, material elèctric 24, equips de protecció 12, consumibles 6.", "manual-garanties.pdf"),
 ("format", "Dona'm els cinc passos del procediment de reclamació en una llista numerada, una línia cadascun.",
  "Cinc línies numerades: comunicar, obrir RMA, enviar la unitat, peritatge, resolució.", "manual-garanties.pdf"),
 ("format", "Respon només amb un número: quants mesos de garantia tenen els consumibles?",
  "6", "manual-garanties.pdf"),
 ("format", "Resumeix la política de devolucions en exactament dues frases.",
  "Dues frases, ni una més, que cobreixin l'autorització prèvia i els terminis segons el motiu.", "procediment-devolucions.pdf"),
 ("format", "Dona'm la resposta en format JSON amb les claus «familia» i «mesos» per a les eines elèctriques.",
  '{"familia": "eines elèctriques", "mesos": 24}', "manual-garanties.pdf"),

 # --- seguiment d'instruccions
 ("instruccions", "Explica la política de garanties sense fer servir en cap moment la paraula «garantia».",
  "Una explicació dels terminis de cobertura que eviti literalment aquesta paraula.", "manual-garanties.pdf"),
 ("instruccions", "Respon en menys de 20 paraules: què cal per tramitar un expedient de garantia?",
  "El número de comanda o l'albarà, la referència del producte i la descripció de l'avaria. Menys de 20 paraules.", "manual-garanties.pdf"),
 ("instruccions", "Ets el SAT. Escriu el correu de resposta a un client que reclama uns discos de tall de fa 18 mesos. Sigues educat però clar que no hi entra.",
  "Un correu breu, educat, que expliqui que els consumibles tenen 6 mesos i que la reclamació queda fora de termini.", "manual-garanties.pdf"),
 ("instruccions", "Enumera només les exclusions de la garantia, sense explicar què SÍ que cobreix.",
  "Només la llista d'exclusions: desgast normal, consumibles gastats, ús inadequat, manca de manteniment, cops, reparacions per tercers, xarxa elèctrica defectuosa, corrosió.", "manual-garanties.pdf"),

 # --- català correcte
 ("català", "Explica en català què és el període de garantia d'una eina elèctrica.",
  "Text en català correcte, sense castellanismes, amb «període», «termini» i «garantia» ben emprats.", "manual-garanties.pdf"),
 ("català", "Escriu tres frases sobre el procediment de devolucions fent servir els pronoms febles correctament.",
  "Tres frases en català amb pronoms febles ben col·locats (n'hi ha, se'n fa, s'hi aplica…).", "procediment-devolucions.pdf"),
 ("català", "Com es diu en català «el plazo de garantía ha vencido»?",
  "«El termini de garantia ha vençut» (no «ha expirat el plaç»).", "—"),
 ("català", "Escriu la data 12/03/2025 en català, amb el mes en lletres.",
  "12 de març de 2025.", "—"),

 # --- negativa correcta (el model HA de dir que no ho sap)
 ("negativa", "Quin preu té la referència REF-2231?",
  "Ha de dir que no té cap informació d'aquesta referència. NO se n'ha d'inventar el preu.", "cap"),
 ("negativa", "Quantes unitats de la REF-2231 queden al magatzem de Girona?",
  "Ha de dir que aquesta referència no consta.", "cap"),
 ("negativa", "Quina és la facturació anual de Distribucions Vallès SL?",
  "Ha de dir que no ho sap: no és a cap document.", "cap"),
 ("negativa", "Quin és el telèfon personal del responsable de magatzem?",
  "Ha de dir que no té aquesta dada.", "cap"),
 ("negativa", "Quina garantia tenen els vehicles industrials que ven l'empresa?",
  "Ha de dir que l'empresa no ven vehicles industrials i que no hi ha aquesta família.", "cap"),
 ("negativa", "Quin descompte té l'escalat comercial F?",
  "Ha de dir que només hi ha els escalats A, B, C i D.", "tarifes-2026.pdf"),
]

# ---------------------------------------------------------------- C5: gold
# Avaluació del RAG i de l'AGENT: cada cas diu quines fonts calen.
C5 = [
 # documents
 ("documents", "Quants mesos de garantia tenen les eines elèctriques?", "24 mesos.", ["documents"]),
 ("documents", "Què NO cobreix la garantia d'una eina elèctrica?",
  "Desgast normal (escombretes, corretges, bateries amb més de 300 cicles), ús inadequat, manca de manteniment, cops i caigudes, reparacions per tercers, xarxa elèctrica defectuosa i corrosió.", ["documents"]),
 ("documents", "Com es tramita una reclamació de garantia?",
  "Comunicar la incidència amb el número de comanda, rebre el RMA en 24 h, enviar la unitat en 10 dies, peritatge en 5 dies laborables i resolució en 15.", ["documents"]),
 ("documents", "Quant costa el peritatge si no s'accepta el pressupost?", "25 euros.", ["documents"]),
 ("documents", "Quins terminis de lliurament hi ha per a la zona 3?",
  "48–72 hores laborables, amb comanda abans de les 15.00 h.", ["documents"]),
 ("documents", "Quina taxa de defectuosos s'admet en equips de protecció?", "0,2 %.", ["documents"]),
 ("documents", "Quin cicle de treball té la soldadora inverter NORBREC IW-200?", "60 % a 160 A.", ["documents"]),
 ("documents", "Quantes peces té el joc de claus fixes FERRALT?", "12 peces, de 6 a 22 mm.", ["documents"]),

 # SQL
 ("sql", "Quantes comandes ha fet Ferreteria Puig SL?",
  "El nombre de files de v_comandes_client per a aquest client.", ["sql"]),
 ("sql", "Quin dia es va fer la comanda 4521?", "El 12 de març de 2025.", ["sql"]),
 ("sql", "Quins productes duia la comanda 4521?",
  "Un trepant percutor VALFORT PX-1800, discos de tall metall i guants de treball.", ["sql"]),
 ("sql", "De quina població és Ferreteria Puig SL?", "De Granollers.", ["sql"]),
 ("sql", "Quantes unitats de la referència REF-1001 hi ha al magatzem central?",
  "Les unitats que consten a v_estoc_disponible per a aquest producte i magatzem.", ["sql"]),
 ("sql", "Quines comandes de Ferreteria Puig estan en trànsit?",
  "Les files de v_comandes_client amb estat 'en trànsit' per a aquest client, entre les quals la 4521.", ["sql"]),

 # API
 ("api", "On és l'enviament de la comanda 4521?",
  "Al centre de distribució de Granollers, en trànsit.", ["api"]),
 ("api", "Quin transportista porta la comanda 4521?",
  "Transports Vallès Express, amb seguiment TVE-2026-0004521.", ["api"]),
 ("api", "Quan arribarà la comanda 4521?", "El 8 de setembre de 2026.", ["api"]),
 ("api", "Quants bultos té l'enviament de la comanda 4521?", "2 bultos, 14,6 kg.", ["api"]),

 # combinades — les importants
 ("combinada", "La comanda 4521 de Ferreteria Puig està en garantia? I on és l'enviament?",
  "El trepant percutor (eines elèctriques, 24 mesos) SÍ que hi és, fins al 12/03/2027; els consumibles (6 mesos) no. L'enviament és en trànsit al centre de distribució de Granollers, amb lliurament previst el 8/9/2026.",
  ["documents", "sql", "api"]),
 ("combinada", "Al trepant de la comanda 4521 se li han gastat les escombretes. Ho cobreix la garantia?",
  "No. Encara que la comanda estigui dins dels 24 mesos, les escombretes són peça de desgast i estan excloses.",
  ["documents", "sql"]),
 ("combinada", "Un client de Granollers pregunta si pot retornar la comanda 4521 perquè s'ha equivocat. Pot?",
  "No: han passat molt més de 14 dies naturals des del 12 de març de 2025.", ["documents", "sql"]),
 ("combinada", "Quant hauria de pagar de ports Ferreteria Puig per la comanda 4521?",
  "Cal comparar l'import net de la comanda amb el llindar de la seva zona (Granollers, zona 1: gratuït des de 150 €).",
  ["documents", "sql"]),
 ("combinada", "La comanda 4521 arribarà dins del termini compromès?",
  "Va sortir el 5/9 i el lliurament previst és el 8/9; la zona 1 compromet el dia laborable següent, així que va amb retard sobre el compromís de zona 1.",
  ["documents", "api"]),
 ("combinada", "Si el trepant de la comanda 4521 s'avaria avui, quants dies li queden de garantia?",
  "Uns 186 dies: fins al 12 de març de 2027.", ["documents", "sql"]),

 # negatives
 ("negativa", "Quin preu té la referència REF-2231?",
  "Ha de dir que aquesta referència no consta ni al catàleg ni a cap document. NO se n'ha d'inventar el preu.", []),
 ("negativa", "Quantes unitats de REF-2231 queden a Tarragona?",
  "Ha de dir que la referència no existeix.", []),
 ("negativa", "On és l'enviament de la comanda 99999?",
  "Ha de dir que no consta cap enviament per a aquesta comanda.", ["api"]),
 ("negativa", "Quina és la política de teletreball de l'empresa?",
  "Ha de dir que no hi ha cap document sobre això.", []),
 ("negativa", "Quin marge de benefici té l'empresa en eines elèctriques?",
  "Ha de dir que no ho sap: la tarifa dóna PVP i descomptes, no marges.", []),
 ("negativa", "Què diu l'acta de la reunió de qualitat del 12 de febrer?",
  "Aquell document és un escaneig sense capa de text: sense OCR el sistema no en pot llegir res, i ho ha de dir.", []),
]

def escriu(cami: Path, files: list[dict]) -> None:
    cami.parent.mkdir(parents=True, exist_ok=True)
    with cami.open("w", encoding="utf-8") as f:
        for r in files:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  {cami.relative_to(ARREL)}: {len(files)} casos")

escriu(ARREL / "c3" / "tests.jsonl", [
    {"id": f"c3-{i:03d}", "pregunta": p, "resposta_esperada": r,
     "categoria": cat, "font": font}
    for i, (cat, p, r, font) in enumerate(C3, start=1)])

escriu(ARREL / "c5" / "eval.jsonl", [
    {"id": f"c5-{i:03d}", "pregunta": p, "resposta_esperada": r,
     "categoria": cat, "fonts_necessaries": fonts}
    for i, (cat, p, r, fonts) in enumerate(C5, start=1)])

from collections import Counter
print("\n  c3 per categoria:", dict(Counter(c for c, *_ in C3)))
print("  c5 per categoria:", dict(Counter(c for c, *_ in C5)))
