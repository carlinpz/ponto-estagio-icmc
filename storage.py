"""
Módulo de Persistência e Gerenciamento de Dados do Ponto Eletrônico.
Salva e carrega dados em JSON local (ponto_eletronico.json), com suporte a exportação CSV.
"""

import json
import os
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd

DEFAULT_DATA_PATH = os.path.join(os.path.dirname(__file__), "ponto_eletronico.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    "carga_horaria_diaria": 6.0,
    "dias_uteis": [
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira",
    ],
    "nome_estagiario": "Carlos Henrique da Luz Pizzi",
    "nome_supervisor": "Maria Fernanda Marreta",
    "empresa_setor": "605001",
    "usuario_estagiario": "carlos",
    "pin_estagiario": "1122",
}

DEFAULT_SPREADSHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1-1XDAVUDdAGK-OUfCog8bDizN8Ax-oeHfl81rHlxfmI/export?format=csv"
DEFAULT_APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyq1Mkm5VjbTd-A48DyCkNBnWmzRbC4fsVjqFuumBHLep7JNaqGA33jHJUjAz023jO8xA/exec"


def _deduplicate_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove registros duplicados da mesma data, mantendo sempre a versão mais recente."""
    dedup: Dict[str, Dict[str, Any]] = {}
    for r in records:
        d_val = str(r.get("data", "")).strip()
        if not d_val or d_val in ("CONFIG_JSON", "__CONFIG__"):
            continue
        dedup[d_val] = r
    result = list(dedup.values())
    result.sort(key=lambda x: str(x.get("data", "")))
    return result


def _merge_configs(base: Dict[str, Any], override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Mescla configurações preservando credenciais e dados cadastrais válidos,
    impedindo que strings vazias ou placeholders genéricos apaguem a senha/usuário salvos.
    """
    result = DEFAULT_CONFIG.copy()
    if isinstance(base, dict):
        for k, v in base.items():
            if v is not None and str(v).strip() != "":
                if k == "nome_estagiario" and str(v).strip() == "Estagiário(a)" and result.get(k) != "Estagiário(a)":
                    continue
                if k == "nome_supervisor" and str(v).strip() == "Gestor(a) / Supervisor(a)" and result.get(k) != "Gestor(a) / Supervisor(a)":
                    continue
                if k == "empresa_setor" and str(v).strip() == "ICMC / USP" and result.get(k) == "605001":
                    continue
                result[k] = v

    if isinstance(override, dict):
        for k, v in override.items():
            if v is not None and str(v).strip() != "":
                if k == "nome_estagiario" and str(v).strip() == "Estagiário(a)" and result.get(k) != "Estagiário(a)":
                    continue
                if k == "nome_supervisor" and str(v).strip() == "Gestor(a) / Supervisor(a)" and result.get(k) != "Gestor(a) / Supervisor(a)":
                    continue
                if k == "empresa_setor" and str(v).strip() == "ICMC / USP" and result.get(k) == "605001":
                    continue
                result[k] = v

    return result


def _parse_meta_dia(v: Any, obs: str = "", default: float = 6.0) -> float:
    """Converte meta_dia preservando 0.0 em feriados/abonos."""
    if v is not None and str(v).strip() != "":
        try:
            return float(v)
        except ValueError:
            pass
    if any(k in str(obs).lower() for k in ("feriado", "recesso", "dispensa", "abono", "folga")):
        return 0.0
    return default


def generate_sample_records_if_empty(target_hours: float = 6.0) -> List[Dict[str, Any]]:
    """
    Gera alguns registros de exemplo no mês atual para que o usuário
    possa visualizar o funcionamento do dashboard e dos gráficos imediatamente.
    """
    hoje = date.today()
    sample_records = []
    
    # Gera registros para os dias úteis passados dos últimos 10 dias
    for i in range(12, 0, -1):
        dia = hoje - timedelta(days=i)
        # Segunda a Sexta: 0 a 4
        if dia.weekday() < 5:
            if i % 3 == 0:
                entrada = "09:00:00"
                ini_p = "12:00:00"
                fim_p = "12:15:00"
                saida = "15:30:00"
                obs = "Estudo técnico"
            elif i % 3 == 1:
                entrada = "09:05:00"
                ini_p = "12:30:00"
                fim_p = "12:45:00"
                saida = "15:10:00"
                obs = "Compromisso acadêmico"
            else:
                entrada = "09:00:00"
                ini_p = "12:00:00"
                fim_p = "12:15:00"
                saida = "15:15:00"
                obs = "Jornada regular"

            sample_records.append({
                "data": dia.strftime("%Y-%m-%d"),
                "entrada": entrada,
                "inicio_pausa": ini_p,
                "fim_pausa": fim_p,
                "saida": saida,
                "meta_dia": target_hours,
                "observacao": obs,
            })

    return sample_records


def is_cloud_configured() -> bool:
    """Verifica se o Google Sheets está configurado via Apps Script, URL padrão ou Service Account."""
    if DEFAULT_APPS_SCRIPT_URL:
        return True
    try:
        import streamlit as st
        return "apps_script_url" in st.secrets or ("gcp_service_account" in st.secrets and "spreadsheet_url" in st.secrets)
    except Exception:
        return False


def _clean_cloud_time(v: Optional[str]) -> Optional[str]:
    """Extrai HH:MM:SS de strings limpas ou de formatos JavaScript Date."""
    if not v:
        return None
    v_str = str(v).strip()
    if not v_str or v_str.lower() in ("none", "null", ""):
        return None
    import re
    m = re.search(r"(\d{2}:\d{2}:\d{2})", v_str)
    if m:
        return m.group(1)
    m2 = re.search(r"(\d{2}:\d{2})", v_str)
    if m2:
        return m2.group(1) + ":00"
    return v_str


def _clean_cloud_date(v: Optional[str]) -> Optional[str]:
    """Extrai YYYY-MM-DD de strings limpas ou de formatos JavaScript Date."""
    if not v:
        return None
    v_str = str(v).strip()
    if v_str in ("CONFIG_JSON", "__CONFIG__"):
        return "CONFIG_JSON"
    import re
    # Verifica padrão YYYY-MM-DD
    m = re.search(r"(\d{4}-\d{2}-\d{2})", v_str)
    if m:
        return m.group(1)
    # Verifica formato 'Mon Sep 28 2026'
    meses_en = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
    m_full = re.search(r"([A-Za-z]{3})\s+(\d{1,2})\s+(\d{4})", v_str)
    if m_full:
        mes_num = meses_en.get(m_full.group(1), 1)
        dia_num = int(m_full.group(2))
        ano_num = int(m_full.group(3))
        return f"{ano_num:04d}-{mes_num:02d}-{dia_num:02d}"
    return None


def load_database_from_sheet_csv(sheet_url: str = DEFAULT_SPREADSHEET_CSV_URL) -> Dict[str, Any]:
    """Lê registros e configurações diretamente da exportação CSV da planilha do Google Docs (<0.5s)."""
    import urllib.request
    import csv
    import io
    import re
    import time

    csv_url = sheet_url
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if m:
        sheet_id = m.group(1)
        # Cache-buster para garantir leitura em tempo real sem cache antigo do CDN
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&t={int(time.time())}"

    req = urllib.request.Request(
        csv_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        text = resp.read().decode("utf-8")

    reader = csv.DictReader(io.StringIO(text))
    records = []
    cloud_cfg: Dict[str, Any] = {}

    for r in reader:
        raw_d = str(r.get("data", "")).strip()
        if raw_d in ("CONFIG_JSON", "__CONFIG__"):
            obs_cfg = str(r.get("observacao", "") or "").strip()
            if obs_cfg:
                try:
                    parsed_cfg = json.loads(obs_cfg)
                    if isinstance(parsed_cfg, dict):
                        cloud_cfg.update(parsed_cfg)
                except Exception:
                    pass
            continue

        d_val = _clean_cloud_date(raw_d)
        if not d_val or d_val == "CONFIG_JSON":
            continue
        obs_str = str(r.get("observacao", "") or "")
        records.append({
            "data": d_val,
            "entrada": _clean_cloud_time(r.get("entrada")),
            "inicio_pausa": _clean_cloud_time(r.get("inicio_pausa")),
            "fim_pausa": _clean_cloud_time(r.get("fim_pausa")),
            "saida": _clean_cloud_time(r.get("saida")),
            "meta_dia": _parse_meta_dia(r.get("meta_dia"), obs_str, 6.0),
            "observacao": obs_str,
        })

    return {"config": cloud_cfg, "registros": _deduplicate_records(records)}


def load_database_from_apps_script(url: str) -> Dict[str, Any]:
    """Lê registros e configurações via Web App do Google Apps Script com normalização."""
    import requests
    resp = requests.get(url, timeout=20)
    if resp.status_code == 200:
        data = resp.json()
        raw_records = []
        cloud_cfg: Dict[str, Any] = {}
        if isinstance(data, list):
            raw_records = data
        elif isinstance(data, dict):
            raw_records = data.get("registros", [])
            if isinstance(data.get("config"), dict):
                cloud_cfg.update(data.get("config", {}))

        cleaned_records = []
        for r in raw_records:
            raw_d = str(r.get("data", "")).strip()
            if raw_d in ("CONFIG_JSON", "__CONFIG__"):
                obs_cfg = str(r.get("observacao", "") or "").strip()
                if obs_cfg:
                    try:
                        parsed_cfg = json.loads(obs_cfg)
                        if isinstance(parsed_cfg, dict):
                            cloud_cfg.update(parsed_cfg)
                    except Exception:
                        pass
                continue

            d_val = _clean_cloud_date(raw_d)
            if not d_val or d_val == "CONFIG_JSON":
                continue
            obs_str = str(r.get("observacao", "") or "")
            cleaned_records.append({
                "data": d_val,
                "entrada": _clean_cloud_time(r.get("entrada")),
                "inicio_pausa": _clean_cloud_time(r.get("inicio_pausa")),
                "fim_pausa": _clean_cloud_time(r.get("fim_pausa")),
                "saida": _clean_cloud_time(r.get("saida")),
                "meta_dia": _parse_meta_dia(r.get("meta_dia"), obs_str, 6.0),
                "observacao": obs_str,
            })

        return {"config": cloud_cfg, "registros": _deduplicate_records(cleaned_records)}
    raise Exception(f"HTTP {resp.status_code}: {resp.text[:150]}")


def save_database_to_apps_script(url: str, data: Dict[str, Any]):
    """Envia registros e configurações (em linha metadado CONFIG_JSON) para a planilha via Apps Script."""
    import requests
    clean_regs = _deduplicate_records(data.get("registros", []))
    cfg_row = {
        "data": "CONFIG_JSON",
        "entrada": "",
        "inicio_pausa": "",
        "fim_pausa": "",
        "saida": "",
        "meta_dia": 0,
        "observacao": json.dumps(data.get("config", {}), ensure_ascii=False),
    }
    payload = {
        "config": data.get("config", {}),
        "registros": clean_regs + [cfg_row],
    }
    resp = requests.post(url, json=payload, timeout=35)
    if resp.status_code not in (200, 201):
        raise Exception(f"HTTP {resp.status_code}: {resp.text[:150]}")


def get_gspread_client():
    """Retorna cliente autenticado do Google Sheets usando as credenciais do Streamlit."""
    import streamlit as st
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    sa_info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    return gspread.authorize(creds)


def load_database_from_sheets() -> Dict[str, Any]:
    """Lê registros e configurações diretamente da planilha do Google Drive via gspread."""
    import streamlit as st
    client = get_gspread_client()
    sheet_url = st.secrets["spreadsheet_url"]
    sh = client.open_by_url(sheet_url)

    # 1. Carrega registros
    try:
        ws_reg = sh.worksheet("Registros")
        records_data = ws_reg.get_all_records()
    except Exception:
        ws_reg = sh.sheet1
        records_data = ws_reg.get_all_records()

    registros = []
    for r in records_data:
        data_val = str(r.get("data", "")).strip()
        if not data_val or data_val in ("CONFIG_JSON", "__CONFIG__"):
            continue
        registros.append({
            "data": data_val,
            "entrada": str(r.get("entrada", "")).strip() if r.get("entrada") else None,
            "inicio_pausa": str(r.get("inicio_pausa", "")).strip() if r.get("inicio_pausa") else None,
            "fim_pausa": str(r.get("fim_pausa", "")).strip() if r.get("fim_pausa") else None,
            "saida": str(r.get("saida", "")).strip() if r.get("saida") else None,
            "meta_dia": _parse_meta_dia(r.get("meta_dia"), 6.0),
            "observacao": str(r.get("observacao", "")),
        })

    # 2. Carrega configurações da aba Config (se existir)
    config = DEFAULT_CONFIG.copy()
    try:
        ws_cfg = sh.worksheet("Config")
        cfg_rows = ws_cfg.get_all_records()
        for row in cfg_rows:
            k = row.get("chave")
            v = row.get("valor")
            if k and v is not None:
                if k == "carga_horaria_diaria":
                    config[k] = float(v)
                elif k == "dias_uteis" and isinstance(v, str):
                    config[k] = [d.strip() for d in v.split(",") if d.strip()]
                else:
                    config[k] = v
    except Exception:
        pass

    return {"config": config, "registros": registros}


def save_database_to_sheets(data: Dict[str, Any]):
    """Sincroniza os dados locais de volta para a planilha do Google Sheets via gspread."""
    import streamlit as st
    client = get_gspread_client()
    sheet_url = st.secrets["spreadsheet_url"]
    sh = client.open_by_url(sheet_url)

    # Atualiza aba Registros
    try:
        ws_reg = sh.worksheet("Registros")
    except Exception:
        ws_reg = sh.sheet1

    cols = ["data", "entrada", "inicio_pausa", "fim_pausa", "saida", "meta_dia", "observacao"]
    rows = [cols]
    for r in data.get("registros", []):
        if str(r.get("data", "")).strip() in ("CONFIG_JSON", "__CONFIG__", ""):
            continue
        rows.append([
            r.get("data", ""),
            r.get("entrada") or "",
            r.get("inicio_pausa") or "",
            r.get("fim_pausa") or "",
            r.get("saida") or "",
            r.get("meta_dia", 6.0),
            r.get("observacao", ""),
        ])
    ws_reg.clear()
    ws_reg.update(rows)

    # Atualiza aba Config
    try:
        ws_cfg = sh.worksheet("Config")
    except Exception:
        ws_cfg = sh.add_worksheet(title="Config", rows=20, cols=5)

    cfg_rows = [["chave", "valor"]]
    for k, v in data.get("config", {}).items():
        if isinstance(v, list):
            val_str = ", ".join(v)
        else:
            val_str = str(v)
        cfg_rows.append([k, val_str])
    ws_cfg.clear()
    ws_cfg.update(cfg_rows)


def _get_secret_or_default(key: str, default_val: str) -> str:
    """Obtém uma chave do st.secrets com fallback seguro para o valor padrão."""
    try:
        import streamlit as st
        val = st.secrets.get(key, default_val)
        return val if val else default_val
    except Exception:
        return default_val


def load_database(filepath: str = DEFAULT_DATA_PATH) -> Dict[str, Any]:
    """
    Carrega o banco de dados.
    Lê com prioridade da planilha na nuvem (Google Sheets CSV rápido ou Apps Script)
    e sincroniza o cache local, preservando sempre as configurações e credenciais.
    Em caso de offline, usa o arquivo local.
    """
    # Carrega estado local primeiro para preservar configurações e comparar registros
    local_cfg = DEFAULT_CONFIG.copy()
    local_records = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, dict):
                    local_records = _deduplicate_records(d.get("registros", []))
                    if "config" in d and isinstance(d["config"], dict):
                        local_cfg = _merge_configs(local_cfg, d["config"])
        except Exception:
            pass

    use_cloud = os.path.abspath(filepath) == os.path.abspath(DEFAULT_DATA_PATH)
    cloud_data = None

    if use_cloud:
        # 1. Tenta carregar instantaneamente do Google Sheets CSV (sub-segundo)
        sheet_url = _get_secret_or_default("spreadsheet_url", DEFAULT_SPREADSHEET_CSV_URL)
        if sheet_url:
            try:
                cloud_data = load_database_from_sheet_csv(sheet_url)
            except Exception:
                pass

        # 2. Se não conseguiu pelo CSV, tenta pelo Apps Script
        if not cloud_data or not cloud_data.get("registros"):
            apps_url = _get_secret_or_default("apps_script_url", DEFAULT_APPS_SCRIPT_URL)
            if apps_url:
                try:
                    cloud_data = load_database_from_apps_script(apps_url)
                except Exception:
                    pass

    # 3. Se temos dados da nuvem e eles são consistentes, mescla com configurações locais
    if cloud_data and cloud_data.get("registros"):
        cloud_records = _deduplicate_records(cloud_data.get("registros", []))
        if len(cloud_records) > 0:
            merged_cfg = _merge_configs(local_cfg, cloud_data.get("config", {}))
            result_data = {
                "config": merged_cfg,
                "registros": cloud_records,
            }
            save_database(result_data, filepath, sync_cloud=False)
            return result_data

    # 4. Fallback para dados locais se disponíveis
    if local_records or os.path.exists(filepath):
        result_data = {
            "config": local_cfg,
            "registros": local_records,
        }
        return result_data

    initial_data = {
        "config": DEFAULT_CONFIG.copy(),
        "registros": [],
    }
    save_database(initial_data, filepath, sync_cloud=False)
    return initial_data


def save_database(data: Dict[str, Any], filepath: str = DEFAULT_DATA_PATH, sync_cloud: bool = True) -> bool:
    """
    Salva os dados de forma segura no JSON local e, se sync_cloud for True e a nuvem estiver ativa,
    sincroniza em tempo real com o Google Sheets.
    """
    # Garante que CONFIG_JSON e duplicatas nunca fiquem na lista em memória/JSON local
    if "registros" in data and isinstance(data["registros"], list):
        data["registros"] = _deduplicate_records(data["registros"])
    if "config" in data and isinstance(data["config"], dict):
        data["config"] = _merge_configs(DEFAULT_CONFIG, data["config"])

    saved_local = False
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        temp_path = filepath + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(filepath):
            os.replace(temp_path, filepath)
        else:
            os.rename(temp_path, filepath)
        saved_local = True
    except Exception as e:
        print(f"Erro ao salvar localmente em {filepath}: {e}")

    # Sincronização em nuvem se solicitada e habilitada
    if sync_cloud and is_cloud_configured():
        try:
            apps_url = _get_secret_or_default("apps_script_url", DEFAULT_APPS_SCRIPT_URL)
            if apps_url:
                save_database_to_apps_script(apps_url, data)
            else:
                save_database_to_sheets(data)
        except Exception as e:
            print(f"Aviso: Erro ao sincronizar com Google Sheets: {e}")

    return saved_local


def get_record_by_date(registros: List[Dict[str, Any]], data_str: str) -> Optional[Dict[str, Any]]:
    """Busca registro por data no formato YYYY-MM-DD."""
    for r in registros:
        if r.get("data") == data_str:
            return r
    return None


def upsert_record(registros: List[Dict[str, Any]], novo_registro: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Insere ou atualiza um registro com base no campo 'data'."""
    data_alvo = novo_registro.get("data")
    encontrado = False
    novos = []
    for r in registros:
        if r.get("data") == data_alvo:
            novos.append(novo_registro)
            encontrado = True
        else:
            novos.append(r)
    if not encontrado:
        novos.append(novo_registro)

    # Ordena por data
    novos.sort(key=lambda x: x.get("data", ""))
    return novos


def delete_record_by_date(registros: List[Dict[str, Any]], data_str: str) -> List[Dict[str, Any]]:
    """Remove registro correspondente à data informada."""
    return [r for r in registros if r.get("data") != data_str]


def export_df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Exporta DataFrame para bytes CSV em UTF-8 com BOM para Excel no Windows."""
    colunas_export = [
        "Data", "Dia da Semana", "Entrada", "Início Pausa", "Fim Pausa",
        "Saída", "Horas Formatadas", "Saldo Formatado", "Status", "Observação"
    ]
    cols = [c for c in colunas_export if c in df.columns]
    csv_str = df[cols].to_csv(index=False, sep=";", encoding="utf-8-sig")
    return csv_str.encode("utf-8-sig")
