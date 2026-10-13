import pandas as pd


class bar_aggregator:
    """Buffers ticks for ONE symbol into a live-updating OHLCV bar for a
    fixed timeframe (any pandas offset alias, e.g. "1min", "5min", "1D").
    update() returns the CURRENT (possibly still-forming) bar on every
    single tick -- it never waits for the bar to "close". Whether to act
    only once a new bar starts (by comparing bar["Timestamp"] across
    calls) is left entirely to the strategy's own on_data logic."""

    def __init__(self, timeframe):
        self.timeframe = timeframe
        self._bucket_start = None
        self._bucket_end = None
        self._open = self._high = self._low = self._close = None
        self._volume = 0
        # A fixed-length timeframe ("1min", "5min", "1D") has a constant
        # span, so the bar a tick belongs to can be answered by two
        # comparisons instead of flooring its timestamp again. Calendar
        # offsets ("1M", "1W") have no constant length -- _span stays None
        # and those keep flooring every tick, exactly as before.
        try:
            self._span = pd.Timedelta(timeframe)
        except (ValueError, TypeError):
            self._span = None

    def _bucket_for(self, ts):
        """Which bar `ts` belongs to.

        Flooring a timestamp is the most expensive single thing in the
        per-tick path -- roughly 190,000 calls in one trading day -- and
        nearly every tick lands in the bar its predecessor already opened.
        Answering those from the current bar's bounds skips the work.

        Bounded on BOTH sides on purpose: a tick arriving out of order
        would otherwise be waved into the current bar just because it is
        below the upper bound.
        """
        if self._bucket_end is not None:
            try:
                if self._bucket_start <= ts < self._bucket_end:
                    return self._bucket_start
            except TypeError:
                pass   # not a Timestamp (a raw string, say) -- take the slow path
        return pd.Timestamp(ts).floor(self.timeframe)

    def update(self, row):
        bucket = self._bucket_for(row["TradeDateTime"])

        if self._bucket_start != bucket:
            self._bucket_start = bucket
            self._bucket_end = (bucket + self._span) if self._span is not None else None
            self._open = self._high = self._low = self._close = row["LastPrice"]
            self._volume = row["Volume"]
        else:
            self._high = max(self._high, row["LastPrice"])
            self._low = min(self._low, row["LastPrice"])
            self._close = row["LastPrice"]
            self._volume += row["Volume"]

        return {
            "ShareCode": row["ShareCode"],
            "Timestamp": str(self._bucket_start),
            "Open": self._open,
            "High": self._high,
            "Low": self._low,
            "Close": self._close,
            "Volume": self._volume,
        }
