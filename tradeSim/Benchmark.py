import os
import glob
import math
from datetime import time
import pandas as pd


_SESSION_OPEN_LATEST = time(10, 30)     # first tick should arrive by here to count as covering market open
_SESSION_CLOSE_EARLIEST = time(16, 0)   # last tick should arrive no earlier than this to count as covering close
                                         # (reference: real SET50 files span 10:00:00-16:30:00)

_MAX_STALE_DAYS = 1   # latest available close must be within this many calendar days of as_of_date to be trusted


def _warn_if_incomplete_session(label, file_path, df, time_col="TradeDateTime"):
    """A day's "close" is only as good as whether its file actually
    covers the trading session -- taking the last row as the close is
    correct only if that last row is genuinely near market close. Never
    raises, just flags the file so a synthetic/partial fixture (or a bad
    data drop) doesn't silently masquerade as a real closing price."""
    first_t = df.iloc[0][time_col].time()
    last_t = df.iloc[-1][time_col].time()
    if first_t > _SESSION_OPEN_LATEST or last_t < _SESSION_CLOSE_EARLIEST:
        print(f"[{label}] WARNING: {file_path} does not look like it spans a full trading "
              f"session (first tick {first_t}, last tick {last_t}) -- the value computed from "
              f"its last row may not reflect the actual market close.")


class benchmark:

    def __init__(self, folder_path="marketInfo/benchmark"):
        self.folder_path = folder_path

    def _find_daily_close_file(self):
        """The official daily closing series, if one has been provided:
        any CSV in the benchmark folder whose name is NOT a date (per-day
        intraday files are named <YYYY-MM-DD>.csv), holding one row per
        trading day with at least `Date` and `Close` columns -- e.g.
        SET50.csv exported straight from the exchange/vendor.

        This is what the competition rules actually call for: Benchmark
        Return and Benchmark Max DD are defined on "the official daily
        closing value published by the SET at end of trading day", and
        explicitly exclude intraday movement. Deriving a close from the
        last row of an intraday file (see _load_daily_closes' fallback)
        is only ever an approximation of that -- it silently depends on
        the file really reaching the close, on the last print being the
        closing auction rather than an off-auction trade, and on the
        file being labelled with the right date in the first place.

        Returns None when no such file exists, so folders that only have
        per-day files keep working exactly as before."""
        candidates = []
        for path in sorted(glob.glob(os.path.join(self.folder_path, "*.csv"))):
            name = os.path.splitext(os.path.basename(path))[0]
            try:
                pd.to_datetime(name)
            except (ValueError, TypeError):
                candidates.append(path)   # not date-named -> a daily series
        if not candidates:
            return None
        if len(candidates) > 1:
            names = ", ".join(os.path.basename(c) for c in candidates)
            raise ValueError(
                f"Benchmark folder '{self.folder_path}' has more than one daily-close file "
                f"({names}) -- keep exactly one so there is no ambiguity about which index "
                f"the competition is being scored against."
            )
        return candidates[0]

    def _load_from_daily_file(self, path, as_of, start):
        """Read (date, close) pairs from the official daily close file,
        applying the same as_of / start_date scoping as the per-day
        path. A row whose Date or Close won't parse is skipped rather
        than taken as a zero, which would read as a -100% crash."""
        df = pd.read_csv(path)
        missing = [c for c in ("Date", "Close") if c not in df.columns]
        if missing:
            raise ValueError(
                f"Benchmark daily-close file '{path}' is missing required column(s): "
                f"{', '.join(missing)}. Expected at least Date and Close, one row per trading day."
            )

        closes = []
        for _, row in df.iterrows():
            try:
                d = pd.to_datetime(row["Date"]).date()
                close = float(row["Close"])
            except (ValueError, TypeError):
                continue
            # float(nan) does NOT raise -- an empty Close cell arrives from
            # pandas as NaN and would sail through the except above, then
            # poison everything downstream silently: a NaN as the last row
            # makes Benchmark Return itself NaN (and so every team's Excess
            # Return), while a NaN in the middle is skipped by every
            # comparison in the drawdown loop, hiding a real drawdown.
            if not math.isfinite(close):
                continue
            if d > as_of:
                continue                      # never look into this run's future
            if start is not None and d < start:
                continue                      # before this league's own start date
            closes.append((str(d), close))
        return closes

    def has_close_for(self, date):
        """Whether this folder can supply the official close for `date`,
        in EITHER supported layout -- a daily-close series containing a row
        for that date, or a per-day <date>.csv.

        Exists so callers that gate a run on the day's data being present
        (main.py, run_daily.py) can ask the benchmark itself instead of
        hard-coding "<folder>/<date>.csv". That hard-coded path is only
        correct for the per-day layout, so a folder using the daily-close
        file the rules actually call for would otherwise be reported as
        missing on every single date and block every run."""
        d = pd.to_datetime(date).date()
        daily_file = self._find_daily_close_file()
        if daily_file is not None:
            return any(day == str(d) for day, _ in self._load_from_daily_file(daily_file, d, None))
        return os.path.exists(os.path.join(self.folder_path, f"{d}.csv"))

    def _load_daily_closes(self, as_of_date, start_date=None):
        """`start_date`, when given, scopes the closes to that university
        group's own competition start (see university_schedule.json) --
        marketInfo/benchmark/ is one shared folder across every university
        group, so without this a group that starts later than another
        would have its benchmark return/drawdown computed from the
        earliest file in the whole folder, including days it wasn't even
        competing yet.

        If the latest available close is more than _MAX_STALE_DAYS from
        as_of_date, returns [] instead -- this normally can't happen for
        a real competition day (run_daily.py hard-blocks before main.py
        even runs if today's own benchmark file is missing), but a
        direct main.py invocation has no such gate. Without this check,
        a caller with no benchmark file anywhere near as_of_date would
        silently get a return/drawdown computed between two unrelated,
        stale dates instead of a plausible-looking but meaningless
        number."""
        as_of = pd.to_datetime(as_of_date).date()
        start = pd.to_datetime(start_date).date() if start_date is not None else None

        # Official daily closes win outright when they're available -- see
        # _find_daily_close_file(). The per-day intraday scan below stays as a
        # fallback for folders that only have those (and for the fixtures the
        # test suite is built on).
        daily_file = self._find_daily_close_file()
        if daily_file is not None:
            closes = self._load_from_daily_file(daily_file, as_of, start)
            closes.sort(key=lambda x: x[0])
            return self._drop_if_stale(closes, as_of)

        pattern = os.path.join(self.folder_path, "*.csv")
        files = sorted(glob.glob(pattern))

        closes = []
        symbols_seen = {}   # ShareCode -> first file it appeared in
        for file_path in files:
            filename = os.path.basename(file_path)
            date_part = os.path.splitext(filename)[0]  # "2025-09-17"
            try:
                file_date = pd.to_datetime(date_part).date()
            except (ValueError, TypeError):
                continue  # not a date-named file, skip

            if file_date > as_of:
                continue  # don't look into the "future" for this run

            if start is not None and file_date < start:
                continue  # before this university group's own start date

            df = pd.read_csv(file_path)
            df["TradeDateTime"] = pd.to_datetime(df["TradeDateTime"])
            df_sorted = df.sort_values("TradeDateTime")
            _warn_if_incomplete_session("Benchmark", file_path, df_sorted)
            close = float(df_sorted.iloc[-1]["LastPrice"])

            # Which index this file actually holds. Nothing here ever filtered
            # on it before -- the last row's LastPrice was taken as "the
            # market's close" whatever instrument it came from.
            if "ShareCode" in df_sorted.columns and not df_sorted.empty:
                symbols_seen.setdefault(str(df_sorted.iloc[-1]["ShareCode"]).strip(), file_path)

            closes.append((str(file_date), close))

        # A return/drawdown series is only meaningful if every close in it came
        # from the SAME index. Two different indices in one window (e.g. a
        # leftover SET50 file at ~1000 ahead of a season of SET files at ~1570)
        # produces a confident, entirely fictional number -- measured here at
        # +58.85% where the real SET move was +2.75% -- which then flows
        # straight into every team's Excess Return and the whole ranking.
        # Loud failure beats a plausible-looking wrong number.
        if len(symbols_seen) > 1:
            detail = ", ".join(f"{sym} (e.g. {os.path.basename(path)})"
                                for sym, path in sorted(symbols_seen.items()))
            raise ValueError(
                f"Benchmark folder '{self.folder_path}' mixes more than one index over the "
                f"window being computed: {detail}. Every file in one window must hold the "
                f"same index -- remove or move aside the odd ones out, or scope the window "
                f"with a start_date that excludes them."
            )

        closes.sort(key=lambda x: x[0])
        return self._drop_if_stale(closes, as_of)

    def _drop_if_stale(self, closes, as_of):
        """Shared by both sources: if the newest close available is more
        than _MAX_STALE_DAYS from the day being scored, treat it as no
        benchmark data at all rather than computing a return between two
        unrelated dates."""
        if closes:
            latest_date = pd.to_datetime(closes[-1][0]).date()
            gap = (as_of - latest_date).days
            if gap > _MAX_STALE_DAYS:
                print(f"[Benchmark] WARNING: latest available close is {closes[-1][0]} but as_of_date "
                      f"is {as_of} ({gap} days apart) -- too stale to use as a market reference, "
                      f"treating this as no benchmark data available.")
                return []
        return closes

    def get_benchmark_return(self, as_of_date, start_date=None):
        closes = self._load_daily_closes(as_of_date, start_date=start_date)
        if len(closes) < 2:
            return 0.0
        index_start = closes[0][1]
        index_end = closes[-1][1]
        if index_start == 0:
            return 0.0
        return ((index_end - index_start) / index_start) * 100

    def get_benchmark_max_dd(self, as_of_date, start_date=None):
        closes = self._load_daily_closes(as_of_date, start_date=start_date)
        if not closes:
            return 0.0

        max_index = None
        min_index = None
        max_dd = 0.0

        for _, close in closes:
            if max_index is None or close > max_index:
                max_index = close
                min_index = close
            elif close < min_index:
                min_index = close

            if max_index and min_index and max_index != 0:
                current_dd = ((max_index - min_index) / max_index) * 100
                max_dd = max(max_dd, current_dd)

        return max_dd