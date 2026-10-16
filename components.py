"""
Módulo de Componentes Visuais Minimalistas com Estética Metálica (Inspirado no ICMC/USP).
Contém dashboard de métricas, gráficos Plotly refinados, registro rápido e painel da chefia.
"""

from datetime import datetime, date, time
import hashlib
from typing import Dict, Any, List, Optional
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from calculations import (
    decimal_hours_to_hm_str,
    parse_time_str,
    format_time_str,
    compute_current_elapsed_time,
    get_business_days_in_month,
    detect_compliance_issues,
    generate_printable_timesheet_html,
    generate_fusp_timesheet_html,
    get_fusp_period_dates,
    now_br,
    today_br,
)
from theme import ICMC_COLORS, get_knot_svg_html, render_html


def compute_auth_token(usuario: str, senha: str) -> str:
    """Gera token de sessão verificável para manter o login ativo após atualizar a página."""
    raw = f"icmc_auth:{usuario.strip().lower()}:{senha.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def render_metric_cards(df_mes: pd.DataFrame, target_hours: float):
    """
    Exibe os indicadores resumidos com estética minimalista metálica:
    - Dias Concluídos
    - Horas Realizadas
    - Carga Prevista
    - Saldo do Banco de Horas
    """
    if df_mes.empty:
        dias_trab = 0
        horas_totais = 0.0
        saldo_total = 0.0
        meta_total = 0.0
    else:
        concluidos = df_mes[df_mes["Status"] == "Concluído"]
        dias_trab = len(concluidos)
        horas_totais = concluidos["Horas Trabalhadas"].sum()
        saldo_total = concluidos["Saldo (h)"].sum()
        meta_total = concluidos["Meta (h)"].sum()

    horas_totais_fmt = decimal_hours_to_hm_str(horas_totais)
    meta_total_fmt = decimal_hours_to_hm_str(meta_total)
    saldo_fmt = decimal_hours_to_hm_str(saldo_total, show_sign=True)

    if saldo_total > 0.001:
        saldo_accent = ICMC_COLORS["status_positive"]
        saldo_bg = "rgba(16, 185, 129, 0.08)"
        saldo_border = "rgba(16, 185, 129, 0.25)"
        saldo_label = "CRÉDITO (HORAS EXTRAS)"
    elif saldo_total < -0.001:
        saldo_accent = ICMC_COLORS["status_negative"]
        saldo_bg = "rgba(239, 68, 68, 0.08)"
        saldo_border = "rgba(239, 68, 68, 0.25)"
        saldo_label = "DÉBITO (HORAS DEVIDAS)"
    else:
        saldo_accent = ICMC_COLORS["steel_blue"]
        saldo_bg = "rgba(56, 189, 248, 0.08)"
        saldo_border = "rgba(56, 189, 248, 0.25)"
        saldo_label = "JORNADA EQUILIBRADA"

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_html(
            f"""
            <div class="metal-card" style="text-align: center;">
                <div style="font-size: 0.72rem; color: {ICMC_COLORS['text_secondary']}; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">
                    DIAS CONCLUÍDOS
                </div>
                <div style="font-size: 2rem; font-weight: 800; margin: 4px 0; font-family: 'JetBrains Mono', monospace; color: {ICMC_COLORS['text_primary']};">
                    {dias_trab}
                </div>
                <div style="font-size: 0.75rem; color: {ICMC_COLORS['text_muted']};">dias com expediente fechado</div>
            </div>
            """
        )

    with col2:
        render_html(
            f"""
            <div class="metal-card" style="text-align: center;">
                <div style="font-size: 0.72rem; color: {ICMC_COLORS['text_secondary']}; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">
                    HORAS REALIZADAS
                </div>
                <div style="font-size: 2rem; font-weight: 800; margin: 4px 0; font-family: 'JetBrains Mono', monospace; color: {ICMC_COLORS['text_primary']};">
                    {horas_totais_fmt}
                </div>
                <div style="font-size: 0.75rem; color: {ICMC_COLORS['text_muted']};">{horas_totais:.2f}h decimais</div>
            </div>
            """
        )

    with col3:
        render_html(
            f"""
            <div class="metal-card" style="text-align: center;">
                <div style="font-size: 0.72rem; color: {ICMC_COLORS['text_secondary']}; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">
                    CARGA PREVISTA
                </div>
                <div style="font-size: 2rem; font-weight: 800; margin: 4px 0; font-family: 'JetBrains Mono', monospace; color: {ICMC_COLORS['text_primary']};">
                    {meta_total_fmt}
                </div>
                <div style="font-size: 0.75rem; color: {ICMC_COLORS['text_muted']};">base: {target_hours:g}h / dia útil</div>
            </div>
            """
        )

    with col4:
        render_html(
            f"""
            <div class="metal-card" style="text-align: center; background: {saldo_bg}; border: 1px solid {saldo_border};">
                <div style="font-size: 0.72rem; color: {saldo_accent}; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">
                    BANCO DE HORAS
                </div>
                <div style="font-size: 2rem; font-weight: 800; margin: 4px 0; font-family: 'JetBrains Mono', monospace; color: {saldo_accent};">
                    {saldo_fmt}
                </div>
                <div style="font-size: 0.72rem; font-weight: 600; color: {saldo_accent};">{saldo_label}</div>
            </div>
            """
        )


def render_quick_registration_panel(
    hoje_str: str,
    registro_hoje: Optional[Dict[str, Any]],
    on_register_callback,
):
    """
    Renderiza o painel de registro rápido com botões de textura metálica e rótulos limpos.
    """
    agora = now_br()
    hora_atual_str = agora.strftime("%H:%M:%S")

    entrada = registro_hoje.get("entrada") if registro_hoje else None
    ini_pausa = registro_hoje.get("inicio_pausa") if registro_hoje else None
    fim_pausa = registro_hoje.get("fim_pausa") if registro_hoje else None
    saida = registro_hoje.get("saida") if registro_hoje else None

    if not entrada:
        estado_label = "EXPEDIENTE NÃO INICIADO"
        estado_desc = "Aguardando o primeiro registro de entrada do dia."
        estado_color = ICMC_COLORS["text_muted"]
        pode_entrada = True
        pode_pausa = False
        pode_retorno = False
        pode_saida = False
    elif entrada and not ini_pausa and not saida:
        estado_label = "EM ATIVIDADE"
        tempo_dec = compute_current_elapsed_time(entrada)
        tempo_str = decimal_hours_to_hm_str(tempo_dec)
        estado_desc = f"Atividade iniciada às {entrada} • Tempo líquido decorrido: {tempo_str}."
        estado_color = ICMC_COLORS["steel_blue"]
        pode_entrada = False
        pode_pausa = True
        pode_retorno = False
        pode_saida = True
    elif entrada and ini_pausa and not fim_pausa and not saida:
        estado_label = "INTERVALO INTRAJORNADA"
        estado_desc = f"Pausa iniciada às {ini_pausa}. Registre o retorno ao retomar as atividades."
        estado_color = ICMC_COLORS["copper_amber"]
        pode_entrada = False
        pode_pausa = False
        pode_retorno = True
        pode_saida = False
    elif entrada and fim_pausa and not saida:
        estado_label = "EM ATIVIDADE (PÓS-INTERVALO)"
        tempo_dec = compute_current_elapsed_time(entrada, ini_pausa, fim_pausa)
        tempo_str = decimal_hours_to_hm_str(tempo_dec)
        estado_desc = f"Retorno registrado às {fim_pausa} • Tempo líquido: {tempo_str}."
        estado_color = ICMC_COLORS["steel_blue"]
        pode_entrada = False
        pode_pausa = False
        pode_retorno = False
        pode_saida = True
    else:
        estado_label = "JORNADA CONCLUÍDA"
        estado_desc = f"Expediente finalizado às {saida}."
        estado_color = "#818CF8"
        pode_entrada = False
        pode_pausa = False
        pode_retorno = False
        pode_saida = False

    render_html(
        f"""
        <div class="metal-card" style="border-left: 4px solid {estado_color}; padding: 14px 20px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: {estado_color}; box-shadow: 0 0 10px {estado_color};"></span>
                        <span style="font-size: 0.85rem; font-weight: 700; letter-spacing: 0.06em; color: {estado_color}; text-transform: uppercase;">{estado_label}</span>
                    </div>
                    <p style="margin: 4px 0 0 16px; font-size: 0.85rem; color: {ICMC_COLORS['text_secondary']};">{estado_desc}</p>
                </div>
                <div style="text-align: right; margin-top: 4px;">
                    <div style="font-size: 0.68rem; color: {ICMC_COLORS['text_muted']}; letter-spacing: 0.08em; text-transform: uppercase;">HORÁRIO LOCAL • AO VIVO</div>
                    <div class="live-clock-display" style="font-size: 1.45rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; color: {ICMC_COLORS['steel_blue']}; letter-spacing: 0.04em;">{hora_atual_str}</div>
                    <div class="live-clock-date" style="font-size: 0.72rem; color: {ICMC_COLORS['text_muted']}; margin-top: 2px;"></div>
                </div>
            </div>
        </div>
        """
    )

    b_col1, b_col2, b_col3, b_col4 = st.columns(4)

    with b_col1:
        if st.button("REGISTRAR ENTRADA", use_container_width=True, disabled=not pode_entrada, type="primary" if pode_entrada else "secondary"):
            on_register_callback("entrada", now_br().strftime("%H:%M:%S"))

    with b_col2:
        if st.button("INICIAR PAUSA", use_container_width=True, disabled=not pode_pausa):
            on_register_callback("inicio_pausa", now_br().strftime("%H:%M:%S"))

    with b_col3:
        if st.button("RETORNAR PAUSA", use_container_width=True, disabled=not pode_retorno):
            on_register_callback("fim_pausa", now_br().strftime("%H:%M:%S"))

    with b_col4:
        if st.button("REGISTRAR SAÍDA", use_container_width=True, disabled=not pode_saida, type="primary" if pode_saida else "secondary"):
            on_register_callback("saida", now_br().strftime("%H:%M:%S"))

    with st.expander("Marcações registradas para hoje (" + today_br().strftime("%d/%m/%Y") + ")", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Entrada", entrada or "--:--:--")
        c2.metric("Início Pausa", ini_pausa or "--:--:--")
        c3.metric("Fim Pausa", fim_pausa or "--:--:--")
        c4.metric("Saída", saida or "--:--:--")


def render_charts(df_mes: pd.DataFrame):
    """
    Gráficos interativos com paleta metálica e alta legibilidade.
    """
    if df_mes.empty:
        st.info("Nenhum registro encontrado para este período para gerar visualizações gráficas.")
        return

    concluidos = df_mes[df_mes["Status"] == "Concluído"].copy()
    if concluidos.empty:
        st.info("Ainda não há dias concluídos com saída registrada neste mês para exibir os gráficos.")
        return

    tab_graf1, tab_graf2, tab_graf3 = st.tabs([
        "Saldo Diário",
        "Evolução Acumulada",
        "Horas Realizadas vs Meta",
    ])

    layout_defaults = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color=ICMC_COLORS["text_secondary"], size=12),
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(gridcolor="rgba(148, 163, 184, 0.08)", linecolor="rgba(148, 163, 184, 0.2)"),
        yaxis=dict(gridcolor="rgba(148, 163, 184, 0.08)", linecolor="rgba(148, 163, 184, 0.2)"),
        hovermode="closest",
        height=360,
    )

    with tab_graf1:
        colors = [ICMC_COLORS["copper_amber"] if s >= 0 else ICMC_COLORS["status_negative"] for s in concluidos["Saldo (h)"]]

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=concluidos["Data"],
            y=concluidos["Saldo (h)"],
            marker_color=colors,
            marker_line_width=1,
            marker_line_color="rgba(255,255,255,0.15)",
            text=concluidos["Saldo Formatado"],
            textposition="auto",
            hovertemplate="<b>Data:</b> %{x}<br><b>Saldo:</b> %{text}<extra></extra>",
        ))

        fig_bar.add_hline(y=0, line_dash="dash", line_color="rgba(148, 163, 184, 0.4)", line_width=1)

        fig_bar.update_layout(
            **layout_defaults,
            title=dict(text="Saldo Diário de Horas (Crédito vs Débito)", font=dict(color=ICMC_COLORS["text_primary"], size=14)),
            yaxis_title="Horas Decimais",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with tab_graf2:
        fig_line = go.Figure()

        fig_line.add_trace(go.Scatter(
            x=concluidos["Data"],
            y=concluidos["Saldo Acumulado (h)"],
            mode="lines+markers",
            name="Saldo Acumulado",
            line=dict(color=ICMC_COLORS["steel_blue"], width=3),
            marker=dict(size=7, color="#0284C7", line=dict(color="#BAE6FD", width=1.5)),
            text=concluidos["Saldo Acumulado Formatado"],
            hovertemplate="<b>Data:</b> %{x}<br><b>Saldo Acumulado:</b> %{text}<extra></extra>",
        ))

        fig_line.add_hline(y=0, line_dash="dash", line_color="rgba(148, 163, 184, 0.4)", line_width=1)

        fig_line.update_layout(
            **layout_defaults,
            title=dict(text="Evolução do Saldo Acumulado no Mês", font=dict(color=ICMC_COLORS["text_primary"], size=14)),
            yaxis_title="Saldo Acumulado (Horas)",
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with tab_graf3:
        fig_comp = go.Figure()

        fig_comp.add_trace(go.Bar(
            x=concluidos["Data"],
            y=concluidos["Horas Trabalhadas"],
            name="Horas Realizadas",
            marker_color="rgba(56, 189, 248, 0.8)",
            text=concluidos["Horas Formatadas"],
            textposition="auto",
        ))

        fig_comp.add_trace(go.Scatter(
            x=concluidos["Data"],
            y=concluidos["Meta (h)"],
            mode="lines",
            name="Meta Diária",
            line=dict(color=ICMC_COLORS["copper_amber"], dash="dash", width=2),
        ))

        fig_comp.update_layout(
            **layout_defaults,
            title=dict(text="Cumprimento Diário vs Meta Contratual", font=dict(color=ICMC_COLORS["text_primary"], size=14)),
            yaxis_title="Horas Decimais",
            barmode="group",
        )
        st.plotly_chart(fig_comp, use_container_width=True)


def render_manager_screen(
    df_mes: pd.DataFrame,
    config: Dict[str, Any],
    registros: List[Dict[str, Any]],
    ano: int,
    mes: int,
    mes_nome: str,
):
    """
    Renderiza o painel executivo consolidado da chefia com design minimalista metálico.
    """
    hoje = today_br()
    hoje_str = hoje.strftime("%Y-%m-%d")

    nome_estagiario = config.get("nome_estagiario", "Estagiário(a)")
    nome_supervisor = config.get("nome_supervisor", "Gestor(a) / Supervisor(a)")
    empresa = config.get("empresa_setor", "ICMC / USP")
    carga = float(config.get("carga_horaria_diaria", 6.0))
    dias_uteis_cfg = config.get("dias_uteis", ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira"])

    knot_svg = get_knot_svg_html(size=32)

    render_html(
        f"""
        <div class="brand-header">
            <div style="display: flex; align-items: center; gap: 14px;">
                {knot_svg}
                <div>
                    <div class="brand-title">PAINEL DE SUPERVISÃO DE ESTÁGIO</div>
                    <div class="brand-sub">Instituto de Ciências Matemáticas e de Computação • Universidade de São Paulo</div>
                </div>
            </div>
            <div>
                <span class="brand-badge">ACESSO EXECUTIVO</span>
            </div>
        </div>
        """
    )

    render_html(
        f"""
        <div class="metal-card" style="margin-bottom: 24px;">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; font-size: 0.85rem;">
                <div><span style="color: {ICMC_COLORS['text_muted']};">ESTAGIÁRIO(A)</span><br><strong style="font-size: 0.95rem;">{nome_estagiario}</strong></div>
                <div><span style="color: {ICMC_COLORS['text_muted']};">SUPERVISOR(A)</span><br><strong style="font-size: 0.95rem;">{nome_supervisor}</strong></div>
                <div><span style="color: {ICMC_COLORS['text_muted']};">DEPARTAMENTO / SETOR</span><br><strong style="font-size: 0.95rem;">{empresa}</strong></div>
                <div><span style="color: {ICMC_COLORS['text_muted']};">CARGA CONTRATUAL</span><br><strong style="font-size: 0.95rem;">{carga:g}h / dia (30h semanais)</strong></div>
                <div><span style="color: {ICMC_COLORS['text_muted']};">PERÍODO DE APURAÇÃO</span><br><strong style="font-size: 0.95rem;">{mes_nome} de {ano}</strong></div>
            </div>
        </div>
        """
    )

    registro_hoje = None
    for r in registros:
        if r.get("data") == hoje_str:
            registro_hoje = r
            break

    if registro_hoje:
        ent = registro_hoje.get("entrada")
        ini_p = registro_hoje.get("inicio_pausa")
        fim_p = registro_hoje.get("fim_pausa")
        sai = registro_hoje.get("saida")

        if sai:
            st_cor = "#818CF8"
            st_txt = f"Jornada concluída (Entrada: {ent} • Saída: {sai})"
        elif ini_p and not fim_p:
            st_cor = ICMC_COLORS["copper_amber"]
            st_txt = f"Em intervalo de descanso desde às {ini_p}"
        elif ent:
            st_cor = ICMC_COLORS["steel_blue"]
            tempo_dec = compute_current_elapsed_time(ent, ini_p, fim_p)
            tempo_str = decimal_hours_to_hm_str(tempo_dec)
            st_txt = f"Em atividade no posto desde às {ent} • {tempo_str} realizados hoje"
        else:
            st_cor = ICMC_COLORS["text_muted"]
            st_txt = "Aguardando primeiro registro de entrada do dia"
    else:
        st_cor = ICMC_COLORS["text_muted"]
        st_txt = "Nenhuma atividade registrada hoje até o momento"

    render_html(
        f"""
        <div class="metal-card" style="border-left: 4px solid {st_cor}; padding: 12px 18px; margin-bottom: 24px;">
            <div style="font-size: 0.7rem; color: {ICMC_COLORS['text_muted']}; letter-spacing: 0.08em; text-transform: uppercase;">STATUS EM TEMPO REAL HOJE</div>
            <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
                <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: {st_cor}; box-shadow: 0 0 10px {st_cor};"></span>
                <span style="font-size: 0.95rem; font-weight: 600; color: {ICMC_COLORS['text_primary']};">{st_txt}</span>
            </div>
        </div>
        """
    )

    dias_uteis_mes = get_business_days_in_month(ano, mes, dias_uteis_cfg)
    meta_horas_mes = dias_uteis_mes * carga

    if not df_mes.empty:
        concluidos = df_mes[df_mes["Status"] == "Concluído"]
        dias_trab = len(concluidos)
        horas_realizadas = concluidos["Horas Trabalhadas"].sum()
        saldo_mes = concluidos["Saldo (h)"].sum()
        media_dia = horas_realizadas / dias_trab if dias_trab > 0 else 0.0
    else:
        dias_trab = 0
        horas_realizadas = 0.0
        saldo_mes = 0.0
        media_dia = 0.0

    pct_meta = (horas_realizadas / meta_horas_mes * 100) if meta_horas_mes > 0 else 0
    pct_assiduidade = (dias_trab / dias_uteis_mes * 100) if dias_uteis_mes > 0 else 0

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        st.metric(
            label="Assiduidade / Presença",
            value=f"{dias_trab} de {dias_uteis_mes} dias",
            delta=f"{pct_assiduidade:.1f}% dos dias úteis",
            delta_color="normal",
        )

    with kpi2:
        st.metric(
            label="Horas Realizadas",
            value=decimal_hours_to_hm_str(horas_realizadas),
            delta=f"{pct_meta:.1f}% da meta ({meta_horas_mes:g}h)",
            delta_color="normal",
        )

    with kpi3:
        if saldo_mes >= 0:
            st.metric(
                label="Saldo do Banco de Horas",
                value=decimal_hours_to_hm_str(saldo_mes, show_sign=True),
                delta="Horas Extras (Crédito)",
                delta_color="normal",
            )
        else:
            st.metric(
                label="Saldo do Banco de Horas",
                value=decimal_hours_to_hm_str(saldo_mes, show_sign=True),
                delta="Horas Devidas (Débito)",
                delta_color="inverse",
            )

    with kpi4:
        st.metric(
            label="Média Diária Cumprida",
            value=decimal_hours_to_hm_str(media_dia),
            delta=f"Padrão: {carga:g}h / dia",
            delta_color="off",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    issues = detect_compliance_issues(registros, carga)
    prefixo_mes = f"{ano:04d}-{mes:02d}"
    issues_mes = [
        iss for iss in issues
        if iss.get("raw_date", "").startswith(prefixo_mes)
    ]

    st.markdown("#### AUDITORIA & CONFORMIDADE COM A LEI DO ESTÁGIO")
    if not issues_mes:
        render_html(
            f"""
            <div class="metal-card" style="border-left: 4px solid {ICMC_COLORS['status_positive']}; padding: 14px 18px;">
                <span style="color: {ICMC_COLORS['status_positive']}; font-weight: 700; font-size: 0.85rem; letter-spacing: 0.06em; text-transform: uppercase;">
                    CONFORMIDADE REGULAR
                </span>
                <p style="margin: 4px 0 0 0; font-size: 0.85rem; color: {ICMC_COLORS['text_secondary']};">
                    Não foram detectadas inconsistências técnicas nas marcações nem descumprimento dos limites da Lei 11.788/2008.
                </p>
            </div>
            """
        )
    else:
        st.warning(f"Identificado(s) {len(issues_mes)} ponto(s) de atenção para conferência da chefia:")
        for iss in issues_mes:
            if iss["tipo"] == "danger":
                st.error(f"Pendente ({iss['data']}): {iss['mensagem']}")
            else:
                st.warning(f"Atenção ({iss['data']}): {iss['mensagem']}")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("#### ESPELHO DE PONTO MENSAL (AUDITORIA)")
    if df_mes.empty:
        st.info("Nenhuma batida registrada neste período.")
    else:
        colunas_chefia = [
            "Data", "Dia da Semana", "Entrada", "Início Pausa", "Fim Pausa",
            "Saída", "Horas Formatadas", "Meta (h)", "Saldo Formatado",
            "Saldo Acumulado Formatado", "Status", "Observação"
        ]
        cols_presentes = [c for c in colunas_chefia if c in df_mes.columns]
        st.dataframe(df_mes[cols_presentes], use_container_width=True, height=300)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("#### BOLETIM DE FREQUÊNCIA OFICIAL (FUSP)")
    fusp_html = generate_fusp_timesheet_html(registros, config, ano, mes)

    st.download_button(
        label="BAIXAR BOLETIM FUSP PREENCHIDO (HTML / PDF)",
        data=fusp_html.encode("utf-8"),
        file_name=f"boletim_fusp_{nome_estagiario.replace(' ', '_')}_{ano}_{mes:02d}.html",
        mime="text/html",
        use_container_width=True,
        type="primary",
        help="Modelo oficial da Fundação de Apoio à USP (FUSP) para entrega até dia 22.",
    )

    with st.expander("Visualizar Prévia do Boletim FUSP Preenchido", expanded=True):
        import streamlit.components.v1 as st_components
        st_components.html(fusp_html, height=680, scrolling=True)


def render_welcome_screen(config: Dict[str, Any], on_save_config=None):
    """
    Exibe a tela inicial de seleção de perfil.
    - Chefia: acesso direto com um clique, sem senha (read-only).
    - Estagiário: acesso autenticado por Usuário e Senha, com opção de alterar credenciais.
    """
    knot_svg = get_knot_svg_html(size=44)
    usuario_cadastrado = str(config.get("usuario_estagiario", "")).strip() or "carlos"
    pin_cadastrado = str(config.get("pin_estagiario", "")).strip() or "1122"

    render_html(
        f"""
        <div style="text-align: center; margin: 30px auto 25px auto; max-width: 680px;">
            <div style="display: flex; justify-content: center; margin-bottom: 12px;">
                {knot_svg}
            </div>
            <div style="font-size: 1.5rem; font-weight: 800; letter-spacing: -0.02em; color: {ICMC_COLORS['text_primary']};">
                ICMC • UNIVERSIDADE DE SÃO PAULO
            </div>
            <div style="font-size: 0.85rem; color: {ICMC_COLORS['text_secondary']}; margin-top: 4px;">
                Sistema Integrado de Ponto Eletrônico & Gestão de Estágio
            </div>
            <div style="margin-top: 14px;">
                <span class="brand-badge">SELEÇÃO DE PERFIL DE ACESSO</span>
            </div>
        </div>
        """
    )

    col_gap1, col_center, col_gap2 = st.columns([1, 8, 1])

    with col_center:
        c_gestor, c_estag = st.columns(2)

        with c_gestor:
            render_html(
                f"""
                <div class="metal-card" style="margin-bottom: 16px;">
                    <div style="font-size: 0.72rem; color: {ICMC_COLORS['steel_blue']}; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">
                        ACESSO EXECUTIVO
                    </div>
                    <div style="font-size: 1.2rem; font-weight: 800; margin: 6px 0 10px 0; color: {ICMC_COLORS['text_primary']};">
                        Visão da Chefia / Supervisão
                    </div>
                    <p style="font-size: 0.85rem; color: {ICMC_COLORS['text_secondary']}; line-height: 1.5; min-height: 60px;">
                        Painel consolidado com indicadores de assiduidade, cumprimento da carga contratual, banco de horas e espelho de ponto oficial para assinatura.
                    </p>
                    <div style="margin: 10px 0; padding: 6px 10px; background: rgba(56, 189, 248, 0.08); border-radius: 6px; font-size: 0.75rem; color: {ICMC_COLORS['steel_blue']};">
                        Modo Somente Leitura (Sem risco de alterações acidentais de registros)
                    </div>
                </div>
                """
            )
            if st.button("ACESSAR COMO SUPERVISOR(A)", use_container_width=True, key="btn_login_gestor"):
                st.session_state["perfil_ativo"] = "gestao"
                st.query_params["acesso"] = "gestao"
                if "token" in st.query_params:
                    del st.query_params["token"]
                st.rerun()

        with c_estag:
            render_html(
                f"""
                <div class="metal-card" style="margin-bottom: 16px;">
                    <div style="font-size: 0.72rem; color: {ICMC_COLORS['copper_amber']}; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">
                        CONTROLE OPERACIONAL
                    </div>
                    <div style="font-size: 1.2rem; font-weight: 800; margin: 6px 0 10px 0; color: {ICMC_COLORS['text_primary']};">
                        Meu Ponto Pessoal
                    </div>
                    <p style="font-size: 0.85rem; color: {ICMC_COLORS['text_secondary']}; line-height: 1.5; min-height: 60px;">
                        Área diária do estagiário para registrar entrada, intervalos e saída com relógio em tempo real, visualização de saldos e ajustes manuais.
                    </p>
                    <div style="margin: 10px 0; padding: 6px 10px; background: rgba(245, 158, 11, 0.08); border-radius: 6px; font-size: 0.75rem; color: {ICMC_COLORS['copper_amber']};">
                        Acesso protegido com seu usuário e senha pessoais sincronizados na nuvem.
                    </div>
                </div>
                """
            )

            with st.form("form_login_estag"):
                usuario_input = st.text_input("Usuário:", placeholder="Digite seu usuário...")
                pin_input = st.text_input("Senha:", type="password", placeholder="Digite sua senha...")
                btn_estag = st.form_submit_button("ENTRAR NO MEU PONTO", use_container_width=True, type="primary")
                if btn_estag:
                    if (
                        usuario_input.strip().lower() == usuario_cadastrado.lower()
                        and pin_input.strip() == pin_cadastrado
                    ):
                        st.session_state["perfil_ativo"] = "estagiario"
                        st.session_state["autenticado_estagiario"] = True
                        st.query_params["acesso"] = "estagiario"
                        st.query_params["token"] = compute_auth_token(usuario_cadastrado, pin_cadastrado)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos. Verifique os dados e tente novamente.")

            with st.expander("Alterar Usuário ou Senha de Acesso", expanded=False):
                with st.form("form_change_credentials_welcome"):
                    st.caption("Informe a senha atual para definir um novo usuário e/ou nova senha.")
                    senha_atual_inp = st.text_input("Senha Atual:", type="password", placeholder="Digite a senha atual...")
                    novo_user_inp = st.text_input("Novo Usuário:", value=usuario_cadastrado, placeholder="Ex: carlos")
                    nova_senha_inp = st.text_input("Nova Senha:", type="password", placeholder="Digite a nova senha...")
                    confirma_senha_inp = st.text_input("Confirmar Nova Senha:", type="password", placeholder="Confirme a nova senha...")
                    btn_salvar_cred = st.form_submit_button("SALVAR NOVO USUÁRIO / SENHA", use_container_width=True)
                    if btn_salvar_cred:
                        if senha_atual_inp.strip() != pin_cadastrado:
                            st.error("A senha atual informada está incorreta.")
                        elif not novo_user_inp.strip():
                            st.error("O nome de usuário não pode ficar em branco.")
                        elif not nova_senha_inp.strip():
                            st.error("A nova senha não pode ficar em branco.")
                        elif nova_senha_inp.strip() != confirma_senha_inp.strip():
                            st.error("A nova senha e a confirmação não coincidem.")
                        else:
                            config["usuario_estagiario"] = novo_user_inp.strip()
                            config["pin_estagiario"] = nova_senha_inp.strip()
                            if on_save_config:
                                on_save_config(config)
                            st.session_state["perfil_ativo"] = "estagiario"
                            st.session_state["autenticado_estagiario"] = True
                            st.query_params["acesso"] = "estagiario"
                            st.query_params["token"] = compute_auth_token(config["usuario_estagiario"], config["pin_estagiario"])
                            st.success("Credenciais atualizadas e sincronizadas na nuvem com sucesso!")
                            st.rerun()

