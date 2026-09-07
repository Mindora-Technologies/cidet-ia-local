#!/usr/bin/env bash
# =============================================================================
#  CIDET · IA en local — aixeca la demo sencera i la verifica
# -----------------------------------------------------------------------------
#  D'una màquina neta amb Docker i Ollama a l'assistent responent la pregunta
#  canònica del curs, sense tocar res més.
#
#     ./scripts/demo-up.sh                 # tot
#     ./scripts/demo-up.sh --sense-ingesta # si ja s'ha indexat abans
#     ./scripts/demo-up.sh --reconstrueix  # esborra volums i torna a començar
#     ./scripts/demo-up.sh --model qwen3:14b
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
DEMO_DIR="$REPO_DIR/demo"
COMPOSE=(docker compose -f "$DEMO_DIR/docker-compose.yml")

# Compte: un apòstrof dins de "${VAR:-...}" obre una cadena per a bash i
# desincronitza el parseig de tot el fitxer. Es defineix a part.
PREGUNTA_PER_DEFECTE="La comanda 4521 de Ferreteria Puig està en garantia? I on és l'enviament?"
PREGUNTA="${PREGUNTA:-$PREGUNTA_PER_DEFECTE}"
FER_INGESTA=1
RECONSTRUEIX=0
MODEL="${OLLAMA_MODEL:-qwen3:8b}"
EMBED="${EMBED_MODEL:-qwen3-embedding:0.6b}"

c_reset=$'\033[0m'; c_bold=$'\033[1m'; c_grn=$'\033[32m'
c_yel=$'\033[33m'; c_red=$'\033[31m'; c_cya=$'\033[36m'; c_dim=$'\033[2m'
log()  { printf '%s[·]%s %s\n' "$c_cya" "$c_reset" "$*"; }
ok()   { printf '%s[✔]%s %s\n' "$c_grn" "$c_reset" "$*"; }
warn() { printf '%s[!]%s %s\n' "$c_yel" "$c_reset" "$*" >&2; }
die()  { printf '%s[✘]%s %s\n' "$c_red" "$c_reset" "$*" >&2; exit 1; }
pas()  { printf '\n%s▶ %s%s\n' "$c_bold" "$*" "$c_reset"; }

while (($#)); do
  case $1 in
    --sense-ingesta) FER_INGESTA=0; shift ;;
    --reconstrueix)  RECONSTRUEIX=1; shift ;;
    --model)         MODEL="$2"; shift 2 ;;
    --pregunta)      PREGUNTA="$2"; shift 2 ;;
    -h|--help)       sed -n '2,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "opció desconeguda: $1" ;;
  esac
done

# ------------------------------------------------------------ 0. requisits
pas "0/6 · Requisits"
command -v docker >/dev/null || die "cal Docker"
docker info >/dev/null 2>&1 || die "el dimoni de Docker no respon (o no tens permisos: usermod -aG docker \$USER)"
docker compose version >/dev/null 2>&1 || die "cal el plugin docker compose"
command -v ollama  >/dev/null || die "cal Ollama (mira c1/install-server.md §6)"
curl -fsS --max-time 5 "${OLLAMA_URL:-http://localhost:11434}/api/tags" >/dev/null \
  || die "Ollama no respon a ${OLLAMA_URL:-http://localhost:11434}"
ok "docker, docker compose i ollama"

PY="$REPO_DIR/.venv/bin/python"
[[ -x $PY ]] || PY="$(command -v python3)"
[[ -n $PY ]] || die "cal python3"
"$PY" -c "import httpx, psycopg2, sqlglot, langgraph" 2>/dev/null \
  || die "falten dependències de Python. Instal·la-les amb:
     python -m venv .venv && .venv/bin/pip install -r demo/requirements.txt"
ok "dependències de Python"

for m in "$MODEL" "$EMBED"; do
  if ollama list | awk 'NR>1{print $1}' | grep -qx "$m"; then
    ok "model $m"
  else
    warn "falta el model $m — el baixo ara"
    ollama pull "$m" || die "no s'ha pogut baixar $m"
  fi
done

# --------------------------------------------------------------- 1. .env
pas "1/6 · Configuració"
if [[ ! -f $DEMO_DIR/.env ]]; then
  cp "$DEMO_DIR/.env.example" "$DEMO_DIR/.env"
  # Contrasenyes aleatòries: el .env.example en porta de reconeixibles a posta.
  CLAU_API="$(head -c 18 /dev/urandom | base64 | tr -d '/+=' | head -c 24)"
  CLAU_DB="$(head -c 18 /dev/urandom | base64 | tr -d '/+=' | head -c 24)"
  sed -i "s|^API_KEY=.*|API_KEY=$CLAU_API|; s|canvia_aquesta_contrasenya|$CLAU_DB|g" \
      "$DEMO_DIR/.env"
  ok ".env creat a partir de .env.example, amb credencials generades"
else
  ok ".env ja existeix (no el toco)"
fi
set -a; . "$DEMO_DIR/.env"; set +a
export OLLAMA_MODEL="$MODEL"

# La contrasenya del rol de només lectura ha de quadrar amb el DSN.
CONTRASENYA_RO="$(sed -n 's|^POSTGRES_DSN=postgresql://assistent_ro:\([^@]*\)@.*|\1|p' "$DEMO_DIR/.env")"

# ------------------------------------------------------------ 2. dades
pas "2/6 · Dades de la demo"
if [[ ! -f $DEMO_DIR/db/postgres-init.sql ]]; then
  log "generant la base de dades…"
  "$PY" "$DEMO_DIR/db/generar_dades.py"
fi
if ! compgen -G "$DEMO_DIR/corpus/*.pdf" >/dev/null; then
  log "generant el corpus documental…"
  "$PY" "$DEMO_DIR/generar_corpus.py"
fi
ok "$(ls "$DEMO_DIR"/corpus/*.pdf "$DEMO_DIR"/corpus/*.docx 2>/dev/null | wc -l) documents · $(du -h "$DEMO_DIR/db/postgres-init.sql" | cut -f1) de SQL"

# ------------------------------------------------------- 3. contenidors
pas "3/6 · Contenidors"
if ((RECONSTRUEIX)); then
  warn "--reconstrueix: esborrant volums (es perden les dades locals)"
  "${COMPOSE[@]}" down -v --remove-orphans || true
fi
"${COMPOSE[@]}" up -d

log "esperant que tot estigui healthy…"
for servei in qdrant postgres api; do
  cid="$("${COMPOSE[@]}" ps -q "$servei")"
  [[ -n $cid ]] || die "el servei $servei no s'ha creat"
  for i in $(seq 1 60); do
    estat="$(docker inspect -f '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo starting)"
    [[ $estat == healthy ]] && break
    [[ $estat == unhealthy ]] && {
      "${COMPOSE[@]}" logs --tail 20 "$servei"
      die "$servei ha quedat unhealthy"
    }
    sleep 2
  done
  [[ ${estat:-} == healthy ]] || die "$servei no ha arribat a healthy en 120 s"
  ok "$servei healthy"
done

# El rol de només lectura porta la contrasenya del .sql; l'alineem amb el .env.
if [[ -n ${CONTRASENYA_RO:-} ]]; then
  docker exec -i "$("${COMPOSE[@]}" ps -q postgres)" \
    psql -q -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-distribuidora}" \
    -c "ALTER ROLE assistent_ro WITH PASSWORD '$CONTRASENYA_RO';" >/dev/null
  ok "contrasenya del rol assistent_ro sincronitzada amb el .env"
fi

# ----------------------------------------------------------- 4. ingesta
pas "4/6 · Ingesta del corpus"
if ((FER_INGESTA)); then
  "$PY" "$DEMO_DIR/rag/ingest.py" --reset
else
  log "--sense-ingesta: em salto la indexació"
fi

# ------------------------------------------------- 5. comprovació de fonts
pas "5/6 · Comprovació de les tres fonts"
DEMO_DIR="$DEMO_DIR" "$PY" "$SCRIPT_DIR/comprova-fonts.py" \
  || die "alguna font no respon; mira la sortida de sobre"

# -------------------------------------------------------- 6. la pregunta
pas "6/6 · La pregunta canònica"
printf '%s  «%s»%s\n\n' "$c_dim" "$PREGUNTA" "$c_reset"
RESPOSTA="$("$PY" "$DEMO_DIR/rag/agent.py" "$PREGUNTA")"
echo "$RESPOSTA"

# La resposta ha de creuar les tres fonts. Ho comprovem de veritat.
# Nota de bash: «arr+=(...)» és una assignació i NO es pot posar a la dreta
# d'un «||» -- el shell hi veu un comandament i peta amb «unexpected token (».
falten=()
comprova() {   # comprova <patró> <què és>
  grep -qiE "$1" <<<"$RESPOSTA" || falten+=("$2")
}
comprova "24 mesos|24 mes|dos anys|2 anys"  "el termini de 24 mesos (documents)"
comprova "2025-03-12|12 de març"            "la data de la comanda (SQL)"
comprova "granollers"                       "la ubicació de l'enviament (API)"
comprova "en garantia|està coberta"         "el veredicte de garantia"

echo
if ((${#falten[@]})); then
  warn "la resposta no cobreix: ${falten[*]}"
  warn "Els models petits varien entre execucions. Torna-ho a provar, o fes servir"
  warn "un model més gran:  ./scripts/demo-up.sh --model qwen3:14b"
  exit 1
fi

printf '%s╔════════════════════════════════════════════════════════════════════╗\n' "$c_grn"
printf '║  La demo respon creuant les TRES fonts: documents + SQL + API.      ║\n'
printf '╚════════════════════════════════════════════════════════════════════╝%s\n' "$c_reset"
echo
log "Open WebUI:      http://localhost:${WEBUI_PORT:-3000}"
log "Consola Qdrant:  http://localhost:${QDRANT_PORT:-6333}/dashboard"
log "API i docs:      http://localhost:${API_PORT:-8080}/docs"
log "Agent en CLI:    .venv/bin/python demo/rag/agent.py \"la teva pregunta\""
log "Aturar-ho tot:   docker compose -f demo/docker-compose.yml down"
