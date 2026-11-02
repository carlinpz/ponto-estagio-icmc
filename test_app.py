"""
Script de testes para verificar cálculos, regras de validação e persistência.
"""

import sys
from datetime import datetime, date, time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from calculations import (
    calculate_day_worked_hours,
    decimal_hours_to_hm_str,
    parse_time_str,
    format_time_str,
    process_records_dataframe,
    compute_current_elapsed_time,
    get_business_days_in_month,
    get_expected_business_days,
    detect_compliance_issues,
    generate_fusp_timesheet_html,
    get_fusp_period_dates,
)
from storage import (
    load_database,
    save_database,
    upsert_record,
    delete_record_by_date,
    export_df_to_csv_bytes,
)

def test_all():
    print("Iniciando testes...")

    # Teste 1: Cálculo de horas com intervalo
    # Entrada 09:00, Almoço 12:00 às 12:15 (15 min), Saída 15:15 -> 6h líquidas
    h_trab, status = calculate_day_worked_hours("09:00:00", "12:00:00", "12:15:00", "15:15:00")
    assert h_trab == 6.0, f"Esperado 6.0, obtido {h_trab}"
    assert status == "Concluído"
    print("✓ Teste 1 passou: 6h com intervalo de 15m")

    # Teste 2: Horas extras (6h30 trabalhadas para meta de 6h -> saldo +0h30)
    h_trab, _ = calculate_day_worked_hours("09:00:00", "12:00:00", "12:00:00", "15:30:00")
    saldo = h_trab - 6.0
    saldo_str = decimal_hours_to_hm_str(saldo, show_sign=True)
    assert saldo_str == "+00h 30m", f"Esperado +00h 30m, obtido {saldo_str}"
    print("✓ Teste 2 passou: Horas extras (+30m)")

    # Teste 3: Horas devidas (-45 minutos)
    saldo_neg = -0.75
    saldo_neg_str = decimal_hours_to_hm_str(saldo_neg, show_sign=True)
    assert saldo_neg_str == "-00h 45m", f"Esperado -00h 45m, obtido {saldo_neg_str}"
    print("✓ Teste 3 passou: Horas devidas (-45m)")

    # Teste 4: Parsing e formatação de horários
    t = parse_time_str("14:35:10")
    assert t == time(14, 35, 10)
    assert format_time_str(t) == "14:35"
    assert format_time_str(t, include_seconds=True) == "14:35:10"
    print("✓ Teste 4 passou: Conversões de horários")

    # Teste 5: Processamento de DataFrame com registros
    sample_records = [
        {
            "data": "2026-10-01",
            "entrada": "09:00:00",
            "inicio_pausa": "12:00:00",
            "fim_pausa": "12:15:00",
            "saida": "15:15:00",
            "meta_dia": 6.0,
            "observacao": "Dia 1",
        },
        {
            "data": "2026-10-02",
            "entrada": "09:00:00",
            "inicio_pausa": None,
            "fim_pausa": None,
            "saida": "15:30:00",
            "meta_dia": 6.0,
            "observacao": "Dia 2",
        },
    ]
    df = process_records_dataframe(sample_records, 6.0)
    assert len(df) == 2
    assert "Saldo Acumulado (h)" in df.columns
    print("✓ Teste 5 passou: Processamento DataFrame")

    # Teste 6: Exportação CSV
    csv_bytes = export_df_to_csv_bytes(df)
    assert len(csv_bytes) > 0
    print("✓ Teste 6 passou: Exportação CSV")

    # Teste 7: Dias úteis no mês e get_expected_business_days
    dias_uteis_padrao = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira"]
    dias_uteis = get_business_days_in_month(2026, 10, dias_uteis_padrao)
    assert dias_uteis == 22, f"Esperado 22 dias úteis em 10/2026, obtido {dias_uteis}"

    # 7a: Setembro/2026 com início de contrato em 2026-09-28 (28, 29, 30 de setembro -> 3 dias úteis)
    recs_setembro = [
        {"data": "2026-09-28", "entrada": "08:00:00", "saida": "14:00:00", "meta_dia": 6.0, "observacao": ""},
        {"data": "2026-09-29", "entrada": "08:00:00", "saida": "14:00:00", "meta_dia": 6.0, "observacao": ""},
        {"data": "2026-09-30", "entrada": "08:00:00", "saida": "14:00:00", "meta_dia": 6.0, "observacao": ""},
    ]
    _, uteis_set_total = get_expected_business_days(2026, 9, dias_uteis_padrao, recs_setembro)
    assert uteis_set_total == 3, f"Esperado 3 dias úteis em 09/2026 a partir de 28/09, obtido {uteis_set_total}"

    # 7b: Outubro/2026 com feriado em 2026-10-12 (reduz de 22 para 21 dias úteis)
    recs_outubro = recs_setembro + [
        {"data": "2026-10-12", "entrada": None, "saida": None, "meta_dia": 0.0, "observacao": "Feriado Nacional"},
    ]
    _, uteis_out_total = get_expected_business_days(2026, 10, dias_uteis_padrao, recs_outubro)
    assert uteis_out_total == 21, f"Esperado 21 dias úteis em 10/2026 descontando feriado 12/10, obtido {uteis_out_total}"
    print(f"✓ Teste 7 passou: Cálculo de dias úteis e get_expected_business_days (09/2026={uteis_set_total}, 10/2026={uteis_out_total})")

    # Teste 8: Detecção de inconsistências (excesso de horas ou batida pendente)
    inconsistencias = detect_compliance_issues([
        {"data": "2026-10-01", "entrada": "09:00:00", "inicio_pausa": None, "fim_pausa": None, "saida": "17:00:00"}
    ], 6.0)
    assert len(inconsistencias) > 0
    print("✓ Teste 8 passou: Detecção de inconformidade legal de estágio")

    # Teste 9: Preservação do Saldo Acumulado (h) em dias de Feriado / Abono após dias com saldo positivo
    recs_acum = [
        {"data": "2026-10-09", "entrada": "08:00:00", "inicio_pausa": None, "fim_pausa": None, "saida": "15:00:00", "meta_dia": 6.0, "observacao": "Sexta (+1h)"},
        {"data": "2026-10-12", "entrada": None, "inicio_pausa": None, "fim_pausa": None, "saida": None, "meta_dia": 0.0, "observacao": "Feriado"},
    ]
    df_acum = process_records_dataframe(recs_acum, 6.0)
    assert df_acum.iloc[0]["Saldo Acumulado (h)"] == 1.0
    assert df_acum.iloc[1]["Status"] == "Feriado / Abono"
    assert df_acum.iloc[1]["Saldo Acumulado (h)"] == 1.0, f"Esperado saldo acumulado 1.0 preservado no feriado, obtido {df_acum.iloc[1]['Saldo Acumulado (h)']}"
    assert df_acum.iloc[1]["Saldo Acumulado Formatado"] == "+01h 00m"
    print("✓ Teste 9 passou: Preservação contínua do Saldo Acumulado em Feriado / Abono")

    # Teste 10: Geração do Boletim de Frequência FUSP
    cfg_test = {"nome_estagiario": "João", "nome_supervisor": "Maria", "empresa_setor": "TI", "carga_horaria_diaria": 6.0}
    ini_fusp, fim_fusp, datas_fusp = get_fusp_period_dates(2026, 10)
    assert ini_fusp == date(2026, 9, 21)
    assert fim_fusp == date(2026, 10, 20)
    assert len(datas_fusp) == 30
    html_fusp = generate_fusp_timesheet_html(sample_records, cfg_test, 2026, 10)
    assert "BOLETIM DE FREQUENCIA - FUSP" in html_fusp
    assert "Período: 10/2026" in html_fusp
    assert "João" in html_fusp
    print("✓ Teste 10 passou: Geração do Boletim Oficial de Frequência FUSP")

    # Teste 11: Feriado com meta_dia = 0.0 e filtro de CONFIG_JSON
    holiday_records = [
        {"data": "2026-10-12", "entrada": None, "inicio_pausa": None, "fim_pausa": None, "saida": None, "meta_dia": 0.0, "observacao": "Feriado"},
        {"data": "CONFIG_JSON", "entrada": None, "inicio_pausa": None, "fim_pausa": None, "saida": None, "meta_dia": 0.0, "observacao": '{"usuario_estagiario": "carlos"}'},
    ]
    df_hol = process_records_dataframe(holiday_records, 6.0)
    assert len(df_hol) == 1, f"CONFIG_JSON deveria ser ignorado, obtido {len(df_hol)}"
    assert df_hol.iloc[0]["Status"] == "Feriado / Abono"
    assert df_hol.iloc[0]["Meta (h)"] == 0.0
    print("✓ Teste 11 passou: Tratamento de feriado (meta 0.0) e filtro de CONFIG_JSON")

    print("TODOS OS TESTES PASSARAM COM SUCESSO! 🎉")


# ---------------------------------------------------------------------------
# Sincronização por registro com a planilha (rede simulada: nenhum teste acessa a internet)
# ---------------------------------------------------------------------------
import json
import os
import re
from pathlib import Path

import pytest
import requests

import storage
import auth

REG_02_10 = {
    "data": "2026-10-02", "entrada": "08:15:00", "inicio_pausa": "12:40:00",
    "fim_pausa": "13:40:00", "saida": "15:15:00", "meta_dia": 6.0, "observacao": "Ajuste manual",
}


class FakeResposta:
    def __init__(self, corpo=None, status=200, texto=None):
        self.status_code = status
        self._corpo = corpo
        self.text = texto if texto is not None else json.dumps(corpo)

    def json(self):
        if self._corpo is None:
            raise ValueError("não é JSON")
        return self._corpo


@pytest.fixture
def planilha(monkeypatch):
    """Configura a nuvem via variáveis de ambiente e intercepta requests.post, guardando cada chamada."""
    monkeypatch.setenv("APPS_SCRIPT_URL", "https://exemplo.invalid/exec")
    monkeypatch.setenv("APPS_SCRIPT_SECRET", "segredo-de-teste")
    # Não deixa o teste ler o secrets.toml real (o Streamlit guardaria em memória para os testes seguintes)
    monkeypatch.setattr(storage, "load_config", lambda: json.loads(json.dumps(storage.DEFAULT_CONFIG)))
    monkeypatch.setattr(storage, "_urls_confirmadas", set())
    estado = {
        "chamadas": [],
        "resposta": FakeResposta({"ok": True}),
        "versao": FakeResposta({"ok": False, "erro": "Use POST com o segredo.", "versao": 2}),
    }

    def fake_post(url, json=None, timeout=None):
        estado["chamadas"].append({"url": url, "corpo": json})
        r = estado["resposta"]
        if isinstance(r, Exception):
            raise r
        return r(json) if callable(r) else r

    def fake_get(url, timeout=None):
        return estado["versao"]

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "get", fake_get)
    return estado


def test_apps_script_antigo_nunca_recebe_post(planilha):
    """O script antigo sobrescreve a planilha inteira em qualquer POST: o app não pode nem tentar."""
    planilha["versao"] = FakeResposta([{"data": "2026-10-01"}])  # GET do script antigo devolve a lista crua
    with pytest.raises(storage.CloudSyncError, match="versão antiga"):
        storage.load_records_from_cloud()
    with pytest.raises(storage.CloudSyncError):
        storage.sync_upsert_records([REG_02_10])
    assert planilha["chamadas"] == []


def test_gravar_envia_so_o_registro_alterado_com_segredo(planilha):
    storage.sync_upsert_records([REG_02_10])
    assert len(planilha["chamadas"]) == 1
    chamada = planilha["chamadas"][0]
    assert chamada["corpo"]["acao"] == "gravar"
    assert chamada["corpo"]["segredo"] == "segredo-de-teste"
    assert "segredo" not in chamada["url"]
    assert [r["data"] for r in chamada["corpo"]["registros"]] == ["2026-10-02"]
    assert set(chamada["corpo"]["registros"][0]) == set(storage.CAMPOS_REGISTRO)


def test_excluir_envia_so_a_data(planilha):
    storage.sync_delete_record("2026-10-05")
    assert planilha["chamadas"][0]["corpo"] == {"segredo": "segredo-de-teste", "acao": "excluir", "data": "2026-10-05"}


@pytest.mark.parametrize("resposta", [
    FakeResposta({"ok": False, "erro": "não autorizado"}),
    FakeResposta({"ok": True}, status=500),
    FakeResposta(None, texto="<html>página de login do Google</html>"),
    FakeResposta([{"data": "2026-10-01"}]),  # formato do Apps Script antigo
    requests.ConnectionError("sem internet"),
])
def test_falha_da_planilha_vira_erro_visivel(planilha, resposta):
    planilha["resposta"] = resposta
    with pytest.raises(storage.CloudSyncError):
        storage.sync_upsert_records([REG_02_10])


def test_mensagem_de_erro_nao_vaza_segredo(planilha):
    planilha["resposta"] = requests.ConnectionError("falhou https://exemplo.invalid/exec segredo-de-teste")
    with pytest.raises(storage.CloudSyncError) as exc:
        storage.sync_delete_record("2026-10-05")
    assert "segredo-de-teste" not in str(exc.value)


def test_enviar_pendentes_mantem_pendencias_quando_falha(planilha):
    pendentes = {"2026-10-02": REG_02_10, "2026-10-05": None}
    planilha["resposta"] = FakeResposta({"ok": False, "erro": "fora do ar"})
    restantes, erro = storage.enviar_pendentes(pendentes)
    assert restantes == pendentes and "fora do ar" in erro

    planilha["resposta"] = FakeResposta({"ok": True})
    planilha["chamadas"].clear()
    restantes, erro = storage.enviar_pendentes(pendentes)
    assert restantes == {} and erro is None
    assert [c["corpo"]["acao"] for c in planilha["chamadas"]] == ["gravar", "excluir"]


def test_aplicar_pendentes_sobre_dados_da_planilha():
    da_planilha = [{"data": "2026-10-05", "entrada": "08:00:00"}, {"data": "2026-10-06", "entrada": "08:00:00"}]
    resultado = storage.aplicar_pendentes(da_planilha, {"2026-10-02": REG_02_10, "2026-10-05": None})
    assert [r["data"] for r in resultado] == ["2026-10-02", "2026-10-06"]


def test_listar_ignora_config_json_e_normaliza(planilha, tmp_path, monkeypatch):
    planilha["resposta"] = FakeResposta({"ok": True, "registros": [
        {"data": "CONFIG_JSON", "observacao": '{"pin_estagiario": "0000"}'},
        {"data": "2026-10-02", "entrada": "8:15:00", "inicio_pausa": "", "fim_pausa": "",
         "saida": "15:15", "meta_dia": "6,0", "observacao": ""},
    ]})
    cache = tmp_path / "ponto_eletronico.json"
    monkeypatch.setattr(storage, "DEFAULT_DATA_PATH", str(cache))
    db = storage.load_database(str(cache))
    assert [r["data"] for r in db["registros"]] == ["2026-10-02"]
    assert db["registros"][0]["entrada"] == "08:15:00"
    assert db["registros"][0]["saida"] == "15:15:00"
    assert db["registros"][0]["inicio_pausa"] is None
    assert db["registros"][0]["meta_dia"] == 6.0
    assert "pin_estagiario" not in json.dumps(db)
    assert planilha["chamadas"][0]["corpo"]["acao"] == "listar"


def test_falha_na_leitura_usa_cache_local_e_avisa(planilha, tmp_path, monkeypatch):
    cache = tmp_path / "ponto_eletronico.json"
    cache.write_text(json.dumps({"registros": [REG_02_10]}), encoding="utf-8")
    monkeypatch.setattr(storage, "DEFAULT_DATA_PATH", str(cache))
    planilha["resposta"] = FakeResposta({"ok": False, "erro": "não autorizado"})
    avisos = []
    db = storage.load_database(str(cache), avisos=avisos)
    assert [r["data"] for r in db["registros"]] == ["2026-10-02"]
    assert len(avisos) == 1 and "não autorizado" in avisos[0]


def test_cache_local_nao_guarda_configuracao_nem_senha(tmp_path):
    cache = tmp_path / "cache.json"
    storage.save_database({"config": {"pin_estagiario": "9999"}, "registros": [REG_02_10]}, str(cache))
    conteudo = json.loads(cache.read_text(encoding="utf-8"))
    assert conteudo == {"registros": [REG_02_10]}


def test_sem_secrets_nao_tenta_nuvem(monkeypatch):
    monkeypatch.delenv("APPS_SCRIPT_URL", raising=False)
    monkeypatch.delenv("APPS_SCRIPT_SECRET", raising=False)
    monkeypatch.setattr(storage, "_get_secret_or_default", lambda k, d="": "")
    assert storage.is_cloud_configured() is False
    assert storage.enviar_pendentes({"2026-10-02": REG_02_10}) == ({}, None)


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

def test_senha_correta_e_errada():
    h = auth.gerar_hash_senha("abc-123", iteracoes=1000)
    assert auth.verificar_senha("abc-123", h)
    assert not auth.verificar_senha("abc-124", h)
    assert not auth.verificar_senha("abc-123", "")
    assert not auth.verificar_senha("abc-123", "lixo")
    assert h != auth.gerar_hash_senha("abc-123", iteracoes=1000)  # salt aleatório


def test_token_valido_adulterado_e_expirado():
    agora = 1_800_000_000
    tok = auth.gerar_token_login("estagiario", "s3gr3do", dias=30, agora=agora)
    assert auth.validar_token_login(tok, "s3gr3do", agora=agora + 3600) == "estagiario"
    assert auth.validar_token_login(tok, "outro", agora=agora) is None
    assert auth.validar_token_login(tok.replace("estagiario", "gestao", 1), "s3gr3do", agora=agora) is None
    perfil, expira, assinatura = tok.split(".")
    assert auth.validar_token_login(f"{perfil}.{int(expira) + 999}.{assinatura}", "s3gr3do", agora=agora) is None
    assert auth.validar_token_login(tok, "s3gr3do", agora=agora + 31 * 24 * 3600) is None
    assert auth.validar_token_login(None, "s3gr3do") is None
    assert auth.validar_token_login("a.b", "s3gr3do") is None
    with pytest.raises(ValueError):
        auth.gerar_token_login("admin", "s3gr3do")


SENHA_TESTE = "senha-de-teste"
SENHA_CHEFIA_TESTE = "chefia-de-teste"


def _app_de_teste():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("app.py", default_timeout=30)
    at.secrets["usuario_estagiario"] = "carlos"
    at.secrets["senha_estagiario_hash"] = auth.gerar_hash_senha(SENHA_TESTE, iteracoes=1000)
    at.secrets["senha_chefia_hash"] = auth.gerar_hash_senha(SENHA_CHEFIA_TESTE, iteracoes=1000)
    at.secrets["cookie_secret"] = "cookie-secret-de-teste"
    return at


@pytest.fixture
def app_offline(monkeypatch, tmp_path):
    """Roda o app sem planilha e com cache vazio em pasta temporária."""
    monkeypatch.delenv("APPS_SCRIPT_URL", raising=False)
    monkeypatch.delenv("APPS_SCRIPT_SECRET", raising=False)
    monkeypatch.setattr(storage, "is_cloud_configured", lambda: False)
    monkeypatch.setattr(storage, "DEFAULT_DATA_PATH", str(tmp_path / "ponto_eletronico.json"))
    return _app_de_teste()


def _html_da_pagina(at) -> str:
    return " ".join(str(getattr(el, "proto", el)) for el in at.main)


def test_tela_de_login_nao_expoe_token_nem_senha(app_offline):
    at = app_offline.run()
    assert not at.exception
    pagina = _html_da_pagina(at)
    assert "cookie-secret-de-teste" not in pagina
    assert "pbkdf2_sha256" not in pagina
    assert "localStorage.getItem" not in pagina
    assert "token" not in pagina.lower()


def test_login_estagiario_senha_errada_e_certa(app_offline):
    at = app_offline.run()
    at.text_input[0].input("carlos")
    at.text_input[1].input("errada")
    at.button[0].click().run()
    assert any("incorretos" in e.value for e in at.error)
    assert at.session_state["perfil_ativo"] is None

    at.text_input[0].input("carlos")
    at.text_input[1].input(SENHA_TESTE)
    at.button[0].click().run()
    assert not at.exception
    assert at.session_state["perfil_ativo"] == "estagiario"


def test_chefia_exige_senha(app_offline):
    at = app_offline.run()
    campo_chefia = [t for t in at.text_input if "chefia" in t.label.lower()][0]
    botao_chefia = [b for b in at.button if "SUPERVISOR" in b.label][0]
    campo_chefia.input("")
    botao_chefia.click().run()
    assert at.session_state["perfil_ativo"] is None

    campo_chefia = [t for t in at.text_input if "chefia" in t.label.lower()][0]
    botao_chefia = [b for b in at.button if "SUPERVISOR" in b.label][0]
    campo_chefia.input(SENHA_CHEFIA_TESTE)
    botao_chefia.click().run()
    assert not at.exception
    assert at.session_state["perfil_ativo"] == "gestao"


# ---------------------------------------------------------------------------
# HTML escapado e nenhum segredo no código versionado
# ---------------------------------------------------------------------------

def test_observacao_com_script_e_escapada_no_boletim():
    reg = dict(REG_02_10, data="2026-10-02", observacao="<script>alert(1)</script>")
    cfg = {"nome_estagiario": "<b>Fulano</b>", "empresa_setor": "<i>x</i>", "carga_horaria_diaria": 6.0}
    html_fusp = generate_fusp_timesheet_html([reg], cfg, 2026, 10)
    assert "<script>alert(1)</script>" not in html_fusp
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_fusp
    assert "<b>Fulano</b>" not in html_fusp
    assert "&lt;b&gt;Fulano&lt;/b&gt;" in html_fusp


def test_nenhum_segredo_ou_dado_pessoal_no_codigo():
    raiz = Path(__file__).parent
    arquivos = [p for padrao in ("*.py", "*.gs", "apps_script/*.gs", ".streamlit/*.example", "*.md", "docs/*.md")
                for p in raiz.glob(padrao) if p.name != Path(__file__).name]
    proibidos = [
        r"script\.google\.com/macros/s/AK",          # URL real do Apps Script
        r"docs\.google\.com/spreadsheets/d/[\w-]{20,}",  # ID real da planilha
        r"pbkdf2_sha256\$\d+\$[0-9a-f]{32}\$",        # hash real de senha
        r"pin_estagiario",
        r"Marreta",
        r"\b1122\b",
    ]
    for arq in arquivos:
        if arq.name in ("projeto_completo.md",):
            continue
        texto = arq.read_text(encoding="utf-8", errors="ignore")
        for padrao in proibidos:
            assert not re.search(padrao, texto), f"{arq.name} contém {padrao}"


if __name__ == "__main__":
    test_all()
