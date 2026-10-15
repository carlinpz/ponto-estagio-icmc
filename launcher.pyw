"""
Script inicializador silencioso para o Ponto Eletrônico de Estágio.
Verifica se o servidor Streamlit já está ativo:
- Se estiver ativo, abre imediatamente a interface no navegador padrão.
- Se não estiver ativo, inicia o Streamlit em segundo plano (sem janela de terminal)
  e abre o navegador assim que o servidor estiver pronto.
"""

import os
import sys
import time
import urllib.request
import webbrowser
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_URL = "http://localhost:8501/?acesso=estagiario"
BASE_CHECK_URL = "http://localhost:8501"
PYTHON_EXE = os.path.join(os.path.dirname(sys.executable), "python.exe")
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = "python"


def is_server_running() -> bool:
    """Verifica se o servidor Streamlit responde na porta 8501."""
    try:
        req = urllib.request.Request(
            APP_URL,
            headers={"User-Agent": "PontoLauncher/1.0"}
        )
        with urllib.request.urlopen(req, timeout=1.2) as response:
            return response.status == 200
    except Exception:
        return False


def start_server():
    """Inicia o servidor Streamlit em segundo plano sem janela de prompt."""
    creationflags = 0
    if os.name == "nt":
        # 0x08000000 = CREATE_NO_WINDOW
        creationflags = 0x08000000

    cmd = [
        PYTHON_EXE,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.headless",
        "true",
        "--server.port",
        "8501",
    ]

    subprocess.Popen(
        cmd,
        cwd=PROJECT_DIR,
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )


def main():
    if not is_server_running():
        start_server()
        # Aguarda o servidor inicializar (até 15 segundos)
        for _ in range(30):
            time.sleep(0.5)
            if is_server_running():
                break

    # Abre a página no navegador padrão
    webbrowser.open(APP_URL)


if __name__ == "__main__":
    main()
