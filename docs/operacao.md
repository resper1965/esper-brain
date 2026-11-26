# Operação da Gabi na VPS

Um comando só, `deploy/gabi.sh`, cobre o dia a dia. Ele não lê nem mostra chaves e tokens.

| Quero | Comando |
|---|---|
| Ver se algo está desatualizado ou parado | `bash ~/esper-brain/deploy/gabi.sh estado` |
| Atualizar tudo (pull dos 3 repositórios, SOUL na ordem certa, config do Hermes, restart) | `sudo bash /home/ricardo/esper-brain/deploy/gabi.sh atualizar` |
| Atualizar sem reiniciar o gateway | `bash ~/esper-brain/deploy/gabi.sh atualizar --sem-reiniciar` |
| Ver o que o Hermes simulava fazer, sem executar | `GABI_SIMULAR=1 bash ~/esper-brain/deploy/gabi.sh atualizar` |

Depois de `atualizar`, mande `/new` no Telegram para a conversa pegar o SOUL novo.

`estado` sai com código 3 quando acha problema: SOUL ainda ensinando ferramentas que migraram, SOUL sem a seção do esper-brain, repositório atrás do remoto, ou rotina `organizar` sem gravar há mais de 36 h com pedaços esperando na `entrada.md`.

## Ordem do SOUL (por que existe o script)

O instalador do gabi-brain sobrescreve o SOUL inteiro. Por isso a ordem importa: SOUL base do gabi-brain, depois as ferramentas de dinheiro (gabi-finance), depois a seção do esper-brain. O `atualizar` faz nessa ordem; fazer à mão fora dela traz de volta ensinos antigos.

## Relatório de uso das ferramentas

Para decidir o que cortar da lista do Hermes (rodar como root, de dentro do clone do gabi-brain):

```
python -m tools.uso_ferramentas --dias 30
```

Mostra quantas vezes cada ferramenta foi chamada e quais da lista oficial nunca foram. Abre o banco só para leitura.
