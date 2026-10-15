"""
Script de testes para verificar cálculos, regras de validação e persistência.
"""

from datetime import datetime, date, time
from calculations import (
    calculate_day_worked_hours,
    decimal_hours_to_hm_str,
    parse_time_str,
    format_time_str,
    process_records_dataframe,
    compute_current_elapsed_time,
    get_business_days_in_month,
    detect_compliance_issues,
    generate_printable_timesheet_html,
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

    # Teste 7: Dias úteis no mês
    from calculations import get_business_days_in_month, detect_compliance_issues, generate_printable_timesheet_html
    dias_uteis = get_business_days_in_month(2026, 10, ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira"])
    assert dias_uteis == 22, f"Esperado 22 dias úteis em 10/2026, obtido {dias_uteis}"
    print(f"✓ Teste 7 passou: Cálculo de dias úteis ({dias_uteis} dias)")

    # Teste 8: Detecção de inconsistências (excesso de horas ou batida pendente)
    inconsistencias = detect_compliance_issues([
        {"data": "2026-10-01", "entrada": "09:00:00", "inicio_pausa": None, "fim_pausa": None, "saida": "17:00:00"}
    ], 6.0)
    assert len(inconsistencias) > 0
    print("✓ Teste 8 passou: Detecção de inconformidade legal de estágio")

    # Teste 9: Geração de Folha de Ponto HTML
    cfg_test = {"nome_estagiario": "João", "nome_supervisor": "Maria", "empresa_setor": "TI", "carga_horaria_diaria": 6.0}
    html_rep = generate_printable_timesheet_html(df, cfg_test, "Outubro", 2026)
    assert "RELATÓRIO MENSAL DE PONTO ELETRÔNICO" in html_rep
    assert "Maria" in html_rep
    print("✓ Teste 9 passou: Geração de Folha de Ponto HTML para impressão")

    # Teste 10: Geração do Boletim de Frequência FUSP
    ini_fusp, fim_fusp, datas_fusp = get_fusp_period_dates(2026, 10)
    assert ini_fusp == date(2026, 9, 21)
    assert fim_fusp == date(2026, 10, 20)
    assert len(datas_fusp) == 30
    html_fusp = generate_fusp_timesheet_html(sample_records, cfg_test, 2026, 10)
    assert "BOLETIM DE FREQUENCIA - FUSP" in html_fusp
    assert "Período: 10/2026" in html_fusp
    assert "João" in html_fusp
    print("✓ Teste 10 passou: Geração do Boletim Oficial de Frequência FUSP")

    print("TODOS OS TESTES PASSARAM COM SUCESSO! 🎉")

if __name__ == "__main__":
    test_all()
