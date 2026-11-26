import os
import pathlib
import subprocess

SH = pathlib.Path(__file__).resolve().parent.parent / "deploy" / "gabi.sh"


def _rodar(home, *args, **env):
    e = {**os.environ, "GABI_HOME": str(home), "HOME": str(home), **env}
    return subprocess.run(["bash", str(SH), *args], capture_output=True, text=True, env=e)


def _git(d, *a):
    subprocess.run(["git", "-C", str(d), "-c", "user.email=t@t", "-c", "user.name=t", *a], check=True, capture_output=True)


def _repo(home, nome, msg="organizar 2026-11-26: 1 pedaços, t"):
    d = home / nome
    d.mkdir(parents=True)
    _git(d, "init", "-q")
    (d / "x").write_text("1")
    _git(d, "add", "x")
    _git(d, "commit", "-qm", msg)
    return d


def _com_entrada(d):
    (d / "entrada.md").write_text("# Entrada\n\n- 2026-11-25 18:18 · um pedaço\n")
    _git(d, "add", "entrada.md")
    _git(d, "commit", "-qm", "digestão 2026-11-26")


def _scripts(home):
    for rel in ("gabi-brain/deploy/instalar-hermes-soul.sh", "gabi-finance/deploy/hermes/editar_soul.py"):
        f = home / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("")


def _soul(home, texto):
    (home / ".hermes").mkdir(exist_ok=True)
    (home / ".hermes" / "SOUL.md").write_text(texto)


def test_estado_acusa_soul_com_texto_antigo(tmp_path):
    _repo(tmp_path, "esper-brain")
    _soul(tmp_path, "use `familia_registrar_pessoa` e `projeto_ligar`")
    r = _rodar(tmp_path, "estado")
    assert r.returncode == 3 and "SOUL desatualizado" in r.stdout


def test_estado_ok_com_soul_limpo_e_organizar_recente(tmp_path):
    _repo(tmp_path, "esper-brain")
    _soul(tmp_path, "<!-- esper-brain:inicio -->\nok\n<!-- esper-brain:fim -->\n")
    r = _rodar(tmp_path, "estado")
    assert r.returncode == 0, r.stdout + r.stderr


def test_estado_acusa_organizar_parado(tmp_path):
    _com_entrada(_repo(tmp_path, "esper-brain", msg="digestão 2026-11-26"))
    _soul(tmp_path, "<!-- esper-brain:inicio -->\nok\n<!-- esper-brain:fim -->\n")
    r = _rodar(tmp_path, "estado")
    assert r.returncode == 3 and "organizar sem gravar" in r.stdout


def test_atualizar_simulado_mostra_a_ordem_e_nao_executa(tmp_path):
    for n in ("esper-brain", "gabi-brain", "gabi-finance"):
        _repo(tmp_path, n)
    _scripts(tmp_path)
    r = _rodar(tmp_path, "atualizar", GABI_SIMULAR="1")
    assert r.returncode == 0, r.stdout + r.stderr
    ordem = [l for l in r.stdout.splitlines() if l.startswith("[simulado]")]
    assert any("pull" in l for l in ordem)
    i_brain = next(i for i, l in enumerate(ordem) if "instalar-hermes-soul.sh" in l)
    i_fin = next(i for i, l in enumerate(ordem) if "editar_soul.py" in l)
    i_restart = next(i for i, l in enumerate(ordem) if "restart hermes-gateway" in l)
    assert i_brain < i_fin < i_restart
    assert not (tmp_path / ".hermes" / "SOUL.md").exists()


def test_atualizar_pula_repositorio_ausente_sem_erro(tmp_path):
    _repo(tmp_path, "esper-brain")
    r = _rodar(tmp_path, "atualizar", "--sem-reiniciar", GABI_SIMULAR="1")
    assert r.returncode == 0 and "gabi-brain: não encontrado" in r.stdout
    assert "restart hermes-gateway" not in r.stdout


def test_sem_argumento_mostra_o_uso(tmp_path):
    r = _rodar(tmp_path)
    assert r.returncode == 2 and "estado" in r.stderr and "atualizar" in r.stderr
