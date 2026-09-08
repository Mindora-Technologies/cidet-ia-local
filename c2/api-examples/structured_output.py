#!/usr/bin/env python3
"""Sortida estructurada: JSON garantit — CIDET · IA en local · Classe 2

El model no «intenta» respondre en JSON: se li passa un esquema i el motor
l'obliga a generar només tokens que hi encaixin. La diferència importa quan la
resposta ha d'entrar en una base de dades o alimentar una altra aplicació: sense
esquema, un dia de cada vint el model afegeix «Aquí tens el JSON:» al davant i
et trenca el programa.

    pip install ollama
    python structured_output.py
"""
import json

import ollama

# L'esquema és el contracte. Amb "required" i additionalProperties:false ens
# assegurem que hi són tots els camps i que no n'apareixen d'inventats.
ESQUEMA = {
    "type": "object",
    "properties": {
        "producte": {"type": "string"},
        "categoria": {"type": "string"},
        "preu_estimat": {"type": "number"},
    },
    "required": ["producte", "categoria", "preu_estimat"],
    "additionalProperties": False,
}

DESCRIPCIONS = [
    "Trepant percutor Valfort PX-1800 de 18 V amb dues bateries de 4 Ah i maletí.",
    "Caixa de 25 discos de tall per a metall Norbrec de 125 mm i 1 mm de gruix.",
    "Botes de seguretat Duracamp categoria S3, puntera de composite, talla 43.",
]

for descripcio in DESCRIPCIONS:
    resposta = ollama.chat(
        model="assistent-valles",
        messages=[{
            "role": "user",
            "content": (
                "Extreu les dades d'aquest producte del catàleg. La categoria ha de "
                "ser una d'aquestes: eines manuals, eines elèctriques, consumibles, "
                "equips de protecció, material elèctric.\n\n"
                f"{descripcio}"
            ),
        }],
        format=ESQUEMA,          # ← aquí passa la màgia
        options={"temperature": 0},   # per extreure dades, sempre 0
    )

    # Ja no cal netejar la resposta ni buscar-hi claudàtors: és JSON i prou.
    dades = json.loads(resposta["message"]["content"])
    # Retallem el nom perquè la taula no es desmunti si el model hi aboca
    # la descripció sencera, que és el que sol passar.
    nom = dades["producte"][:46]
    print(f"{nom:<46} {dades['categoria']:<20} {dades['preu_estimat']:>9.2f} €")

print("\nCap resposta ha calgut netejar-la: totes eren JSON vàlid a la primera.")
print("Compte: l'esquema garanteix el FORMAT, no que el preu sigui correcte.")
