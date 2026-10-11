"""Üretim montajı: kimlik kararlılığı, bozuk sayfa, eşleme, eşik, kayma kapısı (spec §2.2, §3, §6.1).

Canlı iddialardaki sayılar 2026-10-11'de ölçüldü; eşleme bozulursa bu testler düşer.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "scripts"))

import mufredat_agaci as u  # noqa: E402
from src import mufredat_agaci as ma  # noqa: E402


# Review Focus 2: aynı ünitede aynı adlı iki konu.
def test_kimlik_cakismasi_sessizce_yutmaz():
    kullanilan: set[str] = set()
    birinci, cakisti1 = u.kimlik_ver("fen", 3, "Sindirim Sisteminin Sağlığı", kullanilan)
    ikinci, cakisti2 = u.kimlik_ver("fen", 3, "Sindirim Sisteminin Sağlığı", kullanilan)
    assert birinci == "fen-u3-sindirim-sisteminin-sagligi"
    assert ikinci == "fen-u3-sindirim-sisteminin-sagligi-2"
    assert (cakisti1, cakisti2) == (False, True)


def test_kimlik_sirasal_sayi_tasimaz():
    kullanilan: set[str] = set()
    kimlik, _ = u.kimlik_ver("fen", 3, "Dolaşım Sistemi", kullanilan)
    assert kimlik == "fen-u3-dolasim-sistemi"


# Review Focus 3: bozuk sayfa aralığı.
@pytest.mark.parametrize("sayfa", [[101, 97], [0, 5], [-3, 2], [150, 400], None, [97]])
def test_gecersiz_sayfa_reddedilir(sayfa):
    assert u.gecersiz_sayfa(sayfa, 153) is True


def test_gecerli_sayfa_kabul_edilir():
    assert u.gecersiz_sayfa([97, 101], 153) is False


def test_kazanim_eslenmeyince_kaynak_eslenmedi_olur():
    kodlar, kaynak = u.kazanim_esle("Bambaşka Bir Konu", [
        {"kod": "FB.7.3.2", "unite_no": 3,
         "metin": "Sindirim sisteminin sağlığı için yapılması gerekenler konusunda bilgi toplayabilme"}])
    assert kodlar == [] and kaynak == "eslenmedi"


def test_kazanim_baslik_kazanimda_geciyorsa_eslenir():
    """Yön: başlığın sözcükleri kazanımda geçiyor mu — tersi değil.

    Kazanım her zaman daha uzun ve ayrıntılıdır; kazanımın sözcüklerini başlıkta aramak
    ölçüldü ve hiçbir konuyu eşlemiyordu (2026-10-11).
    """
    kodlar, kaynak = u.kazanim_esle("Sindirim Sisteminin Sağlığı", [
        {"kod": "FB.7.3.2", "unite_no": 3,
         "metin": "Sindirim sisteminin sağlığı için yapılması gerekenler konusunda bilgi toplayabilme"}])
    assert kodlar == ["FB.7.3.2"] and kaynak == "metin-ortusmesi"


def test_kazanim_eslemesi_turkce_ekleri_budar():
    """'Organlar' ile 'organların' aynı köktür; ek budanmazsa eşleme düşüyordu."""
    kodlar, _ = u.kazanim_esle("Sindirim Sistemini Oluşturan Yapı ve Organlar", [
        {"kod": "FB.7.3.1", "unite_no": 3,
         "metin": "Sindirim sistemini oluşturan yapı ve organların görevlerini model üzerinde"
                  " bilimsel olarak gözlemleyebilme"}])
    assert kodlar == ["FB.7.3.1"]


def test_ana_cumle_surec_bilesenlerini_atar():
    ham = ("Uzay araştırmaları için geliştirilen teknolojileri karşılaştırabilme a) Uzay"
           " araştırmaları için geliştirilen teknolojilerin özelliklerini belirler.")
    assert u.ana_cumle(ham) == (
        "Uzay araştırmaları için geliştirilen teknolojileri karşılaştırabilme")


def test_temizle_satir_sonu_tirelemesini_birlestirir():
    assert "listeler" in u.temizle("farklılıklarını lis- teler")


@pytest.mark.parametrize("ad", ["Kaynakça", "Sözlük", "Ünite Sonu Değerlendirme",
                                "Neler Biliyoruz?", "Kitabımızı Tanıyalım"])
def test_aparat_konu_olmaz(ad):
    assert u.aparat_mi(ad) is True


def test_gercek_konu_aparat_degil():
    assert u.aparat_mi("Sindirim Sisteminin Sağlığı") is False


@pytest.mark.parametrize("ad", ["1. Sindirim Sistemi", "2. Dolaşım Sistemi", "3. Karışımlar"])
def test_numarali_icindekiler_satiri_grup_basligidir(ad):
    """Fen kitaplarında numaralı satır alt ünite başlığıdır; çocuklarıyla birlikte
    sayılırsa aynı konu iki kez ve iki kazanımla çıkıyordu (ölçüldü)."""
    assert u.grup_basligi_mi(ad) is True


def test_konu_satiri_grup_basligi_degil():
    assert u.grup_basligi_mi("Sindirim Sisteminin Sağlığı") is False


def _db_var() -> bool:
    try:
        u.baglan().execute("select 1 from document limit 1").fetchone()
        return True
    except sqlite3.Error:
        return False


canli = pytest.mark.skipif(not _db_var(), reason="müfredat veritabanı bu makinede yok")


@pytest.fixture(scope="module")
def agac():
    return u.agac_uret(u.baglan(), list(u.DERSLER))


# Bugünün ölçümü kapıya dönüşür (spec §6.1).
@canli
@pytest.mark.parametrize("kitap_id,beklenen_kayma", [(439, 1), (473, 1), (346, 0), (506, 0)])
def test_turetilen_kayma_olculen_degerle_ayni(kitap_id, beklenen_kayma):
    kayma, uyum = u.kitap_kaymasi(u.baglan(), kitap_id)
    assert kayma == beklenen_kayma, f"{kitap_id}: kayma {kayma}, uyum {uyum}"


@canli
def test_dort_dersin_hepsi_yazildi(agac):
    """Dördü de istendi (spec §1). İkisini sessizce düşürmek kapsamı daraltmaktır."""
    assert {d["slug"] for d in agac["dersler"]} == {"turkce", "matematik", "fen", "sosyal"}


@canli
def test_uretilen_agac_semaya_uyar(agac):
    assert ma.dogrula(agac) == []


@canli
@pytest.mark.parametrize("slug,en_az", [("matematik", 26), ("fen", 22), ("sosyal", 15)])
def test_kazanim_kapsamasi_olculen_degerin_altina_dusmez(agac, slug, en_az):
    """Ölçüldü 2026-10-11, son hâl: matematik 26/30, fen 22/35, sosyal 15/17.

    İlk sonda fen 25 ve sosyal 17 saymıştı; o sayım grup başlıklarını (aynı konunun kopyası)
    ve iki sütunlu düzenin bıraktığı kuyruk başlıkları da içeriyordu. İkisi de kasten düşüyor,
    bu yüzden gerçek kapsama daha düşük.
    """
    assert agac["kapsam"][slug]["kazanimi_eslenen"] >= en_az


@canli
def test_turkce_konulari_kazanim_kodu_tasimaz(agac):
    """Türkçe kazanımı temaya değil beceriye kodlu; tema metnine kazanım atamak uydurma olur."""
    turkce = next(d for d in agac["dersler"] if d["slug"] == "turkce")
    for unite in turkce["uniteler"]:
        for konu in unite["konular"]:
            assert konu["kazanimlar"] == [] and konu["kazanim_kaynak"] == "eslenmedi"


@canli
def test_turkce_her_temaya_konu_dustu(agac):
    turkce = next(d for d in agac["dersler"] if d["slug"] == "turkce")
    assert len(turkce["uniteler"]) == 6
    assert all(unite["konular"] for unite in turkce["uniteler"])


@canli
def test_turkce_ve_sosyalde_sayfa_uydurulmaz(agac):
    """Ölçüldü: bu kitapların içindekilerinde nokta öncüllü satır yok, sayfa türetilemez."""
    for slug in ("turkce", "sosyal"):
        ders = next(d for d in agac["dersler"] if d["slug"] == slug)
        for unite in ders["uniteler"]:
            for konu in unite["konular"]:
                assert konu["sayfa_kaynak"] == "yok" and "sayfa" not in konu


@canli
def test_fen_ve_matematikte_sayfa_var(agac):
    for slug in ("fen", "matematik"):
        ders = next(d for d in agac["dersler"] if d["slug"] == slug)
        sayfali = [konu for unite in ders["uniteler"] for konu in unite["konular"]
                   if konu["sayfa_kaynak"] == "icindekiler"]
        assert sayfali, f"{slug}: hiç sayfa aralığı türetilmedi"


@canli
def test_sosyal_duzen_parcasi_konu_olmaz(agac):
    """İki sütunlu içindekilerden gelen yarım başlıklar ("DAVRANIŞLARI") okura gitmez:
    kazanım kanıtı olmayan satır düşer (spec §3)."""
    sosyal = next(d for d in agac["dersler"] if d["slug"] == "sosyal")
    adlar = {konu["ad"] for unite in sosyal["uniteler"] for konu in unite["konular"]}
    assert "Davranışları" not in adlar and "Sağlayan Politikalar" not in adlar


@canli
def test_depodaki_dosya_semaya_uyar():
    durum, agac = ma.oku(ma.agac_yolu(KOK / "src"))
    assert durum == "ok" and agac is not None
