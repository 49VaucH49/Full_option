# `timeframe` และ `on_data(self, bar)`

`on_data` **ไม่ได้รับ tick ดิบอีกต่อไป** — รับแท่งราคา OHLCV (candlestick) ของ timeframe ที่คุณเลือกไว้ตอน
`super().__init__(...)` แทน คล้ายกับการ subscribe candlestick ของ Settrade Open API

## ระบุ timeframe ตอน construct (บังคับ)

```python
from strategy.Strategies_template import Strategy_template

class MyTeam(Strategy_template):
    def __init__(self, handler):
        super().__init__("my_team", "MyTeam", handler, timeframe="1min")
```

`timeframe` เป็น string ตาม [pandas offset alias](https://pandas.pydata.org/docs/user_guide/timeseries.html#offset-aliases) เช่น
`"1min"`, `"5min"`, `"15min"`, `"60min"`, `"1D"` — ใส่ค่าอื่นที่ไม่ใช่ offset alias ที่ถูกต้องจะ error ตอนรันทันที

## `bar` ที่ได้ใน `on_data`

```python
def on_data(self, bar):
    # bar = {
    #     "ShareCode": "AOT",
    #     "Timestamp": "2025-11-24 10:35:00",   # จุดเริ่มของแท่งปัจจุบัน (มีเวลา)
    #     "Open": 30.00, "High": 30.75, "Low": 29.75, "Close": 30.50,
    #     "Volume": 45600,
    # }
    ...
```

**สำคัญที่สุด: `on_data` ถูกเรียกทุก tick เหมือนเดิม ไม่ใช่แค่ตอนแท่งปิด** — `bar` ที่ได้คือแท่ง**ที่กำลังก่อตัวอยู่ตอนนี้**
ซึ่งจะอัปเดต `High`/`Low`/`Close`/`Volume` ขึ้นเรื่อยๆ ทุกครั้งที่มี tick ใหม่เข้ามาในช่วงเวลาเดียวกัน จนกว่าจะข้ามไป
`Timestamp` ใหม่ (แท่งถัดไป) — เหมือนกับตอนเปิดกราฟ candlestick แบบ real-time แล้วแท่งล่าสุดขยับตามราคาสดๆ ไม่ใช่รอ
แท่งปิดแล้วค่อยเห็น

**การตัดสินใจว่าจะรอให้แท่งปิดก่อนค่อยเทรด หรือจะเทรดทันทีที่เห็น tick ใหม่ เป็น logic ของทีมเองทั้งหมด**
engine ไม่ตัดสินใจแทน ตัวอย่างเช็คว่า "แท่งใหม่เริ่มหรือยัง" ด้วยตัวเอง:

```python
def __init__(self, handler):
    super().__init__("my_team", "MyTeam", handler, timeframe="5min")
    self._last_seen_timestamp = None

def on_data(self, bar):
    is_new_bar = bar["Timestamp"] != self._last_seen_timestamp
    self._last_seen_timestamp = bar["Timestamp"]

    if is_new_bar:
        # เพิ่งขึ้นแท่งใหม่ -- ทำอะไรสักอย่างเฉพาะตอนแท่งก่อนหน้าปิดแล้วก็ได้
        pass
    else:
        # ยังเป็นแท่งเดิม กำลังอัปเดต High/Low/Close/Volume อยู่
        pass
```

## ต่างจาก `get_historical_data` ยังไง

| | `on_data(self, bar)` | `handler.get_historical_data(symbol, n, timeframe)` |
|---|---|---|
| ช่วงเวลา | วันปัจจุบัน (ระหว่างแข่ง/จำลองอยู่) | ย้อนหลัง **ก่อน** วันปัจจุบันเท่านั้น (ดู [`get_historical_data.md`](get_historical_data.md)) |
| ความละเอียด | intraday ตาม `timeframe` ที่เลือก (pandas alias อะไรก็ได้) | `"1D"` (ค่าเริ่มต้น) หรือ intraday เฉพาะ `1min` `3min` `5min` `10min` `15min` `30min` `60min` `120min` `240min` |
| field ระบุเวลา | `"Timestamp"` (วันที่+เวลา) | `"Date"` สำหรับ `"1D"` · `"Timestamp"` สำหรับ intraday |
| เรียกยังไง | engine เรียกให้อัตโนมัติทุก tick | strategy เรียกเองเมื่อต้องการ |

ใช้ `get_historical_data` สำหรับดูเทรนด์ยาว/ข้ามวัน และใช้ `on_data`'s `bar` สำหรับตัดสินใจซื้อขายระหว่างวันจริง
