"""Öğretmen skill'lerinin içeriği — depodaki gerçek dosyalar (plan B1, içerik ölçütleri).

Yükleyici biçimi denetler (tests/test_assistant_skills.py); burada, bir gözden geçirenin
elle denetleyeceği ölçütlerin ölçülebilen kısmı var: araç adları gerçek araçlar, kavram
yanılgısı kataloğu ve soru kalıpları dolu ve biçimli, ünite haritası korpustan üretilmiş ve
temaları gövdede, hitap kuralları karşılamada ve hızlı sorularda, metin Türkçe, B1'de
olmayan araçlar anılmıyor, öğretmen bloğu makul boyda.
"""
import re

import pytest

from src import assistant_modules
from src import assistant_skills as sk
from src import assistant_tools as at

DIZINLER = sorted(p.name for p in sk.SKILL_DIZINI.iterdir()
                  if p.is_dir() and not p.name.startswith(("_", ".")))
GERCEK_ARACLAR = {at.LOCAL_TOOL, at.ODEV_TOOL, at.PROGRAM_TOOL, at.SINAV_TOOL, at.TAKVIM_TOOL,
                  at.ICERIK_TOOL, at.NOT_TOOL, at.PLATFORM_TOOL, at.KITAP_TOOL, at.VIDEO_TOOL,
                  assistant_modules.TOOL_NAME, at.SKILL_TOOL, *at.TOOL_ALLOWLIST}
ZORUNLU_ARACLAR = {"kitap_listele", "kitap_sayfa", "mufredat_ara", "figur_ara", "figur_getir",
                   "kazanim_ara", "video_listele", at.PROGRAM_TOOL, at.SINAV_TOOL, at.ICERIK_TOOL,
                   at.ODEV_TOOL, at.SKILL_TOOL}
# Genel moda ya da aileye ait araçlar ve B4'ün henüz olmayan araçları bir öğretmen tanımında anılmaz.
YASAK_ARACLAR = {at.MOD_ONER_TOOL, at.AILE_TOOL, "alistirma_olustur", "ogrenme_gunlugu"}
INGILIZCE = re.compile(r"\b(the|and|of|with|you|your|is|are|this|that|for)\b", re.IGNORECASE)
SORU_TURLERI = {"coktan_secmeli", "dogru_yanlis", "kisa_cevap", "acik_uclu"}
# "siz" hitabı: -sInIz çekimi (sorabilirsiniz), "size/sizin/siz", çıplak -(I)nIz (iyelik ya da
# resmi/çoğul buyurma: "eviniz", "bakınız") ve küçük, açık bir çoğul/resmi buyurma sözcük listesi.
# Çıplak "-In/-Un" sonekini genel bir desenle yakalamak ölçüldü: "istersin", "yapabilirsin"
# (2. tekil "sen" çekimi), "Ödevin", "Kitabın", "metnin", "sorunun", "konunun" (ilgi eki/iyelik),
# "Bugün", "gelsin" gibi çok sayıda yanlış-pozitif üretiyor — bu yüzden bare (ın|in|un|ün) deseni
# kullanılmaz; yalnız aşağıdaki açık listedeki buyurma biçimleri yakalanır.
_COGUL_BUYURMA = ("getirin", "bakın", "yapın", "okuyun", "dinleyin", "söyleyin", "yazın")
SIZ = re.compile(
    r"(siniz|sınız|sunuz|sünüz|size|sizin|\bsiz\b"
    r"|\b\w+(ınız|iniz|unuz|ünüz)\b"
    rf"|\b(?:{'|'.join(_COGUL_BUYURMA)})\b)"
)
BLOK_SINIRI = 12_000


@pytest.fixture(scope="module")
def skiller():
    return sk.yukle()


def _alt_bolumler(metin: str) -> list[str]:
    """'### ' başlıklı bölümler, başlıklarıyla."""
    return [b for b in re.split(r"(?m)^(?=### )", metin) if b.startswith("### ")]


def test_skill_dizini_bos_degil():
    assert DIZINLER


@pytest.mark.parametrize("ad", DIZINLER)
def test_yukleyici_kabul_eder_ve_blok_makul_boyda(skiller, ad):
    assert ad in skiller
    assert len(skiller[ad].sistem_blogu()) <= BLOK_SINIRI


@pytest.mark.parametrize("ad", DIZINLER)
def test_arac_kullanimi_gercek_araclari_adlandirir(skiller, ad):
    bolum = sk.govde_bolumleri(skiller[ad])["Araç kullanımı"]
    anilan = set(re.findall(r"`([a-z_]+)`", bolum))
    assert anilan <= GERCEK_ARACLAR, anilan - GERCEK_ARACLAR
    assert ZORUNLU_ARACLAR <= anilan, ZORUNLU_ARACLAR - anilan


@pytest.mark.parametrize("ad", DIZINLER)
def test_b1de_olmayan_ya_da_baska_moda_ait_arac_anilmaz(skiller, ad):
    metin = (skiller[ad].dizin / "SKILL.md").read_text(encoding="utf-8")
    assert not [a for a in YASAK_ARACLAR if a in metin]


@pytest.mark.parametrize("ad", DIZINLER)
def test_ders_akisi_anlatan_ogretmen(skiller, ad):
    bolum = sk.govde_bolumleri(skiller[ad])["Ders akışı"]
    basliklar = ("### Adım adım", "### Neden böyle?", "### Sıra sende")
    for baslik in basliklar:
        assert baslik in bolum
    konumlar = [bolum.index(baslik) for baslik in basliklar]
    assert konumlar == sorted(konumlar), "üç başlık bu sırada olmalı: " + " | ".join(basliklar)


@pytest.mark.parametrize("ad", DIZINLER)
def test_kavram_yanilgilari_kisa_liste_ve_tam_katalog(skiller, ad):
    s = skiller[ad]
    kisa = [sat for sat in sk.govde_bolumleri(s)["Sık kavram yanılgıları"].splitlines()
            if re.match(r"^- .+ → .+", sat)]
    assert len(kisa) >= 6
    katalog = _alt_bolumler(s.kaynak_oku("kavram-yanilgilari.md"))
    assert len(katalog) >= 12
    for bolum in katalog:
        for etiket in ("**Doğrusu:**", "**Nasıl düzeltirsin:**", "**Kontrol sorusu:**"):
            assert etiket in bolum, (bolum.splitlines()[0], etiket)


@pytest.mark.parametrize("ad", DIZINLER)
def test_soru_kaliplari(skiller, ad):
    kaliplar = _alt_bolumler(skiller[ad].kaynak_oku("soru-kaliplari.md"))
    assert len(kaliplar) >= 6
    turler = set()
    for bolum in kaliplar:
        m = re.search(r"^\*\*Tür:\*\* (\S+)$", bolum, re.M)
        assert m and m.group(1) in SORU_TURLERI, bolum.splitlines()[0]
        turler.add(m.group(1))
        assert "**Örnek:**" in bolum and "**Cevap:**" in bolum, bolum.splitlines()[0]
    assert {"coktan_secmeli", "dogru_yanlis", "kisa_cevap"} <= turler


@pytest.mark.parametrize("ad", DIZINLER)
def test_unite_haritasi_korpustan_ve_temalar_govdede(skiller, ad):
    s = skiller[ad]
    harita = s.kaynak_oku("unite-haritasi.md")
    assert "corpus_version=1.6" in harita
    assert f"`scripts/skill_unite_haritasi.py {ad}`" in harita
    temalar = re.findall(r"(?m)^\d+\. (.+) \(program s\.\d+\)$", harita)
    assert len(temalar) >= 5
    bag = sk.govde_bolumleri(s)["Maarif Modeli bağı"]
    assert [t for t in temalar if t not in bag] == []


@pytest.mark.parametrize("ad", DIZINLER)
def test_hitap(skiller, ad):
    s = skiller[ad]
    assert "Işık" not in s.karsilama["ogrenci"] and not SIZ.search(s.karsilama["ogrenci"])
    assert "Işık" in s.karsilama["aile"] and SIZ.search(s.karsilama["aile"])
    assert all("Işık" in q for q in s.hizli_sorular["aile"])
    assert not any("Işık" in q for q in s.hizli_sorular["ogrenci"])
    rol = sk.govde_bolumleri(s)["Rol ve ses"]
    assert '"sen"' in rol and '"siz"' in rol


@pytest.mark.parametrize("metin", [
    "istersin", "yapabilirsin", "ödevin", "metnin ana fikri", "Bugün", "gelsin",
])
def test_siz_deseni_sen_ve_ilgi_ekini_yakalamaz(metin):
    """SIZ, 2. tekil 'sen' çekimini ('istersin', 'yapabilirsin') ve ilgi eki/iyeliği
    ('ödevin', 'metnin ana fikri') ya da tesadüfen '-In/-Un' ile biten sıradan sözcükleri
    ('Bugün', 'gelsin') yanlışlıkla 'siz' hitabı saymamalı."""
    assert not SIZ.search(metin)


@pytest.mark.parametrize("metin", [
    "sorabilirsiniz", "getirin", "sizin",
])
def test_siz_deseni_gercek_siz_hitabini_yakalar(metin):
    assert SIZ.search(metin)


@pytest.mark.parametrize("ad", DIZINLER)
def test_sinirlar(skiller, ad):
    bolum = sk.govde_bolumleri(skiller[ad])["Sınırlar"]
    assert "teslim" in bolum and "Genel mod" in bolum


@pytest.mark.parametrize("ad", DIZINLER)
def test_metin_turkce(skiller, ad):
    s = skiller[ad]
    metinler = {"SKILL.md": (s.dizin / "SKILL.md").read_text(encoding="utf-8")}
    metinler.update({k: s.kaynak_oku(k) for k in s.kaynaklar})
    ingilizce = {dosya: INGILIZCE.findall(m) for dosya, m in metinler.items() if INGILIZCE.search(m)}
    assert ingilizce == {}


def test_turkce_unite_haritasi_yanlis_govdeyi_secmez(skiller):
    """T.Y.7.1'in gerçek kazanım ifadesi 'Yazma sürecini yönetebilme'dir (heading satırı,
    program s.127); korpustaki 'outcome' satırı iki fıkralı bir açıklama metninin ortasından
    kesiktir ve 'tartışabilme' ile 'değerlendirebilme' ifadelerini birlikte taşır — harita bu
    kesik ifadeyi asla seçmemeli (bkz. scripts/skill_unite_haritasi.py'nin heading tercihi ve
    tests/test_skill_unite_haritasi.py'deki üretici testleri)."""
    if "turkce" not in skiller:
        pytest.skip("turkce skill'i yok")
    harita = skiller["turkce"].kaynak_oku("unite-haritasi.md")
    assert "**T.Y.7.1** — Yazma sürecini yönetebilme" in harita
    assert "**T.Y.7.1** — Yazılı üretimlerinde ve yazılı etkileşimlerinde tartışabilme" not in harita
