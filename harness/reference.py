#!/usr/bin/env python3
"""pandas 參考實作：用來算出「標準答案」。

LOCKED：這是驗證工具的一部分，AI 不可修改。
清理規則與 PROMPT.md 的規格完全一致。
"""
import pandas as pd

DATE_RE = r"^(\d{4})([-/])(\d{2})\2(\d{2})$"


def clean(path: str) -> tuple[pd.DataFrame, int]:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    rows_read = len(df)

    for c in df.columns:
        df[c] = df[c].str.strip()

    # 規則 1：student_id 不可為空
    df = df[df["student_id"] != ""]

    # 規則 2、3：分數必須是數字，且 0 <= score <= 100
    score = pd.to_numeric(df["score"], errors="coerce")
    df = df.assign(score=score)
    df = df[df["score"].notna() & (df["score"] >= 0) & (df["score"] <= 100)]

    # 規則 4：日期格式 YYYY-MM-DD 或 YYYY/MM/DD（分隔符號一致），且為真實存在的日期
    parts = df["date"].str.extract(DATE_RE)
    norm = parts[0] + "-" + parts[2] + "-" + parts[3]
    valid = pd.to_datetime(norm, format="%Y-%m-%d", errors="coerce").notna()
    df = df.assign(date=norm)[valid]

    # 規則 5：清理後完全相同的列只保留一筆
    df = df.drop_duplicates(subset=["student_id", "class", "question_type", "score", "date"])
    return df, rows_read


def aggregate(df: pd.DataFrame, key: str) -> pd.DataFrame:
    out = (
        df.groupby([key, "question_type"], sort=False)["score"]
        .agg(count="count", avg_score="mean")
        .reset_index()
        .sort_values([key, "question_type"], kind="stable")
        .reset_index(drop=True)
    )
    return out
