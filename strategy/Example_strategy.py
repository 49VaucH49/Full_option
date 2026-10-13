from strategy.Strategies_template import Strategy_template

class Example_strategy(Strategy_template):
    def __init__(self, handler):
        super().__init__("example", "Example_strategy", handler, timeframe="1min")
        self.buy_counts = {s: 0 for s in ["ADVANC", "AOT", "AWC", "BANPU", "BBL"]}
        self.sell_counts = {s: 0 for s in ["ADVANC", "AOT", "AWC", "BANPU", "BBL"]}

    def on_data(self, bar):
        symbol = bar['ShareCode']
        price = bar['Close']

        # Check if the symbol is in either the buy_counts or sell_counts dictionary
        if symbol in self.buy_counts or symbol in self.sell_counts:
            if not self.handler.check_port_has_stock(symbol, 100):
                self.handler.create_order_at_market(100, "Buy", symbol)
            else:
                stocks = self.handler.get_stock_by_symbol(symbol)
                if stocks:
                    buy_price = stocks[0].get_buy_price()
                    if price < buy_price:
                        self.handler.create_order_at_market(100, "Sell", symbol)
