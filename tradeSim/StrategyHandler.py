import copy
import os
from types import MappingProxyType

from . import BarAggregator

class StrategyHandler:
    def __init__(self, strategy_class, strategy_runner, strategy_dir=None):
        # Everything the handler exposes is wired up BEFORE the strategy is
        # constructed, so a strategy's __init__ can already use it. That is
        # where reading history and precomputing indicators belongs: it runs
        # once, against data that cannot change during the day (the lookback
        # stops at the previous trading day), instead of inside on_data,
        # which fires on every tick -- roughly 190,000 times a day.
        #
        # Previously _runner was assigned after strategy_class(self), so any
        # such call died with "'StrategyHandler' object has no attribute
        # '_runner'" -- an error that says nothing about the real problem and
        # pushed everyone toward lazy caching inside on_data instead.
        #
        # _aggregator stays below: it needs the timeframe the strategy picks.
        self._strategy_dir = strategy_dir
        self._runner = strategy_runner
        self._current_row = None
        self.cum_buy_volume = 0
        self.cum_sell_volume = 0

        self.strategy = strategy_class(self)
        self._aggregator = BarAggregator.bar_aggregator(self.strategy.timeframe)

    def _resolve_companion_path(self, filename, allowed_extensions):
        """Safely resolve a companion file (a JSON config or a trained
        model) that was submitted alongside the strategy's own .py file --
        never an arbitrary path. `filename` must be a plain file name (no
        directory separators, no "..") so a strategy can never reach
        outside its own submission folder, and its extension must be one
        of `allowed_extensions`."""
        if self._strategy_dir is None:
            raise RuntimeError("No strategy directory available to resolve companion files from")
        if os.path.basename(filename) != filename:
            raise ValueError(f"'{filename}' must be a plain file name, not a path")
        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_extensions:
            raise ValueError(f"'{filename}' must end in one of {sorted(allowed_extensions)}")
        path = os.path.join(self._strategy_dir, filename)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"'{filename}' was not found next to your strategy file")
        return path

    def load_json(self, filename):
        """Load a JSON config file submitted alongside the strategy. A
        strategy can't call open() itself (forbidden at validate time), so
        this is the only way to read a plain data file it brought along."""
        import json
        path = self._resolve_companion_path(filename, {".json"})
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_model(self, filename):
        """Load a trained model submitted as a .skops file (see
        https://skops.readthedocs.io/) -- never pickle/joblib, which can run
        arbitrary code embedded in the file at load time. Refuses to load
        if the file references any type skops doesn't already recognize as
        safe, rather than trusting it blindly."""
        import skops.io as sio
        path = self._resolve_companion_path(filename, {".skops"})
        untrusted = sio.get_untrusted_types(file=path)
        if untrusted:
            raise ValueError(f"'{filename}' contains untrusted type(s), refusing to load: {untrusted}")
        return sio.load(path, trusted=[])

    # Kept in sync by hand with scripts/_common.py's COMPANION_ALLOW_EXTENSIONS
    # -- duplicated rather than imported across into tradeSim/ from scripts/
    # to avoid this engine-core class depending on sys.path setup done by
    # whichever entry point (main.py/_dry_run_runner.py) happens to run it.
    _COMPANION_EXTENSIONS = {".json", ".skops", ".txt", ".ubj", ".cbm"}

    def get_companion_path(self, filename):
        """The full path to a companion file submitted alongside the
        strategy (JSON config, or a model in its own native format --
        xgboost's .json/.ubj, lightgbm's .txt, catboost's .cbm) for handing to that
        library's own path-based loader, e.g.
        xgb.Booster().load_model(handler.get_companion_path("model.json"))."""
        return self._resolve_companion_path(filename, self._COMPANION_EXTENSIONS)

    def process_row(self, row):

        #made deep copy and readonly
        self._current_row = MappingProxyType(copy.deepcopy(dict(row)))

        flag = row["Flag"]
        volume = row["Volume"]

        if flag == "Buy":
            self.cum_buy_volume += volume
        elif flag == "Sell":
            self.cum_sell_volume += volume

        bar = self._aggregator.update(row)
        self.strategy.on_data(bar)

    def create_order_to_limit(self, volume, price, side, symbol):
        if self._current_row is None:
            raise RuntimeError("There is error in daily tick row data. Please check the data source.")
        return self._runner.create_order_to_limit(volume, price, side, symbol, self.cum_sell_volume, self.cum_buy_volume, self._current_row)
    
    def create_order_at_market(self, volume, side, symbol):
        if self._current_row is None:
            raise RuntimeError("There is error in daily tick row data. Please check the data source.")
        return self._runner.create_order_at_market(volume, side, symbol, self.cum_sell_volume, self.cum_buy_volume, self._current_row)

    def get_open_orders(self, symbol=None):
        return self._runner.get_open_orders(symbol)

    def cancel_order(self, order_number):
        return self._runner.cancel_order(order_number)

    def cancel_all_orders(self, symbol=None):
        return self._runner.cancel_all_orders(symbol)

    def check_port_has_stock(self, symbol, volume):
        return self._runner.check_port_has_stock(symbol, volume)

    def get_owner(self):
        return self._runner.get_owner()
    
    def get_all_stocks_info(self):
        return self._runner.get_all_stocks_info()
    
    def get_portfolio_info(self):
        return self._runner.get_portfolio_info()
    
    def get_stock_by_symbol(self,symbol):
        return self._runner.get_stock_by_symbol(symbol)
    
    def get_total_stock_volume_by_symbol(self, symbol):
        return self._runner.get_total_stock_volume_by_symbol(symbol)
    
    def get_cash_balance(self):
        return self._runner.get_cash_balance()
    
    def get_roi(self):
        return self._runner.get_roi()
    
    def get_max_draw_down(self):
        return self._runner.get_max_draw_down()
    
    def get_number_of_wins(self):
        return self._runner.get_number_of_wins()
    
    def get_number_of_sells(self):
        return self._runner.get_number_of_sells()

    def get_round_trip_count(self):
        return self._runner.get_round_trip_count()

    def get_buy_order_count(self):
        return self._runner.get_buy_order_count()

    def get_sell_order_count(self):
        return self._runner.get_sell_order_count()

    def get_win_rate(self):
        return self._runner.get_win_rate()

    def get_expected_payoff(self):
        return self._runner.get_expected_payoff()

    def get_average_exposure(self):
        return self._runner.get_average_exposure()

    def get_historical_data(self, symbol, n, timeframe="1D"):
        return self._runner.get_historical_data(symbol, n, timeframe)