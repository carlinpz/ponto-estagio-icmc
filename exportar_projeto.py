#!/usr/bin/env python3
"""
Script para exportar todo o código e estrutura do projeto para um único arquivo Markdown.
Ideal para carregar contexto completo em modelos de Inteligência Artificial (ChatGPT, Claude, Gemini, etc.).
"""

import os
import re

OUTPUT_FILE = "projeto_completo.md"

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    ".idea",
    ".vscode",
}

IGNORE_FILES = {
    OUTPUT_FILE,
    "exportar_projeto.py",
}

BINARY_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".ico",
    ".exe",
    ".bin",
    ".pyc",
    ".zip",
    ".tar",
    ".gz",
    ".db",
    ".sqlite",
    ".sqlite3",
}

LANGUAGE_MAP = {
    ".py": "python",
    ".pyw": "python",
    ".json": "json",
    ".toml": "toml",
    ".bat": "bat",
    ".cmd": "bat",
    ".csv": "csv",
    ".html": "html",
    ".tex": "latex",
    ".md": "markdown",
    ".txt": "text",
    ".sh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def is_binary(filepath):
    _, ext = os.path.splitext(filepath)
    if ext.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(1024)
            if b"\0" in chunk:
                return True
        return False
    except Exception:
        return True


def get_fence(content):
    ticks = re.findall(r"`+", content)
    if ticks:
        max_len = max(len(t) for t in ticks)
        return "`" * max(3, max_len + 1)
    return "```"


def export_project(root_dir=".", output_path=OUTPUT_FILE):
    collected_files = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Filtrar diretórios ignorados
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        for f in filenames:
            if f in IGNORE_FILES:
                continue
            full_path = os.path.join(dirpath, f)
            rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")
            try:
                size = os.path.getsize(full_path)
            except Exception:
                size = 0
            is_bin = is_binary(full_path)
            collected_files.append((rel_path, full_path, size, is_bin))

    # Ordenar por caminho relativo
    collected_files.sort(key=lambda x: x[0])

    lines = []
    lines.append("# Projeto: Ponto de Estágio - Exportação Completa")
    lines.append("")
    lines.append("> Este arquivo consolida a estrutura de arquivos e o código-fonte de todos os arquivos de texto do projeto para análise e contexto de modelos de IA.")
    lines.append("")
    lines.append("## Estrutura de Arquivos")
    lines.append("")

    for rel_path, _, size, is_bin in collected_files:
        binary_flag = " *(binário)*" if is_bin else ""
        lines.append(f"- `{rel_path}` ({size:,} bytes){binary_flag}")

    lines.append("")
    lines.append("---")
    lines.append("")

    for rel_path, full_path, size, is_bin in collected_files:
        lines.append(f"## Arquivo: `{rel_path}`")
        lines.append("")

        if is_bin:
            lines.append(f"*Arquivo binário não incluído em texto (tamanho: {size:,} bytes).*")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        _, ext = os.path.splitext(rel_path)
        lang = "gitignore" if os.path.basename(rel_path) == ".gitignore" else LANGUAGE_MAP.get(ext.lower(), "")

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            content = f"Erro ao ler arquivo: {e}"

        fence = get_fence(content)
        lines.append(f"{fence}{lang}")
        lines.append(content)
        lines.append(fence)
        lines.append("")
        lines.append("---")
        lines.append("")

    final_content = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_content)

    print(f"Exportação concluída com sucesso em: {output_path}")
    print(f"Total de arquivos incluídos: {len(collected_files)}")
    print(f"Tamanho do arquivo final: {os.path.getsize(output_path):,} bytes")


if __name__ == "__main__":
    export_project()
