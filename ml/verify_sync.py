import json, sys
from pathlib import Path

REPO = Path(__file__).parent.parent
v1   = json.load(open(REPO / "inference/models/v1/class_indices.json"))
root = json.load(open(REPO / "inference/models/class_indices.json"))

if v1 != root:
    print("ERROR: class_indices.json files do not match!")
    sys.exit(1)

print(f"OK: both class_indices.json files are identical ({len(v1)} classes)")
print()
for k, v in sorted(v1.items(), key=lambda x: int(x[0])):
    healthy = " [healthy]" if v["is_healthy"] else ""
    print(f"  {int(k):>2}: {v['crop']}/{v['disease']}{healthy}")
