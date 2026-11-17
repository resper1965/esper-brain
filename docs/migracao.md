# Migração dos dados do gabi-brain (rodar uma vez, na VPS)

Ordem importa: o cofre só pode ser commitado **depois** do `git-crypt init`, senão vai em claro para o GitHub.

## 1. Exportar (só leitura)
```bash
cd ~/gabi-brain && git fetch -q origin exportar-markdown
git show origin/exportar-markdown:tools/exportar_markdown.py | sudo install -m 644 /dev/stdin /tmp/exportar_markdown.py
cd /tmp && sudo -u gabibrain bash -c 'umask 077; python3 /tmp/exportar_markdown.py /tmp/esper-export --banco /var/lib/gabi-brain/gabi.db'
sudo chown -R "$USER": /tmp/esper-export
```
Saída: contagem por pasta e a lista `caminho:linha` das linhas fora do cofre com cara de número/dinheiro. Abra cada uma e decida (manter, apagar ou mover para o cofre).

## 2. Preparar o cofre (git-crypt)
```bash
sudo apt-get install -y git-crypt
git clone git@github.com:resper1965/esper-brain.git /tmp/esper-brain && cd /tmp/esper-brain
git-crypt init
git-crypt export-key ~/esper-brain-gitcrypt.key && chmod 600 ~/esper-brain-gitcrypt.key
```
Guarde `~/esper-brain-gitcrypt.key` no Bitwarden ("esper-brain git-crypt") **agora**. Sem ela, o cofre é irrecuperável.

## 3. Copiar, conferir e publicar
```bash
cp -r /tmp/esper-export/. /tmp/esper-brain/
git add -A
git-crypt status pessoal/cofre/ | grep -v '^ *encrypted:' | grep -v 'README.md' && echo "PARE: cofre em claro" || echo "cofre cifrado OK"
git status --short | head -40        # abra 3 fichas da família, 2 projetos e o cofre
git commit -m "feat: dados migrados do gabi-brain" && git push
git show HEAD:pessoal/cofre/documentos.md | head -c 10 | od -c | head -1   # tem que começar com \0 G I T C R Y P T
```

## 4. Limpar
```bash
sudo rm -rf /tmp/esper-export /tmp/exportar_markdown.py
rm -rf /tmp/esper-brain   # a chave continua em ~/esper-brain-gitcrypt.key (vai para o usuário do Hermes na etapa 3)
```
