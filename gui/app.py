"""
Applicazione principale - assembla e avvia GUI.
Solo gestione eventi e visualizzazione. Logica e dati nel service layer.
"""
import logging
import math
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox

from config import (
    PROJECT_ROOT,
    SLOT_UI,
    SLOT_DB,
    ELEMENTI,
    TIPI_ARMA,
    STATS,
    SET_ARTEFATTI,
)
from gui.form_checkpoint import (
    load_and_apply_gui_checkpoint,
    mark_gui_checkpoint_dirty,
    save_gui_checkpoint_safe,
)
from gui.safe_ops import gui_safe_call, notify_unexpected
from core.nome_normalization import canonicalizza_nome_arma, canonicalizza_nome_personaggio
from core.services import AppService
from core.dps_types import DpsResult
from gui.widgets import AutocompleteCombobox, create_entry

logger = logging.getLogger(__name__)


def _gui_format_num_g(val) -> str:
    """Numero sicuro per etichette (Treeview / DPS): niente NaN, niente crash."""
    try:
        x = float(val)
        if math.isnan(x) or math.isinf(x):
            return "—"
        return f"{x:g}"
    except (TypeError, ValueError):
        return "—"


def _gui_tree_row_values(row, expected_len: int) -> tuple:
    """Righe repository → tuple di stringhe della lunghezza attesa (anti-TclError Treeview)."""
    cells = list(row) if row is not None else []
    while len(cells) < expected_len:
        cells.append("")
    cells = cells[:expected_len]
    return tuple("" if c is None else str(c) for c in cells)


def _dps_ranking_fattori_cell(f: object) -> str:
    """Testo compatto colonna moltiplicatori (ranking DPS GUI)."""
    if not isinstance(f, dict):
        return "—"
    parts = []
    if "elemento" in f:
        parts.append(f"el×{_gui_format_num_g(f.get('elemento'))}")
    if "em" in f:
        parts.append(f"EM×{_gui_format_num_g(f.get('em'))}")
    if "crit_adjust" in f:
        parts.append(f"CR×{_gui_format_num_g(f.get('crit_adjust'))}")
    return " ".join(parts) if parts else "—"


QUESTIONARIO_DOCX = PROJECT_ROOT / "web" / "questionario_genshin_avanzato.docx"
QUESTIONARIO_EMAIL = "shokran@hotmail.it"

_TALENTI_LABELS = (
    "Attacco (AA)",
    "Abilità (E)",
    "Tripudio (Q)",
    "Extra 1 (non nel calcolo DPS)",
    "Extra 2 (non nel calcolo DPS)",
    "Extra 3 (non nel calcolo DPS)",
    "Extra 4 (non nel calcolo DPS)",
)

_ISTRUZIONI_BAMBINI = """Ciao! Questo programma è un quaderno per annotare personaggi, armi e artefatti di Genshin Impact, come nel gioco.

PASSO 1 — Personaggio
• Cerca o scrivi il nome dell’eroe.
• Livello: da 1 a 90 (come nel profilo).
• Elemento: usa i nomi originali del gioco, ad esempio Pyro, Hydro, Electro, Cryo, Anemo, Geo, Dendro (non servono traduzioni in italiano).

PASSO 2 — Statistiche (HP, ATK, DEF, EM, CR, CD, ER)
Sono le stesse voci che vedi sulla scheda personaggio in gioco o su schermate tipo battaglia / attributi. Compila i numeri che vuoi tenere sotto controllo per la tua build.

Inserimento manuale (consigliato)
• Compila scheda personaggio, arma e manufatti a mano. «Dashboard» apre il sito web del programma (in locale avvia prima il server o imposta l’indirizzo con le variabili d’ambiente).
• Su Mac il menu «Dati» sta nella barra in alto dello schermo (vicino al nome dell’app), non sulla finestra.

PASSO 3 — Arma
Nome, tipo (Spada, Claymore, ecc.), livello, stelle, stat secondaria e valore: come nell’inventario arma nel gioco.

PASSO 4 — Artefatti equipaggiati
Per ogni slot (Fiore, Piuma, …) puoi scegliere un artefatto dall’inventario dopo aver salvato/selezionato il personaggio. Prima devi aver registrato gli artefatti da “Inventario artefatti”.

PASSO 5 — Costellazioni C1 … C6
Per ogni costellazione puoi impostare solo:
  • 0 = non attiva (non ce l’hai ancora sbloccata per quel numero)
  • 1 = attiva (l’hai sbloccata)
Non ci sono altri valori: è come un elenco di sì/no per ogni C.

PASSO 6 — Talenti (7 casette, tutte nella stessa schermata)
• Il segno meno “-” in una casella = valore vuoto / non compilato (equivalente a lasciare il campo da ignorare).
• 0 = talento presente ma a livello zero / non potenziato in quel senso.
• Da 1 a 10 = livello del talento come nel gioco.

Le prime tre righe sono quelle che contano per il combattimento diretto: Attacco normale (AA), Abilità elementale (tasto E), Tripudio (tasto Q).
Questi tre livelli entrano anche nella «Stima rotazione» (barra in alto / menu Analisi): un indice che moltiplica il proxy danno della build in base a NA/E/Q, non il DPS reale del gioco.
Le altre quattro sono “Extra 1–4”: servono solo come appunti; non entrano nel calcolo DPS del manufatto né nella rotazione, anche se compili un numero.

PASSO 7 — Salvare sul computer (importante)
1) Se il personaggio esiste già: premi LISTA, clicca sulla riga giusta, controlla i dati, poi SALVA.
2) Se è nuovo: compila tutto, premi SALVA. Se il nome va bene, compare “Salvato” e il programma tiene in memoria l’id del personaggio.
3) SALVA serve a scrivere tutto nel database sul tuo PC: senza salvataggio le modifiche si perdono quando chiudi. In più, alla chiusura della finestra (e a tratti dopo un salvataggio) il programma può copiare i database nella cartella «checkpoints» accanto ai file .db — così hai uno storico recente automatico. Disattiva con variabile d’ambiente GENSHIN_CHECKPOINT=0 se non la vuoi.
4) NUOVO pulisce la scheda per crearne un’altra; non cancella i personaggi già salvati finché non usi CANCELLA.
5) Per artefatti: dopo SALVA del personaggio, puoi assegnare Fiore/Piuma/… con SCEGLI.

Questionario avanzato (opzionale)
Puoi aprire il file Word “questionario_genshin_avanzato.docx” con il pulsante sotto. Compilalo se vuoi e invialo a: """ + QUESTIONARIO_EMAIL + """

Divertiti!"""


_EXIT_GUI_FORCE_WEB = 3


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes")


class GenshinApp:
    """Applicazione Genshin Manager. GUI: solo eventi e view (non l’entry point ufficiale)."""

    def __init__(self):
        self.service = AppService()
        self.selected_id = None
        self.slot_map = dict(zip(SLOT_UI, SLOT_DB))

    def run(self):
        if _env_truthy("GENSHIN_FORCE_WEB"):
            print(
                "GENSHIN_FORCE_WEB=1: avvio GUI Tk bloccato. Entry point ufficiale: python3 run_web.py",
                file=sys.stderr,
            )
            sys.exit(_EXIT_GUI_FORCE_WEB)
        self._build_ui()
        self._bind_events()
        try:
            load_and_apply_gui_checkpoint(self)
        except Exception:
            logger.exception("ripristino checkpoint GUI")
        self._start_periodic_gui_checkpoint()
        self.root.mainloop()

    def _start_periodic_gui_checkpoint(self) -> None:
        """Salvataggio leggero periodico del form (resilienza dopo errori silenziosi)."""

        def tick() -> None:
            try:
                self.root.winfo_exists()
            except tk.TclError:
                return
            try:
                save_gui_checkpoint_safe(self)
            except Exception:
                pass
            try:
                self.root.after(45_000, tick)
            except tk.TclError:
                pass

        try:
            self.root.after(45_000, tick)
        except tk.TclError:
            pass

    def _build_ui(self):
        self.root = tk.Tk()
        self.root.title("Genshin Manager")
        self.root.geometry("1240x1120")
        self._build_menu()
        self._build_header_bar()
        self._build_scrollable_main()
        self._build_personaggio_section()
        self._build_arma_section()
        self._build_artefatti_section()
        self._build_costellazioni_talenti_section()
        self._build_inventario_section()

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        analisi_m = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Analisi", menu=analisi_m)
        analisi_m.add_command(label="Stima rotazione DPS…", command=self._apri_stima_rotazione)

        help_m = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aiuto", menu=help_m)
        help_m.add_command(label="Istruzioni (facili)", command=self._mostra_istruzioni)
        help_m.add_command(label="Apri questionario Word", command=self._apri_questionario_docx)

    def _build_header_bar(self):
        """Barra in alto: Dashboard web, Importa personaggio, ecc."""
        bar = tk.Frame(self.root, bg="#e4e9ff", padx=10, pady=8)
        bar.pack(side="top", fill="x")
        tk.Label(bar, text="Navigazione rapida:", bg="#e4e9ff", fg="#2a3366", font=("Helvetica", 11, "bold")).pack(
            side="left", padx=(0, 10)
        )
        tk.Button(bar, text="Dashboard", font=("Helvetica", 11), command=self._open_web_dashboard, padx=12).pack(
            side="left", padx=(0, 6)
        )
        tk.Button(bar, text="Rotazione…", font=("Helvetica", 11), command=self._apri_stima_rotazione, padx=12).pack(
            side="left", padx=(0, 6)
        )

    def _open_web_dashboard(self):
        """Apre la dashboard Flask nel browser (server locale o base URL da ambiente)."""

        def _open() -> None:
            import webbrowser

            base = (os.environ.get("GENSHIN_WEB_BASE") or "http://127.0.0.1:5001").rstrip("/")
            webbrowser.open(f"{base}/dashboard.html")

        gui_safe_call(self.root, _open)

    def _mostra_istruzioni(self):
        win = tk.Toplevel(self.root)
        win.title("Come si usa — istruzioni facili")
        win.minsize(560, 480)
        win.geometry("640x560")

        outer = tk.Frame(win, bg="#e8f0ff")
        outer.pack(fill="both", expand=True)

        bg_path = PROJECT_ROOT / "sfondi" / "inizio.jpg"
        if bg_path.is_file():
            try:
                from PIL import Image, ImageTk
                pil_img = Image.open(bg_path).convert("RGBA")
                pil_img.thumbnail((900, 700), Image.Resampling.LANCZOS)
                self._istruzioni_bg_photo = ImageTk.PhotoImage(pil_img)
                lbl_bg = tk.Label(outer, image=self._istruzioni_bg_photo, borderwidth=0)
                lbl_bg.place(x=0, y=0, relwidth=1, relheight=1)
            except Exception:
                pass

        wrap = tk.Frame(outer, bg="white", highlightbackground="#b8c4ff", highlightthickness=2)
        wrap.pack(expand=True, fill="both", padx=20, pady=20)

        tk.Label(
            wrap,
            text="Istruzioni facili",
            font=("Helvetica", 18, "bold"),
            bg="white",
            fg="#3d4a9e",
        ).pack(pady=(12, 6))

        fscroll = tk.Frame(wrap, bg="white")
        fscroll.pack(fill="both", expand=True, padx=10, pady=(0, 12))
        sb = tk.Scrollbar(fscroll)
        sb.pack(side="right", fill="y")
        txt = tk.Text(
            fscroll,
            wrap="word",
            font=("Helvetica", 13),
            bg="#fefdff",
            fg="#222233",
            padx=14,
            pady=12,
            yscrollcommand=sb.set,
            relief="flat",
            borderwidth=0,
        )
        txt.pack(side="left", fill="both", expand=True)
        sb.config(command=txt.yview)
        txt.insert("1.0", _ISTRUZIONI_BAMBINI)
        txt.configure(state="disabled")

        foot = tk.Frame(wrap, bg="white")
        foot.pack(fill="x", padx=10, pady=(0, 12))
        tk.Button(foot, text="Apri questionario (Word)", command=self._apri_questionario_docx).pack(side="left", padx=(0, 10))
        tk.Label(foot, text=f"Invio compilato a: {QUESTIONARIO_EMAIL}", bg="white", fg="#3d4a9e").pack(side="left")

    def _apri_questionario_docx(self):
        p = QUESTIONARIO_DOCX
        if not p.is_file():
            messagebox.showinfo("Attenzione", "Non trovo il file del questionario nella cartella del programma.")
            return
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", str(p)], check=False)
            elif os.name == "nt":
                os.startfile(str(p))
            else:
                subprocess.run(["xdg-open", str(p)], check=False)
        except Exception:
            logger.exception("_apri_questionario_docx")
            notify_unexpected(self.root)

    def _build_scrollable_main(self):
        canvas = tk.Canvas(self.root)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview, width=25)
        self.main_frame = tk.Frame(canvas)
        self.main_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.main_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_personaggio_section(self):
        frame = tk.LabelFrame(self.main_frame, text="PERSONAGGIO")
        frame.pack(fill="x", padx=10, pady=10)
        container = tk.Frame(frame)
        container.pack(fill="x")
        data_frame = tk.Frame(container)
        data_frame.pack(side="left", fill="x", expand=True)

        r1 = tk.Frame(data_frame)
        r1.pack(fill="x", pady=5)
        fn = tk.Frame(r1)
        fn.pack(side="left", padx=10)
        tk.Label(fn, text="Nome").pack(side="left")
        self.nome_var = tk.StringVar()
        nomi = self.service.nomi_per_autocomplete()
        self.nome_combo = ttk.Combobox(
            fn,
            values=tuple([""]) + tuple(nomi),
            width=25,
            textvariable=self.nome_var,
            state="normal",
        )
        self.nome_combo.pack(side="left", padx=5)
        self.livello_entry = create_entry(r1, "Livello", 5)
        self.elemento_var = tk.StringVar(value="Pyro")
        fe = tk.Frame(r1)
        fe.pack(side="left", padx=10)
        tk.Label(fe, text="Elemento").pack(side="left")
        AutocompleteCombobox(fe, values=ELEMENTI, width=10, textvariable=self.elemento_var).pack(side="left")

        r2 = tk.Frame(data_frame)
        r2.pack(fill="x", pady=5)
        self.hp_entry = create_entry(r2, "HP", 10)
        self.atk_entry = create_entry(r2, "ATK", 10)
        self.def_entry = create_entry(r2, "DEF", 10)
        self.em_entry = create_entry(r2, "EM", 10)

        r3 = tk.Frame(data_frame)
        r3.pack(fill="x", pady=5)
        self.cr_entry = create_entry(r3, "CR", 10)
        self.cd_entry = create_entry(r3, "CD", 10)
        self.er_entry = create_entry(r3, "ER", 10)

        self._personaggio_entries = [
            self.hp_entry, self.atk_entry, self.def_entry, self.em_entry,
            self.cr_entry, self.cd_entry, self.er_entry
        ]

        btn_frame = tk.Frame(container)
        btn_frame.pack(side="left", padx=20)
        tk.Button(btn_frame, text="Nuovo", width=10, command=self._on_nuovo).pack(pady=3)
        tk.Button(btn_frame, text="Salva", width=10, command=self._on_salva).pack(pady=3)
        tk.Button(btn_frame, text="Cancella", width=10, command=self._on_cancella).pack(pady=3)
        tk.Button(btn_frame, text="Lista", width=10, command=self._on_lista).pack(pady=3)
        tk.Button(btn_frame, text="Pulisci test", width=10, command=self._on_pulisci_test).pack(pady=3)

    def _build_arma_section(self):
        frame = tk.LabelFrame(self.main_frame, text="ARMA")
        frame.pack(fill="x", padx=10, pady=5)
        body = tk.Frame(frame)
        body.pack(fill="x", pady=4, padx=6)
        col_left = tk.Frame(body)
        col_left.pack(side="left", fill="both", expand=True, padx=(0, 24))
        col_right = tk.Frame(body)
        col_right.pack(side="left", fill="y")

        lw = 14

        def row_label(parent, text):
            return tk.Label(parent, text=text, width=lw, anchor="w")

        # Colonna 1: nome, tipo, livello, stelle
        r = tk.Frame(col_left)
        r.pack(fill="x", pady=3)
        row_label(r, "Nome").pack(side="left", padx=(0, 6))
        nomi_ar = self.service.nomi_armi_autocomplete()
        self.arma_nome_entry = ttk.Combobox(
            r,
            values=tuple([""]) + tuple(nomi_ar),
            width=34,
            state="normal",
        )
        self.arma_nome_entry.pack(side="left", fill="x", expand=True)

        r = tk.Frame(col_left)
        r.pack(fill="x", pady=3)
        row_label(r, "Tipo").pack(side="left", padx=(0, 6))
        self.tipo_var = tk.StringVar(value="Spada")
        AutocompleteCombobox(r, values=TIPI_ARMA, width=18, textvariable=self.tipo_var).pack(side="left")

        r = tk.Frame(col_left)
        r.pack(fill="x", pady=3)
        row_label(r, "Livello").pack(side="left", padx=(0, 6))
        self.arma_liv_entry = tk.Entry(r, width=6)
        self.arma_liv_entry.pack(side="left", padx=(0, 18))
        row_label(r, "Stelle ★").pack(side="left", padx=(0, 6))
        self.arma_stelle_entry = tk.Entry(r, width=6)
        self.arma_stelle_entry.pack(side="left")

        # Colonna 2: ATK base, stat secondaria, valore (campi larghi)
        r = tk.Frame(col_right)
        r.pack(fill="x", pady=3)
        row_label(r, "ATK base").pack(side="left", padx=(0, 6))
        self.arma_atk_entry = tk.Entry(r, width=10)
        self.arma_atk_entry.pack(side="left")

        r = tk.Frame(col_right)
        r.pack(fill="x", pady=3)
        row_label(r, "Stat secondaria").pack(side="left", padx=(0, 6))
        self.arma_stat_var = tk.StringVar()
        AutocompleteCombobox(r, values=STATS, width=28, textvariable=self.arma_stat_var).pack(side="left")

        r = tk.Frame(col_right)
        r.pack(fill="x", pady=3)
        row_label(r, "Valore").pack(side="left", padx=(0, 6))
        self.arma_val_entry = tk.Entry(r, width=10)
        self.arma_val_entry.pack(side="left")

    def _build_artefatti_section(self):
        frame = tk.LabelFrame(self.main_frame, text="ARTEFATTI EQUIPAGGIATI")
        frame.pack(fill="x", padx=10, pady=5)
        self.artefatti_widgets = {}
        for slot_ui in SLOT_UI:
            fr = tk.Frame(frame)
            fr.pack(fill="x", pady=3)
            tk.Label(fr, text=slot_ui, width=8).pack(side="left")
            lb = tk.Label(fr, text="—", relief="sunken", width=45, anchor="w")
            lb.pack(side="left", padx=5)
            tk.Button(fr, text="Scegli", width=8, command=lambda s=slot_ui: self._scegli_artefatto(s)).pack(side="left")
            tk.Button(fr, text="Togli", width=6, command=lambda s=slot_ui: self._togli_artefatto(s)).pack(side="left")
            tk.Button(fr, text="DPS", width=6, command=lambda s=slot_ui: self._mostra_dps(s)).pack(side="left")
            self.artefatti_widgets[slot_ui] = {"label_art": lb, "artefatto_id": None}

    def _build_costellazioni_talenti_section(self):
        frame = tk.LabelFrame(self.main_frame, text="COSTELLAZIONI E TALENTI")
        frame.pack(fill="x", padx=10, pady=5)

        cf = tk.Frame(frame)
        cf.pack(fill="x", padx=6, pady=6)
        tk.Label(
            cf,
            text="Costellazioni: per ogni C scegli 0 = non attiva, 1 = attiva.",
            font=("Helvetica", 11),
        ).pack(anchor="w")
        row_c = tk.Frame(cf)
        row_c.pack(fill="x", pady=4)
        self.cost_entries = []
        for i in range(6):
            cell = tk.Frame(row_c)
            cell.pack(side="left", padx=8)
            tk.Label(cell, text=f"C{i + 1}").pack()
            cb = ttk.Combobox(cell, values=["0", "1"], width=4, state="readonly")
            cb.set("0")
            cb.pack()
            self.cost_entries.append(cb)

        tk.Frame(frame, height=1, bg="#ccc").pack(fill="x", padx=8, pady=8)

        tf = tk.Frame(frame)
        tf.pack(fill="x", padx=6, pady=(0, 8))
        tk.Label(
            tf,
            text="Talenti (7): scrivi “-”, oppure 0, oppure il livello 1–10. "
            "AA, E, Q = combattimento e stima rotazione (barra Rotazione…); Extra 1–4 = solo appunti.",
            font=("Helvetica", 11),
            wraplength=900,
            justify="left",
        ).pack(anchor="w")
        gr = tk.Frame(tf)
        gr.pack(fill="x", pady=6)
        self.talenti_entries = []
        for i, lbl in enumerate(_TALENTI_LABELS):
            r, c = divmod(i, 4)
            cell = tk.Frame(gr)
            cell.grid(row=r, column=c, padx=10, pady=6, sticky="n")
            tk.Label(cell, text=lbl, font=("Helvetica", 10)).pack()
            e = tk.Entry(cell, width=6, justify="center")
            e.pack()
            self.talenti_entries.append(e)

    def _build_inventario_section(self):
        frame = tk.LabelFrame(self.main_frame, text="INVENTARIO ARTEFATTI")
        frame.pack(fill="x", padx=10, pady=10)
        tk.Button(frame, text="Apri Inventario Artefatti", command=self._apri_inventario).pack(pady=5)

    def _bind_events(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    # --- Visualizzazione ---
    def _refresh_nome_armi_combos(self, nome_extra: str = "", arma_extra: str = "") -> None:
        nomi = list(self.service.nomi_per_autocomplete())
        ne = (nome_extra or "").strip()
        if ne and ne not in nomi:
            nomi.append(ne)
        self.nome_combo["values"] = tuple([""]) + tuple(sorted(nomi, key=str.lower))
        try:
            self.nome_combo._values = self.nome_combo["values"]
        except tk.TclError:
            pass
        arms = list(self.service.nomi_armi_autocomplete())
        ae = (arma_extra or "").strip()
        if ae and ae not in arms:
            arms.append(ae)
        self.arma_nome_entry["values"] = tuple([""]) + tuple(sorted(arms, key=str.lower))
        try:
            self.arma_nome_entry._values = self.arma_nome_entry["values"]
        except tk.TclError:
            pass

    def _clear_form(self):
        self.nome_var.set("")
        self._set_entry(self.livello_entry, "")
        self.elemento_var.set("Pyro")
        for e in self._personaggio_entries:
            self._set_entry(e, "")
        self.arma_nome_entry.set("")
        self.tipo_var.set("Spada")
        self._set_entry(self.arma_liv_entry, "")
        self._set_entry(self.arma_stelle_entry, "")
        self._set_entry(self.arma_atk_entry, "")
        self.arma_stat_var.set("")
        self._set_entry(self.arma_val_entry, "")
        for cb in self.cost_entries:
            cb.set("0")
        for e in self.talenti_entries:
            self._set_entry(e, "-")
        for w in self.artefatti_widgets.values():
            w["label_art"].config(text="—")
            w["artefatto_id"] = None
        save_gui_checkpoint_safe(self)
        mark_gui_checkpoint_dirty(self)

    def _set_entry(self, entry, val):
        entry.delete(0, tk.END)
        entry.insert(0, str(val))

    def _populate_form(self, dati: dict):
        """Popola form con dati già formattati dal service."""
        try:
            self.nome_var.set(dati["nome"])
            self._set_entry(self.livello_entry, dati["livello"])
            self.elemento_var.set(dati["elemento"])
            stats = [dati["hp_flat"], dati["atk_flat"], dati["def_flat"], dati["em_flat"],
                     dati["cr"], dati["cd"], dati["er"]]
            for e, v in zip(self._personaggio_entries, stats):
                self._set_entry(e, v)

            arma = dati["arma"]
            self.arma_nome_entry.set(arma.get("nome") or "")
            self.tipo_var.set(arma["tipo"])
            self._set_entry(self.arma_liv_entry, arma["livello"])
            self._set_entry(self.arma_stelle_entry, arma["stelle"])
            self._set_entry(self.arma_atk_entry, arma["atk_base"])
            self.arma_stat_var.set(arma["stat_secondaria"])
            self._set_entry(self.arma_val_entry, arma["valore_stat"])

            for cb, v in zip(self.cost_entries, dati["costellazioni"]):
                cb.set("1" if v else "0")
            tal = dati["talenti"] or []
            for i, e in enumerate(self.talenti_entries):
                self._set_entry(e, tal[i] if i < len(tal) else "-")

            for slot_ui, slot_db in self.slot_map.items():
                art = dati["artefatti"].get(slot_db)
                w = self.artefatti_widgets[slot_ui]
                aid = art.get("id") if art else None
                w["artefatto_id"] = aid if aid not in (None, "") else None
                w["label_art"].config(text=(art.get("label") if art else None) or "—")

            am = dati.get("arma") or {}
            self._refresh_nome_armi_combos(nome_extra=dati.get("nome") or "", arma_extra=am.get("nome") or "")
        except Exception:
            logger.exception("_populate_form")
            notify_unexpected(self.root)
            return
        save_gui_checkpoint_safe(self)
        mark_gui_checkpoint_dirty(self)

    def _form_personaggio(self):
        return {
            "nome": self.nome_var.get(),
            "livello": self.livello_entry.get(),
            "elemento": self.elemento_var.get(),
            "hp_flat": self.hp_entry.get(), "atk_flat": self.atk_entry.get(),
            "def_flat": self.def_entry.get(), "em_flat": self.em_entry.get(),
            "cr": self.cr_entry.get(), "cd": self.cd_entry.get(), "er": self.er_entry.get(),
        }

    def _form_arma(self):
        return {
            "nome": self.arma_nome_entry.get(),
            "tipo": self.tipo_var.get(),
            "livello": self.arma_liv_entry.get(),
            "stelle": self.arma_stelle_entry.get(),
            "atk_base": self.arma_atk_entry.get(),
            "stat_secondaria": self.arma_stat_var.get(),
            "valore_stat": self.arma_val_entry.get(),
        }

    def _form_costellazioni(self):
        return {f"c{i+1}": cb.get() for i, cb in enumerate(self.cost_entries[:6])}

    def _form_talenti(self):
        keys = ("aa", "skill", "burst", "pas1", "pas2", "pas3", "pas4")
        return {k: self.talenti_entries[i].get() for i, k in enumerate(keys)}

    def _form_equipaggiamento(self):
        return {slot_db: self.artefatti_widgets[slot_ui]["artefatto_id"]
                for slot_ui, slot_db in self.slot_map.items()}

    # --- Eventi ---
    def _on_nuovo(self):
        self.selected_id = None
        self._clear_form()

    def _on_salva(self):
        fp = self._form_personaggio()
        nome = canonicalizza_nome_personaggio((fp.get("nome") or ""))
        fa = self._form_arma()
        an = canonicalizza_nome_arma((fa.get("nome") or ""))
        meta = {}

        ok, msg = self.service.valida_nome(
            nome,
            self.selected_id,
            custom_confirm=True,
        )
        if not ok:
            messagebox.showinfo("Attenzione", msg)
            return
        try:
            self.selected_id = self.service.salva_completo(
                self.selected_id,
                fp,
                fa,
                self._form_costellazioni(),
                self._form_talenti(),
                self._form_equipaggiamento(),
                meta=meta,
            )
            self._refresh_nome_armi_combos(nome_extra=nome, arma_extra=an)
            try:
                from core.checkpoint import maybe_checkpoint_after_save

                maybe_checkpoint_after_save()
            except Exception:
                pass
            save_gui_checkpoint_safe(self)
            messagebox.showinfo("OK", "Salvato.")
        except Exception:
            logger.exception("_on_salva")
            notify_unexpected(self.root)

    def _on_cancella(self):
        if self.selected_id is None:
            return
        if messagebox.askyesno("Conferma", "Eliminare personaggio e dati collegati?"):
            try:
                self.service.elimina_personaggio(self.selected_id)
                self.selected_id = None
                self._clear_form()
                messagebox.showinfo("OK", "Eliminato.")
            except Exception:
                logger.exception("_on_cancella")
                notify_unexpected(self.root)

    def _on_lista(self):
        try:
            righe = self.service.lista_personaggi_righe()
        except Exception:
            logger.exception("_on_lista")
            notify_unexpected(self.root)
            return
        win = tk.Toplevel(self.root)
        win.title("Lista Personaggi")
        win.geometry("550x400")
        tree = ttk.Treeview(win, columns=("ID", "Nome", "Livello", "Elemento"), show="headings")
        for col in ("ID", "Nome", "Livello", "Elemento"):
            tree.heading(col, text=col)
            tree.column(col, anchor="center")
        tree.pack(fill="both", expand=True)
        for r in righe:
            tree.insert("", "end", values=r)

        def on_select(event):
            sel = tree.selection()
            if sel:
                try:
                    id_pg = int(tree.item(sel[0], "values")[0])
                except (ValueError, TypeError, tk.TclError):
                    notify_unexpected(win)
                    return
                try:
                    dati = self.service.carica_dati_completi(id_pg)
                except Exception:
                    logger.exception("carica_dati_completi lista")
                    notify_unexpected(win)
                    return
                if dati:
                    self.selected_id = id_pg
                    self._populate_form(dati)
                win.destroy()

        tree.bind("<<TreeviewSelect>>", on_select)

    def _on_pulisci_test(self):
        """Elimina personaggi di test dal database."""
        try:
            n = self.service.rimuovi_entrate_test()
            if n > 0:
                self._refresh_nome_armi_combos()
                if self.selected_id:
                    # Verifica se il personaggio selezionato era tra i test
                    dati = self.service.carica_dati_completi(self.selected_id)
                    if not dati:
                        self.selected_id = None
                        self._clear_form()
                messagebox.showinfo("OK", f"Rimossi {n} entrate di test.")
            else:
                messagebox.showinfo("Info", "Nessuna entrata di test trovata.")
        except Exception:
            logger.exception("_on_pulisci_test")
            notify_unexpected(self.root)

    def _scegli_artefatto(self, slot_ui):
        if self.selected_id is None:
            messagebox.showwarning("Attenzione", "Seleziona prima un personaggio (Lista).")
            return
        slot_db = self.slot_map[slot_ui]
        righe = self.service.lista_artefatti_liberi_righe(slot_db)
        if not righe:
            messagebox.showinfo("Info", f"Nessun artefatto libero per {slot_ui}.")
            return
        win = tk.Toplevel(self.root)
        win.title(f"Seleziona artefatto {slot_ui}")
        win.geometry("600x300")
        tree = ttk.Treeview(win, columns=("ID", "Set", "Main", "Liv", "★"), show="headings")
        for col in ("ID", "Set", "Main", "Liv", "★"):
            tree.heading(col, text=col)
            tree.column(col, width=100)
        tree.pack(fill="both", expand=True)
        for r in righe:
            tree.insert("", "end", values=_gui_tree_row_values(r, 5))

        def on_sel(event):
            sel = tree.selection()
            if sel:
                try:
                    vals = tree.item(sel[0], "values")
                    if not vals:
                        return
                    art_id = int(str(vals[0]).strip())
                except (ValueError, TypeError, tk.TclError):
                    messagebox.showwarning("Selezione", "Riga non valida: impossibile leggere l'ID.", parent=win)
                    return
                label = self.service.formato_label_artefatto(art_id)
                if label:
                    self.artefatti_widgets[slot_ui]["artefatto_id"] = art_id
                    self.artefatti_widgets[slot_ui]["label_art"].config(text=label)
                    save_gui_checkpoint_safe(self)
                    mark_gui_checkpoint_dirty(self)
                win.destroy()
        tree.bind("<<TreeviewSelect>>", on_sel)

    def _togli_artefatto(self, slot_ui):
        self.artefatti_widgets[slot_ui]["artefatto_id"] = None
        self.artefatti_widgets[slot_ui]["label_art"].config(text="—")
        save_gui_checkpoint_safe(self)
        mark_gui_checkpoint_dirty(self)

    def _mostra_dps(self, slot_ui):
        aid = self.artefatti_widgets[slot_ui].get("artefatto_id")
        if not aid:
            messagebox.showinfo("Info", "Nessun artefatto equipaggiato.")
            return
        try:
            res = self.service.dps_result_artefatto(aid)
        except Exception:
            logger.exception("_mostra_dps")
            notify_unexpected(self.root)
            return
        if not res:
            notify_unexpected(self.root)
            return
        self._DpsResultWindow(self.root, res).show()

    def _apri_stima_rotazione(self):
        if self.selected_id is None:
            messagebox.showwarning(
                "Attenzione",
                "Seleziona prima un personaggio (Lista) e carica la scheda.",
                parent=self.root,
            )
            return
        try:
            data = self.service.get_rotation_stima(self.selected_id)
        except Exception:
            logger.exception("_apri_stima_rotazione")
            notify_unexpected(self.root)
            return
        if not data.get("ok"):
            notify_unexpected(self.root)
            return
        self._RotationStimaWindow(self.root, data).show()

    def _apri_inventario(self):
        self._InventarioWindow(self.root, self.service).show()

    def _on_closing(self):
        try:
            save_gui_checkpoint_safe(self)
        except Exception:
            pass
        try:
            from core.checkpoint import run_automatic_checkpoint

            run_automatic_checkpoint("exit")
        except Exception:
            pass
        self.service.close()
        self.root.destroy()

    class _DpsResultWindow:
        """Finestra DPS / indice manufatto con CombatStats, classifica e breakdown."""

        def __init__(self, parent: tk.Misc, res: DpsResult):
            self.parent = parent
            self.res = res

        def show(self) -> None:
            try:
                self._show_impl()
            except Exception:
                logger.exception("_DpsResultWindow.show")
                notify_unexpected(self.parent)

        def _show_impl(self) -> None:
            res = self.res
            win = tk.Toplevel(self.parent)
            win.transient(self.parent)
            aid = getattr(res, "artifact_id", None)
            win.title(f"DPS — manufatto #{aid if aid is not None else '—'}")
            win.geometry("660x560")
            win.minsize(480, 400)

            pad = {"padx": 12, "pady": 6}
            head = tk.Frame(win)
            head.pack(fill="x", **pad)
            label_txt = str(getattr(res, "display_label_it", None) or "").strip() or (
                "Indice manufatto confrontato sui personaggi salvati."
            )
            tk.Label(
                head,
                text=label_txt,
                font=("Helvetica", 11),
                wraplength=600,
                justify="left",
            ).pack(anchor="w")
            val_fr = tk.Frame(head)
            val_fr.pack(fill="x", pady=(8, 0))
            tk.Label(val_fr, text="Valore principale:", font=("Helvetica", 10, "bold")).pack(side="left")
            val_str = _gui_format_num_g(getattr(res, "value_display", None))
            tk.Label(val_fr, text=val_str, font=("Helvetica", 14, "bold")).pack(side="left", padx=8)
            unit = str(getattr(res, "unit", "") or "—")
            ver = str(getattr(res, "model_version", "") or "")
            tk.Label(
                val_fr,
                text=f"({unit}) · modello v{ver}",
                font=("Helvetica", 9),
            ).pack(side="left")

            warnings = getattr(res, "warnings", None) or []
            if warnings:
                wf = tk.Frame(win)
                wf.pack(fill="x", **pad)
                for w in warnings:
                    tk.Label(wf, text=f"⚠ {w}", fg="#b45309", wraplength=600, justify="left").pack(anchor="w")

            nb = ttk.Notebook(win)
            nb.pack(fill="both", expand=True, padx=8, pady=(0, 4))

            tab_rank = tk.Frame(nb)
            nb.add(tab_rank, text="Classifica personaggi")
            cols = ("pos", "nome", "elem", "score", "fattori")
            tree = ttk.Treeview(tab_rank, columns=cols, show="headings", height=14)
            for c, h, w in (
                ("pos", "#", 32),
                ("nome", "Personaggio", 160),
                ("elem", "El.", 52),
                ("score", "Indice", 72),
                ("fattori", "Moltiplicatori (elem·EM·CR)", 210),
            ):
                tree.heading(c, text=h)
                tree.column(c, width=w)
            sc = ttk.Scrollbar(tab_rank, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=sc.set)
            tree.pack(side="left", fill="both", expand=True)
            sc.pack(side="right", fill="y")
            ranking = getattr(res, "ranking", None) or []
            for i, row in enumerate(ranking, start=1):
                if not isinstance(row, dict):
                    continue
                ftxt = _dps_ranking_fattori_cell(row.get("fattori"))
                tree.insert(
                    "",
                    "end",
                    values=(
                        i,
                        str(row.get("nome", "") or ""),
                        str(row.get("elemento", "") or ""),
                        _gui_format_num_g(row.get("score")),
                        ftxt,
                    ),
                )

            tab_stats = tk.Frame(nb)
            nb.add(tab_stats, text="Statistiche (pezzo)")
            mono = ("Menlo", 10) if sys.platform == "darwin" else ("Consolas", 10)
            txt_s = tk.Text(tab_stats, height=16, width=78, font=mono, wrap="word")
            txt_s.pack(fill="both", expand=True, padx=6, pady=6)
            cs = getattr(res, "combat_stats", None)
            if cs is not None and hasattr(cs, "format_summary_it"):
                try:
                    txt_s.insert("1.0", cs.format_summary_it())
                except Exception:
                    txt_s.insert("1.0", "— (riepilogo statistiche non disponibile)")
            else:
                txt_s.insert("1.0", "—")
            txt_s.configure(state="disabled")

            tab_det = tk.Frame(nb)
            nb.add(tab_det, text="Dettaglio")
            txt_d = tk.Text(tab_det, height=16, width=78, font=("Helvetica", 10), wrap="word")
            txt_d.pack(fill="both", expand=True, padx=6, pady=6)
            lines: list[str] = []
            lbl = getattr(res, "artifact_label", None)
            if lbl:
                lines.append(f"Pezzo: {lbl}")
                lines.append("")
            breakdown = getattr(res, "breakdown", None) or {}
            if isinstance(breakdown, dict):
                for k, v in breakdown.items():
                    lines.append(f"{k}: {v}")
            else:
                lines.append(str(breakdown))
            if ranking:
                lines.append("")
                lines.append("— Classifica (stesso ordine della tab) —")
                for i, row in enumerate(ranking, start=1):
                    if not isinstance(row, dict):
                        continue
                    nm = str(row.get("nome", "") or "—")
                    sc = _gui_format_num_g(row.get("score"))
                    lines.append(f"{i}. {nm}: indice {sc}")
                    f = row.get("fattori")
                    if isinstance(f, dict):
                        lines.append(
                            f"   base {_gui_format_num_g(f.get('base'))} · elemento ×{_gui_format_num_g(f.get('elemento'))} "
                            f"· EM ×{_gui_format_num_g(f.get('em'))} · CR ×{_gui_format_num_g(f.get('crit_adjust'))}"
                        )
            txt_d.insert("1.0", "\n".join(lines) if lines else "—")
            txt_d.configure(state="disabled")

            tk.Button(win, text="Chiudi", command=win.destroy).pack(pady=(4, 12))

    class _RotationStimaWindow:
        """Stima indice rotazione (v0.1): proxy build × fattore talenti NA/E/Q; stile come DPS manufatto."""

        def __init__(self, parent: tk.Misc, data: dict):
            self.parent = parent
            self.data = data if isinstance(data, dict) else {}

        def show(self) -> None:
            try:
                self._show_impl()
            except Exception:
                logger.exception("_RotationStimaWindow.show")
                notify_unexpected(self.parent)

        def _show_impl(self) -> None:
            d = self.data
            win = tk.Toplevel(self.parent)
            win.transient(self.parent)
            nome = str(d.get("personaggio_nome") or "").strip() or "Personaggio"
            win.title(f"Stima rotazione — {nome}")
            win.geometry("680x560")
            win.minsize(520, 420)
            pad = {"padx": 12, "pady": 6}

            head = tk.Frame(win)
            head.pack(fill="x", **pad)
            tk.Label(
                head,
                text=str(d.get("note_it") or ""),
                font=("Helvetica", 10),
                wraplength=620,
                justify="left",
            ).pack(anchor="w")

            row = tk.Frame(head)
            row.pack(fill="x", pady=(10, 0))
            tk.Label(row, text="Indice rotazione:", font=("Helvetica", 10, "bold")).pack(side="left")
            tk.Label(
                row,
                text=_gui_format_num_g(d.get("rotation_index")),
                font=("Helvetica", 18, "bold"),
            ).pack(side="left", padx=10)
            tk.Label(
                row,
                text=f"proxy × {_gui_format_num_g(d.get('rotation_multiplier'))} · v{d.get('model_version') or '—'}",
                font=("Helvetica", 9),
            ).pack(side="left")

            row2 = tk.Frame(head)
            row2.pack(fill="x", pady=(4, 0))
            tk.Label(row2, text="Proxy build:", font=("Helvetica", 10)).pack(side="left")
            tk.Label(row2, text=_gui_format_num_g(d.get("damage_proxy")), font=("Helvetica", 10)).pack(
                side="left", padx=8
            )
            tk.Label(row2, text=f"preset: {d.get('preset') or '—'}", font=("Helvetica", 10)).pack(side="left", padx=12)

            for w in d.get("warnings") or []:
                tk.Label(head, text=f"⚠ {w}", fg="#b45309", wraplength=620, justify="left").pack(
                    anchor="w", pady=(6, 0)
                )

            nb = ttk.Notebook(win)
            nb.pack(fill="both", expand=True, padx=8, pady=(4, 0))

            tab_t = tk.Frame(nb)
            nb.add(tab_t, text="Talenti e pesi")
            mono = ("Menlo", 10) if sys.platform == "darwin" else ("Consolas", 10)
            txt_t = tk.Text(tab_t, height=18, width=80, font=mono, wrap="word")
            txt_t.pack(fill="both", expand=True, padx=6, pady=6)
            lines = [
                "Livelli talento (AA, E, Q):",
                repr(d.get("talent_levels")),
                "",
                "Moltiplicatori indicativi:",
                repr(d.get("talent_multipliers")),
                "",
                "Pesi NA / E / Q (dopo scala ER sul burst):",
                repr(d.get("weights")),
            ]
            txt_t.insert("1.0", "\n".join(lines))
            txt_t.configure(state="disabled")

            tab_s = tk.Frame(nb)
            nb.add(tab_s, text="Statistiche totali")
            txt_s = tk.Text(tab_s, height=18, width=80, font=mono, wrap="word")
            txt_s.pack(fill="both", expand=True, padx=6, pady=6)
            summary = str(d.get("combat_totale_summary_it") or "—")
            txt_s.insert("1.0", summary)
            txt_s.configure(state="disabled")

            tab_n = tk.Frame(nb)
            nb.add(tab_n, text="Nota proxy")
            txt_n = tk.Text(tab_n, height=18, width=80, font=("Helvetica", 10), wrap="word")
            txt_n.pack(fill="both", expand=True, padx=6, pady=6)
            txt_n.insert("1.0", str(d.get("damage_proxy_note_it") or "—"))
            txt_n.configure(state="disabled")

            tk.Button(win, text="Chiudi", command=win.destroy).pack(pady=(4, 12))

    class _InventarioWindow:
        """Finestra inventario artefatti. Solo UI ed eventi."""

        def __init__(self, parent, service: AppService):
            self.parent = parent
            self.service = service

        def show(self):
            win = tk.Toplevel(self.parent)
            win.title("Inventario Artefatti")
            win.geometry("900x500")
            tree = ttk.Treeview(win, columns=("ID", "Slot", "Set", "Main", "Val", "Liv", "★"), show="headings")
            for col in ("ID", "Slot", "Set", "Main", "Val", "Liv", "★"):
                tree.heading(col, text=col)
                tree.column(col, width=90)
            tree.pack(fill="both", expand=True)

            def refresh():
                for i in tree.get_children():
                    tree.delete(i)
                try:
                    righe = self.service.lista_artefatti_inventario_righe()
                except Exception:
                    logger.exception("inventario refresh")
                    notify_unexpected(win)
                    return
                for r in righe:
                    try:
                        tree.insert("", "end", values=_gui_tree_row_values(r, 7))
                    except tk.TclError:
                        continue
            refresh()

            tk.Button(win, text="+ Registra nuovo artefatto", command=lambda: self._form_aggiungi(win, refresh)).pack(pady=5)

        def _form_aggiungi(self, parent_win, refresh_cb):
            import webbrowser
            add_win = tk.Toplevel(parent_win)
            add_win.title("Registra artefatto")
            add_win.geometry("820x450")
            f = tk.Frame(add_win, padx=10, pady=10)
            f.pack(fill="both", expand=True)
            r1 = tk.Frame(f)
            r1.pack(fill="x", pady=3)
            tk.Label(r1, text="Slot").pack(side="left", padx=(0, 5))
            slot_var = tk.StringVar(value="fiore")
            slot_combo = AutocompleteCombobox(r1, values=SLOT_DB, width=10, textvariable=slot_var)
            slot_combo.pack(side="left")
            tk.Label(r1, text="Nome pezzo").pack(side="left", padx=(20, 5))
            nome_var = tk.StringVar()
            nome_combo = AutocompleteCombobox(r1, values=[], width=36, textvariable=nome_var)
            nome_combo.pack(side="left")
            liv_e = create_entry(r1, "Liv", 5)
            stelle_e = create_entry(r1, "★", 5)
            r_set = tk.Frame(f)
            r_set.pack(fill="x", pady=2)
            tk.Label(r_set, text="Set (catalogo)").pack(side="left", padx=(0, 5))
            set_var = tk.StringVar()
            set_combo = AutocompleteCombobox(r_set, values=[], width=34, textvariable=set_var)
            set_combo.pack(side="left", padx=(0, 10))
            tk.Label(r_set, text="Set libero (opz.)").pack(side="left", padx=(0, 5))
            set_libero_var = tk.StringVar()
            tk.Entry(r_set, textvariable=set_libero_var, width=30).pack(side="left")

            def _set_effettivo():
                return (set_libero_var.get() or "").strip() or (set_var.get() or "").strip()

            r1b = tk.Frame(f)
            r1b.pack(fill="x", pady=2)
            q = lambda: _set_effettivo() or nome_combo.get()
            tk.Button(r1b, text="Cerca web", command=lambda: webbrowser.open(self.service.cerca_artefatto_web(q()))).pack(side="left")

            r2 = tk.Frame(f)
            r2.pack(fill="x", pady=5)
            main_var = tk.StringVar()
            tk.Label(r2, text="Main Stat").pack(side="left", padx=(0, 5))
            main_combo = AutocompleteCombobox(r2, values=STATS, width=18, textvariable=main_var)
            main_combo.pack(side="left")

            def aggiorna_catalogo(*_):
                slot = slot_var.get().strip().lower()
                if slot not in SLOT_DB:
                    return
                set_vals = self.service.set_per_slot(slot)
                set_combo["values"] = set_vals
                set_combo._values = set_vals
                main_vals = self.service.main_stats_per_slot(slot)
                main_combo["values"] = main_vals
                main_combo._values = main_vals
                _aggiorna_nome()

            def _aggiorna_nome(*_):
                slot = slot_var.get().strip().lower()
                if slot not in SLOT_DB:
                    return
                set_p = _set_effettivo()
                nome_p = nome_combo.get().strip()
                righe = self.service.suggerimenti_artefatto(slot, set_p, nome_p)
                nomi = sorted(set(r[1] for r in righe))
                nome_combo["values"] = nomi
                nome_combo._values = nomi

            set_var.trace_add("write", lambda *_: add_win.after(50, _aggiorna_nome))
            set_libero_var.trace_add("write", lambda *_: add_win.after(50, _aggiorna_nome))
            slot_var.trace_add("write", aggiorna_catalogo)
            aggiorna_catalogo()
            main_val_e = create_entry(r2, "Val", 10)
            r3 = tk.Frame(f)
            r3.pack(fill="x", pady=5)
            subs = []
            for i in range(4):
                sv = tk.StringVar()
                AutocompleteCombobox(r3, values=STATS, width=12, textvariable=sv).pack(side="left", padx=2)
                ev = tk.Entry(r3, width=6)
                ev.pack(side="left", padx=2)
                subs.append((sv, ev))

            def ok():
                self.service.aggiungi_artefatto({
                    "slot": slot_var.get(),
                    "set_nome": _set_effettivo(),
                    "nome": nome_combo.get(),
                    "livello": liv_e.get(),
                    "stelle": stelle_e.get(),
                    "main_stat": main_var.get(),
                    "main_val": main_val_e.get(),
                    "sub1_stat": subs[0][0].get(), "sub1_val": subs[0][1].get(),
                    "sub2_stat": subs[1][0].get(), "sub2_val": subs[1][1].get(),
                    "sub3_stat": subs[2][0].get(), "sub3_val": subs[2][1].get(),
                    "sub4_stat": subs[3][0].get(), "sub4_val": subs[3][1].get(),
                })
                refresh_cb()
                add_win.destroy()
                messagebox.showinfo("OK", "Artefatto registrato.")
            tk.Button(f, text="Salva", command=ok).pack(pady=15)
