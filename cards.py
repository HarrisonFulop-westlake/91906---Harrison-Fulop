import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import requests
import threading

DB_FILE = "cards.db"

class DatabaseManager:
    def __init__(self, db_file : str):
        self.db_file = db_file
        self._init_db()

    def connect(self):
        return sqlite3.connect(self.db_file)
        
    def _init_db(self):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS decks (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    name    TEXT NOT NULL UNIQUE
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    scryfall_id  TEXT,
                    name         TEXT NOT NULL,
                    set_name     TEXT,
                    rarity       TEXT,
                    mana_cost    TEXT,
                    type_line    TEXT,
                    image_uri    TEXT,
                    quantity     INTEGER DEFAULT 1,
                    notes        TEXT,
                    deck_id      INTEGER REFERENCES decks(id) ON DELETE SET NULL
                )
            """)
            conn.commit()
    #Decks

    def add_decks(self, name: str) -> int:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO decks (name) VALUES (?)", (name,))
            conn.commit()
            cur.execute("SELECT id FROM decks WHERE name = ?", (name,))
            return cur.fetchone()[0]
        
    def get_all_decks(self) -> list[tuple]:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM decks ORDER BY name")
            return cur.fetchall()

    def delete_deck(self, deck_id: int):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
            conn.commit()

    #Cards
    
    def add_cards(self, card: dict, deck_id: int | None, quantity: int , notes: str):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO cards 
                    (scryfall_id, name, set_name, rarity, mana_cost, type_line, image_uri, quantity, notes, deck_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,(
                card.get("id"),
                card.get("name"),
                card.get("set_name"),
                card.get("rarity"),
                card.get("mana_cost",""),
                card.get("type_line",""),
                card.get("image_uris",{}).get("small",""),
                quantity,
                notes,
                deck_id,

        ))
        conn.commit()

    def get_cards(self, deck_id: int | None = None, search_term: str= "") -> list[tuple]:
        with self.connect() as conn:
            cur = conn.cursor()
            base = """
                SELECT c.id, c.name, c.set_name, c.rarity, c.mana_cost, 
                    c.type_line, c.quantity, c.notes,
                    COALESCE(d.name, 'No Deck')         
                FROM cards c
                LEFT JOIN decks d ON c.deck_id = d.id
            """
            conditions, params = [], []
            if deck_id is not None:
                conditions.append("c.deck_id = ?")
                params.append(deck_id)
            #Seaching capabilities will go here when I figure it out
            if search_term:
                conditions.append("(c.name LIKE ? OR c.set_name LIKE ?)")
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            if conditions:
                base += " WHERE " + " AND ".join(conditions)
            base += " ORDER BY c.name"
            cur.execute(base, params)
            return cur.fetchall()
        
    def delete_card(self, card_id: int):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM cards WHERE id = ?", (card_id,))
            conn.commit()

    def update_cards(self, card_id: int, quantity: int):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE cards SET quantity = ? WHERE id = ?", (quantity, card_id))
            conn.commit()


class ScryfallAPI:
    @staticmethod
    def search(query: str, callback, error_callback):
        def fetch():
            try:
                headers = {"User-Agent": "MTGCardManager/1.0 (hf22417@my.westlake.school.nz)"}
                response = requests.get(
                    "https://api.scryfall.com/cards/search",
                    params={"q": query, "unique": "cards", "order": "name"},
                    timeout=8,
                    headers=headers
                )
                
                print("URL:", response.url)
                print("Status:", response.status_code)
                print("Body:", response.text)


                if response.status_code == 200:
                    data = response.json()
                    callback(data.get("data", []))

                elif response.status_code == 404:
                    callback([])

                else:
                    error_callback(f"Scryfall Error {response.status_code}")
            except requests.RequestException as exception:
                error_callback(str(exception))

        threading.Thread(target=fetch, daemon=True).start()

    @staticmethod
    def exact_search(name: str, callback, error_callback):
        def fetch():
            try:
                headers = {"User-Agent": "MTGCardManager/1.0 (your_email@example.com)"}
                response = requests.get(
                    "https://api.scryfall.com/cards/named",
                    params={"exact": name},
                    headers=headers
                )
                if response.status_code == 200:
                    callback(response.json())

                else:
                    error_callback(f"Card not found: {name}")
            except requests.RequestException as exception:
                error_callback(str(exception))
                
        threading.Thread(target=fetch, daemon=True).start()

class SearchFrame(ttk.LabelFrame):
    def __init__(self, parent, on_card_selected, **kwargs):
        super().__init__(parent, text="Search Scryfall", **kwargs)
        self.on_card_selected = on_card_selected
        self.api = ScryfallAPI()
        self.results: list[dict] = []
        self.search_job = None
        self.build_ui()
    
    def build_ui(self):
        search_row = ttk.Frame(self)
        search_row.pack(fill = "x", padx=6, pady=(6, 2))

        self.search = tk.StringVar()
        self.search_entry = ttk.Entry(search_row, textvariable=self.search)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", self.on_keyrelease)
        self.search_entry.bind("<Return>", lambda _: self.do_search())

        ttk.Button(search_row, text="Search", command=self.do_search).pack(side="left", padx=(4, 0))

        self.status = tk.StringVar(value="Type a card name...")
        ttk.Label(self, textvariable=self.status, foreground="grey").pack(anchor="w", padx=6)

        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=6, pady=(2,6))

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        self.listbox = tk.Listbox(
            list_frame, 
            yscrollcommand=scrollbar.set, 
            selectmode="browse",
            activestyle="dotbox",
            height=12,
        )
        scrollbar.config(command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        
    def on_keyrelease(self, event):
        if self.search_job:
            self.after_cancel(self.search_job) 
        self.search_job = self.after(600, self.do_search)

    def do_search(self):
        query = self.search.get().strip()
        if not query:
            return
        self.status.set("Searching")
        self.listbox.delete(0, tk.END)
        self.results = []
        self.api.search(query, self.on_results, self.on_error)
        
    def on_results(self, cards: list[dict]):
        self.results = cards
        self.listbox.delete(0, tk.END)
        if not cards:
            self.status.set("No results found.")
            return
        self.status.set(f"{len(cards)} result(s) select one to preview.")
        for c in cards:
            label = f"{c['name']} [{c.get('set_name', '?')}] {c.get('rarity', '')}"
            self.listbox.insert(tk.END, label)
    
    def on_error(self, msg: str):
        self.status.set(f"Error: {msg}")

    def on_select(self, event):
        select = self.listbox.curselection()
        if not select:
            return
        card = self.results[select[0]]
        self.on_card_selected(card)

    
class PreviewFrame(ttk.LabelFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, text="Card Preview", **kwargs)
        self.build_ui()
    
    def build_ui(self):
        self.name = tk.StringVar()
        self.set = tk.StringVar()
        self.rarity = tk.StringVar()
        self.mana = tk.StringVar()
        self.type = tk.StringVar()
        
        fields = [
            ("Name", self.name),
            ("Set", self.set),
            ("Rarity", self.rarity),
            ("Mana Cost", self.mana),
            ("Type", self.type)
        ]
        for num, (label, var) in enumerate(fields):
            ttk.Label(self, text=f"{label}:").grid(row=num, column=0, sticky="w")
            ttk.Label(self, textvariable=var).grid(row=num, column=1, sticky="w")

    def load(self, card: dict):
        self.name.set(card.get("name", ""))
        self.set.set(card.get("set_name", ""))
        self.rarity.set(card.get("rarity", ""))
        self.mana.set(card.get("mana_cost", ""))
        self.type.set(card.get("type_line", ""))

    def clear(self):
        for var in (self.name, self.set, self.rarity, self.mana, self.type):
            var.set("")

class AddToDeckFrame(ttk.LabelFrame):
    def __init__(self, parent, db: DatabaseManager, on_add, **kwargs):
        super().__init__(parent, text="Add to Deck", **kwargs)
        self.db = db
        self.on_add = on_add
        self.selected_card: dict| None = None
        self.build_ui()
        
    def build_ui(self):
        deck_row = ttk.Frame(self)
        deck_row.pack(fill="x")

        ttk.Label(deck_row, text="Deck:").pack(side="left")
        self.deck = tk.StringVar()
        self.deck_combo = ttk.Combobox(deck_row, textvariable = self.deck, state="readonly")
        self.deck_combo.pack(side="left")

        ttk.Button(deck_row, text="New Deck", command=self.new_deck).pack(side="left")
        ttk.Button(deck_row, text="Delete Deck", command=self.delete_deck).pack(side="left")

        opt_row = ttk.Frame(self)
        opt_row.pack(fill="x")

        ttk.Label(opt_row, text="Qty:").pack(side="left")
        self.qty = tk.StringVar(value="1")
        ttk.Spinbox(opt_row, from_=1, to=99, textvariable=self.qty).pack(side="left")

        ttk.Label(opt_row, text="Notes:").pack(side="left")
        self.notes = tk.StringVar()
        ttk.Entry(opt_row, textvariable=self.notes).pack(side="left")

        ttk.Button(self, text="Add Card to Deck", command=self.add).pack()

        self.refresh_decks()
        
    def refresh_decks(self):
        decks = self.db.get_all_decks()
        self.deck_map = {name: did for did, name in decks}
        names = list(self.deck_map.keys())
        self.deck_combo["values"] = names
        if self.deck.get() not in self.deck_map:
            self.deck.set(names[0] if names else "")

    def load_card(self, card: dict):
        self.selected_card = card

    def new_deck(self):
        dialog = InputDialog(self, title="New Deck", prompt="Deck name:")
        name = dialog.result
        if name and name.strip():
            self.db.add_decks(name.strip())
            self.refresh_decks()
            self.deck.set(name.strip())

    def delete_deck(self):
        name = self.deck.get()
        deck_id = self.deck_map.get(name)
        if not name or deck_id is None:
            messagebox.showwarning("No Selection", "Select a valid deck first")
            return
        if messagebox.askyesno("Delete Deck", f"Delete deck'{name}'?\ncards will not be deleted"):
            self.db.delete_deck(deck_id)
            self.refresh_decks()

    def add(self):
        if not self.selected_card:
            messagebox.showwarning("No Card", "Search for and select a card first")
            return
        try:
            qty = int(self.qty.get())
            if qty < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid", "Quantity must be a positive integer.")
            return
        
        deck_name = self.deck.get()
        deck_id = self.deck_map.get(deck_name) if deck_name else None

        self.db.add_cards(self.selected_card, deck_id, qty, self.notes.get())
        self.notes.set("")
        self.qty.set("1")
        self.on_add()

class DeckViewerFrame(ttk.LabelFrame):
    COLUMNS = ("ID", "Name", "Set", "Rarity", "Mana", "Type", "Qty", "Notes", "Deck")

    def __init__(self, parent, db: DatabaseManager, **kwargs):
        super().__init__(parent, text="Collection / Deck View", **kwargs)
        self.db = db
        self.build_ui()

    def build_ui(self):
        # Filter row
        filter_row = ttk.Frame(self)
        filter_row.pack(fill="x", padx=6, pady=(6, 2))

        ttk.Label(filter_row, text="Filter deck:").pack(side="left")
        self.filter_deck = tk.StringVar()
        self.filter_deck_combo = ttk.Combobox(
            filter_row, textvariable=self.filter_deck, state="readonly", width=22
        )
        self.filter_deck_combo.pack(side="left", padx=(4, 12))
        self.filter_deck_combo.bind("<<ComboboxSelected>>", lambda _: self.refresh())

        ttk.Label(filter_row, text="Name search:").pack(side="left")
        self.search = tk.StringVar()
        ttk.Entry(filter_row, textvariable=self.search, width=18).pack(side="left", padx=(4, 8))
        ttk.Button(filter_row, text="Apply", command=self.refresh).pack(side="left")
        ttk.Button(filter_row, text="Clear", command=self.clear_filters).pack(side="left", padx=(4, 0))

        # Treeview
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=6, pady=(2, 2))

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=self.COLUMNS,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
        )
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        col_widths = {"ID": 40, "Name": 160, "Set": 110, "Rarity": 75,
                      "Mana": 70, "Type": 140, "Qty": 40, "Notes": 120, "Deck": 100}
        for col in self.COLUMNS:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by(c))
            self.tree.column(col, width=col_widths.get(col, 90), anchor="w")

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        # Action buttons
        btn_row = ttk.Frame(self)
        btn_row.pack(fill="x", padx=6, pady=(2, 6))
        ttk.Button(btn_row, text="Delete Selected", command=self.delete_selected).pack(side="left")
        ttk.Button(btn_row, text="Refresh", command=self.refresh).pack(side="left", padx=(4, 0))

        self._sort_col = "Name"
        self._sort_asc = True

    def refresh_deck_filter(self, decks: list[tuple]):
        names = ["(All Decks)"] + [name for _, name in decks]
        self.deck_filter_map = {"(All Decks)": None}
        self.deck_filter_map.update({name: did for did, name in decks})
        self.filter_deck_combo["values"] = names
        if not self.filter_deck.get():
            self.filter_deck.set("(All Decks)")

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        deck_name = self.filter_deck.get()
        deck_id = self.deck_filter_map.get(deck_name) if hasattr(self, "deck_filter_map") else None
        cards = self.db.get_cards(deck_id=deck_id, search_term=self.search.get())
        for card in cards:
            self.tree.insert("", tk.END, values=card)

    def clear_filters(self):
        self.filter_deck.set("(All Decks)")
        self.search.set("")
        self.refresh()

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Select a card to delete.")
            return
        if not messagebox.askyesno("Delete", f"Delete {len(selected)} card(s)?"):
            return
        for sel in selected:
            card_id = self.tree.item(sel)["values"][0]
            self.db.delete_card(card_id)
        self.refresh()

    def sort_by(self, col: str):
        self._sort_asc = not self._sort_asc if self._sort_col == col else True
        self._sort_col = col
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        items.sort(reverse=not self._sort_asc)
        for idx, (_, k) in enumerate(items):
            self.tree.move(k, "", idx)
    
class InputDialog(tk.Toplevel):
    def __init__(self, parent, title: str, prompt: str):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.result: str | None = None

        ttk.Label(self, text=prompt).pack(padx=20, pady=(16, 4))
        self.var = tk.StringVar()
        entry = ttk.Entry(self, textvariable=self.var, width=28)
        entry.pack(padx=20)
        entry.focus()
        entry.bind("<Return>", lambda _: self.ok())

        btn_row = ttk.Frame(self)
        btn_row.pack(pady=12)
        ttk.Button(btn_row, text="OK", command=self.ok).pack(side="left", padx=6)
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side="left")

        self.wait_window()

    def ok(self):
        self.result = self.var.get()
        self.destroy()

class CardManagerApp:
    def __init__(self):
        self.db = DatabaseManager(DB_FILE)
        self.root = tk.Tk()
        self.root.title("MTG Card Manager")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        self._selected_card: dict | None = None
        self.build_ui()
        self.full_refresh()

    def build_ui(self):
        # Top pane: search (left) | preview + add-form (right)
        top = ttk.PanedWindow(self.root, orient="horizontal")
        top.pack(fill="both", expand=False, padx=8, pady=8)

        self.search_frame = SearchFrame(
            top,
            on_card_selected=self.on_card_selected,
            width=420,
        )
        top.add(self.search_frame, weight=2)

        right_top = ttk.Frame(top)
        top.add(right_top, weight=3)

        self.preview_frame = PreviewFrame(right_top)
        self.preview_frame.pack(fill="x", padx=4, pady=(0, 4))

        self.add_frame = AddToDeckFrame(right_top, db=self.db, on_add=self.on_card_added)
        self.add_frame.pack(fill="x", padx=4)

        # Bottom pane: deck viewer
        self.deck_viewer = DeckViewerFrame(self.root, db=self.db)
        self.deck_viewer.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    
    def on_card_selected(self, card: dict):
        self.selected_card = card
        self.preview_frame.load(card)
        self.add_frame.load_card(card)

    def on_card_added(self):
        self.full_refresh()

    def full_refresh(self):
        decks = self.db.get_all_decks()
        self.add_frame.refresh_decks()
        self.deck_viewer.refresh_deck_filter(decks)
        self.deck_viewer.refresh()

    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = CardManagerApp()
    app.run()
