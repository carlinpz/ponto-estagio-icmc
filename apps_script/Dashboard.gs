/**
 * Painel de Frequência (Dashboard) — cria e atualiza um painel visual na planilha do ponto.
 *
 * Este arquivo fica no MESMO projeto do Apps Script que o Code.gs (é um segundo arquivo).
 * Ele usa funções do Code.gs: obterPlanilha_, lerRegistros_, NOME_ABA.
 *
 * Como usar:
 *   1. No editor, selecione a função montarDashboard e clique em Executar (só na primeira vez).
 *   2. Depois disso, o painel se atualiza sozinho a cada hora. Para atualizar na hora,
 *      use o menu "Ponto → Atualizar painel" da planilha (ou execute atualizarPainel).
 *
 * Regra importante: este código SÓ LÊ a aba Registros. Nunca grava nela.
 * Ele só escreve nas duas abas que ele mesmo cria: "Dashboard" e "Dados do painel".
 *
 * As contas seguem as mesmas regras do calculations.py (process_records_dataframe),
 * para que os números do painel batam com os do app.
 */

var ABA_PAINEL = 'Dashboard';
var ABA_DADOS = 'Dados do painel';
var META_PADRAO = 6; // horas por dia, igual ao padrão do app
var LINHAS_TABELA = 30; // quantos registros recentes aparecem na tabela do painel
var PALAVRAS_ABONO = ['feriado', 'recesso', 'dispensa', 'abono', 'folga'];

var COR = {
  titulo: '#1f3a5f',
  tituloTexto: '#ffffff',
  cartao: '#f3f6fa',
  borda: '#d5dde8',
  rotulo: '#5b6b7f',
  valor: '#1f3a5f',
  positivo: '#1e7e34',
  negativo: '#c62828',
  cabecalhoTabela: '#e3eaf3',
  listra: '#fafbfd'
};

/** Cria o menu "Ponto" quando a planilha é aberta (só funciona se o script estiver "dentro" da planilha). */
function onOpen() {
  try {
    SpreadsheetApp.getUi()
      .createMenu('Ponto')
      .addItem('Atualizar painel', 'atualizarPainel')
      .addToUi();
  } catch (err) {
    // Script fora da planilha: não há menu, mas o gatilho de hora em hora continua funcionando.
  }
}

/** Rode UMA vez: monta o painel e cria o gatilho que atualiza a cada hora. */
function montarDashboard() {
  atualizarPainel();
  criarGatilhoHorario_();
}

/** Recalcula tudo e redesenha o painel. Pode rodar quantas vezes quiser. */
function atualizarPainel() {
  var ss = obterPlanilha_();
  var fuso = ss.getSpreadsheetTimeZone();

  var abaRegistros = ss.getSheetByName(NOME_ABA);
  if (!abaRegistros) throw new Error('Aba "' + NOME_ABA + '" não encontrada.');

  var dias = calcularDias_(lerRegistros_(abaRegistros, mapaCabecalho_(abaRegistros)));
  var hoje = Utilities.formatDate(new Date(), fuso, 'yyyy-MM-dd');
  var ciclo = cicloFuspAtual_(hoje);
  var resumo = resumir_(dias, ciclo);

  var dados = prepararAba_(ss, ABA_DADOS);
  escreverDados_(dados, dias);

  var painel = prepararAba_(ss, ABA_PAINEL);
  desenharPainel_(painel, dados, dias, resumo, ciclo, fuso);

  try {
    dados.hideSheet();
    ss.setActiveSheet(painel);
    ss.moveActiveSheet(1);
  } catch (err) {
    // Fora da planilha (script avulso) essas ações de tela podem falhar; o painel já foi gravado.
  }
}

// ---------------------------------------------------------------------------
// Leitura (somente leitura da aba Registros)
// ---------------------------------------------------------------------------

/** Mapa {nomeColuna: índice} lido do cabeçalho, SEM criar colunas (diferente de garantirCabecalho_). */
function mapaCabecalho_(aba) {
  var mapa = {};
  if (aba.getLastColumn() === 0) return mapa;
  var cab = aba.getRange(1, 1, 1, aba.getLastColumn()).getDisplayValues()[0];
  for (var c = 0; c < cab.length; c++) {
    var nome = String(cab[c]).trim();
    if (nome) mapa[nome] = c;
  }
  return mapa;
}

// ---------------------------------------------------------------------------
// Regras (espelho do calculations.py)
// ---------------------------------------------------------------------------

/** 'HH:MM:SS' -> horas decimais (8.25), ou null se vazio. */
function horaDecimal_(texto) {
  var m = String(texto || '').match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
  if (!m) return null;
  return Number(m[1]) + Number(m[2]) / 60 + Number(m[3] || 0) / 3600;
}

/** Horas líquidas do dia: (saída − entrada) − pausa. Igual a calculate_day_worked_hours. */
function horasTrabalhadas_(ent, ini, fim, sai) {
  var bruto = sai - ent;
  if (bruto < 0) bruto += 24; // cruzou a meia-noite
  var pausa = 0;
  if (ini !== null && fim !== null) {
    pausa = fim - ini;
    if (pausa < 0) pausa += 24;
  }
  return Math.max(0, bruto - pausa);
}

/** Transforma os registros em dias calculados, em ordem cronológica, com o banco acumulado. */
function calcularDias_(registros) {
  // Uma linha por data (a última vence), como no app.
  var porData = {};
  for (var i = 0; i < registros.length; i++) porData[registros[i].data] = registros[i];
  var datas = Object.keys(porData).sort();

  var dias = [];
  var banco = 0;
  for (var j = 0; j < datas.length; j++) {
    var r = porData[datas[j]];
    var ent = horaDecimal_(r.entrada);
    var ini = horaDecimal_(r.inicio_pausa);
    var fim = horaDecimal_(r.fim_pausa);
    var sai = horaDecimal_(r.saida);
    var meta = parseFloat(String(r.meta_dia || '').replace(',', '.'));
    if (isNaN(meta)) meta = META_PADRAO;
    var obs = String(r.observacao || '');
    var obsMinusc = obs.toLowerCase();

    var horas = 0;
    var saldo;
    var status;
    if (ent !== null && sai !== null) {
      horas = horasTrabalhadas_(ent, ini, fim, sai);
      saldo = horas - meta;
      status = 'Concluído';
    } else if (ent !== null) {
      saldo = 0;
      status = 'Em andamento';
    } else if (meta === 0 || PALAVRAS_ABONO.some(function (p) { return obsMinusc.indexOf(p) >= 0; })) {
      saldo = 0;
      status = 'Feriado / Abono';
    } else {
      saldo = -meta;
      status = 'Ausente';
    }
    banco += saldo;

    var intervalo = null;
    if (ini !== null && fim !== null) {
      intervalo = fim - ini;
      if (intervalo < 0) intervalo += 24;
    }

    dias.push({
      data: datas[j],
      ent: ent, ini: ini, fim: fim, sai: sai,
      horas: horas, meta: meta, saldo: saldo, banco: banco,
      intervalo: intervalo, status: status, obs: obs
    });
  }
  return dias;
}

/** Ciclo FUSP que contém a data: do dia 21 do mês anterior ao dia 20 (igual a get_fusp_period_dates). */
function cicloFuspAtual_(hojeIso) {
  var p = hojeIso.split('-');
  var ano = Number(p[0]);
  var mes = Number(p[1]);
  var dia = Number(p[2]);
  // A partir do dia 21, já estamos no ciclo que termina no dia 20 do mês seguinte.
  var mesFim = dia >= 21 ? mes + 1 : mes;
  var anoFim = ano;
  if (mesFim === 13) { mesFim = 1; anoFim += 1; }
  var mesIni = mesFim - 1;
  var anoIni = anoFim;
  if (mesIni === 0) { mesIni = 12; anoIni -= 1; }
  return {
    inicio: anoIni + '-' + dois_(mesIni) + '-21',
    fim: anoFim + '-' + dois_(mesFim) + '-20'
  };
}

function resumir_(dias, ciclo) {
  var r = {
    banco: 0,
    horasCiclo: 0, diasCiclo: 0, faltasCiclo: 0,
    somaEnt: 0, nEnt: 0, somaSai: 0, nSai: 0
  };
  for (var i = 0; i < dias.length; i++) {
    var d = dias[i];
    r.banco += d.saldo;
    if (d.data >= ciclo.inicio && d.data <= ciclo.fim) {
      r.horasCiclo += d.horas;
      if (d.status === 'Concluído') r.diasCiclo += 1;
      if (d.status === 'Ausente') r.faltasCiclo += 1;
      if (d.ent !== null) { r.somaEnt += d.ent; r.nEnt += 1; }
      if (d.sai !== null) { r.somaSai += d.sai; r.nSai += 1; }
    }
  }
  return r;
}

// ---------------------------------------------------------------------------
// Formatação
// ---------------------------------------------------------------------------

function dois_(n) {
  return ('0' + n).slice(-2);
}

/** Horas decimais -> '[+/-]HHh MMm', igual a decimal_hours_to_hm_str. */
function formatarHoras_(horas, comSinal) {
  var minutos = Math.round(Math.abs(horas) * 60);
  var sinal = '';
  if (horas < 0 && minutos > 0) sinal = '-';
  else if (comSinal && horas > 0 && minutos > 0) sinal = '+';
  return sinal + dois_(Math.floor(minutos / 60)) + 'h ' + dois_(minutos % 60) + 'm';
}

/** Horas decimais do relógio (8.25) -> '08:15'. */
function formatarRelogio_(h) {
  if (h === null || h === undefined) return '–';
  var minutos = Math.round(h * 60);
  return dois_(Math.floor(minutos / 60) % 24) + ':' + dois_(minutos % 60);
}

function formatarDataBr_(iso) {
  var p = iso.split('-');
  return p[2] + '/' + p[1] + '/' + p[0];
}

var DIAS_SEMANA = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

function diaSemana_(iso) {
  var p = iso.split('-');
  return DIAS_SEMANA[new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]), 12).getDay()];
}

/** Evita que uma observação começando com "=" vire fórmula na planilha. */
function textoSeguro_(s) {
  s = String(s || '');
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

/** Frase curta sob o banco, para quem não conhece a conta. */
function explicarBanco_(h) {
  var minutos = Math.round(h * 60);
  if (minutos > 0) return 'horas a mais, para folgar depois';
  if (minutos < 0) return 'horas a compensar';
  return 'em dia';
}

function corDoSaldo_(h) {
  if (Math.round(h * 60) > 0) return COR.positivo;
  if (Math.round(h * 60) < 0) return COR.negativo;
  return COR.valor;
}

// ---------------------------------------------------------------------------
// Escrita (só nas abas do painel)
// ---------------------------------------------------------------------------

/** Pega (ou cria) a aba e a deixa limpa: sem conteúdo, formatos, mesclagens e gráficos. */
function prepararAba_(ss, nome) {
  var aba = ss.getSheetByName(nome) || ss.insertSheet(nome);
  aba.getCharts().forEach(function (g) { aba.removeChart(g); });
  aba.getRange(1, 1, aba.getMaxRows(), aba.getMaxColumns()).breakApart();
  aba.clear();
  aba.setConditionalFormatRules([]);
  return aba;
}

/** Tabela que alimenta os gráficos. Horários ficam como fração do dia, formatados hh:mm. */
function escreverDados_(aba, dias) {
  var cab = ['Data', 'Horas trabalhadas', 'Meta (h)', 'Banco de horas (h)',
             'Entrada', 'Saída', 'Intervalo (min)'];
  var linhas = [cab];
  for (var i = 0; i < dias.length; i++) {
    var d = dias[i];
    var p = d.data.split('-');
    linhas.push([
      new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]), 12), // meio-dia: evita pular de dia por fuso
      Math.round(d.horas * 100) / 100,
      d.meta,
      Math.round(d.banco * 100) / 100,
      d.ent === null ? '' : d.ent / 24,
      d.sai === null ? '' : d.sai / 24,
      d.intervalo === null ? '' : Math.round(d.intervalo * 60)
    ]);
  }
  aba.getRange(1, 1, linhas.length, cab.length).setValues(linhas);
  aba.getRange(1, 1, 1, cab.length).setFontWeight('bold');
  if (dias.length) {
    aba.getRange(2, 1, dias.length, 1).setNumberFormat('dd/MM');
    aba.getRange(2, 2, dias.length, 3).setNumberFormat('0.00');
    aba.getRange(2, 5, dias.length, 2).setNumberFormat('hh:mm');
    aba.getRange(2, 7, dias.length, 1).setNumberFormat('0');
  }
}

function desenharPainel_(aba, dados, dias, r, ciclo, fuso) {
  aba.setHiddenGridlines(true);
  aba.setColumnWidth(1, 24);
  aba.setColumnWidths(2, 12, 108);
  aba.setColumnWidth(13, 220); // observação

  // Título
  aba.getRange('B1:M1').merge()
    .setValue('Painel de Frequência do Estágio')
    .setFontSize(20).setFontWeight('bold')
    .setFontColor(COR.tituloTexto).setBackground(COR.titulo)
    .setVerticalAlignment('middle');
  aba.setRowHeight(1, 52);
  aba.getRange('B2:M2').merge()
    .setValue('Ciclo FUSP atual: ' + formatarDataBr_(ciclo.inicio) + ' a ' + formatarDataBr_(ciclo.fim) +
              '   ·   Atualizado em ' + Utilities.formatDate(new Date(), fuso, "dd/MM/yyyy 'às' HH:mm") +
              '   ·   Horários reais registrados no ponto')
    .setFontColor(COR.rotulo).setFontStyle('italic');

  // Cartões (4 cartões de 3 colunas cada, de B a M).
  // Só o banco fala de saldo: números separados de "horas a mais" e "horas a menos"
  // eram lidos como dívida por quem não conhece a conta.
  var mediaEnt = r.nEnt ? formatarRelogio_(r.somaEnt / r.nEnt) : '–';
  var mediaSai = r.nSai ? formatarRelogio_(r.somaSai / r.nSai) : '–';
  var cartoes = [
    ['BANCO DE HORAS', formatarHoras_(r.banco, true), explicarBanco_(r.banco), corDoSaldo_(r.banco)],
    ['HORAS NO CICLO', formatarHoras_(r.horasCiclo, false), 'trabalhadas no ciclo atual', COR.valor],
    ['DIAS NO CICLO', String(r.diasCiclo), r.faltasCiclo + (r.faltasCiclo === 1 ? ' falta' : ' faltas') + ' no ciclo', COR.valor],
    ['HORÁRIO MÉDIO', mediaEnt + ' → ' + mediaSai, 'entrada → saída no ciclo', COR.valor]
  ];
  var largura = 3;
  for (var c = 0; c < cartoes.length; c++) {
    var col = 2 + c * largura;
    var bloco = aba.getRange(4, col, 3, largura);
    bloco.setBackground(COR.cartao)
      .setBorder(true, true, true, true, false, false, COR.borda, SpreadsheetApp.BorderStyle.SOLID)
      .setHorizontalAlignment('center');
    aba.getRange(4, col, 1, largura).merge().setValue(cartoes[c][0])
      .setFontSize(9).setFontWeight('bold').setFontColor(COR.rotulo);
    aba.getRange(5, col, 1, largura).merge().setValue(cartoes[c][1])
      .setFontSize(18).setFontWeight('bold').setFontColor(cartoes[c][3]);
    aba.getRange(6, col, 1, largura).merge().setValue(cartoes[c][2])
      .setFontSize(9).setFontColor(COR.rotulo);
  }
  aba.setRowHeight(5, 40);

  if (!dias.length) {
    aba.getRange('B8').setValue('Ainda não há registros na aba ' + NOME_ABA + '.');
    return;
  }

  // Gráficos (2 por linha). Cada um lê a aba "Dados do painel".
  var n = dias.length + 1; // + cabeçalho
  var colData = dados.getRange(1, 1, n, 1);
  var base = { largura: 640, altura: 320 };

  aba.insertChart(aba.newChart()
    .setChartType(Charts.ChartType.COMBO)
    .addRange(colData).addRange(dados.getRange(1, 2, n, 2))
    .setNumHeaders(1)
    .setOption('title', 'Horas trabalhadas por dia × meta')
    .setOption('seriesType', 'bars')
    .setOption('series', { 0: { type: 'bars', color: '#3b6ea5' },
                           1: { type: 'line', color: '#e0a100', lineWidth: 2 } })
    .setOption('vAxis', { title: 'horas', minValue: 0 })
    .setOption('legend', { position: 'bottom' })
    .setOption('width', base.largura).setOption('height', base.altura)
    .setPosition(8, 2, 0, 0)
    .build());

  aba.insertChart(aba.newChart()
    .setChartType(Charts.ChartType.AREA)
    .addRange(colData).addRange(dados.getRange(1, 4, n, 1))
    .setNumHeaders(1)
    .setOption('title', 'Evolução do banco de horas')
    .setOption('colors', ['#2e7d32'])
    .setOption('vAxis', { title: 'horas' })
    .setOption('legend', { position: 'none' })
    .setOption('width', base.largura).setOption('height', base.altura)
    .setPosition(8, 8, 0, 0)
    .build());

  aba.insertChart(aba.newChart()
    .setChartType(Charts.ChartType.LINE)
    .addRange(colData).addRange(dados.getRange(1, 5, n, 2))
    .setNumHeaders(1)
    .setOption('title', 'Horário de entrada e saída')
    .setOption('colors', ['#3b6ea5', '#c62828'])
    .setOption('pointSize', 5)
    .setOption('legend', { position: 'bottom' })
    .setOption('width', base.largura).setOption('height', base.altura)
    .setPosition(25, 2, 0, 0)
    .build());

  aba.insertChart(aba.newChart()
    .setChartType(Charts.ChartType.COLUMN)
    .addRange(colData).addRange(dados.getRange(1, 7, n, 1))
    .setNumHeaders(1)
    .setOption('title', 'Duração do intervalo (minutos)')
    .setOption('colors', ['#7e57c2'])
    .setOption('vAxis', { title: 'minutos', minValue: 0 })
    .setOption('legend', { position: 'none' })
    .setOption('width', base.largura).setOption('height', base.altura)
    .setPosition(25, 8, 0, 0)
    .build());

  // Tabela dos registros mais recentes
  var linhaTitulo = 43;
  aba.getRange(linhaTitulo, 2, 1, 12).merge()
    .setValue('Últimos ' + Math.min(LINHAS_TABELA, dias.length) + ' registros')
    .setFontSize(13).setFontWeight('bold').setFontColor(COR.valor);

  var cab = ['Data', 'Dia', 'Entrada', 'Saída intervalo', 'Volta intervalo', 'Saída',
             'Intervalo', 'Horas', 'Meta', 'Saldo do dia', 'Banco', 'Observação'];
  var recentes = dias.slice(-LINHAS_TABELA).reverse();
  var linhas = [];
  var cores = [];
  for (var i = 0; i < recentes.length; i++) {
    var d = recentes[i];
    var concluido = d.status === 'Concluído';
    linhas.push([
      formatarDataBr_(d.data),
      diaSemana_(d.data),
      formatarRelogio_(d.ent),
      formatarRelogio_(d.ini),
      formatarRelogio_(d.fim),
      formatarRelogio_(d.sai),
      d.intervalo === null ? '–' : Math.round(d.intervalo * 60) + ' min',
      concluido ? formatarHoras_(d.horas, false) : d.status,
      formatarHoras_(d.meta, false),
      formatarHoras_(d.saldo, true),
      formatarHoras_(d.banco, true),
      textoSeguro_(d.obs)
    ]);
    var linhaCores = [];
    for (var k = 0; k < cab.length; k++) linhaCores.push(COR.valor);
    linhaCores[9] = corDoSaldo_(d.saldo);
    linhaCores[10] = corDoSaldo_(d.banco);
    cores.push(linhaCores);
  }

  var linhaCab = linhaTitulo + 1;
  aba.getRange(linhaCab, 2, 1, cab.length).setValues([cab])
    .setFontWeight('bold').setBackground(COR.cabecalhoTabela).setFontColor(COR.valor)
    .setHorizontalAlignment('center');
  var corpo = aba.getRange(linhaCab + 1, 2, linhas.length, cab.length);
  corpo.setNumberFormat('@'); // texto puro: o Sheets não reinterpreta datas e horários
  corpo.setValues(linhas).setFontColors(cores).setHorizontalAlignment('center');
  aba.getRange(linhaCab + 1, 13, linhas.length, 1).setHorizontalAlignment('left').setWrap(true);
  for (var j = 1; j < linhas.length; j += 2) {
    aba.getRange(linhaCab + 1 + j, 2, 1, cab.length).setBackground(COR.listra);
  }
  aba.getRange(linhaCab, 2, linhas.length + 1, cab.length)
    .setBorder(true, true, true, true, false, true, COR.borda, SpreadsheetApp.BorderStyle.SOLID);
  aba.setFrozenRows(2);
}

/** Cria o gatilho de hora em hora, sem duplicar se já existir. */
function criarGatilhoHorario_() {
  var existentes = ScriptApp.getProjectTriggers();
  for (var i = 0; i < existentes.length; i++) {
    if (existentes[i].getHandlerFunction() === 'atualizarPainel') return;
  }
  ScriptApp.newTrigger('atualizarPainel').timeBased().everyHours(1).create();
}
