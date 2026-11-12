# 任務：用 Rust + Polars 實作 scorecrunch（Loop 模式）

你在一個「自我驗證迴圈」裡工作。每一輪你都會被重新叫起來，**沒有上一輪的對話記憶**，
所以一切進度都靠 `STATE.md` 和 `.loop/last_check.log` 交接。

## 完成條件（唯一標準）

`./check.sh` 結束碼為 0，並印出 `🎉 ALL CHECKS PASSED`。
你自己說「應該好了」不算數，只有 check.sh 說了算。

## 每一輪的固定流程

1. **讀狀態**：先讀 `STATE.md`（特別是「Learnings」），再讀 `.loop/last_check.log` 看上一輪卡在哪一關。
2. **挑一件事**：只處理「目前卡住的那一關」最根本的原因。不要一次大改全部。
3. **動手**：只改「允許範圍」內的檔案。
4. **自己驗證**：執行 `./check.sh`，看 PROGRESS 有沒有前進。
   - 前進了 → 可以繼續修下一關，直到本輪快用完為止。
   - 沒前進 → 換方法，不要重複同一招。
5. **寫交接**：在 `STATE.md` 的 Log 加一筆（見下方格式）。同一個修法失敗兩次，就寫進 Learnings，下一輪不准再試。

## 規格

### 命令列

```
scorecrunch --input <CSV> --output <CSV> --group-by <student_id|class> --summary <JSON>
```

- 四個參數都必填，用 `clap`（derive 模式）解析。
- 任何錯誤（檔案不存在、欄位缺少、寫檔失敗）：印出人看得懂的錯誤到 stderr，結束碼非 0，**絕對不能 panic**。
  主程式用 `anyhow::Result`，禁止在非測試程式碼裡用 `.unwrap()` / `.expect()`。

### 輸入 CSV

欄位：`student_id,class,question_type,score,date`（有表頭、UTF-8）。
**所有欄位都先當字串讀進來**，自己做型別轉換，避免 Polars 自動推斷型別出錯。

### 清理規則（依序套用）

1. 所有欄位去掉前後空白。
2. `student_id` 為空 → 丟棄。
3. `score` 轉成 f64，轉不成功（空白、`abc`、`N/A`…）→ 丟棄。
4. `score` 不在 `0 ≤ score ≤ 100` → 丟棄。
5. `date` 必須符合 `YYYY-MM-DD` 或 `YYYY/MM/DD`（兩個分隔符號必須相同，月、日都是兩位數），
   而且是真實存在的日期（`2026-02-30`、`2026-13-40` 要丟棄）。通過的統一改成 `YYYY-MM-DD`。
6. 清理後五個欄位完全相同的列，只保留一筆。

### 輸出報表 CSV

- 依 `<group-by 欄位>, question_type` 分組。
- 欄位與順序固定：`<group-by 欄位>,question_type,count,avg_score`
  例如 `--group-by class` 時表頭是 `class,question_type,count,avg_score`。
- `count`：該組清理後的筆數（整數）。`avg_score`：平均分，四捨五入到小數 2 位。
- 依前兩欄做字串遞增排序。

### Summary JSON

```json
{ "rows_read": 1000000, "rows_clean": 912345 }
```

`rows_read` = 原始資料列數（不含表頭），`rows_clean` = 清理後列數。可以額外加各規則丟棄的筆數，但這兩個鍵必須正確。

### 技術要求

- 用 `polars`（開 `lazy`、`csv` 等需要的 feature）做讀取、清理、分組。Polars 的 Rust API 版本差異很大，
  **以 `cargo doc` 或實際編譯錯誤為準**，不要相信記憶中的舊寫法。
- 至少為「日期驗證」「分數驗證」寫單元測試（放在 `src/` 的 `#[cfg(test)]` 或 `tests/`）。
- 1,000,000 筆資料要在 10 秒內跑完（release 模式）。

## 允許範圍（Scope）

可以新增或修改：`src/`、`tests/`、`Cargo.toml`、`Cargo.lock`、`STATE.md`、`README.md`。

## 禁區（Denylist）——違反任何一條，整輪作廢

- ❌ 修改、刪除或搬移 `check.sh`、`run_loop.sh`、`harness/`、`PROMPT.md`（有雜湊鎖，改了 check 會直接失敗）。
- ❌ 為了通過檢查而「特判」測試資料（例如寫死 seed 42 的答案、偵測檔名）。
- ❌ 用 `#[allow(...)]` 關掉 clippy 警告來過關（真的必要時，在 STATE.md 說明理由）。
- ❌ `git commit` / `git push`、刪除專案資料夾外的任何東西、安裝全域工具。

## STATE.md 的 Log 格式

```
### 第 N 輪
- 開始時卡在：[k/8] <關卡名稱>
- 根本原因：<一句話>
- 做了什麼：<改了哪些檔案、怎麼改>
- 結束時：PROGRESS k/8
```

卡住超過一輪的問題，寫進「Open issues」；試過無效的方法，寫進「Learnings」。
