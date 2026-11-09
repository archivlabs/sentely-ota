#!/usr/bin/env python3
"""Builds the sentence sets the apps offer ("Get Sentence Sets").

    python3 scripts/build.py

Reads  sources/sets.json   the list: one entry per set, in the order the app shows them
       sources/<source>    each set's sentences, as text or as a .sentely file
Writes ota/sets.json and ota/<id>.sentely. Commit both halves and push: GitHub Pages
serves them, and sentely.archivseoul.com/ota/... redirects there, so the apps see the
new list the next time the screen opens. Nothing in the apps has to be released.

sources/sets.json:

    [
      {
        "id": "everyday-1",                       # file name; never reuse for another set
        "name": {"en": "Everyday 1", "ko": "일상 1"},
        "summary": {"en": "Short sentences for every day", "ko": "매일 쓰는 짧은 문장"},
        "audience": "adult",                      # adult | child | all
        "source": "everyday-1.txt"                # or a .sentely exported from the app
      }
    ]

A .txt source holds one sentence per line. A line right below a sentence that starts
with "(" and ends with ")" is its translation, "- " its source, "* " a note — the same
extras the app writes when a sentence is added by hand. Blank lines and lines starting
with "#" are ignored.

A .txt source can carry recordings: put them in sources/<id>/ named by the sentence's
place in the file, 01.mp3, 02.mp3, ... (.m4a works too). A sentence with no file has
no recording. Recordings made by a speech synthesizer must say so in the set's summary.

A .sentely source (Sets → share a set) is published as it is, recordings included.

The .sentely files are written byte for byte the same from the same input, so the
sha256 in the list changes only when a set does.
"""

import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "sources"
OUT = ROOT / "ota"
AUDIENCES = {"adult", "child", "all"}
AUDIO_TYPES = (".mp3", ".m4a")
FIXED_TIME = (2026, 1, 1, 0, 0, 0)
README = (
    "This is a Sentely sentence set.\n\n"
    "Open it with Sentely to add it as a set of your own. "
    "manifest.json lists its sentences.\n"
)


def fail(message):
    sys.exit(f"build-ota: {message}")


def sentences_from_text(path):
    sentences = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        is_extra = (line.startswith("(") and line.endswith(")")) or line.startswith("- ") or line.startswith("* ")
        if is_extra:
            if not sentences:
                fail(f"{path.name}:{number}: an extra line comes before any sentence")
            sentences[-1].append(line)
        else:
            sentences.append([line])
    return ["\n".join(lines) for lines in sentences]


def package_from_text(entry, path):
    texts = sentences_from_text(path)
    if not texts:
        fail(f"{path.name}: no sentences")

    audio_dir = SOURCE / entry["id"]
    recordings = {}
    if audio_dir.is_dir():
        for file in sorted(audio_dir.iterdir()):
            if file.suffix.lower() not in AUDIO_TYPES:
                continue
            if not file.stem.isdigit() or not 1 <= int(file.stem) <= len(texts):
                fail(f"{entry['id']}/{file.name}: name it after a sentence, 01 to {len(texts):02d}")
            if int(file.stem) in recordings:
                fail(f"{entry['id']}/{file.name}: two recordings for one sentence")
            recordings[int(file.stem)] = file

    rows = []
    for number, text in enumerate(texts, 1):
        row = {"text": text}
        if number in recordings:
            row["audio"] = [{"file": f"Audio/{number:02d}{recordings[number].suffix.lower()}", "primary": True}]
        rows.append(row)
    manifest = {
        "format": "sentely.set",
        "version": 1,
        "set": {
            "id": entry["id"],
            "name": entry["name"].get("en") or next(iter(entry["name"].values())),
            "kind": "set",
            "sentences": rows,
        },
    }
    target = OUT / f"{entry['id']}.sentely"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_STORED) as archive:
        files = [
            ("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")),
        ]
        for number in sorted(recordings):
            file = recordings[number]
            files.append((f"Audio/{number:02d}{file.suffix.lower()}", file.read_bytes()))
        files.append(("README.txt", README.encode("utf-8")))
        for name, data in files:
            info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, data)
    if recordings:
        print(f"{entry['id']}: {len(recordings)} recordings")
    return target, len(texts)


def package_from_sentely(entry, path):
    with zipfile.ZipFile(path) as archive:
        if any(info.compress_type != zipfile.ZIP_STORED for info in archive.infolist()):
            fail(f"{path.name}: compressed entries; use the file the app exported, not a re-zipped one")
        manifest = json.loads(archive.read("manifest.json"))
    if manifest.get("format") != "sentely.set":
        fail(f"{path.name}: not a Sentely set")
    count = len(manifest.get("set", {}).get("sentences", []))
    if count == 0:
        fail(f"{path.name}: no sentences")
    target = OUT / f"{entry['id']}.sentely"
    target.write_bytes(path.read_bytes())
    return target, count


def main():
    entries = json.loads((SOURCE / "sets.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    listed, seen = [], set()

    for entry in entries:
        set_id = entry.get("id", "")
        if not set_id or not all(c.isalnum() or c in "-_" for c in set_id) or set_id in seen:
            fail(f"bad or repeated id: {set_id!r}")
        seen.add(set_id)
        if entry.get("audience") not in AUDIENCES:
            fail(f"{set_id}: audience must be one of {sorted(AUDIENCES)}")
        if not entry.get("name"):
            fail(f"{set_id}: no name")

        source = SOURCE / entry["source"]
        if source.suffix == ".txt":
            target, count = package_from_text(entry, source)
        elif source.suffix == ".sentely":
            target, count = package_from_sentely(entry, source)
        else:
            fail(f"{set_id}: source must be .txt or .sentely")

        item = {
            "id": set_id,
            "name": entry["name"],
            "audience": entry["audience"],
            "sentences": count,
            "file": target.name,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        }
        if entry.get("summary"):
            item["summary"] = entry["summary"]
        listed.append(item)
        print(f"{set_id}: {count} sentences, {target.stat().st_size} bytes")

    # Files of sets taken off the list go too, so the folder is exactly the list.
    for stale in OUT.glob("*.sentely"):
        if stale.stem not in seen:
            stale.unlink()
            print(f"removed {stale.name}")

    (OUT / "sets.json").write_text(
        json.dumps({"format": 1, "sets": listed}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"ota/sets.json: {len(listed)} sets")


if __name__ == "__main__":
    main()
