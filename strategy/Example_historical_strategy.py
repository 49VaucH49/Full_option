from strategy.Strategies_template import Strategy_template


class Example_historical_strategy(Strategy_template):
    """Minimal example that actually calls get_historical_data(): buys when
    the close price is above the 5-day SMA, sells when it drops back below.

    The SMA is computed once in __init__, not in on_data: history stops at
    the previous trading day, so it can't change while the day runs, and
    on_data fires on every tick (~190,000 times a day)."""

    LOOKBACK = 5
    WATCHLIST = ["AOT", "PTT", "ADVANC"]

    def __init__(self, handler):
        # self.handler is set by this call -- history has to come after it
        super().__init__("example", "Example_historical_strategy", handler, timeframe="1D")

        self.sma = {}
        for symbol in self.WATCHLIST:
            history = self.handler.get_historical_data(symbol, self.LOOKBACK)
            if len(history) < self.LOOKBACK:
                continue  # not enough history to compute the SMA (always the case in CI)
            self.sma[symbol] = sum(day["Close"] for day in history) / len(history)

    def on_data(self, bar):
        symbol = bar["ShareCode"]
        sma = self.sma.get(symbol)
        if sma is None:
            return  # not in the watchlist, or not enough history

        price = bar["Close"]

        if price > sma and not self.handler.check_port_has_stock(symbol, 100):
            self.handler.create_order_at_market(100, "Buy", symbol)
        elif price < sma and self.handler.check_port_has_stock(symbol, 100):
            self.handler.create_order_at_market(100, "Sell", symbol)
