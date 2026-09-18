#!/usr/bin/env python3
"""IBM Plex Latin1+Latin2 WOFF2 yüzlerini tek-dosya şablona gömer.

Kaynak yalnız resmî ``@ibm/plex`` npm paketidir. Normal doğrulama ağsızdır:

    python3 scripts/embed_ibm_plex_fonts.py --check

Yeniden üretim, önceden bir kez indirilmiş paketle yapılır:

    npm pack @ibm/plex@6.4.1
    python3 scripts/embed_ibm_plex_fonts.py --archive ibm-plex-6.4.1.tgz

``--fetch`` aynı paketi geçici dizine npm ile indirip üretir; bu açık seçenek
haricinde betik ağ erişimi yapmaz.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile


PACKAGE = "@ibm/plex"
VERSION = "6.4.1"
TARBALL_URL = "https://registry.npmjs.org/@ibm/plex/-/plex-6.4.1.tgz"
NPM_INTEGRITY = (
    "sha512-fnsipQywHt3zWvsnlyYKMikcVI7E2fEwpiPnIHFqlbByXVfQfANAAeJk1IV4mNnx"
    "hppUIDlhU0TzwYwL++Rn2g=="
)
SUBSETS = ("Latin1", "Latin2")
FACES = (
    ("Sans", "IBM Plex Sans", "Regular"),
    ("Sans", "IBM Plex Sans", "Medium"),
    ("Sans", "IBM Plex Sans", "SemiBold"),
    ("Sans", "IBM Plex Sans", "Bold"),
    ("Serif", "IBM Plex Serif", "Regular"),
    ("Serif", "IBM Plex Serif", "SemiBold"),
    ("Serif", "IBM Plex Serif", "Italic"),
    ("Mono", "IBM Plex Mono", "Regular"),
    ("Mono", "IBM Plex Mono", "SemiBold"),
    ("Mono", "IBM Plex Mono", "Bold"),
)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "assets" / "module-template.html"
MANIFEST_PATH = ROOT / "assets" / "fonts-manifest.json"
LICENSE_PATH = ROOT / "assets" / "ibm-plex-OFL.txt"
START_MARKER = "/* IBM_PLEX_INLINE_START */"
END_MARKER = "/* IBM_PLEX_INLINE_END */"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def member_name(family_dir: str, style_name: str, subset: str) -> str:
    return (
        f"package/IBM-Plex-{family_dir}/fonts/split/woff2/"
        f"IBMPlex{family_dir}-{style_name}-{subset}.woff2"
    )


def css_member_name(family_dir: str, style_name: str) -> str:
    return (
        f"package/IBM-Plex-{family_dir}/fonts/split/woff2/"
        f"IBMPlex{family_dir}-{style_name}.css"
    )


def read_member(archive: tarfile.TarFile, name: str) -> bytes:
    extracted = archive.extractfile(name)
    if extracted is None:
        raise RuntimeError(f"Paket üyesi okunamadı: {name}")
    return extracted.read()


def face_metadata(css: str, subset: str) -> tuple[str, int, str]:
    match = re.search(
        rf"/\*\s*Subset:\s*{re.escape(subset)}\s*\*/\s*@font-face\s*\{{(.*?)\}}",
        css,
        flags=re.I | re.S,
    )
    if not match:
        raise RuntimeError(f"{subset} @font-face metadata bloğu bulunamadı")
    block = match.group(1)
    style_match = re.search(r"font-style\s*:\s*([^;]+)", block)
    weight_match = re.search(r"font-weight\s*:\s*(\d+)", block)
    range_match = re.search(r"unicode-range\s*:\s*([^;}]+)", block)
    if not (style_match and weight_match and range_match):
        raise RuntimeError(f"{subset} @font-face metadata alanları eksik")
    return (
        style_match.group(1).strip(),
        int(weight_match.group(1)),
        range_match.group(1).strip(),
    )


def font_id(family: str, style: str, weight: int, subset: str) -> str:
    family_key = family.casefold().replace("ibm plex ", "")
    return f"{family_key}-{style}-{weight}-{subset.casefold()}"


def read_archive(archive_path: Path) -> tuple[list[dict[str, object]], dict[str, str], str]:
    entries: list[dict[str, object]] = []
    blobs: dict[str, str] = {}
    with tarfile.open(archive_path, "r:*") as archive:
        for family_dir, family, style_name in FACES:
            css = read_member(archive, css_member_name(family_dir, style_name)).decode("utf-8")
            for subset in SUBSETS:
                style, weight, unicode_range = face_metadata(css, subset)
                source_member = member_name(family_dir, style_name, subset)
                blob = read_member(archive, source_member)
                if blob[:4] != b"wOF2":
                    raise RuntimeError(f"WOFF2 magic geçersiz: {source_member}")
                ident = font_id(family, style, weight, subset)
                entries.append(
                    {
                        "id": ident,
                        "family": family,
                        "style": style,
                        "weight": weight,
                        "subset": subset,
                        "unicode_range": unicode_range,
                        "source_member": source_member,
                        "bytes": len(blob),
                        "sha256": sha256(blob),
                    }
                )
                blobs[ident] = base64.b64encode(blob).decode("ascii")
        license_text = read_member(archive, "package/LICENSE.txt").decode("utf-8")
    normalized_license = "\n".join(
        line.rstrip() for line in license_text.replace("\r\n", "\n").splitlines()
    ).rstrip() + "\n"
    return entries, blobs, normalized_license


def render_font_block(entries: list[dict[str, object]], blobs: dict[str, str]) -> str:
    lines = [
        START_MARKER,
        "/*",
        f"  Kaynak: {PACKAGE}@{VERSION} ({TARBALL_URL})",
        "  Lisans: SIL Open Font License 1.1 — tam metin: assets/ibm-plex-OFL.txt",
        "  Blob hash manifesti: assets/fonts-manifest.json",
        "  ÜRETİLMİŞ BLOK: scripts/embed_ibm_plex_fonts.py ile yenileyin; elle düzenlemeyin.",
        "*/",
    ]
    for entry in entries:
        ident = str(entry["id"])
        lines.extend(
            [
                f"/* font-id: {ident} */",
                "@font-face{",
                f"  font-family:'{entry['family']}';",
                f"  font-style:{entry['style']};",
                f"  font-weight:{entry['weight']};",
                "  font-display:swap;",
                (
                    '  src:url("data:font/woff2;base64,'
                    + blobs[ident]
                    + '") format("woff2");'
                ),
                f"  unicode-range:{entry['unicode_range']};",
                "}",
            ]
        )
    lines.append(END_MARKER)
    return "\n".join(lines)


def render_manifest(
    archive_path: Path,
    entries: list[dict[str, object]],
    license_text: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "source": {
            "package": PACKAGE,
            "version": VERSION,
            "tarball": TARBALL_URL,
            "npm_integrity": NPM_INTEGRITY,
            "archive_sha256": sha256(archive_path.read_bytes()),
            "license": "SIL Open Font License 1.1",
            "license_sha256": sha256(license_text.encode("utf-8")),
        },
        "subsets": list(SUBSETS),
        "fonts": entries,
    }


def replace_font_block(template: str, block: str) -> str:
    if START_MARKER in template or END_MARKER in template:
        if template.count(START_MARKER) != 1 or template.count(END_MARKER) != 1:
            raise RuntimeError("Şablon font işaretçileri tekil ve dengeli değil")
        start = template.index(START_MARKER)
        end = template.index(END_MARKER, start) + len(END_MARKER)
        return template[:start] + block + template[end:]
    style_start = template.find("<style>")
    if style_start < 0:
        raise RuntimeError("Şablonda <style> bulunamadı")
    insertion = style_start + len("<style>")
    return template[:insertion] + "\n" + block + template[insertion:]


def regenerate(archive_path: Path) -> None:
    entries, blobs, license_text = read_archive(archive_path)
    block = render_font_block(entries, blobs)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    TEMPLATE_PATH.write_text(replace_font_block(template, block), encoding="utf-8")
    manifest = render_manifest(archive_path, entries, license_text)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    LICENSE_PATH.write_text(license_text, encoding="utf-8")
    print(f"{len(entries)} WOFF2 blobu gömüldü; şablon {TEMPLATE_PATH.stat().st_size} bayt.")


def embedded_blobs(template: str) -> dict[str, str]:
    result: dict[str, str] = {}
    pattern = re.compile(
        r"/\*\s*font-id:\s*([a-z0-9-]+)\s*\*/\s*@font-face\s*\{(.*?)\}",
        flags=re.I | re.S,
    )
    for ident, body in pattern.findall(template):
        match = re.search(
            r'url\(["\']data:font/woff2;base64,([A-Za-z0-9+/=]+)["\']\)',
            body,
        )
        if not match:
            raise RuntimeError(f"{ident}: inline data:font/woff2 blobu yok")
        if ident in result:
            raise RuntimeError(f"Yinelenen font-id: {ident}")
        result[ident] = match.group(1)
    return result


def check_generated() -> None:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    license_text = LICENSE_PATH.read_text(encoding="utf-8")
    entries = manifest.get("fonts")
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("Font manifesti boş veya biçimsiz")
    blobs = embedded_blobs(template)
    expected_ids = {str(entry["id"]) for entry in entries}
    if set(blobs) != expected_ids:
        raise RuntimeError("Şablondaki font-id kümesi manifestle eşleşmiyor")
    for entry in entries:
        ident = str(entry["id"])
        blob = base64.b64decode(blobs[ident], validate=True)
        if blob[:4] != b"wOF2":
            raise RuntimeError(f"{ident}: WOFF2 magic geçersiz")
        if len(blob) != entry["bytes"] or sha256(blob) != entry["sha256"]:
            raise RuntimeError(f"{ident}: boyut/SHA-256 manifestten sapıyor")
    if sha256(license_text.encode("utf-8")) != manifest["source"]["license_sha256"]:
        raise RuntimeError("OFL lisans metni manifest hashinden sapıyor")
    canonical = render_font_block(entries, blobs)
    start = template.index(START_MARKER)
    end = template.index(END_MARKER, start) + len(END_MARKER)
    if template[start:end] != canonical:
        raise RuntimeError("Inline font CSS kanonik üretilmiş biçimden sapıyor")
    print(f"OK: {len(entries)} IBM Plex WOFF2 blobu ve SHA-256 manifesti eşleşiyor.")


def fetch_archive(temp_dir: Path) -> Path:
    result = subprocess.run(
        ["npm", "pack", f"{PACKAGE}@{VERSION}", "--pack-destination", str(temp_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    archives = list(temp_dir.glob("*.tgz"))
    if len(archives) != 1:
        raise RuntimeError("npm pack tek bir .tgz üretmedi")
    return archives[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="üretilmiş blob/hash/CSS paritesini denetle")
    group.add_argument("--archive", type=Path, help=f"önceden indirilmiş {PACKAGE}@{VERSION} .tgz")
    group.add_argument("--fetch", action="store_true", help="resmî npm paketini indir ve yeniden üret")
    args = parser.parse_args()

    try:
        if args.archive:
            regenerate(args.archive.resolve())
        elif args.fetch:
            with tempfile.TemporaryDirectory(prefix="edupedia-ibm-plex-") as temp_dir:
                regenerate(fetch_archive(Path(temp_dir)))
        else:
            check_generated()
    except (OSError, KeyError, ValueError, RuntimeError, tarfile.TarError) as exc:
        print(f"HATA: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
