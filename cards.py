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
    #Decks

    def add_decks(self, name):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO DECKS (name) VALUES (?)", (name,))
            cur.execute("SELECT id FROM decks WHERE name = ?", (name,))
            return cur.fetchone()
        
    def get_all_decks(self):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM decks ORDER BY name")
            return cur.fetchall()

    def delete_decks(self, deck_id: int):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM decks WHERE id = ?", (deck_id,))

    #Cards
    
    def add_cards(self, card: dict, deck_id: int | None, quantity: int , notes: str):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO cards 
                    (scryfall_id, name, set_name, rarity, mana_cost, type_line image_uri, quantity, notes, deck_id)
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

    def get_cards(self, deck_id: int |None = None):
        with self.connect() as conn:
            cur = conn.cursor()
            base = """
                SELECT c.id, c.name, c.set_name, c.rarity, c.mana_cost, c.type_line, c.quantity, c.notes,

                COALESCE(d.name, 'No Deck') 
                
                FROM cards c
                LEFT JOIN decks d ON c.deck_id = d.id
            """
            conditions, params = [], []
            if deck_id is not None:
                conditions.append("c.deck_id = ?")
                params.append(deck_id)
            #Seaching capabilities will go here when I figure it out
            base += "ORDER BY c.name"
            cur.execute(base, params)
            return cur.fetchall()
        
    def delete_cards(self, card_id: int):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM cards WHERE id = ?", (card_id))

    def update_cards(self, card_id: int, quantity: int):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE cards SET quantity = ? WHERE id = ?", (quantity, card_id))
        


class ScryfallAPI:
    @staticmethod
    def search(query: str, callback, error_callback):
        def fetch():
            try:
                response = requests.get(
                    SCRYFALL_SEARCH_URL,
                    params={"q": query, "unique" : "cards", "order" : "name"},
                )

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
                response = requests.get(
                    SCRYFALL_NAMED_URL,
                    params={"exact": name}
                )
                if response.status_code == 200:
                    callback(response.json())

                else:
                    error_callback(f"Card not found: {name}")
            except requests.RequestException as exception:
                error_callback(str(exception))
                
        threading.Thread(target=fetch, daemon=True).start()

class SearchFrame:
    pass

class PreviewFrame:
    pass

class AddToDeckFrame:
    pass

class DeckViewrFrame:
    pass

if __name__ == "__main__":
    db = DatabaseManager("cards.db")