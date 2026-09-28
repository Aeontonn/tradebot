# Tradebot

Paper trading bot (fake money) for forex and stocks with a full transaction log,
risk rules, Telegram notifications and a yearly export in SEK for the Swedish tax return.

Starting capital in the simulation: 500 SEK forex + 500 SEK stocks (change in `config.py`).

## Getting started

```bash
python -m venv .venv
source .venv/Scripts/activate    # Git Bash on Windows. Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # fill in Telegram if you want notifications
python main.py once              # run one cycle
python main.py run               # run in a loop
```

## Commands

| Command | What it does |
|---|---|
| `python main.py once` | One cycle: fetches prices, makes decisions, logs |
| `python main.py run` | Loop, one cycle per hour + daily summary at 22:00 |
| `python main.py summary` | Shows balance and open positions |
| `python main.py report --year 2026` | Creates `exports/trades_2026.csv` and `exports/summary_2026.txt` |
| `python tests/test_offline.py` | Offline tests, no network needed |

## What is logged

Everything goes into SQLite (`data/tradebot.db`): every trade (date, symbol, quantity, price,
fee, currency, exchange rate to SEK, order id), every decision with its reason,
and the equity curve over time.

## How signals work

The strategy is a moving average crossover (MA10/MA30) on daily closing prices.
Only completed daily bars are used for the signal, since today's bar keeps changing.
The same signal can only open a position once, so a stop-loss is not followed by an
immediate rebuy on the same crossover.

## Safety

- Stop-loss 5 % per position, max 50 % of the capital per position.
- Daily loss limit (10 %) and total loss limit (30 %).
- Kill switch: create an empty file called `STOP` in the project folder and the bot stops trading.
- API keys live in `.env`, which is ignored by git.

## Before real money

Run on paper for 4-8 weeks. Then replace `PaperBroker` with a real broker class
(OANDA, Interactive Brokers) with the same methods. Check the broker's terms for Swedish customers.

This is a hobby project and not financial advice. Most home-built bots lose money.
