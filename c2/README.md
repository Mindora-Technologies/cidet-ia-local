# Classe 2 — Ollama i execució de models en local

**Dimarts 8 de setembre de 2026 · 15:30–19:00**

Ahir vam muntar el servidor. Avui el fem treballar i, sobretot, **el mesurem**.
Al final de la sessió sabreu dir, amb números, quin model va bé en quina màquina.

## Blocs

| Hora | Bloc |
|---|---|
| 15:30 – 16:15 | Com funciona Ollama per dins: models, tags, `Modelfile`, `keep_alive`, l'API |
| 16:15 – 17:00 | **Mesurar**: tokens/s reals, temps al primer token, VRAM ocupada. Omplim `bench-template.csv` |
| 17:00 – 17:15 | *Pausa* |
| 17:15 – 18:00 | Quantitzacions cara a cara sobre la mateixa GPU: FP16 vs Q8 vs Q4 vs Q3 |
| 18:00 – 19:00 | **Què passa quan NO hi cap**: offload a CPU, i per què és tan lent |

## Materials

| Fitxer | Què és |
|---|---|
| `Modelfile` | Exemple comentat: `FROM`, `PARAMETER`, `SYSTEM`, `TEMPLATE` |
| `bench-template.csv` | Full de mesures que s'omple a classe |
| `bench.sh` | Automatitza les mesures i escriu al CSV |

## L'experiment central

Amb la mateixa pregunta i el mateix `num_ctx`, mesurar a la vostra GPU:

```bash
./c2/bench.sh --models qwen3:4b qwen3:8b qwen3:14b --repeticions 3
```

I comparar-ho amb el que preveia `c1/hardware-calc.xlsx`. La fórmula del curs
és `t/s ≈ amplada de banda ÷ mida del model`; heu de veure entre un 60 % i un
80 % d'això. Si en veieu un 20 %, alguna cosa va per CPU.

## El moment «no hi cap»

```bash
ollama run qwen3:32b "explica'm què és la quantització"
# i en una altra terminal:
nvtop
```

Veureu la VRAM plena, la CPU disparada i la generació caient a menys de 5 t/s.
Això és **offload**: la part del model que no hi cap s'executa a la CPU, i la
CPU té una amplada de banda de memòria deu vegades pitjor.

La conclusió del dia: **no és lent perquè el model sigui gran; és lent perquè
no hi cap.**

## Deures per a la C3

1. `bench-template.csv` omplert amb les vostres mesures.
2. La comparació entre el t/s previst pel full de càlcul i el mesurat.

---

*CIDET · IA en local · Classe 2*
