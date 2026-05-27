import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

DB_FILE = "cards.db"

class DatabaseManager:
    def __init__(self, db_file):
        self.db_file = db_file
        
    def connect(self):
        return sqlite3.connect(self.db_file)
        
    def __init__db(self):
        with self.connect() as conn:
            cur = conn.cursor()

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
