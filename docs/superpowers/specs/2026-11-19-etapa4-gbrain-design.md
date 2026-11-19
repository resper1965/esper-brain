# Etapa 4 — Teste do GBrain sobre o esper-brain

**Objetivo:** Medir, com dados reais, se o GBrain (busca híbrida + grafo de entidades sobre o markdown) responde melhor do que a busca de texto pura no esper-brain, e a que custo. Sai disto uma decisão: adotar, descartar ou revalidar depois.

**Não é:** uma instalação em produção. A Gabi do dia a dia não muda durante o teste. O Honcho e o ciclo noturno do GBrain ficam fora desta etapa.

## O que é o GBrain (resumo para quem executa)

Repositório markdown como fonte da verdade + índice em Postgres (pgvector) com busca híbrida (vetor + texto) + grafo tipado de entidades (pessoas, empresas, projetos) + skills. Roda como servidor MCP (`gbrain serve`). Sobe leve com `gbrain init --pglite` (Postgres embutido, sem Docker). A indexação não usa modelo (barata); o custo está nas consultas, que usam um LLM para expandir a pergunta e sintetizar a resposta. Licença aberta. Repo: github.com/garrytan/gbrain.

## Decisões já tomadas (nov/2026)

- **Só GBrain** nesta etapa; o Honcho vira um segundo teste, separado, depois.
- **Modo leitura:** o GBrain indexa e responde, mas **não reescreve** o esper-brain. O ciclo noturno (reorganizar/religar páginas) fica desligado. A fonte da verdade continua sendo o esper-brain, com as regras do `AGENTS.md` e o `gravar.sh`.
- **Sem o cofre no índice:** a pasta `pessoal/cofre/` fica fora do que o GBrain lê. Nada cifrado nem número de documento entra no índice do GBrain.
- **pglite** (Postgres embutido), não Docker, para pesar o mínimo na VPS.
- **Fora da Gabi de produção:** o teste roda por um harness próprio, não pelo Hermes de produção.

## Restrições do projeto (Global Constraints)

- VPS Contabo única; o Claude escreve os comandos, o Ricardo roda como root ("você roda, eu guio"). Nada é rodado em produção por conta própria.
- Segredos nunca na tela nem no chat. A chave do OpenRouter para o GBrain entra por arquivo, com `read -rs`, e nunca aparece.
- Todo bloco para a VPS começa com `umask 022`; um `umask 077` só entre parênteses.
- O índice do GBrain e o clone de teste ficam **fora** das pastas dos serviços de produção (sugestão: `/home/ricardo/etapa4-gbrain/`), removíveis sem afetar nada.
- O clone de teste é feito do esper-brain **excluindo `pessoal/cofre/`**; o teste nunca destrava o git-crypt.
- Nada da Gabi de produção (config.yaml, serviços, timers) é alterado nesta etapa.

## Dependência do Ricardo

- Uma chave do OpenRouter (pode ser a mesma da Gabi, ou uma dedicada ao teste) e o modelo a usar para a expansão de consulta/síntese do GBrain. É a única parte que custa dinheiro. Entra por arquivo de ambiente do teste, só durante o teste.

## Como o teste roda

1. **Preparar o cérebro de teste:** clonar o esper-brain para `/home/ricardo/etapa4-gbrain/brain`, removendo `pessoal/cofre/` do clone. Confirmar que nenhum arquivo do clone começa com `\0GITCRYPT`.
2. **Subir o GBrain** (`gbrain init --pglite` + indexar o clone). Medir a RAM em repouso e durante consulta.
3. **Camada A (markdown puro):** um script que, para cada pergunta, busca por texto no clone (o mesmo que a Gabi faz hoje: `grep`/busca simples por palavras-chave) e devolve a(s) página(s) candidatas.
4. **Camada B (GBrain):** a mesma pergunta pela consulta do GBrain, devolvendo resposta + página(s)-fonte.
5. **Registrar**, por pergunta e por camada, numa tabela: achou a página certa (sim/não), a resposta certa (sim/não), a latência, o custo estimado da chamada (tokens × preço do modelo). O "certo" é conferido pelo Ricardo ou por um gabarito escrito junto das perguntas.

## As 10 perguntas

Gabarito escrito junto de cada uma, com a página-fonte esperada do esper-brain.

1. Que carro o Ricardo tem? — *fato simples* (`pessoal/casa/bens.md`)
2. Quem é a esposa do Ricardo? — *fato simples* (`pessoal/familia/sabrina-barbosa-de-barros.md`)
3. Quem são as filhas dele? — *lista* (`pessoal/familia/` — Louise e Giovanna)
4. Quais empresas são holdings patrimoniais? — *semântico/filtro por tipo* (`empresas/baalbeck.md`, `empresas/fakiha.md`)
5. Qual empresa era a NESS Law antes? — *síntese de nome* (`empresas/secops.md`)
6. Qual é a PJ do Ricardo? — *semântico* (`empresas/bekaa.md`)
7. Giovanna é filha de qual mãe? — *grafo: filha → mãe* (`pessoal/familia/giovanna-della-torre-esper.md`)
8. Em qual empresa o Ricardo é CISO e cofundador? — *pessoa → papel → empresa* (`empresas/ionic-health.md`)
9. Quem na família tem ficha, além da esposa e das filhas? — *síntese/listagem* (`pessoal/familia/`)
10. O que ainda está pendente para resolver? — *pendências* (`pendencias.md`)

## Critério de decisão

- **GBrain adotado** se acertar páginas/respostas que o markdown erra (sobretudo as semânticas e de grafo: 4, 6, 7, 8), sem custo, latência ou RAM que não compensem na VPS.
- **GBrain descartado** se empatar com o markdown no acerto e perder em custo/latência/RAM.
- **Revalidar depois** se o resultado for inconclusivo por o cérebro estar magro (ver aviso abaixo).

## Aviso: cérebro novo

O esper-brain nasceu em 17/11 e a digestão diária começou em 18/11. O GBrain brilha em cérebro grande e cheio de ligações; num cérebro magro, a busca de texto empata fácil. Este é um primeiro retrato. Um resultado fraco do GBrain agora não encerra a questão: revalida-se depois que a digestão encher o cérebro por algumas semanas (sugestão: reavaliar após ~1 mês de digestão).

## Limpeza

Tudo do teste vive em `/home/ricardo/etapa4-gbrain/`. Ao fim, a pasta inteira é removível (`rm -rf`), e nada de produção foi tocado. A chave do OpenRouter do teste é apagada.

## Fora de escopo (próximas etapas, cada uma com spec própria)

- Honcho (modelo do usuário / memória de conversa), auto-hospedado.
- Ciclo noturno do GBrain (modo "indexar e manter"), num desenho controlado que respeite o `gravar.sh` e o cofre.
- Integração do GBrain na Gabi de produção, se o teste aprovar.
