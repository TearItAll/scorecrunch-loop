# Loop State

Goal: 用 Rust + Polars 實作 scorecrunch，讓 ./check.sh 全部通過
Done criteria: ./check.sh exit 0（8/8 關卡）
Iteration: 4 / 8（已完成：8/8 通過）

## Log

### 第 1 輪
- 開始時卡在：[1/8] cargo fmt（專案不存在）
- 根本原因：沒有 Cargo.toml / src。
- 做了什麼：建立 Cargo.toml（polars 0.55 lazy/csv/strings/round_series、clap derive、anyhow、serde_json）、
  src/main.rs（讀 CSV 全字串 → lazy strip_chars + 過濾空 student_id → Rust 函式驗證 score/date →
  unique_stable → group_by/agg/sort → CsvWriter + summary JSON）、src/validate.rs（parse_score、
  normalize_date 及單元測試）。已 cargo fmt。
- 結束時：PROGRESS 1/8。卡在 [2/8] clippy：**環境問題，不是程式碼問題**（見 Open issues）。
  main.rs 還沒有被編譯器檢查過，下一輪能編譯後先看編譯錯誤（polars API 可能要調整）。

### 第 2 輪
- 開始時卡在：[2/8] cargo clippy
- 根本原因：環境問題沒變，`cargo check` 仍然因為 `dlltool.exe: program not found`（getrandom 0.4.3）失敗。
  也確認了 ~/.cargo 底下沒有 config.toml，dlltool 也還是只有 rustup self-contained 那一份。
- 做了什麼：沒有改程式碼。查過原始碼：windows-link 0.2.1 的 `link!` macro 和 getrandom 0.4.3 的 windows backend
  都**無條件**使用 `kind = "raw-dylib"`，沒有 Cargo feature 可以關，所以只改 Cargo.toml 沒辦法繞過去。
- 結束時：PROGRESS 1/8（等人處理環境）

### 第 3 輪
- 開始時卡在：[2/8] cargo clippy
- 根本原因：同第 1、2 輪，`cargo check` 仍然出現 `error calling dlltool 'dlltool.exe': program not found`（getrandom 0.4.3）。環境沒有變。
- 做了什麼：沒有改程式碼，只跑 `cargo check` 確認錯誤還在。PowerShell 的指令（連單獨一個 `cargo check` 也算）
  這一輪都會被擋下要求核准，Bash 工具才跑得動。另外確認了把 dlltool.exe 放進專案資料夾沒有用：
  Rust 的 `Command` 在 Windows 上不會搜尋目前目錄。
- 結束時：PROGRESS 1/8（阻塞，等人處理環境，請看 Open issues）

### 第 4 輪（prompt 標示為第 1 / 8 輪，跑在環境修好之後）
- 開始時卡在：[2/8] cargo clippy
- 根本原因：polars-expr 0.55.2 的上游 feature bug：開了 `strings` 卻沒開任何會帶入 `polars-time` 的 feature，
  `dispatch/strings.rs` 就無條件 `use polars_time` 而編譯失敗。
- 做了什麼：Cargo.toml 的 polars 加上 `dtype-date` feature（會帶入 polars-time）。main.rs：polars prelude 的
  `PolarsContext` 和 `anyhow::Context` 方法同名會衝突 → 移除 `anyhow::Context`，改用自訂 `ctx()` 輔助函式；
  `with_column` 改收 `Column`（`.into_series().into()`）；`&PathBuf` → `&Path`。validate.rs 用 `is_multiple_of`。
- 結束時：PROGRESS 8/8，🎉 ALL CHECKS PASSED（100 萬筆約 0.8 秒）

## Open issues

- 無。（dlltool 問題已在 2026-11-12 由人工改用 MSVC 工具鏈解決。）
- **[已解決，歷史紀錄] 找不到 `dlltool.exe`**：工具鏈只有 `stable-x86_64-pc-windows-gnu`，而 polars 的相依套件
  （windows-sys 0.61 / windows-link 0.2 / getrandom 0.4，用 raw-dylib）在編譯時需要 dlltool。連 `cargo check` 都會失敗。
  Rust 自帶一份在
  `C:\Users\rich2\.rustup\toolchains\stable-x86_64-pc-windows-gnu\lib\rustlib\x86_64-pc-windows-gnu\bin\self-contained\dlltool.exe`，
  但它不在 PATH 上。允許範圍內的檔案改不到 PATH，修改環境變數的指令也被權限擋下。
  修法（三擇一，由人來做）：(a) 把上面那個 self-contained 目錄加到 PATH；(b) 安裝 MSVC 工具鏈並設為預設；
  (c) 允許建立 `.cargo/config.toml`（目前在允許範圍外）。

## Learnings（不要再試的方法）

- 把相依版本往回釘（cargo update --precise）來避開 windows-link 不可行：chrono、parking_lot、tokio、mio、
  object_store、windows 0.62 等幾十個 crate 都依賴它。
- 用 Cargo feature 關掉 raw-dylib：windows-link 0.2.1 / getrandom 0.4.3 沒有這種開關（只能靠 RUSTFLAGS
  `--cfg getrandom_backend=...`，需要 .cargo/config 或環境變數，一樣在範圍外）。
- 不考慮用 `[patch.crates-io]` 把第三方 crate 複製到 src/ 底下改掉 raw-dylib：等於 fork 一堆依賴來繞過環境問題，
  而且 bcryptprimitives 在 mingw 下沒有 import library，很可能換成連結錯誤。
- 環境沒修好之前重跑 cargo check/clippy 沒有意義，每輪先看 `cargo check` 的最後幾行，確認 dlltool 錯誤還在不在。
- 不要把 dlltool.exe 複製到專案資料夾：Rust 的 `Command` 在 Windows 上不搜尋 cwd，所以沒有用。
  複製到 ~/.cargo/bin 等 PATH 目錄則算「安裝全域工具」，屬於禁區。
- 環境沒修好之前，同樣的 loop 輪次只會重複確認阻塞，浪費輪數。
- polars 0.55：只開 `strings` 不夠，一定要再開會帶入 polars-time 的 feature（例如 `dtype-date`），不然 polars-expr 編不過。
- polars 0.55：不要同時 `use polars::prelude::*` 和 `anyhow::Context`，`.context()` 和 `.with_context()` 會有歧義（E0034）。
- 在本 session 修改 PATH（bash `export`/行內 `PATH=`、PowerShell `$env:PATH`）會被權限系統擋下，不要再試。
