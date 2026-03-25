"""Validazione input - funzioni piccole e specifiche."""
from typing import Optional, Tuple


def parse_number(val, default=None, min_val=None, max_val=None) -> Optional[float]:
    """Converte stringa in numero. Ritorna default se invalido."""
    if val is None or val == "" or val == "-":
        return default
    s = str(val).strip().replace("%", "").replace(",", ".")
    if not s:
        return default
    try:
        n = float(s)
        if n == int(n):
            n = int(n)
    except (ValueError, TypeError):
        return default
    if min_val is not None and n < min_val:
        return default
    if max_val is not None and n > max_val:
        return default
    return n


def parse_stat_value(val) -> Optional[float]:
    """Parsa valore stat (CR, CD, ATK, ecc.)."""
    return parse_number(val, min_val=0, max_val=10000)


def validate_nome(nome: str) -> Tuple[bool, str]:
    """Valida nome personaggio. Ritorna (ok, messaggio_errore)."""
    nome = (nome or "").strip()
    if not nome:
        return False, "Il nome è obbligatorio."
    if len(nome) < 2:
        return False, "Il nome deve avere almeno 2 caratteri."
    return True, ""
