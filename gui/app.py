"""
Applicazione principale - assembla e avvia GUI.
Solo gestione eventi e visualizzazione. Logica e dati nel service layer.
"""
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox

from config import PROJECT_ROOT, SLOT_UI, SLOT_DB, ELEMENTI, TIPI_ARMA, STATS, SET_ARTEFATTI, MOSTRA_PULSANTE_HOYOLAB
from core.manual_import import (
    ImportParseError,
    apply_manual_import,
    list_character_choices,
    parse_pasted_payload,
    preview_summary,
)
from core.services import AppService
from gui.widgets import AutocompleteCombobox, create_entry

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
Le altre quattro sono “Extra 1–4”: servono solo come appunti; non entrano nel calcolo DPS del programma, anche se compili un numero.

PASSO 7 — Salvare sul computer (importante)
1) Se il personaggio esiste già: premi LISTA, clicca sulla riga giusta, controlla i dati, poi SALVA.
2) Se è nuovo: compila tutto, premi SALVA. Se il nome va bene, compare “Salvato” e il programma tiene in memoria l’id del personaggio.
3) SALVA serve a scrivere tutto nel database sul tuo PC: senza salvataggio le modifiche si perdono quando chiudi.
4) NUOVO pulisce la scheda per crearne un’altra; non cancella i personaggi già salvati finché non usi CANCELLA.
5) Per artefatti: dopo SALVA del personaggio, puoi assegnare Fiore/Piuma/… con SCEGLI.

Questionario avanzato (opzionale)
Puoi aprire il file Word “questionario_genshin_avanzato.docx” con il pulsante sotto. Compilalo se vuoi e invialo a: """ + QUESTIONARIO_EMAIL + """

Divertiti!"""


class GenshinApp:
    """Applicazione Genshin Manager. GUI: solo eventi e view."""

    def __init__(self):
        self.service = AppService()
        self.selected_id = None
        self.slot_map = dict(zip(SLOT_UI, SLOT_DB))

    def run(self):
        self._build_ui()
        self._bind_events()
        self.root.mainloop()

    def _build_ui(self):
        self.root = tk.Tk()
        self.root.title("Genshin Manager")
        self.root.geometry("1240x1120")
        self._build_menu()
        self._build_scrollable_main()
        self._build_personaggio_section()
        self._build_arma_section()
        self._build_artefatti_section()
        self._build_costellazioni_talenti_section()
        self._build_inventario_section()

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        data_m = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Dati", menu=data_m)
        data_m.add_command(label="Import da copia (JSON / HoYoLAB manuale)…", command=self._import_da_copia)
        help_m = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aiuto", menu=help_m)
        help_m.add_command(label="Istruzioni (facili)", command=self._mostra_istruzioni)
        help_m.add_command(label="Apri questionario Word", command=self._apri_questionario_docx)

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
            messagebox.showerror("File assente", f"Non trovo il questionario:\n{p}")
            return
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", str(p)], check=False)
            elif os.name == "nt":
                os.startfile(str(p))
            else:
                subprocess.run(["xdg-open", str(p)], check=False)
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def _import_da_copia(self):
        """Import JSON incollato: nessun login HoYoLAB; vedi core/manual_import.py."""
        win = tk.Toplevel(self.root)
        win.title("Import dati — JSON manuale")
        win.geometry("760x580")
        win.minsize(560, 440)

        hint = tk.Text(win, height=5, wrap="word", font=("Helvetica", 11), bg="#f4f6ff", relief="flat", padx=8, pady=8)
        hint.pack(fill="x", padx=10, pady=(10, 4))
        hint.insert(
            "1.0",
            "1) Accedi a HoYoLAB nel browser e apri Battle Chronicle.\n"
            "2) F12 → Rete / Network → filtra XHR/fetch → seleziona un personaggio e individua una risposta JSON con nome, livello, fightPropMap (o propMap).\n"
            "3) Tasto destro sulla risposta → Copia → Copia risposta (o salva JSON e incollalo qui).\n"
            "4) Anteprima, poi Importa nuovo oppure Aggiorna scheda corrente.\n"
            "Oppure incolla un JSON nel formato documentato in core/manual_import.py (chiavi: nome, livello, elemento, hp_flat, crit_rate, …).",
        )
        hint.config(state="disabled")

        outer = tk.Frame(win)
        outer.pack(fill="both", expand=True, padx=10, pady=6)
        txt = tk.Text(outer, height=14, font=("Menlo", 10) if sys.platform == "darwin" else ("Consolas", 10))
        ys = tk.Scrollbar(outer, command=txt.yview)
        txt.config(yscrollcommand=ys.set)
        txt.pack(side="left", fill="both", expand=True)
        ys.pack(side="right", fill="y")

        choice_fr = tk.Frame(win)
        tk.Label(choice_fr, text="Se nel JSON ci sono più personaggi:").pack(side="left", padx=(0, 8))
        choice_var = tk.StringVar()
        choice_cb = ttk.Combobox(choice_fr, textvariable=choice_var, state="readonly", width=36)

        preview_lbl = tk.Label(win, text="Premi Anteprima.", justify="left", anchor="nw", font=("Helvetica", 10))
        preview_lbl.pack(fill="x", padx=10, pady=6)

        parsed_holder: dict = {"p": None}

        def refresh_preview(*_):
            try:
                p = parse_pasted_payload(txt.get("1.0", "end"))
                parsed_holder["p"] = p
                chs = list_character_choices(p)
                if len(chs) > 1:
                    names = [c["nome"] for c in chs]
                    choice_cb["values"] = names
                    if choice_var.get() not in names:
                        choice_var.set(names[0])
                    choice_cb.pack(side="left")
                    choice_fr.pack(fill="x", padx=10, pady=(0, 4))
                else:
                    choice_fr.pack_forget()
                preview_lbl.config(text=preview_summary(_effective_parsed()))
            except ImportParseError as e:
                parsed_holder["p"] = None
                choice_fr.pack_forget()
                preview_lbl.config(text=f"Errore: {e}")

        def _effective_parsed():
            p = parsed_holder["p"]
            if not p:
                return None
            chs = list_character_choices(p)
            if len(chs) <= 1:
                return p
            name = choice_var.get() or chs[0]["nome"]
            sel = next((c for c in chs if c["nome"] == name), chs[0])
            out = dict(p)
            out["character"] = sel
            return out

        choice_cb.bind("<<ComboboxSelected>>", lambda e: preview_lbl.config(text=preview_summary(_effective_parsed())))

        btns = tk.Frame(win)
        btns.pack(fill="x", padx=10, pady=10)
        tk.Button(btns, text="Anteprima", command=refresh_preview).pack(side="left", padx=4)
        tk.Button(btns, text="Importa come nuovo personaggio", command=lambda: _do_import(True)).pack(side="left", padx=4)
        btn_upd = tk.Button(btns, text="Aggiorna scheda aperta (ID corrente)", command=lambda: _do_import(False))
        btn_upd.pack(side="left", padx=4)

        def _do_import(as_new: bool):
            try:
                if parsed_holder["p"] is None:
                    refresh_preview()
                p = _effective_parsed()
                if not p:
                    messagebox.showwarning("Import", "Nessun dato valido: usa Anteprima dopo aver incollato il JSON.", parent=win)
                    return
                sid = None if as_new else self.selected_id
                if not as_new and sid is None:
                    messagebox.showwarning("Import", "Nessuna scheda selezionata: usa Lista o Importa come nuovo.", parent=win)
                    return
                ok, msg = self.service.valida_nome(p["character"]["nome"], sid if sid else None)
                if not ok:
                    messagebox.showerror("Import", msg, parent=win)
                    return
                new_id = apply_manual_import(self.service, p, sid, touch_equipment=False)
                self.selected_id = new_id
                dati = self.service.carica_dati_completi(new_id)
                if dati:
                    self._populate_form(dati)
                win.destroy()
                messagebox.showinfo("Import", f"Salvato. ID personaggio: {new_id}")
            except ImportParseError as e:
                messagebox.showerror("Import", str(e), parent=win)
            except Exception as e:
                messagebox.showerror("Import", str(e), parent=win)

        def _sync_update_btn_state(_evt=None):
            btn_upd.config(state="normal" if self.selected_id is not None else "disabled")

        _sync_update_btn_state()
        win.bind("<FocusIn>", _sync_update_btn_state)

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
        self.nome_combo = AutocompleteCombobox(fn, values=nomi, width=25, textvariable=self.nome_var)
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
        self.arma_nome_entry = tk.Entry(r, width=34)
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
            "AA, E, Q = combattimento; Extra 1–4 = solo appunti (non nel calcolo DPS).",
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
    def _clear_form(self):
        self.nome_var.set("")
        self._set_entry(self.livello_entry, "")
        self.elemento_var.set("Pyro")
        for e in self._personaggio_entries:
            self._set_entry(e, "")
        self._set_entry(self.arma_nome_entry, "")
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

    def _set_entry(self, entry, val):
        entry.delete(0, tk.END)
        entry.insert(0, str(val))

    def _populate_form(self, dati: dict):
        """Popola form con dati già formattati dal service."""
        self.nome_var.set(dati["nome"])
        self._set_entry(self.livello_entry, dati["livello"])
        self.elemento_var.set(dati["elemento"])
        stats = [dati["hp_flat"], dati["atk_flat"], dati["def_flat"], dati["em_flat"],
                 dati["cr"], dati["cd"], dati["er"]]
        for e, v in zip(self._personaggio_entries, stats):
            self._set_entry(e, v)

        arma = dati["arma"]
        self._set_entry(self.arma_nome_entry, arma["nome"])
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
            w["artefatto_id"] = art["id"] if art else None
            w["label_art"].config(text=art["label"] if art else "—")

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
        ok, msg = self.service.valida_nome(self._form_personaggio()["nome"], self.selected_id)
        if not ok:
            messagebox.showerror("Errore", msg)
            return
        try:
            self.selected_id = self.service.salva_completo(
                self.selected_id,
                self._form_personaggio(),
                self._form_arma(),
                self._form_costellazioni(),
                self._form_talenti(),
                self._form_equipaggiamento(),
            )
            # Aggiorna autocomplete con eventuali nuovi nomi
            self.nome_combo["values"] = self.service.nomi_per_autocomplete()
            self.nome_combo._values = self.nome_combo["values"]
            messagebox.showinfo("OK", "Salvato.")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def _on_cancella(self):
        if self.selected_id is None:
            return
        if messagebox.askyesno("Conferma", "Eliminare personaggio e dati collegati?"):
            try:
                self.service.elimina_personaggio(self.selected_id)
                self.selected_id = None
                self._clear_form()
                messagebox.showinfo("OK", "Eliminato.")
            except Exception as e:
                messagebox.showerror("Errore", str(e))

    def _on_lista(self):
        win = tk.Toplevel(self.root)
        win.title("Lista Personaggi")
        win.geometry("550x400")
        tree = ttk.Treeview(win, columns=("ID", "Nome", "Livello", "Elemento"), show="headings")
        for col in ("ID", "Nome", "Livello", "Elemento"):
            tree.heading(col, text=col)
            tree.column(col, anchor="center")
        tree.pack(fill="both", expand=True)
        for r in self.service.lista_personaggi_righe():
            tree.insert("", "end", values=r)

        def on_select(event):
            sel = tree.selection()
            if sel:
                id_pg = int(tree.item(sel[0], "values")[0])
                dati = self.service.carica_dati_completi(id_pg)
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
                self.nome_combo["values"] = self.service.nomi_per_autocomplete()
                self.nome_combo._values = self.nome_combo["values"]
                if self.selected_id:
                    # Verifica se il personaggio selezionato era tra i test
                    dati = self.service.carica_dati_completi(self.selected_id)
                    if not dati:
                        self.selected_id = None
                        self._clear_form()
                messagebox.showinfo("OK", f"Rimossi {n} entrate di test.")
            else:
                messagebox.showinfo("Info", "Nessuna entrata di test trovata.")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

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
            tree.insert("", "end", values=r)

        def on_sel(event):
            sel = tree.selection()
            if sel:
                art_id = int(tree.item(sel[0], "values")[0])
                label = self.service.formato_label_artefatto(art_id)
                if label:
                    self.artefatti_widgets[slot_ui]["artefatto_id"] = art_id
                    self.artefatti_widgets[slot_ui]["label_art"].config(text=label)
                win.destroy()
        tree.bind("<<TreeviewSelect>>", on_sel)

    def _togli_artefatto(self, slot_ui):
        self.artefatti_widgets[slot_ui]["artefatto_id"] = None
        self.artefatti_widgets[slot_ui]["label_art"].config(text="—")

    def _mostra_dps(self, slot_ui):
        aid = self.artefatti_widgets[slot_ui].get("artefatto_id")
        if not aid:
            messagebox.showinfo("Info", "Nessun artefatto equipaggiato.")
            return
        msg = self.service.formato_messaggio_dps(aid)
        messagebox.showinfo("DPS", msg)

    def _apri_inventario(self):
        self._InventarioWindow(self.root, self.service).show()

    def _on_closing(self):
        self.service.close()
        self.root.destroy()

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
                for r in self.service.lista_artefatti_inventario_righe():
                    tree.insert("", "end", values=r)
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
            if MOSTRA_PULSANTE_HOYOLAB:
                tk.Button(r1b, text="Hoyolab", command=lambda: webbrowser.open(self.service.cerca_artefatto_online(q()))).pack(side="left", padx=(0, 5))
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
