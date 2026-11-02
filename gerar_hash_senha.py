"""
Gera o hash de uma senha para colar no secrets.toml (local) ou no painel Secrets do Streamlit Cloud.

Uso:  python gerar_hash_senha.py
A senha é digitada sem aparecer na tela e nunca é gravada em lugar nenhum.
"""

import getpass

from auth import gerar_hash_senha

if __name__ == "__main__":
    senha = getpass.getpass("Nova senha: ")
    if not senha.strip():
        raise SystemExit("A senha não pode ficar em branco.")
    if senha != getpass.getpass("Repita a senha: "):
        raise SystemExit("As senhas não coincidem.")
    print("\nCole a linha abaixo no secrets (troque CHAVE por senha_estagiario_hash ou senha_chefia_hash):\n")
    print(f'CHAVE = "{gerar_hash_senha(senha)}"')
