"""SQLite-logg. Alla affärer, beslut och kapitalkurva sparas här."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    market TEXT NOT NULL,            -- 'forex' eller 'stocks'
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,              -- 'buy' eller 'sell'
    qty REAL NOT NULL,
    price REAL NOT NULL,             -- pris per styck i handelsvalutan
    currency TEXT NOT NULL,
    fee REAL NOT NULL DEFAULT 0,     -- avgift i handelsvalutan
    fx_to_sek REAL NOT NULL,         -- växelkurs handelsvaluta -> SEK vid affären
    value_sek REAL NOT NULL,         -- qty * price * fx_to_sek
    fee_sek REAL NOT NULL DEFAULT 0,
    realized_pl_sek REAL,            -- fylls i vid sälj (genomsnittsmetoden)
    order_id TEXT,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY,
    market TEXT NOT NULL,
    qty REAL NOT NULL,
    margin_sek REAL NOT NULL,        -- bunden kassa (positionens värde / hävstång)
    avg_cost_sek REAL NOT NULL,      -- snittkostnad per styck i SEK, inkl. avgift
    avg_price REAL NOT NULL,         -- snittpris per styck i handelsvalutan
    currency TEXT NOT NULL,
    stop_price REAL,
    opened_ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    symbol TEXT NOT NULL,
    signal TEXT NOT NULL,            -- 'buy', 'sell', 'hold', 'blocked'
    note TEXT
);

CREATE TABLE IF NOT EXISTS equity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    market TEXT NOT NULL,
    cash_sek REAL NOT NULL,
    equity_sek REAL NOT NULL         -- kassa + värde av öppna positioner
);

CREATE TABLE IF NOT EXISTS cash (
    market TEXT PRIMARY KEY,
    cash_sek REAL NOT NULL
);
"""


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect(path=None):
    path = path or config.DB_PATH
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path=None):
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        for market, amount in config.START_CAPITAL_SEK.items():
            conn.execute(
                "INSERT OR IGNORE INTO cash (market, cash_sek) VALUES (?, ?)",
                (market, amount),
            )


def log_decision(conn, symbol, signal, note=""):
    conn.execute(
        "INSERT INTO decisions (ts, symbol, signal, note) VALUES (?, ?, ?, ?)",
        (now_iso(), symbol, signal, note),
    )


def log_equity(conn, market, cash_sek, equity_sek):
    conn.execute(
        "INSERT INTO equity (ts, market, cash_sek, equity_sek) VALUES (?, ?, ?, ?)",
        (now_iso(), market, cash_sek, equity_sek),
    )


def get_cash(conn, market):
    row = conn.execute("SELECT cash_sek FROM cash WHERE market = ?", (market,)).fetchone()
    return row["cash_sek"] if row else 0.0


def set_cash(conn, market, amount):
    conn.execute(
        "INSERT INTO cash (market, cash_sek) VALUES (?, ?) "
        "ON CONFLICT(market) DO UPDATE SET cash_sek = excluded.cash_sek",
        (market, amount),
    )


def get_position(conn, symbol):
    return conn.execute("SELECT * FROM positions WHERE symbol = ?", (symbol,)).fetchone()


def all_positions(conn):
    return conn.execute("SELECT * FROM positions").fetchall()
