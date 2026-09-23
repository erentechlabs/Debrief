"""Keep the renderer skill in sync with renderer/executive_brief.py.

Copilot Studio runs whatever the success-report-fixed-renderer skill contains, so the
skill embeds the renderer source in a fenced python block together with its SHA-256.
Edit renderer/executive_brief.py, then re-embed it here before pasting the skill.

    python agent/build_skills.py            # check only; exit code 1 when out of sync
    python agent/build_skills.py --write    # re-embed the current renderer and hash
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RENDERER = ROOT / "renderer" / "executive_brief.py"
SKILL = ROOT / "agent" / "skills" / "success-report-fixed-renderer.md"

BLOCK = re.compile(r"```python\n(.*?)```", re.S)
SHA_LINE = re.compile(r"(Normalized UTF-8/LF Python source SHA256: )([0-9a-f]{64})")
IMPL_LINE = re.compile(r"(Implementation: executive_brief\.py version )([0-9.]+)(;)")
DESC_VERSION = re.compile(r"(Required fixed PDF renderer for Success Program executive briefs\. Version )([0-9.]+)(,)")


def normalized(text):
    return text.replace("\r\n", "\n").rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help="re-embed the renderer source and hash into the skill")
    args = parser.parse_args()

    source = normalized(RENDERER.read_text(encoding="utf-8"))
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    version = re.search(r'^VERSION = "([^"]+)"', source, re.M).group(1)

    skill = SKILL.read_text(encoding="utf-8")
    block, sha = BLOCK.search(skill), SHA_LINE.search(skill)
    if not block or not sha:
        print("Skill layout not recognised: expected one fenced python block and a SHA256 line.")
        return 2

    if args.write:
        updated = skill[:block.start(1)] + source + skill[block.end(1):]
        updated = SHA_LINE.sub(lambda m: m.group(1) + digest, updated)
        updated = IMPL_LINE.sub(lambda m: m.group(1) + version + m.group(3), updated)
        updated = DESC_VERSION.sub(lambda m: m.group(1) + version + m.group(3), updated)
        SKILL.write_text(updated, encoding="utf-8")
        print(f"Embedded renderer {version} ({digest[:16]}...) into {SKILL.relative_to(ROOT)}")
        return 0

    embedded_ok = normalized(block.group(1)) == source
    hash_ok = sha.group(2) == digest
    print(f"renderer {version}  sha256 {digest[:16]}...  "
          f"embedded source: {'match' if embedded_ok else 'DIFFERENT'}  "
          f"stated hash: {'match' if hash_ok else 'DIFFERENT'}")
    if not (embedded_ok and hash_ok):
        print("Run: python agent/build_skills.py --write")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
