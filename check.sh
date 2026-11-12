#!/usr/bin/env bash
# scorecrunch 完成條件檢查。全部通過才會 exit 0。
# 每通過一關印出 PROGRESS: n/8，run_loop.sh 用它判斷有沒有進步。
# LOCKED：AI 不可修改。

cd "$(dirname "$0")" || exit 1
PY="${PYTHON:-python3}"
TIME_LIMIT="${TIME_LIMIT:-10}"
STAGE=0

pass() { STAGE=$((STAGE + 1)); echo "✅ [$STAGE/8] $1"; echo "PROGRESS: $STAGE/8"; }
fail() { echo "❌ [$((STAGE + 1))/8] $1"; echo "PROGRESS: $STAGE/8"; exit 1; }

"$PY" harness/lock.py verify || { echo "PROGRESS: 0/8"; exit 2; }

cargo fmt --check                                   || fail "cargo fmt：格式不符，請執行 cargo fmt"
pass "格式（cargo fmt）"

cargo clippy --release --all-targets -- -D warnings || fail "cargo clippy：有警告"
pass "靜態檢查（clippy，警告視為錯誤）"

cargo test --release                                || fail "cargo test：單元測試失敗"
pass "單元測試（cargo test）"

cargo build --release                               || fail "cargo build --release 失敗"
pass "編譯"

BIN="${SCORECRUNCH_BIN:-target/release/scorecrunch}"
ERR=$("$BIN" --input .loop/__no_such_file__.csv --output .loop/x.csv --group-by class --summary .loop/x.json 2>&1)
CODE=$?
[ "$CODE" -ne 0 ]                                   || fail "輸入檔不存在時應回傳非 0 結束碼"
echo "$ERR" | grep -q "panicked"                    && fail "輸入檔不存在時不可 panic，應印出友善錯誤訊息"
pass "錯誤處理（檔案不存在 → 友善錯誤、非 0 結束碼）"

"$PY" harness/e2e.py --rows 3000 --seed 7 --group-by student_id || fail "小資料比對（student_id）"
"$PY" harness/e2e.py --rows 3000 --seed 7 --group-by class      || fail "小資料比對（class）"
pass "小資料正確性（3,000 筆，兩種分組）"

"$PY" harness/e2e.py --rows 1000000 --seed 42 --group-by class  || fail "大資料比對（100 萬筆）"
pass "大資料正確性（1,000,000 筆）"

"$PY" harness/e2e.py --rows 1000000 --seed 42 --group-by student_id --time-limit "$TIME_LIMIT" \
                                                    || fail "大資料效能（需在 ${TIME_LIMIT}s 內完成）"
pass "效能（100 萬筆 < ${TIME_LIMIT}s）"

echo "🎉 ALL CHECKS PASSED"
exit 0
