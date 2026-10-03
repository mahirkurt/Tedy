# Asistan değerlendirme ve sınav hazırlığı — B4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Öğretmen modu `alistirma_olustur` ile 3–10 soruluk bir alıştırma kurar; sunucu şemayı doğrular, soruları cevapsız bir `quiz` olayıyla gönderir ve puanı kendisi hesaplar. Cevaplar aynı sqlite günlüğüne yazılır. `ogrenme_gunlugu` zayıf konuları okur. Her skill'e `references/degerlendirme-rubrigi.md` konur. `calisma_degerlendir` yüklenen eki o rubriğe göre yapılandırılmış olarak günlüğe işler. Yaklaşan sınavın çalışma planı `sinavlar` satırındaki ders ve konulardan önerilir. Spec'in sayı vermediği davranışlar aşağıdaki seçimlerle kilitlidir; görevler o değerleri kullanır.

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

## Kilitlenen seçimler

Spec bu davranışları ister, sayı ya da ad vermez. Görevler aşağıdaki değeri kullanır.

| Seçim | Değer |
|---|---|
| Seçenek sayısı | `SECENEK_SAYISI = 4`. `coktan_secmeli` tam dört boş olmayan dizgi ister. `dogru` listede birebir durmalıdır. Üç ya da beş reddedilir. |
| Noktalama | Sıra: `turkce_kucult_katla`, sonra noktalama, sonra `" ".join(metin.split())`. Unicode kategorisi `P` ile başlayan karakter silinir. `/` hiç silinmez. `-` sonraki karakter basamaksa kalır. `,` ve `.` yalnız iki basamak arasındaysa kalır. `1/2` `12` olmaz. `1/2.` `1/2` olur. |
| Sayısal tolerans | `TOLERANS = decimal.Decimal("0.01")`, mutlak. Normal dizginin tamamı sayıysa karşılaştırılır: tam sayı, tek ayraçlı ondalık (`,` ya da `.`), ya da `tam/tam` kesir (payda 0 değil). `abs(a - b) <= TOLERANS`. `0,5` ile `1/2` eşittir. `1/2` ile `12` eşit değildir. Sayı çıkmayan çift dizgi eşitliğine düşer. `kabul_edilenler` durur. |
| Zorluk | Gövde alanı `zorluk`: `kolay`, `orta`, `zor`. Başka değer ya da boş alan araç hatasıdır. Soru başına alan yoktur. |
| `kazanim_kodu` | Alıştırma, `quiz` ve cevap satırı taşır. Alan yoksa, `None` ise ya da strip sonrası boşsa saklanan değer NULL'dur. Bu bir araç hatası değildir ve 400 değildir. |
| Son denemeler | `SON_DENEME = 10`. Grup `(konu, kazanim_kodu)`. Satırlar `zaman` artan. Son 10 sayılır. `toplam >= 3` ve `dogru * 5 < toplam * 3` ise zayıftır. |
| Çalışılan konu | Öğretmen modu (`ogretmen != genel`) asistan satırı yazılınca, o satırın atıflarından, ek model çağrısı olmadan. `kazanim_kodu`: `locator.args` içinde `kazanim_kodu` ya da `kod`; yoksa `label`'ın ilk boşlukla ayrılmış parçası `^[A-ZÇĞİÖŞÜ]{2,10}(?:\.\d+)+$` ile eşleşirse o parça. `sayfa_basligi`: `locator.tool == "kitap_sayfa"` ise `label`'ın strip hali. İkisi de boşsa satır yok. Aynı mesajda aynı çift bir kez yazılır. Araç son `SON_CALISILAN = 5` satırı okur. |
| Hafta | `Europe/Istanbul` pazartesi 00:00 dahil, sonraki pazartesi hariç. `SIMDI` (2026-10-03 08:00 UTC) için aralık 2026-09-27 21:00 UTC dahil, 2026-10-04 21:00 UTC hariç. Gün `2026-09-28`. Sayım: o aralıktaki sohbetler `ogretmen` başına (`guncelleme`), alıştırma sayısı (`alistirma.zaman`), puan (`alistirma_cevap` doğru ve toplam). |
| Rubrik | Düzey belirteçleri `baslangic`, `gelisiyor`, `yeterli`. Okur etiketi `Başlangıç`, `Gelişiyor`, `Yeterli`. Ölçüt, ekteki ders odağıdır. `duzeyler` bu üç belirteçten biri değilse satır yazılmaz. Sayısal not yoktur. |
| Yanlış analizi | `yanlis_esle`: katalogdaki her `###` başlığı ile **Doğrusu** satırı. Belirteçler katlanır; 3 karakterden kısa olan düşer. Skor, yanlış cevap ile soru metninin ortak belirteç sayısıdır. Eşik 2. Beraberlikte dosyada önce gelen kazanır. Dönüş `{baslik, dogrusu, kontrol}`. Eşleşme yoksa anahtar konmaz. |
| Sınav konuları | Yaklaşan satıra ikinci satır: `Konular: ` ve `relatedContent[].title` sırası, en çok 10, araya `; `. Liste yoksa ya da boşsa `Konular: yok`. Geçmiş satıra konu satırı konmaz. `Konular: yok` iken model konu uydurmaz. |
| Boş günlük | `Henüz deneme yok. Bir alıştırma bitince burada görünür.` Yalnız `zayif` boşken. Hafta sayıları yine çizilir. |
| 400 cümlesi | `Cevap alınamadı.` 404 gövdesi `Alıştırma bulunamadı.` İkisi de saklı `dogru`, yol ve istisna adı içermez. |

## Ertelenen

Spec bu üçünde sözcük ya da ikinci bir yüzey yazmaz. Görev eklenmez.

1. **Doğru/yanlış sözcükleri.** `dogru_yanlis` için kabul edilen çift yazılmamıştır. `dogru` boş olmayan bir dizgidir.
2. **Aile günlüğü.** Günlüğü "Işık kendisininkini görür" diye sınırlar. Ailenin günlüğü görmesi ve Işık'ın ekini değerlendirmesi yazılmaz. Başkasının eki bulunamaz.
3. **İki hitap metni.** Işık'a cesaretlendirici, aileye aynı içeriğin "siz" ile saklanması ayrı kolon istemez. Günlük, aracı çağıran okurun tek metnini saklar.

## Kilitlenen adlar

| Ad | Değer | Neden |
|---|---|---|
| Dosya | `output/assistant_sohbetler.sqlite` | §4: olaylar aynı SQLite'ta. B3'ün dosyası. |
| Bağlantı | B3 `SohbetDeposu._baglan` | Yeni bağlantı düzeni yok. |
| `alistirma` | `id, sohbet_id, mesaj_id, sahip_email, ogretmen, baslik, ders, konu, kazanim_kodu, zorluk, sorular_json, zaman` | §4 saklar. `mesaj_id` asistan satırı yazılınca `alistirma_bagla` ile dolar. `zorluk` üç kademeden biridir. |
| `alistirma_cevap` | `id, alistirma_id, sira, ders, konu, kazanim_kodu, dogru, zaman`. `UNIQUE (alistirma_id, sira)` | §4: soru bazında ders, konu, kazanım kodu, doğru mu. |
| `calisma_degerlendirme` | `id, sohbet_id, ek_id, ogretmen, guclu_yanlar, duzeyler, sonraki_adim, okur, zaman` | Ek: güçlü yanlar, düzeyler, tek sonraki adım. `duzeyler` üç belirteçten biri. Sayısal not kolonu yok. |
| `calisilan_konu` | `id, sohbet_id, mesaj_id, sahip_email, ogretmen, kazanim_kodu, sayfa_basligi, zaman` | Atıftan. İki metin kolonu boş dizgi olabilir; ikisi birden boş olan satır yazılmaz. |
| Kimlik | `uuid.uuid4().hex`, `^[0-9a-f]{32}$` | B3 ile aynı biçim. |
| Zaman | UTC `YYYY-MM-DDTHH:MM:SSZ` | B3 `zaman_yazi`. |
| `sira` | `sorular` içinde 1'den başlayan konum | Şemada soru kimliği yok. Liste sıralıdır. |
| Soru sayısı | 3–10, sınırlar dahil | §4. |
| Tür | `coktan_secmeli`, `dogru_yanlis`, `kisa_cevap` | §4. `soru-kaliplari.md` içindeki `acik_uclu` bu üçlüde yoktur; araç onu reddeder. |
| `quiz` | SSE olayı. `dogru`, `kabul_edilenler`, `aciklama` yok | §4: sorular cevapsız gider. Açıklama puanlayınca döner. |
| Puanlama | katlama, noktalama, tek boşluk, sonra `Decimal` toleransı | Kilitlenen seçimler. |
| %60 | `dogru * 5 < toplam * 3`, ve `toplam >= 3` | "Altında": 3/5 zayıf değildir. 1/3 zayıftır. İki yanlış zayıf değildir. |
| Grup | `(konu, kazanim_kodu)` çifti | Satırın taşıdığı iki alan. Başka eşleme yok. |
| Cevap ucu | `POST /api/assistant/alistirmalar/<id>/cevap` | §4. Gövde `{sira, cevap}`. Dönüş `{dogru, aciklama}`. |
| Günlük ucu | `GET /api/assistant/ogrenme-gunlugu` | Spec yol yazmaz. Diğer asistan uçlarının yanındadır. Yalnız çağıranın satırları. |
| Yazma | Yalnız alıştırmanın `sahip_email`'i | B3: yazma sahibine. Aile 403, cümle B3'ün cümlesidir: `Bu sohbet salt okunur.` |
| İkinci cevap | Aynı `(alistirma_id, sira)` yeni satır yazmaz; ilk sonucu döner | Spec yeniden denemeyi yazmaz. |
| Araçlar | `alistirma_olustur`, `ogrenme_gunlugu`, `calisma_degerlendir` | §4 ve ek. `ogrenme_gunlugu` ile `calisma_degerlendir` yalnız `ogretmen != genel` ve `not_deposu` varken ilan edilir. |
| Rubrik | `references/degerlendirme-rubrigi.md` | Ek. `ZORUNLU_KAYNAKLAR`'a eklenir. |
| Sınav planı | Yaklaşan satır: ders, tür, tarih, `Konular:` | `relatedContent` başlıkları. Yeni araç yok. |
| Bağ | `alistirma.mesaj_id` | B3 `mesaj_ekle` `meta_json` için `'{}'` yazar. B4 o eklemeyi değiştirmez. GET `meta_json` okumaz. |
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
| Boş günlük | `Henüz deneme yok. Bir alıştırma bitince burada görünür.` |
| Hafta başlığı | `Bu hafta` |
| 400 | `Cevap alınamadı.` |
| 404 | `Alıştırma bulunamadı.` |
| Düzey etiketi | `Başlangıç`, `Gelişiyor`, `Yeterli` |

Bilinmeyen öğretmen B1 cümlesidir: `Bilinmeyen öğretmen modu.`

## File Structure

| Dosya | Durum | Sorumluluk |
|---|---|---|
| `src/assistant_alistirma.py` | yeni | Şema, noktalama, tolerans, zayıf konu, atıf, hafta, yanlış eşleme |
| `tests/test_assistant_alistirma.py` | yeni | Şema, katlama, pencere, atıf, hafta, eşleme |
| `src/assistant_sohbet.py` | değişir | Dört tablo ve metotlar (B3 dosyası). `mesaj_ekle` imzası değişmez. |
| `src/dashboard_api.py` | değişir | Cevap ucu, günlük ucu, `quiz` sonrası `mesaj_id` |
| `src/assistant_tools.py` | değişir | Üç araç; `sinavlar_metni` konu satırı |
| `tests/test_assistant_skills.py` | değişir | Dört kaynak bekler |
| `tests/test_assistant_skills_icerik.py` | değişir | `YASAK_ARACLAR`'dan B4 araç adlarını çıkarır |
| `tests/test_assistant_ogrenci_araclari.py` | değişir | Konu satırı |
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
- Produces: `alistirma_hata(govde) -> str | None`, `cevap_dogru(verilen, dogru, kabul) -> bool`, `zayif_konular(satirlar) -> list[dict]`, `calisilan_konular(atiflar) -> list[dict]`, `hafta_araligi(simdi) -> tuple[datetime, datetime]`, `yanlis_esle(verilen, soru, katalog) -> dict | None`.

- [ ] **Step 1: Test**

`tests/test_assistant_alistirma.py`:

```python
"""Alıştırma şeması ve puan (spec §4). Ağ yok."""
from datetime import datetime, timezone

from src.assistant_alistirma import (
    alistirma_hata, calisilan_konular, cevap_dogru, hafta_araligi,
    yanlis_esle, zayif_konular,
)


def _soru(**fazla):
    temel = {
        "tur": "kisa_cevap",
        "soru": "1/2 + 1/3",
        "dogru": "5/6",
        "aciklama": "Paydalar eşitlenir.",
    }
    temel.update(fazla)
    return temel


def _govde(sorular, **fazla):
    govde = {"baslik": "Payda", "ders": "Matematik", "konu": "Rasyonel sayılar",
             "zorluk": "orta", "sorular": sorular}
    govde.update(fazla)
    return govde


def test_uc_soru_kabul_kod_zorunlu_degil():
    assert alistirma_hata(_govde([_soru(), _soru(), _soru()])) is None


def test_iki_ve_on_bir_red():
    assert alistirma_hata(_govde([_soru(), _soru()])) is not None
    assert alistirma_hata(_govde([_soru() for _ in range(11)])) is not None


def test_bos_aciklama_ve_yanlis_tur():
    assert alistirma_hata(_govde([_soru(aciklama="  "), _soru(), _soru()])) is not None
    assert alistirma_hata(_govde([_soru(tur="acik_uclu"), _soru(), _soru()])) is not None


def test_dort_secenek_uc_ve_bes_red():
    dort = ["5/6", "2/5", "1/2", "3/4"]
    iyi = _soru(tur="coktan_secmeli", secenekler=dort, dogru="5/6")
    assert alistirma_hata(_govde([iyi, _soru(), _soru()])) is None
    uc = _soru(tur="coktan_secmeli", secenekler=dort[:3], dogru="5/6")
    assert alistirma_hata(_govde([uc, _soru(), _soru()])) is not None
    dis = _soru(tur="coktan_secmeli", secenekler=dort, dogru="9/9")
    assert alistirma_hata(_govde([dis, _soru(), _soru()])) is not None


def test_zorluk_ucu_bos_kod_400_degil():
    assert alistirma_hata(_govde([_soru(), _soru(), _soru()], kazanim_kodu="")) is None
    assert alistirma_hata(_govde([_soru(), _soru(), _soru()], kazanim_kodu=None)) is None
    assert alistirma_hata(_govde([_soru(), _soru(), _soru()], zorluk="kolay")) is None
    assert alistirma_hata(_govde([_soru(), _soru(), _soru()], zorluk="zor")) is None
    assert alistirma_hata(_govde([_soru(), _soru(), _soru()], zorluk="asiri")) is not None


def test_katlama_noktalama_tolerans():
    assert cevap_dogru("  Beş   bölü  ALTI ", "beş bölü altı", None) is True
    assert cevap_dogru("İstanbul", "istanbul", None) is True
    assert cevap_dogru("1/2.", "1/2", None) is True
    assert cevap_dogru("1/2", "12", None) is False
    assert cevap_dogru("0,5", "1/2", None) is True
    assert cevap_dogru("0,52", "1/2", None) is False
    assert cevap_dogru("0,5", "1/2", ["0,5"]) is True


def test_zayif_sinir_ve_son_on():
    def satir(konu, kod, dogru, gun, dakika):
        return {"konu": konu, "kazanim_kodu": kod, "dogru": dogru,
                "zaman": f"2026-10-{gun:02d}T08:{dakika:02d}:00Z"}

    satirlar = [satir("Kesir", "MAT.7.1.1", i == 0, 1, i) for i in range(3)]
    satirlar += [satir("Oran", "MAT.7.1.5", i < 3, 2, i) for i in range(5)]
    satirlar += [satir("Denklem", "", False, 3, i) for i in range(2)]
    zayif = {(z["konu"], z["kazanim_kodu"]) for z in zayif_konular(satirlar)}
    assert ("Kesir", "MAT.7.1.1") in zayif
    assert ("Oran", "MAT.7.1.5") not in zayif
    assert ("Denklem", "") not in zayif
    # 20 eski doğru pencereden düşer. Son 10 yanlış zayıftır. Tümü sayılırsa 20/30 zayıf değildir.
    eski = [satir("Kesir", "MAT.7.2.1", True, 4, i) for i in range(20)]
    yeni = [satir("Kesir", "MAT.7.2.1", False, 5, i) for i in range(10)]
    pencere = zayif_konular(eski + yeni)
    assert pencere[0]["kazanim_kodu"] == "MAT.7.2.1"
    assert pencere[0]["dogru"] == 0 and pencere[0]["toplam"] == 10


def test_atif_satiri_ve_hafta():
    atiflar = [
        {"kind": "mufredat", "label": "MAT.7.1.1 kesir",
         "locator": {"tool": "kazanim_ara", "args": {"kazanim_kodu": "MAT.7.1.1"}}},
        {"kind": "kitap", "label": "Kesirler sayfa 12",
         "locator": {"tool": "kitap_sayfa", "args": {}}},
        {"kind": "ogrenci", "label": "not", "locator": {"tool": "notlar"}},
    ]
    assert calisilan_konular(atiflar) == [
        {"kazanim_kodu": "MAT.7.1.1", "sayfa_basligi": ""},
        {"kazanim_kodu": "", "sayfa_basligi": "Kesirler sayfa 12"},
    ]
    bas, son = hafta_araligi(datetime(2026, 10, 3, 8, 0, tzinfo=timezone.utc))
    assert bas == datetime(2026, 9, 27, 21, 0, tzinfo=timezone.utc)
    assert son == datetime(2026, 10, 4, 21, 0, tzinfo=timezone.utc)


def test_yanlis_katalog_basligina_eslenir():
    katalog = (
        "### Paydalar toplanır\n\n**Doğrusu:** Paydalar eşitlenir.\n"
        "**Kontrol sorusu:** 1/4 + 1/2?\n\n"
        "### Başka bir yanılgı\n\n**Doğrusu:** Başka.\n**Kontrol sorusu:** Yok.\n"
    )
    es = yanlis_esle("paydalar toplanir", "paydalar toplanir", katalog)
    assert es["baslik"] == "Paydalar toplanır"
    assert es["dogrusu"] == "Paydalar eşitlenir."
    assert yanlis_esle("mavi", "kalem", katalog) is None
```

`cevap_dogru` içindeki `"İstanbul"` / `"istanbul"` çifti `turkce_kucult_katla`'nın mevcut sözleşmesidir (`tests/test_assistant_indeks_hijyeni.py`).

- [ ] **Step 2: FAIL**

`cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan && DASHBOARD_SECRET_KEY=yalniz-test /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest tests/test_assistant_alistirma.py -q -p no:cacheprovider`

Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Uygula**

`alistirma_hata` model içindir; okura gitmez. Eksik `baslik`/`ders`/`konu`/`zorluk`, `zorluk` üçlüden değil, `sorular` 3–10 değil, `tur` üçlüden değil, `soru` ya da `aciklama` strip sonrası boş, `dogru` strip sonrası boş ise hata döner. `coktan_secmeli` için `secenekler` tam dört boş olmayan dizgi değilse, ya da `dogru` o listede birebir yoksa hata döner. `dogru_yanlis` ve `kisa_cevap` için `secenekler` aranmaz. `kabul_edilenler` varsa boş olmayan dizgilerdir. `kazanim_kodu` yoksa, `None` ise ya da strip sonrası boşsa hata dönmez. `kaynak` varsa dizgidir; içeriği denetlenmez.

`_norm`: `turkce_kucult_katla`, sonra kilitlenen noktalama, sonra `" ".join(metin.split())`. `cevap_dogru` önce `dogru` ve `kabul_edilenler` içinde `_norm` eşitliği arar. İki taraf da boşsa eşit değildir. Eşitlik yoksa ve iki taraf da sayıysa `decimal.Decimal` ile `abs(a - b) <= Decimal("0.01")`.

`zayif_konular`: satırları `(konu, kazanim_kodu)` ile gruplar. `kazanim_kodu` yoksa `""`. Grup `zaman` artan sıralanır; `zaman` yoksa en eski sayılır. Son 10 kalır. `toplam < 3` ise yok. `dogru * 5 < toplam * 3` ise `{konu, kazanim_kodu, dogru, toplam}` döner. Sıra: `toplam` azalan, sonra konu, sonra kod.

`calisilan_konular` ve `hafta_araligi` kilitlenen seçimlerin kuralıdır. `hafta_araligi` `zoneinfo.ZoneInfo("Europe/Istanbul")` kullanır; dönüş UTC'dir. `yanlis_esle` katalog metnini `### ` başlıklarına böler. **Doğrusu:** ve **Kontrol sorusu:** satırlarının geri kalanı strip edilir. Skor eşiği 2'nin altındaysa `None`.

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
- Produces: `alistirma_yaz`, `alistirma_getir`, `alistirma_bagla`, `cevap_yaz`, `cevaplar`, `degerlendirme_yaz`, `calisilan_yaz`, `gunluk`. `POST /api/assistant/alistirmalar/<id>/cevap`, `GET /api/assistant/ogrenme-gunlugu`.

- [ ] **Step 1: Test**

Saat ve giriş, B3 `tests/test_assistant_sohbet_api.py` kalıbıdır. `ISIK`, `AILE` aynı adresler. `SIMDI = datetime(2026, 10, 3, 8, 0, tzinfo=timezone.utc)`.

```python
def test_cevap_sahibe_aciklama_verir_ikinci_kez_yazmaz(istemci):
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    depo = _sohbet_deposu()
    aid = depo.alistirma_yaz(
        sid, ISIK, "matematik", "Payda", "Matematik", "Kesir", None, "orta",
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
        sid, ISIK, "matematik", "Payda", "Matematik", "Kesir", "MAT.7.1.1", "orta",
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
        sid, ISIK, "matematik", "Payda", "Matematik", "Kesir", None, "orta",
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

`_soru` görev 1'deki gövdedir. Sızdırma testi `meta_json` yazmaz. `mesaj_ekle` B3'teki gibi `'{}'` koyar. `alistirma_bagla` `mesaj_id` yazar. GET alıştırmayı bu kolonla bulur; `aid` gövdededir, `5/6` ve açıklama yoktur.

Günlük testi saati `SIMDI`'ye kilitler. Üç cevabın biri doğruysa `zayif` içinde yazılan kod vardır. `hafta["baslangic"] == "2026-09-28"`, `hafta["alistirma"]` o aralıktaki alıştırma sayısıdır, `hafta["puan"] == {"dogru": 1, "toplam": 3}`. `hafta["sohbet"]` çağıranın o aralıktaki sohbetlerini `ogretmen` başına sayar. Başka kullanıcının satırı dönmez.

Yanlış cevap testi: soru metni `paydalar toplanir`, verilen `paydalar toplanir`, öğretmen `matematik`. 200 gövdesinde `yanlis_analizi.baslik` gerçek `kavram-yanilgilari.md` içindeki `Kesirleri toplarken paylar ve paydalar ayrı ayrı toplanır` başlığıdır. Doğru cevapta bu anahtar yoktur. Boş `cevap` 400 `Cevap alınamadı.` Bilinmeyen kimlik 404 `Alıştırma bulunamadı.`

Atıf testi: `ogretmen="matematik"` asistan satırı, atıf `kitap_sayfa` ve etiket `Kesirler sayfa 12`. `calisilan` içinde `sayfa_basligi` o etikettir. `ogretmen="genel"` aynı atıfla satır yazmaz.

- [ ] **Step 2: FAIL**

`tests/test_assistant_alistirma_api.py`. Expected: FAIL.

- [ ] **Step 3: Uygula**

Tablolar `SohbetDeposu` kuruluşundaki `_SEM` betiğine eklenir. `mesaj_ekle` B3'teki eklemeyi korur: `meta_json` `'{}'` kalır, imzaya alan eklenmez. `alistirma_yaz` `BEGIN IMMEDIATE` ile satır koyar, `mesaj_id` NULL başlar, `zorluk` ve `kazanim_kodu` kolonlarını yazar, kimliği döner. Boş kod NULL saklanır. `alistirma_bagla` yalnız `mesaj_id`'yi yazar. `cevap_yaz` aynı `(alistirma_id, sira)` varsa yeni satır koymaz, eskisini döner.

`POST`: `_require_assistant_access`. Kimlik biçimi bozuksa ya da satır yoksa 404 `Alıştırma bulunamadı.` `sahip_email` çağıran değilse 403 `Bu sohbet salt okunur.` `sira` 1..n değilse ya da `cevap` strip sonrası boşsa 400 `Cevap alınamadı.` 200'de `cevap_dogru` ve o sorunun `aciklama`'sı. Yanlışsa ve `yanlis_esle` doluysa `yanlis_analizi`. Katalog, alıştırmanın `ogretmen` skill'indeki `kavram-yanilgilari.md` metnidir. Genel modda ya da eşleşme yoksa anahtar konmaz. Günlük satırının `ders`, `konu`, `kazanim_kodu` alanları alıştırma satırından kopyalanır. `dogru` 1 ya da 0.

`GET /api/assistant/sohbetler/<id>`: mesajın `id`'si `alistirma.mesaj_id` ile eşleşen satırlar yanıta `alistirma` listesi olarak eklenir (`zaman`, sonra `id`). `meta_json` bu eşlemede okunmaz. Her alıştırmada `id`, `baslik`, `ders`, `konu`, `kazanim_kodu`, `zorluk`, `sorular`. Her soruda yalnız `tur`, `soru` ve varsa `secenekler`. `dogru`, `kabul_edilenler`, `aciklama` yok.

Asistan satırı B3'ün yazdığı yerde, `mesaj_ekle`'den sonra: `ogretmen != "genel"` ise `calisilan_yaz` o satırın atıf listesini `calisilan_konular` ile işler. Genel mod satır yazmaz.

`GET /api/assistant/ogrenme-gunlugu`: çağıranın cevap, değerlendirme ve çalışılan satırları. `zayif` = `zayif_konular` (son 10). `calisilan` son 5, yeniden eskiye. `hafta` kilitlenen aralıktır: `baslangic`, `sohbet` (`ogretmen`, `sayi`), `alistirma`, `puan` (`dogru`, `toplam`). Okur rolü 403, B3 kapısı. Aile için ayrı uç yoktur.

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
- Modify: `tests/test_assistant_skills.py`, `tests/test_assistant_skills_icerik.py`, `tests/test_assistant_ogrenci_araclari.py`
- Modify: dört `src/assistant_skills/<ad>/SKILL.md`
- Create: dört `references/degerlendirme-rubrigi.md`
- Test: `tests/test_assistant_alistirma.py` (araç)

**Interfaces:**
- Consumes: `alistirma_hata`, `Skill.kaynak_oku`, `EkDeposu.oku`, `not_deposu`, `sohbet_id`, `okur`, `ogretmen`, `sinavlar_metni`.
- Produces: üç aracın ilanı ve `olay` alanı `quiz`. Yaklaşan sınav satırında `Konular:`.

- [ ] **Step 1: Test**

`tests/test_assistant_skills.py` içindeki `test_gecerli_skill_yuklenir` beklentisi değişir. `kaynaklar`, `references/` dizinindeki dosya adlarının sıralı demetidir:

```python
assert s.kaynaklar == (
    "degerlendirme-rubrigi.md",
    "kavram-yanilgilari.md",
    "soru-kaliplari.md",
    "unite-haritasi.md",
)
```

Aynı dosyaya şu test eklenir. `KAYNAKLAR` henüz dördüncü anahtarı taşımıyorsa süzgeç hiçbir şey düşürmez ve yükleme hata vermez; bu adımın FAIL'i budur. Uygulamada `KAYNAKLAR` anahtarı yazılınca süzgeç dosyayı düşürür:

```python
def test_rubrik_dosyasi_zorunlu(tmp_path):
    kaynaklar = {k: v for k, v in KAYNAKLAR.items() if k != "degerlendirme-rubrigi.md"}
    skill_yaz(tmp_path, kaynaklar=kaynaklar)
    with pytest.raises(sk.SkillHatasi, match="degerlendirme-rubrigi.md"):
        sk.yukle(tmp_path)
```

Dört gerçek skill yüklenir. Her birinin `kaynak_oku("degerlendirme-rubrigi.md")` metni `not vermez`, `baslangic`, `gelisiyor`, `yeterli` ve o dersin ölçüt satırını içerir.

`tests/test_assistant_ogrenci_araclari.py` yeni test: yaklaşan sınavın `relatedContent` başlıkları `Konular: Rasyonel sayılar; Kesirler` satırını üretir. `relatedContent` yoksa yaklaşan satırda `Konular: yok` vardır. Geçmiş satırda `Konular:` yoktur. Mevcut `test_sinavlar_metni_tarih_ve_turu_yazar` aynen kalır.

Araç, depo tmp, `sohbet_id` dolu:

- `alistirma_olustur` geçerli gövdeyle (`zorluk="orta"`, `kazanim_kodu=""`) `ok` True. `olay["event"] == "quiz"`. `olay["zorluk"] == "orta"`. `olay["kazanim_kodu"] is None`. `olay` içinde `dogru` ve `aciklama` anahtarları yoktur. Satır depodadır. Bu çağrı 400 değildir.
- `zorluk` yoksa `ok` False, satır yok.
- İki soruluk gövde `ok` False, satır yok.
- `coktan_secmeli` üç seçenekle `ok` False.
- `sohbet_id` `""` iken `ok` False, sqlite dosyası yok.
- `ogrenme_gunlugu` `ogretmen="genel"` iken ilan edilmez. İlan edilince metin `zayif_konular` ve son beş `calisilan` satırını taşır.
- `calisma_degerlendir` çağıranın kendi ekiyle `duzeyler="yeterli"` satır yazar. `duzeyler="5"` ya da `duzeyler="iyi"` ise `ok` False, satır yok. `not` diye bir kolon yazılmaz. Başkasının ek kimliği `ok` False. `ogretmen="genel"` iken `ok` False.

`quiz` olayı `chat_events` kuyruğuna B3'ün `mode_suggestion` yolu ile girer: `outcome.olay`. Aynı yanıtta ikinci `quiz`, mevcut `yayinlanan_olaylar` kümesi yüzünden akışa ikinci kez konmaz. Araç yine de ikinci satırı yazar. Bu küme bu planda değiştirilmez. İki satır da aynı asistan `mesaj_id`'sine `alistirma_bagla` ile bağlanır.

- [ ] **Step 2: FAIL**

`tests/test_assistant_skills.py`, `tests/test_assistant_alistirma.py` ve `tests/test_assistant_ogrenci_araclari.py`. Expected: FAIL. Üçlü `kaynaklar` demeti dörde eşit değildir. Rubrik zorunluluğu henüz `SkillHatasi` vermez. `Konular:` satırı yoktur.

- [ ] **Step 3: Uygula**

`ZORUNLU_KAYNAKLAR`'a `"degerlendirme-rubrigi.md"` eklenir. `tests/skill_ornegi.py` `KAYNAKLAR` aynı dosyayı aşağıdaki gövdeyle yazar. `tests/test_assistant_skills_icerik.py` içindeki `YASAK_ARACLAR` kümesinden `"alistirma_olustur"` ve `"ogrenme_gunlugu"` çıkar. Yorum, bu iki adın B4 gelene kadar yasak olduğunu söyler. SKILL cümleleri bu adları ters tırnaksız yazar; `GERCEK_ARACLAR` kontrolü yalnız ters tırnak içine bakar.

Matematik dosyasının tamamı:

```markdown
# Değerlendirme rubriği

Maarif ölçme-değerlendirme anlayışı: süreç odaklıdır, not vermez. Ölçütler ve düzey betimleri programın kazanım ve süreç bileşeni dilindendir.

Ölçüt: çözüm yolu ve gösterim

- baslangic: İşlem var, yol yazılmamış.
- gelisiyor: Yol kısmen yazılı, gösterim eksik.
- yeterli: Yol ve gösterim birbirine bağlı.
```

Diğer üç dosya aynı kalıptır. Yalnız ölçüt satırı ve üç düzey cümlesi değişir:

| Skill | Ölçüt | baslangic | gelisiyor | yeterli |
|---|---|---|---|---|
| `turkce` | yazma ve okuma-anlama | Metin var, ne anlatıldığı seçilmemiş. | Ana düşünce seçilmiş, dayanak eksik. | Ana düşünce dayanakla bağlı. |
| `fen` | deney tasarımı ve bilimsel açıklama | Gözlem var, değişken yok. | Değişken yazılı, açıklama gözleme bağlı değil. | Değişken, gözlem ve açıklama birbirine bağlı. |
| `sosyal` | kaynak ve kanıt kullanımı, neden-sonuç | Yargı var, kaynak yok. | Kaynak var, neden-sonuç bağlanmamış. | Yargı, kaynak ve neden-sonuç bağlı. |

Dört `SKILL.md` gövdesinde `##` sırası değişmez. `## Ders akışı` 4. adımının sonuna aynı cümle eklenir: `Kartlı alıştırma alistirma_olustur ile kurulur. Zorluk kolay, orta ya da zor olur.` `## Araç kullanımı` bölümünün sonuna aynı paragraf eklenir: `Yaklaşan sınav sinavlar listesindedir. Satırda ders, tür, tarih ve Konular satırı vardır. Konular, relatedContent başlıklarıdır. Konular: yok ise konu uydurma. Çalışma planını bu ders ve bu konularla kur; alıştırmayı alistirma_olustur ile ver.`

`sinavlar_metni` yaklaşan her satırın altına kilitlenen `Konular:` satırını ekler. Geçmiş satıra eklemez.

`declarations`: `not_deposu is None` ise üç araç da yoktur. `alistirma_olustur` genel modda da vardır. Diğer ikisi `ogretmen != "genel"` ve skill'in `degerlendirme-rubrigi.md` kaynağı varken vardır.

`alistirma_olustur` argümanı §4'ün nesnesi artı `zorluk`'tur. `alistirma_hata` doluysa `ok` False ve depo yazılmaz. Değilse `alistirma_yaz`. Boş `kazanim_kodu` NULL saklanır ve `ok` True kalır. `olay`:

```python
{"event": "quiz", "id": aid, "baslik": baslik, "ders": ders, "konu": konu,
 "kazanim_kodu": kod or None, "zorluk": zorluk,
 "sorular": [{"tur": s["tur"], "soru": s["soru"], **({"secenekler": s["secenekler"]} if "secenekler" in s else {})}
             for s in sorular]}
```

Araç metni modele kimliği söyler. Okura giden akış `olay`'dır.

`ogrenme_gunlugu` argümansızdır. Metin, çağıranın `zayif_konular` çıktısı ile son beş `calisilan` satırıdır. Yeni bir karakter tavanı yazılmaz; mevcut `TOOL_RESULT_SINIRI` durur. Öneri cümlesini araç uydurmaz; listeyi modele verir.

`calisma_degerlendir` argümanları: `ek` (32 hex), `guclu_yanlar`, `duzeyler`, `sonraki_adim`. `guclu_yanlar` ve `sonraki_adim` strip sonrası boş değil. `duzeyler` strip sonrası `baslangic`, `gelisiyor` ya da `yeterli` değilse `ok` False ve satır yok. `EkDeposu.oku` yalnız çağıranın adresine bakar; `None` ise `ok` False ve satır yok. Sayısal not alanı argümanda aranmaz ve saklanmaz. Satır `degerlendirme_yaz`. Model çağrısı yok. OCR yok. İkinci bir hitap metni üretilmez.

Asistan satırı B3'te `answer` olayından sonra `mesaj_ekle` ile yazılır; `meta_json` `'{}'` kalır. Yazımdan sonra bu yanıttaki her alıştırma kimliği `alistirma_bagla(aid, mid)` ile o satıra bağlanır. `ogretmen != "genel"` ise aynı atıf listesi `calisilan_yaz` olur. Akış yarıda kalırsa B3 asistan satırı yazmaz; alıştırma satırı durur, `mesaj_id` NULL kalır. Bu plan onu silmez.

- [ ] **Step 4: PASS**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan
DASHBOARD_SECRET_KEY=yalniz-test /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest \
  tests/test_assistant_alistirma.py tests/test_assistant_skills.py \
  tests/test_assistant_skills_icerik.py tests/test_assistant_ogrenci_araclari.py \
  tests/test_assistant_ogretmen_modu.py \
  -q -p no:cacheprovider
```

Expected: PASS. İki modun temel sistem bloğu bayt bayt aynı kalır. Rubrik metni `test_metin_turkce` süzgecinden geçer: `the|and|of|with|you|your|is|are|this|that|for` yoktur.

- [ ] **Step 5: Commit**

```bash
git add src/assistant_tools.py src/assistant_skills.py tests/skill_ornegi.py \
  tests/test_assistant_skills.py tests/test_assistant_skills_icerik.py \
  tests/test_assistant_ogrenci_araclari.py tests/test_assistant_alistirma.py \
  src/assistant_skills/turkce/SKILL.md src/assistant_skills/turkce/references/degerlendirme-rubrigi.md \
  src/assistant_skills/matematik/SKILL.md src/assistant_skills/matematik/references/degerlendirme-rubrigi.md \
  src/assistant_skills/fen/SKILL.md src/assistant_skills/fen/references/degerlendirme-rubrigi.md \
  src/assistant_skills/sosyal/SKILL.md src/assistant_skills/sosyal/references/degerlendirme-rubrigi.md
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
data: {"id":"ab0123456789ab0123456789ab012345","baslik":"Payda","ders":"Matematik","konu":"Kesir","kazanim_kodu":null,"zorluk":"orta","sorular":[{"tur":"kisa_cevap","soru":"1/2 + 1/3 kaçtır?"}]}

event: answer
data: {"answer":"Paydaları eşitledim.","citations":[]}
```

Kimlik 32 hex'tir. `dogru` ve `aciklama` bu olayda yoktur.

`POST` 200 `{"dogru": true, "aciklama": "Paydalar eşitlenir."}` döner. Kartta önce yalnız soru görünür. Cevap yazılınca `Doğru` ve açıklama görünür. Üç soruluk bir kartta üçüncü cevapdan sonra `Puan` görünür. Bir yanlış varsa `Yanlışlarımı anlat` görünür; basılınca giden kullanıcı mesajı kaçırılan sorunun `soru` metnini içerir ve `sohbet_id` taşır. Yanlış dönüş `yanlis_analizi.baslik` taşırsa kart o başlığı gösterir.

Salt okuma sohbetinde kartın yazma alanı `disabled` olur ve `Bu sohbet salt okunur.` durur.

İlerleme: `GET /api/assistant/ogrenme-gunlugu` 200 ve gövde `zayif` içinde Kesir, `hafta.baslangic` `2026-09-28`, `hafta.sohbet` `[{ogretmen: "matematik", sayi: 2}]`, `hafta.alistirma` 1, `hafta.puan` `{dogru: 1, toplam: 3}` iken başlık `Öğrenme günlüğü`, `Bu hafta`, `Matematik · 2`, `Alıştırma · 1`, `Puan · 1/3` ve `Kesir` görünür. `ogretmen` kimliği seçicideki kısa adla yazılır. Aynı uçta `zayif` boş, `hafta.sohbet` boş, `alistirma` 0, `puan` `{dogru: 0, toplam: 0}` iken başlık, `Henüz deneme yok. Bir alıştırma bitince burada görünür.`, `Sohbet · 0` ve `Alıştırma · 0` görünür; `Puan` satırı yoktur. 403'te bölüm yoktur.

Axe + IBM, B3 `asistan-sohbet.spec.ts` süzgeci: `aria_id_unique` ve `cds--ai-label|cds--toggletip` ihlal sayılmaz.

- [ ] **Step 2: FAIL**

`cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan/dashboard && npm run build && TEDY_E2E_PYTHON=/mnt/thunderbolt/workspaces/TED/.venv/bin/python DASHBOARD_SECRET_KEY=yalniz-test env -u ANTHROPIC_API_KEY npx playwright test asistan-alistirma.spec.ts`

Expected: FAIL, `Öğrenme günlüğü` yok.

- [ ] **Step 3: Arayüz**

Kart `quiz` olayındaki sırayı korur. Ekranda bir soru vardır. Gönder `POST` ile `{sira, cevap}` gider; `sira` 1'den başlar. Dönüş `Doğru` ya da `Yanlış`, altıda `aciklama`. `yanlis_analizi` varsa başlığı `Yanlış` satırının altında gösterilir; `dogrusu` kartta çizilmez. Son sorudan sonra `Puan` ve iki sayı: doğru sayısı, soru sayısı. Yüzde yazılmaz.

`Yanlışlarımı anlat` yalnız en az bir yanlış varken görünür. Gövde, kaçırılan soruların `soru` dizgeleridir; araya başka cümle konmaz. Gönderim B3'ün `{sohbet_id, ogretmen, messages:[{role:'user', content}]}` gövdesidir.

Salt okunur sohbette kart yazılmaz. 403'ün cümlesi B3 cümlesidir.

İlerleme bölümü `PlatformProgress` içinde, platform akordeonunun üstünde, başlık `Öğrenme günlüğü`. `credentials: 'include'`. 403'te bölüm render edilmez. Dolu `zayif` satırı konu adını gösterir. `zayif` boşsa kilitlenen cümle görünür. `Bu hafta` her dolu yanıtta çizilir: sohbet listesi boşsa `Sohbet · 0`, değilse kısa ad ve sayı; `Alıştırma · {alistirma}`; `puan.toplam > 0` ise `Puan · {dogru}/{toplam}`. Değerlendirme satırının `duzeyler` belirteci okur etiketine çevrilir.

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
- **Asistan değerlendirme ve sınav hazırlığı (B4)** (spec §4, ek "B4'e eklenenler", plan `docs/superpowers/plans/2026-10-03-asistan-degerlendirme-sinav-hazirligi-b4.md`): `alistirma_olustur` validates 3–10 questions, exactly 4 choices, `zorluk` of `kolay`/`orta`/`zor`, and an optional `kazanim_kodu` (blank is stored, not a 400). SSE `quiz` omits `dogru`, `kabul_edilenler` and `aciklama`. Scoring folds Turkish, strips punctuation without turning `1/2` into `12`, then applies an absolute `0.01` tolerance. `POST /api/assistant/alistirmalar/<id>/cevap` is owner-only; family gets `Bu sohbet salt okunur.` The exercise links by `alistirma.mesaj_id`; `mesaj_ekle` still writes `meta_json` `'{}'`. A topic is weak on the last 10 answers when `dogru * 5 < toplam * 3` and `toplam >= 3`. Teacher-mode citations write studied-topic rows. The journal week is Monday-to-Monday `Europe/Istanbul` and includes chat counts, exercises and scores. Each skill's `references/degerlendirme-rubrigi.md` is required (`baslangic`/`gelisiyor`/`yeterli`, no grade). A wrong answer maps onto a `kavram-yanilgilari.md` heading. Upcoming-exam study plans use the `sinavlar` line's course and `Konular:` from `relatedContent`. No `sohbet_id` means the tools are not declared and the file is not opened. `/v1` and `/plan` do not open it.
```

- [ ] **Step 2: Son kapı**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/asistan-b2-plan
DASHBOARD_SECRET_KEY=yalniz-test /mnt/thunderbolt/workspaces/TED/.venv/bin/python -m pytest \
  tests/test_assistant_alistirma.py tests/test_assistant_alistirma_api.py \
  tests/test_assistant_skills.py tests/test_assistant_skills_icerik.py \
  tests/test_assistant_ogrenci_araclari.py \
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
| Seçenek sayısı 4 | 1, 3 |
| SSE `quiz` cevapsız; `zorluk` ve `kazanim_kodu` gider | 3 |
| Puanlama: katlama, noktalama, `0.01` | 1, 2 |
| `1/2` `12` olmaz | 1 |
| Kart: tek tek, anında geri bildirim, puan, `Yanlışlarımı anlat` | 4 |
| Alıştırma `mesaj_id` ile bağlı; `meta_json` `'{}'` kalır; sırlar GET'te yok | 2, 3 |
| Günlük: soru bazında ders, konu, kazanım, doğru mu | 2 |
| Atıftan çalışılan konu | 1, 2, 3 |
| Zayıf konu %60 altı, en az 3, son 10 | 1, 2 |
| `ogrenme_gunlugu` zayıf konu ve son 5 çalışılan | 3 |
| İlerleme bölümü, Işık kendi satırını görür | 2, 4 |
| Boş günlük cümlesi | 4 |
| Haftalık sohbet, alıştırma ve puan | 1, 2, 4 |
| Dört rubrik dosyası, not vermez, ölçüt ve üç düzey | 3 |
| `calisma_degerlendir`, kendi eki, yapılandırılmış çıktı, günlüğe | 2, 3 |
| Işık / aile hitabının iki saklı metni | ertelenen 3 |
| Üç zorluk kademesi `kolay` / `orta` / `zor` | 1, 3 |
| `kazanim_kodu` taşınır; boş kod 400 değil | 1, 2, 3 |
| Yanlışın kataloğa eşlenmesi | 1, 2, 4 |
| `sinavlar` satırından ders ve `Konular:` | 3 |
| 400 `Cevap alınamadı.` / 404 `Alıştırma bulunamadı.` | 2 |
| Doğru/yanlış sözcük çifti | ertelenen 1 |
| Aile günlüğü ve ailenin Işık ekini değerlendirmesi | ertelenen 2 |
| `/v1`, `/plan`, `sohbet_id` yok | 3 |
| B5, B6 | yok |
