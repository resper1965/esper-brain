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
