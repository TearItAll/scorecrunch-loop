#!/usr/bin/env bash
# 外層迴圈：檢查 → 交給 AI 修 → 再檢查，直到通過、預算用完或卡住。
#
# 用法：
#   AGENT=claude ./run_loop.sh      # 用 Claude Code（預設）
#   AGENT=codex  ./run_loop.sh      # 用 Codex CLI
#   MAX=12 ./run_loop.sh            # 調整最大輪數
#
# LOCKED：AI 不可修改。

cd "$(dirname "$0")" || exit 1
MAX="${MAX:-8}"
AGENT="${AGENT:-claude}"
PATIENCE=2          # 連續幾輪 PROGRESS 沒增加就停
mkdir -p .loop

progress() { grep -o 'PROGRESS: [0-9]*' .loop/last_check.log | tail -1 | grep -o '[0-9]*$' || echo 0; }

best=-1
stall=0
for i in $(seq 1 "$MAX"); do
  ./check.sh > .loop/last_check.log 2>&1
  code=$?
  p=$(progress)

  if [ "$code" -eq 0 ]; then
    echo "✅ 第 $i 輪開始前檢查已全部通過（8/8）"
    exit 0
  fi
  if [ "$code" -eq 2 ]; then
    echo "🛑 驗證工具被修改或鎖檔遺失，停止。請檢查 git diff。"
    tail -n 5 .loop/last_check.log
    exit 2
  fi

  if [ "$p" -gt "$best" ]; then best=$p; stall=0; else stall=$((stall + 1)); fi
  echo "🔁 第 $i/$MAX 輪：PROGRESS $p/8（最佳 $best/8，停滯 $stall 輪）"
  if [ "$stall" -ge "$PATIENCE" ]; then
    echo "🧱 連續 $PATIENCE 輪沒有進步，停下來讓人看看。最後的錯誤："
    tail -n 30 .loop/last_check.log
    exit 3
  fi

  PROMPT="$(cat PROMPT.md)

## 本輪資訊
現在是第 $i / $MAX 輪。上一次 ./check.sh 的完整輸出在 .loop/last_check.log，目前 PROGRESS $p/8。
請先讀 STATE.md，然後開始。結束前務必更新 STATE.md。"

  case "$AGENT" in
    claude)
      claude -p "$PROMPT" \
        --allowedTools "Read,Edit,Write,Glob,Grep,Bash(cargo:*),Bash(./check.sh),Bash(python3:*),Bash(ls:*),Bash(cat:*)" \
        --max-turns 40
      ;;
    codex)
      codex exec --full-auto "$PROMPT"
      ;;
    *)
      echo "未知的 AGENT：$AGENT（可用 claude 或 codex）"; exit 1 ;;
  esac
done

./check.sh > .loop/last_check.log 2>&1 && { echo "✅ 最後一輪後全部通過"; exit 0; }
echo "⏹️ 預算用完（$MAX 輪），PROGRESS $(progress)/8。看 STATE.md 了解進度。"
exit 1
