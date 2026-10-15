# ⏱️ Ponto Inteligente — Sistema de Ponto Eletrônico e Banco de Horas de Estágio

Aplicação web interativa desenvolvida em **Python** com **Streamlit**, criada especialmente para estagiários gerenciarem sua jornada de trabalho, calcularem banco de horas (horas extras vs. horas devidas) e emitirem relatórios mensais de forma simples, elegante e segura.

---

## 🚀 Funcionalidades Principais

1. **⚡ Registro Rápido de Ponto:**
   - Botões principais na tela inicial e na barra lateral:
     - 🟢 **Registrar Entrada**
     - ☕ **Iniciar Pausa / Almoço**
     - 🥪 **Retornar da Pausa**
     - 🔴 **Registrar Saída**
   - Captura automática do horário local (`datetime.now()`).
   - Validações inteligentes de fluxo (evita registrar saída antes da entrada, pausas duplicadas ou registrar entrada duas vezes no mesmo dia).
   - Relógio em tempo real e indicador de status da jornada (Não Iniciado, Em Expediente, Em Pausa, Finalizado).

2. **⚙️ Configurações Customizáveis:**
   - Definição da carga horária diária padrão (ex: 6.0 horas para jornadas de 30h semanais).
   - Definição dos dias úteis esperados da semana (ex: Segunda a Sexta).
   - Identificação personalizada com o nome do estagiário.

3. **📊 Painel de Métricas (Dashboard no Topo):**
   - Total de dias trabalhados no mês.
   - Total de horas realizadas (em formato amigável `XXh YYm` e horas decimais).
   - Meta prevista acumulada.
   - **Saldo do Banco de Horas** com destaque visual imediato:
     - 🟢 **Verde** para saldo positivo (Horas Extras / Crédito).
     - 🔴 **Vermelho** para saldo negativo (Horas Devidas / Débito).
     - ⚖️ **Azul** para saldo equilibrado.

4. **📋 Histórico e Lançamento / Edição Manual:**
   - Tabela mensal com destaques de saldo diário e saldo acumulado.
   - Formulário completo para lançamento retroativo ou ajuste manual de horários (caso esqueça de bater o ponto ou precise retificar uma marcação).
   - Opção para excluir registros incorretos com confirmação.

5. **📈 Visualização Gráfica Interativa (Plotly):**
   - Gráfico de barras de **Saldo Diário** com coloração verde/vermelha automática.
   - Gráfico de linha de **Evolução Acumulada** do Banco de Horas ao longo dos dias do mês.
   - Gráfico comparativo de **Horas Realizadas vs. Meta Diária**.

6. **👔 Visão da Chefia / Supervisão (Painel Executivo Integrado):**
   - Alternador no topo da barra lateral para trocar entre o perfil do estagiário e a visão da chefia.
   - **Resumo Contratual:** Dados do Estagiário, Supervisor Responsável, Empresa/Setor e Carga Horária.
   - **Status em Tempo Real:** Mostra instantaneamente se o estagiário está trabalhando agora, em intervalo ou se já finalizou o dia.
   - **KPIs Consolidados:** Assiduidade (presenças vs dias úteis do mês), total de horas realizadas vs meta mensal, saldo acumulado e média diária cumprida.
   - **Auditoria & Conformidade (Lei 11.788/2008):** Varredura automática alertando sobre saídas não batidas em dias passados ou jornadas que excederam o limite legal de 6h.
   - **Emissão da Folha de Ponto Oficial:** Relatório formatado em HTML para impressão em folha A4 / salvamento em PDF com termos de declaração e linhas de assinatura do estagiário e supervisor.

7. **💾 Persistência de Dados & Exportação:**
   - Armazenamento local automático em `ponto_eletronico.json`.
   - Download de relatórios em **CSV compatível com Excel** (UTF-8 com BOM).
   - Backup e restauração completa em JSON.

---

## 📂 Estrutura Modular do Projeto

```text
ponto_estagio/
├── app.py              # Interface principal Streamlit (sidebar, abas, fluxo)
├── calculations.py     # Regras de negócio, cálculo de jornada e saldos
├── components.py       # Indicadores visuais, gráficos Plotly e cards
├── storage.py          # Persistência JSON e exportação CSV
├── test_app.py         # Testes automatizados unitários
├── requirements.txt    # Dependências do projeto
└── ponto_eletronico.json # Base de dados local com registros e configurações
```

---

## 🛠️ Como Executar a Aplicação

### 1. Pré-requisitos
Certifique-se de ter o Python 3.10+ instalado no seu sistema.

### 2. Instalação das dependências
No terminal, execute:
```bash
python -m pip install -r requirements.txt
```

### 3. Iniciar a Aplicação
Execute o comando:
```bash
python -m streamlit run app.py
```

O Streamlit abrirá automaticamente no seu navegador no endereço:
`http://localhost:8501`

---

## ⚖️ Conformidade com a Lei do Estágio (Lei 11.788/2008)
- **Art. 10:** A jornada de atividade em estágio será definida de comum acordo entre a instituição de ensino, a parte concedente e o estagiário, não podendo ultrapassar **6 (seis) horas diárias e 30 (trinta) horas semanais** (no caso de estudantes do ensino superior e técnico).
- Este sistema foi projetado especificamente para que o estagiário tenha clareza absoluta sobre suas horas cumpridas e possa compensar minutos excedentes ou devidos sem ultrapassar os limites legais.
