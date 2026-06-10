# 事件級數據紀律：核心方法論

> 這份文件跟「澆水機」無關。它講的是一套可以套用到任何嵌入式量產裝置的數據思考方式。
> 這是整個包裡最該先讀、也最可遷移的部分。

---

## 一、為什麼是「事件級」，不是「計數器」

大多數人第一次記錄裝置數據，會這樣做：

```
水了幾次 = 142
錯誤次數 = 3
```

這叫計數器。它的問題是：**當第 143 次出事，你完全不知道是哪一次、什麼時候、什麼狀況下出的。** 數據被壓縮成一個數字，所有上下文都丟了。

事件級數據反過來：**每發生一件事，就記一整行，帶完整上下文。**

```
timestamp_ms, machine_id, firmware_version, command_id, slot_id, event_type, duration_ms, result, error_code
16020, EDEN001, v0.1.0, 0, 3, WATER, 2500, OK, NONE
18540, EDEN001, v0.1.0, 0, 4, WATER, 2480, FAIL, LOW_WATER
```

差別在於：計數器只能回答「總共幾次」，事件級能回答「**第幾台、跑哪個版本、第幾槽、花了多久、成功還失敗、為什麼失敗**」。

量產的時候，後者才能讓你回答真正重要的問題：**這批機隊良率多少？要不要召回？**

### 原則 1：每次事件一行，永遠不要用計數器當主要數據。
計數器可以從事件級數據事後算出來；反過來不行。

---

## 二、Registry 機制：禁止裸字串

最容易毀掉一份數據集的，是「同一件事被寫成好幾種名字」。

```
// 災難現場：
Serial.println("water ok");
Serial.println("Water OK");
Serial.println("watering_success");
```

三行其實是同一件事，但對任何分析工具來說是三種不同的事。等你有 200 台機器、跑了三個韌體版本，這種漂移會讓數據徹底無法分析。

**解法：所有事件名、錯誤名，都來自一個集中的 Registry（列舉），程式裡禁止出現裸字串。**

```cpp
enum class EventType { BOOT, HOME, ROTATE, WATER, ERROR, SHUTDOWN };

const char* eventName(EventType e){
  switch(e){
    case EventType::BOOT:  return "BOOT";
    case EventType::HOME:  return "HOME";
    // ...
  }
  return "ERROR";  // fallback：絕不回傳未註冊的字串污染資料
}
```

這樣全系統只有一個地方定義「WATER 怎麼拼」。改名只改一處，永遠不會漂移。

### 原則 2：事件名與錯誤名集中於 Registry，程式碼任何地方都不准硬編碼字串。

---

## 三、追溯鏈：每一筆數據都要能回答「你從哪來」

一筆數據如果不知道它來自哪台機器、哪個韌體版本、哪套設定，它在量產情境下幾乎沒用——因為你無法區分「是這台機器壞」還是「是這個韌體版本的 bug」。

建立一條單向追溯鏈：

```
Machine ID → Firmware Version → Configuration Version → Schema Version
```

- **Machine ID**：唯一來源 = 韌體的 Config 模組。從第一台就用固定格式（如 EDEN001）。
- **Firmware Version**：唯一來源 = 編譯期 Build Metadata。每一筆數據都帶。
- **Config / Schema Version**：是 Metadata，存在文件與測試報告，**不一定要進每一行 CSV**（否則每行都重複，浪費）。

### 原則 3：每一筆事件數據至少帶 machine_id 與 firmware_version。其餘版本資訊放 Metadata 層。

---

## 四、CSV 與 JSON 欄位名必須完全一致

如果你同時用 CSV（存檔）和 JSON（上傳），它們的欄位名一定要一模一樣。

```
CSV:  timestamp_ms,machine_id,...,event_type,duration_ms,result,error_code
JSON: { "timestamp_ms":..., "machine_id":..., "event_type":"WATER", ... }
```

一旦兩邊命名分裂（`event_type` vs `eventType` vs `type`），跨格式、跨設備的資料就會撕裂，後面再也合不起來。

### 原則 4：一種欄位，一個名字，跨所有格式與傳輸通道。

---

## 五、result 與 error_code 分開，不要混進 event_type

很多人會把成敗塞進事件名：`WATER_OK`、`WATER_FAIL`、`HOME_FAIL`。這會讓事件種類爆炸，且難以統計「所有成功事件」或「所有失敗事件」。

正確做法：**事件種類、結果、錯誤碼，三個獨立欄位。**

- `event_type`：發生了什麼（WATER）
- `result`：成功或失敗（OK / FAIL）
- `error_code`：如果失敗，為什麼（LOW_WATER / NONE）

這樣你可以輕鬆問：「所有 WATER 事件的失敗率？」「所有 LOW_WATER 錯誤分佈在哪幾台機器？」

### 原則 5：「發生什麼」「結果如何」「為何失敗」是三個正交維度，各佔一欄。

---

## 六、最重要的一條：把「還沒驗證什麼」寫進原始碼

這是整套方法論裡最反直覺、也最值錢的一條。

工程師的本能是隱藏未完成的部分，讓 demo 看起來完美。但量產真正的風險，往往藏在「我們以為驗過、其實沒驗」的地方。

所以：**主動、明確地把「這個還沒驗證」「這個只是架構預留」寫進程式碼註解與文件。**

```cpp
// ★EVT-0無Encoder/電流回授,不能宣稱即時失步偵測,故無對應錯誤碼。
// PUMP_FAIL/ROTATE_TIMEOUT 為 Registry 預留,本版無對應偵測,故 CSV 不會出現這些碼。
```

```cpp
// MQTT Topic 上行 [Reserved]：farm/eden001/event。
// Architecture Reserved，EVT-0 未實作未驗證。
```

這帶來兩個好處：
1. **對你自己**：三個月後回來看，不會誤以為某功能已經驗過。
2. **對任何接手的人/客戶**：能誠實劃清已知與未知邊界的工程，比假裝完美的 demo 更值得信任。

### 原則 6：誠實的風險登錄不是弱點，是工程信用。把未驗證項寫進原始碼。

---

## 七、把這六條套到你自己的裝置

這六條原則跟「澆水」「植物」「馬達」都無關。把它們套到你的裝置：

1. 列出你的裝置會發生哪些「事件」→ 建你自己的 EventType Registry
2. 列出可能的失敗原因 → 建你自己的 ErrorCode Registry
3. 設計你的九欄（或 N 欄）事件 schema，確保 CSV/JSON 一致
4. 從第一台就給 machine_id 和 firmware_version
5. 把成敗、錯誤拆成獨立欄位
6. 誠實寫下你「還沒驗證」的每一項

`05_full_case_study/` 是這六條原則套在一台真實滴灌機上的完整結果。你可以照著它的形狀，填進你自己的裝置。

---

*方法論結束。接下來的資料夾是這套方法論的具體實作與工具。*
