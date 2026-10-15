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
    "nome_estagiario": "Estagiário(a)",
    "nome_supervisor": "Gestor(a) / Supervisor(a)",
    "empresa_setor": "ICMC / USP",
    "pin_estagiario": "",
}


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
            # Alterna variações para demonstrar saldo positivo e negativo
            if i % 3 == 0:
                # 6h15 trabalhadas (+15 min)
                entrada = "09:00:00"
                ini_p = "12:00:00"
                fim_p = "12:15:00"
                saida = "15:30:00"
                obs = "Estudo técnico"
            elif i % 3 == 1:
                # 5h50 trabalhadas (-10 min)
                entrada = "09:05:00"
                ini_p = "12:30:00"
                fim_p = "12:45:00"
                saida = "15:10:00"
                obs = "Compromisso acadêmico"
            else:
                # 6h cravadas
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
    """Verifica se o Google Sheets está configurado via Apps Script ou Service Account."""
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
    return v_str[:10]


def load_database_from_apps_script(url: str) -> Dict[str, Any]:
    """Lê registros e configurações via Web App do Google Apps Script com normalização."""
    import requests
    resp = requests.get(url, timeout=12)
    if resp.status_code == 200:
        data = resp.json()
        raw_records = []
        cfg = DEFAULT_CONFIG.copy()
        if isinstance(data, list):
            raw_records = data
        elif isinstance(data, dict):
            raw_records = data.get("registros", [])
            cfg.update(data.get("config", {}))

        cleaned_records = []
        for r in raw_records:
            d_val = _clean_cloud_date(r.get("data"))
            if not d_val:
                continue
            cleaned_records.append({
                "data": d_val,
                "entrada": _clean_cloud_time(r.get("entrada")),
                "inicio_pausa": _clean_cloud_time(r.get("inicio_pausa")),
                "fim_pausa": _clean_cloud_time(r.get("fim_pausa")),
                "saida": _clean_cloud_time(r.get("saida")),
                "meta_dia": float(r.get("meta_dia", 6.0)) if r.get("meta_dia") else 6.0,
                "observacao": str(r.get("observacao", "") or ""),
            })

        return {"config": cfg, "registros": cleaned_records}
    raise Exception(f"HTTP {resp.status_code}: {resp.text[:150]}")


def save_database_to_apps_script(url: str, data: Dict[str, Any]):
    """Envia novos registros para a planilha via Web App do Google Apps Script."""
    import requests
    resp = requests.post(url, json=data, timeout=15)
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
        if not data_val:
            continue
        registros.append({
            "data": data_val,
            "entrada": str(r.get("entrada", "")).strip() if r.get("entrada") else None,
            "inicio_pausa": str(r.get("inicio_pausa", "")).strip() if r.get("inicio_pausa") else None,
            "fim_pausa": str(r.get("fim_pausa", "")).strip() if r.get("fim_pausa") else None,
            "saida": str(r.get("saida", "")).strip() if r.get("saida") else None,
            "meta_dia": float(r.get("meta_dia", 6.0)) if r.get("meta_dia") else 6.0,
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


def load_database(filepath: str = DEFAULT_DATA_PATH) -> Dict[str, Any]:
    """
    Carrega o banco de dados.
    Se a nuvem estiver configurada (Apps Script ou gspread), lê de lá e atualiza o cache local.
    Caso contrário ou offline, utiliza o arquivo JSON local.
    """
    if is_cloud_configured():
        try:
            import streamlit as st
            if "apps_script_url" in st.secrets:
                cloud_data = load_database_from_apps_script(st.secrets["apps_script_url"])
            else:
                cloud_data = load_database_from_sheets()

            # Mantém cópia local sincronizada como backup
            save_database(cloud_data, filepath)
            return cloud_data
        except Exception as e:
            print(f"Aviso: Não foi possível conectar ao Google Sheets ({e}). Usando base local.")

    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
                if "config" not in data:
                    data["config"] = DEFAULT_CONFIG.copy()
                if "registros" not in data:
                    data["registros"] = []
                return data
        except Exception as e:
            print(f"Erro ao carregar {filepath}: {e}")

    initial_data = {
        "config": DEFAULT_CONFIG.copy(),
        "registros": [],
    }
    save_database(initial_data, filepath)
    return initial_data


def save_database(data: Dict[str, Any], filepath: str = DEFAULT_DATA_PATH) -> bool:
    """
    Salva os dados de forma segura no JSON local e, se a nuvem estiver ativa,
    sincroniza em tempo real com o Google Sheets.
    """
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

    # Sincronização em nuvem se habilitada
    if is_cloud_configured():
        try:
            import streamlit as st
            if "apps_script_url" in st.secrets:
                save_database_to_apps_script(st.secrets["apps_script_url"], data)
            else:
                save_database_to_sheets(data)
        except Exception as e:
            print(f"Aviso: Erro ao sincronizar com Google Sheets: {e}")

    return saved_local

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
