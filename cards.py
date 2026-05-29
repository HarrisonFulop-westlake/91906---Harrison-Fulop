import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

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

    def add_decks(self, name):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO DECKS (name) VALUES (?)", (name,))
            cur.execute("SELECT id FROM decks WHERE name = ?", (name,))
            return cur.fetchone()
        
    def get_all_decks():
        pass

    def delete_decks():
        pass

class ScryfallAPI:
    pass

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