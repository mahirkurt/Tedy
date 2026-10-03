# Asistan değerlendirme ve sınav hazırlığı — B4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Öğretmen modu `alistirma_olustur` ile 3–10 soruluk bir alıştırma kurar; sunucu şemayı doğrular, soruları cevapsız bir `quiz` olayıyla gönderir ve puanı kendisi hesaplar. Cevaplar aynı sqlite günlüğüne yazılır. `ogrenme_gunlugu` zayıf konuları okur. Her skill'e `references/degerlendirme-rubrigi.md` konur. `calisma_degerlendir` yüklenen eki o rubriğe göre yapılandırılmış olarak günlüğe işler. Yaklaşan sınavın çalışma planı `sinavlar` satırından önerilir.

**Architecture:** Puanlama ve şema `src/assistant_alistirma.py` içindedir; Flask'a import etmez. Alıştırma satırı araç başarılı olunca yazılır, böylece kart akış bitmeden cevaplanabilir. Doğru cevap `GET` ile giden mesaj gövdesine konmaz. Günlük `output/assistant_sohbetler.sqlite` içindedir (B3'ün dosyası). `AssistantRuntime` bu dosyayı kurmaz. `sohbet_id` yoksa araç ilan edilmez ve dosya açılmaz. `/v1`, `/plan` ve API anahtarı bu dosyaya dokunmaz. İkinci bir model çağrısı yok (o çağrı B6'dadır).

**Tech Stack:** Python 3.12 (stdlib `sqlite3`, Flask), B3 `SohbetDeposu` bağlantı düzeni, B2 `EkDeposu.oku`, mevcut `turkce_kucult_katla`, React 19 + Carbon, Playwright + `@axe-core/playwright` + IBM Equal Access.

**Spec:** `docs/superpowers/specs/2026-09-28-asistan-ogretmen-modlari-design.md` — **§4**, "Hata ve boşluk durumları" ile "Test"in B4'e düşen maddeleri, §1'deki "B4'ten sonra `alistirma_olustur`" cümlesi ve `soru-kaliplari.md`'nin B4'ü beslemesi, ekteki **B4'e eklenenler**. B5 ve B6 yok. B2 ve B3 plan dosyaları değişmez.

Bu worktree'nin kodu `c5153d3` üzerindedir: `assistant_uploads.py` ve `assistant_sohbet.py` henüz yoktur. Görevler B2 ve B3 planlarının adlandırdığı sembolleri tüketir. İkisi uygulanmadan B4 uygulanmaz.

## Global Constraints

- **Worktree:** `/mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan`, dal `cursor/asistan-b2-plan-a843`. Ana checkout'a, `feat/asistan-ogretmen` worktree'sine, `feat/asistan-zengin`'e ve portal dallarına dokunma. `docs/superpowers/plans/2026-10-03-asistan-dosya-yukleme-b2.md` ve `docs/superpowers/plans/2026-10-03-asistan-sohbet-gecmisi-b3.md` değişmez.
- **Git:** dosyaları adıyla stage et. `git add -A` / `git add .` yok. Push yok.
- **Testler ücretli bir API'ye ya da ağa hiç gitmez.** `tests/conftest.py` `ANTHROPIC_API_KEY`'i siler. Playwright: `TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python DASHBOARD_SECRET_KEY=yalniz-test env -u ANTHROPIC_API_KEY npx playwright test <spec>`. Soru gönderen her e2e hem `**/api/assistant/stream` hem `**/api/assistant/chat` rotasını kendisi cevaplar.
- **Python:** yorumlayıcı `/mnt/thunderbolt/workspaces/TED/.venv/bin/python`. `DASHBOARD_SECRET_KEY=yalniz-test`. Gerçek `.env` bağlama. Yeni bağımlılık yok.
- **Pano:** `cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan/dashboard`. `node_modules` yoksa `npm ci`. Playwright'dan önce `npm run build`.
- **Renk:** elle hex yok, alfa yok, gradyan yok, `color-mix` yok. Yalnız mevcut `--cds-*` ve `--ted-*`.
- **Dil:** okura giden her yeni cümle Türkçe. Yol, istisna adı ve e-posta okura gitmez. Bu plan, spec'in yazmadığı okur cümlesini yazmaz.
- **Temel sistem bloğu her modda bayt bayt aynı kalır.** Yeni cümle öğretmen gövdesine girer, temel isteme değil.
- **Dağıtım bir plan görevi değildir.**
- **`sohbet_id` yoksa depo yok.** B3 kuralı durur. Bu araçlar depoyu kendileri açmaz.

## Açık kararlar

Spec bunları kapatmıyor. Görevler bunları doldurmaz.

1. **Seçenek sayısı.** §4 sunucunun "seçenek sayısı"nı doğrulamasını yazar, sayı vermez. Dört skill'in `soru-kaliplari.md` dosyası çoktan seçmeliyi "dört seçenek" diye anlatır; bu yazma kalıbıdır, şema sayısı değildir. Sunucu belirli bir uzunluğu reddetmez.
2. **Noktalama.** §4 kısa cevapta noktalama normalleştirmesi ister, silinecek karakterleri yazmaz. `1/2` içindeki `/` noktalama sayılırsa kesir `12` olur. Bu plan karakter silmez.
3. **Sayısal tolerans.** §4 "küçük tolerans" der, miktar ve mutlak/göreli ayrımı yoktur. Eşit olmayan iki sayı eşit sayılmaz. `kabul_edilenler` durur; toleransın yerine geçmesi için konmadı.
4. **Zorluk kademeleri.** Ek "üç zorluk kademesi" der, adları yazmaz. Sunucuda `zorluk` alanı yoktur. Skill metni ad uydurmaz.
5. **`kazanim_kodu`.** §4 alanı `kazanim_kodu?` diye işaretler. Ek "alıştırmalar kazanım kodu taşır" der. Sunucu boş kodu reddetmez.
6. **Doğru/yanlış sözcükleri.** `dogru_yanlis` için kabul edilen sözcük çifti yazılmamıştır. `dogru` boş olmayan bir dizgidir; "Doğru"/"Yanlış" zorunlu değildir.
7. **"Son denemeler".** Zayıf konu "son denemelerde" %60'ın altında ve en az 3 cevaptır. Pencerenin uzunluğu yok. Fonksiyon kendisine verilen satırların hepsini kullanır. Eski satırı atan bir kesim yoktur.
8. **Atıftan çalışılan konu.** §4, öğretmen modundaki cevapların atıflarından kazanım kodu ve kitap sayfası başlığı türetir, ek model çağrısı yoktur. Kayıtlı atıfın alanları `kind`, `label`, `locator`, `snippet`'tir; `kazanim_kodu` ve sayfa başlığı diye bir alan yoktur. Otomatik satır üreten görev yoktur.
9. **Boş günlüğün cümlesi.** "Hata ve boşluk durumları" boş günlüğün ne zaman dolacağını söylemesini ister, cümleyi yazmaz. Bölüm başlığı spec'tedir. Gövdeye cümle konmaz.
10. **Okur hata cümleleri.** Puanlama hatası "Türkçe bir cümle"dir; metin yok. Eksik alıştırma için de metin yok. Durum kodları kilitlidir. Test, `error` değerinin saklı `dogru` cevabını, yol ve istisna adı içermediğini ölçer; sözcükleri ölçmez.
11. **Hafta.** İlerleme bölümü "haftalık ders ders sohbet sayısı" ister. Haftanın hangi günde bittiği yazılmaz. Bu sayı yanıtta yoktur.
12. **Rubrik ölçütleri.** Ek, dosyayı, "not vermez" kuralını ve dört dersin odağını yazar. Ölçüt cümlelerini ve düzey adlarını yazmaz. Dosyaya ölçüt satırı uydurulmaz.
13. **Yanlış analizi.** Ek, yanlış cevabı `kavram-yanilgilari.md` başlığına eşler, kuralı yazmaz. Eşleyen görev yoktur.
14. **Aile.** Günlüğü "Işık kendisininkini görür" diye sınırlar. Ailenin günlüğü görmesi, Işık'ın ekini `calisma_degerlendir` ile değerlendirmesi yazılmaz. Aile `oku` düşümü bu araçta yoktur. Başkasının eki bulunamaz.
15. **İki hitap metni.** Ek, Işık'a cesaretlendirici, aileye aynı içeriği "siz" ile ister. İki metnin ayrı kolonlarda durması yazılmaz. Günlük, aracı çağıran okurun tek metnini saklar. İkinci metin üretilmez. Sohbetteki hitap bugünkü sistem istemindedir.

## Kilitlenen adlar

| Ad | Değer | Neden |
|---|---|---|
| Dosya | `output/assistant_sohbetler.sqlite` | §4: olaylar aynı SQLite'ta. B3'ün dosyası. |
| Bağlantı | B3 `SohbetDeposu._baglan` | Yeni bağlantı düzeni yok. |
| `alistirma` | `id, sohbet_id, mesaj_id, sahip_email, ogretmen, baslik, ders, konu, kazanim_kodu, sorular_json, zaman` | §4 saklar. `mesaj_id` cevap satırı yazılınca dolar; araç daha önce çalışır. |
| `alistirma_cevap` | `id, alistirma_id, sira, ders, konu, kazanim_kodu, dogru, zaman`. `UNIQUE (alistirma_id, sira)` | §4: soru bazında ders, konu, kazanım kodu, doğru mu. |
| `calisma_degerlendirme` | `id, sohbet_id, ek_id, ogretmen, guclu_yanlar, duzeyler, sonraki_adim, okur, zaman` | Ek: güçlü yanlar, düzeyler, tek sonraki adım. Sayısal not kolonu yok. |
| Kimlik | `uuid.uuid4().hex`, `^[0-9a-f]{32}$` | B3 ile aynı biçim. |
| Zaman | UTC `YYYY-MM-DDTHH:MM:SSZ` | B3 `zaman_yazi`. |
| `sira` | `sorular` içinde 1'den başlayan konum | Şemada soru kimliği yok. Liste sıralıdır. |
| Soru sayısı | 3–10, sınırlar dahil | §4. |
| Tür | `coktan_secmeli`, `dogru_yanlis`, `kisa_cevap` | §4. `soru-kaliplari.md` içindeki `acik_uclu` bu üçlüde yoktur; araç onu reddeder. |
| `quiz` | SSE olayı. `dogru`, `kabul_edilenler`, `aciklama` yok | §4: sorular cevapsız gider. Açıklama puanlayınca döner. |
| Puanlama | `turkce_kucult_katla`, sonra `split()` ile tek boşluk | §4'ün yazdığı iki işlem. Noktalama ve tolerans açık karar 2 ve 3. |
| %60 | `dogru * 5 < toplam * 3`, ve `toplam >= 3` | "Altında": 3/5 zayıf değildir. 1/3 zayıftır. İki yanlış zayıf değildir. |
| Grup | `(konu, kazanim_kodu)` çifti | Satırın taşıdığı iki alan. Başka eşleme yok. |
| Cevap ucu | `POST /api/assistant/alistirmalar/<id>/cevap` | §4. Gövde `{sira, cevap}`. Dönüş `{dogru, aciklama}`. |
| Günlük ucu | `GET /api/assistant/ogrenme-gunlugu` | Spec yol yazmaz. Diğer asistan uçlarının yanındadır. Yalnız çağıranın satırları. |
| Yazma | Yalnız alıştırmanın `sahip_email`'i | B3: yazma sahibine. Aile 403, cümle B3'ün cümlesidir: `Bu sohbet salt okunur.` |
| İkinci cevap | Aynı `(alistirma_id, sira)` yeni satır yazmaz; ilk sonucu döner | Spec yeniden denemeyi yazmaz. |
| Araçlar | `alistirma_olustur`, `ogrenme_gunlugu`, `calisma_degerlendir` | §4 ve ek. `ogrenme_gunlugu` ile `calisma_degerlendir` yalnız `ogretmen != genel` ve `not_deposu` varken ilan edilir. |
| Rubrik | `references/degerlendirme-rubrigi.md` | Ek. `ZORUNLU_KAYNAKLAR`'a eklenir. |
| Sınav planı | `sinavlar` metnindeki yaklaşan satır: ders, tür, tarih | `sinavlar_metni` konu alanı taşımaz. Yeni araç yok. |
| Kart düğmesi | `Yanlışlarımı anlat` | §4. Kaçırılan soruların `soru` metinlerini yeni kullanıcı mesajı yapar. |
| Bölüm | İlerleme sayfası (`dashboard/src/components/PlatformProgress.tsx`) başlığı `Öğrenme günlüğü` | §4. Yeni rota yok. |
| `/v1`, `/plan` | Depo açmaz, bu üç aracı ilan etmez | B3 kuralı. |

Okur cümleleri (spec'te yazılanlar):

| Durum | Metin |
|---|---|
| Kartın sonu | `Puan` — yanında doğru sayısı ve soru sayısı |
| Geri bildirim | `Doğru` ya da `Yanlış`, sonra saklı `aciklama` |
| Düğme | `Yanlışlarımı anlat` |
| Bölüm | `Öğrenme günlüğü` |
| Aile kartta yazarsa | `Bu sohbet salt okunur.` |

Bilinmeyen öğretmen B1 cümlesidir: `Bilinmeyen öğretmen modu.`

## File Structure

| Dosya | Durum | Sorumluluk |
|---|---|---|
| `src/assistant_alistirma.py` | yeni | Şema, normalleştirme, zayıf konu |
| `tests/test_assistant_alistirma.py` | yeni | Şema, katlama, %60 |
| `src/assistant_sohbet.py` | değişir | Üç tablo ve metotlar (B3 dosyası) |
| `src/dashboard_api.py` | değişir | Cevap ucu, günlük ucu, `quiz` sonrası `mesaj_id` |
| `src/assistant_tools.py` | değişir | Üç araç |
| `src/assistant_skills.py` | değişir | `ZORUNLU_KAYNAKLAR` |
| `tests/skill_ornegi.py` | değişir | Örnek skill dördüncü dosyayı yazar |
| `src/assistant_skills/*/references/degerlendirme-rubrigi.md` | yeni | Dört ders |
| `src/assistant_skills/*/SKILL.md` | değişir | `alistirma_olustur` ve `sinavlar` cümlesi |
| `tests/test_assistant_alistirma_api.py` | yeni | Sahip, cevapsız GET, ikinci cevap |
| `dashboard/src/components/AssistantChat.tsx` / `.scss` | değişir | Kart |
| `dashboard/src/components/PlatformProgress.tsx` | değişir | Bölüm |
| `dashboard/tests/e2e/asistan-alistirma.spec.ts` | yeni | Kart, düğme, boş bölüm |
| `CLAUDE.md` | değişir | B4 maddesi |

---

### Task 1: Şema, katlama, zayıf konu

**Files:**
- Create: `src/assistant_alistirma.py`
- Test: `tests/test_assistant_alistirma.py`

**Interfaces:**
- Consumes: `turkce_kucult_katla`.
- Produces: `alistirma_hata(govde) -> str | None`, `cevap_dogru(verilen, dogru, kabul) -> bool`, `zayif_konular(satirlar) -> list[dict]`.

- [ ] **Step 1: Test**

`tests/test_assistant_alistirma.py`:

```python
"""Alıştırma şeması ve puan (spec §4). Ağ yok."""
from src.assistant_alistirma import alistirma_hata, cevap_dogru, zayif_konular


def _soru(**fazla):
    temel = {
        "tur": "kisa_cevap",
        "soru": "1/2 + 1/3",
        "dogru": "5/6",
        "aciklama": "Paydalar eşitlenir.",
    }
    temel.update(fazla)
    return temel


def _govde(sorular):
    return {"baslik": "Payda", "ders": "Matematik", "konu": "Rasyonel sayılar",
            "sorular": sorular}


def test_uc_soru_kabul_kod_zorunlu_degil():
    assert alistirma_hata(_govde([_soru(), _soru(), _soru()])) is None


def test_iki_ve_on_bir_red():
    assert alistirma_hata(_govde([_soru(), _soru()])) is not None
    assert alistirma_hata(_govde([_soru() for _ in range(11)])) is not None


def test_bos_aciklama_ve_yanlis_tur():
    assert alistirma_hata(_govde([_soru(aciklama="  "), _soru(), _soru()])) is not None
    assert alistirma_hata(_govde([_soru(tur="acik_uclu"), _soru(), _soru()])) is not None


def test_secenek_disi_dogru_red_uzunluk_serbest():
    soru = _soru(tur="coktan_secmeli", secenekler=["5/6", "2/5"], dogru="1/2")
    assert alistirma_hata(_govde([soru, _soru(), _soru()])) is not None
    ikili = _soru(tur="coktan_secmeli", secenekler=["5/6", "2/5"], dogru="5/6")
    assert alistirma_hata(_govde([ikili, _soru(), _soru()])) is None


def test_katlama_ve_bosluk():
    assert cevap_dogru("  Beş   bölü  ALTI ", "beş bölü altı", None) is True
    assert cevap_dogru("İstanbul", "istanbul", None) is True
    assert cevap_dogru("1/2", "1/2", None) is True
    assert cevap_dogru("0,5", "1/2", None) is False
    assert cevap_dogru("0,5", "1/2", ["0,5"]) is True


def test_zayif_sinir():
    # 1/3 altındadır. 3/5 eşitlik altında değildir. 2 cevap yetmez.
    satirlar = [{"konu": "Kesir", "kazanim_kodu": "MAT.7.1.1", "dogru": i == 0} for i in range(3)]
    satirlar += [{"konu": "Oran", "kazanim_kodu": "MAT.7.1.5", "dogru": i < 3} for i in range(5)]
    satirlar += [{"konu": "Denklem", "kazanim_kodu": "", "dogru": False} for _ in range(2)]
    zayif = {(z["konu"], z["kazanim_kodu"]) for z in zayif_konular(satirlar)}
    assert ("Kesir", "MAT.7.1.1") in zayif
    assert ("Oran", "MAT.7.1.5") not in zayif
    assert ("Denklem", "") not in zayif
```

`cevap_dogru` içindeki `"İstanbul"` / `"istanbul"` çifti `turkce_kucult_katla`'nın mevcut sözleşmesidir (`tests/test_assistant_indeks_hijyeni.py`).

- [ ] **Step 2: FAIL**

`cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan && DASHBOARD_SECRET_KEY=yalniz-test /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest tests/test_assistant_alistirma.py -q -p no:cacheprovider`

Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Uygula**

`alistirma_hata` model içindir; okura gitmez. Eksik `baslik`/`ders`/`konu`, `sorular` 3–10 değil, `tur` üçlüden değil, `soru` ya da `aciklama` strip sonrası boş, `dogru` strip sonrası boş ise hata döner. `coktan_secmeli` için `secenekler` boş olmayan dizgilerden oluşan bir liste değilse, ya da `dogru` o listede birebir yoksa hata döner. Uzunluk eşiği yoktur. `dogru_yanlis` ve `kisa_cevap` için `secenekler` varsa ve `dogru` listedeyse bu bir hata değildir; yoksa da değildir. `kabul_edilenler` varsa boş olmayan dizgilerdir. `kazanim_kodu` yoksa, `None` ise ya da strip sonrası boş dizgiyse kabul edilir. `kaynak` varsa dizgidir; içeriği denetlenmez.

`_norm`: `turkce_kucult_katla`, sonra `" ".join(metin.split())`. Başka karakter silinmez. `cevap_dogru`, `dogru` ve `kabul_edilenler` içinde `_norm` eşitliği arar. İki taraf da boşsa eşit değildir.

`zayif_konular`: satırları `(konu, kazanim_kodu)` ile gruplar. `kazanim_kodu` yoksa `""`. Grupta `toplam < 3` ise yok. `dogru * 5 < toplam * 3` ise `{konu, kazanim_kodu, dogru, toplam}` döner. Sıra: `toplam` azalan, sonra konu, sonra kod.

- [ ] **Step 4: PASS**

Aynı pytest. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/assistant_alistirma.py tests/test_assistant_alistirma.py
git commit -m "feat: alıştırma şemasını ve puanı ekle"
```

---

### Task 2: Günlük satırları ve cevap ucu

**Files:**
- Modify: `src/assistant_sohbet.py`
- Modify: `src/dashboard_api.py`
- Test: `tests/test_assistant_alistirma_api.py`

**Interfaces:**
- Consumes: `SohbetDeposu`, `_sohbet_erisim`, `_require_assistant_access`, `_asistan_simdi`, `OUTPUT_DIR`.
- Produces: `alistirma_yaz`, `alistirma_getir`, `alistirma_bagla`, `cevap_yaz`, `cevaplar`, `degerlendirme_yaz`, `gunluk`. `POST /api/assistant/alistirmalar/<id>/cevap`, `GET /api/assistant/ogrenme-gunlugu`.

- [ ] **Step 1: Test**

Saat ve giriş, B3 `tests/test_assistant_sohbet_api.py` kalıbıdır. `ISIK`, `AILE` aynı adresler. `SIMDI = datetime(2026, 10, 3, 8, 0, tzinfo=timezone.utc)`.

```python
def test_cevap_sahibe_aciklama_verir_ikinci_kez_yazmaz(istemci):
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    depo = _sohbet_deposu()
    aid = depo.alistirma_yaz(
        sid, ISIK, "matematik", "Payda", "Matematik", "Kesir", None,
        [_soru(), _soru(), _soru()], SIMDI)
    bir = istemci.post(f"/api/assistant/alistirmalar/{aid}/cevap",
                       json={"sira": 1, "cevap": "5/6"})
    assert bir.status_code == 200
    assert bir.get_json()["dogru"] is True
    assert bir.get_json()["aciklama"] == "Paydalar eşitlenir."
    iki = istemci.post(f"/api/assistant/alistirmalar/{aid}/cevap",
                       json={"sira": 1, "cevap": "2/5"})
    assert iki.status_code == 200
    assert iki.get_json()["dogru"] is True
    assert len(depo.cevaplar(ISIK)) == 1


def test_get_cevap_sizdirmaz(istemci):
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    depo = _sohbet_deposu()
    aid = depo.alistirma_yaz(
        sid, ISIK, "matematik", "Payda", "Matematik", "Kesir", "MAT.7.1.1",
        [_soru(), _soru(), _soru()], SIMDI)
    mid = depo.mesaj_ekle(sid, "assistant", "anlattım", "matematik", [], SIMDI)
    depo.alistirma_bagla(aid, mid)
    govde = istemci.get(f"/api/assistant/sohbetler/{sid}").get_json()
    metin = str(govde)
    assert "5/6" not in metin
    assert "Paydalar eşitlenir." not in metin
    assert aid in metin


def test_aile_yazamaz_yok_cevap_vermez(istemci):
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    aid = _sohbet_deposu().alistirma_yaz(
        sid, ISIK, "matematik", "Payda", "Matematik", "Kesir", None,
        [_soru(), _soru(), _soru()], SIMDI)
    _giris(istemci, AILE)
    yaz = istemci.post(f"/api/assistant/alistirmalar/{aid}/cevap",
                       json={"sira": 1, "cevap": "5/6"})
    assert yaz.status_code == 403
    assert yaz.get_json()["error"] == "Bu sohbet salt okunur."
    assert "5/6" not in str(yaz.get_json())
    yok = istemci.post("/api/assistant/alistirmalar/" + "ab" * 16 + "/cevap",
                       json={"sira": 1, "cevap": "5/6"})
    assert yok.status_code == 404
    assert "5/6" not in str(yok.get_json())
```

`_soru` görev 1'deki gövdedir. Günlük testi: üç cevabın biri doğruysa `GET /api/assistant/ogrenme-gunlugu` içinde `zayif` listesinde `("Kesir", "")` ya da yazılan kod vardır; `hafta` anahtarı yoktur. Başka kullanıcının satırı dönmez.

- [ ] **Step 2: FAIL**

`tests/test_assistant_alistirma_api.py`. Expected: FAIL.

- [ ] **Step 3: Uygula**

Tablolar `SohbetDeposu` kuruluşundaki `_SEM` betiğine eklenir. `alistirma_yaz` `BEGIN IMMEDIATE` ile satır koyar, `mesaj_id` NULL başlar, kimliği döner. `sorular_json` aracın doğrulanmış listesidir. `alistirma_bagla` yalnız `mesaj_id`'yi yazar. `cevap_yaz` aynı `(alistirma_id, sira)` varsa yeni satır koymaz, eskisini döner.

`POST`: `_require_assistant_access`. Kimlik biçimi bozuksa 404. Satır yoksa 404. `sahip_email` çağıran değilse 403 `Bu sohbet salt okunur.` `sira` 1..n değilse ya da `cevap` strip sonrası boşsa 400. 400 ve 404 gövdesi `{"error": ...}` olur; değer saklı `dogru`, `kabul_edilenler`, yol ve istisna adı içermez. Sözcükler açık karar 10'dadır; bu plan onları seçmez. 200'de `cevap_dogru` ve o sorunun `aciklama`'sı. Günlük satırının `ders`, `konu`, `kazanim_kodu` alanları alıştırma satırından kopyalanır. `dogru` 1 ya da 0.

`GET /api/assistant/sohbetler/<id>`: mesaj `meta_json` içinde `alistirma_id` varsa yanıta `alistirma` eklenir: `id`, `baslik`, `ders`, `konu`, `kazanim_kodu`, `sorular`. Her soruda yalnız `tur`, `soru` ve varsa `secenekler`. `dogru`, `kabul_edilenler`, `aciklama` yok.

`GET /api/assistant/ogrenme-gunlugu`: çağıranın `alistirma_cevap` satırları ve `calisma_degerlendirme` satırları. `zayif` = `zayif_konular`. `hafta` anahtarı konmaz. Okur rolü 403, B3 kapısı.

- [ ] **Step 4: PASS**

Aynı pytest, artı `tests/test_assistant_sohbet_api.py`. Expected: PASS. `sohbet_id`'siz öğretmen testleri 200 kalır.

- [ ] **Step 5: Commit**

```bash
git add src/assistant_sohbet.py src/dashboard_api.py tests/test_assistant_alistirma_api.py
git commit -m "feat: alıştırma cevabını günlüğe yaz"
```

---

### Task 3: Araçlar, quiz olayı, rubrik

**Files:**
- Modify: `src/assistant_tools.py`, `src/assistant_skills.py`, `tests/skill_ornegi.py`
- Modify: dört `src/assistant_skills/<ad>/SKILL.md`
- Create: dört `references/degerlendirme-rubrigi.md`
- Test: `tests/test_assistant_alistirma.py` (araç), `tests/test_assistant_skills.py`

**Interfaces:**
- Consumes: `alistirma_hata`, `Skill.kaynak_oku`, `EkDeposu.oku`, `not_deposu`, `sohbet_id`, `okur`, `ogretmen`.
- Produces: üç aracın ilanı ve `olay` alanı `quiz`.

- [ ] **Step 1: Test**

Rubrik dosyası olmayan örnek skill `tests/skill_ornegi.py` üzerinden yüklenince `SkillHatasi` ve ileti `degerlendirme-rubrigi.md` içerir. Dört gerçek skill yüklenir; `kaynak_oku("degerlendirme-rubrigi.md")` boş değildir ve `not vermez` dizgisini içerir. Dosyada uydurulmuş düzey adı aranmaz.

Araç, depo tmp, `sohbet_id` dolu:

- `alistirma_olustur` geçerli gövdeyle `ok` True. `olay["event"] == "quiz"`. `olay` içinde `dogru` ve `aciklama` anahtarları yoktur. Satır depodadır.
- İki soruluk gövde `ok` False, satır yok.
- `sohbet_id` `""` iken `ok` False, sqlite dosyası yok.
- `ogrenme_gunlugu` `ogretmen="genel"` iken ilan edilmez.
- `calisma_degerlendir` çağıranın kendi ekiyle satır yazar. `not` diye bir kolon yazılmaz. Başkasının ek kimliği `ok` False, satır yok. `ogretmen="genel"` iken `ok` False.

`quiz` olayı `chat_events` kuyruğuna B3'ün `mode_suggestion` yolu ile girer: `outcome.olay`. Aynı yanıtta ikinci `quiz`, mevcut `yayinlanan_olaylar` kümesi yüzünden akışa ikinci kez konmaz. Araç yine de ikinci satırı yazar. Bu küme bu planda değiştirilmez.

- [ ] **Step 2: FAIL**

`tests/test_assistant_skills.py` ve `tests/test_assistant_alistirma.py`. Expected: FAIL.

- [ ] **Step 3: Uygula**

`ZORUNLU_KAYNAKLAR`'a `"degerlendirme-rubrigi.md"` eklenir. `tests/skill_ornegi.py` `KAYNAKLAR` aynı dosyayı boş olmayan bir metinle yazar. Gerçek dört dosyanın tamamı şudur; ders odağı satırı değişir:

```markdown
# Değerlendirme rubriği

Maarif ölçme-değerlendirme anlayışı: süreç odaklıdır, not vermez. Ölçütler ve düzey betimleri programın kazanım ve süreç bileşeni dilindendir.

Bu dersin odağı: çözüm yolu ve gösterim.
```

Odak satırları, ekteki dörtlüden:

| Skill | Odak |
|---|---|
| `turkce` | yazma ve okuma-anlama |
| `matematik` | çözüm yolu ve gösterim |
| `fen` | deney tasarımı ve bilimsel açıklama |
| `sosyal` | kaynak ve kanıt kullanımı, neden-sonuç |

Başka satır yok.

Dört `SKILL.md` gövdesinde `##` sırası değişmez. `## Ders akışı` 4. adımının sonuna aynı cümle eklenir: `Kartlı alıştırma alistirma_olustur ile kurulur.` `## Araç kullanımı` bölümünün sonuna aynı paragraf eklenir: `Yaklaşan sınav sinavlar listesindedir. Satırda ders, tür ve tarih vardır; ayrı bir konu alanı yoktur. Konu uydurma. Çalışma planını bu satırdaki derse göre kur ve alıştırmayı alistirma_olustur ile ver.` Kademe adı yazılmaz.

`declarations`: `not_deposu is None` ise üç araç da yoktur. `alistirma_olustur` genel modda da vardır. Diğer ikisi `ogretmen != "genel"` ve skill'in `degerlendirme-rubrigi.md` kaynağı varken vardır.

`alistirma_olustur` argümanı §4'ün nesnesidir. `alistirma_hata` doluysa `ok` False ve depo yazılmaz. Değilse `alistirma_yaz`. `olay`:

```python
{"event": "quiz", "id": aid, "baslik": baslik, "ders": ders, "konu": konu,
 "kazanim_kodu": kod or None,
 "sorular": [{"tur": s["tur"], "soru": s["soru"], **({"secenekler": s["secenekler"]} if "secenekler" in s else {})}
             for s in sorular]}
```

Araç metni modele kimliği söyler. Okura giden akış `olay`'dır.

`ogrenme_gunlugu` argümansızdır. Metin, çağıranın cevap satırları ile `zayif_konular` çıktısıdır. Yeni bir karakter tavanı yazılmaz; mevcut `TOOL_RESULT_SINIRI` durur. Öneri cümlesini araç uydurmaz; listeyi modele verir.

`calisma_degerlendir` argümanları: `ek` (32 hex), `guclu_yanlar`, `duzeyler`, `sonraki_adim`. Üçü de strip sonrası boş değil. `EkDeposu.oku` yalnız çağıranın adresine bakar; `None` ise `ok` False ve satır yok. Sayısal not alanı argümanda aranmaz ve saklanmaz. Satır `degerlendirme_yaz`. Model çağrısı yok. OCR yok.

Cevap satırı B3'te `answer` olayından sonra yazılır. O yazının `meta_json` değeri, bu yanıtta üretilen alıştırma kimliklerini `{"alistirma_id": ["..."]}` olarak taşır. Yazımdan sonra `alistirma_bagla`. Akış yarıda kalırsa B3 asistan satırı yazmaz; alıştırma satırı durur, `mesaj_id` NULL kalır. Bu plan onu silmez.

- [ ] **Step 4: PASS**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan
DASHBOARD_SECRET_KEY=yalniz-test /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest \
  tests/test_assistant_alistirma.py tests/test_assistant_skills.py \
  tests/test_assistant_ogretmen_modu.py \
  -q -p no:cacheprovider
```

Expected: PASS. İki modun temel sistem bloğu bayt bayt aynı kalır.

- [ ] **Step 5: Commit**

```bash
git add src/assistant_tools.py src/assistant_skills.py tests/skill_ornegi.py \
  src/assistant_skills/turkce/SKILL.md src/assistant_skills/turkce/references/degerlendirme-rubrigi.md \
  src/assistant_skills/matematik/SKILL.md src/assistant_skills/matematik/references/degerlendirme-rubrigi.md \
  src/assistant_skills/fen/SKILL.md src/assistant_skills/fen/references/degerlendirme-rubrigi.md \
  src/assistant_skills/sosyal/SKILL.md src/assistant_skills/sosyal/references/degerlendirme-rubrigi.md \
  tests/test_assistant_alistirma.py
git commit -m "feat: alıştırma aracını ve rubriği bağla"
```

---

### Task 4: Kart ve öğrenme günlüğü bölümü

**Files:**
- Modify: `dashboard/src/components/AssistantChat.tsx`
- Modify: `dashboard/src/components/AssistantChat.scss`
- Modify: `dashboard/src/components/PlatformProgress.tsx`
- Create: `dashboard/tests/e2e/asistan-alistirma.spec.ts`

**Interfaces:**
- Consumes: SSE `quiz`, `POST /api/assistant/alistirmalar/<id>/cevap`, `GET /api/assistant/ogrenme-gunlugu`, B3 salt okuma.
- Produces: kart ve İlerleme bölümü.

- [ ] **Step 1: e2e**

`dashboard/tests/e2e/asistan-alistirma.spec.ts`. Akış `sabitAc` ile kesilir; bu test `page.route` ile `**/api/assistant/stream` yolunu kendi `quiz` ve `answer` olaylarına bağlar. `/chat` sayacı 0.

Olay:

```text
event: quiz
data: {"id":"ab0123456789ab0123456789ab012345","baslik":"Payda","ders":"Matematik","konu":"Kesir","sorular":[{"tur":"kisa_cevap","soru":"1/2 + 1/3 kaçtır?"}]}

event: answer
data: {"answer":"Paydaları eşitledim.","citations":[]}
```

Kimlik 32 hex'tir. `dogru` ve `aciklama` bu olayda yoktur.

`POST` 200 `{"dogru": true, "aciklama": "Paydalar eşitlenir."}` döner. Kartta önce yalnız soru görünür. Cevap yazılınca `Doğru` ve açıklama görünür. Üç soruluk bir kartta üçüncü cevapdan sonra `Puan` görünür. Bir yanlış varsa `Yanlışlarımı anlat` görünür; basılınca giden kullanıcı mesajı kaçırılan sorunun `soru` metnini içerir ve `sohbet_id` taşır.

Salt okuma sohbetinde kartın yazma alanı `disabled` olur ve `Bu sohbet salt okunur.` durur.

İlerleme: `GET /api/assistant/ogrenme-gunlugu` 200 `{"zayif":[{"konu":"Kesir","kazanim_kodu":"MAT.7.1.1","dogru":1,"toplam":3}],"cevaplar":[],"degerlendirmeler":[]}` iken başlık `Öğrenme günlüğü` ve `Kesir` görünür. Aynı uç 200 `{"zayif":[],"cevaplar":[],"degerlendirmeler":[]}` iken başlık görünür; bu planın yazmadığı bir boş-gövde cümlesi yoktur. 403'te bölüm yoktur.

Axe + IBM, B3 `asistan-sohbet.spec.ts` süzgeci: `aria_id_unique` ve `cds--ai-label|cds--toggletip` ihlal sayılmaz.

- [ ] **Step 2: FAIL**

`cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan/dashboard && npm run build && TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python DASHBOARD_SECRET_KEY=yalniz-test env -u ANTHROPIC_API_KEY npx playwright test asistan-alistirma.spec.ts`

Expected: FAIL, `Öğrenme günlüğü` yok.

- [ ] **Step 3: Arayüz**

Kart `quiz` olayındaki sırayı korur. Ekranda bir soru vardır. Gönder `POST` ile `{sira, cevap}` gider; `sira` 1'den başlar. Dönüş `Doğru` ya da `Yanlış`, altıda `aciklama`. Son sorudan sonra `Puan` ve iki sayı: doğru sayısı, soru sayısı. Yüzde yazılmaz.

`Yanlışlarımı anlat` yalnız en az bir yanlış varken görünür. Gövde, kaçırılan soruların `soru` dizgeleridir; araya başka cümle konmaz. Gönderim B3'ün `{sohbet_id, ogretmen, messages:[{role:'user', content}]}` gövdesidir.

Salt okunur sohbette kart yazılmaz. 403'ün cümlesi B3 cümlesidir.

İlerleme bölümü `PlatformProgress` içinde, platform akordeonunun üstünde, başlık `Öğrenme günlüğü`. `credentials: 'include'`. 403'te bölüm render edilmez. Dolu `zayif` satırı konu adını gösterir. Boş listede başlık kalır, gövdeye cümle eklenmez (açık karar 9). Haftalık sohbet sayısı çizilmez (açık karar 11).

Renk token'ları mevcut `--cds-*` ve `--ted-*`. Yeni hex yok.

- [ ] **Step 4: PASS**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan/dashboard
npm run lint
npm run build
TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python DASHBOARD_SECRET_KEY=yalniz-test env -u ANTHROPIC_API_KEY npx playwright test asistan-alistirma.spec.ts
```

Expected: lint, build ve Playwright 0.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/AssistantChat.tsx dashboard/src/components/AssistantChat.scss \
  dashboard/src/components/PlatformProgress.tsx \
  dashboard/tests/e2e/asistan-alistirma.spec.ts
git commit -m "feat: alıştırma kartını ve öğrenme günlüğünü ekle"
```

---

### Task 5: CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`, B3 maddesinin hemen altı. B3 maddesi `- **Asistan sohbet geçmişi (B3)**` ile başlar.

- [ ] **Step 1: Madde**

```markdown
- **Asistan değerlendirme ve sınav hazırlığı (B4)** (spec §4, ek "B4'e eklenenler", plan `docs/superpowers/plans/2026-10-03-asistan-degerlendirme-sinav-hazirligi-b4.md`): `alistirma_olustur` validates 3–10 questions and stores them in `assistant_sohbetler.sqlite`. SSE `quiz` omits `dogru`, `kabul_edilenler` and `aciklama`. `POST /api/assistant/alistirmalar/<id>/cevap` scores with `turkce_kucult_katla` and whitespace collapse; the owner writes, family gets `Bu sohbet salt okunur.` `ogrenme_gunlugu` and `GET /api/assistant/ogrenme-gunlugu` read that owner's rows. A topic is weak when `dogru * 5 < toplam * 3` and `toplam >= 3`. Each skill has `references/degerlendirme-rubrigi.md` (process, no grade, subject focus only). `calisma_degerlendir` stores strengths, levels and one next step for the caller's own upload; no second model call. Upcoming-exam study plans use the `sinavlar` line (course, kind, date). No `sohbet_id` means the tools are not declared and the file is not opened. `/v1` and `/plan` do not open it.
```

- [ ] **Step 2: Son kapı**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan
DASHBOARD_SECRET_KEY=yalniz-test /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest \
  tests/test_assistant_alistirma.py tests/test_assistant_alistirma_api.py \
  tests/test_assistant_skills.py \
  -q -p no:cacheprovider
git diff --check -- CLAUDE.md docs/superpowers/plans/2026-10-03-asistan-degerlendirme-sinav-hazirligi-b4.md
cd dashboard && npm run lint && npm run build
TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python DASHBOARD_SECRET_KEY=yalniz-test env -u ANTHROPIC_API_KEY npx playwright test asistan-alistirma.spec.ts
```

Expected: pytest `0 failed`, `git diff --check` boş, lint, build ve Playwright 0.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: asistan değerlendirme planını CLAUDE.md'ye yaz"
```

## Kapsam denetimi

| Spec | Görev |
|---|---|
| `alistirma_olustur` şeması, 3–10, üç tür, boş açıklama yok, doğru seçeneklerin içinde | 1, 3 |
| Seçenek sayısının belirli bir eşiği | açık karar 1 |
| SSE `quiz` cevapsız | 3 |
| Puanlama: katlama, boşluk | 1, 2 |
| Noktalama silme, sayısal tolerans | açık karar 2, 3 |
| Kart: tek tek, anında geri bildirim, puan, `Yanlışlarımı anlat` | 4 |
| Alıştırma mesajın parçası (`meta_json` kimliği, sırlar GET'te yok) | 2, 3 |
| Günlük: soru bazında ders, konu, kazanım, doğru mu | 2 |
| Atıftan çalışılan konu | açık karar 8 |
| Zayıf konu %60 altı, en az 3 | 1, 2 |
| "Son denemeler" penceresi | açık karar 7 |
| `ogrenme_gunlugu` | 3 |
| İlerleme bölümü, Işık kendi satırını görür | 2, 4 |
| Boş günlük cümlesi | açık karar 9 |
| Haftalık sohbet sayısı | açık karar 11 |
| Dört rubrik dosyası, not vermez, ders odağı | 3 |
| Ölçüt ve düzey adları | açık karar 12 |
| `calisma_degerlendir`, kendi eki, yapılandırılmış çıktı, günlüğe | 2, 3 |
| Işık / aile hitabının iki saklı metni | açık karar 15 |
| Üç zorluk kademesinin adları | açık karar 4 |
| `kazanim_kodu` zorunluluğu | açık karar 5 |
| Yanlışın kataloğa eşlenmesi | açık karar 13 |
| `sinavlar` satırından çalışma planı, konu uydurulmaz | 3 |
| Okur hata cümlelerinin metni | açık karar 10 |
| Aile günlüğü ve ailenin Işık ekini değerlendirmesi | açık karar 14 |
| `/v1`, `/plan`, `sohbet_id` yok | 3 |
| B5, B6 | yok |
