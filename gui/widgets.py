"""Widget riutilizzabili."""
import tkinter as tk
from tkinter import ttk

from config import ELEMENTI, TIPI_ARMA, STATS, SET_ARTEFATTI, SLOT_DB


class AutocompleteCombobox(ttk.Combobox):
    """Combobox con filtraggio mentre digiti."""

    def __init__(self, parent, values=None, width=12, **kwargs):
        self._values = list(values or [])
        super().__init__(parent, values=self._values, width=width, **kwargs)
        self.bind("<KeyRelease>", self._on_key)

    def _on_key(self, event):
        if event.keysym in ("Down", "Up", "Return", "Tab"):
            return
        val = self.get().strip()
        if not val:
            self["values"] = self._values
            return
        val_lower = val.lower()
        filtered = [v for v in self._values if val_lower in str(v).lower()]
        self["values"] = filtered if filtered else self._values


def create_entry(parent, label: str, width: int = 10) -> tk.Entry:
    """Crea Frame con Label + Entry."""
    f = tk.Frame(parent)
    f.pack(side="left", padx=10)
    tk.Label(f, text=label).pack(side="left")
    e = tk.Entry(f, width=width)
    e.pack(side="left", padx=5)
    return e


def create_stat_combobox(parent, label: str, var: tk.StringVar, width: int = 12):
    """Crea combobox per stat con autocomplete."""
    f = tk.Frame(parent)
    f.pack(side="left", padx=10)
    tk.Label(f, text=label).pack(side="left")
    return AutocompleteCombobox(f, values=STATS, width=width, textvariable=var)
