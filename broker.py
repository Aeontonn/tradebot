"""Paper-mäklare: simulerar affärer med spread och avgift, och loggar allt i databasen.

För att byta till en riktig mäklare (OANDA, Interactive Brokers) skriver du en klass
med samma metoder (buy, sell) som lägger riktiga ordrar och loggar dem på samma sätt.
"""
import uuid

import config
import db


def leverage_for(market):
    return config.MAX_LEVERAGE if market == "forex" else 1.0


class PaperBroker:
    def buy(self, conn, market, symbol, price, currency, fx, reason=""):
        lev = leverage_for(market)
        cash = db.get_cash(conn, market)

        target_notional = config.START_CAPITAL_SEK[market] * config.MAX_POSITION_FRACTION * lev
        notional_sek = min(target_notional, cash * lev)
        fill_price = price * (1 + config.SPREAD_PCT)
        qty = notional_sek / (fill_price * fx)
        if qty <= 0:
            return None

        notional_sek = qty * fill_price * fx
        margin = notional_sek / lev
        fee_sek = config.FEE_PER_TRADE_SEK
        fee = fee_sek / fx
        avg_cost_sek = (notional_sek + fee_sek) / qty
        order_id = f"paper-{uuid.uuid4().hex[:10]}"
        ts = db.now_iso()

        conn.execute(
            "INSERT INTO trades (ts, market, symbol, side, qty, price, currency, fee, fx_to_sek, "
            "value_sek, fee_sek, realized_pl_sek, order_id, reason) "
            "VALUES (?, ?, ?, 'buy', ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)",
            (ts, market, symbol, qty, fill_price, currency, fee, fx, notional_sek, fee_sek, order_id, reason),
        )
        conn.execute(
            "INSERT INTO positions (symbol, market, qty, margin_sek, avg_cost_sek, avg_price, currency, "
            "stop_price, opened_ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol, market, qty, margin, avg_cost_sek, fill_price, currency,
             fill_price * (1 - config.STOP_LOSS_PCT), ts),
        )
        db.set_cash(conn, market, cash - margin - fee_sek)
        return {"symbol": symbol, "side": "buy", "qty": qty, "price": fill_price, "value_sek": notional_sek}

    def sell(self, conn, symbol, price, fx, reason=""):
        pos = db.get_position(conn, symbol)
        if pos is None:
            return None

        market = pos["market"]
        lev = leverage_for(market)
        qty = pos["qty"]
        fill_price = price * (1 - config.SPREAD_PCT)
        proceeds_sek = qty * fill_price * fx
        fee_sek = config.FEE_PER_TRADE_SEK
        fee = fee_sek / fx

        realized = proceeds_sek - fee_sek - qty * pos["avg_cost_sek"]
        cost_notional = pos["margin_sek"] * lev
        cash_back = pos["margin_sek"] + (proceeds_sek - cost_notional) - fee_sek
        order_id = f"paper-{uuid.uuid4().hex[:10]}"

        conn.execute(
            "INSERT INTO trades (ts, market, symbol, side, qty, price, currency, fee, fx_to_sek, "
            "value_sek, fee_sek, realized_pl_sek, order_id, reason) "
            "VALUES (?, ?, ?, 'sell', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (db.now_iso(), market, symbol, qty, fill_price, pos["currency"], fee, fx,
             proceeds_sek, fee_sek, realized, order_id, reason),
        )
        conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
        db.set_cash(conn, market, db.get_cash(conn, market) + cash_back)
        return {"symbol": symbol, "side": "sell", "qty": qty, "price": fill_price,
                "value_sek": proceeds_sek, "realized_pl_sek": realized}


def position_value_sek(pos, price, fx):
    """Positionens nuvarande värde i SEK (bunden kassa + orealiserad vinst/förlust)."""
    lev = leverage_for(pos["market"])
    notional_now = pos["qty"] * price * fx
    cost_notional = pos["margin_sek"] * lev
    return pos["margin_sek"] + (notional_now - cost_notional)
