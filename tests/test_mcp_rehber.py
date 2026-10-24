"""Guide sections from vendored references: mapping integrity, part size, navigation, search."""
import re

import pytest

from src.mcp_server import rehber, vendor_sync


def test_every_mapped_heading_exists_in_vendor():
    for bolum, sources in rehber.SECTIONS.items():
        for filename, numbers in sources:
            text = rehber.read_source(filename)
            present = {h for h, _ in rehber.split_sections(text)}
            for number in numbers:
                assert any(re.match(rf"##\s+{re.escape(number)}(\.|\s)", h) for h in present), (bolum, filename, number)


@pytest.mark.parametrize("bolum", sorted(rehber.SECTIONS))
def test_each_section_resolves_to_bounded_parts(bolum):
    first = rehber.guide(bolum)
    assert first["status"] == "ok"
    assert first["toplam_parca"] >= 1
    assert first["metin"].strip()
    for n in range(1, first["toplam_parca"] + 1):
        part = rehber.guide(bolum, parca=n)
        assert len(part["metin"].encode("utf-8")) <= rehber.PART_MAX_BYTES
        assert part["kaynaklar"]


def test_akis_starts_with_build_workflow_and_warns_about_plugin_paths():
    part = rehber.guide("akis")
    assert "İnşa iş akışı" in part["metin"]
    assert "edupedia_derle" in part["uyari"]


def test_part_navigation_and_out_of_range():
    first = rehber.guide("carbon")
    if first["toplam_parca"] > 1:
        assert first["sonraki_parca"] == 2
    bad = rehber.guide("carbon", parca=first["toplam_parca"] + 1)
    assert bad["status"] == "gecersiz_parca"


def test_unknown_section_lists_valid_sections():
    body = rehber.guide("yok-boyle-bolum")
    assert body["status"] == "gecersiz_bolum"
    assert body["bolumler"] == sorted(rehber.SECTIONS)


def test_split_sections_skips_table_of_contents():
    text = "# T\n\n## İçindekiler\n- a\n\n## 1. Bir\nx\n\n## 2. İki\ny\n"
    assert [h for h, _ in rehber.split_sections(text)] == ["## 1. Bir", "## 2. İki"]


def test_search_finds_mcq_segment_and_folds_turkish_case():
    hits = rehber.search("MCQ çoktan seçmeli")
    assert hits["status"] == "ok"
    assert any("mcq" in h["baslik"].lower() for h in hits["sonuclar"])
    upper = rehber.search("İNŞA İŞ AKIŞI")
    assert any("İnşa iş akışı" in h["baslik"] for h in upper["sonuclar"])


def test_search_empty_query():
    assert rehber.search("  ")["status"] == "gecersiz_sorgu"


def test_whole_file_sections_include_preamble():
    text = (vendor_sync.VENDOR_DIR / "references/audio-system.md").read_text(encoding="utf-8")
    pre = rehber.preamble(text)
    assert pre
    first_part = rehber.guide("ses")
    assert first_part["metin"].startswith(pre.splitlines()[0])
    assert "references/audio-system.md (giriş)" in first_part["kaynaklar"]


def test_search_reaches_preamble_text():
    text = (vendor_sync.VENDOR_DIR / "references/carbon-sources.md").read_text(encoding="utf-8")
    pre = rehber.preamble(text)
    line = next(l for l in pre.splitlines() if l.strip() and not l.strip().startswith("#"))
    query = " ".join(line.split()[:5])
    hits = rehber.search(query, limit=50)
    assert any(
        h["kaynak"] == "references/carbon-sources.md" and h["baslik"] == "(giriş)"
        for h in hits["sonuclar"]
    )


def test_kanun_rehberin_onunde_okunur():
    """The design law (docs/, not vendor/) leads the two sections an author reads first (2026-10-19)."""
    kanun = rehber.read_source(rehber.KANUN)
    ozet = next(f"{h}\n\n{b}\n" for h, b in rehber.split_sections(kanun) if re.match(r"##\s+1\.\s", h))
    for bolum in ("akis", "carbon"):
        first = rehber.guide(bolum)
        assert first["metin"].startswith(ozet.strip().splitlines()[0]), bolum
        assert first["kaynaklar"][0].startswith(rehber.KANUN), bolum
    # Room for the summary and SKILL §8 in the first akis part: the build workflow must stay there.
    assert len(ozet.encode("utf-8")) <= 3300
    assert "İnşa iş akışı" in rehber.guide("akis")["metin"]
    assert "kanun" in rehber.UYARI
    # The guide picks sections by number, so every top-level heading of the law carries one.
    assert all(re.match(r"##\s+\d+\.\s", h) for h, _ in rehber.split_sections(kanun))
    whole = rehber.guide("kanun")
    assert whole["status"] == "ok" and whole["metin"].startswith(rehber.preamble(kanun).splitlines()[0])


def test_ilk_parca_butcesi_kanun_bir_ve_skill_bolumu():
    """Kanun §0.4 (inceleme, Küçük 10): `akis`'in ilk parçası kanun §1 + satır sonu + `SKILL.md` §8'dir, `carbon`'unki
    §1 + satır sonu + §10; ikisi de ≤ 8000 bayt (PART_MAX_BYTES). Aşılırsa SKILL bölümü ikinci parçaya düşer ve yazar
    inşa akışını ilk okumada görmez. Toplam doğrudan ölçülür; ileti kalan payı yazar."""
    kanun = rehber.read_source(rehber.KANUN)
    bir = next(f"{h}\n\n{b}\n" for h, b in rehber.split_sections(kanun) if re.match(r"##\s+1\.\s", h))
    skill = rehber.read_source("SKILL.md")
    for bolum, no in (("akis", "8"), ("carbon", "10")):
        blok = next(f"{h}\n\n{b}\n" for h, b in rehber.split_sections(skill) if re.match(rf"##\s+{no}\.\s", h))
        toplam = len(bir.encode("utf-8")) + 1 + len(blok.encode("utf-8"))
        kalan = rehber.PART_MAX_BYTES - toplam
        assert kalan >= 0, (f"{bolum}: kanun §1 + 1 + SKILL §{no} = {toplam} bayt, sınır {rehber.PART_MAX_BYTES}; "
                            f"{-kalan} bayt fazla")
        # Formül gerçek parçanın kendisidir: ilk parça tam olarak bu iki bloktur.
        ilk = rehber.guide(bolum)["metin"]
        assert len(ilk.encode("utf-8")) == toplam, (f"{bolum}: ilk parça {len(ilk.encode('utf-8'))} bayt, formül {toplam}; "
                                                  f"kalan pay {kalan} bayt")


def test_kanun_vendor_icine_kopyalanmaz():
    """One source: the law lives in docs/ and is served from there, never duplicated into vendor/."""
    assert not list(vendor_sync.VENDOR_DIR.rglob("*kanun*"))
    assert rehber.KANUN_YOLU.is_file()


def test_kb35_vendor_bolumleri_kanunla_celismez():
    """KB-35 closed (2026-10-19): the vendored sections an author reads no longer carry what the law overrode."""
    kanun = rehber.read_source(rehber.KANUN)
    ozet = next(f"{h}\n\n{b}\n" for h, b in rehber.split_sections(kanun) if re.match(r"##\s+1\.\s", h)).strip()
    yasak = [
        r"fetch_figure\.py", r"(?<![\w-])ic-(idea|flip|trophy|star)\b", r"pic-trophy",
        r"meta\.accent`?'i derse göre", r'accent: "teal"', r"rozet kasası", r"XP/rozet ekonomisi",
        r"g10 ↔ g100", r"öğrencinin kendi seçimi önceliklidir", r"tema \+ Leitner", r"rozet kalırsa",
        r"orkestre", r"donutSvg", r"sıcak altın", r"otomatik `var\(--accent\)`", r'fill="#[0-9a-fA-F]',
        r"SVG \*\*yedektir\*\*", r"avatarOptions", r"Meydan Oku", r"meydan okuma", r"Yarışma varyantı",
    ]
    for bolum in ("akis", "carbon", "segmentler", "pedagoji", "etkilesim", "svg"):
        toplam = rehber.guide(bolum)["toplam_parca"]
        metin = "\n".join(rehber.guide(bolum, parca=n)["metin"] for n in range(1, toplam + 1))
        metin = metin.replace(ozet, "")  # the law's own §1 names the keys it forbids
        kalan = [d for d in yasak if re.search(d, metin)]
        assert not kalan, (bolum, kalan)
        # "tema düğmesi" may appear only where the text says it is gone or a debt (izinli bağlam).
        dugme = [s for s in metin.splitlines() if "tema düğmesi" in s and not re.search(r"yok|kalk|borç", s)]
        assert not dugme, (bolum, dugme)


def test_rehber_ve_arac_yazara_gorsel_alanlarini_ve_odul_kuralini_soyler(tmp_path):
    """KB-10–KB-12, KB-21 (2026-10-23): yazar yeni alanları rehberin ilk okuduğu bölümde ve edupedia_derle'nin
    açıklamasında bulur; rewards'ın isteğe bağlı olduğu ve badges'in yazılmadığı ikisinde de yazar."""
    import anyio

    from src.mcp_server import server, tools
    from src.mcp_server.config import load_settings

    toplam = rehber.guide("akis")["toplam_parca"]
    akis = "\n".join(rehber.guide("akis", parca=n)["metin"] for n in range(1, toplam + 1))
    for alan in ("`alt`", "`baslik`", "alt_gerekce", "kitap_altyazisi"):
        assert alan in akis, alan
    # Son inceleme (Kritik 1): dayanak kitabın metnidir; rehber yazarı VLM betimine yönlendirmez.
    assert "aciklama" not in akis
    assert "`rewards` isteğe bağlı" in akis

    class _Fed:
        def configured(self, name):
            return False

    mcp = server.build_server(tools.Tools(load_settings({}, project_root=tmp_path), _Fed()))
    listed = {t.name: t for t in anyio.run(mcp.list_tools)}
    derle = listed["edupedia_derle"].description
    for parca in ("alt", "baslik", "alt_gerekce", "alt_metin_dayanaksiz", "rewards isteğe bağlı", "badges",
                  "kitap_altyazisi"):
        assert parca in derle, parca
    gorsel = listed["edupedia_gorsel"].description
    assert "kitap_altyazisi" in gorsel and "etiket" in gorsel and "betim" in gorsel and "aciklama" not in gorsel
