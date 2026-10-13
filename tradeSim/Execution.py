from . import Stock
from . import TransactionLog
from . import PortSummarize as ps
from . import CommissionService
import pandas as pd
import os
import bisect
import logging


class execution:
    PortSummarize = ps.summarize

    def __init__(
        self,
        team_name,
        orders_book=None,
    ):
        self.Orders_Book = orders_book if orders_book is not None else []
        self.tranLog = TransactionLog.Transaction(team_name)

    def addOrderToOrders_Book(self, new_order, row):
        if new_order is None:
            return "Cannot add an invalid/None order."
        if new_order.get_side() == "Buy":
            self.Orders_Book.append(new_order)
            return f"Order {new_order.get_order_number()} added to book ({new_order.get_symbol()})."
        elif new_order.get_side() == "Sell":
            self.Orders_Book.append(new_order)
            return f"Order {new_order.get_order_number()} added to book ({new_order.get_symbol()})."

    def isMatch(self, row):
        """Try the resting limit orders for this tick's stock against it.

        Orders for other stocks are left alone -- they wait for their own
        stock's ticks. Orders are tried in the order they were placed. One
        that this tick fills (see _limit_fill_price) is filled, or cancelled
        if the cash or shares it needs are no longer there; one it doesn't
        fill stays in the book. The book lives for one day: every run builds
        a new tradeSim, so orders still resting at the close are gone the
        next day.
        """
        for order in list(self.Orders_Book):  # copy: orders leave the book inside the loop
            if order.get_symbol() != row["ShareCode"]:
                continue
            if row["TradeDateTime"] < pd.to_datetime(order.get_placed_timestamp(), unit="s"):
                continue
            fill = self._limit_fill_price(row, order)
            order.mark_seen()
            if fill is None:
                continue
            is_valid, _ = self.validate_order(
                order.get_volume(), order.get_side(), order.get_symbol(),
                order.get_ownerPortfolio(), fill, slippage=False,
            )
            if not is_valid:
                self.removeOrder(order)
                continue
            order.mark_filled(row, fill)
            self._process_fill(order)
            self.removeOrder(order)

    @staticmethod
    def _limit_fill_price(row, order):
        """The price a limit order gets on this tick, or None if it doesn't fill.

        The tick's Flag says which side started the trade. "Buy" means a
        buyer took a seller's offer, so someone was offering at that price;
        "Sell" means a seller hit a buyer's bid, so that price was the bid
        and the cheapest offer is about one price step higher. Auction
        prints (OPEN1_E, OPEN2_E, ATC) have no side and fill no limit order.

        On the first tick of its own stock after it is placed, an order
        trades against the quote: a Buy fills if the offer is at or below
        its price and pays the offer -- its own price or better. After that
        it rests in the book and fills at its own price once the market
        trades at or through it.
        """
        flag = row.get("Flag")
        if flag not in ("Buy", "Sell"):
            return None
        last, limit = row["LastPrice"], order.get_price()
        step = CommissionService.commissionService._get_slippage(last)
        if order.get_side() == "Buy":
            if order.is_new():
                offer = last if flag == "Buy" else last + step
                return offer if offer <= limit else None
            return limit if last <= limit else None
        if order.is_new():
            bid = last if flag == "Sell" else last - step
            return bid if bid >= limit else None
        return limit if last >= limit else None

    def isMatchMarketOrder(self, row, market_order):
        """A market order fills at once at the last price one step against
        it, whatever side the tick was -- unless the cash or shares aren't there."""
        if market_order is None:
            return
        if row["ShareCode"] != market_order.get_symbol():
            return f"Market order {market_order.get_order_number()} is not for this tick's stock."
        is_valid, _ = self.validate_order(
            market_order.get_volume(), market_order.get_side(), market_order.get_symbol(),
            market_order.get_ownerPortfolio(), row["LastPrice"], slippage=True,
        )
        if not is_valid:
            return f"Market order {market_order.get_order_number()} could not be filled."
        fill = CommissionService.commissionService.market_fill_price(row["LastPrice"], market_order.get_side())
        market_order.mark_filled(row, fill)
        self._process_fill(market_order)

    def validate_order(self, volume, side, symbol, ownerPortfolio, price, slippage=True):
        cashBalance = ownerPortfolio.get_cash_balance()
        
        if (volume % 100.0) != 0 and volume > 0:
            return False, "Volume must be a multiple of 100.SS S"
        
        if side.capitalize() not in {"Buy", "Sell"}:
            return False, f"Invalid side '{side}'. Must be 'Buy' or 'Sell'. Case sensitive."
        
        if (
            CommissionService.commissionService.verify_transaction(
                volume=volume, price=price, cashBalance=cashBalance, slippage=slippage
            )
            == False
            and side == "Buy"
        ):
            return False, "Insufficient cash balance to cover transaction costs."

        if ownerPortfolio.has_stock(symbol, volume) == False and side == "Sell":
            print(f"Cannot sell {symbol} as it is not in the portfolio or insufficient volume.")
            return False, f"Cannot sell {symbol} as it is not in the portfolio or insufficient volume."

        return True, ""

    def _process_fill(self, order):
        """Book a filled order (limit or market) at its fill price and log it."""
        if order.get_side() == "Buy":
            self._process_buy_order(order)
        else:
            self._process_sell_order(order)
        self.tranLog.create_transaction_log(order)

    def _unit_value(self, order):
        return CommissionService.commissionService.cal_unit_cost(
            order.get_volume(), order.get_fill_price(), order.get_side()
        )

    # The two names below are load-bearing: Portfolio.add_stock() only
    # accepts calls from a function called _process_buy_order.
    def _process_buy_order(self, order):
        unit_value = self._unit_value(order)
        new_stock = Stock.stock(
            order.get_symbol(),
            order.get_volume(),
            unit_value,
            order.get_price(),
            order.get_timestamp(),
            opened_at_order=order.get_order_number(),
        )
        order.get_ownerPortfolio().add_stock(new_stock)
        order.get_ownerPortfolio().update_Buy_stock_valueToPort(unit_value * order.get_volume())

    def _process_sell_order(self, order):
        unit_value = self._unit_value(order)
        order.get_ownerPortfolio().decrease_stock_volume(
            order.get_symbol(), order.get_volume(), unit_value,
            closed_by_order=order.get_order_number(),
            close_timestamp=order.get_timestamp(),
        )
        order.get_ownerPortfolio().update_sold_stock_valueToPort(unit_value * order.get_volume())

    def removeOrder(self, order):
        self.Orders_Book.remove(order)

    def getOpenOrders(self, symbol=None):
        return [o.get_order_info() for o in self.Orders_Book
                if symbol is None or o.get_symbol() == symbol]

    def cancelOrder(self, order_number):
        for o in self.Orders_Book:
            if o.get_order_number() == order_number:
                self.removeOrder(o)
                return True
        return False

    def cancelAllOrders(self, symbol=None):
        to_cancel = [o for o in self.Orders_Book if symbol is None or o.get_symbol() == symbol]
        for o in to_cancel:
            self.removeOrder(o)
        return len(to_cancel)

    def getOrderbooksSize(self):
        return len(self.Orders_Book)

    def isOrderbooksEmpty(self):
        return self.getOrderbooksSize() == 0

    def flushTransactionLog(self):
        self.tranLog.flush_logs()