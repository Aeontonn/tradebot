"""Tradebot: paper trading with logging, risk rules and reports.

Commands:
    python main.py once             run one cycle and exit
    python main.py run              run in a loop (every CHECK_INTERVAL_MINUTES minutes)
    python main.py summary          print the daily summary in the terminal
    python main.py report --year 2026   create CSV and summary for the tax return
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
        print("Kill switch active (the file STOP exists). Skipping this cycle.")
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
                    db.log_decision(conn, symbol, "blocked", f"data error: {exc}")
                    print(f"{symbol}: data error {exc}")
                    continue

                # The latest price is used for stop-loss and fills,
                # but the signal only looks at completed daily bars.
                price = float(close.iloc[-1])
                prices[symbol] = (price, fx)
                pos = db.get_position(conn, symbol)

                # Stop-loss first
                if pos is not None and price <= pos["stop_price"]:
                    res = paper.sell(conn, symbol, price, fx, reason="stop-loss")
                    db.log_decision(conn, symbol, "sell", "stop-loss")
                    notify.send(f"STOP-LOSS: sold {symbol} for {res['value_sek']:.0f} SEK "
                                f"(result {res['realized_pl_sek']:+.1f} SEK)")
                    continue

                bars = strategy.completed_bars(close)
                bar_date = bars.index[-1].date().isoformat()
                signal, note = strategy.signal_for(bars)
                note = f"{note} (bar {bar_date})"

                if signal == "buy" and pos is None:
                    if risk.already_acted_on_bar(conn, symbol, bar_date):
                        db.log_decision(conn, symbol, "hold", f"{note}, already traded on this signal")
                        continue
                    cash = db.get_cash(conn, market_name)
                    notional = brk.buy_notional(market_name, cash)
                    ok, why = risk.check_can_buy(conn, market_name, notional, cash, lev)
                    if not ok:
                        db.log_decision(conn, symbol, "blocked", why)
                        print(f"{symbol}: buy blocked ({why})")
                        continue
                    res = paper.buy(conn, market_name, symbol, price, currency, fx, reason=note)
                    if res:
                        db.log_decision(conn, symbol, "buy", note)
                        notify.send(f"BOUGHT {symbol}: {res['qty']:.4f} units, {res['value_sek']:.0f} SEK ({note})")
                elif signal == "sell" and pos is not None:
                    res = paper.sell(conn, symbol, price, fx, reason=note)
                    db.log_decision(conn, symbol, "sell", note)
                    notify.send(f"SOLD {symbol} for {res['value_sek']:.0f} SEK "
                                f"(result {res['realized_pl_sek']:+.1f} SEK, {note})")
                else:
                    db.log_decision(conn, symbol, "hold", note)

        # Equity curve per part
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
            notify.send("Total loss limit reached. The bot will not buy anything more. "
                        "Create/remove the file STOP to control it manually.")


def loop():
    tz = ZoneInfo("Europe/Stockholm")
    last_summary_date = None
    while True:
        try:
            run_cycle()
        except Exception as exc:
            notify.send(f"Error in the bot: {exc}")

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
        print(f"Saved {csv_path} and {summary_path}")


if __name__ == "__main__":
    main()
