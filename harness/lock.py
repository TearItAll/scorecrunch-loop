#!/usr/bin/env python3
"""驗證工具防竄改鎖。

  lock.py create   記錄 check.sh、run_loop.sh、harness/ 的 SHA-256
  lock.py verify   檢查它們有沒有被改過

鎖檔放在「專案資料夾外面」（../.scorecrunch-lock.json），AI 的工作範圍碰不到。
LOCKED：這是驗證工具的一部分，AI 不可修改。
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT.parent / ".scorecrunch-lock.json"


def files() -> list[Path]:
    fs = [ROOT / "check.sh", ROOT / "run_loop.sh"]
    fs += sorted((ROOT / "harness").glob("*.py"))
    return fs


def digest() -> dict[str, str]:
    return {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files()}


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "create":
        LOCK.write_text(json.dumps(digest(), indent=2), encoding="utf-8")
        print(f"已上鎖 {len(files())} 個檔案 → {LOCK}")
    elif cmd == "verify":
        if not LOCK.exists():
            print("LOCK MISSING：請先執行 python3 harness/lock.py create")
            sys.exit(1)
        want = json.loads(LOCK.read_text(encoding="utf-8"))
        got = digest()
        changed = [k for k in want if got.get(k) != want[k]] + [k for k in got if k not in want]
        if changed:
            print(f"TAMPERED：驗證工具被修改了 → {changed}")
            sys.exit(1)
        print("lock OK")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
