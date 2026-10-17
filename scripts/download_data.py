from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import time
from urllib.parse import quote
from urllib.request import Request, urlopen


REPOSITORY = "sam-single/realwaste"
API_TREE = f"https://api.github.com/repos/{REPOSITORY}/git/trees/main?recursive=1"
RAW_ROOT = f"https://raw.githubusercontent.com/{REPOSITORY}/main"
EXPECTED_COUNTS = {
    "Cardboard": 461,
    "Food Organics": 411,
    "Glass": 420,
    "Metal": 790,
    "Miscellaneous Trash": 495,
    "Paper": 500,
    "Plastic": 921,
    "Textile Trash": 318,
    "Vegetation": 436,
}


def fetch_json(url: str) -> dict[str, object]:
    for attempt in range(5):
        try:
            request = Request(url, headers={"User-Agent": "Atigini-Tani-Academic-Project"})
            with urlopen(request, timeout=90) as response:
                return json.load(response)
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2**attempt)
    raise AssertionError("Ulaşılamaz durum")


def download_one(path: str, target_root: Path) -> str:
    relative = Path(path).relative_to("RealWaste")
    destination = target_root / relative
    if destination.exists() and destination.stat().st_size > 0:
        return "skipped"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    url = f"{RAW_ROOT}/{quote(path, safe='/')}"
    for attempt in range(5):
        try:
            request = Request(url, headers={"User-Agent": "Atigini-Tani-Academic-Project"})
            with urlopen(request, timeout=90) as response, temporary.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            if temporary.stat().st_size == 0:
                raise RuntimeError("Boş dosya indirildi")
            os.replace(temporary, destination)
            return "downloaded"
        except Exception:
            temporary.unlink(missing_ok=True)
            if attempt == 4:
                raise
            time.sleep(2**attempt)
    raise AssertionError("Ulaşılamaz durum")


def main() -> None:
    parser = argparse.ArgumentParser(description="RealWaste görüntülerini resmî yazar deposundan indirir")
    parser.add_argument("--target", type=Path, default=Path("data/raw/realwaste-main/RealWaste"))
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()

    tree = fetch_json(API_TREE)
    paths = sorted(
        item["path"]
        for item in tree["tree"]
        if item.get("type") == "blob"
        and str(item.get("path", "")).startswith("RealWaste/")
        and Path(str(item["path"])).suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    if len(paths) != sum(EXPECTED_COUNTS.values()):
        raise RuntimeError(f"Resmî ağaçta {len(paths)} görüntü bulundu; 4.752 bekleniyordu.")

    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download_one, path, args.target): path for path in paths}
        for future in as_completed(futures):
            future.result()
            completed += 1
            if completed % 100 == 0 or completed == len(paths):
                print(f"{completed}/{len(paths)} görüntü hazır", flush=True)

    actual_counts = Counter(path.parent.name for path in args.target.rglob("*") if path.is_file())
    if dict(actual_counts) != EXPECTED_COUNTS:
        raise RuntimeError(f"Sınıf sayıları uyuşmuyor: {dict(actual_counts)}")
    integrity = {
        "source": f"https://github.com/{REPOSITORY}",
        "commit_tree_sha": tree["sha"],
        "image_count": len(paths),
        "class_counts": EXPECTED_COUNTS,
        "download_method": "GitHub API tree + raw.githubusercontent.com; resumable per file",
    }
    integrity_path = args.target.parent / "source-integrity.json"
    integrity_path.write_text(json.dumps(integrity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"RealWaste hazır: {args.target}")
    print(f"Kaynak kaydı: {integrity_path}")


if __name__ == "__main__":
    main()
