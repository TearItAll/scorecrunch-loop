#!/usr/bin/env python3
"""端對端驗證：跑 scorecrunch，再跟 pandas 參考答案逐列比對。

LOCKED：這是驗證工具的一部分，AI 不可修改。

用法：
  e2e.py --rows N --seed S --group-by student_id|class [--time-limit SEC]
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reference import aggregate, clean  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / ".loop" / "data"


def binary() -> str:
    override = os.environ.get("SCORECRUNCH_BIN")
    if override:
        return override
    exe = ROOT / "target" / "release" / ("scorecrunch.exe" if os.name == "nt" else "scorecrunch")
    return str(exe)


def fail(msg: str) -> None:
    print(f"E2E FAILED: {msg}")
    sys.exit(1)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rows", type=int, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--group-by", choices=["student_id", "class"], required=True)
    p.add_argument("--time-limit", type=float, default=0)
    a = p.parse_args()

    WORK.mkdir(parents=True, exist_ok=True)
    data = WORK / f"scores_{a.rows}_{a.seed}.csv"
    if not data.exists():
        subprocess.run(
            [sys.executable, str(ROOT / "harness" / "gen_data.py"),
             "--rows", str(a.rows), "--seed", str(a.seed), "--out", str(data)],
            check=True,
        )

    out_csv = WORK / f"out_{a.rows}_{a.group_by}.csv"
    out_json = WORK / f"summary_{a.rows}_{a.group_by}.json"
    for f in (out_csv, out_json):
        f.unlink(missing_ok=True)

    cmd = [binary(), "--input", str(data), "--output", str(out_csv),
           "--group-by", a.group_by, "--summary", str(out_json)]
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        fail(f"找不到執行檔 {cmd[0]}（是否已 cargo build --release？）")
    elapsed = time.perf_counter() - t0

    if proc.returncode != 0:
        fail(f"scorecrunch 結束碼 {proc.returncode}\nstderr:\n{proc.stderr[-2000:]}")
    if not out_csv.exists():
        fail("沒有產生 --output 檔案")
    if not out_json.exists():
        fail("沒有產生 --summary 檔案")

    expected_df, rows_read = clean(str(data))
    expected = aggregate(expected_df, a.group_by)

    # --- 比對 summary ---
    try:
        summary = json.loads(out_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"summary 不是合法 JSON：{e}")
    for k, v in (("rows_read", rows_read), ("rows_clean", len(expected_df))):
        if summary.get(k) != v:
            fail(f"summary.{k} = {summary.get(k)!r}，預期 {v}")

    # --- 比對報表 ---
    got = pd.read_csv(out_csv, dtype={a.group_by: str, "question_type": str})
    want_cols = [a.group_by, "question_type", "count", "avg_score"]
    if list(got.columns) != want_cols:
        fail(f"欄位應為 {want_cols}，實際 {list(got.columns)}")
    if len(got) != len(expected):
        fail(f"報表列數 {len(got)}，預期 {len(expected)}")

    keys_got = got[[a.group_by, "question_type"]].astype(str).values.tolist()
    keys_want = expected[[a.group_by, "question_type"]].astype(str).values.tolist()
    if keys_got != keys_want:
        for i, (g, w) in enumerate(zip(keys_got, keys_want)):
            if g != w:
                fail(f"第 {i} 列分組鍵或排序不符：得到 {g}，預期 {w}")

    bad_count = (got["count"].astype(int).values != expected["count"].astype(int).values)
    if bad_count.any():
        i = int(bad_count.argmax())
        fail(f"第 {i} 列 count = {got['count'][i]}，預期 {expected['count'][i]}")

    diff = (got["avg_score"].astype(float) - expected["avg_score"].astype(float)).abs()
    if (diff > 0.0051).any():
        i = int(diff.values.argmax())
        fail(f"第 {i} 列 avg_score = {got['avg_score'][i]}，預期約 {expected['avg_score'][i]:.2f}")

    print(f"E2E OK rows={a.rows} group_by={a.group_by} "
          f"groups={len(got)} clean={len(expected_df)} time={elapsed:.2f}s")

    if a.time_limit and elapsed > a.time_limit:
        fail(f"耗時 {elapsed:.2f}s，超過限制 {a.time_limit}s")


if __name__ == "__main__":
    main()
