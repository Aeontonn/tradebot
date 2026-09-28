"""Risk rules. Every buy goes through here before it may be placed."""
import os
from datetime import datetime, timezone

import config
import db


def kill_switch_active():
    return os.path.exists(config.KILL_SWITCH_FILE)


def total_start_capital():
    return sum(config.START_CAPITAL_SEK.values())


def total_equity(conn):
    row = conn.execute(
        "SELECT market, equity_sek FROM equity WHERE id IN "
        "(SELECT MAX(id) FROM equity GROUP BY market)"
    ).fetchall()
    if not row:
        return total_start_capital()
    return sum(r["equity_sek"] for r in row)


def daily_start_equity(conn):
    today = datetime.now(timezone.utc).date().isoformat()
    rows = conn.execute(
        "SELECT market, equity_sek FROM equity WHERE id IN "
        "(SELECT MIN(id) FROM equity WHERE ts >= ? GROUP BY market)",
        (today,),
    ).fetchall()
    if not rows:
        return None
    return sum(r["equity_sek"] for r in rows)


def already_acted_on_bar(conn, symbol, bar_date):
    """True if we have traded the symbol on or after the date of the signal bar.

    A crossover on one bar stays visible until the next bar exists, so the hourly
    loop sees the same signal many times. This stops a new buy on the same signal,
    for example right after a stop-loss sold the position.
    """
    last = db.last_trade_ts(conn, symbol)
    return last is not None and last[:10] >= bar_date


def check_can_buy(conn, market, notional_sek, cash_sek, leverage):
    """Returns (ok, reason)."""
    if kill_switch_active():
        return False, "kill switch active"

    start = total_start_capital()
    equity = total_equity(conn)
    if equity <= start * (1 - config.MAX_TOTAL_LOSS_PCT):
        return False, "total loss limit reached, bot is stopped"

    day_start = daily_start_equity(conn)
    if day_start and equity <= day_start * (1 - config.MAX_DAILY_LOSS_PCT):
        return False, "daily loss limit reached"

    if notional_sek <= 0:
        return False, "not enough cash"

    market_capital = config.START_CAPITAL_SEK[market]
    max_notional = market_capital * config.MAX_POSITION_FRACTION * leverage
    if notional_sek > max_notional + 1e-9:
        return False, f"position {notional_sek:.0f} SEK above max {max_notional:.0f} SEK"

    margin = notional_sek / leverage
    if margin + config.FEE_PER_TRADE_SEK > cash_sek + 1e-9:
        return False, "not enough cash"

    return True, "ok"


def stop_price_for(entry_price):
    return entry_price * (1 - config.STOP_LOSS_PCT)
