"""Price data and exchange rates via Yahoo Finance (yfinance). No API key needed."""
import pandas as pd
import yfinance as yf

# The currency each symbol is priced in
CURRENCY = {
    "EURUSD=X": "USD",
    "USDSEK=X": "SEK",
    "AAPL": "USD",
    "MSFT": "USD",
    "NVDA": "USD",
    "ASML": "USD",
}


def currency_of(symbol):
    return CURRENCY.get(symbol, "USD")


def get_history(symbol, days=120):
    """Daily closing prices as a pandas Series."""
    df = yf.download(symbol, period=f"{days}d", interval="1d", progress=False, auto_adjust=True)
    if df is None or df.empty:
        raise RuntimeError(f"No price data for {symbol}")
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close.dropna()


def last_price(symbol):
    return float(get_history(symbol, days=10).iloc[-1])


def fx_to_sek(currency):
    """How many SEK one unit of the currency costs right now."""
    if currency == "SEK":
        return 1.0
    return last_price(f"{currency}SEK=X")
