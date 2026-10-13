# โค้ด Workshop TradeSim

โค้ดครบทุกหัวข้อของ workshop — **copy ทั้งก้อนไปวางได้เลย** ไม่ต้องพิมพ์เอง
(เลขหัวข้อตรงกับสไลด์)

## วิธีใช้

1. สร้างไฟล์ `strategy/MyStrategy.py` **ไฟล์เดียว**
2. แต่ละหัวข้อ: **ลบของเดิมในไฟล์ทิ้งทั้งหมด** แล้ววางโค้ดของหัวข้อนั้นทับลงไป
   (โค้ดทุกก้อนในนี้มีบรรทัด `import` ครบแล้ว วางทั้งก้อนได้เลย)
3. แก้ `"MyTeam"` ในบรรทัด `super().__init__("MyTeam", ...)` เป็น**ชื่อทีมที่ลงทะเบียนไว้**
4. ใน `TradingSimulation.ipynb` เซลล์ 3 ตั้ง `strategy_name = "MyStrategy"`
5. รัน **เซลล์ 3 → 4 → 6 → 7 → 8** ทุกครั้งที่แก้โค้ด
   - เซลล์ 3 มี `fresh_start = True` — ล้างพอร์ตแล้วเริ่ม 10 ล้านใหม่ให้ทุกครั้ง
   - **ต้องเริ่มที่เซลล์ 3 เสมอ** กดเซลล์ 6 ซ้ำอย่างเดียว = รันวันเดิมซ้ำบนพอร์ตเดิม ผลเพี้ยน
   - แก้ไฟล์แล้วไม่รันเซลล์ 4 = ได้โค้ดเวอร์ชันเก่า
   - ทุกหัวข้อใช้วันที่ `2026-09-09` (ค่า default ในเซลล์ 2) ยกเว้นหัวข้อ 5

> **ตอนส่งงาน** ใน `strategy/` ต้องมีไฟล์กลยุทธ์ของทีม**ไฟล์เดียว** — มีหลายไฟล์ CI แดง
> อยากเก็บโค้ดแต่ละหัวข้อไว้ดู ให้ copy ไปไว้นอก `strategy/` เช่นโฟลเดอร์ `steps/`

| หัวข้อ | ทำอะไร |
|---|---|
| [3](#3-กลยุทธ์ที่ไม่ทำอะไรเลย) | กลยุทธ์ที่ไม่ทำอะไรเลย — เช็คว่าโครงถูก |
| [4](#4-สั่งซื้อให้ได้-1-ครั้ง) | สั่งซื้อ 1 ครั้ง |
| [5](#5-ซื้อวันนี้-ขายวันหลัง--ปิด-round-trip-แรก) | ซื้อวันนี้ ขายวันหลัง — ปิด round-trip แรก (รันหลายวัน) |
| [6](#6-เปิดกล่องข้อมูลย้อนหลัง) | เปิดกล่องข้อมูลย้อนหลัง |
| [7](#7-sma-ด้วยมือ) | SMA ด้วยมือ |
| [8](#8-rsi-ด้วย-ta-lib) | RSI ด้วย TA-Lib |
| [9](#9-ตัวเต็ม-macd--rsi-หุ้น-8-ตัว) | ตัวเต็ม: MACD + RSI หุ้น 8 ตัว |

---

## 3. กลยุทธ์ที่ไม่ทำอะไรเลย

```python
from strategy.Strategies_template import Strategy_template


class MyStrategy(Strategy_template):
    def __init__(self, handler):
        super().__init__("MyTeam", "MyStrategy", handler, timeframe="1D")

    def on_data(self, bar):
        pass
```

**ต้องได้:** Buy Orders 0 · NAV 10,000,000 เป๊ะ

---

## 4. สั่งซื้อให้ได้ 1 ครั้ง

```python
from strategy.Strategies_template import Strategy_template


class MyStrategy(Strategy_template):
    def __init__(self, handler):
        super().__init__("MyTeam", "MyStrategy", handler, timeframe="1D")
        self.bought = False

    def on_data(self, bar):
        if bar["ShareCode"] != "AOT" or self.bought:
            return

        result = self.handler.create_order_at_market(100, "Buy", "AOT")
        if "successfully" in str(result):
            self.bought = True
```

**ต้องได้:** Buy Orders 1 · AOT 100 หุ้นในตาราง holdings (เซลล์ 8)

---

## 5. ซื้อวันนี้ ขายวันหลัง — ปิด Round-Trip แรก

```python
from strategy.Strategies_template import Strategy_template


class MyStrategy(Strategy_template):
    SYMBOL = "KBANK"
    TAKE_PROFIT = 1.02                     # ขายเมื่อราคาสูงกว่าต้นทุน 2%

    def __init__(self, handler):
        super().__init__("MyTeam", "MyStrategy", handler, timeframe="1D")
        self.ordered_today = False         # วันละ 1 คำสั่ง กันสั่งรัว

    def on_data(self, bar):
        if bar["ShareCode"] != self.SYMBOL or self.ordered_today:
            return
        price = bar["Close"]

        if not self.handler.check_port_has_stock(self.SYMBOL, 100):
            # ยังไม่มีหุ้น → ซื้อ
            result = self.handler.create_order_at_market(100, "Buy", self.SYMBOL)
        elif price >= self.cost() * self.TAKE_PROFIT:
            # มีหุ้นอยู่ (อาจซื้อไว้ตั้งแต่วันก่อน) และถึงเป้า → ขาย
            result = self.handler.create_order_at_market(100, "Sell", self.SYMBOL)
        else:
            return                         # มีหุ้นแต่ยังไม่ถึงเป้า → ถือต่อ

        if "successfully" in str(result):
            self.ordered_today = True

    def cost(self):
        # ต้นทุนเฉลี่ยต่อหุ้น (รวมค่าธรรมเนียมแล้ว) — เก็บในพอร์ต จึงยังอยู่แม้ข้ามวัน
        for stock in self.handler.get_all_stocks_info():
            if stock["Symbol"] == self.SYMBOL:
                return stock["Average Cost"]
```

**หัวข้อนี้รันหลายวัน:**

| รอบ | ตั้งค่า | รันเซลล์ | ต้องได้ |
|---|---|---|---|
| 1 | วันที่ `2026-09-09` · `fresh_start = True` | 3 → 4 → 6 → 7 → 8 | `Created new portfolio` · ซื้อ KBANK 100 หุ้น ต้นทุน 248.42 |
| 2 | เซลล์ 2 เป็น `2026-09-10` · เซลล์ 3 `fresh_start = False` | 2 → 3 → 4 → 6 → 7 → 8 | `Loaded existing portfolio` · KBANK ยังอยู่ ไม่ซื้อซ้ำ ไม่ขาย |
| 3 | — | **9** (รัน 7 วันต่อกันให้เอง) | 09-15 ขาย → **Round-Trip 1** · 09-16 ซื้อรอบใหม่ |

> ⚠️ **จบหัวข้อนี้แล้ว**: เซลล์ 3 ตั้ง `fresh_start` กลับเป็น `True` และเซลล์ 2 วันที่กลับเป็น `2026-09-09`
> ลืม → พอร์ตมี KBANK ค้าง และผลหัวข้อ 7–8 จะไม่ตรง

---

## 6. เปิดกล่องข้อมูลย้อนหลัง

```python
from strategy.Strategies_template import Strategy_template


class MyStrategy(Strategy_template):
    def __init__(self, handler):
        super().__init__("MyTeam", "MyStrategy", handler, timeframe="1D")

        # ดึงข้อมูลย้อนหลังตรงนี้ — ต่อจาก super().__init__() เสมอ
        history = self.handler.get_historical_data("AOT", 5)
        print("ได้มา", len(history), "แท่ง")
        for day in history:
            print(day["Date"], "ปิดที่", day["Close"])

    def on_data(self, bar):
        pass
```

**ต้องได้:** วันที่ + ราคาปิด 5 วันก่อนวันที่รัน (ไม่มีวันที่กำลังรัน) ·
พิมพ์ซ้ำหลายรอบเป็นเรื่องปกติ — หุ้นแต่ละตัวได้ strategy ของตัวเอง

---

## 7. SMA ด้วยมือ

```python
from strategy.Strategies_template import Strategy_template


class MyStrategy(Strategy_template):
    LOOKBACK = 5
    WATCHLIST = ["AOT"]

    def __init__(self, handler):
        super().__init__("MyTeam", "MyStrategy", handler, timeframe="1D")

        # คำนวณครั้งเดียว เก็บไว้ใน self.sma
        self.sma = {}
        for symbol in self.WATCHLIST:
            history = self.handler.get_historical_data(symbol, self.LOOKBACK)
            if len(history) < self.LOOKBACK:
                continue                      # ข้อมูลไม่พอ → ข้ามตัวนี้

            # ↓ คำนวณ SMA เอง ไม่ใช้ library: บวกราคาปิด 5 วัน แล้วหาร 5
            closes = [day["Close"] for day in history]
            self.sma[symbol] = sum(closes) / len(closes)

    def on_data(self, bar):
        symbol = bar["ShareCode"]
        sma = self.sma.get(symbol)            # แค่เปิดดูค่าที่คำนวณไว้
        if sma is None:                       # ไม่อยู่ใน watchlist หรือข้อมูลไม่พอ
            return

        price = bar["Close"]
        if price > sma and not self.handler.check_port_has_stock(symbol, 100):
            self.handler.create_order_at_market(100, "Buy", symbol)
        elif price < sma and self.handler.check_port_has_stock(symbol, 100):
            self.handler.create_order_at_market(100, "Sell", symbol)
```

**คำนวณเองตรงไหน** — 2 บรรทัดใต้ comment `↓ คำนวณ SMA เอง`: ดึงราคาปิดออกมาเป็น list แล้วบวกกันหารจำนวนวัน
ตัวอย่างจริงของ AOT ก่อนวันที่ 09-09:

| วันที่ | 09-02 | 09-03 | 09-04 | 09-07 | 09-08 | **SMA5** |
|---|---|---|---|---|---|---|
| ราคาปิด AOT | 61.75 | 62.75 | 63.50 | 62.50 | 63.00 | 313.50 ÷ 5 = **62.70** |

ไม่มี 09-09 ในตาราง เพราะข้อมูลย้อนหลังหยุดที่เมื่อวานเสมอ

**ต้องได้** (09-09): Round-Trips **86** · ROI ประมาณ **−0.08%** · จบวันไม่ถือหุ้น —
ราคาแค่แกว่งรอบเส้น SMA ก็ซื้อ/ขายวนจนเสียค่าธรรมเนียม

---

## 8. RSI ด้วย TA-Lib

```python
import numpy as np
import talib

from strategy.Strategies_template import Strategy_template


class MyStrategy(Strategy_template):
    LOOKBACK = 60
    RSI_PERIOD = 14
    WATCHLIST = ["AOT", "MTC"]

    def __init__(self, handler):
        super().__init__("MyTeam", "MyStrategy", handler, timeframe="1D")
        self.rsi = {symbol: self._rsi(symbol) for symbol in self.WATCHLIST}

    def _rsi(self, symbol):
        history = self.handler.get_historical_data(symbol, self.LOOKBACK)
        if len(history) < self.RSI_PERIOD + 1:
            return None
        closes = np.array([day["Close"] for day in history], dtype=np.float64)
        value = talib.RSI(closes, timeperiod=self.RSI_PERIOD)[-1]
        return None if np.isnan(value) else float(value)

    def on_data(self, bar):
        symbol = bar["ShareCode"]
        rsi = self.rsi.get(symbol)
        if rsi is None:
            return

        price = bar["Close"]
        if rsi < 40 and not self.handler.check_port_has_stock(symbol, 100):
            self.handler.create_order_at_market(100, "Buy", symbol)
        elif rsi > 60 and self.handler.check_port_has_stock(symbol, 100):
            self.handler.create_order_at_market(100, "Sell", symbol)
```

**ต้องได้** (09-09): Buy Orders ≥ 1 · ถือ **MTC** 100 หุ้นตอนจบวัน (RSI 33) · AOT ไม่ซื้อ (RSI 46) —
ไม่ใช่บั๊ก AOT แค่ RSI อยู่กลาง ๆ

---

## 9. ตัวเต็ม: MACD + RSI หุ้น 8 ตัว

- **เข้าซื้อ** เมื่อ MACD histogram > 0 (ขาขึ้น) **และ** RSI < 70 (ยังไม่แพงเกิน)
- **ขายออก** เมื่อ MACD histogram < 0 **หรือ** RSI > 78
- งบ **400,000 บาท/ตัว** ปัดลงเป็นพหุคูณ 100 และไม่เกินเงินสดที่เหลือ

```python
import numpy as np
import talib

from strategy.Strategies_template import Strategy_template


class MyStrategy(Strategy_template):
    # --- ตั้งค่า indicator ---
    LOOKBACK = 120          # จำนวนแท่งที่ส่งให้ TA-Lib (MACD ต้องการ ~35 ขึ้นไป)
    RSI_PERIOD = 14
    MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9
    OVERBOUGHT = 70.0       # RSI สูงกว่านี้ ไม่เข้าซื้อ
    EXIT_RSI = 78.0         # RSI สูงกว่านี้ ขายทิ้ง

    # --- ตั้งค่าการลงเงิน ---
    WATCHLIST = ["ADVANC", "AOT", "PTT", "KBANK", "SCB", "CPALL", "BBL", "DELTA"]
    BUDGET_PER_POSITION = 400_000.0   # งบต่อหุ้น 1 ตัว
    LOT = 100                          # หน่วยการซื้อขาย ต้องเป็นพหุคูณของค่านี้

    def __init__(self, handler):
        super().__init__("MyTeam", "MyStrategy", handler, timeframe="1D")

        # คำนวณทุกอย่างให้จบตรงนี้ ครั้งเดียว
        # เสร็จแล้ว self.signals จะหน้าตาประมาณ {"AOT": "BUY", "PTT": None, "SCB": "SELL", ...}
        self.signals = {symbol: self._decide(symbol) for symbol in self.WATCHLIST}

    def _decide(self, symbol):
        """สรุปเป็น "BUY" / "SELL" / None (None = ข้อมูลไม่พอ หรือค่ายังเป็น NaN)"""
        history = self.handler.get_historical_data(symbol, self.LOOKBACK)
        if len(history) < self.MACD_SLOW + self.MACD_SIGNAL:
            return None

        closes = np.array([bar["Close"] for bar in history], dtype=np.float64)
        _macd, _signal_line, hist = talib.MACD(
            closes,
            fastperiod=self.MACD_FAST,
            slowperiod=self.MACD_SLOW,
            signalperiod=self.MACD_SIGNAL,
        )
        rsi = talib.RSI(closes, timeperiod=self.RSI_PERIOD)

        if np.isnan(hist[-1]) or np.isnan(rsi[-1]):
            return None

        if hist[-1] > 0 and rsi[-1] < self.OVERBOUGHT:
            return "BUY"
        if hist[-1] < 0 or rsi[-1] > self.EXIT_RSI:
            return "SELL"
        return None

    def _volume_to_buy(self, price):
        """งบต่อไม้ แต่ไม่เกินเงินสดที่เหลือ ปัดลงเป็นพหุคูณของ LOT"""
        budget = min(self.BUDGET_PER_POSITION, self.handler.get_cash_balance())
        lots = int(budget // (price * self.LOT))
        return lots * self.LOT

    def on_data(self, bar):
        symbol = bar["ShareCode"]
        signal = self.signals.get(symbol)
        if signal is None:
            return

        price = bar["Close"]
        held = self.handler.get_total_stock_volume_by_symbol(symbol)

        if signal == "BUY" and held == 0:
            volume = self._volume_to_buy(price)
            if volume >= self.LOT:
                self.handler.create_order_at_market(volume, "Buy", symbol)

        elif signal == "SELL" and held >= self.LOT:
            self.handler.create_order_at_market(held, "Sell", symbol)
```

**ต้องได้** (รัน 7 วันด้วยเซลล์ 9): 4 ใน 8 ตัวไม่เคยเข้าซื้อเลย เพราะ MACD ติดลบตลอด —
เป็นการกรองแนวโน้มที่ทำงานถูก ไม่ใช่บั๊ก

---

## ก่อน push

- [ ] ใน `strategy/` มีไฟล์ของทีม**ไฟล์เดียว** (`Strategies_template.py`, `Example_strategy.py`,
      `Example_historical_strategy.py` ที่มากับ zip ไม่นับ)
- [ ] ชื่อ class ตรงกับชื่อไฟล์ (`MyStrategy.py` ↔ `class MyStrategy`)
- [ ] `"MyTeam"` เปลี่ยนเป็นชื่อทีมที่ลงทะเบียนไว้แล้ว
- [ ] รันใน `TradingSimulation.ipynb` ผ่านแล้ว — **CI ไม่ได้ทดสอบส่วนที่ใช้ข้อมูลย้อนหลัง**
      (ใน CI `get_historical_data` คืน `[]` เสมอ) CI เขียวจึงไม่ได้แปลว่าตรรกะถูก
