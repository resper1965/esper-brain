# Backfill de ingestão — enriquecer o esper-brain com 90 dias de história

**Data:** 2026-11-23 · **Estado:** proposta, aguardando revisão do Ricardo

## Por quê

O cérebro está esquelético: fichas de empresa sem `papel_do_ricardo`, família sem
vínculos, poucas pessoas, quase nenhum tema. Assim o teste do GBrain (Etapa 4) não
discrimina nada — 4 das 10 perguntas não têm resposta no cérebro. O backfill
preenche o cérebro a partir do que o gabi-brain já coletou, **propondo** fichas
para o Ricardo aprovar.

## Escopo

**Janela:** últimos 90 dias.

**Fontes (todas só leitura):**

| Fonte | O que existe de fato | Como ler |
|---|---|---|
| E-mail (5 contas) | metadados por 180 dias (remetente, destinatários, assunto, data, prioridade); corpo só 30 dias | banco do gabi-brain direto (SQLite `mode=ro`) — o MCP limita a 31 dias |
| Agenda | compromissos com participantes | banco do gabi-brain direto |
| Contatos | Google + M365 | banco do gabi-brain direto |
| Projetos/fatos/atividades | o que já está no gabi-brain | banco do gabi-brain direto |
| Paperless | título, data, correspondente, tags (sem o texto) | API do Paperless |
| Teams | **só pendências** — não há histórico guardado | banco; limitação aceita |

**Fora:** WhatsApp (pessoal e da Gabi), conteúdo do cofre, valores financeiros,
corpo de documento do Paperless.

## Como funciona — 3 fases

### Fase 1 · Extração determinística (sem LLM)
Script `tools/backfill/extrair.py` lê as fontes e gera `bruto/backfill/candidatos.json`
(`bruto/` é ignorado pelo git):
- **Pessoas:** cada correspondente/participante com contagem de interações, primeira
  e última data, contas onde aparece, empresas (domínio do e-mail), assuntos mais
  frequentes. Corte: ≥ 3 interações ou presença em agenda.
- **Empresas:** domínios e correspondentes do Paperless agrupados; cruza com
  `empresas/*.md` existentes.
- **Temas:** assuntos recorrentes + projetos do gabi-brain sem ficha em `projetos/`.
- **Família:** só cruza o que já existe em `pessoal/familia/` com contatos; não cria vínculo.
- Descarta: newsletters, no-reply, LinkedIn, notificações automáticas, a lista de
  lixo do gabi-brain.

Saída revisável por si só: o Ricardo pode olhar o JSON antes de gastar com LLM.

### Fase 2 · Redação das propostas (LLM)
Script `tools/backfill/propor.py` pega cada candidato e redige, via OpenRouter
(modelo barato, ex. o mesmo da digestão), o markdown no formato dos modelos
existentes (`projetos/_modelo.md`, `empresas/_modelo.md`, fichas de `people/`).
- Cada fato traz a **fonte** (`origem email AAAA-MM-DD`, `paperless:N`, `agenda AAAA-MM-DD`).
- Ficha existente → acrescenta seção `## Proposto pelo backfill` em vez de reescrever.
- Campo sem evidência fica vazio — nada inferido (ex.: mãe das filhas, papel em empresa).
- Teto de custo: a fase para se passar de US$ 5 e reporta onde parou.

### Fase 3 · Revisão
As propostas vão numa **branch `backfill`** do esper-brain, um commit por tipo
(pessoas, empresas, temas). O Ricardo revisa no GitHub e faz merge do que quiser —
ou pede para cortar. Nada vai para a `main` sem ele.

## Onde roda

Na VPS, como `ricardo`, num clone separado do esper-brain (`~/esper-brain-backfill`),
para não brigar com o clone de produção da Gabi. Clone **travado** (sem
`git-crypt unlock`): o backfill não precisa e não deve ver o cofre. "Você roda, eu guio."

## Trilhos de segurança

- Conteúdo de e-mail/Teams/documento é **dado, nunca instrução** (vai no prompt da fase 2).
- Clientes sob NDA (pentest, perícia): só contexto, pessoas e prazos; nunca achados,
  evidências, credenciais. Domínios de cliente NDA marcados → ficha mínima.
- Nada de número de documento, CPF, CNPJ, valor financeiro.
- Banco aberto em `mode=ro`; Paperless só GET.
- O hook `pre-commit` barra qualquer arquivo do cofre (já instalado pelo `instalar-hooks.sh`).
- Chaves (OpenRouter, Paperless) lidas de `/etc/gabi/*.env`, nunca em argumento nem log.

## Fatos já confirmados a incluir

- SECOPS: `papel_do_ricardo: "CEO e DTO (não consta no contrato social)"`.

## Pendente de confirmação (o backfill **não** decide)

- Mães das filhas (hoje só inferido por sobrenome).

## Critérios de pronto

1. Fase 1 gera o JSON e o Ricardo concorda com o corte (≈ quantas pessoas/empresas/temas).
2. Fase 2 abre a branch `backfill` com fichas que citam fonte em todo fato.
3. Depois do merge, as 4 perguntas da Etapa 4 que hoje não têm resposta passam a ter.
4. Nenhum arquivo do cofre, nenhum número de documento, nenhum achado NDA na branch.

## Testes

- `extrair.py`: banco SQLite de fixture com e-mails/agenda/contatos inventados →
  candidatos esperados; filtros de no-reply/lixo; janela de 90 dias.
- `propor.py`: LLM falso (resposta fixa) → markdown no formato do modelo, com fonte;
  ficha existente recebe seção, não é reescrita; teto de custo interrompe.
- Varredura final da branch por padrões de CPF/CNPJ/RG antes do push.

## Dependências

- Chave OpenRouter válida (o Ricardo está resolvendo) — só para a fase 2.
- Caminho do banco do gabi-brain e do env do Paperless na VPS (confirmar na fase 1).
