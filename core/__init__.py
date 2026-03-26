"""Logica business - validazione, servizi, calcoli DPS."""
from core.validation import parse_number, parse_stat_value, validate_nome
from core.services import AppService
from core.dps import DpsCalculator
from core.dps_types import (
    CombatStats,
    DpsResult,
    DPS_MODEL_VERSION,
    FullCombatBuild,
    build_full_combat_view,
    merge_combat_stats,
)

__all__ = [
    "parse_number",
    "parse_stat_value",
    "validate_nome",
    "AppService",
    "DpsCalculator",
    "CombatStats",
    "DpsResult",
    "DPS_MODEL_VERSION",
    "FullCombatBuild",
    "build_full_combat_view",
    "merge_combat_stats",
]
