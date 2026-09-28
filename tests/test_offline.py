"""Offline tests: no network needed. Run with: python tests/test_offline.py"""
import os
import sys
import tempfile
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import broker as brk
import config
import db
import report
import risk
import strategy


def approx(a, b, tol=0.01):
    return abs(a - b) <= tol


def test_broker_and_risk(path):
    paper = brk.PaperBroker()
    with db.connect(path) as conn:
        # Stock: buy and sell at a profit, USD -> SEK
        b = paper.buy(conn, "stocks", "AAPL", 200.0, "USD", 10.0, reason="test")
        assert b is not None
        assert db.get_position(conn, "AAPL") is not None
        s = paper.sell(conn, "AAPL", 220.0, 10.0, reason="test")
        cash = db.get_cash(conn, "stocks")
        expected = config.START_CAPITAL_SEK["stocks"] + s["realized_pl_sek"]
        assert approx(cash, expected), (cash, expected)
        assert s["realized_pl_sek"] > 0
        assert db.get_position(conn, "AAPL") is None

        # Forex with leverage: buy and sell at a loss
        paper.buy(conn, "forex", "EURUSD=X", 1.10, "USD", 10.0, reason="test")
        pos = db.get_position(conn, "EURUSD=X")
        assert pos is not None
        assert approx(brk.position_value_sek(pos, 1.10, 10.0), pos["margin_sek"], 1.5)
        f = paper.sell(conn, "EURUSD=X", 1.05, 10.0, reason="test")
        cash = db.get_cash(conn, "forex")
        expected = config.START_CAPITAL_SEK["forex"] + f["realized_pl_sek"]
        assert approx(cash, expected), (cash, expected)
        assert f["realized_pl_sek"] < 0

        # Risk rules
        ok, why = risk.check_can_buy(conn, "stocks", 10_000, 500, 1.0)
        assert not ok, why
        ok, why = risk.check_can_buy(conn, "stocks", 200, 500, 1.0)
        assert ok, why

        # Total loss limit
        db.log_equity(conn, "stocks", 100, 100)
        db.log_equity(conn, "forex", 100, 100)
        ok, why = risk.check_can_buy(conn, "stocks", 200, 500, 1.0)
        assert not ok and "loss" in why


def test_cash_never_negative():
    """Buying until the cash runs out must never leave negative cash."""
    path = os.path.join(tempfile.mkdtemp(), "cash.db")
    db.init_db(path)
    paper = brk.PaperBroker()
    with db.connect(path) as conn:
        for symbol in ["AAPL", "MSFT", "NVDA", "ASML"]:
            cash = db.get_cash(conn, "stocks")
            notional = brk.buy_notional("stocks", cash)
            ok, _ = risk.check_can_buy(conn, "stocks", notional, cash, 1.0)
            if ok:
                paper.buy(conn, "stocks", symbol, 100.0, "USD", 10.0)
            assert db.get_cash(conn, "stocks") >= -1e-9, db.get_cash(conn, "stocks")
        # 500 SEK only fits two positions of about 250 SEK including fees
        assert len(db.all_positions(conn)) == 2


def test_signal_uses_completed_bars():
    """A crossover that only exists in today's unfinished bar must not give a signal."""
    n = config.SLOW_MA + 5
    prices = [100.0] * (n - 1) + [200.0]   # only the last (unfinished) bar jumps
    close = pd.Series(prices, index=pd.date_range("2026-01-01", periods=n, freq="D"))
    assert strategy.signal_for(close)[0] == "buy"          # would trigger on the raw data
    assert strategy.signal_for(strategy.completed_bars(close))[0] == "hold"


def test_no_rebuy_on_same_signal():
    """After a stop-loss the same crossover bar must not open a new position."""
    path = os.path.join(tempfile.mkdtemp(), "rebuy.db")
    db.init_db(path)
    paper = brk.PaperBroker()
    today = db.now_iso()[:10]  # trade timestamps are in UTC
    with db.connect(path) as conn:
        assert not risk.already_acted_on_bar(conn, "NVDA", "2026-01-01")
        paper.buy(conn, "stocks", "NVDA", 100.0, "USD", 10.0)
        paper.sell(conn, "NVDA", 94.0, 10.0, reason="stop-loss")
        # Signal bar from yesterday or today: we already traded on it
        assert risk.already_acted_on_bar(conn, "NVDA", "2026-01-01")
        assert risk.already_acted_on_bar(conn, "NVDA", today)
        # A signal bar dated after our last trade is a new signal
        assert not risk.already_acted_on_bar(conn, "NVDA", "2999-01-01")
        # Other symbols are not affected
        assert not risk.already_acted_on_bar(conn, "AAPL", "2026-01-01")


def test_kill_switch():
    """Uses a temporary STOP file, so a real STOP in the project folder is never touched."""
    original = config.KILL_SWITCH_FILE
    config.KILL_SWITCH_FILE = os.path.join(tempfile.mkdtemp(), "STOP")
    try:
        assert not risk.kill_switch_active()
        open(config.KILL_SWITCH_FILE, "w").close()
        assert risk.kill_switch_active()
        ok, why = risk.check_can_buy(None, "stocks", 100, 500, 1.0)
        assert not ok and "kill switch" in why
    finally:
        config.KILL_SWITCH_FILE = original


def test_yearly_export(path, tmp):
    csv_path, summary_path, text = report.export_year(
        datetime.now().year, out_dir=os.path.join(tmp, "exports"), path=path
    )
    assert os.path.exists(csv_path) and os.path.exists(summary_path)
    with open(csv_path, encoding="utf-8") as fh:
        assert len(fh.readlines()) == 5  # header + 4 trades
    return text


def main():
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "test.db")
    db.init_db(path)

    test_broker_and_risk(path)
    test_cash_never_negative()
    test_signal_uses_completed_bars()
    test_no_rebuy_on_same_signal()
    test_kill_switch()
    text = test_yearly_export(path, tmp)
    print(text)
    print("All tests OK")


if __name__ == "__main__":
    main()
