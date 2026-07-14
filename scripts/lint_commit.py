#!/usr/bin/env python3
import re
import sys


def validate_commit_msg(msg: str) -> bool:
    msg = msg.strip()
    if not msg:
        return False
    if re.match(r"^release: v\d+\.\d+\.\d+", msg):
        return True
    pattern = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?: .+"
    return bool(re.match(pattern, msg))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        content = f.read()
    if content.startswith("Merge branch") or content.startswith("Merge "):
        sys.exit(0)
    if not validate_commit_msg(content):
        print(f"ERROR: Invalid commit message: '{content.strip()}'")
        sys.exit(1)
