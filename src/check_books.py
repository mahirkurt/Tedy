"""Sanity-check the Tedy Books shelf after dropping in a new chapter file.

Publishing a chapter needs no code change, but a file can still land wrong: a
name that matches no manifest entry, a title preamble the reader cannot strip,
an empty body. This walks every book through the same functions the API uses,
so it cannot drift from what the dashboard actually serves.

    python src/check_books.py                     # whole shelf
    python src/check_books.py yuzuklerin-efendisi  # one book

Exits non-zero when something needs attention.
"""
import os
import sys

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from src.dashboard_api import (  # noqa: E402
    BOOKS_DIR,
    _book_load,
    _book_markdown_files,
    _book_split_front_matter,
)

OK, WARN = "  ", "! "


def check_book(slug):
    """Return (line_count, warnings) after printing this book's report."""
    book_dir, manifest, chapters = _book_load(slug)
    if not book_dir:
        print(f"{WARN}{slug}: kitap dizini okunamadı")
        return 1

    warnings = 0
    readable = [c for c in chapters if c["available"]]
    words = sum(c["words"] for c in readable)
    declared = {
        str(entry.get("id") or "")
        for entry in (manifest.get("chapters") or [])
        if isinstance(entry, dict)
    }

    print(f"\n{manifest.get('title', slug)}  ({slug})")
    print(f"  {len(readable)}/{len(chapters)} bölüm · {words} kelime")

    for i, ch in enumerate(readable):
        path = os.path.join(book_dir, ch["_file"])
        try:
            with open(path, encoding="utf-8") as f:
                raw = f.read()
        except OSError as err:
            print(f"{WARN}{ch['id']}: okunamadı ({err})")
            warnings += 1
            continue

        front, body = _book_split_front_matter(raw)
        body = body.strip()
        notes = []

        # The reader prints its own title page; a heading left at the top of the
        # body means the preamble was not recognised and will render twice.
        if declared and ch["id"] not in declared:
            notes.append("manifestte karşılığı yok — dosya adı bir bölüm id'siyle "
                         "başlamıyor, listenin sonuna eklendi")
        if body.startswith("#"):
            notes.append("gövde başlıkla başlıyor — künye ayıklanmamış")
        if not body:
            notes.append("gövde boş")
        elif not front:
            notes.append("künye bloğu tanınmadı — bölüm başlığı metinde tekrar "
                         "görünebilir, okuma ekranının en üstünü kontrol et")

        prev_id = readable[i - 1]["id"] if i else "—"
        next_id = readable[i + 1]["id"] if i + 1 < len(readable) else "—"
        mark = WARN if notes else OK
        print(f"{mark}{ch['id']:<10} {ch['label']:<12} {ch['title'][:34]:<34} "
              f"{ch['words']:>5} kel  [{prev_id}→{next_id}]  {ch['_file']}")
        for note in notes:
            print(f"      → {note}")
            warnings += 1

    matched = {c["_file"] for c in readable}
    for name in _book_markdown_files(book_dir):
        if name not in matched:
            print(f"{WARN}{name}: hiçbir bölümle eşleşmedi")
            warnings += 1

    return warnings


def main():
    if not os.path.isdir(BOOKS_DIR):
        print(f"books/ dizini yok: {BOOKS_DIR}")
        return 1

    slugs = sys.argv[1:] or sorted(
        name for name in os.listdir(BOOKS_DIR)
        if os.path.isdir(os.path.join(BOOKS_DIR, name))
    )

    warnings = sum(check_book(slug) for slug in slugs)
    print()
    if warnings:
        print(f"{warnings} uyarı — yukarıdaki '!' satırlarına bak.")
        return 1
    print("Tüm bölümler temiz.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
