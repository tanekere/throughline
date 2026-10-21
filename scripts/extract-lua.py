# Copy the space-lua block of Throughline.md into throughline.lua, unchanged,
# so the code can be read with syntax highlighting. Throughline.md stays the
# file SilverBullet installs; throughline.lua is only for reading.
#
#   python3 scripts/extract-lua.py           write throughline.lua
#   python3 scripts/extract-lua.py --check   fail if throughline.lua is stale
import os
import sys

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
page = open(os.path.join(root, "Throughline.md"), encoding="utf-8").read()

start = page.index("```space-lua\n") + len("```space-lua\n")
end = page.index("\n```", start)
code = page[start:end] + "\n"

target = os.path.join(root, "throughline.lua")
if "--check" in sys.argv:
    current = open(target, encoding="utf-8").read() if os.path.exists(target) else ""
    if current != code:
        print("throughline.lua does not match Throughline.md; run scripts/extract-lua.py")
        sys.exit(1)
    print("throughline.lua matches Throughline.md")
else:
    open(target, "w", encoding="utf-8").write(code)
    print("wrote throughline.lua")
