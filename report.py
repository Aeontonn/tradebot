"""Reports: yearly export (CSV + summary) and daily summary."""
import csv
import os

import config
import db

CSV_COLUMNS = [
    "ts", "market", "symbol", "side", "qty", "price", "currency", "fee",
    "fx_to_sek", "value_sek", "fee_sek", "realized_pl_sek", "order_id", "reason",
]


def export_year(year, out_dir="exports", path=None):
    """Writes trades_<year>.csv and summary_<year>.txt. Returns (csv_path, summary_path, text)."""
    os.makedirs(out_dir, exist_ok=True)
    start, end = f"{year}-01-01", f"{year + 1}-01-01"

    with db.connect(path) as conn:
        rows = conn.execute(
            f"SELECT {', '.join(CSV_COLUMNS)} FROM trades WHERE ts >= ? AND ts < ? ORDER BY ts",
            (start, end),
        ).fetchall()

    csv_path = os.path.join(out_dir, f"trades_{year}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLUMNS)
        for r in rows:
            writer.writerow([r[c] for c in CSV_COLUMNS])

    text = build_summary(year, rows)
    summary_path = os.path.join(out_dir, f"summary_{year}.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(text)
    return csv_path, summary_path, text


def build_summary(year, rows):
    sells = [r for r in rows if r["side"] == "sell"]
    lines = [f"Yearly summary {year} (all amounts in SEK)", "=" * 40]

    total_gain = total_loss = 0.0
    for market in ("stocks", "forex"):
        pls = [r["realized_pl_sek"] for r in sells if r["market"] == market and r["realized_pl_sek"] is not None]
        gain = sum(p for p in pls if p > 0)
        loss = sum(p for p in pls if p < 0)
        total_gain += gain
        total_loss += loss
        lines.append(
            f"{market:7s} trades: {len(pls):3d}   gains: {gain:9.2f}   losses: {loss:9.2f}   net: {gain + loss:9.2f}"
        )

    net = total_gain + total_loss
    fees = sum(r["fee_sek"] for r in rows)
    lines += [
        "-" * 40,
        f"Total gains:  {total_gain:10.2f}",
        f"Total losses: {total_loss:10.2f}",
        f"Net:          {net:10.2f}",
        f"Total fees:   {fees:10.2f} (already included in gains/losses)",
        "",
        "Estimated tax 30 % on net gain: "
        + (f"{net * 0.30:.2f}" if net > 0 else "0.00 (net loss, may give a tax deduction)"),
        "",
        "NOTE: Supporting data, not tax advice. Check the Swedish Tax Agency's rules,",
        "especially for CFD/forex, and compare with the broker's annual statement.",
    ]
    return "\n".join(lines) + "\n"


def daily_summary(conn):
    lines = ["Daily summary"]
    total = 0.0
    for market in ("forex", "stocks"):
        row = conn.execute(
            "SELECT equity_sek FROM equity WHERE market = ? ORDER BY id DESC LIMIT 1", (market,)
        ).fetchone()
        eq = row["equity_sek"] if row else config.START_CAPITAL_SEK[market]
        total += eq
        start = config.START_CAPITAL_SEK[market]
        lines.append(f"{market}: {eq:.0f} SEK ({(eq / start - 1) * 100:+.1f} %)")
    start_total = sum(config.START_CAPITAL_SEK.values())
    lines.append(f"Total: {total:.0f} SEK ({(total / start_total - 1) * 100:+.1f} %)")

    positions = db.all_positions(conn)
    if positions:
        lines.append("Open positions: " + ", ".join(f"{p['symbol']} ({p['qty']:.2f})" for p in positions))
    else:
        lines.append("No open positions")
    return "\n".join(lines)
