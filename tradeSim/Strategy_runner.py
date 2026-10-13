from . import Order
from datetime import timedelta

class strategy_runner:
    def __init__(self, tradeSim):
        """
        Initialize the strategy runner for executing strategies in the trade simulation.
        """
        self.tradeSim = tradeSim

    def create_order_to_limit(self, volume, price, side, symbol, cum_sell_volume, cum_buy_volume, mkt_data):
        return self.tradeSim.create_order_to_limit(volume, price, side, symbol, cum_sell_volume, cum_buy_volume, mkt_data)
    
    def create_order_at_market(self, volume, side, symbol, cum_sell_volume, cum_buy_volume, mkt_data):
        return self.tradeSim.create_order_at_market(volume, side, symbol, cum_sell_volume, cum_buy_volume, mkt_data)
    
    def get_open_orders(self, symbol=None):
        """
        Limit orders still resting in the order book -- all stocks, or only
        `symbol`'s -- as a list of dicts (Order Number, Symbol, Side,
        Volume, Price, Timestamp), oldest first.
        """
        return self.tradeSim.get_open_orders(symbol)

    def cancel_order(self, order_number):
        """
        Remove one resting limit order by its order number. True if it was
        removed; False if it already filled, was cancelled, or never rested.
        """
        return self.tradeSim.cancel_order(order_number)

    def cancel_all_orders(self, symbol=None):
        """
        Remove every resting limit order, or every one for `symbol`.
        Returns how many were removed.
        """
        return self.tradeSim.cancel_all_orders(symbol)

    def check_port_has_stock(self, symbol, volume):
        """
        Check if the portfolio has a specific stock with the given volume.
        """
        return self.tradeSim.portfolio.has_stock(symbol, volume)

    def get_owner(self):
        """
        Get the owner of the portfolio. 
        """
        return self.tradeSim.portfolio.get_owner()
    
    def get_all_stocks_info(self):
        """
        Returns a list of summarized stock information grouped by symbol.

        This method aggregates multiple lots of the same stock into a single summary entry.
        It computes the total volume, total cost, average cost, market value, and both realized and unrealized P&L
        for each unique stock symbol in the portfolio.

        Returns
        -------
        list of dict
            A list where each dictionary contains:
                - "Symbol": str, stock symbol.
                - "Buy Price": float, original buy price of the first lot (not averaged).
                - "Actual Volume": int, total remaining volume held for the symbol.
                - "Average Cost": float, total cost divided by total volume.
                - "Market Price": float, current market price.
                - "Amount Cost": float, total cost for the symbol.
                - "Market Value": float, current market value.
                - "Unrealized P&L": float, total unrealized profit/loss.
                - "Unrealized %": float, percentage of unrealized gain/loss.
                - "Realized P&L": float, total realized profit/loss from sells.
                - "Buy time": str, timestamp of the first buy (not aggregated across lots).
        """
        return self.tradeSim.portfolio.get_all_stocks_info()
    
    def get_portfolio_info(self):
        """
        Returns a summary of the portfolio's current state.

        The summary includes performance metrics, NAV statistics, trading results,
        and both realized and unrealized profit/loss information.

        Returns
        -------
        dict
            A dictionary containing:
                - "Owner": str, portfolio owner name.
                - "Number of Stocks": int, number of stock entries in the portfolio.
                - "Total Cost": float, total cost spent on current holdings.
                - "Unrealized P&L": float, unrealized profit or loss.
                - "Unrealized %": float, percentage of unrealized gain/loss.
                - "Realized P&L": float, realized profit or loss.
                - "Cash Balance": float, remaining cash.
                - "Net Asset Value": float, current NAV (cash + market value of holdings).
                - "Max NAV": float or None, highest end-of-day NAV so far (the drawdown peak).
                - "Min NAV": float or None, lowest end-of-day NAV since that peak -- reset
                  to Max NAV on every new peak, so NOT the all-time low (the drawdown trough).
                - "Max Drawdown (%)": float or None, max drawdown as a percentage.
                - "Relative Drawdown": float, Max Drawdown as a fraction (0.15 = 15%).
                - "Calmar Ratio": float or None, ratio of return to max drawdown.
                - "Previous Day Max DD (%)": float or None, prior day's max drawdown.
                - "Buy Order Count": int, number of executed Buy orders.
                - "Sell Order Count": int, number of executed Sell orders.
                - "Round-Trip Count": int, number of fully-closed FIFO lots.
                - "Profitable Round-Trips": int, number of profitable Round-Trips.
                - "Win Rate": float, win rate across completed Round-Trips.
                - "Expected Payoff": float, expected P&L per Round-Trip.
                - "Avg Gain": float, average P&L of a winning Round-Trip.
                - "Avg Loss": float, average size of a losing Round-Trip's loss (positive).
                - "Average Exposure": float, average fraction (0-1) of NAV invested.
                - "Return rate": float, overall portfolio return (%).
                - "Benchmark Return": float or None, benchmark return (%) over the same window.
                - "Benchmark Max DD": float or None, benchmark max drawdown (%).
                - "Excess Return": float or None, Return rate - Benchmark Return.
                  The three benchmark fields stay None until the day's run is saved.
        """
        return self.tradeSim.portfolio.get_portfolio_info()
    
    def get_stock_by_symbol(self,symbol):
        """
        Get a specific stock by its symbol from the portfolio.
        """
        return self.tradeSim.portfolio.get_stock_by_symbol(symbol)
    
    def get_total_stock_volume_by_symbol(self, symbol):
        """
        Get the total volume of a specific stock symbol in the portfolio.
        """
        return self.tradeSim.portfolio.get_total_stock_volume_by_symbol(symbol)
    
    def get_cash_balance(self):
        """
        Get the current cash balance in the portfolio.
        """
        return self.tradeSim.portfolio.get_cash_balance()
    
    def get_roi(self):
        """
        Calculate the return on investment (ROI) for the portfolio.
        """
        return self.tradeSim.portfolio.calculate_roi()
    
    def get_max_draw_down(self):
        """
        Get the maximum drawdown of the portfolio.
        This is the largest observed loss from a peak to a trough of a portfolio, before a new peak is attained.
        """
        return self.tradeSim.portfolio.get_max_draw_down()
    
    def get_number_of_wins(self):
        """
        Get the total number of winning trades in the portfolio.
        A winning trade is defined as a sell transaction that results in a profit.
        """
        return self.tradeSim.portfolio.get_number_of_wins()
    
    def get_number_of_sells(self):
        """
        Get the total number of completed Round-Trips (fully-closed
        FIFO lots) in the portfolio. NOTE: despite the name (kept for
        backward compatibility), this is NOT a count of sell orders
        placed -- see get_sell_order_count() for that.
        """
        return self.tradeSim.portfolio.get_number_of_sells()

    def get_round_trip_count(self):
        """
        Get the total number of completed Round-Trips (fully-closed
        FIFO lots). Same value as get_number_of_sells(), under a
        clearer name.
        """
        return self.tradeSim.portfolio.get_number_of_sells()

    def get_buy_order_count(self):
        """
        Get the number of Buy orders actually executed (validated and
        matched), regardless of how many Round-Trips they contributed to.
        """
        return self.tradeSim.portfolio.get_buy_order_count()

    def get_sell_order_count(self):
        """
        Get the number of Sell orders actually executed (validated and
        matched), regardless of how many Round-Trips they contributed to.
        """
        return self.tradeSim.portfolio.get_sell_order_count()

    def get_win_rate(self):
        """
        Get the Win Rate (%) across completed Round-Trips. Round-Trips
        with exactly zero net P&L are excluded from this calculation.
        """
        return self.tradeSim.portfolio.get_win_rate()

    def get_expected_payoff(self):
        """
        Get the Expected Payoff: the average P&L per completed
        Round-Trip, weighted by Win Rate and average gain/loss size.
        """
        return self.tradeSim.portfolio.get_expected_payoff()

    def get_avg_gain(self):
        """
        Get the average P&L of a winning Round-Trip.
        """
        return self.tradeSim.portfolio.get_avg_gain()

    def get_avg_loss(self):
        """
        Get the average size of a losing Round-Trip's loss, as a positive
        number (Expected Payoff = Win Rate x Avg Gain - Loss Rate x Avg Loss).
        """
        return self.tradeSim.portfolio.get_avg_loss()

    def get_benchmark_return(self):
        """
        Get the Benchmark Return (%) -- None until the day's run is saved.
        """
        return self.tradeSim.portfolio.benchmark_return

    def get_excess_return(self):
        """
        Get the Excess Return (Return - Benchmark Return, in percentage
        points) -- None until the day's run is saved.
        """
        return self.tradeSim.portfolio.get_excess_return()

    def get_average_exposure(self):
        """
        Get Average Portfolio Exposure: the average fraction (0-1) of
        NAV invested in the market across all trading days so far.
        """
        return self.tradeSim.portfolio.get_average_exposure()

    def get_historical_data(self, symbol, n, timeframe="1D"):
        """
        Get OHLCV bars of `timeframe` ("1D" by default, or an intraday one
        such as "5min") for `symbol`, up to the last `n` (capped at 1000),
        strictly before the day currently being simulated.
        """
        return self.tradeSim.get_historical_data(symbol, n, timeframe)