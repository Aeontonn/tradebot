"""Enkel strategi: moving average crossover.

Köpsignal när snabb MA korsar över långsam MA, sälj när den korsar under.
Returnerar (signal, anteckning) där signal är 'buy', 'sell' eller 'hold'.
"""
import config


def signal_for(close):
    if len(close) < config.SLOW_MA + 2:
        return "hold", "för lite data"

    fast = close.rolling(config.FAST_MA).mean()
    slow = close.rolling(config.SLOW_MA).mean()

    prev_diff = fast.iloc[-2] - slow.iloc[-2]
    curr_diff = fast.iloc[-1] - slow.iloc[-1]

    if prev_diff <= 0 < curr_diff:
        return "buy", f"MA{config.FAST_MA} korsade över MA{config.SLOW_MA}"
    if prev_diff >= 0 > curr_diff:
        return "sell", f"MA{config.FAST_MA} korsade under MA{config.SLOW_MA}"
    return "hold", "ingen korsning"
