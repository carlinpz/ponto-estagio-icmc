"""
Autenticação do Ponto Eletrônico (independente do Streamlit, para ser testável e reaproveitável).

- Senhas nunca ficam no código: em st.secrets fica só o HASH (PBKDF2-SHA256 com salt aleatório).
- "Lembrar login" usa um token assinado (HMAC) com prazo de validade, guardado só em cookie.
"""

import hashlib
import hmac
import secrets
import time
from typing import Optional

PBKDF2_ITERACOES = 600_000
PERFIS_VALIDOS = ("estagiario", "gestao")


def gerar_hash_senha(senha: str, iteracoes: int = PBKDF2_ITERACOES) -> str:
    """Gera o hash de uma senha no formato 'pbkdf2_sha256$iteracoes$salt$hash' (para colar em secrets)."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(salt), iteracoes)
    return f"pbkdf2_sha256${iteracoes}${salt}${dk.hex()}"


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    """Confere a senha digitada contra o hash salvo em secrets. Hash ausente ou inválido nunca autentica."""
    try:
        algoritmo, iteracoes, salt, esperado = str(hash_armazenado).strip().split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(salt), int(iteracoes))
        return hmac.compare_digest(dk.hex(), esperado)
    except (ValueError, TypeError):
        return False


def _assinar(mensagem: str, segredo: str) -> str:
    return hmac.new(segredo.encode("utf-8"), mensagem.encode("utf-8"), hashlib.sha256).hexdigest()


def gerar_token_login(perfil: str, segredo: str, dias: int = 30, agora: Optional[float] = None) -> str:
    """Cria o token 'perfil.expiracao.assinatura' usado no cookie de login lembrado."""
    if perfil not in PERFIS_VALIDOS:
        raise ValueError(f"Perfil inválido: {perfil}")
    if not segredo:
        raise ValueError("cookie_secret não configurado")
    expira = int((agora if agora is not None else time.time()) + dias * 24 * 3600)
    mensagem = f"{perfil}.{expira}"
    return f"{mensagem}.{_assinar(mensagem, segredo)}"


def validar_token_login(token: Optional[str], segredo: str, agora: Optional[float] = None) -> Optional[str]:
    """Retorna o perfil do token se a assinatura confere e o prazo não venceu; senão None."""
    if not token or not segredo:
        return None
    try:
        perfil, expira, assinatura = str(token).split(".")
        expira_int = int(expira)
    except ValueError:
        return None
    if perfil not in PERFIS_VALIDOS:
        return None
    # Compara bytes: com str, compare_digest lança TypeError se o cookie tiver caractere não ASCII
    esperada = _assinar(f"{perfil}.{expira}", segredo)
    if not hmac.compare_digest(assinatura.encode("utf-8"), esperada.encode("utf-8")):
        return None
    if expira_int < (agora if agora is not None else time.time()):
        return None
    return perfil
