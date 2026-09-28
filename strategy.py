"""Simple strategy: moving average crossover.

Buy signal when the fast MA crosses above the slow MA, sell when it crosses below.
Returns (signal, note) where signal is 'buy', 'sell' or 'hold'.
"""
import config


def completed_bars(close):
    """Drop the latest daily bar, since it may still be forming.

    yfinance includes today's unfinished bar, whose price changes every hour.
    Using it would let a crossover appear and disappear during the day.
    """
    return close.iloc[:-1]


def signal_for(close):
    if len(close) < config.SLOW_MA + 2:
        return "hold", "not enough data"

    fast = close.rolling(config.FAST_MA).mean()
    slow = close.rolling(config.SLOW_MA).mean()

    prev_diff = fast.iloc[-2] - slow.iloc[-2]
    curr_diff = fast.iloc[-1] - slow.iloc[-1]

    if prev_diff <= 0 < curr_diff:
        return "buy", f"MA{config.FAST_MA} crossed above MA{config.SLOW_MA}"
    if prev_diff >= 0 > curr_diff:
        return "sell", f"MA{config.FAST_MA} crossed below MA{config.SLOW_MA}"
    return "hold", "no crossover"
