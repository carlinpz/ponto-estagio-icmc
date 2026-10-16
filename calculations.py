"""
Módulo de Cálculos e Regras de Negócio para Ponto Eletrônico de Estágio.
Contém funções para processamento de horas, saldos, formatações e validações.
"""

from datetime import datetime, date, time, timedelta, timezone
from typing import Dict, Any, Tuple, Optional, List
import pandas as pd

# Fuso horário oficial de Brasília / São Paulo (UTC-3) para consistência entre localhost e nuvem
BRT_TZ = timezone(timedelta(hours=-3))


def now_br() -> datetime:
    """Retorna o datetime atual no fuso horário de Brasília (UTC-3), sem tzinfo para cálculos."""
    return datetime.now(BRT_TZ).replace(tzinfo=None)


def today_br() -> date:
    """Retorna a data de hoje no fuso horário de Brasília (UTC-3)."""
    return datetime.now(BRT_TZ).date()


def parse_time_str(time_str: Optional[str]) -> Optional[time]:
    """Converte string 'HH:MM' ou 'HH:MM:SS' para objeto datetime.time."""
    if not time_str or time_str.strip() == "" or time_str == "-":
        return None
    time_str = time_str.strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    return None


def format_time_str(t: Optional[time], include_seconds: bool = False) -> str:
    """Formata datetime.time para string HH:MM ou HH:MM:SS."""
    if not t:
        return "-"
    fmt = "%H:%M:%S" if include_seconds else "%H:%M"
    return t.strftime(fmt)


def timedelta_to_decimal_hours(td: timedelta) -> float:
    """Converte timedelta em horas decimais (ex: 1h30m -> 1.5)."""
    return td.total_seconds() / 3600.0


def decimal_hours_to_hm_str(hours: float, show_sign: bool = False) -> str:
    """
    Converte horas decimais para formato legível '[+/-]HHh MMm'.
    Exemplos:
      1.5  -> '01h 30m' (ou '+01h 30m' se show_sign=True)
     -2.25 -> '-02h 15m'
      0.0  -> '00h 00m'
    """
    sign = ""
    if hours < 0:
        sign = "-"
        hours = abs(hours)
    elif show_sign and hours > 0:
        sign = "+"

    total_minutes = int(round(hours * 60))
    h = total_minutes // 60
    m = total_minutes % 60
    return f"{sign}{h:02d}h {m:02d}m"


def calculate_day_worked_hours(
    entrada: Optional[str],
    inicio_pausa: Optional[str],
    fim_pausa: Optional[str],
    saida: Optional[str],
) -> Tuple[float, str]:
    """
    Calcula o total de horas trabalhadas no dia com base nas batidas.
    Retorna (horas_decimais, status_ou_aviso).
    """
    t_entrada = parse_time_str(entrada)
    t_saida = parse_time_str(saida)
    t_inicio_pausa = parse_time_str(inicio_pausa)
    t_fim_pausa = parse_time_str(fim_pausa)

    if not t_entrada:
        return 0.0, "Sem registro de entrada"

    ref_date = date(2026, 1, 1)
    dt_entrada = datetime.combine(ref_date, t_entrada)

    # Se ainda não saiu, o cálculo final depende de registro de saída
    if not t_saida:
        return 0.0, "Em andamento"

    dt_saida = datetime.combine(ref_date, t_saida)
    if dt_saida < dt_entrada:
        # Tratamento caso cruze a meia-noite (raro em estágio, mas robusto)
        dt_saida += timedelta(days=1)

    total_bruto = dt_saida - dt_entrada

    # Desconto do intervalo / pausa
    pausa_td = timedelta(0)
    if t_inicio_pausa and t_fim_pausa:
        dt_ini_p = datetime.combine(ref_date, t_inicio_pausa)
        dt_fim_p = datetime.combine(ref_date, t_fim_pausa)
        if dt_fim_p < dt_ini_p:
            dt_fim_p += timedelta(days=1)
        pausa_td = max(timedelta(0), dt_fim_p - dt_ini_p)

    horas_liquidas = total_bruto - pausa_td
    if horas_liquidas < timedelta(0):
        horas_liquidas = timedelta(0)

    decimal_hours = timedelta_to_decimal_hours(horas_liquidas)
    return round(decimal_hours, 2), "Concluído"


def compute_current_elapsed_time(entrada: str, inicio_pausa: Optional[str] = None, fim_pausa: Optional[str] = None) -> float:
    """
    Calcula tempo decorrido até o momento presente para um dia em andamento (fuso Brasília).
    """
    t_entrada = parse_time_str(entrada)
    if not t_entrada:
        return 0.0

    agora = now_br()
    dt_entrada = datetime.combine(agora.date(), t_entrada)

    if agora < dt_entrada:
        return 0.0

    tempo_bruto = agora - dt_entrada

    # Desconta pausa se aplicável
    t_inicio_pausa = parse_time_str(inicio_pausa)
    t_fim_pausa = parse_time_str(fim_pausa)

    if t_inicio_pausa:
        dt_ini_p = datetime.combine(agora.date(), t_inicio_pausa)
        if t_fim_pausa:
            dt_fim_p = datetime.combine(agora.date(), t_fim_pausa)
            pausa = max(timedelta(0), dt_fim_p - dt_ini_p)
            tempo_bruto -= pausa
        else:
            # Atualmente em pausa
            if agora >= dt_ini_p:
                pausa = agora - dt_ini_p
                tempo_bruto -= pausa

    return max(0.0, timedelta_to_decimal_hours(tempo_bruto))


def get_weekday_name(d: date) -> str:
    """Retorna o nome do dia da semana em português."""
    dias = [
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira",
        "Sábado",
        "Domingo",
    ]
    return dias[d.weekday()]


def process_records_dataframe(records: List[Dict[str, Any]], target_hours_per_day: float) -> pd.DataFrame:
    """
    Converte lista de registros brutos em um DataFrame enriquecido com:
    - Dia da Semana
    - Horas Trabalhadas
    - Horas Trabalhadas Formatadas
    - Meta do Dia
    - Saldo do Dia (decimal e formatado)
    - Saldo Acumulado
    """
    if not records:
        return pd.DataFrame(columns=[
            "Data", "Dia da Semana", "Entrada", "Início Pausa", "Fim Pausa",
            "Saída", "Horas Trabalhadas", "Horas Formatadas", "Meta (h)",
            "Saldo (h)", "Saldo Formatado", "Status"
        ])

    # Deduplica registros mantendo sempre o último registro válido de cada data
    dedup_map: Dict[str, Dict[str, Any]] = {}
    for r in records:
        d_s = str(r.get("data", "")).strip()
        if not d_s or d_s in ("CONFIG_JSON", "__CONFIG__"):
            continue
        dedup_map[d_s] = r

    rows = []
    for data_str, r in dedup_map.items():
        try:
            d_obj = datetime.strptime(data_str, "%Y-%m-%d").date()
            data_formatada = d_obj.strftime("%d/%m/%Y")
            dia_sem = get_weekday_name(d_obj)
        except Exception:
            data_formatada = data_str
            dia_sem = "-"
            d_obj = None

        entrada = r.get("entrada", "")
        ini_pausa = r.get("inicio_pausa", "")
        fim_pausa = r.get("fim_pausa", "")
        saida = r.get("saida", "")
        meta = float(r.get("meta_dia", target_hours_per_day) if r.get("meta_dia") is not None else target_hours_per_day)
        obs = str(r.get("observacao", "") or "")

        horas_trab, status = calculate_day_worked_hours(entrada, ini_pausa, fim_pausa, saida)

        # Se tiver saída registrada, calculamos o saldo
        if saida and parse_time_str(saida):
            saldo = round(horas_trab - meta, 2)
            saldo_fmt = decimal_hours_to_hm_str(saldo, show_sign=True)
            horas_fmt = decimal_hours_to_hm_str(horas_trab)
        elif entrada:
            # Em andamento hoje
            saldo = 0.0
            saldo_fmt = "Em andamento"
            horas_fmt = "Em andamento"
            status = "Em andamento"
        elif meta == 0.0 or any(k in obs.lower() for k in ("feriado", "recesso", "dispensa", "abono", "folga")):
            saldo = 0.0
            saldo_fmt = "00h 00m"
            horas_fmt = "00h 00m"
            status = "Feriado / Abono"
        else:
            saldo = -meta
            saldo_fmt = decimal_hours_to_hm_str(saldo, show_sign=True)
            horas_fmt = "00h 00m"
            status = "Ausente"

        rows.append({
            "raw_date": data_str,
            "date_obj": d_obj,
            "Data": data_formatada,
            "Dia da Semana": dia_sem,
            "Entrada": entrada or "-",
            "Início Pausa": ini_pausa or "-",
            "Fim Pausa": fim_pausa or "-",
            "Saída": saida or "-",
            "Horas Trabalhadas": horas_trab,
            "Horas Formatadas": horas_fmt,
            "Meta (h)": meta,
            "Saldo (h)": saldo,
            "Saldo Formatado": saldo_fmt,
            "Status": status,
            "Observação": obs
        })

    df = pd.DataFrame(rows)
    # Ordenar por data cronológica e garantir unicidade
    if not df.empty and "date_obj" in df.columns:
        df = df.drop_duplicates(subset=["raw_date"], keep="last").sort_values(by="raw_date", ascending=True).reset_index(drop=True)
        # Calcula saldo acumulado para dias concluídos
        mask_concluido = df["Status"] == "Concluído"
        df["Saldo Acumulado (h)"] = 0.0
        df.loc[mask_concluido, "Saldo Acumulado (h)"] = df.loc[mask_concluido, "Saldo (h)"].cumsum().round(2)
        df["Saldo Acumulado Formatado"] = df["Saldo Acumulado (h)"].apply(lambda s: decimal_hours_to_hm_str(s, show_sign=True))

    return df


def get_business_days_in_month(year: int, month: int, working_weekdays: List[str]) -> int:
    """Calcula a quantidade total de dias úteis esperados em determinado mês e ano."""
    import calendar
    _, total_days = calendar.monthrange(year, month)
    count = 0
    for day in range(1, total_days + 1):
        d = date(year, month, day)
        nome_dia = get_weekday_name(d)
        if nome_dia in working_weekdays:
            count += 1
    return count


def detect_compliance_issues(records: List[Dict[str, Any]], target_hours: float) -> List[Dict[str, str]]:
    """
    Analisa os registros e aponta inconsistências técnicas e alertas de conformidade
    com base nas regras da Lei do Estágio (Lei 11.788/2008).
    """
    issues = []
    hoje = today_br()

    dedup_map: Dict[str, Dict[str, Any]] = {}
    for r in records:
        d_s = str(r.get("data", "")).strip()
        if not d_s or d_s in ("CONFIG_JSON", "__CONFIG__"):
            continue
        dedup_map[d_s] = r

    for data_str, r in dedup_map.items():
        try:
            d_obj = datetime.strptime(data_str, "%Y-%m-%d").date()
            data_fmt = d_obj.strftime("%d/%m/%Y")
        except Exception:
            continue

        entrada = r.get("entrada")
        ini_pausa = r.get("inicio_pausa")
        fim_pausa = r.get("fim_pausa")
        saida = r.get("saida")

        # Batidas incompletas em dias passados
        if d_obj < hoje:
            if entrada and not saida:
                issues.append({
                    "tipo": "danger",
                    "raw_date": data_str,
                    "data": data_fmt,
                    "titulo": "Saída não registrada",
                    "mensagem": f"No dia {data_fmt}, a entrada foi registrada mas a saída não foi marcada.",
                })
            if ini_pausa and not fim_pausa:
                issues.append({
                    "tipo": "warning",
                    "raw_date": data_str,
                    "data": data_fmt,
                    "titulo": "Retorno de intervalo pendente",
                    "mensagem": f"No dia {data_fmt}, houve início de pausa sem registro de retorno.",
                })

        # Alerta de horas diárias excessivas (Lei do Estágio estabelece limite de 6h diárias)
        if entrada and saida:
            horas_trab, status = calculate_day_worked_hours(entrada, ini_pausa, fim_pausa, saida)
            if horas_trab > 6.5:
                issues.append({
                    "tipo": "warning",
                    "raw_date": data_str,
                    "data": data_fmt,
                    "titulo": "Jornada superior ao limite do estágio",
                    "mensagem": f"No dia {data_fmt}, foram realizadas {decimal_hours_to_hm_str(horas_trab)} ({horas_trab:.2f}h). A Lei 11.788/2008 veda horas extras habituais além de 6h diárias.",
                })

    return issues


def generate_printable_timesheet_html(
    df_mes: pd.DataFrame,
    config: Dict[str, Any],
    mes_nome: str,
    ano: int,
) -> str:
    """
    Gera o código HTML completo e estilizado para visualização e impressão da
    Folha de Ponto / Espelho Mensal de Estágio com campos de validação da chefia.
    """
    nome_estagiario = config.get("nome_estagiario", "Estagiário(a)")
    nome_supervisor = config.get("nome_supervisor", "Gestor(a) / Supervisor(a)")
    empresa = config.get("empresa_setor", "Empresa / Setor de Atuação")
    carga = config.get("carga_horaria_diaria", 6.0)

    # Totais
    if not df_mes.empty:
        concluidos = df_mes[df_mes["Status"] == "Concluído"]
        dias_trab = len(concluidos)
        total_horas = concluidos["Horas Trabalhadas"].sum()
        total_saldo = concluidos["Saldo (h)"].sum()
        total_horas_fmt = decimal_hours_to_hm_str(total_horas)
        total_saldo_fmt = decimal_hours_to_hm_str(total_saldo, show_sign=True)
    else:
        dias_trab = 0
        total_horas_fmt = "00h 00m"
        total_saldo_fmt = "00h 00m"

    # Montagem das linhas da tabela
    trows = ""
    if not df_mes.empty:
        for _, row in df_mes.iterrows():
            saldo_str = str(row.get("Saldo Formatado", "-"))
            color = "#10b981" if saldo_str.startswith("+") else ("#ef4444" if saldo_str.startswith("-") else "inherit")
            trows += f"""
            <tr>
                <td style="text-align: center;">{row.get('Data', '-')}</td>
                <td>{row.get('Dia da Semana', '-')}</td>
                <td style="text-align: center;">{row.get('Entrada', '-')}</td>
                <td style="text-align: center;">{row.get('Início Pausa', '-')}</td>
                <td style="text-align: center;">{row.get('Fim Pausa', '-')}</td>
                <td style="text-align: center;">{row.get('Saída', '-')}</td>
                <td style="text-align: center; font-weight: bold;">{row.get('Horas Formatadas', '-')}</td>
                <td style="text-align: center; color: {color}; font-weight: bold;">{saldo_str}</td>
                <td>{row.get('Observação', '') or '-'}</td>
            </tr>
            """
    else:
        trows = "<tr><td colspan='9' style='text-align: center; padding: 20px; color: gray;'>Nenhum registro lançado no mês selecionado.</td></tr>"

    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Espelho de Ponto - {nome_estagiario} - {mes_nome}/{ano}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                color: #222;
                background: #fff;
            }}
            .header-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
                border-bottom: 2px solid #333;
                padding-bottom: 10px;
            }}
            .header-table td {{
                padding: 4px 8px;
            }}
            .title {{
                font-size: 20px;
                font-weight: bold;
                text-align: center;
                margin-bottom: 4px;
            }}
            .subtitle {{
                font-size: 13px;
                text-align: center;
                color: #555;
                margin-bottom: 16px;
            }}
            .report-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
                font-size: 12px;
            }}
            .report-table th {{
                background-color: #f3f4f6;
                color: #111;
                font-weight: bold;
                border: 1px solid #d1d5db;
                padding: 6px;
            }}
            .report-table td {{
                border: 1px solid #e5e7eb;
                padding: 6px;
            }}
            .summary-box {{
                margin-top: 20px;
                display: flex;
                justify-content: space-between;
                background: #f9fafb;
                border: 1px solid #d1d5db;
                padding: 12px;
                border-radius: 6px;
                font-size: 13px;
            }}
            .signatures {{
                margin-top: 50px;
                width: 100%;
                display: flex;
                justify-content: space-between;
            }}
            .sig-line {{
                width: 45%;
                text-align: center;
                border-top: 1px solid #000;
                padding-top: 6px;
                font-size: 12px;
            }}
            @media print {{
                body {{ margin: 0; }}
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="no-print" style="margin-bottom: 16px; text-align: right;">
            <button onclick="window.print()" style="padding: 8px 16px; background: #2563eb; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">
                🖨️ Imprimir / Salvar em PDF
            </button>
        </div>

        <div class="title">RELATÓRIO MENSAL DE PONTO ELETRÔNICO E BANCO DE HORAS</div>
        <div class="subtitle">Controle de Jornada de Estágio — Lei Federal 11.788/2008</div>

        <table class="header-table">
            <tr>
                <td><strong>Estagiário(a):</strong> {nome_estagiario}</td>
                <td><strong>Período de Referência:</strong> {mes_nome} de {ano}</td>
            </tr>
            <tr>
                <td><strong>Supervisor(a) Responsável:</strong> {nome_supervisor}</td>
                <td><strong>Carga Horária Contratual:</strong> {carga:g} horas/dia (30h semanais)</td>
            </tr>
            <tr>
                <td colspan="2"><strong>Empresa / Setor:</strong> {empresa}</td>
            </tr>
        </table>

        <table class="report-table">
            <thead>
                <tr>
                    <th>Data</th>
                    <th>Dia da Semana</th>
                    <th>Entrada</th>
                    <th>Início Intervalo</th>
                    <th>Fim Intervalo</th>
                    <th>Saída</th>
                    <th>Total Trab.</th>
                    <th>Saldo do Dia</th>
                    <th>Observação / Ocorrência</th>
                </tr>
            </thead>
            <tbody>
                {trows}
            </tbody>
        </table>

        <div class="summary-box">
            <div><strong>Dias Trabalhados:</strong> {dias_trab}</div>
            <div><strong>Total de Horas Realizadas:</strong> {total_horas_fmt}</div>
            <div><strong>Saldo do Banco de Horas:</strong> {total_saldo_fmt}</div>
        </div>

        <div style="margin-top: 25px; font-size: 11px; color: #666; line-height: 1.4;">
            <em>Declaro que os horários de entrada, intervalos e saída acima informados correspondem à fiel execução das atividades de estágio no período estipulado, em estrita observância ao Termo de Compromisso de Estágio (TCE).</em>
        </div>

        <div class="signatures">
            <div class="sig-line">
                <strong>{nome_estagiario}</strong><br>
                Estagiário(a)
            </div>
            <div class="sig-line">
                <strong>{nome_supervisor}</strong><br>
                Supervisor(a) da Concedente
            </div>
        </div>
    </body>
    </html>
    """
    return html


def get_fusp_period_dates(ano: int, mes: int) -> Tuple[date, date, List[date]]:
    """
    Retorna o período oficial do Boletim de Frequência da FUSP.
    O ciclo mensal da FUSP compreende do dia 21 do mês anterior até o dia 20 do mês vigente.
    Exemplo para 10/2026: 21/09/2026 até 20/10/2026.
    """
    if mes == 1:
        inicio = date(ano - 1, 12, 21)
    else:
        inicio = date(ano, mes - 1, 21)
    fim = date(ano, mes, 20)

    datas = []
    curr = inicio
    while curr <= fim:
        datas.append(curr)
        curr += timedelta(days=1)
    return inicio, fim, datas


def generate_fusp_timesheet_html(
    registros: List[Dict[str, Any]],
    config: Dict[str, Any],
    ano: int,
    mes: int,
) -> str:
    """
    Gera o documento HTML idêntico ao modelo oficial do Boletim de Frequência da FUSP
    (Fundação de Apoio à Universidade de São Paulo), preenchendo automaticamente
    os horários registrados no período de 21/(mês-1) a 20/mês.
    """
    import base64
    import os

    inicio, fim, datas = get_fusp_period_dates(ano, mes)
    nome_estagiario = config.get("nome_estagiario", "Estagiário(a)")
    empresa_setor = config.get("empresa_setor", "ICMC / USP")

    # Logo oficial da FUSP (usa arquivo local se existir para funcionar 100% offline, senão fallback web)
    logo_src = "http://demonstrativo.fusp.org.br/img/fusp_topo.jpg"
    img_path = os.path.join(os.path.dirname(__file__), "fusp_topo.jpg")
    if os.path.exists(img_path):
        try:
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                logo_src = f"data:image/jpeg;base64,{b64}"
        except Exception:
            pass

    dias_semana_pt = [
        "Segunda-Feira",
        "Terça-Feira",
        "Quarta-Feira",
        "Quinta-Feira",
        "Sexta-Feira",
        "Sábado",
        "Domingo",
    ]

    mapa_registros = {r.get("data"): r for r in registros if "data" in r}

    trows = []
    for d in datas:
        d_str = d.strftime("%Y-%m-%d")
        d_m = f"{d.day}/{d.month}"
        dia_nome = dias_semana_pt[d.weekday()]
        is_fim_de_semana = d.weekday() in (5, 6)

        reg = mapa_registros.get(d_str)

        if reg:
            ent = (reg.get("entrada") or "")[:5]
            ini_p = (reg.get("inicio_pausa") or "")[:5]
            fim_p = (reg.get("fim_pausa") or "")[:5]
            sai = (reg.get("saida") or "")[:5]
            obs = reg.get("observacao") or ""
        else:
            ent = ""
            ini_p = ""
            fim_p = ""
            sai = ""
            obs = ""

        # Estilo visual de recesso para finais de semana
        if is_fim_de_semana:
            row_style = "background-color: #f8fafc; color: #64748b;"
            cell_class = 'class="recesso"'
        else:
            row_style = "background-color: #ffffff; color: #1e293b;"
            cell_class = 'class="normal"'

        trows.append(
            f"""<tr style="{row_style}">
                <td align="center" {cell_class} style="padding: 2px 4px; font-weight: 600;">{d_m}</td>
                <td {cell_class} style="padding: 2px 6px;">{dia_nome}</td>
                <td align="center" {cell_class} style="padding: 2px 4px;">{ent}</td>
                <td align="center" {cell_class} style="padding: 2px 4px;">{ini_p}</td>
                <td align="center" {cell_class} style="padding: 2px 4px;">{fim_p}</td>
                <td align="center" {cell_class} style="padding: 2px 4px;">{sai}</td>
                <td {cell_class} style="padding: 2px 6px; font-size: 9.5px;">{obs}</td>
            </tr>"""
        )

    trows_html = "\n".join(trows)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Boletim de Frequencia - FUSP - {mes:02d}/{ano} - {nome_estagiario}</title>
<style>
    @page {{
        size: A4 portrait;
        margin: 8mm 10mm;
    }}
    body {{
        font-family: Arial, Helvetica, sans-serif;
        color: #111;
        background: #fff;
        margin: 0;
        padding: 10px;
    }}
    .bordasimples {{
        border-collapse: collapse;
        border: 1px solid #333;
    }}
    .bordasimples td, .bordasimples th {{
        border: 1px solid #333;
    }}
    .no-print {{
        margin-bottom: 12px;
        text-align: right;
    }}
    .btn-print {{
        padding: 8px 16px;
        background: #0284c7;
        color: #fff;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 13px;
        font-weight: bold;
    }}
    @media print {{
        .no-print {{ display: none !important; }}
        body {{ padding: 0; }}
    }}
</style>
</head>
<body>

<div class="no-print">
    <button class="btn-print" onclick="window.print()">🖨️ Imprimir / Salvar como PDF</button>
</div>

<table width="680" border="1" class="bordasimples" style="margin: 0 auto; width: 680px; font-size: 11px;">
  <tr>
    <td colspan="2" width="22%" align="center" style="padding: 6px;">
        <img src="{logo_src}" border="0" style="max-height: 58px; max-width: 140px;" alt="FUSP">
    </td>
    <td align="center" style="padding: 6px;">
        <b style="font-size: 13.5px; letter-spacing: 0.02em;">BOLETIM DE FREQUENCIA - FUSP</b><br>
        <span style="font-size: 12px; font-weight: bold;">Período: {mes:02d}/{ano}</span>
    </td>
  </tr>
  <tr>
    <td width="12%" align="right" style="padding: 3px 6px;"><b>Nome:&nbsp;</b></td>
    <td colspan="2" style="padding: 3px 6px;"><b>{nome_estagiario}</b></td>
  </tr>
  <tr>
    <td align="right" style="padding: 3px 6px;"><b>Projeto:&nbsp;</b></td>
    <td colspan="2" style="padding: 3px 6px;">{empresa_setor}</td>
  </tr>
  <tr>
    <td align="right" style="padding: 3px 6px;"><b>Função:&nbsp;</b></td>
    <td colspan="2" style="padding: 3px 6px;">Estagiário</td>
  </tr>
</table>

<table width="680" border="1" class="bordasimples" style="margin: 6px auto 0 auto; width: 680px; font-size: 10px; line-height: 1.2;">
  <tr style="background: #f1f5f9; font-weight: bold; text-align: center;">
    <td colspan="2" rowspan="2" style="padding: 3px 4px; width: 140px;">Dia da Semana</td>
    <td colspan="4" style="padding: 3px 4px;">Horário de</td>
    <td width="160" rowspan="2" style="padding: 3px 4px;">Observação</td>
  </tr>
  <tr style="background: #f1f5f9; font-weight: bold; text-align: center;">
    <td width="72" style="padding: 3px 4px;">Entrada</td>
    <td colspan="2" style="padding: 3px 4px; width: 144px;">Repouso</td>
    <td width="72" style="padding: 3px 4px;">Saída</td>
  </tr>
  {trows_html}
</table>

<table width="680" style="margin: 28px auto 0 auto; width: 680px; font-size: 10.5px;">
  <tr>
    <td width="46%" align="center" style="vertical-align: top;">
      <div style="border-top: 1px solid #000; width: 85%; margin: 0 auto 4px auto;"></div>
      Local e Data
    </td>
    <td width="8%"></td>
    <td width="46%" align="center" style="vertical-align: top;">
      <div style="border-top: 1px solid #000; width: 85%; margin: 0 auto 4px auto;"></div>
      Assinatura do Funcionário
    </td>
  </tr>
  <tr><td colspan="3" style="height: 28px;"></td></tr>
  <tr>
    <td></td>
    <td></td>
    <td width="46%" align="center" style="vertical-align: top;">
      <div style="border-top: 1px solid #000; width: 85%; margin: 0 auto 4px auto;"></div>
      Assinatura da Coordenação
    </td>
  </tr>
</table>

</body>
</html>
"""
    return html

