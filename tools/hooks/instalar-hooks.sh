#!/bin/sh
# Instala os hooks versionados deste repo em .git/hooks.
# Rode uma vez por clone: sh tools/hooks/instalar-hooks.sh
set -eu

raiz=$(git rev-parse --show-toplevel)
cd "$raiz"

for hook in tools/hooks/pre-commit; do
	nome=$(basename "$hook")
	cp "$hook" ".git/hooks/$nome"
	chmod +x ".git/hooks/$nome"
	echo "instalado: .git/hooks/$nome"
done

echo "pronto."
