# scorecrunch loop

用 AI 自動迴圈實作 Rust + Polars 資料清理工具。驗證工具已寫好並上鎖，AI 只能寫 Rust。

## 需要
- Rust（rustup）、Python 3.10+ 與 pandas（`pip install pandas`）
- Claude Code（`claude`）或 Codex CLI（`codex`）
- macOS / Linux 直接用；Windows 請在 WSL 或 Git Bash 裡跑

## 開始
```bash
cd scorecrunch-loop
git init && git add -A && git commit -m "loop harness"   # 方便事後用 git diff 看 AI 改了什麼
python3 harness/lock.py create                           # 替驗證工具上鎖（鎖檔在上一層資料夾）
AGENT=claude ./run_loop.sh                               # 或 AGENT=codex
```

## 檔案
| 檔案 | 角色 | AI 可以改？ |
|---|---|---|
| PROMPT.md | 每輪餵給 AI 的任務與規格 | ❌ |
| check.sh | 8 關完成條件 | ❌ |
| run_loop.sh | 外層迴圈（預算、停滯偵測） | ❌ |
| harness/ | 測資產生器、pandas 參考答案、比對、雜湊鎖 | ❌ |
| STATE.md | 每輪交接紀錄 | ✅ |
| src/ tests/ Cargo.toml | Rust 程式 | ✅ |
