#!/usr/bin/env python3
"""Compara models d'Ollama sobre el banc de proves del domini.

Executa tests.jsonl contra N models, puntua cada resposta amb un MODEL JUTGE i
en treu una taula comparativa amb la nota per categoria, la velocitat i la VRAM.

    python c3/eval_models.py --models qwen3:4b qwen3:8b qwen3:14b
    python c3/eval_models.py --models qwen3:8b --jutge qwen3:14b --limit 10
    python c3/eval_models.py --models qwen3:8b --categoria negativa

Sobre el model jutge: hauria de ser MÉS GRAN que els que avalua, i mai el
mateix model que s'està avaluant (es posa bona nota). Amb 12–16 GB, jutjar amb
un 14B models de 4B i 8B és raonable.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import httpx

ARREL = Path(__file__).resolve().parents[1]
OLLAMA_URL = "http://localhost:11434"
TESTS = ARREL / "c3" / "tests.jsonl"

PROMPT_JUTGE = """\
Ets un avaluador expert. Compara la RESPOSTA DEL MODEL amb la RESPOSTA ESPERADA
i puntua-la de 0 a 10.

Criteris:
· 10 = correcta i completa. 7–9 = correcta amb detalls de menys.
· 4–6 = parcialment correcta o barrejada amb coses que no toquen.
· 1–3 = incorrecta. 0 = no respon o s'inventa dades.
· Si la categoria és «negativa», la resposta CORRECTA és admetre que no ho sap.
  Si el model s'inventa una dada en aquests casos, la nota és 0.
· Si la categoria és «català», penalitza els castellanismes i els errors de llengua.
· Si la categoria és «format», el format demanat s'ha de complir literalment.

PREGUNTA: {pregunta}
CATEGORIA: {categoria}
RESPOSTA ESPERADA: {esperada}
RESPOSTA DEL MODEL: {obtinguda}

Respon NOMÉS amb un JSON, sense res més:
{{"nota": <0-10>, "motiu": "<una frase en català>"}}
"""


@dataclass
class Resultat:
    model: str
    cas_id: str
    categoria: str
    pregunta: str
    esperada: str
    obtinguda: str
    nota: float = 0.0
    motiu: str = ""
    segons: float = 0.0
    tokens: int = 0
    tokens_per_segon: float = 0.0


@dataclass
class ResumModel:
    model: str
    resultats: list[Resultat] = field(default_factory=list)
    vram_mb: int = 0
    mida_gb: float = 0.0

    @property
    def nota(self) -> float:
        return statistics.mean(r.nota for r in self.resultats) if self.resultats else 0.0

    @property
    def tps(self) -> float:
        v = [r.tokens_per_segon for r in self.resultats if r.tokens_per_segon > 0]
        return statistics.median(v) if v else 0.0

    def per_categoria(self) -> dict[str, float]:
        d: dict[str, list[float]] = defaultdict(list)
        for r in self.resultats:
            d[r.categoria].append(r.nota)
        return {k: statistics.mean(v) for k, v in sorted(d.items())}


# ------------------------------------------------------------------ Ollama
def genera(model: str, prompt: str, temperatura: float = 0.1,
           timeout: float = 300.0) -> tuple[str, int, float]:
    """Retorna (text, tokens generats, segons)."""
    t0 = time.time()
    r = httpx.post(f"{OLLAMA_URL}/api/generate", timeout=timeout, json={
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": temperatura},
    })
    r.raise_for_status()
    d = r.json()
    return d.get("response", ""), int(d.get("eval_count", 0)), time.time() - t0


def vram_actual() -> int:
    """VRAM en ús segons nvidia-smi, en MB. 0 si no hi ha GPU NVIDIA."""
    try:
        s = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10)
        return int(s.stdout.strip().splitlines()[0])
    except Exception:                              # noqa: BLE001
        return 0


def mida_model(model: str) -> float:
    """Mida del model en GB, segons ollama list."""
    try:
        s = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        for linia in s.stdout.splitlines()[1:]:
            camps = linia.split()
            if camps and camps[0] == model:
                valor, unitat = float(camps[2]), camps[3].upper()
                return valor if unitat.startswith("GB") else valor / 1024
    except Exception:                              # noqa: BLE001
        pass
    return 0.0


def descarrega(model: str) -> None:
    """Treu el model de la VRAM perquè la mesura del següent sigui neta."""
    try:
        httpx.post(f"{OLLAMA_URL}/api/generate", timeout=30,
                   json={"model": model, "prompt": "", "keep_alive": 0})
    except Exception:                              # noqa: BLE001
        pass


# ------------------------------------------------------------------- jutge
def puntua(jutge: str, cas: dict, resposta: str) -> tuple[float, str]:
    prompt = PROMPT_JUTGE.format(
        pregunta=cas["pregunta"], categoria=cas["categoria"],
        esperada=cas["resposta_esperada"], obtinguda=resposta or "(cap resposta)")
    text, _, _ = genera(jutge, prompt, temperatura=0.0)
    m = re.search(r"\{.*?\}", text, re.S)
    if not m:
        return 0.0, "el jutge no ha retornat JSON"
    try:
        d = json.loads(m.group(0))
        return float(d.get("nota", 0)), str(d.get("motiu", ""))[:160]
    except (json.JSONDecodeError, ValueError):
        return 0.0, "JSON del jutge il·legible"


# -------------------------------------------------------------------- eixida
def taula_markdown(resums: list[ResumModel]) -> str:
    cats = sorted({c for r in resums for c in r.per_categoria()})
    l = ["# Comparativa de models", "",
         f"Banc: `c3/tests.jsonl` · {len(resums[0].resultats)} casos · "
         f"generat el {time.strftime('%Y-%m-%d %H:%M')}", "",
         "| Model | Mida | VRAM | t/s | Nota | " + " | ".join(cats) + " |",
         "|---|---|---|---|---|" + "---|" * len(cats)]
    for r in sorted(resums, key=lambda x: -x.nota):
        pc = r.per_categoria()
        l.append(f"| **{r.model}** | {r.mida_gb:.1f} GB | {r.vram_mb/1024:.1f} GB | "
                 f"{r.tps:.0f} | **{r.nota:.1f}** | "
                 + " | ".join(f"{pc.get(c, 0):.1f}" for c in cats) + " |")
    l += ["", "Notes de 0 a 10, puntuades per un model jutge.", "",
          "## Com llegir-ho", "",
          "· **Nota** és la mitjana de totes les categories: mira també les columnes.",
          "· **negativa** és la categoria que més separa els models: és la capacitat",
          "  de dir «no ho sé» en comptes d'inventar-se una dada. En un assistent",
          "  d'empresa val més que la nota global.",
          "· **t/s** és la mediana de tokens per segon generats en aquesta GPU.",
          "· **VRAM** és el que marcava `nvidia-smi` amb el model carregat: compara-ho",
          "  amb el que preveia `c1/hardware-calc.xlsx`.", ""]
    return "\n".join(l)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--jutge", default="qwen3:14b")
    ap.add_argument("--tests", type=Path, default=TESTS)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--categoria", help="avalua només una categoria")
    ap.add_argument("--sortida", type=Path, default=ARREL / "c3" / "resultats")
    args = ap.parse_args()

    if not args.tests.exists():
        raise SystemExit(f"✘ no trobo {args.tests}")

    casos = [json.loads(l) for l in args.tests.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.categoria:
        casos = [c for c in casos if c["categoria"] == args.categoria]
    if args.limit:
        casos = casos[:args.limit]
    if not casos:
        raise SystemExit("✘ cap cas seleccionat")

    disponibles = {m["name"] for m in httpx.get(f"{OLLAMA_URL}/api/tags").json()["models"]}
    for m in [*args.models, args.jutge]:
        if m not in disponibles:
            raise SystemExit(f"✘ el model «{m}» no hi és. Baixa'l: ollama pull {m}")
    if args.jutge in args.models:
        print(f"⚠ el jutge ({args.jutge}) també s'avalua: es puntuarà a si mateix "
              f"i tendirà a ser generós.\n", file=sys.stderr)

    print(f"\n▶ {len(casos)} casos × {len(args.models)} models · jutge: {args.jutge}\n")

    resums: list[ResumModel] = []
    for model in args.models:
        print(f"── {model}")
        descarrega(model)
        base = vram_actual()
        resum = ResumModel(model=model, mida_gb=mida_model(model))

        for i, cas in enumerate(casos, start=1):
            print(f"   [{i:>3}/{len(casos)}] {cas['categoria']:<12} "
                  f"{cas['pregunta'][:46]:<46}", end="", flush=True)
            try:
                text, tokens, segons = genera(model, cas["pregunta"])
            except Exception as e:                 # noqa: BLE001
                print(f" ✘ {type(e).__name__}")
                resum.resultats.append(Resultat(
                    model=model, cas_id=cas["id"], categoria=cas["categoria"],
                    pregunta=cas["pregunta"], esperada=cas["resposta_esperada"],
                    obtinguda=f"ERROR: {e}", nota=0.0, motiu="el model ha fallat"))
                continue

            if i == 1:
                resum.vram_mb = max(0, vram_actual() - base)

            nota, motiu = puntua(args.jutge, cas, text)
            resum.resultats.append(Resultat(
                model=model, cas_id=cas["id"], categoria=cas["categoria"],
                pregunta=cas["pregunta"], esperada=cas["resposta_esperada"],
                obtinguda=text.strip(), nota=nota, motiu=motiu, segons=segons,
                tokens=tokens,
                tokens_per_segon=tokens / segons if segons > 0 else 0.0))
            print(f" {nota:>4.1f}  {tokens/max(segons,0.01):>5.1f} t/s")

        print(f"   → nota {resum.nota:.1f}/10 · {resum.tps:.0f} t/s · "
              f"{resum.vram_mb/1024:.1f} GB de VRAM\n")
        resums.append(resum)
        descarrega(model)

    args.sortida.mkdir(parents=True, exist_ok=True)
    marca = time.strftime("%Y%m%d-%H%M")

    md = args.sortida / f"comparativa-{marca}.md"
    md.write_text(taula_markdown(resums), encoding="utf-8")

    csv_path = args.sortida / f"resultats-{marca}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "cas_id", "categoria", "nota", "tokens_per_segon",
                    "segons", "pregunta", "resposta_esperada", "resposta_model", "motiu"])
        for r in resums:
            for x in r.resultats:
                w.writerow([x.model, x.cas_id, x.categoria, x.nota,
                            f"{x.tokens_per_segon:.1f}", f"{x.segons:.2f}",
                            x.pregunta, x.esperada, x.obtinguda, x.motiu])

    print(taula_markdown(resums))
    print(f"\n✔ {md}\n✔ {csv_path}")


if __name__ == "__main__":
    main()
