"""Modelli dati - strutture tipizzate per calcoli e validazione."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Personaggio:
    """Dati personaggio - immutabile per calcoli."""
    id: int
    nome: str
    livello: int
    elemento: str
    hp_flat: Optional[int]
    atk_flat: Optional[int]
    def_flat: Optional[int]
    em_flat: Optional[int]
    cr: Optional[int]
    cd: Optional[int]
    er: Optional[int]

    @classmethod
    def from_row(cls, row: tuple) -> "Personaggio":
        return cls(
            id=row[0], nome=row[1] or "", livello=row[2] or 1, elemento=row[3] or "Pyro",
            hp_flat=row[4], atk_flat=row[5], def_flat=row[6], em_flat=row[7],
            cr=row[8], cd=row[9], er=row[10]
        )


@dataclass(frozen=True)
class Arma:
    id: int
    personaggio_id: int
    nome: str
    tipo: str
    livello: int
    stelle: int
    atk_base: Optional[int]
    stat_secondaria: Optional[str]
    valore_stat: Optional[float]

    @classmethod
    def from_row(cls, row: tuple) -> "Arma":
        return cls(
            id=row[0], personaggio_id=row[1], nome=row[2] or "",
            tipo=row[3] or "Spada", livello=row[4] or 1, stelle=row[5] or 5,
            atk_base=row[6], stat_secondaria=row[7], valore_stat=row[8]
        )


@dataclass(frozen=True)
class Artefatto:
    """Dati artefatto - per calcoli DPS."""
    id: int
    slot: str
    set_nome: Optional[str]
    nome: Optional[str]
    livello: int
    stelle: int
    main_stat: Optional[str]
    main_val: Optional[float]
    sub1_stat: Optional[str]
    sub1_val: Optional[float]
    sub2_stat: Optional[str]
    sub2_val: Optional[float]
    sub3_stat: Optional[str]
    sub3_val: Optional[float]
    sub4_stat: Optional[str]
    sub4_val: Optional[float]

    @classmethod
    def from_dict(cls, d: dict) -> "Artefatto":
        return cls(
            id=d["id"], slot=d["slot"], set_nome=d.get("set_nome"), nome=d.get("nome"),
            livello=d.get("livello") or 20, stelle=d.get("stelle") or 5,
            main_stat=d.get("main_stat"), main_val=d.get("main_val"),
            sub1_stat=d.get("sub1_stat"), sub1_val=d.get("sub1_val"),
            sub2_stat=d.get("sub2_stat"), sub2_val=d.get("sub2_val"),
            sub3_stat=d.get("sub3_stat"), sub3_val=d.get("sub3_val"),
            sub4_stat=d.get("sub4_stat"), sub4_val=d.get("sub4_val")
        )


@dataclass(frozen=True)
class Costellazioni:
    c1: int
    c2: int
    c3: int
    c4: int
    c5: int
    c6: int

    @classmethod
    def from_row(cls, row: tuple) -> "Costellazioni":
        r = row or (0, 0, 0, 0, 0, 0)
        return cls(*(r[i] or 0 for i in range(6)))


@dataclass(frozen=True)
class Talenti:
    """Livelli talento: None = non usato (- in UI), 0–10 = valore salvato."""
    aa: Optional[int]
    skill: Optional[int]
    burst: Optional[int]
    pas1: Optional[int]
    pas2: Optional[int]
    pas3: Optional[int]
    pas4: Optional[int]

    @classmethod
    def from_row(cls, row: tuple) -> "Talenti":
        if not row:
            return cls(None, None, None, None, None, None, None)
        r = list(row)
        while len(r) < 7:
            r.append(None)
        return cls(
            aa=r[0], skill=r[1], burst=r[2], pas1=r[3], pas2=r[4], pas3=r[5], pas4=r[6]
        )


