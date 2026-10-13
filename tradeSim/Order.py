import time
import csv
import os
import bisect
from datetime import datetime, timedelta
from . import CommissionService


# Index names a strategy might reasonably try to order by mistake -- they
# can be read through get_historical_data() but never held.
INDEX_SYMBOLS = {"SET", "SET50", "SET100", "MAI", "SETHD"}


def tick_timestamp(mkt_data):
    """The timestamp the engine stores on an order for a given tick: when it
    was placed, and again when a resting order fills, so the stock's buy and
    sell times are the tick it actually traded on."""
    return (mkt_data["TradeDateTime"] - timedelta(hours=7)).timestamp()


class order:
    _order_counter = 1
    _set50_symbols = set()
    _csv_loaded = False

    @classmethod
    def load_set50_symbols(cls, csv_path=None):
        if cls._csv_loaded:
            return

        if csv_path is None:
            base_dir = os.path.dirname((__file__))
            csv_path = os.path.join(
                base_dir, "..", "marketInfo", "symbolSET50", "Symbol_SET50.csv"
            )
            csv_path = os.path.abspath(csv_path)

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"[ERROR] Cannot find SET50 list at '{csv_path}'")

        with open(csv_path, mode="r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            headers = [h.strip() for h in reader.fieldnames]

            symbol_col = None
            for h in headers:
                if h.lower() == "symbol":
                    symbol_col = h
                    break
            if symbol_col is None:
                raise KeyError("[ERROR] 'Symbol' column not found in CSV headers.")

            for row in reader:
                symbol = row[symbol_col].strip().upper()
                cls._set50_symbols.add(symbol)

        cls._csv_loaded = True

    def __init__(
        self,
        ownerPortfolio,
        volume,
        price,
        side,  # 'Buy' or 'Sell'
        symbol,
        cum_sell_volume,
        cum_buy_volume,
        timestamp=None,
        order_type="Limit",  # 'Limit' or 'Market'
    ):
        order.load_set50_symbols()
        self.order_type = order_type
        is_valid, reason = self.validate_order(
            volume, side, symbol, ownerPortfolio, price, cum_sell_volume, cum_buy_volume
        )
        if not is_valid:
            raise ValueError(
                f"[ERROR] Order for {symbol} (Vol: {volume}, Price: {price}, Side: {side}) skipped due to {reason}"
            )
        order_ts = timestamp if timestamp is not None else time.time()
        date_prefix = datetime.fromtimestamp(order_ts).strftime("%Y%m%d")
        self.order_number = f"{date_prefix}-ORD{order._order_counter:05d}"
        order._order_counter += 1

        self.ownerPortfolio = ownerPortfolio
        self.volume = volume
        self.price = price
        self.side = side
        self.symbol = symbol
        self.cum_sell_volume = cum_sell_volume
        self.cum_buy_volume = cum_buy_volume
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.placed_timestamp = self.timestamp
        self.fill_price = None
        self.fill_market_price = None
        self._new = True  # not yet tried against a tick of its own stock


    def validate_order(self, volume, side, symbol, ownerPortfolio, price, cum_sell_volume, cum_buy_volume):
        cashBalance = ownerPortfolio.get_cash_balance()
        
        if (volume % 100.0) != 0 and volume > 0:
            return False, "Volume must be a multiple of 100.SS S"
        
        if side.capitalize() not in {"Buy", "Sell"}:
            return False, f"Invalid side '{side}'. Must be 'Buy' or 'Sell'. Case sensitive."
        
        if symbol.upper() not in self._set50_symbols:
            # An index name gets its own message. "Symbol 'SET50' is not in
            # SET50." is technically accurate and reads like a bug, and the
            # mistake behind it is a specific one worth answering directly:
            # the index is readable history, not something you can hold.
            if symbol.upper() in INDEX_SYMBOLS:
                return False, (
                    f"'{symbol}' is a market index, not a tradable stock -- orders can only be "
                    f"placed on the individual SET50 constituent stocks (AOT, PTT, ...). "
                    f"To read the index itself, use get_historical_data('{symbol.upper()}', n)."
                )
            return False, (
                f"Symbol '{symbol}' is not one of the tradable SET50 stocks "
                f"(see marketInfo/symbolSET50/Symbol_SET50.csv for the full list)."
            )
        
        if (
            CommissionService.commissionService.verify_transaction(
                volume=volume, price=price, cashBalance=cashBalance,
                slippage=(self.order_type == "Market"),
            )
            == False
            and side == "Buy"
        ):
            return False, "Insufficient cash balance to cover transaction costs."

        if ownerPortfolio.has_stock(symbol, volume) == False and side == "Sell":
            return (
                False,
                f"Cannot sell {symbol} as it is not in the portfolio or insufficient volume.",
            )
            
        if side == "Buy" and volume > cum_sell_volume:
            return False, "Order's buy volume exceeds the cumulative sell volume from the daily ticks."
        
        if side == "Sell" and volume > cum_buy_volume:
            return False, "Order's sell volume exceeds the cumulative buy volume from the daily ticks."
        
        return True, ""
        
        

    # --------- Getter Methods ---------
    def get_order_number(self):
        return self.order_number

    def get_ownerPortfolio(self):
        return self.ownerPortfolio

    def get_volume(self):
        return self.volume

    def get_price(self):
        return self.price

    def get_side(self):
        return self.side

    def get_symbol(self):
        return self.symbol

    def get_timestamp(self):
        return self.timestamp

    def get_formatted_timestamp(self):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))

    def get_order_type(self):
        return self.order_type

    def get_placed_timestamp(self):
        return self.placed_timestamp

    def get_formatted_placed_timestamp(self):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.placed_timestamp))

    def get_fill_price(self):
        return self.fill_price

    def get_fill_market_price(self):
        return self.fill_market_price

    def is_new(self):
        """True until the order has been tried against a tick of its own stock."""
        return self._new

    def mark_seen(self):
        self._new = False

    def mark_filled(self, mkt_data, fill_price):
        """Record the fill: the price per share before fees, the market's last
        price on that tick, and the tick's time as the order's timestamp, so
        the stock's buy/sell time is when it actually traded."""
        self.fill_price = fill_price
        self.fill_market_price = mkt_data["LastPrice"]
        self.timestamp = tick_timestamp(mkt_data)
        self._new = False

    def get_order_info(self):
        return {
            "Order Number": self.get_order_number(),
            "owner": self.ownerPortfolio.get_owner(),
            "Type": self.get_order_type(),
            "Volume": self.get_volume(),
            "Price": self.get_price(),
            "Side": self.get_side(),
            "Symbol": self.get_symbol(),
            "Timestamp": self.get_formatted_timestamp(),
        }

    # --------- Setter Methods ---------
    def set_owner(self, owner):
        self.owner = owner

    def set_volume(self, volume):
        self.volume = volume

    def set_price(self, price):
        self.price = price

    def set_side(self, side):
        self.side = side

    def set_symbol(self, symbol):
        self.symbol = symbol