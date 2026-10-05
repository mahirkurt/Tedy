"""Asistan karma araması (2026-10-05): bge-m3 vektörleri, toplu gömme, soru gömme, RRF.

Hiçbir test ağa çıkmaz: gömme işlevi her testte sahte olarak verilir. Ölçüm: BM25'in dolaylı
sorularda ilk 8'de bulma oranı 0.53, karma 0.69 (öğrenci indeksinde vektör ağırlıklı 0.49 -> 0.82;
aile indeksinin İngilizce kitaplarında BM25 0.00).
"""
import numpy as np
import pytest

from src import assistant_vektor as av


def _ayar(**kw):
    base = dict(acik=True, model="bge-m3", sorgu_adresleri=("http://hp",), toplu_adresleri=("http://mbp", "http://pi"),
                agirlik_ogrenci=3.0, agirlik_aile=1.0, sure=60.0)
    base.update(kw)
    return av.VektorAyari(**base)


def _vektor(metin, boyut=8):
    """Deterministic fake embedding: a few words map to fixed axes."""
    v = np.zeros(boyut, dtype=np.float32)
    for i, kelime in enumerate(("galaksi", "yıldız", "kesir", "ödev", "öfke", "uyku", "evren", "payda")):
        if kelime in metin.lower():
            v[i] = 1.0
    v[-1] += 0.01
    return v.tolist()


def _sahte_gom(cagrilar=None, bozuk=()):
    def gom(adres, model, metinler, zaman_asimi):
        if cagrilar is not None:
            cagrilar.append((adres, len(metinler)))
        if adres in bozuk:
            raise OSError("bağlantı yok")
        return [_vektor(m) for m in metinler]
    return gom


def _parca(i, metin):
    return {"chunk_id": f"c{i}", "path": f"content/eba/k{i}.md", "chunk_index": 0, "text": metin}


ANLAMLI = " Bu cümle yalnız parçayı anlamlı uzunluğa getirmek için yazılmış dolgu metnidir."


def test_anlamsiz_parca_gomulmez():
    assert av.anlamli_mi("Galaksiler yıldızlardan oluşur." + ANLAMLI)
    assert not av.anlamli_mi("." * 400)
    assert not av.anlamli_mi("Chapter 3 Research 75")


def test_doldur_eksikleri_gomer_kaybolanlari_atar_ve_modeli_kaydeder(tmp_path):
    depo = av.VektorDeposu(tmp_path)
    parcalar = [_parca(1, "Galaksi" + ANLAMLI), _parca(2, "Kesir" + ANLAMLI), _parca(3, "." * 300)]
    sonuc = av.doldur(parcalar, depo, _ayar(), gom=_sahte_gom())
    assert sonuc["toplam"] == 2 and sonuc["vektorlu"] == 2 and sonuc["yeni"] == 2 and sonuc["eksik"] == 0
    anahtarlar, matris, model = depo.yukle()
    assert model == "bge-m3" and matris.shape == (2, 8)
    assert np.allclose(np.linalg.norm(matris, axis=1), 1.0)

    cagrilar = []
    sonuc = av.doldur(parcalar[:1] + [_parca(4, "Ödev" + ANLAMLI)], depo, _ayar(), gom=_sahte_gom(cagrilar))
    assert sonuc["yeni"] == 1 and sonuc["vektorlu"] == 2  # kesir parçası artık yok, atıldı
    assert sum(n for _, n in cagrilar) == 1
    assert set(depo.yukle()[0]) == {av.metin_anahtari("Galaksi" + ANLAMLI), av.metin_anahtari("Ödev" + ANLAMLI)}


def test_anahtar_metindir_kimlik_degil(tmp_path):
    """Portal eşitlemesi metin aynıyken chunk_id'yi değiştirir (ölçüldü 2026-10-05); yeniden gömme olmaz."""
    depo = av.VektorDeposu(tmp_path)
    av.doldur([_parca(1, "Galaksi" + ANLAMLI)], depo, _ayar(), gom=_sahte_gom())
    cagrilar = []
    yeni = {**_parca(1, "Galaksi" + ANLAMLI), "chunk_id": "baska-kimlik"}
    assert av.doldur([yeni], depo, _ayar(), gom=_sahte_gom(cagrilar))["yeni"] == 0
    assert cagrilar == []


def test_baska_modelin_vektorleri_kullanilmaz(tmp_path):
    depo = av.VektorDeposu(tmp_path)
    av.doldur([_parca(1, "Galaksi" + ANLAMLI)], depo, _ayar(model="eski-model"), gom=_sahte_gom())
    sonuc = av.doldur([_parca(1, "Galaksi" + ANLAMLI)], depo, _ayar(), gom=_sahte_gom())
    assert sonuc["yeni"] == 1 and depo.yukle()[2] == "bge-m3"


def test_dusen_dugum_atlanir_digerleri_bitirir(tmp_path):
    parcalar = [_parca(i, f"Yıldız {i}" + ANLAMLI) for i in range(30)]
    cagrilar = []
    sonuc = av.doldur(parcalar, av.VektorDeposu(tmp_path), _ayar(), gom=_sahte_gom(cagrilar, bozuk={"http://mbp"}))
    assert sonuc["vektorlu"] == 30 and sonuc["eksik"] == 0
    assert sonuc["hatalar"].get("http://mbp", 0) >= 1
    assert any(a == "http://pi" for a, _ in cagrilar)


def test_sure_dolunca_kalan_sonraki_turda_gomulur(tmp_path):
    saat = iter([0.0, 0.0] + [100.0] * 1000)
    parcalar = [_parca(i, f"Uyku {i}" + ANLAMLI) for i in range(40)]
    depo = av.VektorDeposu(tmp_path)
    sonuc = av.doldur(parcalar, depo, _ayar(sure=10.0), gom=_sahte_gom(), saat=lambda: next(saat))
    assert 0 < sonuc["vektorlu"] < 40 and sonuc["eksik"] == 40 - sonuc["vektorlu"]
    assert av.doldur(parcalar, depo, _ayar(sure=0), gom=_sahte_gom())["eksik"] == 0  # 0 = süresiz


def test_hicbir_dugum_yoksa_depo_bozulmaz(tmp_path):
    depo = av.VektorDeposu(tmp_path)
    av.doldur([_parca(1, "Galaksi" + ANLAMLI)], depo, _ayar(), gom=_sahte_gom())
    sonuc = av.doldur([_parca(1, "Galaksi" + ANLAMLI), _parca(2, "Kesir" + ANLAMLI)], depo, _ayar(),
                      gom=_sahte_gom(bozuk={"http://mbp", "http://pi"}))
    assert sonuc["vektorlu"] == 1 and sonuc["eksik"] == 1
    assert depo.yukle()[1].shape == (1, 8)


def test_soru_vektoru_sirayla_dener_hepsi_duserse_none(monkeypatch):
    import time
    # Warm-up is its own test; here it would race the call log.
    monkeypatch.setattr(av, "_son_isitma", {"http://hp": time.monotonic()})
    cagrilar = []
    v = av.sorgu_vektoru("galaksi", _ayar(sorgu_adresleri=("http://hp", "http://mbp")),
                         gom=_sahte_gom(cagrilar, bozuk={"http://hp"}))
    assert v is not None and abs(float(np.linalg.norm(v)) - 1.0) < 1e-5
    assert [a for a, _ in cagrilar] == ["http://hp", "http://mbp"]
    assert av.sorgu_vektoru("galaksi", _ayar(), gom=_sahte_gom(bozuk={"http://hp"})) is None


def test_kapaliyken_soru_gomulmez():
    assert av.sorgu_vektoru("galaksi", _ayar(acik=False), gom=lambda *a: pytest.fail("ağ")) is None


def test_rrf_agirligi_siralamayi_cevirir():
    bm25, vektor = [1, 2, 3], [3, 2, 1]
    assert set(av.rrf([(bm25, 1.0), (vektor, 1.0)])[:2]) == {1, 3}
    assert av.rrf([(bm25, 1.0), (vektor, 3.0)])[0] == 3
    assert av.rrf([(bm25, 1.0), (vektor, 0.0)])[:3] == [1, 2, 3]


def test_ayarlar_ortamdan(monkeypatch):
    for k in ("ASSISTANT_ENABLE_EMBEDDINGS", "ASSISTANT_EMBED_MODEL", "ASSISTANT_VEKTOR_AGIRLIGI"):
        monkeypatch.delenv(k, raising=False)
    a = av.ayarlar()
    assert a.acik is False and a.model == "bge-m3" and a.agirlik_ogrenci == 3.0 and a.agirlik_aile == 1.0
    assert a.sorgu_adresleri[0] == "http://127.0.0.1:11434"
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "1")
    monkeypatch.setenv("ASSISTANT_VEKTOR_AGIRLIGI", "2")
    monkeypatch.setenv("ASSISTANT_EMBED_TOPLU_URLS", "http://a:1/, http://b:2")
    a = av.ayarlar()
    assert a.acik and a.agirlik_ogrenci == 2.0 and a.toplu_adresleri == ("http://a:1", "http://b:2")


def test_ilk_dugum_soguksa_arka_planda_isitilir_ve_soru_bekletilmez(monkeypatch):
    """Canlı 2026-10-05: HP'de bge-m3 soğukken yükleme 4.4 sn sürdü, 2 sn'lik soru bekleyişi her
    seferinde kesti ve bütün aramalar mbp'ye düştü (medyan 2.3 sn). İlk düğüm düşünce o düğüm arka
    planda süresiz bir istekle ısıtılır; soru o arada sıradaki düğümden yanıtlanır."""
    isitma = []

    def gercek_gibi(adres, model, metinler, zaman_asimi):
        if zaman_asimi is None:
            isitma.append(adres)
            return [_vektor("x")]
        if adres == "http://hp":
            raise TimeoutError("soğuk")
        return [_vektor(m) for m in metinler]

    monkeypatch.setattr(av, "ollama_gom", gercek_gibi)
    monkeypatch.setattr(av, "_son_isitma", {})
    ayar = _ayar(sorgu_adresleri=("http://hp", "http://mbp"))
    assert av.sorgu_vektoru("galaksi", ayar) is not None
    av._isitma_bekle()
    assert isitma == ["http://hp"]
    assert av.sorgu_vektoru("galaksi", ayar) is not None
    av._isitma_bekle()
    assert isitma == ["http://hp"]  # aynı düğüm bir dakika içinde yeniden ısıtılmaz


def test_gomme_istegi_modeli_bellekte_tutar(monkeypatch):
    gonderilen = {}

    class Yanit:
        def raise_for_status(self):
            pass

        def json(self):
            return {"embeddings": [[0.1]]}

    def post(url, json=None, timeout=None):
        gonderilen.update(json)
        return Yanit()

    monkeypatch.setattr(av.requests, "post", post)
    monkeypatch.setattr(av, "ollama_gom", av._ollama_gom_gercek)
    av.ollama_gom("http://hp", "bge-m3", ["x"], 2.0)
    assert gonderilen["keep_alive"] == -1
