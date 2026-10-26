"""docs/sinav-kilavuzu-kanunu.md'deki kapı adları gerçek testlere bağlı kalır (son inceleme, madde 10).

Kanun'un 'Kapı' sütunu testleri adıyla anar: pytest `dosya::ad` (ve aynı hücrede virgülle sıralanan yalın `test_ad`'lar),
e2e/birim dosyasının ardından tırnak içinde test başlığı. Bir test yeniden adlandırılır ya da silinirse Kanun'un
hükmü kapısız kalır; bu test o anda düşer."""
import re
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
KANUN = KOK / "docs" / "sinav-kilavuzu-kanunu.md"
ARAMA_DIZINLERI = (KOK, KOK / "tests", KOK / "dashboard" / "tests", KOK / "dashboard" / "tests" / "e2e")
DOSYA = re.compile(r"^[\w./-]+\.(?:py|ts|tsx)$")
YALIN_TEST = re.compile(r"^test_\w+$")


def _kapi_hucreleri() -> dict[str, str]:
    """{K1: 'Kapı hücresi', ...}: yalnız `| K<n> | ... | ... | <kapı> |` satırları."""
    hucreler = {}
    for satir in KANUN.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(K\d+)\s*\|(.*)\|\s*$", satir)
        if m:
            sutunlar = m.group(2).split("|")
            hucreler[m.group(1)] = sutunlar[-1].strip()
    return hucreler


def _dosya_coz(ad: str) -> Path | None:
    if "/" in ad:
        yol = KOK / ad
        return yol if yol.is_file() else None
    for dizin in ARAMA_DIZINLERI[1:]:
        yol = dizin / ad
        if yol.is_file():
            return yol
    return None


def _anilar(hucre: str):
    """Hücreyi soldan sağa tarar: (tür, dosya adı | None, ad) üçlüleri. Tür: dosya | python_testi | baslik."""
    mevcut_dosya = None
    anilar = []
    for m in re.finditer(r"`([^`]+)`(?:\s*\"([^\"]+)\")?", hucre):
        belirtec, baslik = m.group(1), m.group(2)
        if "::" in belirtec and DOSYA.match(belirtec.split("::", 1)[0]):   # `::after` gibi CSS ögeleri sayılmaz
            dosya, ad = belirtec.split("::", 1)
            anilar.append(("dosya", dosya, None))
            anilar.append(("python_testi", dosya, ad))
            mevcut_dosya = dosya
        elif DOSYA.match(belirtec):
            anilar.append(("dosya", belirtec, None))
            mevcut_dosya = belirtec
            if baslik:
                anilar.append(("baslik", belirtec, baslik))
        elif YALIN_TEST.match(belirtec):
            anilar.append(("python_testi", mevcut_dosya if mevcut_dosya and mevcut_dosya.startswith("tests/") else None,
                           belirtec))
    return anilar


def test_kanunun_kapi_sutunu_okunabiliyor():
    hucreler = _kapi_hucreleri()
    assert sorted(hucreler, key=lambda k: int(k[1:])) == [f"K{i}" for i in range(1, 13)]
    toplam = sum(len(_anilar(h)) for h in hucreler.values())
    assert toplam > 40, f"kapı hücrelerinden yalnız {toplam} anı çıktı; ayrıştırıcı bozulmuş olabilir"


def test_ayristirici_bulunamayan_adi_yakalar():
    """Ayrıştırıcının kendisi: var olmayan dosya/ad/başlık düşmeli (aksi halde asıl test hiçbir şey kanıtlamaz)."""
    anilar = _anilar("`tests/test_pdf_kapilari.py::test_yok_boyle_bir_test`, `test_bir_baska_yok`; "
                     "`dashboard/tests/e2e/hazirlik-kilavuz.spec.ts` \"olmayan başlık\"")
    assert ("python_testi", "tests/test_pdf_kapilari.py", "test_yok_boyle_bir_test") in anilar
    assert ("python_testi", "tests/test_pdf_kapilari.py", "test_bir_baska_yok") in anilar
    assert ("baslik", "dashboard/tests/e2e/hazirlik-kilavuz.spec.ts", "olmayan başlık") in anilar
    py = (KOK / "tests/test_pdf_kapilari.py").read_text(encoding="utf-8")
    assert not re.search(r"def test_yok_boyle_bir_test\b", py)
    ts = (KOK / "dashboard/tests/e2e/hazirlik-kilavuz.spec.ts").read_text(encoding="utf-8")
    assert "olmayan başlık" not in ts


@pytest.mark.parametrize("kapi", [f"K{i}" for i in range(1, 13)])
def test_kanundaki_kapi_adlari_depoda_var(kapi):
    eksik = []
    for tur, dosya, ad in _anilar(_kapi_hucreleri()[kapi]):
        if tur == "dosya":
            if _dosya_coz(dosya) is None:
                eksik.append(f"dosya yok: {dosya}")
        elif tur == "python_testi":
            adaylar = [_dosya_coz(dosya)] if dosya else sorted((KOK / "tests").glob("*.py"))
            if not any(y and re.search(rf"^\s*(?:async\s+)?def {re.escape(ad)}\b", y.read_text(encoding="utf-8"), re.M)
                       for y in adaylar):
                eksik.append(f"test yok: {dosya or 'tests/*.py'}::{ad}")
        elif tur == "baslik":
            yol = _dosya_coz(dosya)
            if yol is not None and ad not in yol.read_text(encoding="utf-8"):
                eksik.append(f"başlık yok: {dosya} \"{ad}\"")
    assert not eksik, f"{kapi}: Kanun'daki kapı adları depoda bulunamadı: {eksik}"
