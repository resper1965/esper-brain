# Etapa 3B: digestão diária (06:30)

O gabi-brain já coleta agenda, e-mail (Gmail e Graph da ness), Teams e convites; por ora **ele é o coletor** (o `gabi-coletor` separado fica para quando o brain for enxugado). A digestão é uma rotina do Hermes que lê essas fontes pelo MCP `gabi_brain` (só leitura) e escreve no esper-brain pelo MCP `esper_brain`: `hot.md`, pendências novas do Ricardo e uma linha no diário. Instruções: `skills/digestao/SKILL.md`.

Tudo como **root**. O Ricardo roda; o Claude guia.

## Passo 1: atualizar o clone e o MCP

```bash
HUSER=ricardo; HOME_H=/home/ricardo; EB=$HOME_H/esper-brain; D=$(date +%F-%H%M)
PYM="$HOME_H/.local/share/esper-brain-mcp/bin/python"
sudo -u "$HUSER" -H git -C "$EB" pull -q
ls "$HOME_H/.hermes/skills/esper-brain/"
sudo -u "$HUSER" cp -p "$HOME_H/.hermes/config.yaml" "$HOME_H/.hermes/config.yaml.bak-antes-3b-$D"
sudo -u "$HUSER" -H python3 "$EB/deploy/hermes/configurar_hermes.py" "$HOME_H/.hermes/config.yaml" --python "$PYM" --eb "$EB" --gravar
systemctl restart hermes-gateway; sleep 8; systemctl is-active hermes-gateway
```

**Verificação:** a pasta de skills lista `digestao`; `esper_brain: ferramentas novas no include: ['reescrever_hot']`; `active`.

## Passo 2: ferramentas do gabi_brain que a digestão usa

```bash
python3 - <<'PY'
import yaml
inc = yaml.safe_load(open("/home/ricardo/.hermes/config.yaml"))["mcp_servers"]["gabi_brain"]["tools"]["include"]
for t in ["agenda_listar", "email_listar", "email_ler", "teams_pendentes", "promessas_candidatas", "atividade_listar",
          "olhar_a_frente", "familia_vencimentos", "documentos_vencimentos"]:
    print(("ok    " if t in inc else "FALTA ") + t)
PY
```

Faltou alguma? A digestão pula e anota "falhou"; me mande a lista se quiser incluí-las.

## Passo 3: criar a rotina (pelo Telegram, `/new` antes)

Mande à Gabi:

> Crie uma rotina diária às 06:30 (America/Sao_Paulo) chamada `digestao-cerebro` com este prompt: "Use a skill digestao do esper-brain e siga exatamente. Responda só a linha final." Entregue no Telegram.

Depois: `roda a digestão agora`. Confira no GitHub o commit `digestão AAAA-MM-DD` com `hot.md` e `diario/`.

## Volta
Peça à Gabi para pausar ou apagar a rotina `digestao-cerebro`; `config.yaml.bak-antes-3b-$D` desfaz o include.
