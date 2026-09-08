#!/usr/bin/env python3
"""Mesura de rendiment amb peticions SIMULTÀNIES — CIDET · IA en local · Classe 2

`bench.sh` mesura una petició darrere l'altra, i respon a «quant triga una
resposta». Aquest script en llança unes quantes alhora i respon a una pregunta
diferent: **quantes peticions aguanta el servidor**. No és el mateix, i és la
que importa quan darrere hi ha una empresa i no una persona.

El número que en surt és el **cabal agregat**: la suma de tokens generats
dividida pel temps que ha durat la tanda sencera. Amb una sola petició, el
cabal agregat i els tokens/s d'aquella petició són el mateix; amb vuit, no.

Serveix per comparar dos servidors amb el mateix model:

    python bench-concurrent.py --base-url http://localhost:11434/v1 --model qwen3:8b
    python bench-concurrent.py --base-url http://localhost:8000/v1  --model qwen3:8b

El primer és Ollama; el segon, vLLM. Ollama sol guanyar amb una petició i
perdre de llarg amb vuit: vLLM agrupa les peticions en un sol lot i comparteix
el càlcul, i Ollama no.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

ARREL = Path(__file__).resolve().parent
FITXER_PROMPT = ARREL / "prompt-mesura.txt"
PROMPT_RECANVI = ("Explica en tres paràgrafs què és la quantització d'un model "
                  "de llenguatge i per què importa quan s'executa en local.")


@dataclass
class Peticio:
    """El resultat d'una petició."""
    ok: bool
    tokens: int = 0
    segons: float = 0.0
    primer_token: float = 0.0
    error: str = ""

    @property
    def tps(self) -> float:
        return self.tokens / self.segons if self.segons > 0 else 0.0


async def una_peticio(client: httpx.AsyncClient, base_url: str, model: str,
                      prompt: str, max_tokens: int) -> Peticio:
    """Una petició en streaming, per poder mesurar el temps al primer token."""
    t0 = time.perf_counter()
    primer = 0.0
    tokens = 0
    try:
        async with client.stream(
            "POST", f"{base_url.rstrip('/')}/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
                "max_tokens": max_tokens,
                "temperature": 0.2,
            },
            headers={"Authorization": "Bearer ollama"},   # Ollama l'ignora; vLLM la pot demanar
            timeout=httpx.Timeout(300.0, connect=15.0),
        ) as r:
            if r.status_code != 200:
                cos = (await r.aread()).decode()[:120]
                return Peticio(ok=False, error=f"HTTP {r.status_code}: {cos}")
            async for linia in r.aiter_lines():
                if not linia.startswith("data: "):
                    continue
                dades = linia[6:].strip()
                if dades == "[DONE]":
                    break
                try:
                    tros = json.loads(dades)
                except json.JSONDecodeError:
                    continue
                delta = tros.get("choices", [{}])[0].get("delta", {})
                # Els models que «pensen» (qwen3, gpt-oss…) envien el raonament
                # al camp `reasoning` i deixen `content` buit fins que acaben de
                # rumiar. Aquests tokens els genera la GPU igual que els altres,
                # així que compten per al rendiment: si només miressis `content`,
                # un model que raona et sortiria a 0 tokens/s.
                if delta.get("content") or delta.get("reasoning"):
                    tokens += 1          # un tros ≈ un token en tots dos servidors
                    if primer == 0.0:
                        primer = time.perf_counter() - t0
    except Exception as e:                                    # noqa: BLE001
        return Peticio(ok=False, error=f"{type(e).__name__}: {e}")

    return Peticio(ok=True, tokens=tokens, segons=time.perf_counter() - t0,
                   primer_token=primer)


async def una_tanda(base_url: str, model: str, prompt: str, n: int,
                    max_tokens: int) -> tuple[list[Peticio], float]:
    """Llança n peticions alhora i espera que acabin totes."""
    limits = httpx.Limits(max_connections=n + 4, max_keepalive_connections=n + 4)
    async with httpx.AsyncClient(limits=limits) as client:
        t0 = time.perf_counter()
        resultats = await asyncio.gather(*[
            una_peticio(client, base_url, model, prompt, max_tokens)
            for _ in range(n)
        ])
        return list(resultats), time.perf_counter() - t0


def imprimeix_tanda(concurrencia: int, resultats: list[Peticio],
                    durada: float) -> dict | None:
    bones = [r for r in resultats if r.ok]
    dolentes = [r for r in resultats if not r.ok]

    if not bones:
        print(f"  {concurrencia:>3}  ✘ totes han fallat: {dolentes[0].error}")
        return None

    tokens = sum(r.tokens for r in bones)
    agregat = tokens / durada if durada > 0 else 0.0
    per_peticio = statistics.mean(r.tps for r in bones)
    ttft = statistics.median(r.primer_token for r in bones if r.primer_token > 0) \
        if any(r.primer_token > 0 for r in bones) else 0.0

    print(f"  {concurrencia:>3}  {len(bones):>4}  {tokens:>7}  {durada:>7.1f}  "
          f"{agregat:>9.1f}  {per_peticio:>10.1f}  {ttft*1000:>8.0f}"
          + (f"   ({len(dolentes)} fallides)" if dolentes else ""))

    return {"concurrencia": concurrencia, "agregat": agregat,
            "per_peticio": per_peticio, "ttft": ttft, "fallides": len(dolentes)}


async def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="http://localhost:11434/v1",
                    help="endpoint compatible amb OpenAI (per defecte, Ollama)")
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--concurrencia", type=int, nargs="+", default=[1, 2, 4, 8],
                    help="quantes peticions alhora; se'n pot posar més d'una")
    ap.add_argument("--repeticions", type=int, default=1,
                    help="tandes per cada nivell de concurrència")
    ap.add_argument("--max-tokens", type=int, default=256,
                    help="sostre de tokens per resposta, perquè la tanda no s'eternitzi")
    ap.add_argument("--prompt", help="text a fer servir (per defecte, prompt-mesura.txt)")
    args = ap.parse_args()

    if args.prompt:
        prompt = args.prompt
    elif FITXER_PROMPT.exists():
        prompt = FITXER_PROMPT.read_text(encoding="utf-8").strip()
    else:
        print(f"AVÍS: no trobo {FITXER_PROMPT}; faig servir el prompt de recanvi.",
              file=sys.stderr)
        prompt = PROMPT_RECANVI

    print(f"\n▶ {args.base_url}  ·  model {args.model}  ·  "
          f"sostre {args.max_tokens} tokens")
    print(f"  prompt: «{prompt[:64]}…»\n")
    print("  sim.   ok   tokens   temps    cabal/s   per petic.   TTFT ms")
    print("  " + "─" * 62)

    resums: list[dict] = []
    for n in args.concurrencia:
        tandes = []
        for _ in range(args.repeticions):
            resultats, durada = await una_tanda(
                args.base_url, args.model, prompt, n, args.max_tokens)
            r = imprimeix_tanda(n, resultats, durada)
            if r:
                tandes.append(r)
        if tandes:
            # ens quedem amb la millor tanda de cada nivell
            resums.append(max(tandes, key=lambda x: x["agregat"]))

    if not resums:
        print("\n✘ No s'ha pogut mesurar res. Comprova que el servidor respon:")
        print(f"   curl {args.base_url.rstrip('/')}/models")
        return 1

    print()
    base = resums[0]
    millor = max(resums, key=lambda x: x["agregat"])

    if base["agregat"] <= 0:
        print("  El servidor ha respost però no ha generat cap token. Sol voler dir")
        print("  que --max-tokens és massa baix per a un model que raona abans de")
        print("  respondre: puja'l a 512 o més.")
        return 1
    print(f"  Amb 1 petició:  {base['agregat']:.1f} tokens/s")
    print(f"  Millor cabal:   {millor['agregat']:.1f} tokens/s "
          f"amb {millor['concurrencia']} simultànies "
          f"(×{millor['agregat']/base['agregat']:.2f})")

    if millor["agregat"] / base["agregat"] < 1.3:
        print("\n  El cabal gairebé no puja en paral·lel: aquest servidor atén les")
        print("  peticions d'una en una. És el comportament típic d'Ollama.")
    else:
        print("\n  El cabal puja de valent amb la concurrència: el servidor agrupa")
        print("  les peticions en lots. És el que fa vLLM, i per això es fa servir")
        print("  quan hi ha molts usuaris alhora.")

    print("\n  Compte en comparar: el TTFT (temps al primer token) sol EMPITJORAR")
    print("  quan puja la concurrència, encara que el cabal total millori. Un usuari")
    print("  sol nota el TTFT; l'empresa sencera nota el cabal.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
