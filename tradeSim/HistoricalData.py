import os
import glob
from bisect import bisect_left
from datetime import time
import pandas as pd
from pandas.tseries.frequencies import to_offset


MAX_LOOKBACK_DAYS = 1000   # also caps intraday requests -- n counts bars either way

DAILY = "1D"

# The intraday intervals Settrade's candlestick API serves, keyed by length in
# minutes. These are the only intraday timeframes get_historical_data() can
# back with real history -- scripts/fetch_intraday_history.py saves each one
# to marketInfo/intraday_history/<interval>/<symbol>.csv.
INTRADAY_INTERVALS = {1: "1m", 3: "3m", 5: "5m", 10: "10m", 15: "15m",
                      30: "30m", 60: "60m", 120: "120m", 240: "240m"}

SUPPORTED_TIMEFRAMES_TEXT = ", ".join(f"{m}min" for m in INTRADAY_INTERVALS) + ", 1D"


def resolve_timeframe(timeframe):
    """DAILY, or the interval folder name ("5m", ...) that `timeframe` names.

    Any pandas alias of the same length is accepted ("60min", "1h", "1H"), so
    a strategy can pass the same string it gave super().__init__(). Raises
    ValueError for anything else -- a timeframe there is no data for must
    fail loudly, not come back as a silent [] that looks like "no history"."""
    try:
        # to_offset rather than pd.Timedelta: it reads a bare "D" or "h" the
        # way BarAggregator's floor(timeframe) does. Calendar offsets ("1M")
        # have no fixed length and raise on .nanos.
        span = pd.Timedelta(to_offset(timeframe).nanos, unit="ns")
    except (ValueError, TypeError, AttributeError):
        span = None
    if span == pd.Timedelta(days=1):
        return DAILY
    if span is not None and span % pd.Timedelta(minutes=1) == pd.Timedelta(0):
        interval = INTRADAY_INTERVALS.get(int(span / pd.Timedelta(minutes=1)))
        if interval is not None:
            return interval
    raise ValueError(
        f"get_historical_data() has no data for timeframe {timeframe!r} -- "
        f"use one of: {SUPPORTED_TIMEFRAMES_TEXT}"
    )

_SESSION_OPEN_LATEST = time(10, 30)     # first tick should arrive by here to count as covering market open
_SESSION_CLOSE_EARLIEST = time(16, 0)   # last tick should arrive no earlier than this to count as covering close
                                         # (reference: real SET50 files span 10:00:00-16:30:00)


def _warn_if_incomplete_session(label, file_path, df, time_col="TradeDateTime"):
    """A day's OHLCV bar is only as good as whether its file actually
    covers the trading session -- Open/High/Low/Close computed from
    whatever rows are there are only correct if those rows genuinely
    span the session. Never raises, just flags the file so a
    synthetic/partial fixture (or a bad data drop) doesn't silently
    masquerade as a real day's bar."""
    first_t = df.iloc[0][time_col].time()
    last_t = df.iloc[-1][time_col].time()
    if first_t > _SESSION_OPEN_LATEST or last_t < _SESSION_CLOSE_EARLIEST:
        print(f"[{label}] WARNING: {file_path} does not look like it spans a full trading "
              f"session (first tick {first_t}, last tick {last_t}) -- the value computed from "
              f"its last row may not reflect the actual market close.")


class historical_data:
    """Reads marketInfo/ticks/<date>.csv and aggregates each day's raw
    ticks (there can be many thousands of them across all SET50 symbols
    in a single day's file) into one OHLCV bar per symbol per day.

    A second source, marketInfo/daily_history/<symbol>.csv, backs
    lookback beyond what marketInfo/ticks/ can ever cover (raw tick data
    going back years isn't practical to obtain/store). Whenever a date
    has an entry there, it wins over re-reading tick data.

    READ-ONLY. This class never writes to daily_history. It used to
    persist newly tick-computed bars back into it as a permanent cache,
    which made the engine mutate its own input: the folder ended up
    holding a mix of supplied data and data the engine derived, appended
    out of date order, with no way to tell which was which. Any run at
    all -- including a throwaway test run -- silently edited the dataset
    every later run and every team would then be scored against. A
    dataset that is judged on must not be rewritten by the thing doing
    the judging, so the only writer of daily_history is now whatever
    populates it in the first place.

    Caches per `historical_data` instance -- one instance lives for the
    whole lifetime of one tradeSim run (see TradeSim.py), shared by every
    symbol's StrategyHandler in that run -- so within one run, a given
    day's file is only ever read and sorted once even if a strategy
    calls get_historical_data() on every single tick."""

    def __init__(self, folder_path="marketInfo/ticks", history_folder="marketInfo/daily_history",
                 intraday_folder="marketInfo/intraday_history"):
        self.folder_path = folder_path
        self.history_folder = history_folder
        self.intraday_folder = intraday_folder
        self._dated_files_cache = None       # sorted [(date, path), ...], scanned once
        self._bar_cache = {}                 # (file_path, symbol) -> bar dict or None
        self._daily_history_cache = {}       # symbol -> {date: bar dict}, loaded lazily once per symbol
        self._sorted_dates_cache = {}        # (symbol, as_of) -> sorted list of usable dates
        self._intraday_cache = {}            # (symbol, interval) -> (bar dates, bars), both ascending

    def _list_dated_files(self):
        if self._dated_files_cache is None:
            pattern = os.path.join(self.folder_path, "*.csv")
            dated = []
            for file_path in glob.glob(pattern):
                filename = os.path.basename(file_path)
                date_part = os.path.splitext(filename)[0]
                try:
                    file_date = pd.to_datetime(date_part).date()
                except (ValueError, TypeError):
                    continue  # not a date-named file, skip
                dated.append((file_date, file_path))
            dated.sort(key=lambda x: x[0])
            self._dated_files_cache = dated
        return self._dated_files_cache

    def _compute_bar(self, file_path, file_date, symbol):
        """One day's OHLCV for `symbol`, or None if the symbol has no
        rows that day. A day's file can hold many thousands of ticks
        across every symbol -- sort with kind="stable" so ties on the
        same TradeDateTime keep the file's own original (chronological)
        order instead of risking pandas' default unstable sort silently
        reordering which tick counts as "first"/"last" for Open/Close."""
        try:
            df = pd.read_csv(file_path)
            df = df[df["ShareCode"] == symbol].copy()
            if df.empty:
                return None

            df["TradeDateTime"] = pd.to_datetime(df["TradeDateTime"])
            df = df.sort_values("TradeDateTime", kind="stable")
            _warn_if_incomplete_session("HistoricalData", file_path, df)

            return {
                "Date": str(file_date),
                "Open": float(df.iloc[0]["LastPrice"]),
                "High": float(df["LastPrice"].max()),
                "Low": float(df["LastPrice"].min()),
                "Close": float(df.iloc[-1]["LastPrice"]),
                "Volume": int(df["Volume"].sum()),
            }
        except Exception:
            return None  # a malformed day's file shouldn't break the whole call

    def _load_daily_history(self, symbol):
        """Load marketInfo/daily_history/<symbol>.csv -- pre-aggregated
        daily OHLCV, either supplied externally (vendor export going
        back years, beyond what marketInfo/ticks/ can ever cover) or
        written by this engine itself the first time a given day's bar
        was computed from tick data (see _cache_new_bars). Both live in
        the same file since a past trading day's bar never changes once
        computed, so there's nothing to keep separately in sync. Never
        raises: a missing file, an unreadable file, or a malformed row
        are all just skipped."""
        if symbol not in self._daily_history_cache:
            path = os.path.join(self.history_folder, f"{symbol}.csv")
            bars_by_date = {}
            if os.path.isfile(path):
                try:
                    df = pd.read_csv(path)
                    # Parsed column-at-a-time rather than row-at-a-time. The
                    # per-row version called pd.to_datetime() on one scalar
                    # per row, which cost ~333ms for a 726-row file -- paid
                    # once per symbol per run, for every team, every day.
                    # errors="coerce" turns anything unparseable into
                    # NaT/NaN, so the mask below drops exactly the rows the
                    # old per-row try/except skipped, and keeps the rest.
                    dates = pd.to_datetime(df["Date"], errors="coerce")
                    cols = {
                        name: pd.to_numeric(df[name], errors="coerce")
                        for name in ("Open", "High", "Low", "Close", "Volume")
                    }
                    keep = dates.notna()
                    for series in cols.values():
                        keep &= series.notna()

                    for d, o, h, l, c, v in zip(
                        dates[keep].dt.date,
                        cols["Open"][keep], cols["High"][keep], cols["Low"][keep],
                        cols["Close"][keep], cols["Volume"][keep],
                    ):
                        bars_by_date[d] = {
                            "Date": str(d),
                            "Open": float(o),
                            "High": float(h),
                            "Low": float(l),
                            "Close": float(c),
                            "Volume": int(v),
                        }
                except Exception:
                    pass  # unreadable file -- no external history for this symbol
            self._daily_history_cache[symbol] = bars_by_date
        return self._daily_history_cache[symbol]

    def get_ohlcv(self, symbol, as_of_date, n):
        """Up to `n` OHLCV sequences for `symbol`, ascending by date, from
        trading days STRICTLY BEFORE `as_of_date`. Anti-lookahead: a date
        `as_of_date` or later is never read, even if its tick file or a
        daily_history entry already physically exists on disk. `n` is
        silently capped at MAX_LOOKBACK_DAYS (1000) rather than erroring.
        Never raises -- a missing folder, an unparseable filename, or a
        malformed file are all just skipped."""
        if n is None or n <= 0:
            return []
        n = min(n, MAX_LOOKBACK_DAYS)

        as_of = pd.to_datetime(as_of_date).date()
        daily_history = self._load_daily_history(symbol)
        tick_dates = {d: p for d, p in self._list_dated_files() if d < as_of}

        # The sorted union is identical on every call for a given symbol and
        # as_of -- both sources are fixed for the whole run -- but sorting
        # ~775 dates each time cost more than everything else in here put
        # together once a strategy asked for more than a handful of symbols.
        dates_key = (symbol, as_of)
        if dates_key not in self._sorted_dates_cache:
            self._sorted_dates_cache[dates_key] = sorted(
                d for d in (set(daily_history) | set(tick_dates)) if d < as_of
            )
        candidate_dates = self._sorted_dates_cache[dates_key][-n:]

        bars = []
        for d in candidate_dates:
            if d in daily_history:
                bars.append(daily_history[d])
            elif d in tick_dates:
                file_path = tick_dates[d]
                cache_key = (file_path, symbol)
                if cache_key not in self._bar_cache:
                    self._bar_cache[cache_key] = self._compute_bar(file_path, d, symbol)
                bar = self._bar_cache[cache_key]
                if bar is not None:
                    bars.append(bar)

        return bars

    def _load_intraday(self, symbol, interval):
        """marketInfo/intraday_history/<interval>/<symbol>.csv as two
        ascending lists: each bar's date (for the lookahead cut) and the
        bar itself. Loaded once per (symbol, interval) per run. Never
        raises -- a missing or unreadable file is just no history, and a
        malformed row is skipped."""
        key = (symbol, interval)
        if key not in self._intraday_cache:
            dates, bars = [], []
            path = os.path.join(self.intraday_folder, interval, f"{symbol}.csv")
            if os.path.isfile(path):
                try:
                    df = pd.read_csv(path)
                    stamps = pd.to_datetime(df["Timestamp"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
                    cols = {
                        name: pd.to_numeric(df[name], errors="coerce")
                        for name in ("Open", "High", "Low", "Close", "Volume")
                    }
                    keep = stamps.notna()
                    for series in cols.values():
                        keep &= series.notna()
                    frame = pd.DataFrame({"Timestamp": stamps, **cols})[keep]
                    frame = frame.drop_duplicates("Timestamp", keep="last").sort_values("Timestamp")

                    for ts, o, h, l, c, v in frame.itertuples(index=False):
                        dates.append(ts.date())
                        bars.append({
                            # same shape as the live bar on_data receives
                            "Timestamp": str(ts),
                            "Open": float(o),
                            "High": float(h),
                            "Low": float(l),
                            "Close": float(c),
                            "Volume": int(v),
                        })
                except Exception:
                    dates, bars = [], []
            self._intraday_cache[key] = (dates, bars)
        return self._intraday_cache[key]

    def get_intraday_ohlcv(self, symbol, as_of_date, n, interval):
        """Up to `n` intraday bars of `interval` for `symbol`, ascending,
        from trading days STRICTLY BEFORE `as_of_date` -- the same
        anti-lookahead cut as get_ohlcv(): nothing from the simulated day
        itself, whose bars the strategy gets live through on_data. `n` is
        capped at MAX_LOOKBACK_DAYS. Never raises."""
        if n is None or n <= 0:
            return []
        n = min(n, MAX_LOOKBACK_DAYS)

        as_of = pd.to_datetime(as_of_date).date()
        dates, bars = self._load_intraday(symbol, interval)
        end = bisect_left(dates, as_of)
        return bars[max(0, end - n):end]
