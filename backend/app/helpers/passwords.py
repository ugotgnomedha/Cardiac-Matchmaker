from pwdlib import PasswordHash


def password_hash(password: str) -> str:
    ph = PasswordHash.recommended()
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    ph = PasswordHash.recommended()
    return ph.verify(password, password_hash)
