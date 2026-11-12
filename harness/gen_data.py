#!/usr/bin/env python3
"""產生「故意弄髒」的測驗成績 CSV（固定 seed，結果可重現）。

LOCKED：這是驗證工具的一部分，AI 不可修改。
"""
import argparse
import csv
import random


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rows", type=int, default=1_000_000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    r = random.Random(a.seed)
    classes = [f"{c}{n}" for c in "ABCD" for n in range(1, 6)]
    types = ["grammar", "listening", "reading", "vocabulary", "writing"]
    students = [(f"S{i:05d}", r.choice(classes)) for i in range(5000)]

    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["student_id", "class", "question_type", "score", "date"])
        prev = None
        for _ in range(a.rows):
            # 約 1% 的列是上一列的完全重複
            if prev is not None and r.random() < 0.01:
                w.writerow(prev)
                continue

            sid, cls = r.choice(students)
            qt = r.choice(types)
            score = str(r.randint(0, 100))
            date = f"2026-{r.randint(1, 12):02d}-{r.randint(1, 28):02d}"

            x = r.random()
            if x < 0.01:
                score = ""  # 缺分數
            elif x < 0.02:
                score = str(r.choice([-5, 101, 150, 999]))  # 超出範圍
            elif x < 0.025:
                score = r.choice(["abc", "N/A", "--"])  # 非數字
            elif x < 0.035:
                date = date.replace("-", "/")  # 斜線日期（合法，要轉成 -）
            elif x < 0.04:
                date = "2026-13-40"  # 不存在的日期
            elif x < 0.045:
                date = "2026-02-30"  # 不存在的日期
            elif x < 0.0475:
                date = "2026/03-02"  # 分隔符號不一致
            elif x < 0.055:
                sid = f"  {sid} "  # 前後空白（要 trim）
                cls = f" {cls}"
            elif x < 0.057:
                sid = ""  # 缺學生 ID
            elif x < 0.065:
                score = f"{r.randint(0, 99)}.{r.randint(0, 9)}"  # 小數分數（合法）

            row = [sid, cls, qt, score, date]
            w.writerow(row)
            prev = row


if __name__ == "__main__":
    main()
