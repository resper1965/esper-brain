#!/usr/bin/env bash
# Comando único da Gabi na VPS.
#   gabi.sh estado                       só leitura: o que está desatualizado ou parado (sai com 3 se achar problema)
#   gabi.sh atualizar [--sem-reiniciar]  puxa os repositórios e recompõe o SOUL e a config do Hermes, na ordem certa
# Rodando como root, o trabalho é feito como o usuário `ricardo` e só o restart do gateway fica com o root.
# Variáveis: GABI_HOME (padrão: home do ricardo se rodar como root, senão $HOME), GABI_SIMULAR=1 (só mostra o que faria). Nunca lê nem mostra chave ou token.
set -uo pipefail

HOME_G="${GABI_HOME:-}"
if [ -z "$HOME_G" ]; then
  if [ "$(id -u)" = 0 ] && id ricardo >/dev/null 2>&1; then HOME_G="$(getent passwd ricardo | cut -d: -f6)"; else HOME_G="$HOME"; fi
fi
EB="$HOME_G/esper-brain"; GB="$HOME_G/gabi-brain"; GF="$HOME_G/gabi-finance"
SOUL="$HOME_G/.hermes/SOUL.md"; CFG="$HOME_G/.hermes/config.yaml"; ENVF="$HOME_G/.hermes/.env"
SIMULAR="${GABI_SIMULAR:-0}"
ANTIGO='projeto_(ligar|criar|listar|ver|atualizar|pessoa|gasto|fato|fatos|anexar)|anexo_recentes|familia_(listar|consultar|atualizar_contato|registrar_pessoa|registrar_pet|propor_documento)'

rodar() {
  if [ "$SIMULAR" = 1 ]; then echo "[simulado] $*"; else "$@"; fi
}

estado() {
  local problema=0 r d atras
  for r in esper-brain gabi-brain gabi-finance; do
    d="$HOME_G/$r"
    if [ ! -d "$d/.git" ]; then echo "$r: não encontrado"; continue; fi
    echo "$r: $(git -C "$d" rev-parse --abbrev-ref HEAD 2>/dev/null) @ $(git -C "$d" rev-parse --short HEAD 2>/dev/null)"
    git -C "$d" fetch -q 2>/dev/null || true
    atras=$(git -C "$d" rev-list --count 'HEAD..@{u}' 2>/dev/null || echo 0)
    if [ "${atras:-0}" -gt 0 ]; then echo "  $atras commit(s) atrás do remoto (rode: gabi.sh atualizar)"; problema=1; fi
  done
  if [ ! -f "$SOUL" ]; then
    echo "SOUL: arquivo não encontrado ($SOUL)"; problema=1
  else
    if grep -Eq "$ANTIGO" "$SOUL"; then echo "SOUL desatualizado: ainda ensina ferramentas que migraram (rode: gabi.sh atualizar)"; problema=1; fi
    if ! grep -q '<!-- esper-brain:inicio -->' "$SOUL"; then echo "SOUL sem a seção do esper-brain (rode: gabi.sh atualizar)"; problema=1; fi
  fi
  if [ -f "$EB/entrada.md" ] && grep -q '^- ' "$EB/entrada.md"; then
    local ult agora; agora=$(date +%s)
    ult=$(git -C "$EB" log -1 --format=%ct --grep='^organizar ' 2>/dev/null || true)
    if [ -z "$ult" ] || [ $((agora - ult)) -gt $((36 * 3600)) ]; then
      echo "organizar sem gravar há mais de 36 h e a entrada tem pedaços esperando (veja: hermes cron list)"; problema=1
    fi
  fi
  if [ -f "$CFG" ]; then
    grep -q '^  esper_brain:' "$CFG" && echo "config: esper_brain ligado" || echo "config: esper_brain AUSENTE"
    grep -q '^  ness_know:' "$CFG" && echo "config: ness_know ligado" || echo "config: ness_know não ligado"
  fi
  if command -v hermes >/dev/null 2>&1 && [ "$SIMULAR" != 1 ]; then echo "--- rotinas"; hermes cron list 2>&1 | head -20 || true; fi
  [ "$problema" = 0 ] && echo "tudo certo" || return 3
}

atualizar() {
  local reiniciar=1 falhas=0 a r d py
  for a in "$@"; do [ "$a" = "--sem-reiniciar" ] && reiniciar=0; done
  # como root: faz o trabalho como ricardo e reinicia o gateway aqui
  if [ "$(id -u)" = 0 ] && [ -z "${GABI_AS_USER:-}" ] && [ "$SIMULAR" != 1 ] && id ricardo >/dev/null 2>&1; then
    sudo -u ricardo -H env GABI_AS_USER=1 bash "$0" atualizar --sem-reiniciar || falhas=1
    [ "$reiniciar" = 1 ] && { systemctl restart hermes-gateway || { echo "FALHOU: restart do gateway"; falhas=1; }; }
    sudo -u ricardo -H env GABI_AS_USER=1 bash "$0" estado || falhas=1
    echo "Falta: mande /new no Telegram"
    return "$falhas"
  fi
  passo() { local nome="$1"; shift; "$@" || { echo "FALHOU: $nome"; falhas=1; }; }

  for r in esper-brain gabi-brain gabi-finance; do
    d="$HOME_G/$r"
    if [ -d "$d/.git" ]; then passo "pull $r" rodar git -C "$d" pull -q --ff-only; else echo "$r: não encontrado"; fi
  done
  [ -f "$GB/deploy/instalar-hermes-soul.sh" ] && passo "SOUL base" rodar bash "$GB/deploy/instalar-hermes-soul.sh"
  [ -f "$GF/deploy/hermes/editar_soul.py" ] && passo "SOUL dinheiro" rodar python3 "$GF/deploy/hermes/editar_soul.py" --data "$(date +%Y-%m-%d-%H%M)"
  if [ -f "$CFG" ] && [ -d "$EB" ]; then
    if grep -qs '^NESS_KNOW_TOKEN=' "$ENVF"; then
      passo "ness_know" rodar python3 "$EB/deploy/hermes/ligar_ness_know.py" "$CFG" --gravar
    fi
    py=$(python3 -c "import sys,yaml; print((yaml.safe_load(open(sys.argv[1])).get('mcp_servers') or {}).get('esper_brain',{}).get('command',''))" "$CFG" 2>/dev/null || true)
    if [ -n "$py" ]; then
      passo "config esper_brain" rodar python3 "$EB/deploy/hermes/configurar_hermes.py" "$CFG" --python "$py" --eb "$EB" --gravar
    fi
  fi
  if [ "$reiniciar" = 1 ]; then
    if [ "$(id -u)" = 0 ]; then passo "restart do gateway" rodar systemctl restart hermes-gateway
    else passo "restart do gateway" rodar sudo systemctl restart hermes-gateway; fi
  fi
  if [ "$SIMULAR" = 1 ]; then echo "[simulado] gabi.sh estado"
  else estado || falhas=1; fi
  [ "$reiniciar" = 1 ] && echo "Falta: mande /new no Telegram"
  return "$falhas"
}

case "${1:-}" in
  estado) estado; exit $? ;;
  atualizar) shift; atualizar "$@"; exit $? ;;
  *) echo "uso: gabi.sh estado | atualizar [--sem-reiniciar]" >&2; exit 2 ;;
esac
