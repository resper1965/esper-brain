import csv
import json
import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import harness  # noqa: E402
import tabela  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
PERGUNTAS = Path(__file__).with_name("perguntas.json")


def _brain(tmp_path):
    b = tmp_path / "brain"
    for rel, txt in {
        "empresas/bekaa.md": "# Bekaa\nPJ do Ricardo",
        "pessoal/familia/sabrina.md": "# Sabrina\nesposa",
        "pessoal/casa/bens.md": "# Bens\nFord Ranger carro",
        "pessoal/cofre/segredo.md": "carro carro Ranger",
        "docs/x.md": "carro carro",
    }.items():
        p = b / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")
    return b


def _perguntas(tmp_path):
    rows = [
        {"n": 1, "pergunta": "Que carro?", "fonte_esperada": "pessoal/casa/bens.md", "gabarito": "x", "palavras_chave": ["carro"]},
        {"n": 2, "pergunta": "Esposa?", "fonte_esperada": "pessoal/familia/", "gabarito": "x", "palavras_chave": ["esposa"]},
        {"n": 3, "pergunta": "PJ?", "fonte_esperada": ["empresas/x.md", "empresas/bekaa.md"], "gabarito": "x", "palavras_chave": ["pj"]},
    ]
    p = tmp_path / "perguntas.json"
    p.write_text(json.dumps(rows), encoding="utf-8")
    return harness.carregar_perguntas(p)


def test_markdown_acha_carro_e_ignora_cofre(tmp_path):
    out = harness.markdown(_brain(tmp_path), _perguntas(tmp_path))
    assert out[0]["fonte_bateu"] is True
    assert out[0]["paginas_achadas"] == ["pessoal/casa/bens.md"]
    assert out[1]["fonte_bateu"] is True  # prefixo de pasta
    assert out[2]["fonte_bateu"] is True  # lista de fontes
    assert all(r["camada"] == "markdown" and r["latencia_ms"] >= 0 for r in out)


def test_markdown_no_repo_real():
    out = harness.markdown(REPO, harness.carregar_perguntas(PERGUNTAS))
    assert [r["n"] for r in out] == list(range(1, 11))
    assert out[1]["fonte_bateu"] is True, out[1]
    for p in harness.carregar_perguntas(PERGUNTAS):
        for f in harness.como_lista(p["fonte_esperada"]):
            assert (REPO / f).exists(), f


def _fake_gbrain(tmp_path, body, code=0):
    s = tmp_path / "gbrain"
    s.write_text(f"#!/bin/sh\ncat <<'EOF'\n{body}\nEOF\nexit {code}\n")
    s.chmod(s.stat().st_mode | stat.S_IEXEC)
    return str(s)


def test_gbrain_search_extrai_paginas(tmp_path):
    brain = _brain(tmp_path)
    body = json.dumps({"results": [
        {"slug": "x", "path": f"{brain}/pessoal/casa/bens.md", "score": 1},
        {"source": "brain/empresas/bekaa.md"},
    ]})
    g = _fake_gbrain(tmp_path, body)
    out = harness.gbrain(brain, _perguntas(tmp_path)[:1], "gbrain-search", g)
    assert out[0]["paginas_achadas"] == ["pessoal/casa/bens.md", "empresas/bekaa.md"]
    assert out[0]["fonte_bateu"] is True and out[0]["erro"] == ""


def test_gbrain_think_guarda_resposta(tmp_path):
    brain = _brain(tmp_path)
    body = json.dumps({"answer": "Uma Ranger", "citations": [{"file": "pessoal/casa/bens.md"}]})
    g = _fake_gbrain(tmp_path, body)
    out = harness.gbrain(brain, _perguntas(tmp_path)[:1], "gbrain-think", g)
    assert out[0]["fonte_bateu"] is True and "Ranger" in out[0]["resposta"]


def test_gbrain_erro_json_e_exit(tmp_path):
    brain = _brain(tmp_path)
    ps = _perguntas(tmp_path)[:1]
    r = harness.gbrain(brain, ps, "gbrain-search", _fake_gbrain(tmp_path, "nao e json"))[0]
    assert r["fonte_bateu"] is False and r["erro"]
    r = harness.gbrain(brain, ps, "gbrain-search", _fake_gbrain(tmp_path, "{}", code=3))[0]
    assert r["fonte_bateu"] is False and "3" in r["erro"]
    r = harness.gbrain(brain, ps, "gbrain-search", str(tmp_path / "inexistente"))[0]
    assert r["fonte_bateu"] is False and r["erro"]


def test_csv_e_tabela(tmp_path):
    brain = _brain(tmp_path)
    ps = _perguntas(tmp_path)
    m = tmp_path / "m.csv"
    harness.gravar_csv(harness.markdown(brain, ps), m)
    with open(m, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0].keys()) == harness.COLUNAS
    g = _fake_gbrain(tmp_path, json.dumps({"results": [{"path": "pessoal/casa/bens.md"}]}))
    gc = tmp_path / "g.csv"
    harness.gravar_csv(harness.gbrain(brain, ps, "gbrain-search", g), gc)
    md = tabela.montar([m, gc])
    linhas = md.strip().splitlines()
    assert "markdown: página?" in linhas[0] and "gbrain-search: ms" in linhas[0]
    assert linhas[0].count("resposta certa?") == 2
    assert len(linhas) == 2 + 3
    assert "| sim |" in linhas[2]
    assert linhas[2].rstrip().endswith("|  |")
