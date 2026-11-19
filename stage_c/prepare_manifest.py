"""Download only pinned public task-list metadata. Never execute a challenge."""

import hashlib
import json
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent


def parse_tasks(readme):
    tasks = []
    for line in readme.splitlines():
        cells = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] not in {"cry", "for", "pwn", "rev", "web", "msc"}:
            continue
        category, event, name, difficulty = cells
        tasks.append({"id": f"{event}-{category}-{name}", "category": category,
                      "event": event, "name": name, "published_difficulty": difficulty})
    if len({task["id"] for task in tasks}) != len(tasks):
        raise ValueError("Duplicate benchmark task identifiers")
    return tasks


def build_manifest(config, source):
    digest = hashlib.sha256(source).hexdigest()
    if digest != config["benchmark_readme_sha256"]:
        raise ValueError("Pinned task-list hash does not match")
    all_tasks = parse_tasks(source.decode("utf-8"))
    if len(all_tasks) != 50:
        raise ValueError("Expected the published 50-task CTFTiny list")
    selected = sorted((task for task in all_tasks if task["category"] in config["categories"]),
                      key=lambda task: task["id"])
    if len(selected) != config["test_tasks"]:
        raise ValueError("Selected task count differs from the proposal")
    return {
        "status": "metadata-only proposal; no solutions or outcomes inspected",
        "source_url": f"https://github.com/{config['benchmark_repository']}/blob/"
                      f"{config['benchmark_revision']}/README.md",
        "source_sha256": digest,
        "selection": "Every web and pwn task in the pinned published list; no difficulty exclusion",
        "full_benchmark_tasks": len(all_tasks),
        "selected_tasks": len(selected),
        "category_counts": dict(Counter(task["category"] for task in selected)),
        "difficulty_counts": dict(Counter(task["published_difficulty"] for task in selected)),
        "tasks": selected,
    }


def main():
    config = json.loads((ROOT / "study_config.json").read_text())
    url = (f"https://raw.githubusercontent.com/{config['benchmark_repository']}/"
           f"{config['benchmark_revision']}/README.md")
    with urlopen(Request(url, headers={"User-Agent": "capstone-metadata-preflight"}), timeout=30) as response:
        source = response.read()
    manifest = build_manifest(config, source)
    (ROOT / "challenge_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({key: manifest[key] for key in
                      ("selected_tasks", "category_counts", "difficulty_counts")}, indent=2))


if __name__ == "__main__":
    main()
