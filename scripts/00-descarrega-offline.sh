#!/usr/bin/env bash
# =============================================================================
#  CIDET · IA en local — Descàrrega offline de tot el material pesat
# -----------------------------------------------------------------------------
#  Descarga a ./offline/ todo lo necesario para montar el servidor SIN internet.
#  Pensado para volcarse a un pen drive (>= 64 GB, exFAT).
#
#  Uso:
#     ./scripts/00-descarrega-offline.sh                 # todo
#     ./scripts/00-descarrega-offline.sh --only iso      # solo un grupo
#     ./scripts/00-descarrega-offline.sh --skip models   # sin los GGUF
#     ./scripts/00-descarrega-offline.sh --dest /media/usb/offline
#
#  Grupos: iso · nvidia · docker · models · ollama
#  Es idempotente y reanudable: se puede parar (Ctrl-C) y relanzar.
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------- configuració
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
DEST="${DEST:-$REPO_DIR/offline}"
UBUNTU_SERIES="${UBUNTU_SERIES:-24.04}"
UBUNTU_MIRROR="${UBUNTU_MIRROR:-https://releases.ubuntu.com}"
NVIDIA_BASE="https://download.nvidia.com/XFree86/Linux-x86_64"
NVIDIA_VER="${NVIDIA_VER:-}"          # buida = detecta l'última branca de producció
MIN_NVIDIA_MAJOR=570                   # RTX 50xx (Blackwell) necessiten >= 570

DOCKER_IMAGES=(
  "nvidia/cuda:12.6.0-base-ubuntu24.04"
  "qdrant/qdrant:latest"
  "postgres:16"
  "ghcr.io/open-webui/open-webui:main"
)

# Models GGUF: "fitxer_destí|URL"
GGUF_MODELS=(
  "Qwen3-4B-Q4_K_M.gguf|https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf"
  "Qwen3-8B-Q4_K_M.gguf|https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/main/Qwen3-8B-Q4_K_M.gguf"
  "Qwen3-14B-Q4_K_M.gguf|https://huggingface.co/Qwen/Qwen3-14B-GGUF/resolve/main/Qwen3-14B-Q4_K_M.gguf"
  "Qwen3-Embedding-0.6B-Q8_0.gguf|https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/main/Qwen3-Embedding-0.6B-Q8_0.gguf"
  "Qwen3-32B-Q4_K_M.gguf|https://huggingface.co/Qwen/Qwen3-32B-GGUF/resolve/main/Qwen3-32B-Q4_K_M.gguf"
)

ONLY=""
SKIP=""
WARNINGS=()

# ----------------------------------------------------------------------- utils
c_reset=$'\033[0m'; c_bold=$'\033[1m'; c_grn=$'\033[32m'; c_yel=$'\033[33m'
c_red=$'\033[31m'; c_cya=$'\033[36m'; c_dim=$'\033[2m'

log()   { printf '%s[·]%s %s\n' "$c_cya" "$c_reset" "$*"; }
ok()    { printf '%s[✔]%s %s\n' "$c_grn" "$c_reset" "$*"; }
warn()  { printf '%s[!]%s %s\n' "$c_yel" "$c_reset" "$*" >&2; WARNINGS+=("$*"); }
die()   { printf '%s[✘]%s %s\n' "$c_red" "$c_reset" "$*" >&2; exit 1; }
hr()    { printf '%s%s%s\n' "$c_dim" "$(printf '─%.0s' $(seq 1 72))" "$c_reset"; }
title() { printf '\n%s%s%s\n' "$c_bold" "$*" "$c_reset"; hr; }

human() {  # bytes -> llegible
  local b=${1:-0}
  awk -v b="$b" 'BEGIN{
    split("B KiB MiB GiB TiB",u," "); i=1
    while (b>=1024 && i<5) { b/=1024; i++ }
    printf (i==1 ? "%d %s" : "%.1f %s"), b, u[i]
  }'
}

dir_size() { [[ -d $1 ]] && du -sb "$1" 2>/dev/null | cut -f1 || echo 0; }

group_enabled() {
  local g=$1
  [[ -n $ONLY && " $ONLY " != *" $g "* ]] && return 1
  [[ -n $SKIP && " $SKIP " == *" $g "* ]] && return 1
  return 0
}

# Descàrrega reanudable amb barra de progrés.
# fetch <url> <fitxer_destí>
fetch() {
  local url=$1 out=$2
  mkdir -p "$(dirname "$out")"
  log "baixant $(basename "$out")"
  if ! curl -fL --retry 3 --retry-delay 5 --connect-timeout 20 \
            -C - --progress-bar -o "$out" "$url"; then
    # curl surt 33 quan el servidor no admet resume i el fitxer ja és complet
    local rc=$?
    if [[ $rc -eq 33 && -s $out ]]; then
      warn "$(basename "$out"): el servidor no admet resume; es considera complet"
      return 0
    fi
    rm -f "$out.part" 2>/dev/null || true
    return 1
  fi
  return 0
}

# url_ok <url>  -> 0 si respon 200/302 amb contingut
url_ok() { curl -fsIL --connect-timeout 15 -o /dev/null "$1" 2>/dev/null; }

# verify_sha <fitxer> <sha256esperat> -> 0 si coincideix
verify_sha() {
  local f=$1 want=$2 got
  got="$(sha256sum "$f" | cut -d' ' -f1)"
  [[ $got == "$want" ]]
}

# --------------------------------------------------------------- dependències
check_deps() {
  title "0. Comprovació de dependències"
  local missing=()
  for bin in curl sha256sum awk du; do
    command -v "$bin" >/dev/null 2>&1 || missing+=("$bin")
  done
  ((${#missing[@]})) && die "falten binaris obligatoris: ${missing[*]}"
  ok "curl, sha256sum, awk, du"

  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    ok "docker operatiu (les imatges es podran exportar)"
  else
    warn "docker no disponible o sense permisos: es saltarà el grup 'docker'"
    SKIP="$SKIP docker"
  fi

  if command -v ollama >/dev/null 2>&1; then
    ok "ollama present (opcional, només informatiu)"
  else
    log "ollama no instal·lat (opcional en aquesta màquina)"
  fi

  local free_kb free_b
  free_kb=$(df -Pk "$(dirname "$DEST")" | awk 'NR==2{print $4}')
  free_b=$((free_kb * 1024))
  log "espai lliure a $(dirname "$DEST"): $(human "$free_b")"
  if (( free_b < 70000000000 )); then
    warn "menys de ~70 GB lliures; potser no hi cabrà tot (models GGUF inclosos)"
  fi
}

# ------------------------------------------------------------------ 1. ISO
do_iso() {
  title "1. ISO Ubuntu Server ${UBUNTU_SERIES} LTS (amd64)  [prioritat 1]"
  local dir="$DEST/iso" sums="$DEST/iso/SHA256SUMS" iso name want
  mkdir -p "$dir"

  if ! curl -fsSL --connect-timeout 20 -o "$sums" "$UBUNTU_MIRROR/$UBUNTU_SERIES/SHA256SUMS"; then
    warn "no s'ha pogut baixar SHA256SUMS d'Ubuntu; ISO omesa"
    return 0
  fi
  name="$(awk '/live-server-amd64\.iso$/ {gsub(/^\*/,"",$2); print $2; exit}' "$sums")"
  want="$(awk '/live-server-amd64\.iso$/ {print $1; exit}' "$sums")"
  [[ -z $name ]] && { warn "no trobo cap live-server-amd64.iso a SHA256SUMS"; return 0; }
  iso="$dir/$name"
  log "versió detectada: $name"

  if [[ -f $iso ]] && verify_sha "$iso" "$want"; then
    ok "$name ja hi és i el SHA256 quadra — no es torna a baixar"
    return 0
  fi

  fetch "$UBUNTU_MIRROR/$UBUNTU_SERIES/$name" "$iso" || { warn "descàrrega de la ISO fallida"; return 0; }

  if verify_sha "$iso" "$want"; then
    ok "$name — SHA256 verificat"
  else
    warn "SHA256 de la ISO NO coincideix. Esborra '$iso' i torna-ho a provar abans de gravar cap USB."
  fi
}

# --------------------------------------------------------------- 2. NVIDIA
resolve_nvidia_ver() {
  [[ -n $NVIDIA_VER ]] && { echo "$NVIDIA_VER"; return 0; }
  local v
  v="$(curl -fsSL --connect-timeout 15 "$NVIDIA_BASE/latest.txt" 2>/dev/null | awk 'NR==1{print $1}')" || true
  if [[ -n ${v:-} ]]; then echo "$v"; return 0; fi
  # Fallback: branques de producció conegudes, de més nova a més antiga
  local cand
  for cand in 580.82.07 575.64.05 570.169 570.133.07 570.86.16; do
    if url_ok "$NVIDIA_BASE/$cand/NVIDIA-Linux-x86_64-$cand.run"; then echo "$cand"; return 0; fi
  done
  return 1
}

do_nvidia() {
  title "2. Driver NVIDIA .run (>= $MIN_NVIDIA_MAJOR)  [prioritat 2]"
  local ver run url major
  if ! ver="$(resolve_nvidia_ver)"; then
    warn "no s'ha pogut determinar cap versió de driver NVIDIA; grup omès"
    return 0
  fi
  major="${ver%%.*}"
  log "versió: $ver"
  if (( major < MIN_NVIDIA_MAJOR )); then
    warn "el driver detectat ($ver) és < $MIN_NVIDIA_MAJOR: NO serveix per a RTX 50xx (Blackwell). Fixa'n un amb NVIDIA_VER=..."
  fi

  run="$DEST/nvidia/NVIDIA-Linux-x86_64-$ver.run"
  url="$NVIDIA_BASE/$ver/NVIDIA-Linux-x86_64-$ver.run"

  if [[ -s $run ]]; then
    ok "$(basename "$run") ja hi és ($(human "$(stat -c%s "$run")"))"
  else
    fetch "$url" "$run" || { warn "descàrrega del driver NVIDIA fallida"; return 0; }
    chmod +x "$run"
    ok "$(basename "$run") baixat"
  fi
  # NVIDIA no publica SHA256 al costat del .run; deixem constància del hash local.
  log "sha256 local: $(sha256sum "$run" | cut -d' ' -f1)"
}

# --------------------------------------------------------------- 3. Docker
do_docker() {
  title "3. Imatges Docker  [prioritat 3]"
  local dir="$DEST/docker" img tar
  mkdir -p "$dir"
  for img in "${DOCKER_IMAGES[@]}"; do
    tar="$dir/$(echo "$img" | tr '/:' '__').tar"
    if [[ -s $tar ]]; then
      ok "$(basename "$tar") ja hi és ($(human "$(stat -c%s "$tar")"))"
      continue
    fi
    log "docker pull $img"
    if ! docker pull "$img" >/dev/null; then
      warn "no s'ha pogut fer pull de $img"
      continue
    fi
    log "docker save -> $(basename "$tar")"
    if docker save "$img" -o "$tar"; then
      ok "$(basename "$tar") ($(human "$(stat -c%s "$tar")"))"
    else
      warn "docker save ha fallat per a $img"
      rm -f "$tar"
    fi
  done
}

# ---------------------------------------------------------------- 4. Models
do_models() {
  title "4. Models GGUF  [prioritat 4 — només si hi ha espai i temps]"
  local dir="$DEST/models" entry name url out
  mkdir -p "$dir"
  for entry in "${GGUF_MODELS[@]}"; do
    name="${entry%%|*}"; url="${entry#*|}"; out="$dir/$name"
    if [[ -s $out ]]; then
      ok "$name ja hi és ($(human "$(stat -c%s "$out")"))"
      continue
    fi
    if ! url_ok "$url"; then
      warn "$name: la URL no respon (el repo de HF pot haver canviat de nom de fitxer). Revisa-ho a mà: $url"
      continue
    fi
    fetch "$url" "$out" || { warn "descàrrega de $name fallida"; continue; }
    ok "$name ($(human "$(stat -c%s "$out")"))"
  done
}

# ---------------------------------------------------------------- 5. Ollama
do_ollama() {
  title "5. Instal·lador d'Ollama  [prioritat 5]"
  local dir="$DEST/ollama"
  mkdir -p "$dir"

  if [[ -s $dir/install.sh ]]; then
    ok "install.sh ja hi és"
  else
    fetch "https://ollama.com/install.sh" "$dir/install.sh" \
      && chmod +x "$dir/install.sh" && ok "install.sh baixat" \
      || warn "no s'ha pogut baixar install.sh d'Ollama"
  fi

  local tgz="$dir/ollama-linux-amd64.tgz"
  if [[ -s $tgz ]]; then
    ok "$(basename "$tgz") ja hi és ($(human "$(stat -c%s "$tgz")"))"
  else
    fetch "https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tgz" "$tgz" \
      && ok "$(basename "$tgz") baixat ($(human "$(stat -c%s "$tgz")"))" \
      || warn "no s'ha pogut baixar el tarball d'Ollama"
  fi
}

# ------------------------------------------------------------- CHECKSUMS.txt
write_checksums() {
  title "6. CHECKSUMS.txt"
  local out="$DEST/CHECKSUMS.txt"
  {
    echo "# CIDET · IA en local — checksums del material offline"
    echo "# generat: $(date -Is)"
    echo "# verificació al destí:  cd offline && sha256sum -c CHECKSUMS.txt"
    echo
  } > "$out"
  ( cd "$DEST" && find . -type f ! -name CHECKSUMS.txt ! -name 'SHA256SUMS' -print0 \
      | sort -z | xargs -0 -r sha256sum >> "$out" )
  ok "$(grep -cv '^#\|^$' "$out") fitxers indexats a CHECKSUMS.txt"
}

# ------------------------------------------------------------------- resum
summary() {
  title "RESUM"
  local g total=0 sz
  printf '%-12s %12s   %s\n' "GRUP" "MIDA" "CONTINGUT"
  hr
  for g in iso nvidia docker models ollama; do
    sz=$(dir_size "$DEST/$g")
    total=$((total + sz))
    printf '%-12s %12s   %s\n' "$g" "$(human "$sz")" \
      "$(ls -1 "$DEST/$g" 2>/dev/null | tr '\n' ' ' | cut -c1-40)"
  done
  hr
  printf '%-12s %12s\n' "TOTAL" "$(human "$total")"
  echo
  printf '%sEl pen drive de dades ha de ser de %s≥ 64 GB%s i estar formatat en %sexFAT%s.\n' \
    "$c_bold" "$c_yel" "$c_reset$c_bold" "$c_yel" "$c_reset"
  printf '%sNO facis servir FAT32: la ISO i els GGUF passen dels 4 GB per fitxer.%s\n' "$c_dim" "$c_reset"
  echo
  if ((${#WARNINGS[@]})); then
    printf '%s%d avisos:%s\n' "$c_yel" "${#WARNINGS[@]}" "$c_reset"
    printf '  · %s\n' "${WARNINGS[@]}"
  else
    ok "cap avís: tot correcte"
  fi
  echo
  log "següent pas: docs/preparacio-pendrive.md"
}

# -------------------------------------------------------------------- main
usage() {
  sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 0
}

main() {
  while (($#)); do
    case $1 in
      --only)  ONLY="${ONLY} $2"; shift 2 ;;
      --skip)  SKIP="${SKIP} $2"; shift 2 ;;
      --dest)  DEST="$2"; shift 2 ;;
      -h|--help) usage ;;
      *) die "opció desconeguda: $1 (prova --help)" ;;
    esac
  done

  printf '%s\n' "$c_bold╔══════════════════════════════════════════════════════════════════════╗"
  printf '%s\n' "║  CIDET · IA en local — descàrrega del material offline                ║"
  printf '%s\n' "╚══════════════════════════════════════════════════════════════════════╝$c_reset"
  log "destí: $DEST"
  mkdir -p "$DEST"

  check_deps
  local t0=$SECONDS
  group_enabled iso    && do_iso
  group_enabled nvidia && do_nvidia
  group_enabled docker && do_docker
  group_enabled models && do_models
  group_enabled ollama && do_ollama
  write_checksums
  summary
  log "temps total: $(( (SECONDS - t0) / 60 )) min $(( (SECONDS - t0) % 60 )) s"
}

main "$@"
