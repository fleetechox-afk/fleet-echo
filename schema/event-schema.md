# 事件 Schema 規格（分層版）

> 一個嵌入式裝置事件數據格式。**核心欄位裝置無關、可原封沿用；裝置專屬欄位你自己換。**

> **不想讀表格、想直接驗證?** 這個資料夾裡有兩個可執行檔,零安裝:
> - `event-schema.json` — 正式的 JSON Schema（draft 2020-12),核心 7 欄,可丟進任何 JSON Schema 驗證器。
> - `validate.py` — 零依賴 Python(只用標準庫)。吃 CSV、JSON 陣列、或 JSON-lines(自動偵測),用同一套規則檢查七條核心紀律。`python validate.py your_log.csv`,或 `--json` 輸出機器可讀結果接進 CI。有錯回傳 exit 1。
>
> 下面的表格是這份規格的人類可讀版;上面兩個檔是機器可執行版,一字不差。

---

## 設計哲學：兩層分開（重要）

早期版本把所有欄位混在一起，造成一個問題：`command_id`、`slot_id` 其實是為「會旋轉、有多個槽」的裝置設計的。如果你的裝置沒有「槽」（例如溫控器、單泵設備），這些欄位對你沒意義，你會以為這個 schema 不通用。

**正確設計是分兩層：**

### Layer 1 — 核心追溯層（裝置無關，所有裝置都該有）
```
timestamp, machine_id, firmware_version, event_type, duration_ms, result, error_code
```
這 7 欄是任何嵌入式裝置都適用的骨架。**直接沿用，不要改。**

### Layer 2 — 裝置專屬層（你自己定義，可有可無、可多可少）
```
（旋轉式多槽裝置範例）command_id, slot_id
（你的裝置可能是）zone_id, channel, target_temp …或完全沒有
```
這層放「只對你的裝置有意義」的欄位。**原始案例的 command_id / slot_id 屬於這層——它們是浇水機的胎記，不是核心，你的裝置該換成自己的。**

> 浇水機案例剛好 7 + 2 = 9 欄。但「9」不是神聖數字，**核心 7 欄才是。** 你的裝置可能是 7、8 或 11 欄。

---

## ⚠️ 核心前提：時間戳必須能跨裝置、跨重啟對齊（別當脚註）

這是「跨機隊基準」能不能成立的**致命前提**，不是小細節：

- EVT-0 用開機後相對時間（millis）**只能**用於單機、單次開機分析。
- 一旦你要做「跨機隊比較」「跨重啟趨勢」——也就是你護城河的核心——相對時間會讓對比全錯。設備 A 的 t=5000 和設備 B 的 t=5000 毫無可比性。
- 所以：任何認真的機隊場景，timestamp **必須是可對齊的絕對時間**（RTC、NTP 校時、或上行時伺服器蓋戳）。
- 在接入第一個真實機隊**之前**就要決定時間源策略。它決定你的數據能不能合併。

| 階段 | 時間源 | 能做什麼 |
|------|--------|----------|
| EVT-0 單機 | 開機相對 millis | 單機單次行為分析 |
| 多機 / 機隊 | 絕對時間 | 跨機隊基準、趨勢——**護城河的前提** |

---

## 完整欄位（浇水機案例：核心 7 + 專屬 2）

| 層 | 欄位 | 型別 | 說明 |
|----|------|------|------|
| 核心 | `timestamp` | 整數/時間 | 見上方⚠️。單機可相對 millis；機隊必須絕對時間 |
| 核心 | `machine_id` | 字串 | 機器唯一識別。**從第一台就用** |
| 核心 | `firmware_version` | 字串 | 韌體版本。每筆都帶，區分版本 bug |
| 核心 | `event_type` | 列舉 | 發生什麼。**來自 EventType Registry** |
| 核心 | `duration_ms` | 整數 | 實際耗時（真實量測，非計算值） |
| 核心 | `result` | 列舉 | OK / FAIL。**與 event_type 分開** |
| 核心 | `error_code` | 列舉 | 失敗原因。來自 ErrorCode Registry，成功時 NONE |
| 專屬 | `command_id` | 整數 | （浇水機用）命令識別。你的裝置可能不需要 |
| 專屬 | `slot_id` | 整數 | （浇水機用）哪一槽。換成你自己的或刪掉 |

---

## 範例資料

```csv
timestamp,machine_id,firmware_version,command_id,slot_id,event_type,duration_ms,result,error_code
1717000000000,EDEN001,v0.1.0,0,0,BOOT,0,OK,NONE
1717000006680,EDEN001,v0.1.0,0,1,WATER,2500,OK,NONE
1717000012100,EDEN001,v0.1.0,0,2,WATER,2480,FAIL,LOW_WATER
```
*上例用絕對時間戳示意機隊場景；EVT-0 單機才用從 0 起算的相對 millis。*

JSON（**欄位名與 CSV 一字不差**）：
```json
{ "timestamp":1717000006680, "machine_id":"EDEN001", "firmware_version":"v0.1.0",
  "command_id":0, "slot_id":1, "event_type":"WATER", "duration_ms":2500,
  "result":"OK", "error_code":"NONE" }
```

---

## Registry（事件與錯誤的唯一定義來源）

EventType：`BOOT HOME ROTATE WATER ERROR SHUTDOWN`（ROTATE/WATER 是裝置專屬動作，換成你的）
ErrorCode：`NONE HOME_FAIL LOW_WATER PUMP_FAIL ROTATE_TIMEOUT SENSOR_FAIL MANUAL_STOP`

> **誠實註記：** 原始案例 EVT-0 因無 Encoder／電流回授，實際只發出 HOME_FAIL 與 LOW_WATER。其餘是 Registry 預留位。Registry 可預留未來欄位，但要誠實標明哪些尚未實作。

---

## 與現有遙測格式的關係（誠實說明）

這個 schema 不取代 MQTT Sparkplug、OpenTelemetry 等成熟遙測標準。它們更通用更重；這個格式刻意極簡，針對「資源受限 MCU、要人能直接讀 CSV、從第一行就建立紀律」的場景。**已經在用成熟遙測棧就沿用它；這個 schema 的價值在『還沒有任何紀律、想用最低成本起步』的早期裝置。** 想清楚這層關係，免得重造輪子。

---

## 設計規則

1. **核心 7 欄優先，裝置專屬欄位單獨一層。**
2. 欄位順序固定，CSV 表頭與每行嚴格對齊。
3. CSV 與 JSON 欄位名一字不差。
4. event_type / result / error_code 三者正交，不要把成敗塞進事件名。
5. 機隊場景時間戳必須可對齊（見⚠️）。
6. duration_ms 一律真實量測值。
7. 事件名、錯誤名禁止裸字串，一律經 Registry 函式產生。
8. config_version、schema_version 是 Metadata，不進每行 CSV。

---

## 套到你自己的裝置

1. 核心 7 欄原封沿用。
2. command_id / slot_id 換成你裝置的專屬欄位，或刪掉。
3. EventType / ErrorCode 換成你裝置的動作與失效模式。
4. 機隊場景先決定時間源策略。

**核心層裝置無關，專屬層你自己長——這才是「裝置無關」的真正含義。**
