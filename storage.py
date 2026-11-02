"""
Módulo de Persistência e Gerenciamento de Dados do Ponto Eletrônico.

- Fonte da verdade: planilha Google, acessada pelo Web App do Apps Script (`apps_script/Code.gs`).
- Cada alteração envia SÓ o(s) registro(s) alterado(s) (gravar/excluir por data), de forma síncrona:
  se a planilha não confirmar, o erro sobe para a interface (nada de falha silenciosa).
- `ponto_eletronico.json` é só um cache local dos registros (sem configurações nem credenciais).
- Configurações pessoais (nomes, setor) vêm de st.secrets, seção [perfil].
"""

import json
import os
from typing import Dict, Any, List, Optional, Tuple
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
    "nome_supervisor": "Supervisor(a)",
    "empresa_setor": "",
}

CAMPOS_REGISTRO = ("data", "entrada", "inicio_pausa", "fim_pausa", "saida", "meta_dia", "observacao")


class CloudSyncError(Exception):
    """Falha ao ler ou gravar na planilha (rede, segredo errado, Apps Script desatualizado...)."""


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


def _parse_meta_dia(v: Any, obs: str = "", default: float = 6.0) -> float:
    """Converte meta_dia preservando 0.0 em feriados/abonos."""
    if v is not None and str(v).strip() != "":
        try:
            return float(str(v).replace(",", "."))
        except ValueError:
            pass
    if any(k in str(obs).lower() for k in ("feriado", "recesso", "dispensa", "abono", "folga")):
        return 0.0
    return default


def _get_secret_or_default(key: str, default_val: str = "") -> str:
    """Obtém uma chave de st.secrets ou variáveis de ambiente (os.environ) com fallback para o valor padrão."""
    env_val = os.environ.get(key) or os.environ.get(key.upper())
    if env_val and str(env_val).strip():
        return str(env_val).strip()
    try:
        import streamlit as st
        val = st.secrets.get(key, default_val)
        return str(val).strip() if val else default_val
    except Exception:
        return default_val


def load_config() -> Dict[str, Any]:
    """Configuração do app: padrões do contrato + dados pessoais da seção [perfil] de st.secrets."""
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        import streamlit as st
        perfil = st.secrets.get("perfil", {})
        for k in DEFAULT_CONFIG:
            if k in perfil and perfil[k] not in (None, ""):
                config[k] = list(perfil[k]) if k == "dias_uteis" else perfil[k]
    except Exception:
        pass
    config["carga_horaria_diaria"] = float(config["carga_horaria_diaria"])
    return config


def is_cloud_configured() -> bool:
    """A planilha só é usada quando a URL do Apps Script E o segredo compartilhado estão em secrets."""
    return bool(_get_secret_or_default("apps_script_url") and _get_secret_or_default("apps_script_secret"))


def _clean_cloud_time(v: Optional[str]) -> Optional[str]:
    """Extrai HH:MM:SS de strings limpas ou de formatos JavaScript Date."""
    if not v:
        return None
    v_str = str(v).strip()
    if not v_str or v_str.lower() in ("none", "null", ""):
        return None
    import re
    m = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", v_str)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}:{m.group(3) or '00'}"
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


def _normalizar_registro(r: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Converte um registro vindo da planilha para o formato interno; ignora linhas inválidas e CONFIG_JSON."""
    d_val = _clean_cloud_date(str(r.get("data", "")).strip())
    if not d_val or d_val == "CONFIG_JSON":
        return None
    obs_str = str(r.get("observacao", "") or "")
    return {
        "data": d_val,
        "entrada": _clean_cloud_time(r.get("entrada")),
        "inicio_pausa": _clean_cloud_time(r.get("inicio_pausa")),
        "fim_pausa": _clean_cloud_time(r.get("fim_pausa")),
        "saida": _clean_cloud_time(r.get("saida")),
        "meta_dia": _parse_meta_dia(r.get("meta_dia"), obs_str, 6.0),
        "observacao": obs_str,
    }


VERSAO_PROTOCOLO = 2
_urls_confirmadas: set = set()


def _confirmar_versao_apps_script(url: str) -> None:
    """
    Antes do primeiro POST, confere (por GET, que não altera nada) se o Apps Script é a versão nova.
    O script antigo trata qualquer POST como "substituir a planilha inteira": mandar
    {"acao": "listar"} para ele poderia apagar todos os registros.
    """
    import requests

    if url in _urls_confirmadas:
        return
    try:
        dados = requests.get(url, timeout=30).json()
    except (requests.RequestException, ValueError) as e:
        raise CloudSyncError(f"Não foi possível conferir a versão do Apps Script ({type(e).__name__}).") from e
    if not isinstance(dados, dict) or dados.get("versao") != VERSAO_PROTOCOLO:
        raise CloudSyncError("O Apps Script publicado é a versão antiga. Atualize-o com apps_script/Code.gs.")
    _urls_confirmadas.add(url)


def _chamar_apps_script(acao: str, **campos: Any) -> Dict[str, Any]:
    """
    Faz UMA chamada ao Web App do Apps Script e devolve a resposta já validada.
    Toda chamada leva o segredo compartilhado no corpo (nunca na URL).
    Qualquer resposta que não seja {"ok": true, ...} vira CloudSyncError.
    """
    import requests

    url = _get_secret_or_default("apps_script_url")
    segredo = _get_secret_or_default("apps_script_secret")
    if not url or not segredo:
        raise CloudSyncError("Planilha não configurada (faltam apps_script_url / apps_script_secret em secrets).")

    _confirmar_versao_apps_script(url)
    try:
        resp = requests.post(url, json={"segredo": segredo, "acao": acao, **campos}, timeout=30)
    except requests.RequestException as e:
        raise CloudSyncError(f"Sem conexão com a planilha ({type(e).__name__}).") from e

    if resp.status_code != 200:
        raise CloudSyncError(f"A planilha respondeu HTTP {resp.status_code}.")
    try:
        dados = resp.json()
    except ValueError:
        raise CloudSyncError("Resposta inesperada da planilha (o Apps Script está na versão nova?).")
    if not isinstance(dados, dict) or dados.get("ok") is not True:
        erro = dados.get("erro") if isinstance(dados, dict) else None
        raise CloudSyncError(f"A planilha recusou a operação: {erro or 'resposta sem ok=true'}.")
    return dados


def load_records_from_cloud() -> List[Dict[str, Any]]:
    """Lê todos os registros da planilha (sem a linha CONFIG_JSON)."""
    dados = _chamar_apps_script("listar")
    brutos = dados.get("registros", [])
    if not isinstance(brutos, list):
        raise CloudSyncError("Resposta da planilha sem lista de registros.")
    normalizados = [r for r in (_normalizar_registro(x) for x in brutos if isinstance(x, dict)) if r]
    return _deduplicate_records(normalizados)


def _registro_para_envio(r: Dict[str, Any]) -> Dict[str, Any]:
    """Mantém só as colunas da planilha, com valores simples (texto ou número)."""
    envio = {k: r.get(k) for k in CAMPOS_REGISTRO}
    for k in ("entrada", "inicio_pausa", "fim_pausa", "saida", "observacao"):
        envio[k] = "" if envio[k] is None else str(envio[k])
    envio["meta_dia"] = float(envio["meta_dia"]) if envio["meta_dia"] not in (None, "") else 6.0
    return envio


def sync_upsert_records(registros: List[Dict[str, Any]]) -> None:
    """Grava (insere ou atualiza) SÓ estes registros na planilha, um por data. Levanta CloudSyncError se falhar."""
    if not registros:
        return
    _chamar_apps_script("gravar", registros=[_registro_para_envio(r) for r in registros])


def sync_delete_record(data_str: str) -> None:
    """Exclui da planilha SÓ a linha desta data. Levanta CloudSyncError se falhar."""
    _chamar_apps_script("excluir", data=data_str)


def enviar_pendentes(pendentes: Dict[str, Optional[Dict[str, Any]]]) -> Tuple[Dict[str, Optional[Dict[str, Any]]], Optional[str]]:
    """
    Envia à planilha as alterações pendentes desta sessão.
    `pendentes` mapeia data -> registro a gravar, ou None para excluir aquela data.
    Retorna (o que continua pendente, mensagem de erro ou None).
    Reenviar é seguro: gravar/excluir a mesma data duas vezes dá o mesmo resultado.
    """
    if not pendentes or not is_cloud_configured():
        return {}, None
    try:
        sync_upsert_records([r for r in pendentes.values() if r is not None])
        for data_str, r in pendentes.items():
            if r is None:
                sync_delete_record(data_str)
    except CloudSyncError as e:
        return dict(pendentes), str(e)
    return {}, None


def aplicar_pendentes(
    registros: List[Dict[str, Any]], pendentes: Dict[str, Optional[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """Reaplica sobre os registros (recém-lidos da planilha) as alterações que ainda não foram enviadas."""
    for data_str, r in (pendentes or {}).items():
        registros = delete_record_by_date(registros, data_str) if r is None else upsert_record(registros, r)
    return registros


def load_database(filepath: str = DEFAULT_DATA_PATH, avisos: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Carrega o banco de dados: registros da planilha (se configurada) e configuração de st.secrets.
    Se a planilha falhar, usa o cache local e acrescenta o motivo em `avisos`.
    """
    local_records: List[Dict[str, Any]] = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                local_records = _deduplicate_records(d.get("registros", []))
        except Exception:
            pass

    config = load_config()
    use_cloud = os.path.abspath(filepath) == os.path.abspath(DEFAULT_DATA_PATH) and is_cloud_configured()

    if use_cloud:
        try:
            cloud_records = load_records_from_cloud()
            if cloud_records or not local_records:
                result_data = {"config": config, "registros": cloud_records}
                save_database(result_data, filepath)
                return result_data
            if avisos is not None:
                avisos.append("A planilha voltou vazia; exibindo a cópia local. Confira a planilha antes de lançar pontos.")
        except CloudSyncError as e:
            if avisos is not None:
                avisos.append(f"Não foi possível ler a planilha: {e} Exibindo a cópia local, que pode estar desatualizada.")

    return {"config": config, "registros": local_records}


def save_database(data: Dict[str, Any], filepath: str = DEFAULT_DATA_PATH) -> bool:
    """
    Salva SÓ os registros no cache local (JSON). Não envia nada à planilha:
    o envio é feito por registro em sync_upsert_records / sync_delete_record.
    """
    if "registros" in data and isinstance(data["registros"], list):
        data["registros"] = _deduplicate_records(data["registros"])

    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        temp_path = filepath + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump({"registros": data.get("registros", [])}, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, filepath)
        return True
    except Exception as e:
        print(f"Erro ao salvar localmente em {filepath}: {e}")
        return False


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
