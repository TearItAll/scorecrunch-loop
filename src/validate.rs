//! 單筆欄位驗證：分數與日期。

/// 解析分數：必須是數字且 0 <= score <= 100，否則回傳 None。
pub fn parse_score(raw: &str) -> Option<f64> {
    let s = raw.trim();
    if s.is_empty() {
        return None;
    }
    let v: f64 = s.parse().ok()?;
    if v.is_nan() || !(0.0..=100.0).contains(&v) {
        return None;
    }
    Some(v)
}

fn is_leap(y: u32) -> bool {
    (y.is_multiple_of(4) && !y.is_multiple_of(100)) || y.is_multiple_of(400)
}

fn digits(b: &[u8]) -> Option<u32> {
    let mut n = 0u32;
    for &c in b {
        if !c.is_ascii_digit() {
            return None;
        }
        n = n * 10 + u32::from(c - b'0');
    }
    Some(n)
}

/// 驗證日期：`YYYY-MM-DD` 或 `YYYY/MM/DD`（分隔符號一致、月日兩位數），
/// 且為真實存在的日期。成功時回傳 `YYYY-MM-DD`。
pub fn normalize_date(raw: &str) -> Option<String> {
    let b = raw.trim().as_bytes();
    if b.len() != 10 {
        return None;
    }
    let sep = b[4];
    if (sep != b'-' && sep != b'/') || b[7] != sep {
        return None;
    }
    let y = digits(&b[0..4])?;
    let m = digits(&b[5..7])?;
    let d = digits(&b[8..10])?;
    if y == 0 || !(1..=12).contains(&m) || d == 0 {
        return None;
    }
    let max_day = match m {
        2 if is_leap(y) => 29,
        2 => 28,
        4 | 6 | 9 | 11 => 30,
        _ => 31,
    };
    if d > max_day {
        return None;
    }
    Some(format!("{y:04}-{m:02}-{d:02}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn score_valid() {
        assert_eq!(parse_score("85"), Some(85.0));
        assert_eq!(parse_score(" 0 "), Some(0.0));
        assert_eq!(parse_score("100"), Some(100.0));
        assert_eq!(parse_score("42.5"), Some(42.5));
    }

    #[test]
    fn score_invalid() {
        for s in [
            "", "   ", "abc", "N/A", "--", "-5", "101", "100.01", "NaN", "inf",
        ] {
            assert_eq!(parse_score(s), None, "{s:?} 應該被丟棄");
        }
    }

    #[test]
    fn date_valid() {
        assert_eq!(normalize_date("2026-01-05").as_deref(), Some("2026-01-05"));
        assert_eq!(normalize_date("2026/12/31").as_deref(), Some("2026-12-31"));
        assert_eq!(normalize_date("2024-02-29").as_deref(), Some("2024-02-29"));
        assert_eq!(normalize_date("2000-02-29").as_deref(), Some("2000-02-29"));
    }

    #[test]
    fn date_invalid() {
        for s in [
            "",
            "2026-02-30",
            "2026-13-40",
            "2026/03-02",
            "2026-3-2",
            "2026-00-10",
            "2026-01-00",
            "2026-04-31",
            "1900-02-29",
            "2026.01.01",
            "abcd-ef-gh",
            "2026-01-011",
        ] {
            assert_eq!(normalize_date(s), None, "{s:?} 應該被丟棄");
        }
    }
}
