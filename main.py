"""Tradebot: paper trading med logg, riskregler och rapporter.

Kommandon:
    python main.py once             kör en runda och avslutar
    python main.py run              kör i loop (var CHECK_INTERVAL_MINUTES minut)
    python main.py summary          skriver dagssammanfattning i terminalen
    python main.py report --year 2026   skapar CSV och sammanfattning för deklarationen
"""
import argparse
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import broker as brk
import config
import db
import market as mkt
import notify
import report
import risk
import strategy

SYMBOLS = {"forex": config.FOREX_SYMBOLS, "stocks": config.STOCK_SYMBOLS}


def run_cycle(paper=None):
    paper = paper or brk.PaperBroker()

    if risk.kill_switch_active():
        print("Kill switch aktiv (filen STOP finns). Hoppar över rundan.")
        return

    with db.connect() as conn:
        prices = {}
        for market_name, symbols in SYMBOLS.items():
            lev = brk.leverage_for(market_name)
            for symbol in symbols:
                try:
                    close = mkt.get_history(symbol)
                    currency = mkt.currency_of(symbol)
                    fx = mkt.fx_to_sek(currency)
                except Exception as exc:
                    db.log_decision(conn, symbol, "blocked", f"datafel: {exc}")
                    print(f"{symbol}: datafel {exc}")
                    continue

                price = float(close.iloc[-1])
                prices[symbol] = (price, fx)
                pos = db.get_position(conn, symbol)

                # Stop-loss först
                if pos is not None and price <= pos["stop_price"]:
                    res = paper.sell(conn, symbol, price, fx, reason="stop-loss")
                    db.log_decision(conn, symbol, "sell", "stop-loss")
                    notify.send(f"STOP-LOSS: sålde {symbol} för {res['value_sek']:.0f} kr "
                                f"(resultat {res['realized_pl_sek']:+.1f} kr)")
                    continue

                signal, note = strategy.signal_for(close)

                if signal == "buy" and pos is None:
                    cash = db.get_cash(conn, market_name)
                    target = config.START_CAPITAL_SEK[market_name] * config.MAX_POSITION_FRACTION * lev
                    notional = min(target, cash * lev)
                    ok, why = risk.check_can_buy(conn, market_name, notional, cash, lev)
                    if not ok:
                        db.log_decision(conn, symbol, "blocked", why)
                        print(f"{symbol}: köp blockerat ({why})")
                        continue
                    res = paper.buy(conn, market_name, symbol, price, currency, fx, reason=note)
                    if res:
                        db.log_decision(conn, symbol, "buy", note)
                        notify.send(f"KÖPTE {symbol}: {res['qty']:.4f} st, {res['value_sek']:.0f} kr ({note})")
                elif signal == "sell" and pos is not None:
                    res = paper.sell(conn, symbol, price, fx, reason=note)
                    db.log_decision(conn, symbol, "sell", note)
                    notify.send(f"SÅLDE {symbol} för {res['value_sek']:.0f} kr "
                                f"(resultat {res['realized_pl_sek']:+.1f} kr, {note})")
                else:
                    db.log_decision(conn, symbol, "hold", note)

        # Kapitalkurva per del
        for market_name in SYMBOLS:
            cash = db.get_cash(conn, market_name)
            equity = cash
            for pos in db.all_positions(conn):
                if pos["market"] != market_name:
                    continue
                if pos["symbol"] in prices:
                    p, fx = prices[pos["symbol"]]
                else:
                    p, fx = pos["avg_price"], mkt.fx_to_sek(pos["currency"])
                equity += brk.position_value_sek(pos, p, fx)
            db.log_equity(conn, market_name, cash, equity)

        total = risk.total_equity(conn)
        if total <= risk.total_start_capital() * (1 - config.MAX_TOTAL_LOSS_PCT):
            notify.send("Total förlustgräns nådd. Boten köper inte mer. Skapa/ta bort filen STOP för att styra manuellt.")


def loop():
    tz = ZoneInfo("Europe/Stockholm")
    last_summary_date = None
    while True:
        try:
            run_cycle()
        except Exception as exc:
            notify.send(f"Fel i boten: {exc}")

        now = datetime.now(tz)
        if now.hour >= 22 and last_summary_date != now.date():
            with db.connect() as conn:
                notify.send(report.daily_summary(conn))
            last_summary_date = now.date()

        time.sleep(config.CHECK_INTERVAL_MINUTES * 60)


def main():
    parser = argparse.ArgumentParser(description="Tradebot (paper trading)")
    parser.add_argument("command", choices=["once", "run", "summary", "report"])
    parser.add_argument("--year", type=int, default=datetime.now().year)
    args = parser.parse_args()

    db.init_db()

    if args.command == "once":
        run_cycle()
    elif args.command == "run":
        loop()
    elif args.command == "summary":
        with db.connect() as conn:
            print(report.daily_summary(conn))
    elif args.command == "report":
        csv_path, summary_path, text = report.export_year(args.year)
        print(text)
        print(f"Sparade {csv_path} och {summary_path}")


if __name__ == "__main__":
    main()
