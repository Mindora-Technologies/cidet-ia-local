#!/usr/bin/env bash
# =============================================================================
#  CIDET · IA en local — descàrrega dels models de la C2/C3
# -----------------------------------------------------------------------------
#  Es llança al minut 5 de la classe 1 i va baixant models EN SEGON PLA
#  mentre es fa la teoria. Quan arribi la part pràctica, ja hi seran.
#
#  Ús:
#     ./c1/pull-models.sh                      # descàrrega normal (necessita xarxa)
#     ./c1/pull-models.sh --offline /ruta/models   # importa GGUF del pen drive
#     ./c1/pull-models.sh --only qwen3:4b      # només un model
#     ./c1/pull-models.sh --list               # mostra què faria i surt
#
#  Recomanat a l'aula:
#     nohup ./c1/pull-models.sh > /dev/null 2>&1 &
#     tail -f logs/pull-models-*.log
# =============================================================================
set -euo pipefail

# --------------------------------------------------------------- els models
# Edita aquesta llista i prou. L'ordre és l'ordre de descàrrega.
MODELS=(
  "qwen3:4b"                 # C1 — deures: el primer model que executen
  "qwen3-embedding:0.6b"     # C3 — embeddings per al RAG
  "qwen3:8b"                 # C2 — el de referència per a les mesures
  "qwen3:14b"                # C2/C3 — el cas «just» a la 5070
  "gemma3:12b"               # C3 — per comparar famílies de models
  "qwen3:32b"                # C2 — NO hi cap: es fa servir per provocar offload
)

# Correspondència model Ollama → fitxer GGUF al pen drive (mode --offline)
declare -A GGUF_FILES=(
  ["qwen3:4b"]="Qwen3-4B-Q4_K_M.gguf"
  ["qwen3:8b"]="Qwen3-8B-Q4_K_M.gguf"
  ["qwen3:14b"]="Qwen3-14B-Q4_K_M.gguf"
  ["qwen3:32b"]="Qwen3-32B-Q4_K_M.gguf"
  ["qwen3-embedding:0.6b"]="Qwen3-Embedding-0.6B-Q8_0.gguf"
)

# Context per defecte de cada model (num_ctx del Modelfile en mode offline)
declare -A NUM_CTX=(
  ["qwen3:4b"]=8192
  ["qwen3:8b"]=8192
  ["qwen3:14b"]=8192
  ["qwen3:32b"]=4096
  ["qwen3-embedding:0.6b"]=2048
)

# -------------------------------------------------------------- configuració
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="${LOG_DIR:-$REPO_DIR/logs}"
LOG_FILE="$LOG_DIR/pull-models-$(date +%Y%m%d-%H%M%S).log"
OFFLINE_DIR=""
ONLY=""
LIST_ONLY=0

OK_MODELS=(); SKIP_MODELS=(); FAIL_MODELS=()

# ---------------------------------------------------------------------- utils
c_reset=$'\033[0m'; c_bold=$'\033[1m'; c_grn=$'\033[32m'
c_yel=$'\033[33m'; c_red=$'\033[31m'; c_cya=$'\033[36m'; c_dim=$'\033[2m'

# Tot va al log; a pantalla només el resum.
_ts() { date '+%Y-%m-%d %H:%M:%S'; }
logfile() { printf '[%s] %s\n' "$(_ts)" "$*" >> "$LOG_FILE"; }
say()  { printf '%s\n' "$*"; logfile "$*"; }
log()  { printf '%s[·]%s %s\n' "$c_cya" "$c_reset" "$*"; logfile "$*"; }
ok()   { printf '%s[✔]%s %s\n' "$c_grn" "$c_reset" "$*"; logfile "OK: $*"; }
warn() { printf '%s[!]%s %s\n' "$c_yel" "$c_reset" "$*" >&2; logfile "AVÍS: $*"; }
die()  { printf '%s[✘]%s %s\n' "$c_red" "$c_reset" "$*" >&2; logfile "ERROR: $*"; exit 1; }

human() {
  awk -v b="${1:-0}" 'BEGIN{
    split("B KiB MiB GiB TiB",u," "); i=1
    while (b>=1024 && i<5) { b/=1024; i++ }
    printf (i==1 ? "%d %s" : "%.1f %s"), b, u[i]
  }'
}

hhmmss() { printf '%02d:%02d:%02d' $(($1/3600)) $(($1%3600/60)) $(($1%60)); }

# Mida total del magatzem d'Ollama
ollama_disk() {
  local d
  for d in "$HOME/.ollama/models" /usr/share/ollama/.ollama/models; do
    [[ -d $d ]] && { du -sb "$d" 2>/dev/null | cut -f1; return; }
  done
  echo 0
}

model_present() {
  ollama list 2>/dev/null | awk 'NR>1{print $1}' | grep -qx "$1"
}

# ------------------------------------------------------------------ descàrrega
pull_online() {
  local m=$1
  log "ollama pull $m"
  if ollama pull "$m" >>"$LOG_FILE" 2>&1; then
    return 0
  fi
  return 1
}

pull_offline() {
  local m=$1 gguf mf ctx
  gguf="${GGUF_FILES[$m]:-}"
  if [[ -z $gguf ]]; then
    warn "$m: no hi ha cap GGUF associat a la taula GGUF_FILES; el salto"
    return 1
  fi
  if [[ ! -f "$OFFLINE_DIR/$gguf" ]]; then
    warn "$m: no trobo $OFFLINE_DIR/$gguf"
    return 1
  fi

  ctx="${NUM_CTX[$m]:-8192}"
  mf="$OFFLINE_DIR/Modelfile.$(echo "$m" | tr ':' '-')"
  cat > "$mf" <<MF
FROM ./$gguf

PARAMETER temperature 0.2
PARAMETER num_ctx $ctx

SYSTEM """Ets un assistent tècnic d'una empresa distribuïdora.
Respon sempre en català, de manera concisa i basant-te només en la informació que tens.
Si no ho saps, digues que no ho saps."""
MF
  log "ollama create $m  (des de $gguf, num_ctx=$ctx)"
  ( cd "$OFFLINE_DIR" && ollama create "$m" -f "$mf" ) >>"$LOG_FILE" 2>&1
}

# --------------------------------------------------------------------- main
usage() { sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0; }

main() {
  while (($#)); do
    case $1 in
      --offline) OFFLINE_DIR="${2:?cal indicar la ruta dels GGUF}"; shift 2 ;;
      --only)    ONLY="$ONLY $2"; shift 2 ;;
      --list)    LIST_ONLY=1; shift ;;
      -h|--help) usage ;;
      *) die "opció desconeguda: $1 (prova --help)" ;;
    esac
  done

  mkdir -p "$LOG_DIR"
  : > "$LOG_FILE"

  command -v ollama >/dev/null 2>&1 || die "ollama no està instal·lat (mira c1/install-server.md §6)"

  local targets=()
  local m
  for m in "${MODELS[@]}"; do
    [[ -n $ONLY && " $ONLY " != *" $m "* ]] && continue
    targets+=("$m")
  done
  ((${#targets[@]})) || die "cap model seleccionat"

  if ((LIST_ONLY)); then
    printf '%sModels que es baixarien:%s\n' "$c_bold" "$c_reset"
    printf '  · %s\n' "${targets[@]}"
    exit 0
  fi

  printf '%s╔════════════════════════════════════════════════════════════╗\n' "$c_bold"
  printf '║  CIDET · descàrrega de models                              ║\n'
  printf '╚════════════════════════════════════════════════════════════╝%s\n' "$c_reset"
  log "registre: $LOG_FILE"
  if [[ -n $OFFLINE_DIR ]]; then
    [[ -d $OFFLINE_DIR ]] || die "el directori offline no existeix: $OFFLINE_DIR"
    log "mode OFFLINE des de $OFFLINE_DIR"
  else
    log "mode en línia (ollama pull)"
    if ! curl -fsI --connect-timeout 10 https://ollama.com >/dev/null 2>&1; then
      warn "sembla que no hi ha connexió amb ollama.com. Prova --offline /ruta/models"
    fi
  fi
  log "${#targets[@]} models a processar, un darrere l'altre (en paral·lel saturaríem la xarxa de l'aula)"

  local t0=$SECONDS disk0 disk1
  disk0=$(ollama_disk)

  local i=0 n=${#targets[@]} tm
  for m in "${targets[@]}"; do
    i=$((i + 1))
    printf '\n%s[%d/%d] %s%s\n' "$c_bold" "$i" "$n" "$m" "$c_reset"
    if model_present "$m"; then
      ok "$m ja hi és — el salto"
      SKIP_MODELS+=("$m")
      continue
    fi
    tm=$SECONDS
    if [[ -n $OFFLINE_DIR ]]; then
      if pull_offline "$m"; then
        ok "$m importat en $(hhmmss $((SECONDS - tm)))"; OK_MODELS+=("$m")
      else
        warn "$m ha fallat (mira $LOG_FILE)"; FAIL_MODELS+=("$m")
      fi
    else
      if pull_online "$m"; then
        ok "$m baixat en $(hhmmss $((SECONDS - tm)))"; OK_MODELS+=("$m")
      else
        warn "$m ha fallat (mira $LOG_FILE)"; FAIL_MODELS+=("$m")
      fi
    fi
  done

  disk1=$(ollama_disk)

  # ------------------------------------------------------------------ resum
  printf '\n%s─────────────────────── RESUM ───────────────────────%s\n' "$c_dim" "$c_reset"
  printf '%-14s %d  %s\n' "Baixats:"  "${#OK_MODELS[@]}"   "${OK_MODELS[*]:-—}"
  printf '%-14s %d  %s\n' "Ja hi eren:" "${#SKIP_MODELS[@]}" "${SKIP_MODELS[*]:-—}"
  printf '%-14s %d  %s\n' "Fallits:"  "${#FAIL_MODELS[@]}" "${FAIL_MODELS[*]:-—}"
  printf '%-14s %s\n' "Temps total:" "$(hhmmss $((SECONDS - t0)))"
  printf '%-14s %s  (magatzem total: %s)\n' "Espai afegit:" \
    "$(human $((disk1 - disk0)))" "$(human "$disk1")"
  printf '%s─────────────────────────────────────────────────────%s\n' "$c_dim" "$c_reset"
  echo
  ollama list 2>/dev/null || true
  echo
  log "registre complet: $LOG_FILE"

  ((${#FAIL_MODELS[@]} == 0)) || exit 1
}

main "$@"
