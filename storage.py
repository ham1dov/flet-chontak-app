import json
import logging
from pathlib import Path

import flet as ft


log = logging.getLogger(f"app.{__name__}")
LEGACY_STATE_KEY = "chontak_local_state_v1"


class PreferencesStorage:
    """Browser-compatible storage used by the Flet web preview and web builds."""

    def __init__(self, preferences):
        self.preferences = preferences

    async def load_state(self):
        raw = await self.preferences.get(LEGACY_STATE_KEY)
        if not raw:
            return None
        try:
            state = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            log.warning("Saved browser state could not be decoded")
            return None
        return state if isinstance(state, dict) else None

    async def save_state(self, state):
        await self.preferences.set(
            LEGACY_STATE_KEY,
            json.dumps(state, ensure_ascii=False),
        )


class SQLiteStorage:
    """Persistent SQLite storage for native desktop and mobile builds."""

    def __init__(self, database_path):
        import sqlite3

        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self):
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS categories (
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                position INTEGER NOT NULL,
                PRIMARY KEY (kind, name)
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                payment TEXT NOT NULL,
                category TEXT NOT NULL,
                note TEXT NOT NULL,
                transaction_date TEXT NOT NULL,
                position INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS exchange_rates (
                currency TEXT PRIMARY KEY,
                rate REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    async def load_state(self):
        settings_rows = self.connection.execute(
            "SELECT key, value FROM settings"
        ).fetchall()
        transaction_rows = self.connection.execute(
            "SELECT id, kind, amount, currency, payment, category, note, transaction_date "
            "FROM transactions ORDER BY position"
        ).fetchall()
        if not settings_rows and not transaction_rows:
            return None

        categories = {"Expense": [], "Income": []}
        for row in self.connection.execute(
            "SELECT kind, name FROM categories ORDER BY kind, position"
        ):
            categories.setdefault(row["kind"], []).append(row["name"])
        rates = {
            row["currency"]: row["rate"]
            for row in self.connection.execute("SELECT currency, rate FROM exchange_rates")
        }
        metadata = {
            row["key"]: row["value"]
            for row in self.connection.execute("SELECT key, value FROM metadata")
        }
        return {
            "settings": {row["key"]: row["value"] for row in settings_rows},
            "categories": categories,
            "transactions": [
                {
                    "id": row["id"],
                    "kind": row["kind"],
                    "amount": row["amount"],
                    "currency": row["currency"],
                    "payment": row["payment"],
                    "category": row["category"],
                    "note": row["note"],
                    "date": row["transaction_date"],
                }
                for row in transaction_rows
            ],
            "rates": rates,
            "rates_updated_at": metadata.get("rates_updated_at", ""),
        }

    async def save_state(self, state):
        with self.connection:
            self.connection.execute("DELETE FROM settings")
            self.connection.execute("DELETE FROM categories")
            self.connection.execute("DELETE FROM transactions")
            self.connection.execute("DELETE FROM exchange_rates")
            self.connection.execute("DELETE FROM metadata")

            self.connection.executemany(
                "INSERT INTO settings(key, value) VALUES (?, ?)",
                [(key, str(value)) for key, value in state.get("settings", {}).items()],
            )
            category_rows = [
                (kind, name, position)
                for kind, names in state.get("categories", {}).items()
                for position, name in enumerate(names)
            ]
            self.connection.executemany(
                "INSERT INTO categories(kind, name, position) VALUES (?, ?, ?)",
                category_rows,
            )
            transaction_rows = [
                (
                    item["id"], item["kind"], float(item["amount"]), item["currency"],
                    item["payment"], item["category"], item.get("note", ""),
                    item["date"], position,
                )
                for position, item in enumerate(state.get("transactions", []))
            ]
            self.connection.executemany(
                """INSERT INTO transactions(
                    id, kind, amount, currency, payment, category, note, transaction_date, position
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                transaction_rows,
            )
            self.connection.executemany(
                "INSERT INTO exchange_rates(currency, rate) VALUES (?, ?)",
                [(currency, float(rate)) for currency, rate in state.get("rates", {}).items()],
            )
            if state.get("rates_updated_at"):
                self.connection.execute(
                    "INSERT INTO metadata(key, value) VALUES (?, ?)",
                    ("rates_updated_at", str(state["rates_updated_at"])),
                )


async def create_storage(page):
    preferences = ft.SharedPreferences()
    if page.web:
        log.info("Using browser persistence for web preview/web builds")
        return PreferencesStorage(preferences)

    storage_paths = ft.StoragePaths()
    support_directory = await storage_paths.get_application_support_directory()
    Path(support_directory).mkdir(parents=True, exist_ok=True)
    database_path = str(Path(support_directory) / "chontak.sqlite3")
    store = SQLiteStorage(database_path)

    # Import existing local preferences once when the SQLite database is first created.
    if await store.load_state() is None:
        raw = await preferences.get(LEGACY_STATE_KEY)
        if raw:
            try:
                legacy_state = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                legacy_state = None
            if isinstance(legacy_state, dict):
                await store.save_state(legacy_state)
                await preferences.remove(LEGACY_STATE_KEY)
                log.info("Migrated saved finance data into SQLite")
    log.info("Using SQLite database at %s", database_path)
    return store
