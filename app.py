"""
Aplicação Web Streamlit: Sistema de Ponto Eletrônico e Banco de Horas de Estágio.
Identidade visual minimalista e moderna inspirada no ICMC/USP com acabamento metálico.
"""

import os
import json
from datetime import datetime, date, time
import streamlit as st
import pandas as pd

# Módulos internos
from storage import (
    load_database,
    save_database,
    get_record_by_date,
    upsert_record,
    delete_record_by_date,
    export_df_to_csv_bytes,
    DEFAULT_DATA_PATH,
)
from calculations import (
    process_records_dataframe,
    decimal_hours_to_hm_str,
    parse_time_str,
    format_time_str,
    get_weekday_name,
    generate_fusp_timesheet_html,
    get_fusp_period_dates,
    now_br,
    today_br,
)
from theme import (
    inject_custom_theme,
    get_knot_svg_html,
    ICMC_COLORS,
    render_html,
)
from components import (
    render_metric_cards,
    render_quick_registration_panel,
    render_charts,
    render_manager_screen,
    render_welcome_screen,
    compute_auth_token,
)

# Configuração da página Streamlit
st.set_page_config(
    page_title="Ponto ICMC • USP",
    page_icon="⏱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Injeção da Identidade Visual Metálica e Animação de Rede no Background
inject_custom_theme()


def init_session_state(force_reload: bool = False):
    """Inicializa e carrega os dados mais recentes do banco de dados."""
    if force_reload or "db" not in st.session_state:
        st.session_state.db = load_database()


init_session_state()
db = st.session_state.db
config = db.setdefault("config", {})
registros = db.setdefault("registros", [])

carga_padrao = float(config.get("carga_horaria_diaria", 6.0))
dias_uteis_padrao = config.get(
    "dias_uteis",
    ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira"],
)

hoje = today_br()
hoje_str = hoje.strftime("%Y-%m-%d")
registro_hoje = get_record_by_date(registros, hoje_str)

# -------------------------------------------------------------
# GERENCIAMENTO DE PERFIL E AUTENTICAÇÃO (USUÁRIO E SENHA)
# -------------------------------------------------------------
usuario_cadastrado = str(config.get("usuario_estagiario", "")).strip() or "carlos"
pin_cadastrado = str(config.get("pin_estagiario", "")).strip() or "1122"
expected_token = compute_auth_token(usuario_cadastrado, pin_cadastrado)

acesso_param = st.query_params.get("acesso")
token_param = st.query_params.get("token")

if "perfil_ativo" not in st.session_state:
    if acesso_param in ("gestao", "chefia", "supervisor"):
        st.session_state["perfil_ativo"] = "gestao"
    elif acesso_param in ("estagiario", "estagio") and token_param == expected_token:
        st.session_state["perfil_ativo"] = "estagiario"
        st.session_state["autenticado_estagiario"] = True
    else:
        st.session_state["perfil_ativo"] = None

# Se o perfil for estagiário mas não estiver autenticado na sessão nem com token válido, exige login
if st.session_state.get("perfil_ativo") == "estagiario" and not st.session_state.get("autenticado_estagiario"):
    if token_param == expected_token:
        st.session_state["autenticado_estagiario"] = True
    else:
        st.session_state["perfil_ativo"] = None

# Se nenhum perfil estiver ativo, exibe a tela inicial de seleção e login:
if st.session_state["perfil_ativo"] is None:
    def salvar_config_callback(nova_config):
        st.session_state.db["config"] = nova_config
        save_database(st.session_state.db)

    render_welcome_screen(config, on_save_config=salvar_config_callback)
    st.stop()

# -------------------------------------------------------------
# BARRA LATERAL (SIDEBAR): Configurações, Filtro e Ações
# -------------------------------------------------------------
with st.sidebar:
    knot_sidebar = get_knot_svg_html(size=26)
    render_html(
        f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            {knot_sidebar}
            <div>
                <div style="font-size: 0.95rem; font-weight: 800; letter-spacing: -0.02em; color: {ICMC_COLORS['text_primary']};">
                    ICMC • USP
                </div>
                <div style="font-size: 0.72rem; color: {ICMC_COLORS['text_secondary']}; letter-spacing: 0.05em; text-transform: uppercase;">
                    Ponto Eletrônico
                </div>
            </div>
        </div>
        """
    )

    # Indicador de Perfil Ativo e Botão para Alternar
    if st.session_state["perfil_ativo"] == "gestao":
        st.caption("Perfil Ativo: **Supervisão / Chefia** (Read-Only)")
        if st.button("Acesso Estagiário (Login)", use_container_width=True, key="btn_switch_to_estag"):
            if st.session_state.get("autenticado_estagiario"):
                st.session_state["perfil_ativo"] = "estagiario"
                st.query_params["acesso"] = "estagiario"
                st.query_params["token"] = expected_token
            else:
                st.session_state["perfil_ativo"] = None
                if "acesso" in st.query_params:
                    del st.query_params["acesso"]
            st.rerun()
    else:
        st.caption(f"Perfil Ativo: **Estagiário(a)** (`{usuario_cadastrado}`)")
        col_sw1, col_sw2 = st.columns(2)
        with col_sw1:
            if st.button("Ver Chefia", use_container_width=True, key="btn_switch_to_gestao", help="Visualizar como a chefia visualiza o painel"):
                st.session_state["perfil_ativo"] = "gestao"
                st.query_params["acesso"] = "gestao"
                st.rerun()
        with col_sw2:
            if st.button("Sair", use_container_width=True, key="btn_logout", help="Encerrar sessão e voltar para a tela de login"):
                st.session_state["perfil_ativo"] = None
                st.session_state["autenticado_estagiario"] = False
                st.query_params.clear()
                st.rerun()

    if st.button("🔄 Sincronizar Nuvem", use_container_width=True, key="btn_sync_cloud", help="Recarregar dados mais recentes da planilha Google Sheets"):
        init_session_state(force_reload=True)
        st.toast("Dados sincronizados com a nuvem!")
        st.rerun()

    st.divider()

    st.markdown("##### Período de Análise")
    meses_pt = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    ano_atual = hoje.year
    mes_atual = hoje.month

    anos_disp = sorted(
        list(
            {
                int(r["data"][:4])
                for r in registros
                if "data" in r and len(str(r["data"])) >= 4 and str(r["data"])[:4].isdigit()
            }
            | {ano_atual}
        ),
        reverse=True,
    )

    col_mes, col_ano = st.columns(2)
    with col_mes:
        mes_selecionado = st.selectbox(
            "Mês",
            options=list(range(1, 13)),
            format_func=lambda m: meses_pt[m - 1],
            index=mes_atual - 1,
            key="filtro_mes",
        )
    with col_ano:
        ano_selecionado = st.selectbox(
            "Ano",
            options=anos_disp,
            index=anos_disp.index(ano_atual) if ano_atual in anos_disp else 0,
            key="filtro_ano",
        )

    st.divider()

    if st.session_state["perfil_ativo"] == "gestao":
        st.info("Visão Executiva: Modo de consulta e emissão de relatórios. Ações de bater ponto e configurações cadastrais estão desabilitadas para supervisão.")
    else:
        with st.expander("Configurações & Contrato", expanded=False):
            nova_carga = st.number_input(
                "Carga Horária Diária (horas):",
                min_value=1.0,
                max_value=12.0,
                value=carga_padrao,
                step=0.5,
                help="6 horas por dia para jornadas de 30h semanais (Lei 11.788/2008).",
            )

            opcoes_dias = [
                "Segunda-feira",
                "Terça-feira",
                "Quarta-feira",
                "Quinta-feira",
                "Sexta-feira",
                "Sábado",
                "Domingo",
            ]
            novos_dias = st.multiselect(
                "Dias Úteis Esperados:",
                options=opcoes_dias,
                default=[d for d in dias_uteis_padrao if d in opcoes_dias],
            )

            nome_estag = st.text_input(
                "Nome do Estagiário(a):",
                value=config.get("nome_estagiario", "Carlos Henrique da Luz Pizzi"),
            )

            nome_superv = st.text_input(
                "Nome do(a) Supervisor(a):",
                value=config.get("nome_supervisor", "Gestor(a) / Supervisor(a)"),
            )

            empresa_setor = st.text_input(
                "Departamento / Projeto:",
                value=config.get("empresa_setor", "605001"),
            )

            novo_usuario = st.text_input(
                "Usuário de Login (Estagiário):",
                value=usuario_cadastrado,
                help="Nome de usuário utilizado para entrar no sistema.",
            )

            novo_pin = st.text_input(
                "Senha de Acesso (Estagiário):",
                value=pin_cadastrado,
                type="password",
                help="Senha pessoal sincronizada na nuvem para acesso ao ponto.",
            )

            if st.button("Salvar Parâmetros", use_container_width=True):
                config["carga_horaria_diaria"] = float(nova_carga)
                config["dias_uteis"] = novos_dias
                config["nome_estagiario"] = nome_estag
                config["nome_supervisor"] = nome_superv
                config["empresa_setor"] = empresa_setor
                config["usuario_estagiario"] = novo_usuario.strip() if novo_usuario.strip() else usuario_cadastrado
                config["pin_estagiario"] = novo_pin.strip() if novo_pin.strip() else pin_cadastrado
                save_database(db)
                st.query_params["token"] = compute_auth_token(config["usuario_estagiario"], config["pin_estagiario"])
                st.toast("Configurações e credenciais salvas na nuvem com sucesso.")
                st.rerun()

        st.divider()

        st.markdown("##### Registro Rápido")
        hora_preview = now_br().strftime("%H:%M:%S")
        render_html(
            f"""
            <div style="display: flex; align-items: center; justify-content: space-between; margin: 4px 0 10px 0; padding: 6px 10px; background: rgba(56, 189, 248, 0.06); border: 1px solid rgba(56, 189, 248, 0.18); border-radius: 6px;">
                <span style="font-size: 0.72rem; color: {ICMC_COLORS['text_muted']};">Horário ao vivo:</span>
                <span class="live-clock-display" style="font-family: 'JetBrains Mono', monospace; font-size: 0.88rem; font-weight: 700; color: {ICMC_COLORS['steel_blue']};">{hora_preview}</span>
            </div>
            """
        )


        def handle_ponto_action(acao: str, timestamp_str: str):
            reg = get_record_by_date(st.session_state.db["registros"], hoje_str)
            if not reg:
                reg = {
                    "data": hoje_str,
                    "entrada": None,
                    "inicio_pausa": None,
                    "fim_pausa": None,
                    "saida": None,
                    "meta_dia": config.get("carga_horaria_diaria", 6.0),
                    "observacao": "Registro via Ponto Rápido",
                }

            if acao == "entrada":
                if reg.get("entrada"):
                    st.error("Entrada já registrada para o dia de hoje.")
                    return
                reg["entrada"] = timestamp_str
                st.toast(f"Entrada registrada às {timestamp_str}.")

            elif acao == "inicio_pausa":
                if not reg.get("entrada"):
                    st.error("Não é possível iniciar pausa sem ter registrado a entrada.")
                    return
                if reg.get("inicio_pausa"):
                    st.error("Pausa já foi iniciada anteriormente hoje.")
                    return
                reg["inicio_pausa"] = timestamp_str
                st.toast(f"Pausa iniciada às {timestamp_str}.")

            elif acao == "fim_pausa":
                if not reg.get("inicio_pausa"):
                    st.error("Não há início de pausa registrado para retornar.")
                    return
                if reg.get("fim_pausa"):
                    st.error("Retorno de pausa já registrado hoje.")
                    return
                reg["fim_pausa"] = timestamp_str
                st.toast(f"Retorno registrado às {timestamp_str}.")

            elif acao == "saida":
                if not reg.get("entrada"):
                    st.error("Não é possível registrar saída sem ter registrado a entrada.")
                    return
                if reg.get("inicio_pausa") and not reg.get("fim_pausa"):
                    st.error("Finalize o intervalo antes de registrar a saída.")
                    return
                if reg.get("saida"):
                    st.error("Saída já registrada hoje.")
                    return
                reg["saida"] = timestamp_str
                st.toast(f"Saída registrada às {timestamp_str}.")

            st.session_state.db["registros"] = upsert_record(st.session_state.db["registros"], reg)
            save_database(st.session_state.db)
            st.rerun()


        sb_ent = registro_hoje.get("entrada") if registro_hoje else None
        sb_ini_p = registro_hoje.get("inicio_pausa") if registro_hoje else None
        sb_fim_p = registro_hoje.get("fim_pausa") if registro_hoje else None
        sb_sai = registro_hoje.get("saida") if registro_hoje else None

        pode_ent = not sb_ent
        pode_pau = bool(sb_ent and not sb_ini_p and not sb_sai)
        pode_ret = bool(sb_ent and sb_ini_p and not sb_fim_p and not sb_sai)
        pode_sai = bool(sb_ent and (not sb_ini_p or sb_fim_p) and not sb_sai)

        if st.button("BATER ENTRADA", disabled=not pode_ent, use_container_width=True, key="sb_btn_ent", type="primary" if pode_ent else "secondary"):
            handle_ponto_action("entrada", now_br().strftime("%H:%M:%S"))

        if st.button("INICIAR PAUSA", disabled=not pode_pau, use_container_width=True, key="sb_btn_pau"):
            handle_ponto_action("inicio_pausa", now_br().strftime("%H:%M:%S"))

        if st.button("RETORNAR PAUSA", disabled=not pode_ret, use_container_width=True, key="sb_btn_ret"):
            handle_ponto_action("fim_pausa", now_br().strftime("%H:%M:%S"))

        if st.button("BATER SAÍDA", disabled=not pode_sai, use_container_width=True, key="sb_btn_sai", type="primary" if pode_sai else "secondary"):
            handle_ponto_action("saida", now_br().strftime("%H:%M:%S"))

    st.divider()
    st.caption(f"Base de dados: `{os.path.basename(DEFAULT_DATA_PATH)}` • Sincronizado Google Sheets")

# -------------------------------------------------------------
# PROCESSAMENTO DOS DADOS PARA O PERÍODO SELECIONADO
# -------------------------------------------------------------
df_todos = process_records_dataframe(registros, config.get("carga_horaria_diaria", 6.0))

if not df_todos.empty and "raw_date" in df_todos.columns:
    prefixo_mes = f"{ano_selecionado:04d}-{mes_selecionado:02d}"
    df_mes = df_todos[df_todos["raw_date"].str.startswith(prefixo_mes)].copy()
else:
    df_mes = pd.DataFrame()

# -------------------------------------------------------------
# RENDERIZAÇÃO CONFORME PERFIL SELECIONADO
# -------------------------------------------------------------
if st.session_state["perfil_ativo"] == "gestao":
    render_manager_screen(
        df_mes=df_mes,
        config=config,
        registros=registros,
        ano=ano_selecionado,
        mes=mes_selecionado,
        mes_nome=meses_pt[mes_selecionado - 1],
    )
    st.stop()

# -------------------------------------------------------------
# VISÃO DO ESTAGIÁRIO (MEU PONTO PESSOAL)
# -------------------------------------------------------------
nome_usuario = config.get("nome_estagiario", "Estagiário(a)")
empresa_usuario = config.get("empresa_setor", "ICMC / USP")

knot_header = get_knot_svg_html(size=30)
render_html(
    f"""
    <div class="brand-header">
        <div style="display: flex; align-items: center; gap: 12px;">
            {knot_header}
            <div>
                <div class="brand-title">CONTROLE DE PONTO • {nome_usuario.upper()}</div>
                <div class="brand-sub">{empresa_usuario} • Período de {meses_pt[mes_selecionado-1]} de {ano_selecionado}</div>
            </div>
        </div>
        <div>
            <span class="brand-badge">JORNADA ATIVA</span>
        </div>
    </div>
    """
)

# Painel de Métricas (Dashboard no Topo)
render_metric_cards(df_mes, config.get("carga_horaria_diaria", 6.0))

st.markdown("<br>", unsafe_allow_html=True)

# Abas Principais Minimalistas
tab_registro, tab_graficos, tab_historico, tab_manual, tab_fusp, tab_exportar = st.tabs([
    "Registro Rápido",
    "Gráficos & Análise",
    "Histórico Mensal",
    "Ajuste Manual",
    "Boletim FUSP",
    "Exportação & Backup",
])

# TAB 1: REGISTRO RÁPIDO DO PONTO
with tab_registro:
    render_quick_registration_panel(
        hoje_str=hoje_str,
        registro_hoje=registro_hoje,
        on_register_callback=handle_ponto_action,
    )

    st.markdown(
        f"""
        <div style="margin-top: 15px; font-size: 0.8rem; color: {ICMC_COLORS['text_muted']}; line-height: 1.5;">
            <strong>Diretrizes:</strong> Carga contratual padrão de {config.get('carga_horaria_diaria', 6.0):g} horas diárias. 
            Intervalo intrajornada recomendado para descanso conforme acordo de estágio (Lei 11.788/2008).
        </div>
        """,
        unsafe_allow_html=True,
    )

# TAB 2: VISUALIZAÇÃO GRÁFICA
with tab_graficos:
    render_charts(df_mes)

# TAB 3: TABELA DE HISTÓRICO
with tab_historico:
    st.markdown(f"##### Registros de {meses_pt[mes_selecionado-1]} de {ano_selecionado}")

    if df_mes.empty:
        st.info("Nenhum registro encontrado para o período selecionado.")
    else:
        colunas_exibicao = [
            "Data",
            "Dia da Semana",
            "Entrada",
            "Início Pausa",
            "Fim Pausa",
            "Saída",
            "Horas Formatadas",
            "Meta (h)",
            "Saldo Formatado",
            "Saldo Acumulado Formatado",
            "Status",
            "Observação",
        ]
        cols_presentes = [c for c in colunas_exibicao if c in df_mes.columns]
        st.dataframe(df_mes[cols_presentes], use_container_width=True, height=360)

# TAB 4: LANÇAMENTO / AJUSTE MANUAL
with tab_manual:
    st.markdown("##### Retificação ou Inclusão Manual")
    st.caption("Utilize para ajustar marcações esquecidas ou retificar horários com justificativa.")

    col_data_sel, col_info_ajuste = st.columns([1, 2])

    with col_data_sel:
        data_ajuste = st.date_input(
            "Data do Registro:",
            value=hoje,
            max_value=hoje,
            key="data_ajuste_picker",
        )
        data_ajuste_str = data_ajuste.strftime("%Y-%m-%d")
        reg_existente = get_record_by_date(registros, data_ajuste_str)

        if reg_existente:
            st.info(f"Registro existente em {data_ajuste.strftime('%d/%m/%Y')}. Campos pré-preenchidos.")
        else:
            st.caption(f"Novo lançamento para {data_ajuste.strftime('%d/%m/%Y')}.")

    ent_default = (parse_time_str(reg_existente.get("entrada")) if reg_existente and reg_existente.get("entrada") else None) or time(8, 0)
    ini_p_default = (parse_time_str(reg_existente.get("inicio_pausa")) if reg_existente and reg_existente.get("inicio_pausa") else None) or time(12, 0)
    fim_p_default = (parse_time_str(reg_existente.get("fim_pausa")) if reg_existente and reg_existente.get("fim_pausa") else None) or time(13, 0)
    sai_default = (parse_time_str(reg_existente.get("saida")) if reg_existente and reg_existente.get("saida") else None) or time(14, 0)
    obs_default = reg_existente.get("observacao", "") if reg_existente else ""
    meta_default = float(reg_existente["meta_dia"]) if (reg_existente and reg_existente.get("meta_dia") is not None) else float(config.get("carga_horaria_diaria", 6.0))
    teve_pausa_default = bool(reg_existente and reg_existente.get("inicio_pausa"))
    teve_saida_default = bool(reg_existente.get("saida")) if reg_existente else (data_ajuste < hoje)

    with col_info_ajuste:
        with st.form("form_ajuste_manual"):
            st.markdown(f"**Data selecionada:** {data_ajuste.strftime('%d/%m/%Y')} ({get_weekday_name(data_ajuste)})")

            c_f1, c_f2 = st.columns(2)
            with c_f1:
                input_entrada = st.time_input("Horário de Entrada:", value=ent_default, step=60)
                input_ini_pausa = st.time_input("Início do Intervalo:", value=ini_p_default, step=60)
                teve_pausa = st.checkbox("Houve intervalo de descanso?", value=teve_pausa_default)

            with c_f2:
                input_fim_pausa = st.time_input("Fim do Intervalo:", value=fim_p_default, step=60)
                input_saida = st.time_input("Horário de Saída:", value=sai_default, step=60)
                teve_saida = st.checkbox("Expediente concluído (registrar saída)?", value=teve_saida_default)

            input_meta = st.number_input("Carga do Dia (horas) — use 0 para Feriado/Abono:", min_value=0.0, max_value=12.0, value=meta_default, step=0.5)
            input_obs = st.text_input("Justificativa / Observação:", value=obs_default, placeholder="Ex: Ajuste por esquecimento, feriado nacional...")

            submitted = st.form_submit_button("SALVAR REGISTRO MANUAL", use_container_width=True, type="primary")

            if submitted:
                if float(input_meta) == 0.0 and not teve_saida and "feriado" in (input_obs or "").lower():
                    novo_reg = {
                        "data": data_ajuste_str,
                        "entrada": None,
                        "inicio_pausa": None,
                        "fim_pausa": None,
                        "saida": None,
                        "meta_dia": 0.0,
                        "observacao": input_obs or "Feriado / Abono",
                    }
                else:
                    if teve_pausa:
                        if input_ini_pausa <= input_entrada:
                            st.error("O início do intervalo deve ser posterior à entrada.")
                            st.stop()
                        if input_fim_pausa <= input_ini_pausa:
                            st.error("O término do intervalo deve ser posterior ao início.")
                            st.stop()
                        if teve_saida and input_saida <= input_fim_pausa:
                            st.error("A saída deve ser posterior ao término do intervalo.")
                            st.stop()
                    else:
                        if teve_saida and input_saida <= input_entrada:
                            st.error("A saída deve ser posterior ao horário de entrada.")
                            st.stop()

                    novo_reg = {
                        "data": data_ajuste_str,
                        "entrada": format_time_str(input_entrada, include_seconds=True),
                        "inicio_pausa": format_time_str(input_ini_pausa, include_seconds=True) if teve_pausa else None,
                        "fim_pausa": format_time_str(input_fim_pausa, include_seconds=True) if teve_pausa else None,
                        "saida": format_time_str(input_saida, include_seconds=True) if teve_saida else None,
                        "meta_dia": float(input_meta),
                        "observacao": input_obs or "Ajuste manual",
                    }

                st.session_state.db["registros"] = upsert_record(st.session_state.db["registros"], novo_reg)
                save_database(st.session_state.db)
                st.toast(f"Registro de {data_ajuste.strftime('%d/%m/%Y')} gravado com sucesso.")
                st.rerun()

    if reg_existente:
        st.markdown("---")
        with st.expander("Excluir este registro", expanded=False):
            st.caption(f"Confirma a exclusão definitiva do registro de {data_ajuste.strftime('%d/%m/%Y')}?")
            if st.button("EXCLUIR REGISTRO", type="secondary", key="btn_del_reg"):
                st.session_state.db["registros"] = delete_record_by_date(st.session_state.db["registros"], data_ajuste_str)
                save_database(st.session_state.db)
                st.toast(f"Registro de {data_ajuste.strftime('%d/%m/%Y')} removido.")
                st.rerun()

# TAB 5: BOLETIM DE FREQUÊNCIA FUSP (MODELO OFICIAL)
with tab_fusp:
    inicio_fusp, fim_fusp, _ = get_fusp_period_dates(ano_selecionado, mes_selecionado)
    periodo_fusp_str = f"{inicio_fusp.strftime('%d/%m/%Y')} a {fim_fusp.strftime('%d/%m/%Y')}"

    render_html(
        f"""
        <div class="metal-card" style="margin-bottom: 16px;">
            <div style="font-size: 0.72rem; color: {ICMC_COLORS['copper_amber']}; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;">
                DOCUMENTO OFICIAL DA FUNDAÇÃO
            </div>
            <div style="font-size: 1.25rem; font-weight: 800; margin: 4px 0 6px 0; color: {ICMC_COLORS['text_primary']};">
                Boletim de Frequência FUSP
            </div>
            <p style="font-size: 0.85rem; color: {ICMC_COLORS['text_secondary']}; margin-bottom: 8px;">
                Modelo oficial da <strong>FUSP (Fundação de Apoio à Universidade de São Paulo)</strong> para envio até o dia 22 de cada mês.
                Preenchido e atualizado automaticamente com as marcações de ponto do ciclo mensal.
            </p>
            <div style="font-size: 0.8rem; color: {ICMC_COLORS['steel_blue']};">
                <strong>Ciclo FUSP:</strong> {periodo_fusp_str} (Referência: {meses_pt[mes_selecionado-1]} de {ano_selecionado})
            </div>
        </div>
        """
    )

    fusp_html = generate_fusp_timesheet_html(registros, config, ano_selecionado, mes_selecionado)

    col_fusp1, col_fusp2 = st.columns([1, 1])
    with col_fusp1:
        st.download_button(
            label="BAIXAR BOLETIM FUSP PREENCHIDO (HTML / PDF)",
            data=fusp_html.encode("utf-8"),
            file_name=f"boletim_fusp_{nome_usuario.replace(' ', '_')}_{ano_selecionado}_{mes_selecionado:02d}.html",
            mime="text/html",
            use_container_width=True,
            type="primary",
            help="Arquivo pronto para imprimir diretamente no navegador (Ctrl+P) ou salvar como PDF.",
        )
    with col_fusp2:
        url_original_fusp = f"http://demonstrativo.fusp.org.br/imprimirbf.php?mes={mes_selecionado}&ano={ano_selecionado}"
        st.link_button(
            label="ABRIR MODELO EM BRANCO NO PORTAL FUSP",
            url=url_original_fusp,
            use_container_width=True,
            help="Acessa a página oficial geradora de formulários em branco no site da FUSP.",
        )

    st.markdown("##### Prévia do Documento Oficial Preenchido")
    import streamlit.components.v1 as st_components
    st_components.html(fusp_html, height=750, scrolling=True)

# TAB 6: EXPORTAÇÃO & BACKUP
with tab_exportar:
    st.markdown("##### Exportação de Dados e Cópias de Segurança")

    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        st.markdown("**Relatório em Planilha (CSV / Excel)**")
        st.caption("Arquivo tabular em UTF-8 com codificação compatível com Microsoft Excel.")
        if not df_mes.empty:
            csv_bytes = export_df_to_csv_bytes(df_mes)
            nome_arquivo_csv = f"relatorio_ponto_{ano_selecionado}_{mes_selecionado:02d}.csv"
            st.download_button(
                label=f"BAIXAR RELATÓRIO DO MÊS ({meses_pt[mes_selecionado-1]}/{ano_selecionado})",
                data=csv_bytes,
                file_name=nome_arquivo_csv,
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("Sem dados para exportação no período.")

        if not df_todos.empty:
            csv_todos_bytes = export_df_to_csv_bytes(df_todos)
            st.download_button(
                label="BAIXAR HISTÓRICO COMPLETO (TODOS OS PERÍODOS)",
                data=csv_todos_bytes,
                file_name="relatorio_ponto_completo.csv",
                mime="text/csv",
                use_container_width=True,
            )

    with col_exp2:
        st.markdown("**Backup e Restauração (JSON)**")
        st.caption("Cópia de segurança integral dos parâmetros e histórico.")

        json_str = json.dumps(st.session_state.db, ensure_ascii=False, indent=2)
        st.download_button(
            label="BAIXAR BACKUP LOCAL (JSON)",
            data=json_str.encode("utf-8"),
            file_name="ponto_eletronico.json",
            mime="application/json",
            use_container_width=True,
        )

        upload_backup = st.file_uploader("Restaurar dados de arquivo JSON:", type=["json"])
        if upload_backup is not None:
            try:
                uploaded_data = json.load(upload_backup)
                if "registros" in uploaded_data and isinstance(uploaded_data["registros"], list):
                    if st.button("RESTAURAR ARQUIVO ENVIADO", type="primary"):
                        st.session_state.db = uploaded_data
                        save_database(uploaded_data)
                        st.toast("Dados restaurados com sucesso.")
                        st.rerun()
                else:
                    st.error("Formato inválido. O arquivo deve conter o campo 'registros'.")
            except Exception as e:
                st.error(f"Falha na leitura do arquivo: {e}")
