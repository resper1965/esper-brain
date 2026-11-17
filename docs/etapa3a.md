# Etapa 3A: a Gabi passa a usar o esper-brain

Mesma VPS, sem serviço novo. Ao fim: a Gabi lê o cérebro em toda conversa, anota em temas (`capturar`), retoma temas (`retomar`), salva a conversa (`salvar-sessao`) e grava com commit e push. Projetos e família saem do `gabi_brain` do Hermes (os dados ficam no banco; nada é apagado).

Tudo como **root**. O Ricardo roda; o Claude guia. Nenhum segredo aparece na tela.

```bash
HUSER=ricardo; HOME_H=/home/ricardo; EB=$HOME_H/esper-brain; D=$(date +%F-%H%M)
```

## Passo 0: o Hermes tem terminal nos canais?

```bash
python3 - <<'PY'
import yaml
c = yaml.safe_load(open("/home/ricardo/.hermes/config.yaml"))
for p, ts in (c.get("platform_toolsets") or {}).items():
    print(p, "->", ts)
PY
```

**Verificação:** `telegram` e `whatsapp` incluem o toolset de terminal (`terminal`, `hermes-telegram`/`hermes-whatsapp` ou equivalente que o inclua). Se não incluírem, **pare** e me mande a saída.

## Passo 1: chave de deploy (escrita só no esper-brain)

```bash
sudo -u "$HUSER" ssh-keygen -q -t ed25519 -N '' -C 'gabi-vps esper-brain' -f "$HOME_H/.ssh/esper-brain"
cat "$HOME_H/.ssh/esper-brain.pub"
```

No GitHub: `resper1965/esper-brain` → Settings → Deploy keys → **Add deploy key**. Título `gabi-vps`, cole a linha `.pub`, marque **Allow write access**.

```bash
sudo -u "$HUSER" tee -a "$HOME_H/.ssh/config" >/dev/null <<'CFG'

Host github-esper-brain
  HostName github.com
  User git
  IdentityFile ~/.ssh/esper-brain
  IdentitiesOnly yes
CFG
chmod 600 "$HOME_H/.ssh/config"
sudo -u "$HUSER" -H ssh -o StrictHostKeyChecking=accept-new -T github-esper-brain 2>&1 | head -2
```

**Verificação:** `Hi resper1965/esper-brain! You've successfully authenticated...`

## Passo 2: clone, chave do cofre e destravar

```bash
sudo -u "$HUSER" -H git clone -q github-esper-brain:resper1965/esper-brain.git "$EB"
install -d -o "$HUSER" -g "$HUSER" -m 700 "$HOME_H/.config/esper-brain"
echo "cole a linha base64 da nota 'esper-brain git-crypt' do Bitwarden e tecle Enter (não aparece na tela):"
read -rs K; printf '%s' "$K" | base64 -d > "$HOME_H/.config/esper-brain/gitcrypt.key"; unset K
chown "$HUSER:$HUSER" "$HOME_H/.config/esper-brain/gitcrypt.key"; chmod 600 "$HOME_H/.config/esper-brain/gitcrypt.key"
sudo -u "$HUSER" -H bash -c "cd '$EB' && git-crypt unlock ~/.config/esper-brain/gitcrypt.key && git config user.name Gabi && git config user.email gabi@esper-brain.local && git config pull.rebase true"
sudo -u "$HUSER" -H python3 - "$EB" <<'PY'
import pathlib, sys
fs = [f for f in pathlib.Path(sys.argv[1], "pessoal/cofre").rglob("*") if f.is_file() and f.name != "README.md"]
cifrados = [f for f in fs if f.read_bytes()[:9] == b"\x00GITCRYPT"]
print(f"cofre: {len(fs)} arquivos, {len(cifrados)} ainda cifrados (esperado 0)")
PY
sudo -u "$HUSER" -H bash -c "cd '$EB' && tools/gravar.sh 'teste' hot.md"
```

**Verificação:** `cofre: N arquivos, 0 ainda cifrados` e `nada a gravar`. Se o unlock disser que a chave é inválida, a linha colada veio incompleta: rode de novo só o `read -rs` e o `unlock`.

## Passo 3: nada ficou para trás desde a exportação

Exporta de novo o banco do brain (só leitura) e compara **só nomes de arquivo** com o clone:

```bash
install -m 644 "$EB/tools/exportar_markdown.py" /tmp/exportar_markdown.py
rm -rf /tmp/esper-delta
runuser -u gabibrain -- python3 /tmp/exportar_markdown.py /tmp/esper-delta >/dev/null
diff -rq /tmp/esper-delta "$EB" | grep -v "^Only in $EB" | sed "s#/tmp/esper-delta#NOVO#; s#$EB#CLONE#"
```

**Verificação:** nenhuma linha = nada mudou no brain desde a exportação. Linhas `Files ... differ` ou `Only in NOVO` = algo entrou ou mudou depois: me mande **só a lista** (sem conteúdo) e eu digo o que trazer. Depois: `rm -rf /tmp/esper-delta /tmp/exportar_markdown.py`.

## Passo 4: skills no Hermes

```bash
sudo -u "$HUSER" ln -sfn "$EB/skills" "$HOME_H/.hermes/skills/esper-brain"
ls "$HOME_H/.hermes/skills/esper-brain/"
sudo -u "$HUSER" -H bash -lc 'hermes skills list 2>/dev/null | grep -E "capturar|retomar|salvar-sessao"'
```

**Verificação:** as três skills aparecem (e não estão em `skills.platform_disabled` do Telegram/WhatsApp).

## Passo 5: SOUL e ferramentas do gabi_brain

```bash
sudo -u "$HUSER" cp -p "$HOME_H/.hermes/config.yaml" "$HOME_H/.hermes/config.yaml.bak-antes-esper-brain-$D"
sudo -u "$HUSER" -H python3 "$EB/deploy/hermes/tirar_ferramentas.py" "$HOME_H/.hermes/config.yaml"
```

Simulação ok (`ainda no gabi_brain: nenhuma`; ficam `familia_vencimentos` e as `atividade_*`)? Então grave e instale o SOUL:

```bash
sudo -u "$HUSER" -H python3 "$EB/deploy/hermes/tirar_ferramentas.py" "$HOME_H/.hermes/config.yaml" --gravar
sudo -u "$HUSER" -H python3 "$EB/deploy/hermes/instalar_soul.py" --data "$D"
grep -nE 'projeto_[a-z]+|familia_(listar|consultar|registrar|atualizar|propor)' "$HOME_H/.hermes/SOUL.md" | head
systemctl restart hermes-gateway; sleep 5; systemctl is-active hermes-gateway
```

O `grep` lista instruções antigas do SOUL que ainda citam ferramentas de projeto/família: me mande (só os números de linha e nomes) para eu ajustar. Depois mande `/new` no Telegram e no WhatsApp.

## Passo 6: aceite

1. Telegram: `teste: anotar que o cérebro novo está no ar` → a Gabi pergunta se é tema novo; responda `novo, "Teste esper-brain"` → `anotado em Teste esper-brain`.
2. GitHub: o commit `capturar(teste-esper-brain): ...` aparece no `esper-brain`.
3. Telegram: `como está o teste esper-brain?` → briefing com a ideia de hoje.
4. Telegram: `salva a sessão` → resumo do que salvou; `diario/AAAA/MM-DD.md` aparece no GitHub.
5. Pergunta de família (ex.: "quando é o aniversário da Louise?") → resposta vinda do markdown.

Depois do aceite, apague o tema de teste no seu clone local e dê push.

## Volta

```bash
sudo -u "$HUSER" cp -p "$HOME_H/.hermes/config.yaml.bak-antes-esper-brain-$D" "$HOME_H/.hermes/config.yaml"
sudo -u "$HUSER" cp -p "$HOME_H/.hermes/SOUL.md.bak-antes-esper-brain-$D" "$HOME_H/.hermes/SOUL.md"
rm "$HOME_H/.hermes/skills/esper-brain"
systemctl restart hermes-gateway
```
O clone e a chave podem ficar; para tirar o acesso, apague a deploy key no GitHub.
