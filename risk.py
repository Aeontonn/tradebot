"""Riskregler. Alla köp går igenom här innan de får läggas."""
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


def check_can_buy(conn, market, notional_sek, cash_sek, leverage):
    """Returnerar (ok, anledning)."""
    if kill_switch_active():
        return False, "kill switch aktiv"

    start = total_start_capital()
    equity = total_equity(conn)
    if equity <= start * (1 - config.MAX_TOTAL_LOSS_PCT):
        return False, "total förlustgräns nådd, boten är stoppad"

    day_start = daily_start_equity(conn)
    if day_start and equity <= day_start * (1 - config.MAX_DAILY_LOSS_PCT):
        return False, "daglig förlustgräns nådd"

    market_capital = config.START_CAPITAL_SEK[market]
    max_notional = market_capital * config.MAX_POSITION_FRACTION * leverage
    if notional_sek > max_notional + 1e-9:
        return False, f"position {notional_sek:.0f} SEK över max {max_notional:.0f} SEK"

    margin = notional_sek / leverage
    if margin > cash_sek:
        return False, "inte tillräckligt med kassa"

    return True, "ok"


def stop_price_for(entry_price):
    return entry_price * (1 - config.STOP_LOSS_PCT)
