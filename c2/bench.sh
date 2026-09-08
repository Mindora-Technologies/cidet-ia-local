#!/usr/bin/env bash
# Mesura tokens/s, latència i VRAM de cada model i ho escriu en CSV.
#   ./c2/bench.sh --models qwen3:4b qwen3:8b --repeticions 3
set -euo pipefail

# El prompt de mesura viu en un fitxer a part, i no aquí dins, perquè TOTHOM
# ha de mesurar amb exactament el mateix text. Si cadascú fa servir el seu, els
# números de la classe no es poden comparar entre ells i l'exercici no serveix.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FITXER_PROMPT="${FITXER_PROMPT:-$SCRIPT_DIR/prompt-mesura.txt}"

# Recanvi per si algú executa el script fora del repositori.
PREGUNTA_DEFECTE="Explica en tres paràgrafs què és la quantització d'un model de llenguatge i per què importa quan s'executa en local."

if [[ -f $FITXER_PROMPT ]]; then
  # Llegim el fitxer sencer i li traiem els salts de línia finals.
  PREGUNTA_FITXER="$(< "$FITXER_PROMPT")"
  PREGUNTA_DEFECTE="${PREGUNTA_FITXER%$'\n'}"
else
  echo "AVÍS: no trobo $FITXER_PROMPT; faig servir el prompt de recanvi." >&2
  echo "      Els teus números NO seran comparables amb els dels companys." >&2
fi

PREGUNTA="${PREGUNTA:-$PREGUNTA_DEFECTE}"
MODELS=(); REPETICIONS=3; NUM_CTX=8192
SORTIDA="${SORTIDA:-$(dirname "${BASH_SOURCE[0]}")/bench-$(date +%Y%m%d-%H%M).csv}"

while (($#)); do
  case $1 in
    --models) shift; while (($#)) && [[ $1 != --* ]]; do MODELS+=("$1"); shift; done ;;
    --repeticions) REPETICIONS="$2"; shift 2 ;;
    --num-ctx) NUM_CTX="$2"; shift 2 ;;
    --pregunta) PREGUNTA="$2"; shift 2 ;;
    *) echo "opció desconeguda: $1" >&2; exit 1 ;;
  esac
done
((${#MODELS[@]})) || { echo "ús: $0 --models <model>..." >&2; exit 1; }

vram() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 || echo 0; }
gpu()  { nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "sense GPU"; }

echo "gpu,model,repeticio,num_ctx,vram_usada_mb,temps_primer_token,tokens_generats,segons_generacio,tokens_per_segon" > "$SORTIDA"
printf '%-22s %-6s %10s %10s %12s\n' MODEL REP "VRAM MB" "TOKENS" "TOKENS/S"

for m in "${MODELS[@]}"; do
  curl -s http://localhost:11434/api/generate -d "{\"model\":\"$m\",\"prompt\":\"\",\"keep_alive\":0}" >/dev/null
  base=$(vram)
  for r in $(seq 1 "$REPETICIONS"); do
    resposta=$(curl -s http://localhost:11434/api/generate -d "$(jq -nc \
      --arg m "$m" --arg p "$PREGUNTA" --argjson c "$NUM_CTX" \
      '{model:$m, prompt:$p, stream:false, options:{num_ctx:$c, temperature:0.2}}')")
    usada=$(( $(vram) - base ))
    eval_count=$(jq -r '.eval_count // 0'     <<<"$resposta")
    eval_dur=$(  jq -r '.eval_duration // 0'  <<<"$resposta")
    first=$(     jq -r '.prompt_eval_duration // 0' <<<"$resposta")
    segons=$(awk "BEGIN{printf \"%.2f\", $eval_dur/1e9}")
    ttft=$(awk   "BEGIN{printf \"%.2f\", $first/1e9}")
    tps=$(awk    "BEGIN{if($segons>0) printf \"%.1f\", $eval_count/$segons; else print 0}")
    echo "$(gpu),$m,$r,$NUM_CTX,$usada,$ttft,$eval_count,$segons,$tps" >> "$SORTIDA"
    printf '%-22s %-6s %10s %10s %12s\n' "$m" "$r" "$usada" "$eval_count" "$tps"
  done
  curl -s http://localhost:11434/api/generate -d "{\"model\":\"$m\",\"prompt\":\"\",\"keep_alive\":0}" >/dev/null
done
echo
echo "→ $SORTIDA"
echo "Prompt de mesura: $([[ -f $FITXER_PROMPT ]] && echo "$FITXER_PROMPT" || echo "(de recanvi, dins de l'script)")"
echo "Compara el tokens/s amb el que preveia c1/hardware-calc.xlsx: ha de quedar entre el 60 % i el 80 %."
