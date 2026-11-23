import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def _publicar(repo):
    return subprocess.run(["bash", "tools/backfill/publicar.sh"], cwd=repo, capture_output=True, text=True)


def _repo(tmp_path):
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "-q", "--bare", str(remote))

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "checkout", "-q", "-b", "main")
    _git(repo, "config", "user.name", "teste")
    _git(repo, "config", "user.email", "teste@example.com")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "tools" / "backfill").mkdir(parents=True)
    for nome in ("varrer.py", "publicar.sh"):
        (repo / "tools" / "backfill" / nome).write_text((ROOT / "tools" / "backfill" / nome).read_text(encoding="utf-8"), encoding="utf-8")
    for tipo in ("people", "empresas", "projetos"):
        (repo / tipo).mkdir()
        (repo / tipo / ".gitkeep").write_text("")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "origin", "main")
    _git(repo, "checkout", "-q", "-b", "backfill")
    return repo, remote


def test_publicar_bloqueia_arquivo_ja_no_indice(tmp_path):
    repo, _ = _repo(tmp_path)
    (repo / "projetos" / "nota.md").write_text("CPF 123.456.789-09", encoding="utf-8")
    _git(repo, "add", "projetos/nota.md")

    r = _publicar(repo)
    assert r.returncode != 0
    assert _git(repo, "rev-list", "--count", "main..backfill").strip() == "0"


def test_publicar_bloqueia_pasta_nova_com_cpf_e_publica_limpo(tmp_path):
    repo, remote = _repo(tmp_path)

    pasta = repo / "projetos" / "novo tema"
    pasta.mkdir()
    (pasta / "nota.md").write_text("CPF 123.456.789-09", encoding="utf-8")

    r = _publicar(repo)
    assert r.returncode != 0
    assert _git(repo, "rev-list", "--count", "main..backfill").strip() == "0"

    (pasta / "nota.md").write_text("reunião sem dados sensíveis", encoding="utf-8")
    (repo / "people" / "a.md").write_text("contato limpo", encoding="utf-8")

    r = _publicar(repo)
    assert r.returncode == 0, r.stdout + r.stderr
    assert int(_git(repo, "rev-list", "--count", "main..backfill").strip()) >= 1
    assert "backfill" in _git(tmp_path, "ls-remote", "--heads", str(remote))
