#!/usr/bin/env python3
"""Ollama amb la llibreria d'OpenAI — CIDET · IA en local · Classe 2

La gràcia d'aquest fitxer és el que NO té: cap adaptació. És el mateix codi que
faries servir contra OpenAI, canviant només base_url i api_key. Per això migrar
una aplicació que ja funciona cap a un model local sol ser qüestió de dues línies.

    pip install openai
    python openai_client.py
"""
from openai import OpenAI

# api_key és obligatòria a la llibreria, però Ollama no la mira: qualsevol text val.
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

flux = client.chat.completions.create(
    model="assistent-valles",
    messages=[{"role": "user",
               "content": "Quina garantia té un trepant percutor? Respon en una frase."}],
    stream=True,
)

for tros in flux:
    print(tros.choices[0].delta.content or "", end="", flush=True)
print()
