# Classe 1 — Fonaments, maquinari i instal·lació del servidor

**Dilluns 7 de setembre de 2026 · 15:30–19:00 · CIDET**

---

## Què farem avui

Avui no entrenarem cap model ni muntarem cap RAG. Avui aixequem **la base**: entendre
què és de veritat un LLM que s'executa a casa teva, saber **calcular abans de comprar**
si un model hi cabrà, i deixar tres servidors funcionant amb GPU.

Al final de la sessió cada un de vosaltres tindrà una màquina que respon a
`ollama run` amb la GPU al 100 %. I, més important, sabreu **per què** funciona.

> **Primer de tot:** llancem la descàrrega de models en segon pla, que triga.
> ```bash
> nohup ./c1/pull-models.sh > /dev/null 2>&1 &
> ```

---

## Horaris

| Hora | Bloc | Què |
|---|---|---|
| **15:30 – 15:45** | Obertura | La demo final: l'assistent de la distribuïdora responent amb documents + SQL + API. On anem a parar en 6 classes. |
| **15:45 – 16:45** | **Bloc 1 — Fonaments** | Què és un LLM i què no. Paràmetres, quantització, context, KV cache. Per què la VRAM és el coll d'ampolla i no la potència de càlcul. La demo de l'al·lucinació: preguntem el preu de la `REF-2231`. |
| *16:45 – 17:00* | *Pausa* | |
| **17:00 – 17:45** | **Bloc 2 — Dimensionament** | Les dues fórmules del curs. Fem servir `hardware-calc.xlsx` amb casos reals vostres. La matriu «hi cap?» de les tres GPU de l'aula. Quan compensa comprar VRAM i quan no. |
| **17:45 – 19:00** | **Bloc 3 — Instal·lació** | Ubuntu Server, driver NVIDIA, CUDA, Docker amb GPU i Ollama. Cadascú a la seva màquina, seguint `install-server.md`. Acabem amb `ollama run qwen3:4b`. |

---

## Materials d'avui

| Fitxer | Què és |
|---|---|
| [`hardware-calc.xlsx`](hardware-calc.xlsx) | **La plantilla de dimensionament.** L'eina que us emporteu i que fareu servir a casa dels clients. Ompliu només les caselles grogues. |
| [`install-server.md`](install-server.md) | El guió pas a pas de la instal·lació. Pensat per seguir-lo sense professor al davant. |
| [`pull-models.sh`](pull-models.sh) | Baixa els models de la C2 en segon pla mentre fem teoria. |
| [`../docs/preparacio-pendrive.md`](../docs/preparacio-pendrive.md) | Com preparar els USB i com instal·lar-ho tot **sense internet**. |

---

## Les dues fórmules que heu de recordar

```
VRAM_pesos (GB) ≈ paràmetres (B) × bytes/paràmetre × 1,1

tokens/s ≈ amplada de banda (GB/s) ÷ mida del model (GB)
```

**Bytes per paràmetre:** FP16 = 2 · Q8 = 1 · Q6 = 0,75 · **Q4 = 0,5** · Q3 = 0,4

Amb això sol ja podeu respondre, en 30 segons i davant del client, la pregunta que
sempre fan: *«amb aquesta targeta n'hi ha prou?»*.

---

## Les GPU de l'aula

| GPU | VRAM | Amplada de banda | Arquitectura | Accelera FP8/FP4 |
|---|---|---|---|---|
| RTX 3060 | 12 GB | ~360 GB/s | Ampere (2021) | No |
| RTX 5070 | 12 GB | ~672 GB/s | Blackwell (2025) | Sí |
| RTX 5060 Ti | 16 GB | ~448 GB/s | Blackwell (2025) | Sí |

Fixeu-vos en una cosa que sorprèn tothom: la **5060 Ti té menys amplada de banda que
la 5070** (448 vs 672 GB/s) i, per tant, generarà menys tokens per segon amb el mateix
model. Però té **4 GB més de VRAM**, i això vol dir que hi caben models que a la 5070
no hi caben de cap manera. *Més ràpida* i *millor* no són el mateix.

---

## Regles que repetirem tot el curs

- **Q4_K_M és el punt dolç.** Quatre vegades menys memòria que FP16, pèrdua de qualitat
  que gairebé no es nota.
- **Per al 95 % dels casos d'empresa, la resposta és RAG, no *fine-tuning*.**
- **Temperatura 0–0,3** per a assistents d'empresa. La creativitat aquí és un defecte.
- **El català tokenitza pitjor que l'anglès**: consumeix més context i va més lent.
- **El rendiment real queda entre el 60 % i el 80 % del teòric.** Sempre.
- **Les Blackwell (50xx) accelen FP8/FP4 per maquinari; les Ampere, no.**

---

## Deures per a la C2

1. Deixeu el servidor engegat i accessible per SSH.
2. `./c1/pull-models.sh` executat, amb els models baixats.
3. `ollama run qwen3:4b "Explica'm què és la quantització"` — i mireu `nvtop` mentre respon.
4. **Ompliu `hardware-calc.xlsx` amb un cas real d'un client vostre.** El comentem a la C2.

---

## Enllaços de la sessió

- Ubuntu Server 24.04 LTS — <https://releases.ubuntu.com/24.04/>
- Ollama — <https://ollama.com> · biblioteca de models: <https://ollama.com/library>
- Especificacions de GPU (amplada de banda!) — <https://www.techpowerup.com/gpu-specs/>
- Drivers NVIDIA per a Linux — <https://www.nvidia.com/en-us/drivers/unix/>
- NVIDIA Container Toolkit — <https://docs.nvidia.com/datacenter/cloud-native/>
- Models Qwen3 en GGUF — <https://huggingface.co/Qwen>
- Repositori d'aquest curs — <https://github.com/Mindora-Technologies/cidet-ia-local>

---

## Propera classe

**C2 — dimarts 8/9: Ollama i execució de models en local.** Mesurarem tokens/s de
veritat, compararem quantitzacions a la mateixa GPU, i veurem què passa exactament
quan un model **no** hi cap i cau a la CPU.

---

*CIDET · IA en local · Classe 1*
