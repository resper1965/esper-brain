# Painel de temas (quadro estilo Trello)

App em `tools/painel/` (Starlette), servida num socket Unix (`/run/esper-painel/painel.sock`, pasta 0700 do `ricardo`) e publicada **só na Tailscale** pelo `tailscale serve` na porta 8448. Sem porta TCP. Quem entra: o login da Tailscale listado em `ESPER_PAINEL_LOGINS`. Escrita: POST JSON com `Origin` de `ESPER_PAINEL_ORIGENS`; toda mudança termina num commit pelo `tools/gravar.sh` (mensagem `painel: ...`).

## Instalar (root, na VPS)
```bash
umask 022
sudo -u ricardo -H bash -lc 'cd ~/esper-brain && git pull -q && ~/.local/share/esper-brain-mcp/bin/python -m pip install -q -r tools/requirements-mcp.txt'
# seu login na Tailscale (o do PC):
tailscale whois 100.81.153.100 | grep -i login
cat > /etc/esper-painel.env <<'X'
ESPER_PAINEL_LOGINS=<seu-login-da-tailscale>
ESPER_PAINEL_ORIGENS=https://srv-hermes.tail985643.ts.net:8448
X
chmod 600 /etc/esper-painel.env
install -m 644 /home/ricardo/esper-brain/deploy/painel/esper-painel.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now esper-painel
tailscale serve --bg --https=8448 unix:/run/esper-painel/painel.sock
curl -s -o /dev/null -w "%{http_code}\n" --unix-socket /run/esper-painel/painel.sock http://x/api/quadro   # 403 = vivo (sem login)
```
Abrir: https://srv-hermes.tail985643.ts.net:8448

## Atualizar
`git pull` no clone e `systemctl restart esper-painel`.

## Problemas
| Sintoma | Causa | O que fazer |
|---|---|---|
| 403 "proibido" no navegador | login fora de `ESPER_PAINEL_LOGINS` | conferir com `tailscale whois <ip do aparelho>` e corrigir o env; restart |
| 403 "origem" ao salvar | endereço diferente de `ESPER_PAINEL_ORIGENS` | acrescentar o endereço usado (separado por vírgula); restart |
| 502 ao salvar | o `gravar` falhou (pull/push) | `journalctl -u esper-painel -n 30`; a edição fica no disco e entra no próximo gravar |
