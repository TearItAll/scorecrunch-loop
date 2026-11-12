# scorecrunch-loop

這個 repo 有兩個部分：

1. **scorecrunch**：用 Rust + [Polars](https://pola.rs/) 寫的命令列工具。它會清理「很髒」的測驗成績 CSV，再依學生或班級算出各題型的筆數和平均分。100 萬筆資料約 0.6 秒處理完。
2. **AI 自我驗證迴圈（loop harness）**：一套讓 AI 自己寫程式、自己檢查、自己修，直到真的完成為止的工作流程。檢查工具已經上鎖，AI 改不到，也就沒辦法作弊過關。

scorecrunch 的程式碼（`src/`、`Cargo.toml`）完全是 AI 在這個迴圈裡寫出來的。人只負責寫規格、寫檢查工具，以及處理環境問題。

---

## 目錄

- [scorecrunch 能做什麼](#scorecrunch-能做什麼)
- [快速開始：只想用 scorecrunch](#快速開始只想用-scorecrunch)
- [使用說明](#使用說明)
- [清理規則](#清理規則)
- [AI 自我驗證迴圈](#ai-自我驗證迴圈)
- [自己跑一次迴圈](#自己跑一次迴圈)
- [8 關檢查](#8-關檢查)
- [檔案說明](#檔案說明)
- [環境安裝與常見問題](#環境安裝與常見問題)
- [這個 repo 是怎麼做出來的](#這個-repo-是怎麼做出來的)
- [限制](#限制)

---

## scorecrunch 能做什麼

輸入一份成績 CSV，欄位是 `student_id,class,question_type,score,date`。真實資料常常長這樣：

```csv
student_id,class,question_type,score,date
S00601,C2,reading,9,2026-03-18
S03210,D1,listening,,2026-10-18          ← 缺分數
S00769,B1,listening,abc,2026-05-08       ← 分數不是數字
S02985,B5,listening,49,2026-02-30        ← 2 月 30 日不存在
S02572,C3,writing,25,2026/02/13          ← 斜線日期
  S03621 , D4,writing,88,2026-01-08      ← 多餘空白
```

scorecrunch 會把這些清乾淨，輸出兩個檔案。

**統計報表 CSV**（以 `--group-by class` 為例）：

```csv
class,question_type,count,avg_score
A1,grammar,7925,49.76
A1,listening,7993,50.37
A1,reading,7993,50.12
...
```

**摘要 JSON**：

```json
{
  "rows_clean": 950138,
  "rows_read": 1000000
}
```

用 100 萬筆測試資料（seed 42）實測的結果：

| 分組方式 | 輸出組數 | 清理後筆數 | 耗時（release 版） |
|---|---|---|---|
| `--group-by class` | 100（20 班 × 5 題型） | 950,138 | 約 0.6 秒 |
| `--group-by student_id` | 25,000（5,000 人 × 5 題型） | 950,138 | 約 0.6 秒 |

適合的用途：補習班或學校整理大量測驗紀錄、清理研究用的問卷或實驗資料，或任何「髒資料進來、乾淨報表出去」的批次工作。

---

## 快速開始：只想用 scorecrunch

只想用這個工具、不跑 AI 迴圈的話，只需要 Rust。

```bash
git clone https://github.com/TearItAll/scorecrunch-loop.git
cd scorecrunch-loop
cargo build --release
```

第一次編譯 Polars 會比較久，大約 5 到 15 分鐘。之後再編譯就快了。

編好的執行檔在 `target/release/scorecrunch`，Windows 上是 `scorecrunch.exe`：

```bash
./target/release/scorecrunch \
  --input 成績.csv \
  --output report.csv \
  --group-by class \
  --summary summary.json
```

手邊沒有資料的話，可以用內建的產生器做一份測試資料。這一步需要 Python 3.10 以上：

```bash
python3 harness/gen_data.py --rows 3000 --seed 7 --out sample.csv
./target/release/scorecrunch --input sample.csv --output report.csv --group-by class --summary summary.json
```

---

## 使用說明

```
scorecrunch --input <CSV> --output <CSV> --group-by <student_id|class> --summary <JSON>
```

| 參數 | 說明 |
|---|---|
| `--input` | 輸入的成績 CSV，必須有表頭、UTF-8 編碼，且包含五個欄位 |
| `--output` | 輸出的統計報表 CSV |
| `--group-by` | 分組欄位：`class`（每班各題型）或 `student_id`（每位學生各題型） |
| `--summary` | 輸出的摘要 JSON |

四個參數都必填。`scorecrunch --help` 可以看完整說明。

### 輸出格式

**報表 CSV**
- 欄位依序是 `<分組欄位>,question_type,count,avg_score`。
- `count`：該組清理後的筆數。
- `avg_score`：該組平均分，取到小數第 2 位。
- 依前兩欄做字串遞增排序。

**摘要 JSON**
- `rows_read`：原始資料列數，不含表頭。
- `rows_clean`：清理並去重後剩下的列數。

### 錯誤處理

發生錯誤時，程式會印出中文錯誤訊息到 stderr，並以結束碼 `1` 結束，不會當掉（panic）：

```
$ ./target/release/scorecrunch --input nope.csv --output x.csv --group-by class --summary x.json
錯誤：找不到輸入檔：nope.csv
```

會處理的錯誤有：找不到輸入檔、CSV 缺少欄位、讀檔失敗、寫檔失敗。

---

## 清理規則

依下面的順序套用。任何一條不合格，該列就會被丟掉。

| # | 規則 | 範例 |
|---|---|---|
| 1 | 所有欄位去掉前後空白 | `"  S03621 "` → `S03621` |
| 2 | `student_id` 為空 → 丟棄 | `""` |
| 3 | `score` 轉不成數字 → 丟棄 | 空白、`abc`、`N/A`、`--` |
| 4 | `score` 不在 0–100 之間 → 丟棄 | `-5`、`101`、`999` |
| 5 | `date` 必須是 `YYYY-MM-DD` 或 `YYYY/MM/DD`，兩個分隔符號要相同、月日都是兩位數，而且要是真實存在的日期（閏年也會判斷）。通過的一律改成 `YYYY-MM-DD` | `2026/02/13` → `2026-02-13`；`2026-02-30`、`2026-13-40`、`2026/03-02` 丟棄 |
| 6 | 清理後五個欄位完全相同的列只保留一筆 | 重複列 |

100 萬筆測試資料中，各原因丟掉的筆數如下。一列只算在它第一個不合格的規則上：

| 原因 | 筆數 |
|---|---|
| 分數不是數字或空白 | 15,119 |
| 日期格式錯或不存在 | 12,439 |
| 重複的列 | 10,184 |
| 分數超出 0–100 | 10,081 |
| 缺學生 ID | 2,039 |
| **合計** | **49,862**（5.0%） |

---

## AI 自我驗證迴圈

### 要解決的問題

叫 AI 寫程式時，常見的問題有三個：

1. **AI 說「好了」，其實沒好。** 它可能沒實際跑過，或只測了簡單的情況。
2. **AI 為了過關而作弊。** 例如改掉測試、寫死答案，或把警告關掉。
3. **大任務一次做不完。** 對話太長會失焦，或做到一半就停了。

### 運作方式

```
┌──────────────── run_loop.sh（外層迴圈）────────────────┐
│  1. 跑 ./check.sh → 得到 PROGRESS n/8                   │
│  2. 8/8 了嗎？是 → 結束 ✅                               │
│  3. 否 → 叫起一個「全新」的 AI，給它任務與上次的錯誤      │
│  4. AI 修一件事、自己跑 check.sh、把交接寫進 STATE.md    │
│  5. 回到 1（最多 MAX 輪；連續 2 輪沒進步就停下來找人）    │
└────────────────────────────────────────────────────────┘
```

### 每個設計對應的問題

| 設計 | 解決什麼 |
|---|---|
| `check.sh` 的 8 關是唯一的完成標準 | AI 說好了不算數，由程式檢查來判定 |
| 用 pandas 寫參考答案，逐列比對 | 不只檢查「能跑」，還檢查「答案對不對」 |
| 雜湊鎖（`harness/lock.py`），鎖檔放在專案資料夾外面 | AI 一改檢查工具，`check.sh` 就以結束碼 2 失敗，迴圈立刻停止 |
| `PROMPT.md` 的禁區：不准特判測試資料、不准用 `#[allow]` 關警告、不准 commit | 防止投機取巧 |
| 每輪都是全新的 AI，靠 `STATE.md` 交接 | 不會因對話太長而失焦，進度和失敗經驗都有紀錄 |
| 停滯偵測：連續 2 輪 PROGRESS 沒增加就停 | 不會在死胡同裡一直燒用量 |
| 限制 AI 可用的工具（`claude --allowedTools`） | AI 只能讀寫檔案和跑 `cargo`、`python3` 等指令，不能亂動電腦 |

---

## 自己跑一次迴圈

如果想重現「AI 從零寫出 scorecrunch」的過程，可以把 AI 寫的程式刪掉，從頭跑一次。

### 需要

- Rust（[rustup](https://rustup.rs/)）
- Python 3.10 以上，加上 pandas（`pip install pandas`）
- 以下其中一個 AI CLI：[Claude Code](https://claude.com/claude-code)（`claude`）或 Codex CLI（`codex`）
- bash：macOS 和 Linux 直接用；Windows 請用 Git Bash 或 WSL

### 步驟

```bash
git clone https://github.com/TearItAll/scorecrunch-loop.git
cd scorecrunch-loop

# （選用）刪掉 AI 寫好的程式，從零開始
git rm -r --quiet src Cargo.toml Cargo.lock
git commit -m "start from scratch"
# 記得把 STATE.md 改回初始狀態（可參考第一個 commit：git show a1664b3:STATE.md）

# 替驗證工具上鎖，鎖檔會寫到上一層資料夾的 .scorecrunch-lock.json
python3 harness/lock.py create

# 開始迴圈
AGENT=claude ./run_loop.sh        # 用 Claude Code
AGENT=codex  ./run_loop.sh        # 或用 Codex CLI
MAX=12 AGENT=claude ./run_loop.sh # 調整最大輪數（預設 8）
```

### 結束碼

| 結束碼 | 意思 |
|---|---|
| `0` | 8/8 全部通過 🎉 |
| `1` | 輪數用完，還沒全過，看 `STATE.md` 了解進度 |
| `2` | 驗證工具被修改，或鎖檔遺失，請檢查 `git diff` |
| `3` | 連續 2 輪沒有進步，需要人來看。通常是環境問題 |

### 跑完之後

```bash
git diff                 # 看 AI 改了什麼
cat STATE.md             # 看每一輪的交接紀錄與 Learnings
cat .loop/last_check.log # 看最後一次 check.sh 的完整輸出
```

> ⚠️ 每一輪都是一次完整的 AI 工作，會用掉你的 Claude 或 Codex 額度。預設最多 8 輪，每輪最多 40 turns。

---

## 8 關檢查

不跑迴圈也可以單獨執行：

```bash
./check.sh
```

| 關卡 | 內容 |
|---|---|
| 0 | `lock.py verify`：驗證工具沒被改過（失敗時結束碼 2） |
| 1 | `cargo fmt --check`：格式 |
| 2 | `cargo clippy --release --all-targets -- -D warnings`：靜態檢查，警告視為錯誤 |
| 3 | `cargo test --release`：單元測試（日期驗證、分數驗證） |
| 4 | `cargo build --release`：編譯 |
| 5 | 輸入檔不存在時，必須回傳非 0 結束碼，而且不可 panic |
| 6 | 3,000 筆資料，用兩種分組方式跟 pandas 參考答案逐列比對 |
| 7 | 1,000,000 筆資料的正確性 |
| 8 | 1,000,000 筆資料必須在 10 秒內跑完（可用 `TIME_LIMIT` 環境變數調整） |

每通過一關會印出 `PROGRESS: n/8`。全部通過時印出 `🎉 ALL CHECKS PASSED`，並以結束碼 0 結束。

測試資料由 `harness/gen_data.py` 用固定 seed 產生，第一次執行時會建立在 `.loop/data/`，100 萬筆的檔案大約 30 MB。

可以用環境變數調整的設定：

| 變數 | 預設 | 說明 |
|---|---|---|
| `PYTHON` | `python3` | 用哪個 Python 跑 harness |
| `TIME_LIMIT` | `10` | 效能關卡的秒數上限 |
| `SCORECRUNCH_BIN` | `target/release/scorecrunch` | 要測試的執行檔路徑 |

---

## 檔案說明

| 檔案 | 角色 | AI 可以改？ | 有上鎖？ |
|---|---|---|---|
| `PROMPT.md` | 每輪交給 AI 的任務、規格、允許範圍與禁區 | ❌ | 規則禁止 |
| `check.sh` | 8 關完成條件 | ❌ | 🔒 |
| `run_loop.sh` | 外層迴圈：輪數預算、停滯偵測、呼叫 AI | ❌ | 🔒 |
| `harness/gen_data.py` | 產生故意弄髒的測試資料（固定 seed） | ❌ | 🔒 |
| `harness/reference.py` | 用 pandas 寫的參考答案 | ❌ | 🔒 |
| `harness/e2e.py` | 執行 scorecrunch，並跟參考答案逐列比對 | ❌ | 🔒 |
| `harness/lock.py` | SHA-256 雜湊鎖（`create` / `verify`） | ❌ | 🔒 |
| `STATE.md` | 每輪的交接紀錄：Log、Open issues、Learnings | ✅ | |
| `src/main.rs` | 命令列解析、讀檔、清理、分組、輸出 | ✅ | |
| `src/validate.rs` | 分數與日期驗證，以及單元測試 | ✅ | |
| `Cargo.toml` / `Cargo.lock` | Rust 相依套件 | ✅ | |

### scorecrunch 用到的套件

| 套件 | 用途 |
|---|---|
| `polars` 0.55（`lazy`、`csv`、`strings`、`round_series`、`fmt`、`dtype-date`） | 讀 CSV、清理、分組、寫 CSV |
| `clap` 4（derive） | 命令列參數 |
| `anyhow` | 錯誤處理，搭配友善的錯誤訊息 |
| `serde_json` | 輸出摘要 JSON |

---

## 環境安裝與常見問題

### Windows：請用 MSVC 工具鏈

Polars 的部分相依套件（`windows-sys`、`getrandom`）在 Windows GNU 工具鏈（`x86_64-pc-windows-gnu`）上編譯時需要完整的 `dlltool`，rustup 附的版本不夠用，會出現：

```
error: error calling dlltool 'dlltool.exe': program not found
```

解法是改用 MSVC 工具鏈：

```bash
# 1. 安裝 Visual Studio Build Tools（C++ 工作負載）
winget install --id Microsoft.VisualStudio.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"

# 2. 安裝並切換 Rust 工具鏈
rustup toolchain install stable-x86_64-pc-windows-msvc
rustup default stable-x86_64-pc-windows-msvc
```

### Windows：換行字元（CRLF）會讓鎖失效

如果 git 設定了 `core.autocrlf=true`，checkout 時可能把 `.sh` 和 `.py` 轉成 CRLF。這會有兩個後果：

- 檔案雜湊改變，`lock.py verify` 判定為被竄改。
- bash 無法執行 CRLF 的 `.sh` 檔。

解法：clone 前先關掉自動轉換。如果已經 clone 了，可以重新 checkout 後再上鎖。

```bash
git config --global core.autocrlf input
```

### `python3` 找不到，或找不到 pandas

`check.sh` 預設呼叫 `python3`。如果你的 Python 指令叫 `python`，或 pandas 裝在另一個 Python 上，可以這樣指定：

```bash
PYTHON=python ./check.sh
```

### Polars 編譯錯誤 `cannot find module or crate polars_time`

Polars 0.55 開了 `strings` feature 時，一定要有某個會帶入 `polars-time` 的 feature，否則 `polars-expr` 會編譯失敗。本專案用 `dtype-date` 解決。

---

## 這個 repo 是怎麼做出來的

完整紀錄在 [`STATE.md`](STATE.md)，摘要如下：

| 輪次 | 開始時 | 發生了什麼 | 結束時 |
|---|---|---|---|
| 1 | 0/8 | AI 建立 `Cargo.toml`、`src/main.rs`、`src/validate.rs` 和單元測試 | 1/8 |
| 2–3 | 1/8 | 編譯卡在 Windows GNU 工具鏈缺 `dlltool`。AI 判斷這是**環境問題**，沒有亂改程式，只在 `STATE.md` 記下需要人處理 | 1/8 |
| — | — | 停滯偵測生效，迴圈停下來。人安裝 VS Build Tools、改用 MSVC 工具鏈 | — |
| 4 | 1/8 | AI 找出 Polars feature 組合問題（補 `dtype-date`），並修正幾個 API 寫法 | **8/8** 🎉 |

這次實際只花 4 輪 AI。人只介入一次，而且是在 AI 本來就碰不到的環境設定上。

---

## 限制

- **檢查寫得好，結果才可靠。** 如果 `check.sh` 漏測某種髒資料，AI 寫錯了也照樣能過關。這套方法最需要人花心思的地方，是設計完成條件。
- **環境問題還是需要人處理。** 安裝軟體、改系統設定這類事，AI 被刻意限制做不到。
- **適合「對錯能自動判斷」的任務。** 有參考答案可以比對的資料處理很合適；「好不好看」這類主觀的事就不適用。
- **平均分的進位方式。** `avg_score` 用的是 Polars 的 half-to-even 進位（例如 `x.xx5` 可能進位也可能捨去），跟傳統的四捨五入在極少數情況下會差 0.01。比對容許誤差是 0.0051，所以不影響檢查結果。
- **測試資料是隨機產生的。** 分數是 0 到 100 隨機均勻分布，所以各班、各學生的平均都接近 50。換成真實資料才看得出差異。
