#!/usr/bin/env python3
"""Install the skill where the harness expects it.

Some skill-authoring harnesses read /app/submission/SKILL.md, others read the
uploaded output directory directly. This script is idempotent and covers both:
it copies the package into /app/submission when that path exists and does not
already hold a SKILL.md, and it never overwrites an existing file unless
--force is given.

    python install.py [--target /app/submission] [--force]
"""
import argparse
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {"install.py", "__pycache__"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="/app/submission")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    target = a.target
    if not os.path.isdir(os.path.dirname(target) or "."):
        print("parent of %s does not exist; nothing to do (skill stays in place)" % target)
        return 0
    os.makedirs(target, exist_ok=True)

    copied, skipped = [], []
    for root, dirs, names in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith("_")]
        for name in names:
            if name in SKIP:
                continue
            src = os.path.join(root, name)
            rel = os.path.relpath(src, HERE)
            dst = os.path.join(target, rel)
            if os.path.exists(dst) and not a.force:
                skipped.append(rel)
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(rel)

    print("target: %s" % target)
    print("copied: %d, skipped (already present): %d" % (len(copied), len(skipped)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
