/**
 * Web App do Ponto Eletrônico — ponte entre o app (Python) e a planilha.
 *
 * Toda requisição é POST com JSON: { "segredo": "...", "acao": "listar" | "gravar" | "excluir", ... }
 *   - listar  -> { ok: true, registros: [ {data, entrada, inicio_pausa, fim_pausa, saida, meta_dia, observacao}, ... ] }
 *   - gravar  -> recebe { registros: [...] } e insere/atualiza SÓ essas datas
 *   - excluir -> recebe { data: "AAAA-MM-DD" } e apaga SÓ a linha dessa data
 *
 * O segredo NÃO fica neste código: fica em Configurações do projeto -> Propriedades do script,
 * com o nome SEGREDO (o mesmo valor de apps_script_secret no secrets do app).
 * Se o script não estiver "dentro" da planilha, crie também a propriedade PLANILHA_ID.
 */

var NOME_ABA = 'Registros';
var COLUNAS = ['data', 'entrada', 'inicio_pausa', 'fim_pausa', 'saida', 'meta_dia', 'observacao'];
var COLUNAS_HORARIO = ['entrada', 'inicio_pausa', 'fim_pausa', 'saida'];

var VERSAO_PROTOCOLO = 2;

function doGet() {
  // Leitura sem segredo não é mais permitida (antes devolvia tudo, inclusive a senha).
  // Só informa a versão: o app confere isso antes de mandar qualquer POST.
  return responder_({ ok: false, erro: 'Use POST com o segredo.', versao: VERSAO_PROTOCOLO });
}

function doPost(e) {
  var corpo;
  try {
    corpo = JSON.parse(e.postData.contents);
  } catch (err) {
    return responder_({ ok: false, erro: 'JSON inválido' });
  }

  var segredo = PropertiesService.getScriptProperties().getProperty('SEGREDO');
  if (!segredo || corpo.segredo !== segredo) {
    return responder_({ ok: false, erro: 'não autorizado' });
  }

  // Trava: se dois aparelhos gravarem ao mesmo tempo, um espera o outro (evita linhas duplicadas).
  var trava = LockService.getScriptLock();
  trava.waitLock(20000);
  try {
    var aba = obterAba_();
    var cab = garantirCabecalho_(aba);
    removerLinhaConfig_(aba, cab);

    if (corpo.acao === 'listar') {
      return responder_({ ok: true, registros: lerRegistros_(aba, cab) });
    }
    if (corpo.acao === 'gravar') {
      var lista = corpo.registros || [];
      for (var i = 0; i < lista.length; i++) {
        gravarRegistro_(aba, cab, lista[i]);
      }
      return responder_({ ok: true, gravados: lista.length });
    }
    if (corpo.acao === 'excluir') {
      var apagadas = excluirData_(aba, cab, String(corpo.data || ''));
      return responder_({ ok: true, excluidos: apagadas });
    }
    return responder_({ ok: false, erro: 'ação desconhecida: ' + corpo.acao });
  } catch (err) {
    return responder_({ ok: false, erro: String(err) });
  } finally {
    trava.releaseLock();
  }
}

function responder_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function obterPlanilha_() {
  var id = PropertiesService.getScriptProperties().getProperty('PLANILHA_ID');
  return id ? SpreadsheetApp.openById(id) : SpreadsheetApp.getActiveSpreadsheet();
}

function obterAba_() {
  var ss = obterPlanilha_();
  return ss.getSheetByName(NOME_ABA) || ss.getSheets()[0];
}

/** Garante a linha de cabeçalho e devolve {nomeColuna: índice começando em 0}. */
function garantirCabecalho_(aba) {
  if (aba.getLastColumn() === 0) {
    aba.getRange(1, 1, 1, COLUNAS.length).setValues([COLUNAS]);
  }
  var cabecalho = aba.getRange(1, 1, 1, aba.getLastColumn()).getDisplayValues()[0];
  var mapa = {};
  for (var c = 0; c < cabecalho.length; c++) {
    var nome = String(cabecalho[c]).trim();
    if (nome) mapa[nome] = c;
  }
  for (var i = 0; i < COLUNAS.length; i++) {
    if (mapa[COLUNAS[i]] === undefined) {
      var nova = aba.getLastColumn() + 1;
      aba.getRange(1, nova).setValue(COLUNAS[i]);
      mapa[COLUNAS[i]] = nova - 1;
    }
  }
  return mapa;
}

/** Converte a célula de data (Date ou texto) em 'AAAA-MM-DD'. */
function normalizarData_(valor, fuso) {
  if (valor instanceof Date) {
    return Utilities.formatDate(valor, fuso, 'yyyy-MM-dd');
  }
  var s = String(valor || '').trim();
  if (s === 'CONFIG_JSON' || s === '__CONFIG__') return s;
  var iso = s.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (iso) return iso[1] + '-' + iso[2] + '-' + iso[3];
  var br = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (br) return br[3] + '-' + ('0' + br[2]).slice(-2) + '-' + ('0' + br[1]).slice(-2);
  return '';
}

/** Converte o texto exibido de um horário em 'HH:MM:SS' (ou '' se vazio). */
function normalizarHorario_(texto) {
  var m = String(texto || '').match(/(\d{1,2}):(\d{2})(?::(\d{2}))?/);
  if (!m) return '';
  return ('0' + m[1]).slice(-2) + ':' + m[2] + ':' + (m[3] || '00');
}

function lerLinhas_(aba) {
  var n = aba.getLastRow() - 1;
  if (n < 1) return { valores: [], exibidos: [] };
  var faixa = aba.getRange(2, 1, n, aba.getLastColumn());
  return { valores: faixa.getValues(), exibidos: faixa.getDisplayValues() };
}

/** Números das linhas (1 = cabeçalho) cuja coluna data é igual a `dataAlvo`. */
function linhasDaData_(aba, cab, dataAlvo) {
  var fuso = obterPlanilha_().getSpreadsheetTimeZone();
  var linhas = lerLinhas_(aba);
  var achadas = [];
  for (var i = 0; i < linhas.valores.length; i++) {
    if (normalizarData_(linhas.valores[i][cab.data], fuso) === dataAlvo) achadas.push(i + 2);
  }
  return achadas;
}

function lerRegistros_(aba, cab) {
  var fuso = obterPlanilha_().getSpreadsheetTimeZone();
  var linhas = lerLinhas_(aba);
  var registros = [];
  for (var i = 0; i < linhas.valores.length; i++) {
    var v = linhas.valores[i];
    var t = linhas.exibidos[i];
    var data = normalizarData_(v[cab.data], fuso);
    if (!data || data === 'CONFIG_JSON' || data === '__CONFIG__') continue;
    var reg = { data: data };
    for (var k = 0; k < COLUNAS_HORARIO.length; k++) {
      // Horários vêm do texto exibido: evita o bug de fuso de datas de 1899 do Google Sheets.
      reg[COLUNAS_HORARIO[k]] = normalizarHorario_(t[cab[COLUNAS_HORARIO[k]]]);
    }
    reg.meta_dia = String(t[cab.meta_dia] || '').replace(',', '.');
    reg.observacao = String(v[cab.observacao] || '');
    registros.push(reg);
  }
  return registros;
}

function gravarRegistro_(aba, cab, reg) {
  var data = normalizarData_(reg.data, 'GMT');
  if (!data || data === 'CONFIG_JSON' || data === '__CONFIG__') throw new Error('data inválida: ' + reg.data);

  var largura = aba.getLastColumn();
  var linhas = linhasDaData_(aba, cab, data);
  var alvo = linhas.length ? linhas[0] : aba.getLastRow() + 1;

  // Começa da linha atual (preserva colunas extras que existam na planilha) e troca só as nossas.
  var valores = linhas.length ? aba.getRange(alvo, 1, 1, largura).getValues()[0] : new Array(largura).fill('');
  for (var i = 0; i < COLUNAS.length; i++) {
    var col = COLUNAS[i];
    var valor = reg[col] === null || reg[col] === undefined ? '' : String(reg[col]);
    if (col === 'data') valor = data;
    valores[cab[col]] = valor;
  }

  var faixa = aba.getRange(alvo, 1, 1, largura);
  faixa.setNumberFormat('@'); // grava como texto: o Sheets não converte '08:15:00' em data
  faixa.setValues([valores]);

  // Se havia linhas duplicadas da mesma data, apaga as extras (de baixo para cima).
  for (var j = linhas.length - 1; j >= 1; j--) aba.deleteRow(linhas[j]);
}

function excluirData_(aba, cab, data) {
  var linhas = linhasDaData_(aba, cab, normalizarData_(data, 'GMT'));
  for (var j = linhas.length - 1; j >= 0; j--) aba.deleteRow(linhas[j]);
  return linhas.length;
}

/** Remove a antiga linha CONFIG_JSON (ela guardava usuário e senha em texto puro). */
function removerLinhaConfig_(aba, cab) {
  var linhas = lerLinhas_(aba);
  for (var i = linhas.valores.length - 1; i >= 0; i--) {
    var d = String(linhas.valores[i][cab.data] || '').trim();
    if (d === 'CONFIG_JSON' || d === '__CONFIG__') aba.deleteRow(i + 2);
  }
}
