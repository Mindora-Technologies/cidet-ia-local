#!/usr/bin/env bash
# =============================================================================
#  L'API d'Ollama amb curl, sense cap llibreria pel mig
#  CIDET · IA en local · Classe 2
# -----------------------------------------------------------------------------
#  Primer sense streaming i després amb streaming, perquè es vegi la diferència.
#  Ús:  ./curl-chat.sh
# =============================================================================
set -euo pipefail

OLLAMA="${OLLAMA_URL:-http://localhost:11434}"
MODEL="${MODEL:-assistent-valles}"
PREGUNTA="Quants mesos de garantia tenen les eines elèctriques?"

command -v jq >/dev/null || { echo "Cal 'jq': sudo apt install -y jq"; exit 1; }

echo "══ 1. Sense streaming ─ stream: false ══"
echo "   La petició es queda esperant i, quan el model ha acabat del tot,"
echo "   arriba la resposta sencera de cop."
echo

curl -s "$OLLAMA/api/chat" -d "$(jq -nc \
  --arg m "$MODEL" --arg p "$PREGUNTA" \
  '{model:$m, stream:false, messages:[{role:"user", content:$p}]}')" \
| jq -r '
    "Resposta: " + .message.content,
    "",
    "Tokens generats:  \(.eval_count)",
    "Temps generació:  \(.eval_duration / 1000000000 | .*10 | round / 10) s",
    "Tokens per segon: \(.eval_count / (.eval_duration / 1000000000) | .*10 | round / 10)"
  '

echo
echo "══ 2. Amb streaming ─ stream: true ══"
echo "   Ara arriba un objecte JSON per cada tros de text. És el que fa que"
echo "   un xat sembli ràpid: el primer token surt de seguida."
echo

curl -s -N "$OLLAMA/api/chat" -d "$(jq -nc \
  --arg m "$MODEL" --arg p "$PREGUNTA" \
  '{model:$m, stream:true, messages:[{role:"user", content:$p}]}')" \
| while IFS= read -r linia; do
    # Cada línia és un JSON independent. Anem imprimint només el tros de text.
    printf '%s' "$(jq -rj '.message.content // ""' <<<"$linia")"
    # L'últim objecte porta done:true i les estadístiques.
    if [[ $(jq -r '.done // false' <<<"$linia") == true ]]; then
      echo; echo
      jq -r '"Tokens: \(.eval_count) · \(.eval_count / (.eval_duration / 1000000000) | .*10 | round / 10) tokens/s"' <<<"$linia"
    fi
  done

echo
echo "Fixa't que el total de tokens és semblant en tots dos casos: el streaming"
echo "no fa que el model vagi més ràpid, fa que ho SEMBLI."
