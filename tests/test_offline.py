"""Offline-test: kräver inget nätverk. Kör med: python tests/test_offline.py"""
import os
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import broker as brk
import config
import db
import report
import risk


def approx(a, b, tol=0.01):
    return abs(a - b) <= tol


def main():
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "test.db")
    db.init_db(path)
    paper = brk.PaperBroker()

    with db.connect(path) as conn:
        # Aktie: köp och sälj med vinst, USD -> SEK
        b = paper.buy(conn, "stocks", "AAPL", 200.0, "USD", 10.0, reason="test")
        assert b is not None
        assert db.get_position(conn, "AAPL") is not None
        s = paper.sell(conn, "AAPL", 220.0, 10.0, reason="test")
        cash = db.get_cash(conn, "stocks")
        expected = config.START_CAPITAL_SEK["stocks"] + s["realized_pl_sek"]
        assert approx(cash, expected), (cash, expected)
        assert s["realized_pl_sek"] > 0
        assert db.get_position(conn, "AAPL") is None

        # Forex med hävstång: köp och sälj med förlust
        paper.buy(conn, "forex", "EURUSD=X", 1.10, "USD", 10.0, reason="test")
        pos = db.get_position(conn, "EURUSD=X")
        assert pos is not None
        assert approx(brk.position_value_sek(pos, 1.10, 10.0), pos["margin_sek"], 1.5)
        f = paper.sell(conn, "EURUSD=X", 1.05, 10.0, reason="test")
        cash = db.get_cash(conn, "forex")
        expected = config.START_CAPITAL_SEK["forex"] + f["realized_pl_sek"]
        assert approx(cash, expected), (cash, expected)
        assert f["realized_pl_sek"] < 0

        # Riskregler
        ok, why = risk.check_can_buy(conn, "stocks", 10_000, 500, 1.0)
        assert not ok, why
        ok, why = risk.check_can_buy(conn, "stocks", 200, 500, 1.0)
        assert ok, why

        # Total förlustgräns
        db.log_equity(conn, "stocks", 100, 100)
        db.log_equity(conn, "forex", 100, 100)
        ok, why = risk.check_can_buy(conn, "stocks", 200, 500, 1.0)
        assert not ok and "förlust" in why

    # Kill switch
    open(config.KILL_SWITCH_FILE, "w").close()
    try:
        assert risk.kill_switch_active()
    finally:
        os.remove(config.KILL_SWITCH_FILE)
    assert not risk.kill_switch_active()

    # Årsexport
    csv_path, summary_path, text = report.export_year(
        datetime.now().year, out_dir=os.path.join(tmp, "exports"), path=path
    )
    assert os.path.exists(csv_path) and os.path.exists(summary_path)
    with open(csv_path, encoding="utf-8") as fh:
        assert len(fh.readlines()) == 5  # header + 4 affärer
    print(text)
    print("Alla tester OK")


if __name__ == "__main__":
    main()
