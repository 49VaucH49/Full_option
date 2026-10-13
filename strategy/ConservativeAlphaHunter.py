from strategy.Strategies_template import Strategy_template
from datetime import datetime
import numpy as np
import talib


class ConservativeAlphaHunter(Strategy_template):
    """
    Conservative Alpha Hunter v2
    - Cooldown 5 นาที/หุ้น → ลด overtrading
    - Stop-loss −3%, Take-profit +5%
    - Position size 10% NAV (ลดจาก 15%)
    - Universe 5 ตัว (ลดจาก 10)
    """

    # ⚠️ ลด universe เหลือ 5 หุ้นใหญ่สุด
    WATCHLIST = ["ADVANC", "AOT", "PTT", "KBANK", "SCB"]

    LOOKBACK = 60
    SMA_PERIOD = 20
    RSI_PERIOD = 14
    VOL_PERIOD = 20
    RSI_MIN = 40
    RSI_MAX = 70
    VOL_MULTIPLIER = 1.2

    STOP_LOSS = -0.03
    TAKE_PROFIT = 0.05
    MAX_POSITION_PCT = 0.10          # ⚠️ 15% → 10%

    LOT = 100
    COOLDOWN_SECONDS = 300           # ⚠️ ใหม่ — 5 นาที/หุ้น

    def __init__(self, handler):
        super().__init__(
            "Full_option",              # ← ⚠️ แก้เป็นชื่อทีมคุณ
            "ConservativeAlphaHunter",     # ← ต้องตรงกับชื่อไฟล์
            handler,
            timeframe="1D",
        )

        # Precompute indicators
        self.sma = {}
        self.rsi = {}
        self.avg_vol = {}

        for symbol in self.WATCHLIST:
            history = self.handler.get_historical_data(symbol, self.LOOKBACK)
            if len(history) < max(self.SMA_PERIOD, self.RSI_PERIOD, self.VOL_PERIOD):
                continue

            closes = np.array([d["Close"] for d in history], dtype=np.float64)
            volumes = np.array([d["Volume"] for d in history], dtype=np.float64)

            sma_arr = talib.SMA(closes, timeperiod=self.SMA_PERIOD)
            rsi_arr = talib.RSI(closes, timeperiod=self.RSI_PERIOD)

            if np.isnan(sma_arr[-1]) or np.isnan(rsi_arr[-1]):
                continue

            self.sma[symbol] = float(sma_arr[-1])
            self.rsi[symbol] = float(rsi_arr[-1])
            self.avg_vol[symbol] = float(np.mean(volumes[-self.VOL_PERIOD:]))

        # Cooldown tracker
        self.last_trade_time = {}

    # ------------------------------------------------------------------
    def _is_on_cooldown(self, symbol, timestamp):
        """เช็คว่าหุ้นนี้อยู่ในช่วง cooldown ไหม"""
        last = self.last_trade_time.get(symbol)
        if last is None:
            return False

        try:
            t_now = datetime.fromisoformat(str(timestamp))
            t_last = datetime.fromisoformat(str(last))
            elapsed = (t_now - t_last).total_seconds()
            return elapsed < self.COOLDOWN_SECONDS
        except Exception:
            return False

    def _mark_traded(self, symbol, timestamp):
        self.last_trade_time[symbol] = timestamp

    # ------------------------------------------------------------------
    def _get_nav(self):
        """NAV = cash + มูลค่าหุ้นที่ถือ"""
        cash = self.handler.get_cash_balance()
        stocks = self.handler.get_all_stocks_info()
        stock_value = sum(s.get("Market Value", 0) for s in stocks)
        return cash + stock_value

    def _volume_to_buy(self, price):
        """คำนวณ position size ตาม NAV"""
        cash = self.handler.get_cash_balance()
        nav = self._get_nav()
        target = nav * self.MAX_POSITION_PCT
        budget = min(target, cash * 0.95)
        lots = int(budget // (price * self.LOT))
        return lots * self.LOT

    # ------------------------------------------------------------------
    def _entry_signal(self, symbol, bar):
        """ตรวจ 3 เงื่อนไขก่อนซื้อ"""
        price = bar["Close"]
        sma = self.sma.get(symbol)
        rsi = self.rsi.get(symbol)
        avg_vol = self.avg_vol.get(symbol)

        if sma is None or rsi is None or avg_vol is None:
            return False

        # 1. Trend
        if price <= sma:
            return False

        # 2. Momentum
        if not (self.RSI_MIN <= rsi <= self.RSI_MAX):
            return False

        # 3. Volume
        if bar["Volume"] < avg_vol * self.VOL_MULTIPLIER:
            return False

        return True

    def _exit_signal(self, symbol, bar):
        """คืน 'STOP_LOSS' / 'TAKE_PROFIT' / 'TREND_BREAK' / None"""
        stocks = self.handler.get_stock_by_symbol(symbol)
        if not stocks:
            return None

        price = bar["Close"]
        buy_price = stocks[0].get_buy_price()
        if buy_price <= 0:
            return None

        pnl_pct = (price - buy_price) / buy_price

        if pnl_pct <= self.STOP_LOSS:
            return "STOP_LOSS"
        if pnl_pct >= self.TAKE_PROFIT:
            return "TAKE_PROFIT"
        if price < self.sma.get(symbol, float("inf")):
            return "TREND_BREAK"
        return None

    # ------------------------------------------------------------------
    def on_data(self, bar):
        symbol = bar["ShareCode"]

        # Skip ถ้าไม่มี indicator
        if symbol not in self.sma:
            return

        # ⚠️ Cooldown check — หัวใจของการแก้รอบนี้
        if self._is_on_cooldown(symbol, bar["Timestamp"]):
            return

        held = self.handler.get_total_stock_volume_by_symbol(symbol)

        # ไม่มีหุ้น → หาจังหวะซื้อ
        if held == 0:
            if self._entry_signal(symbol, bar):
                volume = self._volume_to_buy(bar["Close"])
                if volume >= self.LOT:
                    self.handler.create_order_at_market(volume, "Buy", symbol)
                    self._mark_traded(symbol, bar["Timestamp"])
            return

        # มีหุ้น → หาจังหวะขาย
        exit_reason = self._exit_signal(symbol, bar)
        if exit_reason and held >= self.LOT:
            self.handler.create_order_at_market(held, "Sell", symbol)
            self._mark_traded(symbol, bar["Timestamp"])