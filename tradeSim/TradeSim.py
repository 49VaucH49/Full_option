from . import Portfolio
from . import Execution
from . import Strategy_runner
from . import Order
from . import Benchmark
from . import HistoricalData
import os
import threading
lock = threading.Lock()

import os
import pandas as pd
from datetime import datetime

logged_errors = set()

class tradeSim:
    def __init__(self, team_name, load_existing=True, folder="result", current_date=None):
        self.error_logger = ErrorLogger(team_name)
        """
        Initialize the trade simulation environment for a simulation.
        ----------
        Parameter
        team_name: Name of the team.
        current_date: The date being simulated (e.g. from --date), used to
            bound get_historical_data() so it can never see this run's own
            day or any later day. None (the default) means "unknown" --
            get_historical_data() then just returns [] rather than
            guessing, e.g. during CI dry-run.
        """
        # create directory if it does not exist
        team_folder = os.path.join(folder, team_name)
        os.makedirs(team_folder, exist_ok=True)

        portfolio_file_name = f"{team_name}_portfolio.json"
        file_path = os.path.join(folder,team_name, portfolio_file_name)

        if load_existing and os.path.exists(file_path):
            self.portfolio = Portfolio.portfolio.load_from_file(team_name)
            print(f"[INFO] Loaded existing portfolio from '{file_path}'")
        else:
            self.portfolio = Portfolio.portfolio(team_name)
            print(f"[INFO] Created new portfolio for '{team_name}'")
            self.portfolio.save_to_file(team_name)
        self.execution = Execution.execution(team_name)
        self.current_date = pd.to_datetime(current_date).date() if current_date is not None else None
        self._historical_data_reader = HistoricalData.historical_data()

    def create_order_to_limit(self, volume, price, side, symbol, cum_sell_volume, cum_buy_volume, mkt_data):
        with lock:
            limit_order = None
            try:
                limit_order = Order.order(
                    ownerPortfolio=self.portfolio,
                    volume=volume,
                    price=price,
                    side=side,
                    symbol=symbol,
                    cum_sell_volume=cum_sell_volume,
                    cum_buy_volume=cum_buy_volume,
                    timestamp=Order.tick_timestamp(mkt_data)
                )
                self.execution.addOrderToOrders_Book(limit_order, mkt_data)

            except ValueError as e:
                self.error_logger.log_error(e)
                return e
            except FileNotFoundError as e:
                self.error_logger.log_error(e)
                return e
            except KeyError as e:
                self.error_logger.log_error(e)
                return e

            # The order number is what cancel_order() takes. "created" means
            # the order passed validation and is in the book, not that it filled.
            return "Order {number} for {symbol} (Vol: {volume}, Price: {price}, Side: {side}) created successfully.".format(
                number=limit_order.get_order_number(),
                symbol=symbol,
                volume=volume,
                price=price,
                side=side
            )

    def create_order_at_market(self, volume, side, symbol, cum_sell_volume, cum_buy_volume, mkt_data):
        with lock:
            # A market order fills at mkt_data's price, i.e. the stock whose
            # bar is being processed. Ordering another symbol from here used
            # to price it at the wrong stock's LastPrice, fail to match, vanish
            # silently -- and still report success.
            if symbol != mkt_data['ShareCode']:
                e = ValueError(
                    f"[ERROR] Market order for {symbol} (Vol: {volume}, Side: {side}) skipped: a market "
                    f"order fills at the price of the bar being processed, which is {mkt_data['ShareCode']}. "
                    f"Place it from {symbol}'s own on_data call (check bar['ShareCode']), or use "
                    f"create_order_to_limit with a price."
                )
                self.error_logger.log_error(e)
                return e

            new_order = None
            try:
                new_order = Order.order(
                    ownerPortfolio=self.portfolio,
                    volume=volume,
                    price=mkt_data['LastPrice'],
                    side=side,
                    symbol=symbol,
                    cum_sell_volume=cum_sell_volume,
                    cum_buy_volume=cum_buy_volume,
                    timestamp=Order.tick_timestamp(mkt_data),
                    order_type="Market",
                )
                self.execution.isMatchMarketOrder(mkt_data,new_order)

            except ValueError as e:
                self.error_logger.log_error(e)
                return e
            except FileNotFoundError as e:
                self.error_logger.log_error(e)
                return e
            except KeyError as e:
                self.error_logger.log_error(e)
                return e

            # "submitted", not "created": like a broker's confirmation, this
            # says the order was accepted, not that it filled -- the portfolio
            # is the source of truth for that. Still contains "successfully"
            # so a strategy's `"successfully" in result` check keeps working.
            return "Market order for {symbol} (Vol: {volume}, Price: {price}, Side: {side}) submitted successfully.".format(
                symbol=symbol,
                volume=volume,
                price=mkt_data['LastPrice'],
                side=side
            )

    def get_strategy_runner(self):
        """
        Returns the strategy runner instance for executing strategies.
        """
        return Strategy_runner.strategy_runner(self)
    
    def save_portfolio(self):
        """ 
        Save the current portfolio state to  JSONfile. 
        """
        self.portfolio.save_to_file(self.portfolio.get_owner())
    
    def save_summary_csv(self, trading_date, university_start_date=None):
        self.portfolio.finalize_day(trading_date)

        bm = Benchmark.benchmark("marketInfo/benchmark")
        benchmark_return = bm.get_benchmark_return(trading_date, start_date=university_start_date)
        benchmark_max_dd = bm.get_benchmark_max_dd(trading_date, start_date=university_start_date)

        self.portfolio.save_summary_csv(
            trading_date,
            benchmark_return=benchmark_return,
            benchmark_max_dd=benchmark_max_dd,
        )

    def create_transaction_summarize(self, team_name):
        """
        Create a transaction summary for the team.
        """
        self.execution.PortSummarize.create_transaction_summarize(team_name)

    def isOrderbooksEmpty(self):
        """
        Check if the order book is empty.
        """
        return len(self.execution.Orders_Book) == 0

    def get_open_orders(self, symbol=None):
        """
        Limit orders still resting in the order book -- all stocks, or only
        `symbol`'s -- as a list of dicts (Order Number, Symbol, Side,
        Volume, Price, Timestamp), oldest first.
        """
        with lock:
            return self.execution.getOpenOrders(symbol)

    def cancel_order(self, order_number):
        """
        Remove one resting limit order. True if it was in the book and is
        now gone; False if it already filled, was cancelled, or never rested.
        """
        with lock:
            return self.execution.cancelOrder(order_number)

    def cancel_all_orders(self, symbol=None):
        """
        Remove every resting limit order, or every one for `symbol`.
        Returns how many were removed.
        """
        with lock:
            return self.execution.cancelAllOrders(symbol)
    
    def isMatch(self, row):
        with lock:
            return self.execution.isMatch(row)
    
        # update market prices in portfolio
    def update_market_prices(self, price_update):
        """
        Update the market prices in the portfolio based on the provided price update.
        """
        self.portfolio.update_market_prices(price_update)
        
    def flushTransactionLog(self):
        self.execution.flushTransactionLog()

    def flushErrorLogger(self):
        self.error_logger.flush_logs()

    def get_historical_data(self, symbol, n, timeframe="1D"):
        """OHLCV bars for `symbol`, up to the last `n` (capped at
        HistoricalData.MAX_LOOKBACK_DAYS) strictly before the date this
        simulation run was constructed with. `timeframe` "1D" (the default)
        gives daily bars from marketInfo/ticks/ + daily_history/; an
        intraday one gives bars from marketInfo/intraday_history/.

        Raises ValueError for a timeframe there is no data for -- checked
        before anything else, so CI catches it too. Otherwise returns [] if
        no current_date was given at construction (e.g. CI dry-run, or a
        test that doesn't pass one)."""
        interval = HistoricalData.resolve_timeframe(timeframe)
        if self.current_date is None:
            return []
        if interval == HistoricalData.DAILY:
            return self._historical_data_reader.get_ohlcv(symbol, self.current_date, n)
        return self._historical_data_reader.get_intraday_ohlcv(symbol, self.current_date, n, interval)


class ErrorLogger:
    def __init__(self, team_name, filename_suffix="error_log.txt"):
        self.error_log = []
        self.team_name = team_name

        folder = os.path.join("result", team_name)
        os.makedirs(folder, exist_ok=True)
        self.txt_file = os.path.join(folder, f"{team_name}_{filename_suffix}")

        # Write header once
        if not os.path.exists(self.txt_file):
            with open(self.txt_file, "w", encoding="utf-8") as f:
                f.write("Timestamp | Error Message\n")
                f.write("-" * 80 + "\n")

    def log_error(self, error: Exception):
        err_msg = str(error)
        # Avoid duplicates within current runtime
        if err_msg not in [e["message"] for e in self.error_log]:
            self.error_log.append({
                "timestamp": datetime.now(),
                "message": err_msg
            })

    def flush_logs(self):
        if not self.error_log:
            return

        with open(self.txt_file, "a", encoding="utf-8") as f:
            for e in self.error_log:
                f.write(f"{e['timestamp']} | {e['message']}\n")

        self.error_log.clear()