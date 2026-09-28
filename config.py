"""Inställningar för boten. Ändra här, inte i resten av koden."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Vad boten får handla (Yahoo Finance-symboler)
FOREX_SYMBOLS = ["EURUSD=X", "USDSEK=X"]
STOCK_SYMBOLS = ["AAPL", "MSFT", "NVDA", "ASML"]

# Kapital i SEK, uppdelat på de två delarna
START_CAPITAL_SEK = {"forex": 500.0, "stocks": 500.0}

# Riskregler
MAX_POSITION_FRACTION = 0.5     # max 50 % av delens kapital i en enskild position
MAX_LEVERAGE = 2.0              # max hävstång på forex
STOP_LOSS_PCT = 0.05            # 5 % stop-loss per position
MAX_DAILY_LOSS_PCT = 0.10       # stoppa handel resten av dagen vid -10 %
MAX_TOTAL_LOSS_PCT = 0.30       # stoppa boten helt vid -30 % totalt

# Strategi (moving average crossover)
FAST_MA = 10
SLOW_MA = 30

# Kostnader i paper-läge (för realistiska resultat)
FEE_PER_TRADE_SEK = 1.0
SPREAD_PCT = 0.0005             # 0,05 %

# Filer
DB_PATH = os.getenv("DB_PATH", "data/tradebot.db")
KILL_SWITCH_FILE = "STOP"       # skapa en fil med detta namn för att stoppa boten

# Telegram (valfritt)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Loop
CHECK_INTERVAL_MINUTES = 60
