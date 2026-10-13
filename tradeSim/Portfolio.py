from collections import defaultdict
import csv
import json
from . import Stock
import os
from datetime import datetime
import sys


class portfolio:
    def __init__(
        self,
        owner,
        stocksList=None,
        amountByCost=0.0,
        unrealized=0.0,
        unrealizedInPercentage=0.0,
        realized=0.0,
        cashbalance=10000000.0,
        cashbalance_start=None,
        prevousDay_maxDD=None,
        nav=0.0,
        max_nav=None,
        min_nav=None,
        max_Draw_down=0.0,
        round_trips=None,
        buy_order_count=0,
        sell_order_count=0,
        daily_snapshots=None,
    ):
        self.owner = owner
        self.stocksList = stocksList if stocksList is not None else []
        self.amountByCost = amountByCost
        self.unrealized = unrealized
        self.unrealizedInPercentage = unrealizedInPercentage
        self.realized = realized
        self.cashbalance = cashbalance
        self.initial_cash = 10000000.0
        self.prevousDay_maxDD = prevousDay_maxDD
        self.cashbalance_start = cashbalance_start if cashbalance_start is not None else 10000000.0
        self.nav = nav
        self.max_nav = max_nav
        self.min_nav = min_nav
        self.max_Draw_down = max_Draw_down
        self.round_trips = round_trips if round_trips is not None else []
        self.buy_order_count = buy_order_count
        self.sell_order_count = sell_order_count
        self.daily_snapshots = daily_snapshots if daily_snapshots is not None else []
        # Set only by save_summary_csv(), i.e. once the day is over: the
        # benchmark's return for today uses today's closing index level, so
        # exposing it any earlier would hand a strategy the close before the
        # market got there. Deliberately NOT saved to portfolio.json either --
        # loaded tomorrow it would read as today's number.
        self.benchmark_return = None
        self.benchmark_max_dd = None

    def add_stock(self, stock):
        caller = sys._getframe(1).f_code.co_name
        if caller != "_process_buy_order" and caller != "_process_market_order":
            print(caller)
            raise ValueError(f"add stock must be called from create_order(). unable to add stock from {caller}()")

        self.stocksList.append(stock)
        self.buy_order_count += 1
        self.update_portfolio_totals()
        self.update_avg_stocks_by_symbol(stock.get_symbol())

    def decrease_stock_volume(self, symbol, volume, price, closed_by_order=None, close_timestamp=None):

        self.stocksList.sort(key=lambda stock: stock.buy_time)
        self.sell_order_count += 1

        remaining_volume = volume

        for s in list(self.stocksList):

            if remaining_volume == 0:
                break

            if s.get_symbol() == symbol:

                vol_to_decrease = min(s.get_actual_vol(), remaining_volume)

                realized_profit = (price * vol_to_decrease) - (
                    s.get_buy_price() * vol_to_decrease
                )
                self.realized += realized_profit
                s.add_realized(realized_profit)

                s.decreaseStockVolume(vol_to_decrease)
                remaining_volume -= vol_to_decrease

                if s.get_actual_vol() <= 0:
                    lot_pnl = s.get_realized()
                    if lot_pnl > 0:
                        outcome = "win"
                    elif lot_pnl < 0:
                        outcome = "loss"
                    else:
                        outcome = "breakeven"

                    self.round_trips.append({
                        "symbol": s.get_symbol(),
                        "opened_at_order": s.get_order_opened_at(),
                        "closed_at_order": closed_by_order,
                        "open_volume": s.get_start_vol(),
                        "open_timestamp": s.buy_time,
                        "close_timestamp": close_timestamp,
                        "realized_pnl": lot_pnl,
                        "outcome": outcome,
                    })

                    self.stocksList.remove(s)

        self.update_portfolio_totals()
        self.update_avg_stocks_by_symbol(symbol)

    def update_avg_stocks_by_symbol(self, symbol):
            for stocks in self.get_stock_by_symbol(symbol):
                new_price = stocks.get_mkt_price()
                symbol_avg_cost = self._cal_avg_cost(symbol)
                stocks.updateStockMk_value(new_price, symbol_avg_cost)

    def update_sold_stock_valueToPort(self, amount):
        self.cashbalance += amount

    def update_Buy_stock_valueToPort(self, amount):
        self.cashbalance -= amount

    def _update_max_min_nav(self):
        nav = self.get_nav()

        if self.max_nav is None or nav > self.max_nav:
            self.max_nav = nav
            self.min_nav = nav
        elif nav < self.min_nav:
            self.min_nav = nav

    def _calUnrealized(self):
        self.unrealized = self.market_value - self.amount_cost

    def _calUnrealizedInPercentagee(self):
        self.unrealizedInPercentage = (
            (self.unrealized / self.amount_cost) * 100 if self.amount_cost != 0 else 0.0
        )

    def _cal_avg_cost(self, symbol):
        symbol_stocks = self.get_stock_by_symbol(symbol)
        total_volume = 0
        total_cost = 0.0
        for stock in symbol_stocks:
            volume = stock.get_actual_vol()
            price = stock.get_buy_price()
            total_volume += volume
            total_cost += price * volume

        if total_volume == 0:
            return 0.0

        avg_cost = total_cost / total_volume
        return avg_cost

    def _cal_maxDD(self):
        if self.max_nav and self.min_nav and self.max_nav != 0:
            current_dd = ((self.max_nav - self.min_nav) / self.max_nav) * 100
            self.prevousDay_maxDD = max(self.prevousDay_maxDD or 0, current_dd)
            self.max_Draw_down = self.prevousDay_maxDD

    def _cal_winRate(self):
        counted = [rt for rt in self.round_trips if rt["outcome"] != "breakeven"]
        if not counted:
            return 0
        wins = sum(1 for rt in counted if rt["outcome"] == "win")
        return (wins / len(counted)) * 100

    def _calculate_nav(self):
        self.nav = self.get_unrealized() + self.cashbalance + self.get_amount_by_cost()

    def calculate_roi(self):
        return (
            ((self.get_nav() - self.initial_cash) / self.initial_cash * 100) 
        )

    def _cal_relativeDrawdown(self):
        """Portfolio Max DD expressed as a fraction rather than a percent
        (0.15 for a 15% drawdown). Not one of the competition's scored
        metrics -- it appears in no ranking or qualification rule -- just a
        convenience alongside them.

        Previously divided by initial_cash as well, which mixed a percentage
        with a baht amount and produced ~1e-8 for every portfolio no matter
        what happened, while save_summary_csv() wrote max_dd/100 into the
        "Relative Drawdown" CSV column teams actually receive. Two different
        numbers under one name; this is the CSV's meaning, which is the one
        that was ever useful."""
        return self.max_Draw_down / 100

    def update_portfolio_totals(self):
        total_amount = 0.0
        total_unrealized = 0.0
        total_realized = 0.0

        for stock in self.stocksList:
            total_amount += stock.get_amount_cost()
            total_unrealized += stock.get_unrealized()
            total_realized += stock.get_realized()
            


        self.amountByCost = total_amount
        self.unrealized = total_unrealized
        self.unrealizedInPercentage = (
            (self.unrealized / self.amountByCost) * 100
            if self.amountByCost != 0
            else 0.0
        )
        self._calculate_nav()

    def _cal_calmar_ratio(self):
        if self.max_Draw_down == 0:
            return 0
        return self.calculate_roi() / self.max_Draw_down

    def finalize_day(self, date):
        invested_value = sum(stock.get_market_value() for stock in self.stocksList)
        nav = self.get_nav()

        self.daily_snapshots.append({
            "date": str(date),
            "nav": nav,
            "invested_value": invested_value,
            "cash_balance": self.cashbalance,
        })

        self._update_max_min_nav()
        self._cal_maxDD()

    def get_average_exposure(self):
        """Average Portfolio Exposure = (1/T) * Sum(Invested_t / NAV_t),
        the mean of each day's OWN exposure ratio -- not a pooled ratio
        (Sum(Invested) / Sum(NAV)). A pooled ratio implicitly NAV-weights
        each day, which silently diverges from the per-day mean whenever
        NAV varies day to day (e.g. 80% exposure on a 10M NAV day then 0%
        on a 20M NAV day averages to 40%, not the pooled 26.7%)."""
        if not self.daily_snapshots:
            return 0.0
        daily_ratios = [
            (d["invested_value"] / d["nav"]) if d["nav"] else 0.0
            for d in self.daily_snapshots
        ]
        return sum(daily_ratios) / len(daily_ratios)

    def update_market_prices(self, price_updates: dict):
        """
        price_updates: dict mapping symbol (str) -> new market price (float)
        """
        for stock in self.stocksList:
            if stock.get_symbol() in price_updates:
                new_price = price_updates[stock.get_symbol()]
                symbol_avg_cost = self._cal_avg_cost(stock.get_symbol())
                stock.updateStockMk_value(new_price, symbol_avg_cost)
        self.update_portfolio_totals()

    def has_stock(self, symbol, volume):
        total_volume = 0.0
        for stock in self.stocksList:
            if stock.get_symbol() == symbol:
                total_volume += stock.get_actual_vol()
        if total_volume >= volume:
            return True
        return False

    def cal_realized(self, total_cost, total_value):
        return total_value - total_cost

    # getter methods
    def get_owner(self):
        return self.owner

    def get_stocks_list(self):
        return self.stocksList

    def get_amount_by_cost(self):
        return self.amountByCost

    def get_unrealized(self):
        return self.unrealized

    def get_unrealized_in_percentage(self):
        return self.unrealizedInPercentage

    def get_realized(self):
        return self.realized

    def get_cash_balance(self):
        return self.cashbalance

    def get_initial_cash(self):
        return self.initial_cash

    def get_prevous_day_max_dd(self):
        return self.prevousDay_maxDD

    def get_nav(self):
        return self.nav

    def get_max_nav(self):
        return self.max_nav

    def get_min_nav(self):
        return self.min_nav

    def get_max_draw_down(self):
        return self.max_Draw_down

    def get_number_of_wins(self):
        return sum(1 for rt in self.round_trips if rt["outcome"] == "win")

    def get_number_of_sells(self):
        return len(self.round_trips)

    def get_buy_order_count(self):
        return self.buy_order_count

    def get_sell_order_count(self):
        return self.sell_order_count

    def get_win_rate(self):
        return self._cal_winRate()

    def _avg_gain_loss(self):
        """(Avg Gain, Avg Loss) over completed Round-Trips, breakeven ones
        excluded. Avg Loss is a positive size (3000, not -3000), the way it
        appears in the Expected Payoff formula."""
        wins = [rt["realized_pnl"] for rt in self.round_trips if rt["outcome"] == "win"]
        losses = [rt["realized_pnl"] for rt in self.round_trips if rt["outcome"] == "loss"]
        avg_gain = (sum(wins) / len(wins)) if wins else 0.0
        avg_loss = (abs(sum(losses)) / len(losses)) if losses else 0.0
        return avg_gain, avg_loss

    def get_avg_gain(self):
        return self._avg_gain_loss()[0]

    def get_avg_loss(self):
        return self._avg_gain_loss()[1]

    def get_excess_return(self):
        """Return rate minus Benchmark Return, in percentage points -- None
        until the day's benchmark is known (see __init__)."""
        if self.benchmark_return is None:
            return None
        return self.calculate_roi() - self.benchmark_return

    def get_expected_payoff(self):
        """
        Expected Payoff = (Win Rate x Avg Gain) - (Loss Rate x Avg Loss),
        computed only over completed Round-Trips. Breakeven Round-Trips
        (net P&L exactly 0) are excluded, per the same rule as Win Rate.
        """
        counted = [rt for rt in self.round_trips if rt["outcome"] != "breakeven"]
        if not counted:
            return 0.0

        wins = sum(1 for rt in counted if rt["outcome"] == "win")
        losses = sum(1 for rt in counted if rt["outcome"] == "loss")

        win_rate = wins / len(counted)
        loss_rate = losses / len(counted)
        avg_gain, avg_loss = self._avg_gain_loss()

        return (win_rate * avg_gain) - (loss_rate * avg_loss)

    def get_all_stocks_info(self):
        """
        Returns a list of aggregated stock info dictionaries by symbol.
        Combines multiple lots of the same stock into a single summary row.
        """
        aggregated = defaultdict(
            lambda: {
                "Symbol": "",
                "Buy Price": 0.0,
                "Actual Volume": 0,
                "Total Cost": 0.0,
                "Market Value": 0.0,
                "Unrealized P&L": 0.0,
                "Realized P&L": 0.0,
                "Buy time": "",
                "Market Price": 0.0,
            }
        )

        for stock in self.stocksList:
            info = stock.get_stock_info()
            symbol = info["Symbol"]

            aggregated[symbol]["Symbol"] = symbol
            aggregated[symbol]["Buy Price"] = info["Buy Price"]
            aggregated[symbol]["Actual Volume"] += info["Actual Volume"]
            aggregated[symbol]["Total Cost"] += info["Amount Cost"]
            aggregated[symbol]["Market Value"] += info["Market Value"]
            aggregated[symbol]["Unrealized P&L"] += info["Unrealized P&L"]
            aggregated[symbol]["Realized P&L"] += info["Realized P&L"]
            aggregated[symbol]["Buy time"] = info["Buy time"]
            aggregated[symbol]["Market Price"] = info["Market Price"]

        result = []
        for sym_data in aggregated.values():
            actual_vol = sym_data["Actual Volume"]
            avg_cost = sym_data["Total Cost"] / actual_vol if actual_vol != 0 else 0.0
            unrealized_pct = (
                (sym_data["Unrealized P&L"] / sym_data["Total Cost"] * 100)
                if sym_data["Total Cost"] != 0
                else 0.0
            )

            result.append(
                {
                    "Symbol": sym_data["Symbol"],
                    "Buy Price": sym_data["Buy Price"],
                    "Actual Volume": actual_vol,
                    "Average Cost": avg_cost,
                    "Market Price": sym_data["Market Price"],
                    "Amount Cost": sym_data["Total Cost"],
                    "Market Value": sym_data["Market Value"],
                    "Unrealized P&L": sym_data["Unrealized P&L"],
                    "Unrealized %": unrealized_pct,
                    "Realized P&L": sym_data["Realized P&L"],
                    "Buy time": sym_data["Buy time"],
                }
            )

        return result

    def get_stock_by_symbol(self, symbol):
        return [stock for stock in self.stocksList if stock.get_symbol() == symbol]

    def get_total_stock_volume_by_symbol(self, symbol):
        total_volume = 0
        all_stocks_of_symbol = self.get_stock_by_symbol(symbol)
        for stock in all_stocks_of_symbol:
            total_volume += stock.get_actual_vol()
        return total_volume

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
                  Expected Payoff = Win Rate x Avg Gain - Loss Rate x Avg Loss.
                - "Average Exposure": float, average fraction (0-1) of NAV invested.
                - "Return rate": float, overall portfolio return (%).
                - "Benchmark Return": float or None, benchmark return (%) over the same window.
                - "Benchmark Max DD": float or None, benchmark max drawdown (%).
                - "Excess Return": float or None, Return rate - Benchmark Return.
                  The three benchmark fields stay None until the day's run is saved
                  (save_summary_csv), so a strategy never sees them mid-day.
        """

        return {
            "Owner": self.owner,
            "Number of Stocks": len(self.stocksList),
            "Total Cost": round(self.amountByCost, 2),
            "Unrealized P&L": round(self.unrealized, 2),
            "Unrealized %": round(self.unrealizedInPercentage, 2),
            "Realized P&L": round(self.realized, 2),
            "Cash Balance": round(self.cashbalance, 2),
            "Net Asset Value": round(self.nav, 2),
            "Max NAV": round(self.max_nav, 2) if self.max_nav is not None else None,
            "Min NAV": round(self.min_nav, 2) if self.min_nav is not None else None,
            "Max Drawdown (%)": (
                round(self.max_Draw_down, 2) if self.max_Draw_down is not None else None
            ),
            "Relative Drawdown": self._cal_relativeDrawdown(),
            "Calmar Ratio": self._cal_calmar_ratio(),
            "Previous Day Max DD (%)": (
                round(self.prevousDay_maxDD, 2)
                if self.prevousDay_maxDD is not None
                else None
            ),
            "Buy Order Count": self.get_buy_order_count(),
            "Sell Order Count": self.get_sell_order_count(),
            "Round-Trip Count": self.get_number_of_sells(),
            "Profitable Round-Trips": self.get_number_of_wins(),
            "Win Rate": self._cal_winRate(),
            "Expected Payoff": round(self.get_expected_payoff(), 2),
            "Avg Gain": round(self.get_avg_gain(), 2),
            "Avg Loss": round(self.get_avg_loss(), 2),
            "Average Exposure": round(self.get_average_exposure(), 4),
            "Return rate": self.calculate_roi(),
            "Benchmark Return": self.benchmark_return,
            "Benchmark Max DD": self.benchmark_max_dd,
            "Excess Return": self.get_excess_return(),
        }

    def get_All_stock_count_by_symbol(self):
        """
        Returns a dict mapping symbol -> number of buy entries in stocksList.
        Each entry counts as one buy regardless of volume.
        """
        buy_count = defaultdict(int)
        for stock in self.stocksList:
            symbol = stock.get_symbol()
            buy_count[symbol] += 1
        return dict(buy_count)

    def export_stocks_to_csv(self):
        stocks = self.get_all_stocks_info()
        if not stocks:
            print("No stock in portfolio")
            return

        keys = ["Symbol", "Actual Volume", "Buy Price", "Buy time"]

    def save_to_file(self, owner):

        filename = owner + "_" + "portfolio.json"
        folder_path = os.path.join("result", self.owner)
        os.makedirs(folder_path, exist_ok=True)

        filename = os.path.join(folder_path, filename)

        data = {
            "owner": self.owner,
            "cashbalance_start": self.cashbalance_start,
            "cashbalance": self.cashbalance,
            "realized": self.realized,
            "stocksList": [stock.to_dict() for stock in self.stocksList],
            "round_trips": self.round_trips,
            "buy_order_count": self.buy_order_count,
            "sell_order_count": self.sell_order_count,
            "daily_snapshots": self.daily_snapshots,
            "prevousDay_maxDD": self.prevousDay_maxDD,
            "max_nav": self.max_nav,
            "min_nav": self.min_nav,
        }
        with open(filename, "w") as f:
            json.dump(data, f, indent=4, default=str)

    def save_summary_csv(self, daily_ticks_timestamp, benchmark_return=None, benchmark_max_dd=None):
        # Define folder and filename
        folder_path = os.path.join("result", self.owner)
        os.makedirs(folder_path, exist_ok=True)
        summary_file = os.path.join(folder_path, f"{self.owner}_portfolio_summary.csv")
        self.benchmark_return = benchmark_return
        self.benchmark_max_dd = benchmark_max_dd

        # Calculate derived stats
        num_stocks = len(self.stocksList)
        total_cost = sum(stock.amount_cost for stock in self.stocksList)
        unrealized = sum(stock.unrealized for stock in self.stocksList)
        unrealized_percent = (unrealized / total_cost * 100) if total_cost else 0
        nav = self.get_nav()
        max_nav = self.max_nav
        min_nav = self.min_nav
        max_dd = self.max_Draw_down  # in %
        relative_dd = self._cal_relativeDrawdown()
        calmar = ((nav - 10000000) / 10000000) / abs(max_dd / 100) if max_dd != 0 else 0
        win_rate = self._cal_winRate()
        expected_payoff = self.get_expected_payoff()
        avg_exposure = self.get_average_exposure()
        return_rate = ((nav - 10000000) / 10000000 * 100)  # assuming 10M initial

        if benchmark_return is not None:
            excess_return = return_rate - benchmark_return
        else:
            excess_return = ""
        benchmark_return_out = benchmark_return if benchmark_return is not None else ""
        benchmark_max_dd_out = benchmark_max_dd if benchmark_max_dd is not None else ""

        # Prepare row
        row = [
            self.owner,
            num_stocks,
            round(total_cost, 2),
            round(unrealized, 2),
            round(unrealized_percent, 1),
            round(self.realized, 2),
            round(self.cashbalance_start, 2),
            round(self.cashbalance, 2),
            round(nav, 2),
            round(max_nav, 2),
            round(min_nav, 2),
            round(max_dd, 2),
            relative_dd,
            calmar,
            round(self.prevousDay_maxDD, 2),
            self.get_buy_order_count(),
            self.get_sell_order_count(),
            self.get_number_of_sells(),
            self.get_number_of_wins(),
            round(win_rate, 1),
            round(expected_payoff, 2),
            round(avg_exposure, 4),
            round(return_rate, 10),
            round(benchmark_return_out, 4) if benchmark_return_out != "" else "",
            round(benchmark_max_dd_out, 4) if benchmark_max_dd_out != "" else "",
            round(excess_return, 4) if excess_return != "" else "",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            daily_ticks_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        ]

        # Write header and row
        header = [
            "Owner", "Number of Stocks", "Total Cost", "Unrealized P&L", "Unrealized %",
            "Realized P&L", "cashbalance start", "Cash Balance", "Net Asset Value", "Max NAV", "Min NAV",
            "Portfolio Maximum Drawdown (%)", "Relative Drawdown", "Calmar Ratio",
            "Previous Day Max DD (%)", "Buy Order Count", "Sell Order Count",
            "Total Round-Trip", "Profitable Round-Trip", "Win Rate", "Expected Payoff",
            "Average Portfolio Exposure", "Portfolio Total Return", "Benchmark Return", "Benchmark Maximum Drawdown",
            "Excess Return", "Saved At", "Daily Ticks Time"
        ]

        write_header = not os.path.exists(summary_file)

        with open(summary_file, mode='a', newline='') as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(header)
            writer.writerow(row)

        

    @classmethod
    def load_from_file(cls, owner):

        file_path = os.path.join("result", owner, owner + "_" + "portfolio.json")

        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Portfolio file for {owner} does not exist: {file_path}"
            )

        with open(file_path, "r") as f:
            data = json.load(f)
            stocks_data = data["stocksList"]
            stocksList = [Stock.stock.from_dict(d) for d in stocks_data]
        return cls(
            owner=data["owner"],
            stocksList=stocksList,
            cashbalance=data["cashbalance"],
            cashbalance_start=data["cashbalance"],
            realized=data["realized"],
            round_trips=data.get("round_trips", []),
            buy_order_count=data.get("buy_order_count", 0),
            sell_order_count=data.get("sell_order_count", 0),
            daily_snapshots=data.get("daily_snapshots", []),
            prevousDay_maxDD=data.get("prevousDay_maxDD", None),
            max_nav=data.get("max_nav"),
            min_nav=data.get("min_nav"),
        )