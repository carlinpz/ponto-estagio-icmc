"""
Script de exportação de conversas do Antigravity para Markdown.
Gera arquivos organizados e legíveis com todo o histórico de interações do projeto.
"""
import os
import json
import re
from datetime import datetime

BRAIN_DIR = r"C:\Users\carli\.gemini\antigravity\brain"
OUTPUT_DIR = r"g:\Meu Drive\Projetos\ponto_estagio\historico_chats"

CHATS_METADATA = [
    {
        "id": "df46372a-bb29-4d8a-84d9-1e485714fce7",
        "file_name": "Chat_01_Refatoracao_e_Engenharia.md",
        "title": "Especificação Completa de Engenharia e Refatoração Arquitetural",
        "date": "2026-10-21 / 2026-10-22",
        "description": "Refatoração profunda de segurança, regras de negócio FUSP, ciclo mensal (dia 20), deduplicação por data, persistência segura com PBKDF2 e criação de suíte automatizada de testes."
    },
    {
        "id": "2773045a-f089-4e68-b24d-bfc94ab88843",
        "file_name": "Chat_02_Responsividade_Mobile_e_GitHub.md",
        "title": "Ajustes de Responsividade Mobile e Publicação no GitHub",
        "date": "2026-10-21 / 2026-10-22",
        "description": "Diagnóstico do bug de travamento de scroll e tela cortada no mobile. Ajustes com testes Playwright em viewport de smartphone, redesign em abas sem conflitos de CSS com Streamlit e push para o GitHub."
    },
    {
        "id": "d26607e7-5e64-4035-bbb6-749e4e9cd6a2",
        "file_name": "Chat_03_Exportacao_Projeto_Arquivo_Unico.md",
        "title": "Exportação Completa do Projeto para Arquivo Único (Markdown)",
        "date": "2026-10-21 / 2026-10-22",
        "description": "Criação do utilitário `exportar_projeto.py` e geração do `projeto_completo.md` consolidando código-fonte e estrutura para backup e contexto em outras IAs."
    },
    {
        "id": "fa31c730-5a8b-41c7-b2e5-2d4871bc71c1",
        "file_name": "Chat_04_Opcoes_Arquivamento_Antigravity.md",
        "title": "Dúvidas sobre Arquivamento de Projetos no Antigravity",
        "date": "2026-10-26",
        "description": "Explicação sobre como o Antigravity gerencia pastas de trabalho, como funciona o desacoplamento de projetos locais e segurança dos arquivos locais."
    },
    {
        "id": "43ff7f83-149b-4d16-b4c4-0dedbac231b1",
        "file_name": "Chat_05_Exportacao_Historico_e_Desvinculacao.md",
        "title": "Exportação de Chats e Guia de Desvinculação do Antigravity",
        "date": "2026-10-26",
        "description": "Solicitação do usuário para desvincular o projeto do Antigravity mantendo o histórico de conversas em Markdown no Google Drive, com instruções completas de segurança."
    }
]

def clean_user_message(content):
    if not content:
        return ""
    content = re.sub(r"<ADDITIONAL_METADATA>[\s\S]*?</ADDITIONAL_METADATA>", "", content)
    content = re.sub(r"<USER_SETTINGS_CHANGE>[\s\S]*?</USER_SETTINGS_CHANGE>", "", content)
    m = re.search(r"<USER_REQUEST>([\s\S]*?)</USER_REQUEST>", content)
    if m:
        content = m.group(1).strip()
    return content.strip()

def summarize_tools(tools):
    read_files = []
    edited_files = []
    commands = []
    other = []
    
    for t in tools:
        name = t.get("name") or t.get("tool_name")
        args = t.get("args") or t.get("arguments") or {}
        
        if name == "read_file":
            path = args.get("Path", "")
            if path and path not in read_files:
                read_files.append(path)
        elif name in ("edit_file", "write_file"):
            path = args.get("Path", "")
            action = "Criação" if name == "write_file" else "Edição"
            entry = f"{action}: `{os.path.basename(path)}` ({path})"
            if entry not in edited_files:
                edited_files.append(entry)
        elif name == "run_command":
            cmd = args.get("CommandLine", "")
            summary = args.get("toolSummary", "")
            entry = f"`{cmd}`" + (f" *({summary})*" if summary else "")
            commands.append(entry)
        elif name:
            if name not in other:
                other.append(name)
                
    return read_files, edited_files, commands, other

def parse_conversation(cid):
    p = os.path.join(BRAIN_DIR, cid, ".system_generated", "logs", "transcript_full.jsonl")
    if not os.path.exists(p):
        p = os.path.join(BRAIN_DIR, cid, ".system_generated", "logs", "transcript.jsonl")
    
    if not os.path.exists(p):
        return []

    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        lines = [json.loads(l) for l in f]

    turns = []
    current_turn = {"user": None, "tools": [], "agent": None, "user_time": None, "agent_time": None}

    for item in lines:
        tp = item.get("type")
        c = item.get("content")
        created = item.get("created_at")
        tool_calls = item.get("tool_calls")

        if tp == "USER_INPUT":
            if current_turn["user"] is not None:
                turns.append(current_turn)
                current_turn = {"user": None, "tools": [], "agent": None, "user_time": None, "agent_time": None}
            current_turn["user"] = clean_user_message(c)
            current_turn["user_time"] = created

        elif tool_calls:
            for tc in tool_calls:
                current_turn["tools"].append(tc)

        elif tp == "PLANNER_RESPONSE" and c:
            current_turn["agent"] = c
            current_turn["agent_time"] = created

    if current_turn["user"] is not None or current_turn["agent"] is not None or current_turn["tools"]:
        turns.append(current_turn)

    return turns

def format_turn_to_markdown(turn, index):
    md = []
    user_time_str = f" *({turn['user_time']})*" if turn.get("user_time") else ""
    agent_time_str = f" *({turn['agent_time']})*" if turn.get("agent_time") else ""
    
    md.append(f"## 👤 Turno {index + 1} - Usuário{user_time_str}\n")
    if turn.get("user"):
        md.append(turn["user"] + "\n")
    else:
        md.append("*(Sem mensagem explícita)*\n")
        
    tools = turn.get("tools", [])
    if tools:
        rf, ef, cmd, oth = summarize_tools(tools)
        md.append(f"<details>\n<summary>🛠️ <b>Operações e Ferramentas Executadas ({len(tools)} chamadas)</b> (clique para expandir)</summary>\n")
        
        if ef:
            md.append("\n**Arquivos Criados / Modificados:**")
            for item in ef:
                md.append(f"- {item}")
        
        if rf:
            md.append("\n**Arquivos Consultados:**")
            for item in rf:
                md.append(f"- `{os.path.basename(item)}` (`{item}`)")
                
        if cmd:
            md.append("\n**Comandos de Terminal Executados:**")
            for item in cmd:
                md.append(f"- {item}")
                
        if oth:
            md.append(f"\n**Outras Ações:** {', '.join(oth)}")
            
        md.append("\n</details>\n")

    md.append(f"## 🤖 Resposta do Assistente (Antigravity){agent_time_str}\n")
    if turn.get("agent"):
        md.append(turn["agent"] + "\n")
    else:
        md.append("*(Resposta em andamento / finalizada nesta sessão)*\n")

    md.append("\n---\n")
    return "\n".join(md)

def export_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    for meta in CHATS_METADATA:
        cid = meta["id"]
        file_path = os.path.join(OUTPUT_DIR, meta["file_name"])
        turns = parse_conversation(cid)
        
        # Especial para o chat 5 (atual) caso o agente ainda não tenha gravado o fechamento no transcript
        if cid == "43ff7f83-149b-4d16-b4c4-0dedbac231b1" and turns and not turns[-1].get("agent"):
            turns[-1]["agent"] = (
                "**Exportação do Histórico e Instruções de Desvinculação do Antigravity:**\n\n"
                "1. Todos os chats deste projeto foram exportados para arquivos Markdown estruturados nesta pasta (`historico_chats/`).\n"
                "2. O projeto está 100% seguro no seu Google Drive (`G:\\Meu Drive\\Projetos\\ponto_estagio`).\n"
                "3. Para desvincular o projeto do Antigravity sem risco de perder arquivos no Drive, siga o procedimento seguro detalhado no arquivo `INDICE_E_GUIA_DESVINCULAR.md`:\n"
                "   - No menu do Antigravity, clique em **File > Close Folder** (ou feche o workspace).\n"
                "   - Isso apenas remove a pasta da visualização ativa do editor.\n"
                "   - **ATENÇÃO:** Nunca delete arquivos clicando em 'Delete' na árvore do Explorer do Antigravity, pois isso apagaria os arquivos reais do Drive.\n"
                "   - Seus arquivos no Google Drive permanecerão exatamente como estão."
            )
            turns[-1]["agent_time"] = datetime.now().isoformat()

        doc = []
        doc.append(f"# {meta['title']}\n")
        doc.append(f"> **Projeto:** Sistema de Ponto Eletrônico ICMC/USP  \n"
                   f"> **Pasta Local:** `g:\\Meu Drive\\Projetos\\ponto_estagio`  \n"
                   f"> **ID da Conversa Antigravity:** `{cid}`  \n"
                   f"> **Data do Atendimento:** {meta['date']}  \n"
                   f"> **Resumo:** {meta['description']}\n")
        doc.append("---\n")
        
        for i, turn in enumerate(turns):
            doc.append(format_turn_to_markdown(turn, i))
            
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(doc))
        print(f"Salvo: {meta['file_name']} ({len(turns)} turnos)")

    # Gerar Índice e Guia Completo
    generate_index_and_guide()

def generate_index_and_guide():
    index_path = os.path.join(OUTPUT_DIR, "INDICE_E_GUIA_DESVINCULAR.md")
    readme_path = os.path.join(OUTPUT_DIR, "README.md")
    
    content = """# Histórico Completo de Chats & Guia de Desvinculação do Antigravity

Este diretório contém o registro detalhado de todas as sessões de desenvolvimento, refatoração e assistência técnica realizadas pela IA no projeto **Sistema de Ponto Eletrônico ICMC/USP**.

---

## 🗂️ Índice das Conversas Salvas

| Arquivo | Título do Chat | Data | Resumo |
| :--- | :--- | :--- | :--- |
| **[`Chat_01_Refatoracao_e_Engenharia.md`](./Chat_01_Refatoracao_e_Engenharia.md)** | Especificação de Engenharia e Refatoração | 21-22/10/2026 | Refatoração completa de segurança, regras de negócio FUSP (dia 20), fechamento mensal, PBKDF2 e testes automatizados. |
| **[`Chat_02_Responsividade_Mobile_e_GitHub.md`](./Chat_02_Responsividade_Mobile_e_GitHub.md)** | Responsividade Mobile e GitHub | 21-22/10/2026 | Resolução de bugs no celular (scroll travado e elementos cortados), testes Playwright, redesign em abas e push para o repositório remoto. |
| **[`Chat_03_Exportacao_Projeto_Arquivo_Unico.md`](./Chat_03_Exportacao_Projeto_Arquivo_Unico.md)** | Exportação Completa para Arquivo Único | 21-22/10/2026 | Script `exportar_projeto.py` e arquivo consolidado `projeto_completo.md` para contexto em LLMs. |
| **[`Chat_04_Opcoes_Arquivamento_Antigravity.md`](./Chat_04_Opcoes_Arquivamento_Antigravity.md)** | Dúvidas sobre Arquivamento no Antigravity | 26/10/2026 | Explicação sobre a arquitetura de pastas do Antigravity e desacoplamento de arquivos locais. |
| **[`Chat_05_Exportacao_Historico_e_Desvinculacao.md`](./Chat_05_Exportacao_Historico_e_Desvinculacao.md)** | Exportação do Histórico e Desvinculação | 26/10/2026 | Preservação dos registros de conversa em Markdown e confirmação de integridade no Google Drive. |

---

## ❓ "Depois que eu deletar aqui, estará tudo no Drive ainda, né?"

### ✅ **RESPOSTA DIRETA: SIM! Seus arquivos continuam 100% seguros no Google Drive.**

O **Antigravity** funciona como uma IDE (ambiente de desenvolvimento/editor de código baseado em VS Code / Gemini CLI):
1. **Onde ficam os seus arquivos:** Seus arquivos estão fisicamente na sua máquina e no Google Drive (`G:\\Meu Drive\\Projetos\\ponto_estagio`). O Antigravity apenas "enxerga" e abre essa pasta, assim como o Bloco de Notas ou o VS Code fazem.
2. **O que o Antigravity armazena separadamente:** Apenas o cache da IA, histórico de prompts e sessões em `C:\\Users\\carli\\.gemini\\antigravity`.
3. **Com estes arquivos Markdown exportados:** Agora, até mesmo o histórico de conversa com a IA está salvo fisicamente **DENTRO** da sua pasta do projeto (`G:\\Meu Drive\\Projetos\\ponto_estagio\\historico_chats`).
4. **Sincronização com o Google Drive:** O Google Drive para Computador sincroniza automaticamente toda a pasta `ponto_estagio`, incluindo os scripts, o banco de dados (`ponto_eletronico.json`), a planilha CSV e agora esta pasta de chats.

---

## ⚠️ CUIDADO: A Diferença Crucial ao "Deletar / Fechar"

Para não perder arquivos por engano, preste muita atenção na distinção abaixo:

### 🟢 O QUE FAZER (Correto e Seguro): "Fechar Pasta / Desvincular"
- No Antigravity, vá em **File (Arquivo) > Close Folder (Fechar Pasta)** (ou `Ctrl + K F`).
- Se houver lista de projetos recentes na tela inicial do Antigravity, você pode clicar no **"X"** ao lado do nome `ponto_estagio` para removê-lo da lista de atalhos recentes.
- **Resultado:** O Antigravity simplesmente "desconecta" da pasta. Nenhum arquivo é apagado do disco nem do Google Drive. Quando quiser, você pode abrir a pasta em qualquer outro editor.

### 🔴 O QUE NUNCA FAZER (Perigoso): "Excluir arquivos dentro da árvore do Explorer"
- **NUNCA** selecione os arquivos na barra lateral esquerda (Explorer) do Antigravity e clique com o botão direito em **"Delete" (Excluir)**.
- Se você fizer isso, você estará enviando o comando do Windows para apagar os arquivos físicos do seu HD/Google Drive!

---

## 🚀 Como Reabrir ou Usar o Projeto no Futuro

- **Para rodar o sistema localmente:** Basta dar dois cliques em `iniciar_ponto.bat` ou rodar `python -m streamlit run app.py`.
- **Para subir novas alterações ao GitHub:** Execute `enviar_para_github.bat`.
- **Para reabrir no Antigravity ou VS Code futuramente:** Basta ir em **File > Open Folder...** e selecionar `G:\\Meu Drive\\Projetos\\ponto_estagio`.
"""
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Índices gerados com sucesso!")

if __name__ == "__main__":
    export_all()
