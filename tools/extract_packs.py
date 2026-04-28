"""
Extract all sub-textures from Project Zomboid .pack files.

Format (verified from GameWindow.java:805 + TexturePackPage.java:158):
    File = page_count(i32) | page x page_count
    page = name(string) | sub_count(i32) | has_alpha(i32)
         | sub_info x sub_count
         | atlas (raw PNG bytes)
         | 0xDEADBEEF terminator (i32)
    sub_info = name(string) | x y w h ox oy fx fy (8 x i32)
    string = length(i32) | bytes[length] (ASCII)

All ints little-endian.
"""

import io
import json
import os
import struct
import sys
from pathlib import Path

from PIL import Image

PACK_TERMINATOR = 0xDEADBEEF
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_IEND_TAIL = b"\x00\x00\x00\x00IEND\xaeB`\x82"


def read_i32(stream):
    raw = stream.read(4)
    if len(raw) < 4:
        return None
    return struct.unpack("<i", raw)[0]


def read_string(stream):
    n = read_i32(stream)
    if n is None or n < 0 or n > 4096:
        raise ValueError(f"bad string length {n}")
    return stream.read(n).decode("ascii", errors="replace")


def read_png_through_iend(stream):
    sig = stream.read(8)
    if sig != PNG_SIGNATURE:
        raise ValueError(f"expected PNG signature, got {sig.hex()}")
    out = bytearray(sig)
    while True:
        chunk = stream.read(8192)
        if not chunk:
            raise ValueError("EOF before IEND")
        out.extend(chunk)
        idx = out.rfind(PNG_IEND_TAIL)
        if idx >= 0:
            png_end = idx + len(PNG_IEND_TAIL)
            extra = bytes(out[png_end:])
            return bytes(out[:png_end]), extra


def parse_pack(pack_path):
    with open(pack_path, "rb") as f:
        data = f.read()
    stream = io.BytesIO(data)

    # Newer packs (UI2.pack, Tiles*.pack) start with magic 'PZPK' + version(i32),
    # then standard page_count + pages. New format also length-prefixes the
    # atlas PNG, vs. old format which just streams PNG bytes inline.
    head = stream.read(4)
    if head == b"PZPK":
        _version = read_i32(stream)  # always 1 in the wild
        page_count = read_i32(stream)
        new_format = True
    else:
        # Old format: first int32 IS page_count.
        stream.seek(0)
        page_count = read_i32(stream)
        new_format = False
    if page_count is None or page_count < 0 or page_count > 100000:
        raise ValueError(f"bad page_count {page_count}")

    for page_idx in range(page_count):
        page_name = read_string(stream)
        sub_count = read_i32(stream)
        _has_alpha = read_i32(stream)
        if sub_count is None or sub_count < 0 or sub_count > 1_000_000:
            raise ValueError(f"bad sub_count {sub_count} on page {page_name!r}")

        subs = []
        for _ in range(sub_count):
            name = read_string(stream)
            ints = struct.unpack("<8i", stream.read(32))
            x, y, w, h, ox, oy, fx, fy = ints
            subs.append({"name": name, "x": x, "y": y, "w": w, "h": h,
                         "ox": ox, "oy": oy, "fx": fx, "fy": fy})

        if new_format:
            png_len = read_i32(stream)
            if png_len is None or png_len <= 0 or png_len > 200_000_000:
                raise ValueError(f"bad png_len {png_len} on page {page_name!r}")
            png_data = stream.read(png_len)
            if not png_data.startswith(PNG_SIGNATURE):
                raise ValueError(f"length-prefixed atlas not PNG on {page_name!r}")
            # New format has no terminator — pages follow each other directly,
            # last page just hits EOF.
        else:
            png_data, extra = read_png_through_iend(stream)
            # Consume terminator (may already be partly in `extra`)
            term_buf = bytearray(extra)
            while len(term_buf) < 4:
                term_buf.extend(stream.read(4 - len(term_buf)))
            term = struct.unpack("<I", bytes(term_buf[:4]))[0]
            leftover = bytes(term_buf[4:])
            if term != PACK_TERMINATOR:
                scan = leftover + stream.read(64)
                idx = scan.find(struct.pack("<I", PACK_TERMINATOR))
                if idx < 0:
                    raise ValueError(
                        f"no DEADBEEF on page {page_idx} {page_name!r} (got {term:08x})"
                    )
                consumed = len(scan) - (idx + 4)
                stream.seek(-consumed, os.SEEK_CUR)
            elif leftover:
                stream.seek(-len(leftover), os.SEEK_CUR)

        atlas = Image.open(io.BytesIO(png_data))
        atlas.load()
        yield page_name, atlas, subs


def extract_pack_to_dir(pack_path, out_dir, index):
    saved = 0
    for page_name, atlas, subs in parse_pack(pack_path):
        for s in subs:
            if s["w"] <= 0 or s["h"] <= 0:
                continue
            crop = atlas.crop((s["x"], s["y"], s["x"] + s["w"], s["y"] + s["h"]))
            safe = s["name"].replace("/", "_").replace("\\", "_")
            out_path = out_dir / f"{safe}.png"
            crop.save(out_path, "PNG")
            saved += 1
            index[s["name"]] = {
                "file": out_path.name,
                "page": page_name,
                "pack": pack_path.stem,
                "ox": s["ox"], "oy": s["oy"],
                "fx": s["fx"], "fy": s["fy"],
            }
    return saved


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <pack_dir> <out_dir>")
        sys.exit(1)
    pack_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    index = {}
    total = 0
    pack_files = sorted(pack_dir.glob("*.pack"))
    print(f"Found {len(pack_files)} pack files")
    for pack in pack_files:
        try:
            n = extract_pack_to_dir(pack, out_dir, index)
            print(f"  {pack.name}: extracted {n}")
            total += n
        except Exception as e:
            print(f"  {pack.name}: FAILED -- {e!s}".encode("ascii", "replace").decode("ascii"))

    index_path = out_dir.parent / "icon_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    print(f"\nTotal extracted: {total}")
    print(f"Index: {index_path} ({len(index)} entries)")


if __name__ == "__main__":
    main()
