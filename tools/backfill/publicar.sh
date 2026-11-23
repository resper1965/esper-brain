#!/usr/bin/env bash
# Fase 3 do backfill: varre e faz um commit por tipo na branch backfill. Roda na raiz do clone ~/esper-brain-backfill.
set -euo pipefail
[ "$(git rev-parse --abbrev-ref HEAD)" = backfill ] || { echo "não estou na branch backfill"; exit 1; }
git add -A -- people empresas projetos
mapfile -d '' -t mudados < <(git diff --cached --name-only -z --diff-filter=d -- people empresas projetos)
[ "${#mudados[@]}" -gt 0 ] || { echo "nada a publicar"; exit 0; }
python3 tools/backfill/varrer.py "${mudados[@]}"
for tipo in people empresas projetos; do
  if ! git diff --cached --quiet -- "$tipo"; then
    git commit -q -m "backfill: propostas em $tipo/ (90 dias de e-mail, agenda, contatos, Paperless)" -- "$tipo"
  fi
done
git -c push.negotiate=true push -q -u origin backfill
git log --oneline main..backfill
