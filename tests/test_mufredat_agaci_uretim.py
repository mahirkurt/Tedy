"""Üretim montajı: kimlik kararlılığı, bozuk sayfa, eşleme, eşik, kayma kapısı (spec §2.2, §3, §6.1).

Canlı iddialardaki sayılar 2026-10-11'de ölçüldü; eşleme bozulursa bu testler düşer.
"""
import re
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
@pytest.mark.parametrize("slug,en_az", [("matematik", 22), ("fen", 22), ("sosyal", 17)])
def test_kazanim_kapsamasi_olculen_degerin_altina_dusmez(agac, slug, en_az):
    """Ölçüldü 2026-10-11, denetim turundan sonra: matematik 22/30, fen 22/35, sosyal 15/17.
    2026-10-19: sosyal 17/17 — iki satıra bölünmüş iki başlık (SB.7.1.3, SB.7.3.1) birleştirildi.

    Sayı iki kez düştü ve ikisi de kasıtlı. İlk sonda fen 25 / sosyal 17 saymıştı; o sayım
    grup başlıklarını (aynı konunun kopyası) ve iki sütunlu düzenin kuyruk başlıklarını
    içeriyordu. Denetim turunda matematik 26 → 22 oldu: eşleme kesinliği sıkılaştırıldı ve
    bir konunun kendi ünitesi dışından gelen kazanımı artık reddediliyor — "Eşitsizlikler"
    ünite 2'de olup olasılık kazanımı MAT.7.7.2'yi taşıyordu. Kapsama düştü, doğruluk arttı.
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
    assert "Tüketim Arasındaki Döngü" not in adlar


@canli
def test_sosyalde_bolunmus_basliklar_tam_adla_konu_olur(agac):
    """Ölçüldü 2026-10-19 (doc 491): iki satıra bölünmüş başlığın yalnız kuyruğu okunuyordu ve
    SB.7.1.3 ile SB.7.3.1'in konusu ağaçta yoktu — "Millî Meseleler" modülü hiçbir yaprağa
    bağlanamıyordu."""
    sosyal = next(d for d in agac["dersler"] if d["slug"] == "sosyal")
    konular = {konu["ad"]: konu["kazanimlar"] for unite in sosyal["uniteler"] for konu in unite["konular"]}
    assert konular["Millî Meseleler Karşısında Türk Toplumunun Tutum ve Davranışları"] == ["SB.7.1.3"]
    assert konular["Osmanlı Devleti’nin Cihan Devleti Hâline Gelmesini Sağlayan Politikalar"] == ["SB.7.3.1"]
    assert all("i\u0307" not in ad for ad in konular), "Türkçe küçültme 'i̇' bıraktı"


@canli
def test_matematik_sayilar_yapraklari_kendi_kazanimini_tasir(agac):
    """Ölçüldü 2026-10-19: "Tam Sayılar" ve "Rasyonel Sayılar" MAT.7.1.1–7.1.4'ün dördünü de
    taşıyordu ("Tam" dört harften kısa diye sayılmıyordu; eşit skorlu her kazanım yazılıyordu)."""
    mat = next(d for d in agac["dersler"] if d["slug"] == "matematik")
    konular = {konu["ad"]: konu["kazanimlar"] for unite in mat["uniteler"] for konu in unite["konular"]}
    assert konular["Tam Sayılar"] == ["MAT.7.1.1"]
    assert konular["Rasyonel Sayılar"] == ["MAT.7.1.1", "MAT.7.1.2"]
    assert konular["Rasyonel Sayılarda Karşılaştırma ve Sıralama"] == ["MAT.7.1.3"]
    assert konular["Yansıma Dönüşümü"] == ["MAT.7.3.1"]


def test_kazanim_en_guclu_yaprakta_kalir_ve_yaprak_bos_kalmaz():
    metinler = {"K1": "rasyonel sayıları karşılaştırma ve sıralama", "K2": "rasyonel sayılar yorumlama"}
    genel = {"ad": "Rasyonel Sayılar", "kazanimlar": ["K1", "K2"]}
    ozel = {"ad": "Rasyonel Sayılarda Karşılaştırma ve Sıralama", "kazanimlar": ["K1"]}
    tek = {"ad": "Rasyonel Sayılar Örnekleri", "kazanimlar": ["K1"]}
    u.kazanimi_en_guclu_yaprakta_birak([genel, ozel, tek], metinler)
    assert genel["kazanimlar"] == ["K2"] and ozel["kazanimlar"] == ["K1"]
    assert tek["kazanimlar"] == ["K1"], "son kazanımını kaybeden yaprak boş kalırdı"


def test_uc_harfli_icerik_sozcugu_sayilir_kisa_kok_tam_esitlik_ister():
    assert "tam" in u._icerik_sozcukleri("Tam Sayılar")
    assert u._ortusme_orani("Tam Sayılar", "rasyonel sayıların ondalık gösterimi") == 0.5
    assert u._ortusme_orani("Tam Sayılar", "tamamlanan sayılar") == 0.5
    assert "her" not in u._icerik_sozcukleri("her durumda")


def test_bolunmus_icindekiler_basligi_birlesir_unite_adi_yapismaz():
    db = sqlite3.connect(":memory:")
    db.execute("create table document_page (document_id int, page_no int, text text)")
    db.execute("insert into document_page values (1, 7, ?)", ("\n".join([
        "ORTAK MİRASIMIZ",
        "KÜRESELLEŞMENİN ETKİSİ ...............",
        "MİLLÎ MESELELER KARŞISINDA TÜRK TOPLUMUNUN TUTUM VE",
        " DAVRANIŞLARI ..............................",
        "30",
        "KİTABIMIZI TANIYALIM .......",
    ]),))
    basliklar = u.icindekiler_basliklari(db, 1, frozenset({u.harf_katla("Ortak Mirasımız")}))
    assert basliklar == ["KÜRESELLEŞMENİN ETKİSİ",
                         "MİLLÎ MESELELER KARŞISINDA TÜRK TOPLUMUNUN TUTUM VE\nDAVRANIŞLARI",
                         "KİTABIMIZI TANIYALIM"]


def test_baslik_duzeni_kucuk_kalan_baglaci_turkce_kucultur():
    assert u.baslik_duzeni("EKONOMİK GELİŞMİŞLİK İLE ÜRETİM") == "Ekonomik Gelişmişlik ile Üretim"


@canli
def test_depodaki_dosya_semaya_uyar():
    durum, agac = ma.oku(ma.agac_yolu(KOK / "src"))
    assert durum == "ok" and agac is not None


# ── Denetim turu: eşleme kesinliği ve ad kalitesi ────────────────────────────


def test_ayni_kok_kisa_onekte_eslesmez():
    """Gevşek `startswith` en az paylaşılan uzunluk istemeli.

    Denetimde ölçüldü: `_ayni_kok("esitsizlikler", "esit")` True dönüyordu ve "Eşitsizlikler"
    başlığı MAT.7.7.2 (olasılık) kazanımına 1.0 skorla eşleşiyordu; "dair" (ilgili) ile
    "dairenin" de aynı kökten sayılıyordu.
    """
    assert u._ayni_kok("esitsizlikler", "esit") is False
    assert u._ayni_kok("dairenin", "dair") is False
    # Gerçek ek budaması sürmeli.
    assert u._ayni_kok("organlar", "organlarin") is True
    assert u._ayni_kok("nitelikleri", "niteliklerini") is True


def test_tek_sozcuklu_baslik_tesadufi_kokle_eslesmez():
    """Tek içerik sözcüğü olan başlık bir tesadüfle 1.0 almamalı."""
    kodlar, kaynak = u.kazanim_esle("Eşitsizlikler", [
        {"kod": "MAT.7.7.2", "unite_no": 7,
         "metin": "Aynı deneye ait olayların eşit olasılıklı olma durumlarını değerlendirebilme"}])
    assert kodlar == [] and kaynak == "eslenmedi"


@pytest.mark.parametrize("ham,beklenen", [
    # Zaten doğru büyük-küçük yazılmış başlığa dokunulmaz (denetimde 17 başlık bozulmuştu).
    ("Sen Sor O Yanıtlasın-Sporda ve Yaşamda Hedefe Odaklan", None),
    ("Ağaç ve Sen (Serbest Okuma Metni)", None),
    ("Milli Mücadele Sergisi Kahraman Çocuklar (Dinleme/İzleme)", None),
    ("Komik mi Komik", None),
    ("Dünya Komşuları ile Birlikte", None),
])
def test_baslik_duzeni_dogru_yazilmis_basligi_bozmaz(ham, beklenen):
    assert u.baslik_duzeni(ham) == (beklenen or ham)


def test_baslik_duzeni_buyuk_harfli_basligi_duzenler():
    assert u.baslik_duzeni("TAM SAYILAR") == "Tam Sayılar"


def test_unite_adindan_bolum_isareti_atilir():
    """Program bir temayı iki sayfa dizisine bölüyor: "SAYILAR VE NİCELİKLER (1)" ve "(2)".

    Ünite numarasına göre tekilleştirmek doğru, ama "(1)" işaretini okura taşımak
    hiç gelmeyecek bir "(2)" vaat eder (denetimde ölçüldü).
    """
    assert u.unite_adi_duzelt("Sayılar ve Nicelikler (1)") == "Sayılar ve Nicelikler"
    assert u.unite_adi_duzelt("Geometrik Nicelikler (2)") == "Geometrik Nicelikler"
    assert u.unite_adi_duzelt("Uzay Çağı") == "Uzay Çağı"


def test_ocr_duzeltmesi_olculen_bozulmayi_kapsar():
    assert u.baslik_duzeni("HAY ATIMIZDAKİ EKONOMİ") == "Hayatımızdaki Ekonomi"


def test_grup_basligi_numarasi_okura_gitmez():
    assert u.numara_at("1. Işığın Kırılması") == "Işığın Kırılması"
    assert u.numara_at("Işığın Kırılması") == "Işığın Kırılması"


@canli
def test_hicbir_kazanim_konunun_unitesi_disindan_gelmez(agac):
    """C1: bir konunun kazanımı kendi ünitesine ait olmalı.

    Denetimde ölçüldü: "Eşitsizlikler" (ünite 2) MAT.7.7.2'yi (ünite 7) taşıyordu ve
    o kazanıma sahip bir modül yanlış üniteye bağlanıyordu.
    """
    ihlal = []
    for ders in agac["dersler"]:
        for unite in ders["uniteler"]:
            for konu in unite["konular"]:
                for kod in konu["kazanimlar"]:
                    eslesme = re.search(r"\.(\d+)\.\d+$", kod)
                    if eslesme and int(eslesme.group(1)) != unite["no"]:
                        ihlal.append(f"{konu['id']} (ünite {unite['no']}) ← {kod}")
    assert ihlal == [], "ünite dışı kazanım:\n" + "\n".join(ihlal)


@canli
def test_hicbir_konu_adi_iki_kez_gecmez(agac):
    """I4: aynı ad iki ayrı ünitede görünürse kimlik çakışması sayılmaz ve kopya gizli kalır.

    Denetimde ölçüldü: Türkçe'de kitap arka maddesi haritaları iki temada birden çıkıyordu.
    """
    for ders in agac["dersler"]:
        adlar = [konu["ad"] for unite in ders["uniteler"] for konu in unite["konular"]]
        yineleyen = sorted({ad for ad in adlar if adlar.count(ad) > 1})
        assert yineleyen == [], f"{ders['slug']}: yinelenen ad {yineleyen}"


@canli
def test_kitaptan_gelen_ad_cumle_degil(agac):
    """I4: gövde metninden kopmuş cümleler konu adı olmaz.

    Kural kitabın başlığına (`ad_kaynak`) uygulanır; programdan onarılan ad meşru olarak
    daha uzun olabilir (I ayrımını yitirmiş kitapta kazanım metnine düşülüyor). İçindekilerde
    iki satıra bölünmüş başlık " / " ile yazılır ve sınır her satıra ayrı uygulanır (2026-10-19).
    """
    uzun = []
    for ders in agac["dersler"]:
        for unite in ders["uniteler"]:
            for konu in unite["konular"]:
                ham = konu["ad_kaynak"]
                if (max(len(satir) for satir in ham.split(" / ")) > u.KONU_AD_SINIRI
                        or ham.rstrip().endswith((",", "."))):
                    uzun.append(f"{konu['id']}: {ham[:60]}")
    assert uzun == [], "cümle gibi konu adı:\n" + "\n".join(uzun)


@canli
def test_hasarli_kitapta_cozulemeyen_i_programa_duser(agac):
    """Onarım bir I'yı çözemezse ad kazanımdan gelir; yanlış harf okura gitmez (D4)."""
    sosyal = next(d for d in agac["dersler"] if d["slug"] == "sosyal")
    adlar = [konu["ad"] for unite in sosyal["uniteler"] for konu in unite["konular"]]
    # Onarımın tuttuğu başlıklar kitabın kendi adıdır.
    assert "Türkiye Cumhuriyeti’nin Nitelikleri" in adlar
    assert "Millî Kalkınma Hamleleri" in adlar
    # Hiçbir ad, onarılmamış noktasız I kalıbını taşımaz.
    assert not [ad for ad in adlar if "ı" in ad and "Karşılaşılabılecek" in ad]
