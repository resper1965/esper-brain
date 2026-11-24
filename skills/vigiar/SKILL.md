---
name: vigiar
description: Avisa o Ricardo, sem ele pedir, do que pede atenção nos temas do esper-brain — prazos vencidos ou chegando, temas parados, sem próximo passo, entrada esquecida. Use quando as rotinas "vigiar-diario" (08:40) ou "vigiar-semanal" (segunda 08:50) rodarem, ou quando ele perguntar "o que está atrasado?", "o que precisa de atenção?".
---
# Vigiar

Só lê; **nunca grava nem muda tema**: avisa e, no máximo, pergunta. Ferramentas do MCP `esper_brain`: `temas_atencao` (JSON) e, se precisar do nome bonito da área, `listar_temas`.

## Modo diário (rotina 08:40)
1. `temas_atencao(dias_prazo=3)`.
2. Junte `vencido` e `prazo_perto`. Nada nas duas listas → responda exatamente `[SILENT]` (o cron não entrega) e pare.
3. Senão, uma linha por item, vencidos primeiro, no máximo 8:
   `⚠️ Trabalho › ness › Proposta pentest — venceu 21/11` ou `📅 Casa › Trocar de carro — vence sex 28/11 (em 3 dias)`.
   Trabalho mostra a empresa (IONIC também a frente quando estiver no caminho); Patrimônio mostra a holding.
4. Última linha: `Quer que eu retome algum?` — nada mais.

## Modo semanal (rotina segunda 08:50, ou quando ele pedir a revisão)
1. `temas_atencao(dias_prazo=7, dias_parado=30)`.
2. Responda agrupado **por área** (Família, Casa, Saúde, Pessoal, Patrimônio, Trabalho › ness/IONIC/Bekaa), no máximo 15 linhas no total:
   - vencidos e prazos da semana (`dias`), primeiro;
   - parados há mais de 30 dias (`⏸ parado há N dias`);
   - sem próximo passo (`sem próximo passo`), só os 5 mais antigos.
   Um tema que aparece em mais de uma lista vira uma linha só, com as marcas juntas.
3. Entrada: se `entrada.pendentes` > 0 e a mais antiga tem mais de 2 dias → `📥 N pedaços na entrada desde DD/MM — quer que eu organize?`.
4. Tudo vazio → `Tudo em dia nos temas. 👍` (no semanal sempre responde).
5. Termine com: `Qual destes você quer retomar?`

## Regras
- Datas em DD/MM e dia da semana abreviado; "hoje" e "amanhã" quando couber. Hoje = America/Sao_Paulo (`temas_atencao` já traz `hoje`).
- Não invente prazo nem próximo passo; não sugira concluir tema sozinha.
- Se ele responder pedindo para retomar, use a skill `retomar`; para mudar estado ou prazo, a skill `capturar` (ou `substituir` + `gravar` com o sim dele).
