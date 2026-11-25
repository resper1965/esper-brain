#!/usr/bin/env bash
# Testa tools/gravar.sh com um remoto local. Uso: bash tests/test_gravar.sh
set -euo pipefail
src="$(cd "$(dirname "$0")/.." && pwd)"
t="$(mktemp -d)"; trap 'rm -rf "$t"' EXIT
git init -q --bare -b main "$t/remoto.git"
git clone -q "$t/remoto.git" "$t/a" 2>/dev/null
cd "$t/a"; git checkout -q -b main 2>/dev/null || true; git config user.email t@t; git config user.name t
mkdir -p tools pessoal/cofre projetos; cp "$src/tools/gravar.sh" tools/
echo x > projetos/a.md; git add -A; git commit -qm init; git push -qu origin main 2>/dev/null
ok=0; falha() { echo "FALHOU: $*"; ok=1; }

echo "- ideia" >> projetos/a.md
out=$(tools/gravar.sh "teste: ideia" projetos/a.md) && [[ $out == gravado:* ]] || falha "gravação simples: $out"
[ "$(git -C "$t/remoto.git" log --oneline | wc -l)" = 2 ] || falha "push não chegou"

out=$(tools/gravar.sh "nada" projetos/a.md); [ "$out" = "nada a gravar" ] || falha "nada a gravar: $out"

tools/gravar.sh "x" ../fora 2>/dev/null && falha "aceitou caminho com .." || true
tools/gravar.sh "x" bruto/a 2>/dev/null && falha "aceitou bruto/" || true

echo "CPF 123" > pessoal/cofre/doc.md
if tools/gravar.sh "cofre" pessoal/cofre/doc.md 2>/dev/null; then falha "gravou cofre em texto claro"; fi
git diff --cached --quiet || falha "deixou o cofre no índice"

# concorrência: outro clone grava antes; o rebase resolve
git clone -q "$t/remoto.git" "$t/b" 2>/dev/null; cd "$t/b"; git config user.email t@t; git config user.name t
echo y > projetos/b.md; tools/gravar.sh "b" projetos/b.md >/dev/null || falha "clone b"
cd "$t/a"; echo "- outra" >> projetos/a.md
out=$(tools/gravar.sh "a de novo" projetos/a.md) && [[ $out == gravado:* ]] || falha "rebase com remoto à frente: $out"
[ -f projetos/b.md ] || falha "não trouxe o commit do outro clone"

# conflito: o outro clone muda a MESMA linha; a edição local não pode virar commit com marcas de conflito
cd "$t/b"; git pull -q 2>/dev/null; printf 'linha do b\n' > projetos/c.md; git add -A; git commit -qm c; git push -q 2>/dev/null
cd "$t/a"; git pull -q 2>/dev/null; cd "$t/b"; printf 'linha do b mudada\n' > projetos/c.md; tools/gravar.sh "b muda c" projetos/c.md >/dev/null || falha "b muda c"
cd "$t/a"; printf 'linha do a\n' > projetos/c.md
if tools/gravar.sh "a muda c" projetos/c.md 2>/dev/null; then falha "gravou com conflito"; fi
git -C "$t/remoto.git" show main:projetos/c.md | grep -q '<<<<<<<' && falha "marcas de conflito chegaram ao remoto"
grep -q '<<<<<<<' projetos/c.md && falha "deixou marcas de conflito no arquivo"
git stash list | grep -q . || falha "a edição local não ficou no stash"
[ $ok = 0 ] && echo "gravar.sh: todos os testes passaram"; exit $ok
