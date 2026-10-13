# คู่มือทีมแข่งขัน (Competitor Guide)

เอกสารนี้สรุป step การใช้งานทั้งหมดสำหรับทีมที่ส่งกลยุทธ์เข้าแข่ง ตั้งแต่เขียนโค้ดจนถึงดูผล
รายละเอียดกติกาฉบับเต็มอยู่ที่ [`README.md`](../README.md) ของ repo นี้ —
ไฟล์นี้เรียบเรียงเป็นลำดับขั้นตอนให้อ่านเร็วขึ้น

---

## 1. ภาพรวม

ทีมเขียนกลยุทธ์เทรดเป็นไฟล์ Python 1 ไฟล์ → push เข้า repo ของทีม → ระบบตรวจอัตโนมัติ (CI)
ทันทีว่าโค้ดถูกกติกาไหม → ทุกคืน/ทุกวันแข่ง ผู้จัดรันกลยุทธ์ล่าสุดของทุกทีมจริงกับข้อมูลตลาดของวันนั้น
บน VPS ส่วนกลาง → ผลจะถูกเขียนกลับมาเป็น `RESULTS.md` ใน repo ของทีมเอง

**ผลตัดสินจริงมาจากการรันบน VPS เท่านั้น** การรันที่เครื่องตัวเองมีไว้ซ้อม/debug อย่างเดียว

---

## 2. เตรียมตัวก่อนเริ่ม

1. รับ repo ของทีม (สร้างจาก template `strategy-template` โดยผู้จัด — ทีมไม่ต้องสร้างเอง)
2. โหลด engine เต็ม (`tradeSim` + ตัวอย่างข้อมูล tick) `tradeSim<version>.zip` จาก**ลิงก์ Google Drive ที่ผู้จัดส่งให้**
   แล้วแตกทับลงในโฟลเดอร์ repo ของทีม (ระวังแตกซ้อนโฟลเดอร์ — ดูขั้นตอนที่ 3 ใน [`README.md`](../README.md))
3. เปิด `TradingSimulation.ipynb` ที่แนบมา เพื่อรันกลยุทธ์ตัวอย่างที่เครื่องตัวเองดูก่อน
4. อ่าน [`strategy/Example_strategy.py`](../strategy/Example_strategy.py)
   เป็นจุดเริ่มต้น (โครงพร้อมใช้ แก้ไขต่อได้เลย) — ถ้าอยากดูตัวอย่างที่เรียก `get_historical_data` จริง
   ดูที่ [`strategy/Example_historical_strategy.py`](../strategy/Example_historical_strategy.py) แทน

---

## 3. เขียนกลยุทธ์ — กติกาโครงสร้าง (บังคับ)

| ข้อ | กติกา |
|---|---|
| ไฟล์ | เขียนกลยุทธ์ไว้ที่ `strategy/<ชื่อไฟล์>.py` **1 ไฟล์เท่านั้น** ต่อ repo |
| ชื่อ class | ต้องตรงกับชื่อไฟล์เป๊ะ ๆ (ไฟล์ `MyTeam.py` → `class MyTeam(...)`) |
| Inherit | ต้อง inherit จาก `Strategy_template` โดยตรง (**ห้ามแก้ไฟล์** [`Strategies_template.py`](../strategy/Strategies_template.py)) |
| Constructor | เรียก `super().__init__(owner, strategy_name, handler, timeframe)` — `owner`/ชื่อทีมต้องตรงกับที่ลงทะเบียนไว้กับผู้จัด (ระบบเช็คไขว้กับ roster) |
| Timeframe | กำหนดเอง เช่น `"1min"`, `"5min"`, `"1D"` (pandas offset alias ใดก็ได้) |
| Method บังคับ | ต้อง implement `on_data(self, bar)` |

> ⚠️ **"1 ไฟล์เท่านั้น" หมายถึงไฟล์เดียวจริง ๆ** — ระบบหยิบไฟล์ส่งงานด้วยการไล่ `.py` ทั้งหมดใน
> `strategy/` แล้วตัด 4 ไฟล์ที่มากับ template ทิ้ง (`Strategies_template.py`, `Example_strategy.py`,
> `Example_historical_strategy.py`, `__init__.py`) **ที่เหลือต้องมีพอดี 1 ไฟล์**
>
> | วางอะไรไว้ใน `strategy/` | ผล |
> |---|---|
> | ไฟล์กลยุทธ์ของทีมไฟล์เดียว | ✅ ผ่าน |
> | `.py` ตัวที่สอง (โมดูลย่อย, ไฟล์สำรอง เช่น `MyTeam_backup.py`) | ❌ CI แดง — `Expected exactly one strategy file ... found 2` |
> | `.json` `.skops` `.txt` `.ubj` `.cbm` (≤20MB) | ✅ ผ่าน และถูกส่งไปรันด้วย |
> | `.pkl` `.joblib` `.h5` `.pt` | ❌ CI แดง — รันโค้ดได้ตอนโหลด |
> | `.csv` `.md` อื่น ๆ | ⚠️ ผ่าน CI แต่**ไม่ถูกส่งไปรันด้วย** (และเปิดอ่านเองไม่ได้ `open()` ต้องห้าม) |
>
> `git add .` ไม่เตือนอะไรทั้งนั้น จะรู้ตัวอีกทีตอนแท็บ Checks ขึ้นแดง
>
> **ทดลองอะไรนอก `strategy/` ได้ตามสบาย ไม่ได้ห้าม** — สคริปต์ train โมเดล, โน้ตบุ๊ควิเคราะห์,
> กราฟ, ข้อมูลดิบ วางไว้ที่ root หรือโฟลเดอร์ของตัวเองแล้ว commit ขึ้น repo ไปด้วยก็ไม่มีปัญหา
> เพราะ CI ดูเฉพาะใน `strategy/` เท่านั้น
>
> **กฎมีข้อเดียว: ไฟล์กลยุทธ์ต้องรันได้ด้วยตัวเองไฟล์เดียว ห้าม `import` ไฟล์อื่นของทีม**
> ไม่ว่าไฟล์นั้นจะอยู่ใน `strategy/`, ในโฟลเดอร์ย่อย หรือที่อื่นใน repo — ระบบคัดลอกไปรันแค่
> ไฟล์กลยุทธ์กับไฟล์แนบที่อนุญาต โค้ดที่พึ่งไฟล์อื่นจะพังบนเครื่องผู้จัด ทั้งที่เครื่องตัวเองรันผ่าน
>
> **ถ้าจำเป็นต้องมี helper function จริง ๆ ให้ติดต่อผู้จัดก่อน** — ส่งเป็น request หรือ message
> มาให้ทีมงานตรวจ อย่าเพิ่ง push ไฟล์ที่สองขึ้นไปเอง

**คำนวณ indicator หนัก ๆ ให้ทำใน `__init__`** — `self.handler` ใช้งานได้ตั้งแต่ใน `__init__` แล้ว
ซึ่งทำงานครั้งเดียว ต่างจาก `on_data` ที่ถูกเรียกวันละ ~190,000 ครั้ง และเพราะ `get_historical_data()`
คืนข้อมูลถึงแค่วันก่อนหน้า ข้อมูลจึงนิ่งตลอดวัน คำนวณซ้ำทุก tick = ได้คำตอบเดิมเสมอ
(ดูตัวอย่างเต็มที่ [`docs/examples/Test_TALib_strategy.py`](examples/Test_TALib_strategy.py))

**`on_data` ทำงานทุก tick ไม่ใช่แค่ตอนปิดแท่ง** — `bar` ที่ได้รับคือแท่งราคา timeframe ที่เลือก
ซึ่งยัง "กำลังก่อตัว" (update ทุก tick) ไม่ใช่ tick ดิบ และไม่ใช่แท่งที่ปิดแล้วเท่านั้น
ถ้าต้องการ logic แบบ "ทำงานเฉพาะตอนแท่งใหม่เริ่ม" ต้องเช็ค timestamp เองในโค้ด
(ดูตัวอย่าง pattern ที่ [`docs/on_data_timeframe.md`](on_data_timeframe.md))

---

## 4. สิ่งที่ห้ามทำ (ตรวจอัตโนมัติด้วย static analysis, ตกทันทีถ้าเจอ)

- **ห้าม import**: `os`, `sys`, `subprocess`, `socket`, `shutil`, `requests`, `urllib`, `http`,
  `ftplib`, `importlib`, `ctypes`, `multiprocessing`, `threading`, `pathlib`
- **ห้ามเรียก**: `eval`, `exec`, `compile`, `__import__`, `open`
- ห้ามมีมากกว่า 1 class หลักในไฟล์ หรือชื่อ class ไม่ตรงไฟล์

เหตุผล: strategy รันในแซนด์บ็อกซ์ ห้ามแตะ filesystem/network/process ใด ๆ

---

## 5. Method ที่ใช้ได้ผ่าน `self.handler`

รายละเอียดเต็ม/ตัวอย่าง output ของแต่ละ method อยู่ที่ [`docs/api_reference.md`](api_reference.md) — ตารางนี้มีแค่ signature + กับดักที่ควรรู้ก่อนใช้สั้น ๆ

| Method | Parameter | หมายเหตุ |
|---|---|---|
| `create_order_to_limit` | `(volume, price, side, symbol)` | ได้**ราคาที่ตั้งหรือดีกว่า**เท่านั้น · ใช้ฝั่งของ tick ตัดสิน: tick ฝั่ง Buy = มีคนตั้งขายที่ราคานั้น · ฝั่ง Sell = ราคานั้นคือฝั่งเสนอซื้อ (คนตั้งขายถูกสุด ≈ +1 ช่วงราคา) · ถ้ายังไม่มีคนขายถึงราคา คำสั่ง**ค้างใน order book** จนจบวัน แล้วได้ราคาที่ตั้งเมื่อตลาดลงมาถึง · ตั้งที่ `bar["Close"]` ไม่รับประกันว่าได้หุ้น · tick ช่วงประมูลไม่จับคู่ limit · เรียกทุก tick = คำสั่งค้างพอกพูน ให้เช็ค `get_open_orders()` ก่อน · ข้อความที่คืนมามีเลขคำสั่ง (ใช้กับ `cancel_order`) · "successfully" ≠ ได้หุ้น — รายละเอียดที่ [A guide to create a buy/sell order](api_reference.md#a-guide-to-create-a-buysell-order) |
| `create_order_at_market` | `(volume, side, symbol)` | ไม่ต้องใส่ราคา **ได้ทันทีเสมอ**ไม่สนฝั่งของ tick · ซื้อจ่ายราคาล่าสุด + 1 ช่วงราคา ขายได้ราคาล่าสุด − 1 ช่วงราคา (แทนการข้าม spread) · สั่งได้เฉพาะหุ้นของแท่งที่กำลังประมวลผล (`bar["ShareCode"]`) · ใช้เมื่อต้องเข้า/ออกทันที เช่น ตัดขาดทุน · ได้ข้อความ "submitted successfully" = ระบบรับคำสั่งแล้ว ไม่ใช่ได้หุ้น — ดูราคาที่ได้จริงใน [transaction log](api_reference.md#reading-the-transaction-log) |
| `get_open_orders` | `(symbol=None)` | คำสั่ง limit ที่ยังค้างอยู่ เป็น list ของ dict (เลขคำสั่ง หุ้น ฝั่ง จำนวน ราคา เวลา) เรียงจากเก่าไปใหม่ · ครอบทั้ง order book ของทีม ใส่ `bar["ShareCode"]` ถ้าจะดูเฉพาะหุ้นตัวเอง — รายละเอียดที่ [Managing resting orders](api_reference.md#managing-resting-orders) |
| `cancel_order` | `(order_number)` | ยกเลิกคำสั่งที่ค้างอยู่ 1 ตัว คืน `True` ถ้ายกเลิกได้ · `False` ถ้าได้หุ้นไปแล้ว ถูกยกเลิกไปแล้ว หรือไม่เคยค้าง |
| `cancel_all_orders` | `(symbol=None)` | ยกเลิกคำสั่งที่ค้างทั้งหมด หรือเฉพาะหุ้น `symbol` คืนจำนวนที่ยกเลิก |
| `check_port_has_stock` | `(symbol, volume)` | เช็คจากปริมาณที่ถืออยู่จริงตอนนี้เท่านั้น — รายละเอียดที่ [Check if portfolio has stock](api_reference.md#check_port_has_stocksymbol-volume) |
| `get_stock_by_symbol` | `(symbol)` | คืนเป็น **list** ของทุกล็อตที่ถืออยู่ (FIFO) ไม่ใช่ object เดียว — รายละเอียดที่ [Get information from the stocks in the portfolio by symbol](api_reference.md#get_stock_by_symbolsymbol) |
| `get_all_stocks_info` | `()` | สรุปรวมทุกล็อตของ symbol เดียวกันเป็น 1 แถวต่อ symbol — รายละเอียดที่ [Get information from the stocks in the portfolio](api_reference.md#get_all_stocks_info) |
| `get_portfolio_info` | `()` | คืน dict สรุปพอร์ตทั้งก้อน — ดูฟิลด์ทั้งหมด/กับดักชื่อ method ที่ [Get information from the portfolio](api_reference.md#get_portfolio_info) |
| `get_cash_balance` | `()` | สะท้อนเฉพาะเงินสดหลัง order ที่ **match แล้วจริง** เท่านั้น ไม่มี concept "จองเงิน" ตอนสั่ง order — รายละเอียดที่ [Additional getter method for strategy runner](api_reference.md#additional-getter-method-for-strategy-runner) |
| `get_historical_data` | `(symbol, n, timeframe="1D")` | anti-lookahead, cap ที่ 1000 แท่ง, `"1D"` ดึงจาก `marketInfo/ticks/` + `marketInfo/daily_history/<symbol>.csv` รวมกันอัตโนมัติ · ใส่ `timeframe` intraday (`"5min"`, `"60min"` ฯลฯ) ได้แท่งระหว่างวันของวันก่อน ๆ — ย้อนหลังได้สั้นกว่ารายวัน · ใส่ `"SET50"` เป็น symbol เพื่อขอแท่งย้อนหลังของ**ตัวดัชนี**ได้ (ดูข้อมูลได้ แต่สั่งซื้อขายไม่ได้) — รายละเอียดเต็มที่ [`get_historical_data(symbol, n)`](api_reference.md#get_historical_datasymbol-n) หรือ [`docs/get_historical_data.md`](get_historical_data.md) |

---

## 6. Library ที่ใช้ได้ (ลงไว้ล่วงหน้าบน runner แล้ว)

**ทีมสั่ง `pip install` เองไม่ได้** (ตัดออกเพื่อความปลอดภัย) ใช้ได้เลยโดยไม่ต้องขอ:

- **ตัวเลข/สถิติ**: `numpy`, `pandas`, `scipy`, `statsmodels`
- **Machine learning**: `scikit-learn`, `xgboost`, `lightgbm`, `catboost`
- **Technical analysis**: `TA-Lib` (import เป็น `talib`), `ta`, `finta`
- **Time series**: `pmdarima`, `arch`
- **Portfolio optimization**: `cvxpy`, `PuLP`, `pyportfolioopt` (import เป็น `pypfopt`)
- **Plotting** (ใช้ debug ที่เครื่องตัวเองเท่านั้น): `matplotlib`
- **Symbolic math**: `sympy`
- **Model serialization ที่ปลอดภัย**: `skops`

**ติดตั้งในเครื่องตัวเอง** แบ่งเป็น 2 ไฟล์ (บน runner มีครบทั้งหมดอยู่แล้ว):
- `pip install -r requirements.txt` — จำเป็น: engine, `numpy` `pandas`, technical analysis และ Jupyter (~80MB)
- `pip install -r requirements-optional.txt` — **ลงเมื่อจะใช้จริง**: ตัวเลข/สถิติที่เหลือ, ML,
  time series, portfolio optimization, `matplotlib`, `sympy`, `skops` (~240MB)
  ถ้ายังไม่ได้ลงแล้ว import → `ModuleNotFoundError` ในเครื่องตัวเอง (บน runner ไม่เป็น)

ต้องการ library อื่นนอกเหนือจากนี้ → **ติดต่อผู้จัดโดยตรง** ไม่มีกลไกขอผ่าน push

---

## 7. แนบไฟล์โมเดล/config มากับกลยุทธ์ (ถ้าต้องใช้)

1. วางไฟล์ในโฟลเดอร์ `strategy/` เดียวกับไฟล์ `.py` ของทีม
2. โหลดผ่าน `self.handler` เท่านั้น (เรียก `open()` เองไม่ได้):

   | Method | ใช้กับ |
   |---|---|
   | `handler.load_json(filename)` | ไฟล์ `.json` (config/พารามิเตอร์) |
   | `handler.load_model(filename)` | ไฟล์ `.skops` (โมเดล scikit-learn ที่ train แล้ว) |
   | `handler.get_companion_path(filename)` | ไฟล์ `.json`/`.txt`/`.ubj`/`.cbm` ที่จะยื่นให้ library โหลดเอง (xgboost `.json`/`.ubj` · lightgbm `.txt` · catboost `.cbm`) |

3. **ห้ามแนบ** `.pkl`/`.pickle`/`.joblib`/`.h5`/`.pt`/`.pth` — รันโค้ดได้ตอนโหลด ตรวจไม่ผ่านทันทีถ้าเจอ
   - โมเดล scikit-learn → เซฟด้วย `skops.io.dump(model, "strategy/model.skops")`
   - โมเดล xgboost/lightgbm → ใช้ native format ของตัวเอง (`Booster.save_model("model.json")` / `"model.txt"`)
4. แต่ละไฟล์ห้ามเกิน **20MB**

---

## 8. ส่งงาน — ขั้นตอน push

1. Commit + push โค้ดเข้า branch **`main`** ของทีม — CI ตรวจให้ทุก push ทุก branch แต่**ใช้แข่งเฉพาะโค้ดบน `main`**
2. เปิดแท็บ **Checks** บนหน้า commit ของตัวเองใน GitHub
3. **เขียว** = ผ่านการตรวจโครงสร้าง+dry-run, ระบบจะใช้โค้ดเวอร์ชันนี้ตัดสินจริงตั้งแต่วันเทรดถัดไปที่ทันเส้นตาย **09:30** (ดูด้านล่าง)
4. **แดง** = ระบบ**ไม่เอาไปใช้** แข่งต่อด้วยเวอร์ชันล่าสุดที่เคยผ่าน (ถ้ายังไม่เคยมีตัวที่ผ่านเลย
   วันนั้นจะไม่มีผล) — เปิด log ใน Checks ดูรายละเอียด error ตรง ๆ แก้แล้ว push ใหม่

### ระบบเก็บโค้ดเป็นเวอร์ชันยังไง

**เส้นตายคือ 09:30 ของวันเทรด** — แต่ละวันเทรด ระบบใช้โค้ดบน `main` ตามที่เป็นอยู่ ณ **09:30 น. ของวันนั้น**

| push เมื่อไหร่ | ใช้กับวันเทรดไหน |
|---|---|
| ก่อน 09:30 ของวันที่ 16 | วันที่ 16 |
| ตั้งแต่ 09:30 ของวันที่ 16 เป็นต้นไป | วันเทรดถัดไป (วันที่ 17) |

ถ้าโค้ด ณ 09:30 เปลี่ยนจากวันก่อน**และ CI ไม่แดง** จะถูกเก็บเป็นเวอร์ชันใหม่ (v1 → v2 → …) ถ้าไม่เปลี่ยนก็ใช้เวอร์ชันเดิมต่อ
ทุกเวอร์ชันเก็บไว้ตลอด ไม่มีการเขียนทับ

- เวลาที่นับคือ**เวลาที่ GitHub ได้รับ push** ไม่ใช่เวลาที่เขียนใน commit — commit ไว้ก่อนแต่ push หลัง 09:30 = นับเป็นวันถัดไป
- push หลายรอบ นับเฉพาะโค้ดที่อยู่บน `main` ณ 09:30
- ผู้จัดรันจำลองของแต่ละวัน**หลังตลาดปิด** (ปกติเช้าวันทำการถัดไป) ผลใน `RESULTS.md` จึงขึ้นช้ากว่าวันเทรด 1 วัน — ไม่มีผลกับเส้นตาย
- push ให้เขียวก่อน 09:30 จะปลอดภัยที่สุด — โค้ดที่ CI แดงไม่ถูกใช้ ระบบแข่งต่อด้วยเวอร์ชันก่อนหน้า
- ถ้าเวอร์ชันล่าสุดไปพังตอนรันจริง (error หรือเกิน 15 นาที) ระบบลองเวอร์ชันก่อนหน้าให้ **1 เวอร์ชัน**

### สิ่งที่ CI ตรวจ เรียงตามลำดับ (ล้มที่ข้อไหนหยุดที่ข้อนั้น)

1. **Syntax** — โค้ด parse ได้ไหม
2. **โครงสร้าง** — มี class เดียว, ชื่อ class ตรงไฟล์, inherit `Strategy_template`, มี `on_data`
3. **Import/call ต้องห้าม** — ตามข้อ 4 ด้านบน
4. **ชื่อทีมตรงกับ roster** — `owner`/`strategy_name` ที่ใส่ใน `super().__init__()` ต้องตรงกับชื่อทีมที่ลงทะเบียนไว้กับผู้จัด (สำคัญมาก — ถ้าไม่ตรง ผลจะถูกไฟล์ผิดทีมหรือ CI ไม่ผ่าน)
5. **Dry-run จริง** — เอาไฟล์ไปรันจริงกับข้อมูล tick ตัวอย่าง 1 วัน เพื่อพิสูจน์ว่ารันจบไม่ error/ไม่ timeout (ยังไม่ใช่ผลคะแนนจริง — แค่พิสูจน์ว่ารันได้)

**CI เขียวไม่ได้แปลว่ากลยุทธ์ทำงานถูก** — dry-run ไม่มีข้อมูลย้อนหลัง `get_historical_data()` จึงคืน `[]`
ทุกครั้ง โค้ดส่วนที่คำนวณจากข้อมูลย้อนหลังจะไม่ถูกรันใน CI เลย ต้องรัน `TradingSimulation.ipynb`
กับข้อมูลจริงเองก่อน push · ตอนรันจริงประจำวันมีเวลาให้ **15 นาที/ทีม/วัน** (ปกติใช้ ~20 วินาที)
ถ้าเกินหรือ error ระบบจะใช้เวอร์ชันก่อนหน้าของทีมแทน

หมายเหตุ: ถ้า push ครั้งแรกยังไม่มีไฟล์กลยุทธ์ (repo เพิ่งสร้างจาก template) CI จะผ่านเฉย ๆ
โดยไม่ตรวจอะไร (ยังไม่มีอะไรให้ตรวจ)

---

## 9. ดูผลการแข่งขัน

- ทุกวันที่มีการรันจริง ผู้จัดจะ push ไฟล์ `RESULTS.md` / `results.csv` กลับเข้า repo ของทีมเองอัตโนมัติ
- ใน `RESULTS.md` จะมี: ตัวเลขของวันล่าสุด (Portfolio Total Return, MaxDD, Excess Return, Calmar,
  Total Round-Trip, Win Rate, Expected Payoff, Avg Exposure, Benchmark Return, Benchmark MaxDD),
  ตาราง holdings ปัจจุบัน, และตารางย้อนหลังทั้งหมด
- เกณฑ์คุณสมบัติที่ใช้ตอนจัดอันดับ (อิงเกณฑ์ "Common Criteria" ของการแข่งขัน) — ในตารางรายวันจะขึ้นเป็น
  `PASS` หรือ `NOT MET: <เหตุผล>` ซึ่ง**ยังไม่ใช่การตัดสิทธิ์** เป็นแค่สถานะ ณ วันนั้น วันถัดไปกลับมาผ่านได้:

  | เกณฑ์ | ต้องผ่าน |
  |---|---|
  | Max Drawdown | **น้อยกว่า** 1.5 เท่าของ Benchmark MaxDD (เท่ากับพอดี = ไม่ผ่าน) |
  | จำนวน Round-trip | ≥ 5 |
  | Average Exposure | ≥ 50% |
  | Expected Payoff | > 0 |

---

## 10. คำถามที่พบบ่อย

- **push แล้ว Checks ไม่ขึ้นเลย** → เช็คว่า push เข้า branch จริงหรือไม่ (workflow trigger ทุก branch)
- **แดงที่ "Checkout production engine"** → ไม่ใช่ปัญหาโค้ดทีม เป็นปัญหาฝั่งผู้จัด (token/engine repo) ติดต่อผู้จัด
- **แดงเพราะ forbidden import** → ปกติมักเกิดจาก import อ้อม ๆ ผ่าน library อื่นที่ import `os`/`sys` ภายใน — เช็ค import ตรง ๆ ในไฟล์ของตัวเองก่อน (ตัวตรวจดูเฉพาะ import ระดับ root ของไฟล์เรา ไม่ไล่เข้าไปใน library ที่อนุญาต)
- **แดงเพราะชื่อทีมไม่ตรง roster** → เช็คค่าที่ใส่ใน `super().__init__(owner, ...)` ให้ตรงกับชื่อทีมที่ลงทะเบียนไว้เป๊ะ ๆ (case-sensitive)
- **ผลที่เครื่องตัวเองกับผลจริงต่างกัน** → ปกติ ถ้าเครื่องตัวเองใช้ข้อมูล/เวอร์ชัน engine เก่ากว่า VPS จริง — อ้างอิงผลจาก `RESULTS.md` ใน repo ทีมเท่านั้น
