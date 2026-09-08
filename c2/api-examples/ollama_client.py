#!/usr/bin/env python3
"""Ollama amb la seva llibreria oficial — CIDET · IA en local · Classe 2

El mateix que openai_client.py, però amb la llibreria d'Ollama. Aquesta té
accés a coses que l'API d'OpenAI no contempla (gestionar models, veure quins
n'hi ha carregats), a canvi de lligar-te a Ollama.

    pip install ollama
    python ollama_client.py
"""
import ollama

for tros in ollama.chat(
    model="assistent-valles",
    messages=[{"role": "user",
               "content": "Quina garantia té un trepant percutor? Respon en una frase."}],
    stream=True,
):
    print(tros["message"]["content"], end="", flush=True)
print()

# Això no ho pots fer amb l'API d'OpenAI: és propi d'Ollama.
print("\nModels carregats ara mateix a la GPU:")
for m in ollama.ps().get("models", []):
    print(f"  · {m['name']}")
