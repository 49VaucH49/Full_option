# **Trading Simulator**

This simulation platform is built in Python OOP, which is designed to simulate a realistic trading environment using the SET50 daily ticks dataset. It supports core functionalities such as order matching, real-time data streaming, portfolio management, fee calculations, and an automated CI pipeline that validates and sandboxes every strategy submission, providing a practical foundation for developing and testing algorithmic trading strategies.

Each trader is provided with an initial cash balance of 10,000,000 baht upon portfolio creation. This amount represents the trader's total available capital for the entire competition. Participants are expected to maximize profits by designing and implementing efficient trading algorithms to compete against other teams.

**Feature contained in the simulation:**

- Stock & portfolio management:
  * Initiate & Load portfolio information.
  * Create summarized portfolio information throughout the day of trading.
  * Update the stock market value along with a streaming system.
  * Calculation of the necessary information for creating strategies.
    * Amount Cost
    * Average cost of stock in the portfolio
    * Unrealized & Unrealized in percentage
    * Realized
    * NAV (Net Asset Value)
    * Max drawdown
    * Calmar ratio
    * Round-Trip count, Win Rate, Expected Payoff, Average Exposure (see [Accessing Portfolio Data](#accessing-portfolio-data))
- Ordering & matching during the streaming of the trading market:
  * Creating an order for selling or buying stock in the market
    * Ordered stock must be in SET50 & volume required to be in full stock unit at least 100 volume (able to be mod by 100), and unable to order partial volume of stock
      For example, 100 volume is acceptable, but 150 (150 % 100 = 50) cannot be ordered.
    * Ordering stock must be in either Buy or Sell.
    * When an order buys stocks from the market, if the trader's portfolio doesn't have enough cash balance, the order will be rejected.
    * When an order sells stock from the market, if the portfolio of trade doesn't have enough volume of stock in its portfolio, the order will be rejected.
  * Matching the order with the market streaming situation:
    * A limit order that doesn't fill right away rests in the order book and is tried again on every later tick of its stock, until it fills, you cancel it, or the trading day ends — see [Create order to limit](#create-order-to-limit) and [Managing resting orders](#managing-resting-orders).
- **Automated CI validation**: every push to your team repo is automatically checked (syntax, structure, forbidden imports/calls, team-name match, and a real dry-run against sample tick data) before it is trusted for the daily official run. See [Automated Submission Checks (CI)](#automated-submission-checks-ci).

**Where the "real" result comes from:** the numbers that count are produced by the organizers' daily run against the day's real tick data on their own machine (VPS), from whatever version of your strategy last passed CI. Anything you run on your own computer (this notebook included) is for practice/debugging only.

&nbsp;

# **Installing dependency**

Before you can run the trading simulator, you need to install the required dependencies. Follow the steps below to set up your Python environment properly:

1. Ensure Python **3.13.x** is installed — the engine's dependencies, in particular `TA-Lib`, only ship a prebuilt wheel for `cp313`; on any other Python version `pip install` will fail to find a wheel and try to build from source instead.
   1. (Optional) Install [pyenv](https://github.com/pyenv/pyenv) to handle multiple Python versions.
2. Download the full engine (`tradeSim` + a sample tick dataset), `tradeSim<version>.zip`, from the **Google Drive link the organizers sent you**, and extract it straight into your team repo's folder. Watch out for Windows' "Extract All": it suggests a path ending in a new `tradeSim<version>` folder — remove that part, or the notebook ends up in a subfolder and cannot find your strategy in `strategy/`.
3. (Recommended) Create and activate a virtual environment inside your team repo's folder. Name it `.venv` — the repo's `.gitignore` already excludes that name, so `git add .` will not pick up its ~400MB:

   ```powershell
   cd path\to\<UNI>-<TEAM>
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

4. Install required dependencies using the provided requirements.txt file (~80MB download — the engine, `numpy`/`pandas`, the technical-analysis libraries, and Jupyter itself — open the notebook with `jupyter notebook`, or in VS Code by picking the `.venv` kernel):

   ```powershell
   pip install -r requirements.txt
   ```

   If this fails with `OSError: [Errno 2] No such file or directory` and a hint about **Windows Long Path support**, the folder path is too deep: some installed files sit ~125 characters below `site-packages`, and Windows stops at 260. Move the repo somewhere shorter (e.g. `C:\TradeSim\<UNI>-<TEAM>`) and try again. The Microsoft Store build of Python installs packages under a very long path and is the most likely to hit this — prefer the installer from python.org.

   The machine-learning, statistics and optimization libraries are in a separate `requirements-optional.txt` (~240MB). Skip it until your strategy actually imports one of them, then run `pip install -r requirements-optional.txt`. The official runner has both installed.

5. If the Jupyter kernel is running, restart the kernel.

**This is only for your own local practice.** Once your strategy is pushed, the official runner already has every allowed library pre-installed. **You cannot `pip install` anything yourself as part of the competition** (installing a package can run arbitrary code, which a sandboxed strategy file cannot). See [Allowed libraries](#allowed-libraries) for the full pre-installed list.

**Need a library that isn't on the list? Ask early.** If your team needs a library that isn't pre-installed, let the organizers know **before the competition starts**, not after — there is no way to request or install one mid-competition through a push. Reach out with the exact package name (and ideally why you need it) so the organizers have time to test and add it to `requirements.txt` ahead of time if approved.

<a id="introduction-to-tradesim"></a>

# **Introduction to TradeSim**

`TradingSimulation.ipynb` runs your strategy against one trading day of real tick data on your own machine, the same way the organizers' daily run does. Run the code cells from top to bottom. The cells, in order:

| Cell | What it does |
|---|---|
| 1 | Imports |
| 2 | Loads the tick file for the day you want to practise on |
| 3 | Team name, strategy name, `fresh_start` — and creates the portfolio |
| 4 | Imports your strategy file |
| 5 | `with_visual` — live tables (`True`) or headless (`False`, much faster) |
| 6 | **The simulation** — streams every tick through your strategy, then saves the day |
| 7–8 | Portfolio summary and current holdings |
| 9 | **Run Several Days in a Row** (optional) — see [below](#run-several-days-in-a-row) |

**Cell 2 — pick the day.** The practice data you downloaded with the engine has one file per trading day in `marketInfo/ticks/`:

```python
#TODO: Change ticks information daily
daily_ticks = "./marketInfo/ticks/2026-09-09.csv"
```

**Cell 3 — names and `fresh_start`.**

```python
#TODO: Replace with your team name
team_name = "example"
strategy_name = "Example_strategy"
# True  = start from a fresh 10,000,000 every time this cell runs (deletes result/<team_name>/)
# False = carry on from the saved portfolio -- use this when practising one day at a time
fresh_start = True
```

* `strategy_name` is your strategy's file name without `.py` (and therefore also its class name).
* `team_name` only names the local results folder, `result/<team_name>/`. The team name that counts for the competition is the first argument to `super().__init__()` inside your strategy file — that is the one CI checks against the roster (see [Automated Submission Checks (CI)](#automated-submission-checks-ci), item 4). Using the same name in both places avoids confusion.
* Names may contain only letters, digits, `-` and `_`, at most 30 characters.
* The day being simulated is passed to the engine as `current_date` here. It powers the anti-lookahead guarantee of [`get_historical_data()`](#get_historical_datasymbol-n): a strategy can never see the simulated day's own data.

**Your portfolio is saved between runs.** At the end of cell 6 the portfolio (cash, holdings, trade counts, daily NAV history) is written to `result/<team_name>/<team_name>_portfolio.json`, and cell 3 loads it back the next time it runs — exactly how the official run carries your portfolio from one day to the next. `fresh_start` decides which you get:

* `fresh_start = True` (the default): cell 3 deletes `result/<team_name>/` first, so every run starts from 10,000,000. Use this while trying out or changing a strategy.
* `fresh_start = False`: cell 3 loads the saved portfolio and carries on. Use this to practise day by day: change the date in cell 2, then run cells 2 → 8 again. Cell 3 prints `Loaded existing portfolio from ...` when it did load one, and `Created new portfolio` when it started fresh.

**Always start again from cell 3.** The portfolio is created in cell 3, not in cell 6 — re-running cell 6 alone replays the same day on top of the portfolio already in memory, and every order is counted twice. After editing your strategy file, re-run cell 4 as well, or the old version of your code is used. The simplest habit: run cells 2 → 8 every time.

**Cell 4 — import your strategy.** If the file is missing, or has no class named exactly like the file, this cell raises an error that says which of the two it is — fix it before going on, the simulation cannot run without a strategy.

**Cell 5 — visual or headless.**

* `with_visual = True` (the default): live-updating market and portfolio tables while ticks stream in — good for watching what your strategy does.
* `with_visual = False`: no tables, much faster. This is how the official daily run works.

**Cell 6 — the simulation.** Streams every tick of the day to your strategy (`on_data` is called on every tick of every symbol), matches pending orders against the market, then saves the transaction log, the day's summary and the portfolio into `result/<team_name>/`.

**Cells 7–8 — the results.** Cell 7 shows `strategy_runner.get_portfolio_info()` (see [Get information from the portfolio](#get_portfolio_info)) and cell 8 the holdings table from `get_all_stocks_info()`.

<a id="run-several-days-in-a-row"></a>

## **Run Several Days in a Row**

Cell 9 runs the strategy loaded in cell 4 over several days back to back, carrying the portfolio from each day to the next — so a position bought on one day can be sold on a later one. Run cells 1–4 first, then this cell; it runs headless and ends with a table of one row per day.

```python
#TODO: The days to run, oldest first
trading_days = ["2026-09-09", "2026-09-10", "2026-09-11", "2026-09-14",
                "2026-09-15", "2026-09-16", "2026-09-17"]
# True  = delete result/<team_name>/ first, so the run starts from a fresh 10,000,000
# False = carry on from whatever portfolio is already saved there
fresh_start = True
```

This cell has its own `fresh_start`, independent of the one in cell 3. Buy/Sell/Round-Trip counts in the table are running totals since the portfolio started, not per day. A week of practice data takes about a minute or two.

**Local runs are practice only.** Nothing in `result/` is sent anywhere. The results that count come from the organizers' daily run on the VPS, which is also what writes `RESULTS.md` into your repo.

# 

<a id="implementing-a-strategy"></a>

# **Implementing a Strategy**

All custom strategies must be implemented inside the strategy/ directory. You will find two important Python files:

* Strategies\_template.py: the abstract base class you must inherit from
* Example\_strategy.py: a basic example to help you get started

TODO: Create your strategy class; you need to inherit from Strategies\_template.py

**Strategies\_template.py: The Base Class**
This file defines the strategy interface. Your strategy must inherit from Strategy\_template, pass a `timeframe` to the constructor, and implement the required on\_data() method:

| from abc import ABC, abstractmethodfrom datetime import timedeltaclass Strategy\_template(ABC):    def \_\_init\_\_(self, owner, strategy\_name, handler, timeframe):        self.owner \= owner        self.strategy\_name \= strategy\_name        self.handler \= handler        self.timeframe \= timeframe    @abstractmethod    def on\_data(self, bar):        """        Called once per tick with the CURRENT (live-updating) OHLCV bar        for self.timeframe -- {"ShareCode", "Timestamp", "Open", "High",        "Low", "Close", "Volume"}. Never waits for the bar to close.        MUST be implemented by subclass.        DO NOT EDIT THIS CLASS.        """        pass |
| :---- |

**Example\_strategy.py: A Sample Strategy**
The following class is a simple example of a custom strategy that buys and sells selected stocks based on basic rules:

| from strategy.Strategies\_template import Strategy\_templateclass Example\_strategy(Strategy\_template):    def \_\_init\_\_(self, handler):        super().\_\_init\_\_("example", "Example\_strategy", handler, timeframe="1min")        self.buy\_counts \= {s: 0 for s in \["ADVANC", "AOT", "AWC", "BANPU", "BBL"\]}        self.sell\_counts \= {s: 0 for s in \["ADVANC", "AOT", "AWC", "BANPU", "BBL"\]}    def on\_data(self, bar):        symbol \= bar\['ShareCode'\]        price \= bar\['Close'\]        if symbol in self.buy\_counts or symbol in self.sell\_counts:            if not self.handler.check\_port\_has\_stock(symbol, 100):                self.handler.create\_order\_to\_limit(100, price, "Buy", symbol)            else:                stocks \= self.handler.get\_stock\_by\_symbol(symbol)                if stocks:                    buy\_price \= stocks\[0\].get\_buy\_price()                    if price \< buy\_price:                        self.handler.create\_order\_to\_limit(100, price, "Sell", symbol) |
| :---- |

## **To ensure your strategy is loaded correctly, the following naming rules must be strictly followed**

The names that count are the ones inside your strategy file. (The `team_name`/`strategy_name` in cell 3 of `TradingSimulation.ipynb` only tell the notebook which file to load and where to save local results — see [Introduction to TradeSim](#introduction-to-tradesim). Keeping them the same as below avoids confusion.)

* Team\_name must be the first parameter in the class constructor.
* Strategy\_name must be the second parameter in the class constructor, and the class name.
* **The class name must also match the `.py` file name exactly** (file `MyTeam.py` → `class MyTeam(...)`).
* **`team_name` (the `owner` you pass to `super().__init__()`) must match the team name registered with the organizers in `teams_roster.csv`, exactly (case-sensitive)** — CI cross-checks it automatically, and a mismatch means your daily results get filed under the wrong name (or CI fails) instead of ending up in your `RESULTS.md`.

| class MyTeam(Strategy\_template):    def \_\_init\_\_(self, handler):        super().\_\_init\_\_("my\_team", "MyTeam", handler, timeframe="5min") |
| :---- |

The strategy\_name must also match the Python file name (without the .py extension)

## **`timeframe` and the bar resolution `on_data` runs on**

`on_data` receives an OHLCV **bar** for whatever `timeframe` you pass to `super().__init__()`, similar to subscribing to a candlestick feed on a real broker API. `timeframe` is any [pandas offset alias](https://pandas.pydata.org/docs/user_guide/timeseries.html#offset-aliases) string, e.g. `"1min"`, `"5min"`, `"15min"`, `"1D"` — an invalid alias errors immediately at runtime.

**`on_data` fires on every tick, not only when a bar closes.** The `bar` you receive is the bar *currently forming*: its `High`/`Low`/`Close`/`Volume` keep updating every time a new tick lands inside the same time window, until the timestamp rolls over to the next bar. If your logic should only act once per closed bar, you have to detect that yourself by comparing timestamps, e.g.:

```python
def __init__(self, handler):
    super().__init__("my_team", "MyTeam", handler, timeframe="5min")
    self._last_seen_timestamp = None

def on_data(self, bar):
    is_new_bar = bar["Timestamp"] != self._last_seen_timestamp
    self._last_seen_timestamp = bar["Timestamp"]
    if is_new_bar:
        pass  # previous bar just closed
    else:
        pass  # still the same bar, being updated live
```

<a id="automated-submission-checks-ci"></a>

## **Automated Submission Checks (CI)**

Every push to your team's repository is automatically validated before your strategy is trusted for the daily official run. Checked in this order — it stops at the first failure:

1. **Syntax** — does the file parse at all.
2. **Structure** — exactly one top-level class, its name matches the file name, it inherits `Strategy_template`, and it implements `on_data`.
3. **Forbidden imports/calls** — see the list below.
4. **Team name match** — the `owner` passed to `super().__init__()` must match your team's registered name in `teams_roster.csv`.
5. **Dry-run** — your file is actually imported and run against a small sample tick file in a subprocess with a timeout, to prove it runs end-to-end without crashing (this does **not** count toward your score — it just proves the code runs).

**A green check does not mean your strategy logic works.** The dry-run has no historical data, so `get_historical_data()` returns `[]` there every time — any code that only runs once history is available (e.g. after `if len(history) < N: return`) is never exercised by CI. Run `TradingSimulation.ipynb` against real data before you push. The official daily run allows **15 minutes per team per day** (a normal day takes ~20 seconds); a run that errors or exceeds that falls back to your team's previous version.

Checks run on every push to any branch, but only the code on your **`main`** branch competes. Open the **Checks** tab on your commit in GitHub: green = passed, red = this version is **not** used — the official run keeps using your last version that passed, so open the log for the exact error, fix it and push again.

**The daily deadline is 09:30 Bangkok time on the trading day.** Each trading day is run with your `main` branch as it stood at 09:30 that morning: a push before 09:30 counts for that day, a push at or after 09:30 counts for the next trading day. What counts is the time GitHub received the push, not the date written in the commit. The organizers run each day's simulation after the market has closed (normally the next business morning), so `RESULTS.md` appears a day behind — that does not move the deadline.

**Forbidden — will fail validation immediately if present anywhere in your strategy file:**

- **Imports**: `os`, `sys`, `subprocess`, `socket`, `shutil`, `requests`, `urllib`, `http`, `ftplib`, `importlib`, `ctypes`, `multiprocessing`, `threading`, `pathlib`
- **Calls**: `eval`, `exec`, `compile`, `__import__`, `open`

Reason: your strategy runs inside a sandbox and must never touch the filesystem, network, or another process directly — anything you need from a file must go through `self.handler` (see [Attaching a model/config file](#attaching-a-modelconfig-file) below).

You are only allowed to modify/implement your own strategy file (which inherits from `Strategies_template.py`) — **never** `Strategies_template.py` itself, order-matching/portfolio logic, or anything else in the engine. See [Penalties](#penalties-for-unauthorized-modification-of-the-trading-system) below for what happens otherwise.

## 

<a id="a-guide-to-create-a-buysell-order"></a>

## **A guide to create a buy/sell order**

To place an order in your strategy, use the method provided by the handler object. There are two variations of the create order method you can use: create\_order\_to\_limit() and create\_order\_at\_market()

**The parameter:**

| Parameter | Type | Description |
| :---- | :---- | :---- |
| volume | int | Must be a multiple of 100 (e.g., 100, 200). |
| price | float | The price at which you want to trade. |
| side | string | Either "Buy" or "Sell" (case-insensitive). |
| symbol | str | Stock symbol (e.g., "AOT", must be in the SET50). |

&nbsp;

### **Create order to limit** Place an order at a price you choose. It fills only at your price or a better one — never worse. If someone in the market is already trading at your price it fills on the current tick; otherwise it waits in the order book until someone trades at your price. Use it when the price matters more than filling right away.

| create\_order\_to\_limit(volume, price, side, symbol) |
| :---- |

Example usage:

| self.handler.create\_order\_to\_limit(100, 35.67, "Buy", "AOT") self.handler.create\_order\_to\_limit(100, 39.89, "Sell", "PTT") |
| :---- |

<a id="create-order-to-limit"></a>

**How a limit order is matched.** Every tick says which side started the trade (the `Flag` column of the tick data). `Buy` means a buyer took a seller's offer, so someone was **offering** at that price. `Sell` means a seller hit a buyer's bid, so that price was the **bid**, and the cheapest offer is about one price step higher. "One price step" is 0.25 around 60 baht and 1.00 around 250.

| | Buy limit | Sell limit |
|---|---|---|
| **When placed** — fills at once if | the offer is at or below your price (`Buy` tick: offer = last price · `Sell` tick: offer = last price + one step) | the bid is at or above your price (`Sell` tick: bid = last price · `Buy` tick: bid = last price − one step) |
| You pay / receive | the offer — your price or better | the bid — your price or better |
| **Otherwise it rests**, and fills once | the market trades at or below your price | the market trades at or above your price |
| You pay / receive | your price | your price |

Fees (commission 0.157% + VAT 7% of it) come on top of every fill.

Example, last price 62.75 for a Buy: on a `Buy` tick a limit at 62.75 fills at once at 62.75; on a `Sell` tick the same order waits; a limit at 63.50 fills at once on either tick, at 62.75 or 63.00 respectively — never at 63.50.

- **Auction ticks** (`OPEN1_E`, `OPEN2_E`, `ATC`) have no side and never fill a limit order.
- **A resting order lasts for the trading day.** Each day starts with an empty order book; orders still waiting at the close are gone.
- **Orders fill in the order you placed them.** When the price arrives, the engine checks your cash (Buy) or holdings (Sell) again. If they are no longer enough — for example you already spent the cash, or two Sell orders wait on the same 100 shares — that order is cancelled.
- **Every call places a new order.** A strategy that calls `create_order_to_limit` on every tick while a condition holds piles up resting orders, and they can all fill later. Check [`get_open_orders()`](#managing-resting-orders) first, or cancel what you no longer want.
- A limit at `bar["Close"]` is **not** guaranteed to fill — on a `Sell` tick it waits. When the strategy has to get in or out now, use a market order.
- "created successfully" means the order passed validation (cash, holdings, volume) and is in the order book, not that it filled. Check with [`check_port_has_stock()`](#check_port_has_stocksymbol-volume) or [`get_all_stocks_info()`](#get_all_stocks_info).

### **Create order at the market** Fill right away, whatever side the tick was: a Buy pays the latest price plus one price step, a Sell receives the latest price minus one step (plus fees either way). The step stands in for crossing the spread to the other side's best price. Only for the stock of the current bar. Use it when filling now matters more than the price.

| create\_order\_at\_market(volume, side, symbol) |
| :---- |

Example usage:

| self.handler.create\_order\_at\_market(1000, "Buy", "AOT") self.handler.create\_order\_at\_market(5000, "Sell", "PTT") |
| :---- |

A market order fills at the latest price of the bar being processed, so it can only be placed for **that bar's stock** (`bar["ShareCode"]`). Called from AOT's `on_data` for any other symbol, it is rejected with `[ERROR] Market order for PTT ... skipped: ...` and nothing is bought.

On success it returns `Market order for AOT (Vol: 1000, Price: 62.5, Side: Buy) submitted successfully.` — like a broker's confirmation, this means the order was **accepted**, not that it filled. Check what you actually hold with [`check_port_has_stock()`](#check_port_has_stocksymbol-volume) or [`get_all_stocks_info()`](#get_all_stocks_info).

### **Return value from Create order** Both create\_order\_to\_limit() and create\_order\_at\_market() return a string message that indicates whether the order was successfully placed or rejected. This allows your strategy to confirm the outcome of the order and handle errors appropriately. Example of a valid order:

| order\_result \= self.handler.create\_order\_to\_limit(100, 58, "Buy", "AOT")print(order\_result) |
| :---- |

### Output:

| Order 20260909-ORD00012 for AOT (Vol: 100, Price: 58.0, Side: Buy) created successfully. |
| :---- |

The order number at the start (`20260909-ORD00012`) is what [`cancel_order()`](#managing-resting-orders) takes.

### If the order is invalid, such as due to insufficient holdings or an incorrect volume, it will not be registered. Instead, an error message will be returned with the reason. Example of invalid order:

| order\_result \= self.handler.create\_order\_to\_limit(500, 58, "Sell", "AOT")print(order\_result) |
| :---- |

## Output:

| \[ERROR\] Order for AOT (Vol: 500, Price: 58.0, Side: Sell) skipped due to Cannot sell AOT as it is not in the portfolio or insufficient volume. |
| :---- |

An order can also be rejected for reasons beyond the two shown above — the same mechanism reports all of them the same way (`[ERROR] ... skipped due to <reason>`):

| Reason string | When |
| :---- | :---- |
| Volume must be a multiple of 100. | volume isn't a multiple of 100 |
| Invalid side '\<side\>'. Must be 'Buy' or 'Sell'. | side isn't Buy/Sell |
| Symbol '\<symbol\>' is not one of the tradable SET50 stocks ... | symbol not in the SET50 list |
| '\<symbol\>' is a market index, not a tradable stock ... | tried to order an index (SET, SET50, ...) instead of a stock |
| Insufficient cash balance to cover transaction costs. | Buy order, not enough cash (commission/VAT included) |
| Cannot sell \<symbol\> as it is not in the portfolio or insufficient volume. | Sell order, not enough held volume |
| Order's buy volume exceeds the cumulative sell volume from the daily ticks. | Buy order larger than the market's own matched sell volume so far that tick |
| Order's sell volume exceeds the cumulative buy volume from the daily ticks. | Sell order larger than the market's own matched buy volume so far that tick |

<a id="managing-resting-orders"></a>

### **Managing resting orders**

Limit orders that haven't filled yet wait in the order book. These three methods let your strategy see and cancel them. They cover the whole team's order book, so pass `bar["ShareCode"]` when a strategy should only touch its own stock's orders.

| Method | Returns |
| :---- | :---- |
| `get_open_orders(symbol=None)` | list of dicts, oldest first — one per resting order: `Order Number`, `Type`, `Symbol`, `Side`, `Volume`, `Price` (your limit), `Timestamp` (when placed), `owner`. With `symbol`, only that stock's orders. |
| `cancel_order(order_number)` | `True` if the order was resting and is now removed; `False` if it already filled, was already cancelled, or never rested. |
| `cancel_all_orders(symbol=None)` | how many orders were removed — all of them, or only `symbol`'s. |

Example: wait for a dip with one resting Buy per stock, and withdraw it once the signal is gone.

```python
def on_data(self, bar):
    symbol = bar["ShareCode"]
    waiting = self.handler.get_open_orders(symbol)

    if not self.wants_to_buy(symbol):
        if waiting:
            self.handler.cancel_all_orders(symbol)   # signal gone: stop waiting
        return

    if not waiting and not self.handler.check_port_has_stock(symbol, 100):
        self.handler.create_order_to_limit(100, self.dip_price[symbol], "Buy", symbol)
```

<a id="reading-the-transaction-log"></a>

### **Reading the transaction log**

Every fill is written to `result/<team>/<team>_transaction_log.csv`, one row each. `Order Price` next to `Price` shows what you asked for and what you got.

| Column | Meaning |
| :---- | :---- |
| `Order Number` · `owner` | the order and your team |
| `Type` | `Limit` or `Market` |
| `Side` · `Symbol` · `Volume` | what was traded |
| `Order Price` | the price you set (limit), or the last price when you placed it (market) |
| `Market Price` | the last price of the tick it filled on |
| `Price` | what you actually paid / received per share, before fees |
| `Placed` | when the order was placed |
| `Timestamp` | when it filled |

A market Buy shows `Price` one step above `Order Price`; a limit Buy shows `Price` at or below `Order Price`, and `Placed` earlier than `Timestamp` if it had to wait.

### **Accessing information in the `bar` passed to `on_data`**

The `bar` parameter passed to your strategy's on\_data() method is the current (live-updating) OHLCV candlestick for the `timeframe` you chose in `super().__init__()`. See [`timeframe` and the bar resolution `on_data` runs on](#timeframe-and-the-bar-resolution-on_data-runs-on) above for how it behaves tick-to-tick.

**Sample structure of `bar`:**

| {    'ShareCode': 'AOT',    'Timestamp': '2025-11-24 10:35:00',    'Open': 30.00,    'High': 30.75,    'Low': 29.75,    'Close': 30.50,    'Volume': 45600,} |
| :---- |

**The data can be accessed as follows:**

| symbol \= bar\["ShareCode"\]price \= bar\["Close"\]timestamp \= bar\["Timestamp"\]volume \= bar\["Volume"\] |
| :---- |

**The following are key data from `bar`:**

| Key | Type | Description |
| :---- | :---- | :---- |
| ShareCode | str | Stock symbol (e.g., "AOT") |
| Timestamp | str | Start time of the current (possibly still-forming) bar. |
| Open | float | Opening price of this bar. |
| High | float | Highest price seen in this bar so far. |
| Low | float | Lowest price seen in this bar so far. |
| Close | float | Most recent price in this bar so far. |
| Volume | int | Total volume traded within this bar so far. |

&nbsp;

**Note:** `bar` is effectively read-only from your strategy's point of view — assigning into it does not affect the simulation.

<a id="accessing-portfolio-data"></a>

# **Accessing Portfolio Data**

The following methods are available for participants to inspect the current state of their portfolio. These can be used during or after the simulation to monitor holdings, cash balance, or export results.

<a id="get_portfolio_info"></a>

## **Get information from the portfolio**

| get\_portfolio\_info() |
| :---- |

A competitor can retrieve a summary of portfolio information from this method.

Return:

- Summary of information in portfolio

Example:

| pprint(self.handler.get\_portfolio\_info()) |
| :---- |

Output:

| {'Owner': 'Testing', 'Number of Stocks': 0, 'Total Cost': 0.0, 'Unrealized P\&L': 0.0, 'Unrealized %': 0.0, 'Realized P\&L': 74723.68, 'Cash Balance': 10074723.68, 'Net Asset Value': 10074723.68, 'Max NAV': 10104164.72, 'Min NAV': 7230540.27, 'Max Drawdown (%)': 28.44, 'Relative Drawdown': 0.2844, 'Calmar Ratio': 0.026274, 'Previous Day Max DD (%)': 28.44, 'Buy Order Count': 8, 'Sell Order Count': 8, 'Round-Trip Count': 8, 'Profitable Round-Trips': 8, 'Win Rate': 100.0, 'Expected Payoff': 9340.46, 'Avg Gain': 9340.46, 'Avg Loss': 0.0, 'Average Exposure': 0.3120, 'Return rate': 0.747237, 'Benchmark Return': None, 'Benchmark Max DD': None, 'Excess Return': None} |
| :---- |

**Important distinction — read carefully:**

- `Profitable Round-Trips` / `Round-Trip Count` count **completed Round-Trips** (a fully-closed FIFO lot: bought then fully sold), **not** the number of sell orders you placed.
- `Sell Order Count` / `Buy Order Count` count actual **orders executed**, regardless of how many Round-Trips they closed.
- `Win Rate` excludes Round-Trips with exactly zero net P\&L.
- `Average Exposure` is a fraction (0–1) of NAV invested in the market, averaged across all trading days so far (`0.3120` = 31.20%).
- `Expected Payoff` is the average P\&L per completed Round-Trip.
- `Avg Gain` is the average P\&L of a winning Round-Trip and `Avg Loss` the average size of a losing one's loss, as a **positive** number (`3000`, not `-3000`); breakeven Round-Trips count in neither. Together with `Win Rate` they rebuild `Expected Payoff`: `Win Rate × Avg Gain − Loss Rate × Avg Loss`, where `Loss Rate = 100% − Win Rate`.
- `Return rate` is the portfolio's return (%) since it started. `Benchmark Return` / `Benchmark Max DD` measure the SET50 index over the same days, and `Excess Return = Return rate − Benchmark Return` (percentage points). All three are **always `None` while the simulation is running** — today's benchmark needs today's closing index level, which a strategy must not see before the day ends. They are filled in once the day is saved, so you see them in the notebook's results (cell 7), never from inside `on_data`.
- `Max NAV` / `Min NAV` are the **peak and trough behind `Max Drawdown`**, measured on end-of-day NAV only (updated once per day, not per tick). `Min NAV` is the lowest NAV **since the most recent peak**: every new peak resets it to the same value as `Max NAV`, so it is not the all-time low. Earlier drawdowns are not lost — `Max Drawdown (%)` keeps the largest one seen so far. On the first day of a portfolio both equal that day's NAV.

These four (`Round-Trip Count`/`Win Rate`/`Expected Payoff`/`Average Exposure`), together with `Max Drawdown`, are also exactly the metrics used for the qualification criteria when the organizers rank results — see the "Common Criteria" thresholds in [`competitor_guide.md`](competitor_guide.md).

<a id="get_all_stocks_info"></a>

## **Get information from the stocks in the portfolio**

| get\_all\_stocks\_info() |
| :---- |

Competitors can retrieve information about their stocks that are in their portfolio from this method.

Return:

- Dicts of all stock information in the portfolio

Example:

| pprint(self.handler.get\_all\_stocks\_info()) |
| :---- |

Output:

| \[{'Symbol': 'AOT', 'Buy Price': 35.23, 'Actual Volume': 200, 'Average Cost': 0.0, 'Market Price': 35, 'Amount Cost': 0.0, 'Market Value': 0.0, 'Unrealized P\&L': 0.0, 'Unrealized %': 0.0, 'Realized P\&L': 0.0, 'Buy time': '2025-06-23 11:27:53'}\] |
| :---- |

## 

<a id="get_stock_by_symbolsymbol"></a>

## **Get information from the stocks in the portfolio by symbol**

| get\_stock\_by\_symbol(symbol) |
| :---- |

Competitors can get specific stock by providing a preferred symbol of stock symbol.

Parameter:

* symbol: (*string*) - symbol

Return:

- List of stocks with the same symbol in the parameter

Example

| print(self.handler.get\_stock\_by\_symbol('AOT')\[0\].get\_stock\_info())print(self.handler.get\_stock\_by\_symbol('AOT')\[1\].get\_stock\_info()) |
| :---- |

Output:

| {'Symbol': 'AOT', 'Actual Volume': 100, 'Buy Price': 30.2, 'Market Price': 30, 'Average Cost': 0.0, 'Amount Cost': 0.0, 'Market Value': 0.0, 'Unrealized P\&L': 0.0, 'Unrealized %': 0.0, 'Realized P\&L': 0.0, 'Buy time': '2025-06-23 11:54:48'}{'Symbol': 'AOT', 'Actual Volume': 100, 'Buy Price': 35.23, 'Market Price': 35, 'Average Cost': 0.0, 'Amount Cost': 0.0, 'Market Value': 0.0, 'Unrealized P\&L': 0.0, 'Unrealized %': 0.0, 'Realized P\&L': 0.0, 'Buy time': '2025-06-23 11:54:48'} |
| :---- |

&nbsp;

<a id="check_port_has_stocksymbol-volume"></a>

## **Check if portfolio has stock in the provided symbol**

| check\_port\_has\_stock(symbol, volume) |
| :---- |

Competitors can check if their portfolio has the stock of a preferred symbol and volume or not with this method.

Parameter:

* symbol: (*string*) – symbol
* volume: (*integer*) – volume

Return

- Boolean (True or False)

Example

| print(self.handler.check\_port\_has\_stock('AOT',100)) |
| :---- |

Output

| True |
| :---- |

<a id="additional-getter-method-for-strategy-runner"></a>

## **Additional getter method for strategy runner**

The self.handler object provides several getter methods to help participants monitor their portfolio throughout the simulation. These methods can be used to retrieve information such as holdings, cash balance, NAV, drawdowns, and performance metrics.

Below is a list of available getter methods:

| Portfolio Checks |  |
| ----- | :---- |
| check\_port\_has\_stock(symbol, volume) | Returns True if the portfolio holds at least a volume of the symbol |
| **Portfolio Info** |  |
| get\_owner() | Returns the team name |
| get\_all\_stocks\_info() | Returns a list of summarized stock info, grouped by symbol. |
| get\_portfolio\_info() | Returns a summary of the current portfolio |
| get\_stock\_by\_symbol(symbol) | Returns a specific stock object by symbol |
| get\_total\_stock\_volume\_by\_symbol(symbol) | Returns the total number of shares held for a specific symbol |
| get\_cash\_balance() | Returns the current cash available in the portfolio |
| **Performance Metrics** |  |
| get\_roi() | Returns the portfolio's current Return on Investment |
| get\_max\_draw\_down() | Returns the maximum drawdown encountered so far |
| get\_number\_of\_wins() | Returns the total number of profitable Round-Trips |
| get\_number\_of\_sells() | ⚠️ Despite the name, returns the **Round-Trip count** (fully-closed FIFO lots), **not** the number of sell orders placed. Prefer the two methods below. |
| get\_round\_trip\_count() | Same value as get\_number\_of\_sells(), under a clearer name — use this instead. |
| get\_buy\_order\_count() | Returns the number of Buy orders actually executed. |
| get\_sell\_order\_count() | Returns the number of Sell orders actually executed — this is what "number of sells" sounds like it should mean. |
| get\_win\_rate() | Win Rate (%) across completed Round-Trips (excludes exactly-zero P\&L Round-Trips). |
| get\_expected\_payoff() | Average P\&L per completed Round-Trip. |
| get\_average\_exposure() | Average fraction (0-1) of NAV invested in the market across all trading days so far. |
| get\_historical\_data(symbol, n, timeframe="1D") | OHLCV bars for `symbol` — daily by default, or intraday with `timeframe` — up to `n` (capped at 1000) bars **strictly before** the day currently being simulated — see below. |

&nbsp;

<a id="get_historical_datasymbol-n"></a>

## **`get_historical_data(symbol, n)`**

Returns daily OHLCV bars for `symbol`, going back up to `n` sequences, from **strictly before** the day currently being simulated — you can never see the current day's own data, or any day after it, no matter how many local tick files happen to be sitting on disk.

```python
bars = self.handler.get_historical_data("AOT", 5)   # up to 5 sequences of history
```

- `n` is a count of **sequences** (one OHLCV bar per trading day with data), not literally "days" — the engine walks backward collecting the most recent sequences that actually exist.
- Ask for more than is available → you get whatever exists, no error.
- Ask for more than **1000** → automatically capped at 1000 per call, no error.
- A day where `symbol` didn't trade at all is skipped entirely (not padded with zeros) — so you may get fewer sequences than `n` even with plenty of historical files present.
- Ask for `0` or a negative number → `[]`.

<a id="get_historical_data-in-init"></a>

### **Call it from `__init__`, not from `on_data`**

`self.handler` is fully usable inside your strategy's `__init__`, which runs
once. `on_data` runs on every tick — around 190,000 times in a real trading
day.

The history this returns stops at the previous trading day, so it cannot
change while the day runs. Recomputing an indicator on every tick therefore
produces the same answer several hundred thousand times over.

```python
class MyTeam(Strategy_template):
    WATCHLIST = ["AOT", "PTT"]

    def __init__(self, handler):
        super().__init__("MyTeam", "MyTeam", handler, timeframe="1D")
        # once, here
        self.signals = {s: self._decide(s) for s in self.WATCHLIST}

    def _decide(self, symbol):
        history = self.handler.get_historical_data(symbol, 120)
        ...

    def on_data(self, bar):
        signal = self.signals.get(bar["ShareCode"])   # just a lookup
        ...
```

A full worked example, including the TA-Lib specifics, is in
[`docs/examples/Test_TALib_strategy.py`](examples/Test_TALib_strategy.py).

**Where the data comes from:** two sources, combined automatically — you don't need to do anything differently to use either one.
- `marketInfo/ticks/<date>.csv` — the same daily tick files used to run the simulation itself, aggregated into one OHLCV bar per symbol per day.
- `marketInfo/daily_history/<symbol>.csv` — one file per symbol holding pre-aggregated daily OHLCV, which is what lets lookback reach further back than the tick files on their own could ever practically cover (years, not just the days included in this competition). If a date has an entry here, it's always used instead of re-aggregating that date from the tick file.

Because of this, you may sometimes get back more history than you expected if you ask for a large `n` — that's expected, not a bug.

Return format — a list of dicts, **oldest to newest**:

```python
[
    {"Date": "2025-11-17", "Open": 30.00, "High": 30.50, "Low": 29.75, "Close": 30.25, "Volume": 1234500},
    {"Date": "2025-11-18", "Open": 30.25, "High": 30.75, "Low": 30.00, "Close": 30.50, "Volume": 987000},
    ...
]
```

Use `get_historical_data` for longer/cross-day trend context, and `on_data`'s `bar` for actual intraday buy/sell decisions.

<a id="get_historical_data-timeframe"></a>

### **Intraday bars: the `timeframe` argument**

```python
bars = self.handler.get_historical_data("AOT", 100, timeframe="5min")
```

- Leave it out for `"1D"`, the daily bars described above. Otherwise it must be one of `"1min"`, `"3min"`, `"5min"`, `"10min"`, `"15min"`, `"30min"`, `"60min"`, `"120min"`, `"240min"` — any alias of the same length works too (`"1h"` = `"60min"`). Anything else (`"2min"`, `"1W"`, ...) raises `ValueError` listing the allowed values, and CI catches it on push.
- Intraday bars carry `"Timestamp"` (the bar's start, date and time) instead of `"Date"` — the same shape as `on_data`'s `bar`:
  `{"Timestamp": "2026-09-16 09:45:00", "Open": 60.75, "High": 61.25, "Low": 60.75, "Close": 61.0, "Volume": 743200}`
- Same anti-lookahead rule: only bars from trading days **before** the simulated one. Today's bars come live through `on_data`.
- `n` counts bars, capped at 1000.
- Intraday history is much shorter than daily. The data source keeps short intervals for only a few days, so the organizers started collecting it on 2026-09-29 and add every trading day since. At that point it reached back to about 2026-09-24 for `1min`, 2026-09-07 for `15min`, 2026-07-01 for `60min` and 2025-09-30 for `240min` — see [`get_historical_data.md`](get_historical_data.md) for every interval. Always check `len(bars)`.
- Neither source counts odd-lot trades. Since zip 0.2.3 the tick files leave them out, so the bars `on_data` builds during a day match the historical bars for that same day, and an order is never matched at an odd-lot price away from the main board. (Zip 0.2.2 and earlier still had odd lots in the ticks.)

**A small working example** — buy when price is above the 5-day SMA, sell when it drops back below. The SMA is computed once in `__init__`; `on_data` only looks it up (see `strategy/Example_historical_strategy.py` for the full file):

```python
from strategy.Strategies_template import Strategy_template


class Example_historical_strategy(Strategy_template):
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
```

<a id="get_historical_data-set50"></a>

### **Historical data for the SET50 index itself**

Passing `"SET50"` as the symbol returns the index's own daily bars, in the
same format as any stock:

```python
index = self.handler.get_historical_data("SET50", 20)
# {"Date": "2026-09-17", "Open": 1062.19, "High": 1071.36,
#  "Low": 1062.19, "Close": 1069.77, "Volume": 1638462300}
```

Useful for gauging the broad market before taking a position in a single
name, for relative-strength comparisons, or for beta/correlation against
your own watchlist.

Three things to know:

1. `on_data` is never called with `SET50`. The daily tick data holds
   individual stocks only, so the index has to be requested explicitly
   from inside `on_data` for some other symbol.
2. `SET50` cannot be traded -- only the individual stocks that make up
   the index can. An index is a calculated number, not something there is
   a share of to hold, so `create_order_to_limit` /
   `create_order_at_market` reject it:

   > `'SET50' is a market index, not a tradable stock -- orders can only be
   > placed on the individual SET50 constituent stocks (AOT, PTT, ...).
   > To read the index itself, use get_historical_data('SET50', n).`

   The same applies to `SET` and the other index names. Read the index to
   decide **which stock** to trade, then place the order on that stock.
3. The same anti-lookahead rule applies: the index value for the day being
   traded is never visible, only up to the previous trading day.

This is a different dataset from the one the organizers use to compute
Benchmark Return / Excess Return when scoring. A strategy has no access to
the competition's benchmark or to its own score: `get_portfolio_info()`
reports them as `None` for as long as the day is running, and fills them in
only after the day is saved — which is what you see in the notebook's results.


## **Additional getter method for stock**

The following methods are available to retrieve detailed information about a stock position held in the portfolio. These can be useful for analysis, logging, or debugging strategy during simulation.

| Basic Info |  |
| ----- | :---- |
| get\_symbol() | Returns the stock symbol (e.g., "AOT", "PTT") |
| **Trade Details** |  |
| get\_buy\_price() | Returns the price per share at which the stock was purchased |
| get\_start\_vol() | Returns initial number of shares bought |
| get\_actual\_vol() | Returns remaining shares currently held |
| get\_buy\_time\_str() | Returns timestamp of the purchase in readable format |
| **Valuation** |  |
| get\_mkt\_price() | Returns current market price of the stock |
| get\_amount\_cost() | Returns total cost spent on this stock (buy\_price × volume) |
| get\_market\_value() | Returns current market value of the held stock (market\_price × volume) |
| **Performance** |  |
| get\_unrealized() | Returns current unrealized profit/loss |
| get\_unrealized\_in\_percentage() | Returns unrealized profit/loss as a percentage |
| get\_realized() | Returns realized profit/loss (from partial sells) |

<a id="attaching-a-modelconfig-file"></a>

## **Attaching a model/config file**

Since strategy files run in a sandbox and can never call `open()` directly, if your strategy needs its own config or a pre-trained model, you attach it as an extra file next to your `.py` file and load it only through `self.handler`:

1. Put the file in the same `strategy/` folder as your team's `.py` file.
2. Load it through one of these — never `open()` yourself:

   | Method | For |
   | :---- | :---- |
   | `handler.load_json(filename)` | `.json` config/parameter files |
   | `handler.load_model(filename)` | a trained scikit-learn model saved as `.skops` |
   | `handler.get_companion_path(filename)` | `.json`/`.txt`/`.ubj`/`.cbm` files you hand to a library's own loader (xgboost `.json`/`.ubj`, lightgbm `.txt`, catboost `.cbm`) |

3. **Never attach `.pkl`/`.pickle`/`.joblib`/`.h5`/`.pt`/`.pth`** — these formats can execute arbitrary code just by being loaded, and validation rejects them outright.
   - scikit-learn models → save with `skops.io.dump(model, "strategy/model.skops")`
   - xgboost/lightgbm models → use their own native format (`Booster.save_model("model.json")` / `"model.txt"`)
4. Each attached file must be **20MB or smaller**.

<a id="allowed-libraries"></a>

## **Allowed libraries**

Pre-installed on the official runner already — import and use directly, no `requirements.txt` of your own, and no `pip install` of your own. For local practice, `numpy`, `pandas` and the technical-analysis libraries come with `requirements.txt`; everything else on this list is in `requirements-optional.txt` — install it only when you need it:

- **Numerical/statistics**: `numpy`, `pandas`, `scipy`, `statsmodels`
- **Machine learning**: `scikit-learn`, `xgboost`, `lightgbm`, `catboost`
- **Technical analysis**: `TA-Lib` (import as `talib`), `ta`, `finta`
- **Time series**: `pmdarima`, `arch`
- **Portfolio optimization**: `cvxpy`, `PuLP`, `pyportfolioopt` (import as `pypfopt`)
- **Plotting** (local debugging only — no display on CI): `matplotlib`
- **Symbolic math**: `sympy`
- **Safe model serialization**: `skops`

Need something not on this list? Contact the organizers directly, and ideally before the competition starts — see [Installing dependency](#installing-dependency).

<a id="penalties-for-unauthorized-modification-of-the-trading-system"></a>

# **Penalties for Unauthorized Modification of the Trading System**

To ensure fairness and integrity in this trading simulation, the following rules and penalties apply:

#### **Prohibited Actions** Any developer found to have **intentionally modified any part of the trading system** other than the designated strategy section for the purpose of gaining an unfair advantage or bypassing system rules **will be subject to penalties**, including:

* Modifying order execution logic
* Altering portfolio/account handling mechanisms
* Changing the data feed or timing
* Interfering with result tracking or logging processes
  Any code manipulation that affects global behavior or evaluation outcomes

Many of the mechanical parts of this (forbidden imports/calls, editing `Strategies_template.py`, single-class-per-file, team-name spoofing) are caught automatically by the CI checks described in [Automated Submission Checks (CI)](#automated-submission-checks-ci) — anything CI can't mechanically detect is still covered by this policy and reviewed manually.

#### **Intention and Scope** If our team detects intentional modification aimed at benefiting a specific team by cheating or bypassing the agent rules of the competition:

* **Your team's simulation results will be disqualified and not counted in the final evaluation.**
* **Your strategy will be removed from the pool of valid entries.**

#### **Permitted Area** You are allowed to:

* Modify or implement your strategy **within the designated strategy file that was inherited from strategy\_template.py**
* Use public APIs and allowed utility/helper functions that do not compromise the system's fairness

#### **Final Decision**

All decisions regarding disqualification and result invalidation are **final and at the discretion of the organizing team**.
