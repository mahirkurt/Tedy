"""Öğretmen skill'lerinin yükleyicisi ve doğrulayıcısı (spec §1 "Yükleme ve doğrulama").

Bozuk bir skill açılışta hata verir, sessizce atlanmaz; ileti hangi skill'in neden bozuk
olduğunu söyler. Burada her skill tmp_path'e yazılır — gerçek öğretmenlerin içeriği
tests/test_assistant_skills_icerik.py'dedir.
"""
import os

import pytest

from src import assistant_skills as sk
from tests.skill_ornegi import BASLIKLAR, KAYNAKLAR, govde, on_bilgi, skill_yaz


def test_modul_dosyasi_skill_diziniyle_karismaz():
    # src/assistant_skills.py ile src/assistant_skills/ yan yana: import .py'yi bulmalı.
    assert sk.__file__.endswith("assistant_skills.py")
    assert sk.SKILL_DIZINI.name == "assistant_skills"


def test_gecerli_skill_yuklenir(tmp_path):
    skill_yaz(tmp_path)
    s = sk.yukle(tmp_path)["matematik"]
    assert (s.ad, s.kisa_ad, s.ders, s.renk_ailesi) == ("matematik", "Matematik", "Matematik", "purple")
    assert s.ogretmen_adi == "Matematik öğretmeni"
    assert s.karsilama == {"ogrenci": "Merhaba! Bir soruyu getir: adım adım bakalım.",
                           "aile": "Merhaba! Işık'ın sorusunu sorabilirsiniz."}
    assert s.hizli_sorular["aile"] == ("Işık için birinci soru", "Işık için ikinci soru",
                                       "Işık için üçüncü soru")
    assert s.kaynaklar == ("degerlendirme-rubrigi.md", "kavram-yanilgilari.md", "soru-kaliplari.md", "unite-haritasi.md")
    assert s.govde.startswith("## Rol ve ses")
    assert s.gecis_sorusu == "Matematik öğretmenine geçelim mi?"


def test_secici_sirasi_turkce_fen_sosyal_matematik(tmp_path):
    skill_yaz(tmp_path, "matematik", "Matematik", "purple")
    skill_yaz(tmp_path, "sosyal", "Sosyal Bilgiler", "cyan", kisa_ad="Sosyal",
              ogretmen_adi="Sosyal Bilgiler öğretmeni")
    skill_yaz(tmp_path, "fen", "Fen Bilimleri", "teal", kisa_ad="Fen",
              ogretmen_adi="Fen Bilimleri öğretmeni")
    skill_yaz(tmp_path, "turkce", "Türkçe", "magenta", kisa_ad="Türkçe", ogretmen_adi="Türkçe öğretmeni")
    assert list(sk.yukle(tmp_path)) == ["turkce", "fen", "sosyal", "matematik"]


def test_bos_dizin_bos_sozluk_dizin_yoksa_hata(tmp_path):
    assert sk.yukle(tmp_path) == {}
    with pytest.raises(sk.SkillHatasi, match="skill dizini yok"):
        sk.yukle(tmp_path / "yok")


def _bozuk(tmp_path, **kw):
    skill_yaz(tmp_path, **kw)
    with pytest.raises(sk.SkillHatasi) as hata:
        sk.yukle(tmp_path)
    return str(hata.value)


def test_eksik_alan(tmp_path):
    on = on_bilgi().replace("kisa_ad: Matematik\n", "")
    assert "eksik alan: kisa_ad" in _bozuk(tmp_path, on=on)


def test_bilinmeyen_alan(tmp_path):
    on = on_bilgi().replace("ders: Matematik\n", "ders: Matematik\nrenk: mor\n")
    assert "bilinmeyen alan: renk" in _bozuk(tmp_path, on=on)


def test_renk_ailesi_subject_themes_ile_eslesmeli(tmp_path):
    ileti = _bozuk(tmp_path, aile="magenta")
    assert "matematik/SKILL.md" in ileti and "'purple' olmalı" in ileti


def test_ad_dizinle_ayni_olmali(tmp_path):
    on = on_bilgi().replace("name: matematik", "name: mat")
    assert "dizin adıyla" in _bozuk(tmp_path, on=on)


def test_genel_ayrilmis_addir(tmp_path):
    assert "'genel' dışında" in _bozuk(tmp_path, ad="genel", on=on_bilgi(ad="genel"))


def test_ogretmen_adi_ogretmeni_ile_bitmeli(tmp_path):
    assert "ogretmen_adi" in _bozuk(tmp_path, ogretmen_adi="Matematik")


def test_aciklama_tek_cumle(tmp_path):
    on = on_bilgi().replace("sorularında kullanılır.", "sorularında kullanılır. Başka bir cümle.")
    assert "tek cümle" in _bozuk(tmp_path, on=on)


def test_hizli_sorular_uc_dort_madde(tmp_path):
    on = on_bilgi().replace("    - Üçüncü soru\n", "")
    assert "hizli_sorular.ogrenci 3–4" in _bozuk(tmp_path, on=on)


def test_karsilama_iki_okur(tmp_path):
    on = on_bilgi().replace("  aile: Merhaba! Işık'ın sorusunu sorabilirsiniz.\n", "")
    assert "karsilama" in _bozuk(tmp_path, on=on)


def test_on_bilgi_kapanmamis(tmp_path):
    on = on_bilgi().rstrip("-\n") + "\n"
    assert "kapanmamış" in _bozuk(tmp_path, on=on, govde_metni="")


def test_sekme_reddedilir(tmp_path):
    on = on_bilgi().replace("  ogrenci: Merhaba!", "\togrenci: Merhaba!")
    assert "sekme" in _bozuk(tmp_path, on=on)


def test_girinti_bozuk(tmp_path):
    on = on_bilgi().replace("    - Birinci soru", "   - Birinci soru")
    assert "beklenmeyen girinti" in _bozuk(tmp_path, on=on)


@pytest.mark.parametrize("basliklar", [
    BASLIKLAR[:-1],                                   # Sınırlar eksik
    (BASLIKLAR[1], BASLIKLAR[0], *BASLIKLAR[2:]),     # sıra bozuk
    (*BASLIKLAR, "Ek bölüm"),                          # fazla başlık
])
def test_govde_basliklari_tam_ve_sirali(tmp_path, basliklar):
    assert "başlıkları tam olarak" in _bozuk(tmp_path, govde_metni=govde(basliklar))


def test_bos_bolum_reddedilir(tmp_path):
    metin = govde().replace("Sınırlar bölümünün metni.", "")
    assert "'## Sınırlar' bölümü boş" in _bozuk(tmp_path, govde_metni=metin)


def test_eksik_kaynak(tmp_path):
    kaynaklar = {k: v for k, v in KAYNAKLAR.items() if k != "soru-kaliplari.md"}
    assert "references/ eksik: soru-kaliplari.md" in _bozuk(tmp_path, kaynaklar=kaynaklar)


def test_bos_kaynak(tmp_path):
    assert "boş" in _bozuk(tmp_path, kaynaklar={**KAYNAKLAR, "unite-haritasi.md": "  \n"})


def test_kaynak_adi_bicimi(tmp_path):
    assert "kabul edilmez" in _bozuk(tmp_path, kaynaklar={**KAYNAKLAR, "Notlar.MD": "x"})


def test_kaynak_baglantisi_reddedilir(tmp_path):
    kok = tmp_path / "skiller"
    dizin = skill_yaz(kok)
    (tmp_path / "gizli.md").write_text("gizli", encoding="utf-8")
    os.symlink(tmp_path / "gizli.md", dizin / "references" / "baglanti.md")
    with pytest.raises(sk.SkillHatasi, match="kabul edilmez"):
        sk.yukle(kok)


def test_kaynak_oku_yalniz_listedeki_adlari_acar(tmp_path):
    skill_yaz(tmp_path)
    s = sk.yukle(tmp_path)["matematik"]
    assert "Paydalar toplanmaz" in s.kaynak_oku("kavram-yanilgilari.md")
    for ad in ("../SKILL.md", "references/unite-haritasi.md", "/etc/passwd", "SKILL.md", ""):
        with pytest.raises(KeyError):
            s.kaynak_oku(ad)


def test_sayfalara_bol_sinirda_boler_ve_icerigi_korur():
    paragraflar = [f"Paragraf {i}: " + "kelime " * 60 for i in range(60)]
    metin = "\n\n".join(paragraflar)
    sayfalar = sk.sayfalara_bol(metin)
    assert len(sayfalar) > 1
    assert all(len(s) <= sk.SAYFA_SINIRI for s in sayfalar)
    assert "\n\n".join(sayfalar).split() == metin.split()
    assert sk.sayfalara_bol("kısa") == ["kısa"]


def test_tek_uzun_satir_da_bolunur():
    sayfalar = sk.sayfalara_bol("a" * (sk.SAYFA_SINIRI * 2 + 5))
    assert [len(s) for s in sayfalar] == [sk.SAYFA_SINIRI, sk.SAYFA_SINIRI, 5]


def test_kaynak_sayfasi_aralik_disi(tmp_path):
    skill_yaz(tmp_path)
    s = sk.yukle(tmp_path)["matematik"]
    assert s.kaynak_sayfasi("unite-haritasi.md") == ("# Harita\n\n1. Sayılar ve Nicelikler", 1)
    with pytest.raises(IndexError):
        s.kaynak_sayfasi("unite-haritasi.md", 2)


def test_sistem_blogu_belirlenimci_ve_notlari_adlandirir(tmp_path):
    skill_yaz(tmp_path)
    s = sk.yukle(tmp_path)["matematik"]
    blok = s.sistem_blogu()
    assert blok == s.sistem_blogu()
    assert blok.startswith("# Öğretmen modu: Matematik öğretmeni\n")
    assert "`skill_kaynagi`" in blok and "`unite-haritasi.md`" in blok
    assert "## Sınırlar" in blok


def test_govde_bolumleri(tmp_path):
    skill_yaz(tmp_path)
    bolumler = sk.govde_bolumleri(sk.yukle(tmp_path)["matematik"])
    assert list(bolumler) == list(BASLIKLAR)
    assert bolumler["Sınırlar"].strip() == "Sınırlar bölümünün metni."


def test_secici_ozeti(tmp_path):
    skill_yaz(tmp_path)
    oz = sk.yukle(tmp_path)["matematik"].secici_ozeti()
    assert oz["id"] == "matematik" and oz["renk_ailesi"] == "purple"
    assert oz["hizli_sorular"]["ogrenci"] == ["Birinci soru", "İkinci soru", "Üçüncü soru"]
    assert set(oz) == {"id", "kisa_ad", "ogretmen_adi", "ders", "renk_ailesi", "karsilama",
                       "hizli_sorular"}


def test_on_bilgi_degerde_iki_nokta_kalir():
    ob = sk.on_bilgi_coz(["karsilama:", "  ogrenci: Bir soru getir: bakalım."], "x")
    assert ob == {"karsilama": {"ogrenci": "Bir soru getir: bakalım."}}


def test_degerlendirme_rubrigi_zorunlu(tmp_path):
    kaynaklar = {k: v for k, v in KAYNAKLAR.items() if k != "degerlendirme-rubrigi.md"}
    assert "references/ eksik: degerlendirme-rubrigi.md" in _bozuk(tmp_path, kaynaklar=kaynaklar)
