"""Bot settings. Change things here, not in the rest of the code."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# What the bot may trade (Yahoo Finance symbols)
FOREX_SYMBOLS = ["EURUSD=X", "USDSEK=X"]
STOCK_SYMBOLS = ["AAPL", "MSFT", "NVDA", "ASML"]

# Capital in SEK, split into two parts
START_CAPITAL_SEK = {"forex": 500.0, "stocks": 500.0}

# Risk rules
MAX_POSITION_FRACTION = 0.5     # max 50 % of the part's capital in a single position
MAX_LEVERAGE = 2.0              # max leverage on forex
STOP_LOSS_PCT = 0.05            # 5 % stop-loss per position
MAX_DAILY_LOSS_PCT = 0.10       # stop trading for the rest of the day at -10 %
MAX_TOTAL_LOSS_PCT = 0.30       # stop the bot completely at -30 % total

# Strategy (moving average crossover)
FAST_MA = 10
SLOW_MA = 30

# Costs in paper mode (for realistic results)
FEE_PER_TRADE_SEK = 1.0
SPREAD_PCT = 0.0005             # 0.05 %

# Files
DB_PATH = os.getenv("DB_PATH", "data/tradebot.db")
KILL_SWITCH_FILE = "STOP"       # create a file with this name to stop the bot

# Telegram (optional)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Loop
CHECK_INTERVAL_MINUTES = 60
