import numpy as np
import talib

from strategy.Strategies_template import Strategy_template


class Test_TALib_strategy(Strategy_template):
    """ตัวอย่างกลยุทธ์ที่ใช้ indicator จาก TA-Lib บนข้อมูลย้อนหลัง

    ==================================================================
    กลยุทธ์นี้ทำอะไร
    ==================================================================

    ดูหุ้น 8 ตัวใน WATCHLIST แล้วตัดสินใจจาก indicator 2 ตัวประกอบกัน

      MACD histogram  บอก "ทิศทาง"  -> บวก = โมเมนตัมขาขึ้น
      RSI             บอก "ความร้อน" -> สูงมาก = ราคาวิ่งมาไกลเกินไปแล้ว

      เข้าซื้อ : MACD hist > 0  และ  RSI < 70
                 (ขาขึ้น แต่ยังไม่ร้อนเกิน — ไม่ไล่ซื้อของแพง)
      ขายออก  : MACD hist < 0  หรือ  RSI > 78
                 (ทิศทางกลับ หรือ ร้อนจัดจนน่าจะย่อ)

    ขนาดไม้ : งบ 400,000 บาทต่อหุ้น 1 ตัว ปัดลงให้เป็นพหุคูณของ 100 หุ้น
              และตัดตามเงินสดที่เหลืออยู่จริง

    ==================================================================
    ลำดับการทำงาน — จุดที่อยากให้ดูเป็นพิเศษ
    ==================================================================

    1) ตอนสร้าง strategy (__init__)  <- ทำครั้งเดียว
         ดึงข้อมูลย้อนหลังของทุกตัวใน WATCHLIST
         คำนวณ MACD/RSI ด้วย TA-Lib
         สรุปเป็นคำตอบ "BUY / SELL / None" เก็บไว้ใน self.signals

    2) ตอน on_data (ทุก tick)        <- ทำแสนกว่าครั้งต่อวัน
         แค่เปิดดู self.signals แล้วสั่งซื้อขาย
         ไม่มีการดึงข้อมูลหรือคำนวณ indicator ใด ๆ อีกเลย

    ทำไมต้องแยกแบบนี้:

      on_data ถูกเรียกทุก tick — วันหนึ่งประมาณ 190,000 ครั้ง ถ้าคำนวณ
      indicator ตรงนั้นก็จะคำนวณซ้ำแสนกว่ารอบเพื่อให้ได้ "คำตอบเดิม"
      ทุกครั้ง เพราะ get_historical_data() คืนเฉพาะวันก่อนหน้าวันที่
      กำลังเทรด ข้อมูลชุดนี้จึงนิ่งตลอดทั้งวัน ไม่มีทางเปลี่ยนระหว่างวัน

      พูดอีกแบบ: ข้อมูลเปลี่ยนวันละครั้ง ก็ควรคำนวณวันละครั้ง

    ==================================================================
    ข้อควรระวังที่โผล่มาจากการใช้ TA-Lib จริง
    ==================================================================

    * TA-Lib รับ numpy array ของ float ไม่ใช่ list ของ dict -> ต้องแปลงก่อน

    * ช่วงอุ่นเครื่อง TA-Lib จะเติมค่า NaN มาให้ และการเปรียบเทียบอะไร
      กับ NaN ได้ False เสมอ ถ้าไม่เช็ค np.isnan() กลยุทธ์จะกลายเป็น
      "ไม่มีสัญญาณ" แบบเงียบ ๆ โดยไม่มี error ให้เห็นเลย

    * indicator แต่ละตัวต้องการจำนวนแท่งขั้นต่ำไม่เท่ากัน MACD(12,26,9)
      ต้องการประมาณ 35 แท่งขึ้นไป และบางหลักทรัพย์มีข้อมูลย้อนหลังสั้น
      กว่าเพื่อน จึงต้องเช็คความยาวก่อนคำนวณเสมอ

    * เงื่อนไขเข้าใช้ "hist > 0" (สถานะ) ไม่ใช่ "hist ตัดขึ้นผ่าน 0"
      (crossover) เพราะข้อมูลย้อนหลังหยุดที่เมื่อวาน กฎ crossover จึงยิง
      ได้แค่วันเดียวหลังตัด — ทดสอบจริง 7 วัน x 8 ตัว ได้สัญญาณเข้าแค่
      1 ครั้ง ขณะที่แบบสถานะได้ 14 ครั้ง

    * คำสั่งซื้อขายถูกปฏิเสธได้เป็นปกติ (เงินไม่พอ หรือปริมาณฝั่งตรงข้าม
      ยังสะสมไม่พอในช่วงเช้า) create_order_* คืนข้อความกลับมา ไม่ throw
      กลยุทธ์จึงไม่ต้องทำอะไรเป็นพิเศษ — tick ถัดไปก็ลองใหม่เอง
    """

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
        super().__init__("test", "Test_TALib_strategy", handler, timeframe="1D")

        # คำนวณทุกอย่างให้จบตั้งแต่ตรงนี้ ครั้งเดียวต่อการรัน 1 วัน
        # เสร็จแล้ว self.signals จะหน้าตาประมาณ
        #   {"AOT": "BUY", "PTT": None, "SCB": "SELL", ...}
        self.signals = {symbol: self._decide(symbol) for symbol in self.WATCHLIST}

    # ------------------------------------------------------------------
    def _decide(self, symbol):
        """อ่านข้อมูลย้อนหลังของ symbol แล้วสรุปเป็น BUY / SELL / None

        คืน None เมื่อ "ยังตัดสินใจไม่ได้" ซึ่งมีได้ 2 กรณี คือข้อมูล
        ย้อนหลังไม่พอให้ indicator คำนวณ กับค่าที่ได้ยังเป็น NaN
        """
        history = self.handler.get_historical_data(symbol, self.LOOKBACK)

        # ข้อมูลไม่พอให้ MACD คำนวณ (เช่นหุ้นที่เพิ่งเข้า SET50 ได้ไม่นาน)
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

        # ค่าล่าสุดยังเป็น NaN แปลว่า indicator ยังอุ่นเครื่องไม่เสร็จ
        if np.isnan(hist[-1]) or np.isnan(rsi[-1]):
            return None

        if hist[-1] > 0 and rsi[-1] < self.OVERBOUGHT:
            return "BUY"
        if hist[-1] < 0 or rsi[-1] > self.EXIT_RSI:
            return "SELL"
        return None

    def _volume_to_buy(self, price):
        """จำนวนหุ้นที่ซื้อได้จริง = งบต่อไม้ แต่ไม่เกินเงินสดที่เหลือ
        แล้วปัดลงให้เป็นพหุคูณของ LOT (คำสั่งที่ไม่ลงตัว 100 จะถูกปฏิเสธ)"""
        budget = min(self.BUDGET_PER_POSITION, self.handler.get_cash_balance())
        lots = int(budget // (price * self.LOT))
        return lots * self.LOT

    # ------------------------------------------------------------------
    def on_data(self, bar):
        """ถูกเรียกทุก tick — ตรงนี้มีแค่ "เปิดตารางคำตอบแล้วสั่ง" เท่านั้น
        ไม่มีการดึงข้อมูลหรือคำนวณ indicator ใด ๆ"""
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
