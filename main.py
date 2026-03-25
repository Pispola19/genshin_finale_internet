"""Punto di ingresso - avvia l'applicazione."""
import sys

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from gui.app import GenshinApp


def main():
    try:
        app = GenshinApp()
        app.run()
    except Exception as e:
        from tkinter import messagebox
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Errore avvio", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
