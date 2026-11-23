"""Leitura só-leitura do banco do gabi-brain para o backfill. Nunca escreve."""
import sqlite3
from pathlib import Path


def abrir(caminho: str) -> sqlite3.Connection:
    con = sqlite3.connect(f"{Path(caminho).resolve().as_uri()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def contas_proprias(con) -> set[str]:
    return {r["conta"].lower() for r in con.execute("select conta from email_fonte")}


def emails(con, desde: str) -> list[dict]:
    sql = ("select f.conta, lower(coalesce(m.remetente,'')) remetente, coalesce(m.assunto,'') assunto, m.recebida_em, "
           "m.classe, m.lista from email_msg m join email_fonte f on f.id=m.fonte_id "
           "where m.recebida_em >= ? and f.estado='sim' and m.estado<>'na_lixeira'")
    return [dict(r) for r in con.execute(sql, (desde,))]


def respondidos(con) -> set[str]:
    """Endereços que o gabi-brain registrou em email_respondido (todo To/Cc de 365 dias de enviados, não um log de
    respostas; `em` é a hora da sincronização). Só sinal booleano: sem datas. Exclui a linha sentinela endereco=''."""
    sql = ("select distinct lower(r.endereco) e from email_respondido r join email_fonte f on f.id=r.fonte_id "
           "where f.estado='sim' and r.endereco<>''")
    return {r["e"] for r in con.execute(sql)}


def contatos(con) -> dict[str, str]:
    sql = "select lower(email) e, nome from contato_google_email where coalesce(nome,'')<>''"
    return {r["e"]: r["nome"] for r in con.execute(sql)}


def agenda(con, desde: str) -> list[dict]:
    sql = ("select dia_local dia, coalesce(titulo,'') titulo, coalesce(organizador_nome,'') organizador, participantes_qtd participantes "
           "from agenda_evento e join agenda_fonte f on f.id=e.fonte_id "
           "where f.estado='sim' and dia_local >= ? and coalesce(status,'') <> 'cancelled' and not coalesce(privado,0)")
    return [dict(r) for r in con.execute(sql, (desde,))]


def projetos(con) -> list[dict]:
    saida = []
    for p in con.execute("select id, nome, objetivo, status, prazo from projeto order by id"):
        pessoas = [r["nome"] for r in con.execute("select nome from projeto_pessoa where projeto_id=? order by id", (p["id"],))]
        saida.append({**dict(p), "pessoas": pessoas})
    return saida
