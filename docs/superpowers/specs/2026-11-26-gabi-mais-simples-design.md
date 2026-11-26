# Gabi mais simples: SOUL enxuto, relatório de uso e comando único

Data: 2026-11-26. Origem: análise de usabilidade e excesso de engenharia pedida pelo Ricardo ("faça e execute sem intervenção, use suas melhores recomendações").

## Problema

1. O SOUL que a Gabi lê é a soma de quatro remendos em ordem (SOUL do gabi-brain → `editar_soul.py` do gabi-finance → `ajustar_soul_antigo.py` → seção do esper-brain). O instalador do gabi-brain sobrescreve o SOUL e só reaplica a seção do esper-brain, então o texto antigo (família e projetos pelo gabi-brain, projetos pelo Linear) volta. Foi o que fez a Gabi procurar `familia_registrar_pessoa` em 25/11.
2. O gabi-brain ainda ensina e lista (no `tools.include` oficial) ferramentas que saíram do Hermes na migração: `familia_*` (menos `familia_vencimentos`), `projeto_*`, `anexo_recentes`. A VPS já as tirou à mão (`configurar_hermes.py`), o repositório não.
3. Não há como saber quais ferramentas a Gabi realmente usa. `chamada_mcp` registra tudo, mas ninguém lê.
4. Atualizar a Gabi são 5 a 8 comandos manuais; ontem três regras ficaram sem instalar e a rotina `organizar` das 21:30 falhou sem aviso.

## Decisões (recomendação aplicada, sem pergunta)

- A fonte do SOUL do gabi-brain passa a ser curta e sem o que migrou; a seção do esper-brain cobre família, temas e projetos. O que migrou não é apagado do código (as ferramentas continuam existindo no servidor, só saem do Hermes).
- `ferramentas_do_hermes()` passa a excluir as ferramentas migradas, igualando o repositório ao que a VPS já faz.
- O corte por uso real fica em duas etapas: este trabalho entrega só o relatório (leitura); o corte em si precisa dos números da VPS e será decidido com o Ricardo depois.
- Um único comando `deploy/gabi.sh` (no esper-brain, que é o centro) com `estado` (somente leitura) e `atualizar` (compõe o SOUL na ordem certa).
- Fora do escopo, de propósito: apagar o código morto de `dinheiro/` e `cobrar/` no gabi-brain, a página de entrada única, o aviso de falha de rotina no Telegram e a troca de modelo. Cada um merece decisão própria.

## Restrições

- Nada vai para a VPS daqui: o Ricardo roda os comandos. Nenhum arquivo de dados do esper-brain é editado.
- Segredos nunca em texto; scripts não leem nem imprimem chaves.
- gabi-brain tem 1 teste que já falhava antes (`test_obter_token_teams::test_main_gravar_falhando_nao_mostra_o_token`); não conta como regressão.
