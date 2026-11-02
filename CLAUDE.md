# Ponto Eletrônico de Estágio — ICMC/USP

App Streamlit de ponto eletrônico e banco de horas para UM estagiário (Carlos), com
visão somente leitura para a supervisora. Gera o Boletim de Frequência FUSP (ciclo 21→20).

Este projeto será o primeiro de vários sistemas de um futuro **hub** num mesmo domínio,
que provavelmente NÃO será em Streamlit (ver `docs/HANDOFF.md`, seção 4). Por isso:
não investir em soluções sofisticadas específicas de Streamlit, e manter as regras de
negócio (`calculations.py`) independentes da interface e bem testadas.

Contexto completo, histórico de decisões e próximos passos: `docs/HANDOFF.md`.
Leia esse arquivo no início de qualquer tarefa não trivial.

## Arquitetura
- `app.py` — fluxo principal Streamlit, autenticação, sidebar e abas.
- `calculations.py` — regras de jornada, saldo, conformidade (Lei 11.788/2008), HTML do boletim FUSP.
- `components.py` — cards, gráficos Plotly, painel da chefia, tela de login, cookies.
- `storage.py` — cache JSON local (`ponto_eletronico.json`, só registros) + sincronização POR REGISTRO
  com Google Sheets via Apps Script (gravar/excluir uma data, síncrono, erro visível, pendências com reenvio).
- `apps_script/Code.gs` — código do Web App (colado manualmente no editor do Apps Script; segredo em
  Propriedades do script, nunca no código). Protocolo versionado: o app só faz POST se o GET devolver `versao: 2`.
- `auth.py` — hash de senha (PBKDF2) e token de login assinado com validade; `gerar_hash_senha.py` gera hashes.
- `theme.py` — CSS, logo SVG, relógio em JS.
- `launcher.pyw` / `iniciar_ponto.bat` — inicia o app no Windows sem janela de terminal.
- Dados de verdade ficam na planilha Google "Ponto Eletrônico - Carlos" (aba Registros).

## Regras invioláveis
- NUNCA colocar senhas, PINs, tokens ou URLs de Apps Script/planilha no código, testes ou docs.
  Tudo vem de `st.secrets` (`.streamlit/secrets.toml`, fora do git) ou variáveis de ambiente.
- NUNCA commitar dados pessoais: `ponto_eletronico.json`, `historico_chats/`, `projeto_completo.md`
  estão no `.gitignore` e devem continuar assim.
- Todo texto vindo de usuário/dados inserido em HTML passa por `html.escape()`.
- Mudanças que gravam na planilha não podem sobrescrever registros que a sessão não alterou.
- Não refatorar o que não foi pedido. Escopo de cada tarefa é o que o usuário definiu.

## Fluxo de trabalho
1. Tarefa não trivial → apresentar plano e esperar aprovação antes de editar.
2. Implementar em passos pequenos.
3. Rodar os testes. Para bug corrigido, criar teste que falharia antes da correção.
4. Ao terminar, resumir o que mudou e o que o usuário precisa fazer manualmente
   (secrets, Apps Script, etc.). Explicar as decisões: o usuário está aprendendo e quer entender.

## Comandos (Windows / PowerShell)
- Ambiente: `.\.venv\Scripts\Activate.ps1` (criar com `python -m venv .venv` se não existir)
- Dependências: `pip install -r requirements.txt`
- Rodar: `python -m streamlit run app.py`
- Testes: `python -m pytest -q test_app.py`

## Sobre o usuário
Carlos está aprendendo desenvolvimento com IA. Responda em português, explique conceitos
quando introduzir algo novo e prefira soluções simples e bem explicadas a soluções espertas.
