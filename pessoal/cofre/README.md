# Cofre

Tudo nesta pasta, menos este README, é cifrado com **git-crypt** antes de ir para o GitHub.

- `documentos.md` — números de documento da família e dos bens (CPF, RG, passaporte, CNH, RENAVAM), com `paperless:N`.
- `empresas.md` — CNPJ das empresas (IE, IM e certificados entram à mão).

**Chave:** guardada no Bitwarden ("esper-brain git-crypt") e na VPS, legível só pelo usuário do Hermes.
**Destravar numa máquina nova:** `git-crypt unlock /caminho/da/chave`.
**Conferir antes de todo commit que mexa aqui:** o laço do passo 3 de `docs/migracao.md` (lê o blob do índice e exige o cabeçalho `GITCRYPT`).
