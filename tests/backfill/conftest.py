import sqlite3
import pytest

DDL = """
create table email_fonte(id integer primary key, conta text not null unique, provedor text not null, estado text not null default 'sim');
create table email_msg(id integer primary key, fonte_id integer not null, externo_id text not null, remetente text, assunto text,
  recebida_em text not null, trecho text, lista integer not null default 0, classe text, estado text not null default 'classificada');
create table email_respondido(fonte_id integer not null, endereco text not null, em text not null, primary key(fonte_id, endereco));
create table contato_google_email(conta text not null, email text not null, telefone text not null default '', nome text,
  primary key (conta, email, telefone));
create table agenda_evento(id integer primary key, fonte_id integer not null, externo_id text not null, inicio_utc text not null,
  fim_utc text not null, dia_local text not null, dia_fim_local text not null, titulo text, participantes_qtd integer not null default 0,
  status text, organizador_nome text, privado integer not null default 0);
create table projeto(id integer primary key, nome text not null, objetivo text, status text not null default 'ativo', prazo text,
  criado_em text not null, origem text not null);
create table projeto_pessoa(id integer primary key, projeto_id integer not null, nome text not null, papel text, pessoa_id text, contato text);
"""

def _popular(con):
    con.execute("insert into email_fonte values (1,'resper@gmail.com','google','sim'),(2,'ricardo@ness.com.br','graph','sim'),(3,'velha@esper.ws','google','nao')")
    msgs = [
        ("ana@acme.com.br", "RE: Proposta Acme", "2026-11-10T10:00:00Z", 0, "importante"),
        ("ana@acme.com.br", "Proposta Acme", "2026-11-05T10:00:00Z", 0, "normal"),
        ("ana@acme.com.br", "FW: Proposta Acme", "2026-10-30T10:00:00Z", 0, "normal"),
        ("bob@acme.com.br", "Reunião", "2026-11-01T10:00:00Z", 0, "normal"),
        ("noreply@banco.com.br", "Seu extrato", "2026-11-02T10:00:00Z", 0, "normal"),
        ("news@loja.com", "Ofertas", "2026-11-03T10:00:00Z", 1, "normal"),
        ("spam@x.com", "Ganhe", "2026-11-03T10:00:00Z", 0, "lixo"),
        ("velho@antigo.com", "Antigo", "2026-01-01T10:00:00Z", 0, "normal"),
        ("ricardo@ness.com.br", "nota para mim", "2026-11-04T10:00:00Z", 0, "normal"),
    ]
    for i, (rem, ass, em, lista, classe) in enumerate(msgs, 1):
        con.execute("insert into email_msg(id,fonte_id,externo_id,remetente,assunto,recebida_em,lista,classe) values (?,?,?,?,?,?,?,?)",
                    (i, 1, f"m{i}", rem, ass, em, lista, classe))
    con.execute("insert into email_msg(id,fonte_id,externo_id,remetente,assunto,recebida_em,lista,classe) values (10,3,'m10','carlos@acme.com.br','Contrato','2026-11-06T10:00:00Z',0,'normal')")
    con.execute("insert into email_msg(id,fonte_id,externo_id,remetente,assunto,recebida_em,lista,classe,estado) values (11,1,'m11','lixo@acme.com.br','Lixo','2026-11-07T10:00:00Z',0,'normal','na_lixeira')")
    con.execute("insert into email_respondido values (2,'bob@acme.com.br','2026-11-01T12:00:00Z')")
    con.execute("insert into contato_google_email values ('resper@gmail.com','ana@acme.com.br','','Ana Souza')")
    con.execute("insert into agenda_evento(id,fonte_id,externo_id,inicio_utc,fim_utc,dia_local,dia_fim_local,titulo,participantes_qtd,status,organizador_nome) "
                "values (1,1,'e1','2026-11-12T13:00:00Z','2026-11-12T14:00:00Z','2026-11-12','2026-11-12','Kickoff Acme',3,'confirmed','Ana Souza'),"
                "(2,1,'e2','2026-11-13T13:00:00Z','2026-11-13T14:00:00Z','2026-11-13','2026-11-13','Follow-up Acme',3,'confirmed','Ana Souza')")
    con.execute("insert into agenda_evento(id,fonte_id,externo_id,inicio_utc,fim_utc,dia_local,dia_fim_local,titulo,participantes_qtd,status,organizador_nome,privado) "
                "values (3,1,'e3','2026-11-14T13:00:00Z','2026-11-14T14:00:00Z','2026-11-14','2026-11-14','Conversa pessoal',1,'confirmed','Privado Fulano',1),"
                "(4,1,'e4','2026-11-15T13:00:00Z','2026-11-15T14:00:00Z','2026-11-15','2026-11-15','Reunião cancelada',2,'cancelled','Cancelado Beltrano',0)")
    con.execute("insert into projeto values (7,'Trocar de carro','SUV híbrido','ativo','2027-03-31','2026-11-01','ricardo')")
    con.execute("insert into projeto_pessoa(projeto_id,nome) values (7,'Vendedor Toyota')")

@pytest.fixture
def banco(tmp_path):
    caminho = tmp_path / "gabi.db"
    con = sqlite3.connect(caminho)
    con.executescript(DDL)
    _popular(con)
    con.commit()
    con.close()
    return str(caminho)
