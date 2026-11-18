# Migração dos dados do gabi-brain (rodar uma vez, na VPS)

Ordem importa: o cofre só pode ser commitado **depois** do `git-crypt init`, e o passo 3 confere a cifra **antes** do commit.

## 1. Exportar (só leitura)
```bash
cd ~/gabi-brain && git fetch -q origin exportar-markdown && git show origin/exportar-markdown:tools/exportar_markdown.py | sudo install -m 644 /dev/stdin /tmp/exportar_markdown.py
cd /tmp && sudo -u gabibrain bash -c 'umask 077; python3 -I /tmp/exportar_markdown.py /tmp/esper-export --banco /var/lib/gabi-brain/gabi.db'
sudo chown -R "$USER": /tmp/esper-export
```
Saída: contagem por pasta e a lista `caminho:linha` das linhas fora do cofre com cara de número/dinheiro (telefones também aparecem). Abra cada uma e decida: manter, apagar ou mover o número para `pessoal/cofre/`.

## 2. Preparar o cofre (git-crypt)
```bash
sudo apt-get install -y git-crypt
git clone git@github.com:resper1965/esper-brain.git /tmp/esper-brain && cd /tmp/esper-brain && git-crypt init
(umask 077; git-crypt export-key ~/esper-brain-gitcrypt.key)
base64 -w0 ~/esper-brain-gitcrypt.key; echo
```
Cole a linha base64 no Bitwarden como nota segura "esper-brain git-crypt" **agora**. Sem a chave, o cofre é irrecuperável. Para restaurar: `base64 -d > chave` e `git-crypt unlock chave`.

## 3. Copiar e conferir (ainda sem commit)
O `cp` sobrescreve `pendencias.md` e `people/_aprovados.md` do esqueleto — são só cabeçalhos, é esperado.
```bash
cp -r /tmp/esper-export/. /tmp/esper-brain/ && cd /tmp/esper-brain && git add -A
ok=1; n=0
for f in $(git ls-files pessoal/cofre/ | grep -v '/README.md$'); do
  n=$((n+1))
  git cat-file blob ":$f" | head -c 10 | grep -qa GITCRYPT || { echo "PARE: $f está em claro"; ok=0; }
done
if [ "$n" -ge 2 ] && [ "$ok" = 1 ] && git-crypt status pessoal/cofre/ >/dev/null; then echo "cofre cifrado OK ($n arquivos)"; else echo "PARE: NÃO faça commit"; fi
git status --short | head -40        # abra 3 fichas da família, 2 projetos e o cofre
```
Só siga para o passo 4 se apareceu `cofre cifrado OK (2 arquivos)` e nenhum `PARE`.

## 4. Publicar
```bash
cd /tmp/esper-brain && git commit -m "feat: dados migrados do gabi-brain" && git push
git show HEAD:pessoal/cofre/documentos.md | head -c 10 | od -c | head -1   # confirmação: \0 G I T C R Y P T \0
```

## 5. Limpar
```bash
sudo rm -rf /tmp/esper-export /tmp/exportar_markdown.py
rm -rf /tmp/esper-brain   # a chave continua em ~/esper-brain-gitcrypt.key (vai para o usuário do Hermes na etapa 3)
```

## Estado em 2026-11-18

**O que roda na VPS (Contabo, a mesma de sempre)**

| Peça | O que faz | Onde |
|---|---|---|
| `gabi-finance` | Dinheiro: Open Finance (mcp.ai), avisos no Telegram, MCP `gabi_finance` (porta 8082), painel "laudo" em `:8446` | `/opt/gabi-finance`, banco `/var/lib/gabi-finance/gabi.db` |
| `gabi-brain` | Coletor: agenda, e-mail (Gmail, Graph da ness), Teams, Paperless, atividades (Linear), avisos não financeiros; `GABI_SEM_FINANCEIRO=1` e `GABI_SEM_PESSOAL=1` | `/opt/gabi-brain`, clone `~ricardo/gabi-brain` na `main` |
| `esper-brain` | Este cérebro: a Gabi lê e grava pelo MCP `esper_brain` (sem shell); skills `capturar`, `retomar`, `salvar-sessao`, `digestao` (06:30) | clone `~ricardo/esper-brain` |
| Hermes | A Gabi (Telegram e WhatsApp), sem terminal nos canais | `~ricardo/.hermes` |

**Segredos (só onde estão; nunca os valores)**
- git-crypt do cofre: `~ricardo/.config/esper-brain/gitcrypt.key` (600) e no Bitwarden, nota "esper-brain git-crypt" (chave nova de 18/11; a de 17/11 se perdeu e o cofre foi recifrado).
- GitHub na VPS: só chaves de deploy (`~ricardo/.ssh/esper-brain` com escrita; `gabi-brain` e `gabi-finance` só leitura). O `gh` do root foi deslogado.
- Tokens MCP: Hermes no brain (id 3, sem `fin`/`propostas`/`projetos`); Hermes no finance (`GABI_FINANCE_TOKEN` em `~ricardo/.hermes/.env`).
- Google: `/etc/gabi/google.env` (5 contas de e-mail lendo; renovados gmail e esper.ws em 18/11). Telegram: `/etc/gabi/telegram.env` e `/etc/gabi-finance/telegram.env`.

**Em aberto**
- Nibo: o plano não dá chave de API; `gabi-finance-notas.timer` desligado. Avaliar o MCP do Nibo (`https://mcp-empresa.nibo.com.br/mcp`), só leitura.
- Chave do modelo (OpenRouter) e chave do agente GPT: com o Ricardo.
- Etapa 4: GBrain e Honcho contra este markdown (spec própria).
