"""Logica business - validazione, servizi, calcoli DPS."""
from core.validation import parse_number, parse_stat_value, validate_nome
from core.services import AppService
from core.dps import DpsCalculator

__all__ = ["parse_number", "parse_stat_value", "validate_nome", "AppService", "DpsCalculator"]
