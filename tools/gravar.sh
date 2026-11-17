#!/usr/bin/env bash
# Grava no esper-brain: trava, pull --rebase, add, confere o cofre, commit, push.
# Uso: tools/gravar.sh "mensagem do commit" caminho [caminho...]
# Saída 0 = gravado e enviado (ou nada a gravar). Qualquer outra = NÃO diga "anotado".
set -euo pipefail
raiz="$(cd "$(dirname "$0")/.." && pwd)"
cd "$raiz"
[ $# -ge 2 ] || { echo "uso: tools/gravar.sh \"mensagem\" caminho [caminho...]" >&2; exit 2; }
msg="$1"; shift
for p in "$@"; do
  case "$p" in
    /*|*..*|bruto/*|.git/*) echo "caminho recusado: $p" >&2; exit 2;;
  esac
done
exec 9>"$raiz/.git/gravar.lock"
flock -w 60 9 || { echo "outra gravação em andamento há mais de 60 s" >&2; exit 3; }

git pull --rebase --autostash -q >/dev/null 2>&1 || { echo "falhou: git pull --rebase (nada gravado)" >&2; git rebase --abort 2>/dev/null || true; exit 4; }
git add -- "$@"
if git diff --cached --quiet; then echo "nada a gravar"; exit 0; fi

# Cofre: todo arquivo de pessoal/cofre/ (exceto README.md) tem de estar cifrado no índice.
while IFS= read -r f; do
  case "$f" in pessoal/cofre/README.md) continue;; pessoal/cofre/*) ;; *) continue;; esac
  if ! git cat-file -p ":$f" 2>/dev/null | head -c 10 | grep -q GITCRYPT; then
    git reset -q -- "$@"
    echo "recusado: $f iria em texto claro (clone sem git-crypt unlock?). Nada gravado." >&2
    exit 5
  fi
done < <(git diff --cached --name-only)

git commit -q -m "$msg"
h="$(git rev-parse --short HEAD)"
if ! git push -q 2>/dev/null; then
  git pull --rebase -q >/dev/null 2>&1 && git push -q 2>/dev/null || { echo "gravado só local ($h): push falhou; tento de novo na próxima gravação" >&2; exit 6; }
  h="$(git rev-parse --short HEAD)"
fi
echo "gravado: $h"
