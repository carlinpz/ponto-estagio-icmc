# Handoff — estado do projeto em 31/10/2026

Documento de passagem de contexto de uma conversa no Claude (app) para o Claude Code.
Resume a análise do projeto, o que já foi feito e o que falta.

---

## STATUS em 01/11/2026 (noite) — leia antes da seção 0

- Etapa 1 ✅. **Etapa 2 ✅ no código** (sync por registro, síncrono, aviso + reenvio; `apps_script/Code.gs`
  escrito com segredo, trava `LockService`, remoção automática da linha `CONFIG_JSON`).
  **Etapa 3 ✅ no código**: URLs/PIN/nomes fora do código; login por hash PBKDF2 (biblioteca padrão,
  em vez de bcrypt, para não adicionar dependência); chefia com senha própria; token assinado com
  validade de 30 dias só em cookie; tela de login sem token; `html.escape` no boletim e cabeçalhos;
  configurações pessoais em `st.secrets` `[perfil]` (a aba de config no app virou somente leitura).
- Proteção extra: o app só faz POST se o `doGet` responder `versao: 2`. O Apps Script ANTIGO trata
  qualquer POST como "substituir a planilha inteira", então sem a trava o app novo poderia apagá-la.
- `.streamlit/secrets.toml` local já tem as chaves novas (senhas novas geradas; o PIN antigo morreu).
- **Pendente, depende do Carlos:** colar `Code.gs` + propriedade `SEGREDO` no Apps Script e publicar
  nova versão (mesma URL); Etapa 4 (Streamlit Cloud); Etapa 5 (os 3 registros: a gravação direta foi
  bloqueada pelo controle de permissões, então entram pelo app depois do Apps Script novo — conferido
  offline que outubro fica 20/20); Etapa 6.
- Planilha conferida em 01/11: 22 registros, idêntica ao JSON local; nada foi gravado nela hoje.

## 0. PLANO ATUAL — leia primeiro (atualizado 31/10, 15h)

O Carlos quer **deixar de depender do PC do ICMC** e bater ponto de qualquer lugar
(celular/notebook). Decisão: publicar o app no **Streamlit Community Cloud como app
privado** (repo privado → app privado; só e-mails convidados entram, com login Google).
Isso já protege a entrada do app, então a Parte B fica menor.

O Carlos está cansado do processo manual: **conduza ele passo a passo**, uma etapa por vez,
dizendo exatamente onde clicar nas partes que só ele pode fazer (sites do Google, GitHub,
Streamlit Cloud). Faça você mesmo tudo que for possível pelo terminal.

Etapas, nesta ordem:

**Etapa 1 — Commit inicial.** Commitar `CLAUDE.md` e `docs/HANDOFF.md`.

**Etapa 2 — Parte C antes de tudo: sincronização por registro.** (ver seção 3, 1º e 2º bugs)
Hoje `save_database_to_apps_script` envia a base inteira e a sincronização roda numa thread
em segundo plano que engole erros. Com vários aparelhos isso vai apagar dias. Mudar para:
gravar/excluir **um registro por data** (upsert/delete no Apps Script), de forma **síncrona**,
mostrando erro visível ao usuário se falhar. Escrever o novo código do Apps Script
(`doGet`/`doPost`) para o Carlos colar — já incluindo a verificação do **segredo
compartilhado** (Parte B, item 6) e sem devolver/gravar a linha `CONFIG_JSON` com credenciais.
Ensinar a atualizar o Apps Script **mantendo a URL**: Implantar → Gerenciar implantações →
lápis ✏️ → Versão: "Nova versão" → Implantar.

**Etapa 3 — Parte B reduzida.** Com o login Google do Streamlit Cloud na frente, fazer só:
- tirar URLs fixas (`DEFAULT_APPS_SCRIPT_URL`, `DEFAULT_SPREADSHEET_CSV_URL`) do código;
- tirar senha/PIN e nomes reais do código, testes e planilha (config pessoal vai para secrets);
- remover o token do HTML da tela de login (`components.py`, `render_welcome_screen`);
- `html.escape` em observações/nomes no HTML;
- simplificar ou remover o login interno do app SE fizer sentido com o login Google —
  proponha no plano e explique a troca ao Carlos antes de decidir.
- Atualizar `.streamlit/secrets.toml.example` e testes.

**Etapa 4 — Publicar no Streamlit Cloud (guiar o Carlos).**
share.streamlit.io → login com GitHub (carlinpz) → se existir app antigo do ponto, apagar
ou reconfigurar → Create app: repo `carlinpz/ponto-estagio-icmc`, branch `main`, arquivo
`app.py` → Advanced settings → Secrets (colar o conteúdo do `secrets.toml` local) → Deploy →
Settings → Sharing → "Only specific people can view this app" → adicionar
carlinhospizzi@gmail.com (e o e-mail da supervisora, se ele quiser) → testar em aba anônima.
Celular: abrir o link e "Adicionar à tela inicial". Avisar: app dorme sem uso e leva ~30 s
para acordar; plano grátis permite 1 app privado.

**Etapa 5 — Corrigir dados.** Inserir na planilha (pelo app ou via código, depois da Etapa 2):
- 02/10: 08:15 · 12:40 · 13:40 · 15:15 · meta 6 · "Ajuste manual"
- 05/10: 08:15 · 13:00 · 14:00 · 15:15 · meta 6 · "Ajuste manual"
- 30/10: sem horários · meta 0 · "Feriado"
Conferir: painel da chefia de outubro deve mostrar assiduidade 20 de 20 dias.

**Etapa 6 — Aposentar o uso local no PC do ICMC** (o ponto passa a ser só pelo link).

Depois disso: configurar subagentes/hook neste projeto (seção 4) e, mais adiante, o hub.

---

## 1. O que já foi feito (Parte A — contenção, concluída em 31/10)

- Repositório GitHub `carlinpz/ponto-estagio-icmc` tornado **privado**.
- Planilha Google restringida (só o dono tem acesso; sem link público).
  → Consequência: a leitura rápida via export CSV público (`load_database_from_sheet_csv`)
    **não funciona mais**; o app cai no Apps Script. Isso é esperado.
- Apps Script: criada **nova implantação** (Executar como: Eu / Acesso: Qualquer pessoa)
  e a implantação antiga foi **arquivada**. A URL antiga que ainda aparece fixa em
  `storage.py` (`DEFAULT_APPS_SCRIPT_URL`) está morta.
- URL nova configurada em `.streamlit/secrets.toml` como `apps_script_url` (fora do git).
- Backup da planilha: "Cópia de Ponto Eletrônico - Carlos" no Drive.
- Projeto movido para `C:\Users\carli\projetos\ponto_estagio` (fora de Drive/OneDrive).
- Commit "chore: salva melhorias de 21/10 e para de versionar dados pessoais" enviado ao GitHub.
  `ponto_eletronico.json`, `projeto_completo.md`, `historico_chats/` saíram do versionamento.

- 31/10 15h: app rodando local no notebook, confirmado lendo da planilha pela URL nova.

### Pendências de dados (ver Etapa 5 na seção 0)
- **02/10** (sex): 08:15 · 12:40 · 13:40 · 15:15 — sumiu da planilha (sobrescrita pelo bug de sync).
- **05/10** (seg): 08:15 · 13:00 · 14:00 · 15:15 — idem.
- **30/10** (sex): feriado → carga 0, observação "Feriado".
- Conferir que o PC do ICMC (onde o ponto é batido no dia a dia) também está com o
  `secrets.toml` novo antes de bater ponto em 02/11.

---

## 2. Parte B — correções de segurança (lista completa; a seção 0 define o que fazer agora)

Escopo: SOMENTE segurança. Não mexer em cálculos, layout ou outras funcionalidades.
Apresentar o plano antes de editar.

Este app será substituído quando o hub existir (seção 4). Prefira a solução **mais simples
que seja segura** em cada item — sem frameworks de auth novos ou arquitetura elaborada.
Se algum item abaixo parecer exagerado para esse contexto, proponha a alternativa simples
no plano.

1. **Token exposto na tela de login.** `components.py` (~linha 803, `render_welcome_screen`)
   injeta `expected_token` no JavaScript enviado a qualquer visitante não autenticado.
   Quem abrir o site lê o token e entra com `?acesso=estagiario&token=...`.
2. **URLs fixas.** `DEFAULT_APPS_SCRIPT_URL` e `DEFAULT_SPREADSHEET_CSV_URL` em `storage.py`
   devem sair do código. Sem secret configurado, o app funciona só com JSON local.
3. **Credenciais no código e na planilha.** Usuário/PIN em `DEFAULT_CONFIG` (`storage.py`),
   fallbacks `or "carlos"` / `or "<PIN>"` em `app.py` e `components.py`, testes em `test_app.py`,
   e gravados na planilha na linha `CONFIG_JSON`. A senha deve existir só em `st.secrets`,
   como hash bcrypt, e nunca ser enviada à planilha. A tela de troca de senha atual deixa de
   fazer sentido (troca passa a ser: gerar novo hash e atualizar secrets).
4. **Token fraco e eterno na URL.** `compute_auth_token` = SHA-256 de usuário+senha, truncado,
   sem expiração, trafega na query string. Trocar por token aleatório assinado com expiração
   (~30 dias), só em cookie, nunca na URL.
5. **Chefia sem senha.** Qualquer um com `?acesso=gestao` vê horários e status em tempo real.
   Criar senha própria da chefia (hash em secrets).
6. **Apps Script sem autenticação.** `doGet` devolve tudo (inclusive config) e `doPost`
   aceita sobrescrever a base inteira. Enviar um segredo compartilhado (secrets) em toda
   requisição e **escrever o novo código de `doGet`/`doPost`** para o usuário colar no
   editor do Apps Script manualmente (o Claude Code não tem acesso ao Apps Script).
7. **HTML sem escape.** Observações e nomes vão crus para o HTML do boletim e para `render_html`.
8. **Dados pessoais no código.** Nomes reais em `DEFAULT_CONFIG` e defaults de `text_input`.

Entregáveis extras:
- `.streamlit/secrets.toml.example` atualizado com todas as chaves (valores fictícios).
- Script para gerar hash bcrypt de uma senha.
- Testes: senha errada falha; token adulterado/expirado rejeitado; HTML da tela de login
  não contém token; nenhum segredo em `.py`/`.json` versionados; observação com `<script>` escapada.
- Resumo final do que o usuário precisa configurar (secrets + Apps Script).

---

## 3. Bugs conhecidos (para depois da Parte B)

- **Sincronização sobrescreve tudo (último a gravar vence).** `save_database_to_apps_script`
  envia a base inteira. Duas sessões (PC do ICMC + notebook + celular) apagam dados uma da
  outra — foi o que apagou 02/10 e 05/10. Solução: upsert/delete por data no Apps Script.
- **Falha de sync silenciosa e agora assíncrona.** Na versão atual, `save_database` dispara
  a sincronização numa `threading.Thread` daemon; erro vira só `print`. O usuário acha que
  bateu ponto e não salvou. Precisa de feedback visível e, idealmente, fila de reenvio.
- **Dia sem saída nunca entra no saldo** (fica "Em andamento" para sempre; só alerta na chefia).
- **Dia útil sem registro não conta como falta** no banco de horas.
- **Validação de pausa fora do intervalo entrada–saída** ausente no cálculo
  (entrada 08:00 + pausa 07:00–07:30 + saída 14:00 calcula 5,5 h sem erro).
- **Alerta legal inconsistente:** dispara > 6,5 h mas a mensagem cita 6 h; não há checagem
  do limite semanal de 30 h; "30h semanais" fixo no texto.
- **Arredondamento:** horas arredondadas a 2 casas (36 s) antes de somar o saldo. Calcular
  em segundos/minutos inteiros.
- **Ajuste manual de feriado** só funciona se a observação contiver "feriado"; "Abono" com
  carga 0 grava horários padrão.
- **Carregamento lento:** requisições de rede síncronas a cada nova sessão, sem `st.cache_data`.
- Código morto/duplicado: leitores CSV e Apps Script quase idênticos; deduplicação em vários
  lugares; `fetch_fusp.py` usa `bs4` fora do requirements.
- Testes: um único `test_all()` sequencial; sem cobertura de `storage`.

---

## 4. Visão de longo prazo: hub de sistemas

Objetivo do Carlos: vários sistemas num mesmo domínio, acessados por um portal.
**O hub NÃO será necessariamente em Streamlit** — será reestruturado do zero mais adiante.

Direção atual (ainda não decidida em definitivo):
- **Modelo preferido: um único app web modular** (cada sistema = um módulo/rota:
  `/ponto`, `/sistema2`...), com login, banco de dados, layout e menu compartilhados.
  Evita o problema de login único entre apps separados. Um módulo pode ser extraído
  para serviço próprio no futuro, se precisar.
- **Stack candidata: Django** (Python; já traz auth, permissões, ORM, admin; "projeto com
  vários apps" casa com a ideia do hub). Alternativa: Next.js.
- **Banco de dados de verdade** (SQLite para começar, PostgreSQL em produção). Google Sheets
  deixa de ser fonte da verdade — no máximo exportação.

Sistemas planejados para o hub:
- **ponto** — este app, migrado.
- **concursos** — estudo para concursos com provas antigas: escolher concurso, nível e tema;
  responder questões; registrar progresso (acertos por tema, histórico, refazer erradas).
  Modelo de dados esboçado: Concurso ─< Prova ─< Questão ─< Alternativa; Questão ↔ Tema
  (hierárquico); Usuário ─< Resposta (alternativa marcada, acerto, data, tempo).
  Entrada de questões: script que extrai prova + gabarito de PDF para dados estruturados,
  com revisão humana no Django admin antes de publicar.
- Outros sistemas futuros, todos sob o mesmo domínio e login.

Plano: o hub em Django começa pelo app **concursos** (projeto novo, sem risco); o ponto
migra depois, quando Django já for familiar.

Implicações para o trabalho atual:
- A Parte B deve ser **simples e suficiente** (o app está em uso diário), sem investir em
  um sistema de login sofisticado em Streamlit que será descartado.
- `calculations.py` (regras de jornada, saldo, ciclo FUSP, conformidade) é o ativo mais
  reaproveitável na migração: manter independente de Streamlit e bem testado.

### Equipe de subagentes planejada (`.claude/agents/`)
- `revisor` — só leitura (Read, Grep, Glob, Bash); revisa `git diff` buscando bugs,
  segurança e violações do CLAUDE.md; responde por gravidade com arquivo:linha.
- `testador` — escreve testes pytest que tentam quebrar o código; só edita `tests/`.
- `corretor` — recebe UM problema diagnosticado e faz a menor correção possível.
Hook planejado: `PostToolUse` em `Edit|Write` rodando `ruff` + checagem de credenciais
fixas, retornando exit 2 para o Claude corrigir.

### Ordem combinada
1. ✅ Parte A (contenção)
2. Parte B (segurança do ponto, versão simples) ← **próximo**
3. Configurar subagentes e hook neste projeto (para aprender o fluxo)
4. Criar o hub em Django começando pelo app `concursos`
5. Migrar o ponto para o hub, reaproveitando `calculations.py`
6. Demais sistemas
