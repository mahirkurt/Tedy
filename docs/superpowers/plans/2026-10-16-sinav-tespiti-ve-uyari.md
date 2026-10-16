# Sınav tespiti, içerik birleştirme ve uyarı — uygulama planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Işık'ın yaklaşan sınavlarını takvimden ve ders içeriği/ödev/duyuru/ek metinlerinden eksiksiz bulmak, her sınava kaynaktaki konuları bağlamak, `output/sinavlar.json`'u tek gerçek kaynak yapmak ve sınav yaklaştıkça Işık'a ve aileye web push bildirimi göndermek.

**Architecture:** `run_sync`'e süre bütçeli bir adım eklenir: takvim + gelişim raporu listesi (`dashboard_api._sinav_listesi`) taban alınır, serbest metin adayları ücretsiz ön süzgeçten geçer, yeni/değişen metinler Claude Haiku'ya yapılandırılmış çıktıyla sorulur, deterministik uydurma kapısından geçen bulgular tabanla birleşip `output/sinavlar.json`'a atomik yazılır. `/api/exams` bu dosyayı okur (yoksa bugünkü hesaba düşer). Ayrı bir systemd zamanlayıcısı (10 dk) dosyayı, abonelik deposunu ve gönderim defterini okuyup vadesi gelen uyarıları VAPID web push ile yollar; pano bir servis çalışanı ve PWA manifest'i kazanır.

**Tech Stack:** Python 3.12, Flask, `anthropic` SDK (yapılandırılmış çıktı), `pywebpush` (yeni), `cryptography`; React 18 + Carbon, Vite, `node --test`, Playwright; systemd user units.

**Spec:** `docs/superpowers/specs/2026-10-16-sinav-tespiti-ve-uyari-design.md` (2c70194, kullanıcı onaylı 2026-10-16)

## Global Constraints

- Tüm kullanıcıya dönük metinler Türkçe. Bildirimde Işık'a "sen", aileye "siz" (Işık adıyla); hitap `roles.okur_turu(email)` ile seçilir (`ogrenci` / `aile`).
- Model `claude-haiku-4-5` (değiştirmek için `TEDY_SINAV_MODEL`), `src/claude_api.py` istemcisi, `output_config.format` JSON şeması.
- Aylık tavan `TEDY_SINAV_AYLIK_USD` (varsayılan `2`), defter `output/sinav_cikarim_defteri.json`; adım süresi `TEDY_SINAV_SURE` (varsayılan `45` sn).
- Önbellek `output/sinav_cikarim_onbellegi.json`, anahtar `sha256(metin) + ISTEM_SURUMU`.
- Bildirim bayrağı `TEDY_SINAV_UYARI=1`; kapalıyken zamanlayıcı hiçbir şey göndermez.
- Uyarı zamanları (İstanbul): `tespit` sonraki tur; `gun_7` −7 gün 18:00; `gun_2` −2 gün 18:00; `aksam` −1 gün 19:00. Sessiz saat 22:00–07:30 (bu arada hiç gönderim yok).
- Gönderim defteri `output/bildirim_defteri.jsonl`, anahtar `(email, sinav_id, tur, icerik_surumu)`.
- Abonelik deposu `output/bildirim_abonelikleri.json`, `fcntl.flock` altında (gunicorn iki işçi).
- Geçmiş sınavlar `sinavlar.json`'da 30 gün kalır.
- Takvim sınavının kimliği `md5(f"{course}|{title}|{_kimlik_zamani(date_str)}")[:12]` **değişmez** (modüller bu kimlikle bağlı).
- Bildirim uçları oturum + tam rol ister; okuyucu, API anahtarı ve `/v1` reddedilir; `READER_ENDPOINTS`'e eklenmez.
- Hiçbir test ücretli çağrı yapmaz (`tests/conftest.py` gerçek anahtarı kaldırır; yeni adım için de koruma eklenir); push testleri sahte gönderici kullanır.
- Bugün sayfası sessiz kalır (İ6, İ8): renkli geri sayım çipi yok, ders rengi yalnız 10 px işaret; "Yeni"/"Değişti" metinli gri etiket (renk tek başına anlam taşımaz).
- SCSS'te boşluk/tip/hareket Carbon token'larıyla (`npm run lint` stylelint).
- Bildirim yükü 4 KB altında: başlık ≤ 80, gövde ≤ 300 karakter.
- Paylaşılan checkout: iş yalnız `/mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-uyari` (dal `feat/sinav-uyari`) içinde; kendi dosyalarını adıyla stage et. Push, birleştirme, canlıya dağıtım, `.venv`'e paket kurulumu, `.env` yazımı ve unit kurulumu **yalnız kullanıcının açık onayıyla**.
- Commit mesajlarında model adı geçmez; her commit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` satırıyla biter.

## Review Focus

1. **Aynı ilanın kopyaları** — portal her yazıyı bir de başlıksız ikinci kart olarak verir ve kart sonraki haftaya taşınır (Matematik KTT 4. ve 5. haftada, 2+2 kart). Beklenen: tek aday, tek sınav, kişi başına tek bildirim. Testler: Görev 2 `test_ktt_kopyalari_tek_aday`, Görev 4 `test_ayni_ders_ayni_gun_iki_bulgu_tek_kayit`.
2. **Gece ya da aksaklık sonrası koşan zamanlayıcı** — 22:00–07:30 arası hiçbir bildirim gitmez; 19:00'da gitmesi gereken `aksam` ertesi sabah 07:30'da "Bugün … Başarılar!" diye gider; sınav başladıysa hiç gitmez. Test: Görev 8 `test_sessiz_saatte_hicbir_sey_gitmez`, `test_kacan_aksam_sabah_bugun_metniyle`, `test_baslamis_sinava_uyari_yok`.
3. **Yeni cihaz / yeni kişi aboneliği** — abone olan kişi o anda bilinen bütün sınavlar için bir anda "yeni sınav" seli almaz; yalnız bundan sonraki değişiklik ve hatırlatmaları alır. Test: Görev 8 `test_kisiyi_tohumla_eski_tespitleri_gondermez`, Görev 7 `test_ilk_abonelik_kisiyi_tohumlar`.
4. **Bozuk, eski sürümlü ya da olmayan `sinavlar.json`** — `/api/exams` asla boş dönmez; bugünkü takvim + gelişim raporu hesabına düşer. Test: Görev 6 `test_bozuk_dosyada_eski_hesaba_duser`, `test_eski_surumde_eski_hesaba_duser`.
5. **Çok uzun ilan** — 30 konulu ya da 2.000 karakterlik başlıklı bir ilan bildirim yükünü 4 KB'ın altında tutar; metin kesilir ama anlamlı kalır (ilk üç konu + "…"). Test: Görev 8 `test_uzun_konular_yuk_siniri`.

## Spec'i somutlaştıran kararlar

Spec'in açık bıraktığı ya da canlı veriyle karşılaşınca netleşen noktalar; her biri ilgili görevde testli.

| # | Karar | Neden | Görev |
|---|---|---|---|
| K1 | Gün vermeyen ifade ("Next week", "bu hafta") `tarih: null` + yeni `hafta` alanı (pazartesi) olur; hafta geçince kayıt geçmişe düşer, hafta-yalnız kayıt o haftadaki tek tarihli sınava bağlanır | Canlıda İngilizce ve Fen quiz'leri tam böyle duyuruluyor; hafta bilgisi atılırsa "tarih belirsiz" sonsuza dek "yaklaşan" kalırdı | 1, 4, 6 |
| K2 | Model tarihi tek başına kullanılmaz; tarih yalnız kaynakta doğrulanan ifadeden bizim çözümleyicimizle çıkar. Metindeki açık tarihlerin hepsi geçmişse kayıt atılır (yalnız tarih değil) | "15 Ekim'de yapılan KTT sonuçları" bir sınav duyurusu değil; tarihi atıp kaydı tutmak sahte "tarih belirsiz" sınav üretirdi | 1, 3 |
| K3 | Başlığın sözcükleri kaynakta yoksa başlık türden kurulur ("Matematik KTT") | Uydurma kapısı başlığa da uygulanır | 3 |
| K4 | İlk kurulumda `ilk_tespit: null` ("kurulumda zaten vardı"); sonraki yeni kayıtlar `ilk_tespit = şimdi` | Kurulum günü her sınav "Yeni" etiketi almaz; hatırlatmalar kesilmez | 4, 8, 10 |
| K5 | Ders "Genel" olan bulgu aynı gündeki takvim sınavına bağlanır | Ortak sınavlar (GİS, Sebit) takvimde ders adı taşımaz | 4 |
| K6 | Tarihsiz ve haftasız kayıt, son kaynağının yayınından 21 gün sonra düşer | Aksi hâlde eski bir "quiz olacak" cümlesi listede kalır | 4 |
| K7 | Ders sekmesinin `text` alanı yalnız kartı olmayan sekmede aday olur | `text` kartların birleşimi; kartlı sekmede onları yutup konumlarını kaybettirirdi | 2 |
| K8 | `TEDY_VAPID_SUBJECT` `.env`'e yazılmaz; varsayılan `https://tedy.online` (ortamdan değiştirilebilir) | `env_prep` `:` içeren değeri reddeder; kişisel e-posta push servislerine gönderilmez | 7 |
| K9 | 403 de "ölü abonelik" sayılır (spec: 404/410) | FCM 403'ü VAPID anahtarı uyuşmayan aboneliğe verir; o abonelik bizim için bir daha çalışmaz | 7 |
| K10 | Kişinin **ilk** cihazı abone olunca o an vadesi gelmiş uyarılar "gönderildi" sayılır (`kisiyi_tohumla`); yayında bir kez `tohumla` | Review Focus 3: yeni abone sel almaz | 7, 8 |
| K11 | `relatedContent` API'de kalır ama panoda ve asistanda "Konular" olarak gösterilmez; yerini `konular` alır | Spec §3: o alan bu haftanın kart başlıklarıydı, sınavın konusu değil | 6, 10 |
| K12 | Sınav uyarıları kartı metni kişisiz yazılır ("…izin verilmeli") | Kart Işık'a da aileye de aynı sayfada görünür; bildirim metni ise hitaplıdır | 9 |

---

## Dosya yapısı

| Dosya | Durum | Sorumluluk |
|---|---|---|
| `src/sinav_tarihi.py` | yeni | Tarih ifadelerini yayın bağlamıyla çözer (saf) |
| `src/sinav_kaynaklari.py` | yeni | Aday metinleri kaynak konumu ve yayın tarihiyle toplar; ön süzgeç; kopya birleştirme |
| `src/sinav_cikarimi.py` | yeni | Haiku okuyucusu, önbellek, bütçe defteri, uydurma kapısı |
| `src/sinav_tespiti.py` | yeni | Birleştirme, kimlik, sürüm, `sinavlar.json` oku/yaz, `tespit_et`, `--kuru` CLI |
| `src/web_push.py` | yeni | VAPID anahtarları, abonelik doğrulama ve deposu, gönderim |
| `src/sinav_uyari.py` | yeni | Vade hesabı (saf), metin, defter, `gonder`/`tohumla` CLI |
| `tedy-sinav-uyari.service`, `tedy-sinav-uyari.timer` | yeni | Zamanlayıcı unit'leri (repo kökünde izlenir) |
| `src/run_sync.py` | değişir | `_sinav_tespiti_adimi`, `health.json`'a `sinav_tespiti` ve `sinav_uyari` |
| `src/dashboard_api.py` | değişir | `_is_exam_event` takvim etiketi; `/api/exams` `sinavlar.json`'dan; `aiSummary`/`studyGuide` kalkar; bildirim uçları |
| `src/assistant_tools.py` | değişir | `sinavlar_metni` gerçek konuları ve "tarih belirsiz"i yazar |
| `requirements.txt` | değişir | `pywebpush>=2,<3` |
| `tests/conftest.py` | değişir | Testte gerçek sınav tespiti yok |
| `dashboard/public/sw.js`, `manifest.webmanifest`, `tedy-192.png`, `tedy-512.png` | yeni | Servis çalışanı (yalnız bildirim) ve PWA |
| `dashboard/index.html` | değişir | manifest bağlantısı |
| `dashboard/src/utils/bildirim.ts` | yeni | Bildirim durumu (saf) + tarayıcı akışları |
| `dashboard/src/utils/sinav.ts` | yeni | Yeni/Değişti, en yakın sınav, konu özeti, zaman metni (saf) |
| `dashboard/src/components/SinavUyarilari.tsx` (+`.scss`) | yeni | Bu cihazda aç/kapat, deneme, durum |
| `dashboard/src/components/SinavKarti.tsx` (+`.scss`) | yeni | `SinavOnizleme` (Bugün), `SinavEtiketi` (İşler), `SinavAyrintisi` (Sınavlar) |
| `dashboard/src/components/ExamTimeline.tsx`, `TodaySchedule.tsx`, `HomeworkTracker.tsx`, `DahaFazla.tsx`, `CourseContent.tsx` | değişir | Yeni bileşenlerin yerleşimi; `?sinav=`, `?hafta=` |
| `dashboard/src/types.ts` | değişir | `ExamItem` yeni alanlar, `aiSummary`/`studyGuide` kalkar |
| Testler | yeni | `tests/test_sinav_*.py`, `tests/sinav_fikstur.py`, `tests/test_web_push.py`, `tests/test_bildirim_api.py`, `dashboard/tests/bildirim.test.ts`, `dashboard/tests/sinav.test.ts`, `dashboard/tests/e2e/sinav-uyari.spec.ts` |

Komut kalıpları (worktree kökünden):

- Python testleri: `unshare -rn .venv/bin/python -m pytest -q <dosyalar>` (ağsız; tüm süit için dosya vermeden).
- Birim (pano): `cd dashboard && node --test tests/<dosya>.test.ts`
- e2e: `cd dashboard && npm run build:carbon-ai && TEDY_E2E_PORT=8391 env -u ANTHROPIC_API_KEY npx playwright test <spec> --retries=0`

---

### Görev 1: Tarih çözümleyici (`src/sinav_tarihi.py`) ve çalışma ortamı

**Files:**
- Create: `src/sinav_tarihi.py`
- Test: `tests/test_sinav_tarihi.py`

**Interfaces:**
- Consumes: `src.assistant_core.turkce_kucult_katla(text: str) -> str`
- Produces:
  - `@dataclass(frozen=True) TarihCozumu(gun: date | None, hafta: date | None, gecersiz: bool)` — `hafta` haftanın pazartesisi; `gecersiz` yalnız metindeki açık tarihlerin hepsi geçmiş/okul yılı dışıyken ve başka çözüm yokken `True`.
  - `okul_yili(bugun: date) -> tuple[date, date]` — `(Y-09-01, Y+1-07-15)`, `Y = bugun.year if bugun.month >= 8 else bugun.year - 1`
  - `pazartesi(gun: date) -> date`
  - `hafta_etiketi_araligi(etiket: str, baslangic_yili: int) -> tuple[date, date] | None` — "4. Hafta 05 Eki. - 11 Eki."
  - `yayin_tarihi(metin: str) -> date | None` — kart imzasındaki "| 05.10.2026"
  - `tarih_coz(metin: str, yayin: date, okul_araligi: tuple[date, date]) -> TarihCozumu`
  - `katla(metin: str) -> str` — `turkce_kucult_katla` + boşluk sadeleştirme (diğer modüller de bunu kullanır)

- [ ] **Adım 1: Worktree ortamını hazırla**

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-uyari
git branch --show-current            # beklenen: feat/sinav-uyari
ln -s /mnt/thunderbolt/workspaces/TED/.venv .venv
ln -s /mnt/thunderbolt/workspaces/TED/.env .env
grep -qx '.venv' .git/info/exclude 2>/dev/null || true   # .venv ve .env zaten .gitignore'da; git status'ta görünmemeli
git status --short                   # beklenen: boş
(cd dashboard && npm ci --no-audit --no-fund > /tmp/sinav-npm-ci.log 2>&1; echo "npm ci: $?")
unshare -rn .venv/bin/python -m pytest -q -x > /tmp/sinav-taban.log 2>&1; tail -3 /tmp/sinav-taban.log
```

Beklenen: `npm ci: 0`; pytest taban sonucu (geçen sayı) not edilir. Taban kırmızısı varsa adıyla kaydedilir, bu planın işi değildir.

- [ ] **Adım 2: Başarısız testi yaz** — `tests/test_sinav_tarihi.py`

```python
"""src/sinav_tarihi: kaynak metindeki sınav zamanını yayın bağlamıyla çözer.
Tarihler 2026-2027 okul yılından; 2026-10-12 pazartesi, 2026-10-16 cuma."""
from datetime import date

from src.sinav_tarihi import (TarihCozumu, hafta_etiketi_araligi, katla, okul_yili, pazartesi,
                              tarih_coz, yayin_tarihi)

YIL = (date(2026, 9, 1), date(2027, 7, 15))


def test_okul_yili_eylulden_temmuza():
    assert okul_yili(date(2026, 10, 16)) == YIL
    assert okul_yili(date(2027, 3, 2)) == YIL
    assert okul_yili(date(2026, 8, 20)) == YIL


def test_pazartesi():
    assert pazartesi(date(2026, 10, 16)) == date(2026, 10, 12)
    assert pazartesi(date(2026, 10, 12)) == date(2026, 10, 12)


def test_katla_turkce_ve_bosluk():
    assert katla("  MATEMATİK  KONU\nTARAMA ") == "matematik konu tarama"
    assert katla("Işık'ın SINAVI") == "isik'in sinavi"


def test_hafta_etiketi_ay_adlarindan_aralik():
    assert hafta_etiketi_araligi("4. Hafta 05 Eki. - 11 Eki.", 2026) == (date(2026, 10, 5), date(2026, 10, 11))


def test_hafta_etiketi_yil_sinirini_asar():
    assert hafta_etiketi_araligi("15. Hafta 28 Ara. - 03 Oca.", 2026) == (date(2026, 12, 28), date(2027, 1, 3))
    assert hafta_etiketi_araligi("19. Hafta 08 Şub. - 14 Şub.", 2026) == (date(2027, 2, 8), date(2027, 2, 14))


def test_hafta_etiketi_okunamazsa_none():
    assert hafta_etiketi_araligi("Bu hafta", 2026) is None


def test_yayin_tarihi_imza_satirindan():
    assert yayin_tarihi("KTT-1 KONULARI\nÖğretmen A | 05.10.2026\nMATEMATİK") == date(2026, 10, 5)
    assert yayin_tarihi("tarihsiz metin") is None


def test_turkce_gun_ay_buyuk_harf():
    c = tarih_coz("15 EKİM PERŞEMBE günü yapılacak olan Matematik KTT", date(2026, 10, 5), YIL)
    assert c == TarihCozumu(gun=date(2026, 10, 15), hafta=None, gecersiz=False)


def test_ay_adi_yilsiz_ocak_sonraki_yila_duser():
    assert tarih_coz("5 Ocak Salı ortak yazılı", date(2026, 12, 20), YIL).gun == date(2027, 1, 5)


def test_sayisal_bicimler():
    assert tarih_coz("Sınav 15.10 tarihinde", date(2026, 10, 5), YIL).gun == date(2026, 10, 15)
    assert tarih_coz("Sınav 15/10'da", date(2026, 10, 5), YIL).gun == date(2026, 10, 15)
    assert tarih_coz("Exam on 15.10.2026", date(2026, 10, 5), YIL).gun == date(2026, 10, 15)


def test_ingilizce_ay_gun():
    assert tarih_coz("The quiz is on October 21st", date(2026, 10, 12), YIL).gun == date(2026, 10, 21)


def test_yayindan_onceki_tarih_gecersiz():
    assert tarih_coz("15 Ekim'de yapılan KTT", date(2026, 10, 16), YIL) == TarihCozumu(None, None, True)


def test_okul_yili_disi_gecersiz():
    c = tarih_coz("Sınav 15.08.2027", date(2026, 10, 1), YIL)
    assert c.gun is None and c.gecersiz


def test_gecersiz_acik_tarih_goreli_ifadeyi_engellemez():
    c = tarih_coz("15 Ekim'deki KTT'nin ardından haftaya yeni quiz", date(2026, 10, 16), YIL)
    assert c == TarihCozumu(None, date(2026, 10, 19), False)


def test_haftaya_ve_next_week_hafta_dondurur():
    assert tarih_coz("Next week, you will have an Irregular Verbs Quiz", date(2026, 9, 21), YIL) \
        == TarihCozumu(None, date(2026, 9, 28), False)
    assert tarih_coz("haftaya kısa sınav var", date(2026, 9, 24), YIL).hafta == date(2026, 9, 28)


def test_bu_hafta():
    c = tarih_coz("Bu hafta ilk ünitemizin tamamını kapsayan bir quiz", date(2026, 10, 5), YIL)
    assert c == TarihCozumu(None, date(2026, 10, 5), False)


def test_haftaya_gun_adi_gun_verir():
    assert tarih_coz("haftaya Salı quiz", date(2026, 10, 7), YIL).gun == date(2026, 10, 13)


def test_yalniz_gun_adi_sonraki_o_gun():
    assert tarih_coz("Cuma günü kısa sınav", date(2026, 10, 12), YIL).gun == date(2026, 10, 16)
    assert tarih_coz("Cuma günü kısa sınav", date(2026, 10, 16), YIL).gun == date(2026, 10, 23)


def test_cumartesi_cuma_ile_karismaz():
    assert tarih_coz("Cumartesi deneme sınavı", date(2026, 10, 12), YIL).gun == date(2026, 10, 17)


def test_yarin_ve_bugun():
    assert tarih_coz("Yarın quiz var", date(2026, 10, 12), YIL).gun == date(2026, 10, 13)
    assert tarih_coz("tomorrow's quiz", date(2026, 10, 12), YIL).gun == date(2026, 10, 13)
    assert tarih_coz("Bugün kısa sınav", date(2026, 10, 12), YIL).gun == date(2026, 10, 12)


def test_ara_sozcugu_ay_sanilmaz():
    assert tarih_coz("20 arasında soru", date(2026, 10, 12), YIL) == TarihCozumu(None, None, False)


def test_cozulemeyen_ifade_tarih_uydurmaz():
    assert tarih_coz("Yakında bir quiz olacak", date(2026, 10, 12), YIL) == TarihCozumu(None, None, False)
```

- [ ] **Adım 3: Testin başarısız olduğunu gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_sinav_tarihi.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.sinav_tarihi'`

- [ ] **Adım 4: Uygula** — `src/sinav_tarihi.py`

```python
"""Sınav tarihini kaynak metinden, yayın bağlamıyla çözer (saf: dosya, ağ, saat yok).

Öğretmen tarihi nadiren yılıyla yazar ("15 EKİM PERŞEMBE", "15.10") ve sık sık
göreli konuşur ("haftaya", "Next week", "Cuma günü"). Yıl okul yılından, göreli
ifade yayın tarihinden gelir. Çözülemeyen ifade tarih uydurmaz: gun ve hafta
None kalır. Metindeki açık tarihlerin hepsi yayından önce ya da okul yılı
dışındaysa (başka çözüm de yoksa) `gecersiz` True olur — o metin geçmiş bir
sınavı anlatıyordur (spec §5 kural 4)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from src.assistant_core import turkce_kucult_katla

_AYLAR = {
    "ocak": 1, "oca": 1, "subat": 2, "sub": 2, "mart": 3, "mar": 3, "nisan": 4, "nis": 4,
    "mayis": 5, "may": 5, "haziran": 6, "haz": 6, "temmuz": 7, "tem": 7, "agustos": 8, "agu": 8,
    "eylul": 9, "eyl": 9, "ekim": 10, "eki": 10, "kasim": 11, "kas": 11, "aralik": 12, "ara": 12,
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "april": 4, "apr": 4,
    "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9, "sept": 9,
    "sep": 9, "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
_GUNLER = {
    "pazartesi": 0, "sali": 1, "carsamba": 2, "persembe": 3, "cumartesi": 5, "cuma": 4, "pazar": 6,
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
}


def _alternatif(sozluk: dict[str, int]) -> str:
    return "|".join(sorted(sozluk, key=len, reverse=True))


_AY = _alternatif(_AYLAR)
_GUN = _alternatif(_GUNLER)
_GUN_AY = re.compile(rf"\b(\d{{1,2}})\s+({_AY})\b\.?(?:\s+(\d{{4}}))?")
_AY_GUN = re.compile(rf"\b({_AY})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?:,?\s+(\d{{4}}))?")
_SAYISAL = re.compile(r"\b(\d{1,2})[./](\d{1,2})(?:[./](\d{4}|\d{2}))?\b")
_GUN_ADI = re.compile(rf"\b({_GUN})\b")
_GELECEK_HAFTA = re.compile(r"\b(haftaya|gelecek hafta|onumuzdeki hafta|next week)\b")
_BU_HAFTA = re.compile(r"\b(bu hafta|this week)\b")
_YARIN = re.compile(r"\b(yarin|tomorrow)\b")
_BUGUN = re.compile(r"\b(bugun|today)\b")
_IMZA = re.compile(r"\|\s*(\d{2})\.(\d{2})\.(\d{4})")
_ETIKET = re.compile(rf"(\d{{1,2}})\s+({_AY})\.?\s*-\s*(\d{{1,2}})\s+({_AY})\.?")


@dataclass(frozen=True)
class TarihCozumu:
    gun: date | None
    hafta: date | None
    gecersiz: bool


def katla(metin: str) -> str:
    return " ".join(turkce_kucult_katla(str(metin or "")).split())


def okul_yili(bugun: date) -> tuple[date, date]:
    y = bugun.year if bugun.month >= 8 else bugun.year - 1
    return date(y, 9, 1), date(y + 1, 7, 15)


def pazartesi(gun: date) -> date:
    return gun - timedelta(days=gun.weekday())


def _yil(ay: int, baslangic_yili: int) -> int:
    return baslangic_yili if ay >= 8 else baslangic_yili + 1


def _gun_kur(y: int, a: int, g: int) -> date | None:
    try:
        return date(y, a, g)
    except ValueError:
        return None


def hafta_etiketi_araligi(etiket: str, baslangic_yili: int) -> tuple[date, date] | None:
    m = _ETIKET.search(katla(etiket))
    if not m:
        return None
    a1, a2 = _AYLAR[m.group(2)], _AYLAR[m.group(4)]
    bas = _gun_kur(_yil(a1, baslangic_yili), a1, int(m.group(1)))
    son = _gun_kur(_yil(a2, baslangic_yili), a2, int(m.group(3)))
    return (bas, son) if bas and son else None


def yayin_tarihi(metin: str) -> date | None:
    m = _IMZA.search(str(metin or ""))
    return _gun_kur(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def _acik_tarihler(k: str, baslangic_yili: int) -> list[tuple[int, date]]:
    """Every explicit date in the folded text, with its position."""
    bulunan: list[tuple[int, date]] = []

    def yil_sec(ham: str | None, ay: int) -> int:
        if ham:
            y = int(ham)
            return y + 2000 if y < 100 else y
        return _yil(ay, baslangic_yili)

    for m in _GUN_AY.finditer(k):
        ay = _AYLAR[m.group(2)]
        g = _gun_kur(yil_sec(m.group(3), ay), ay, int(m.group(1)))
        if g:
            bulunan.append((m.start(), g))
    for m in _AY_GUN.finditer(k):
        ay = _AYLAR[m.group(1)]
        g = _gun_kur(yil_sec(m.group(3), ay), ay, int(m.group(2)))
        if g:
            bulunan.append((m.start(), g))
    for m in _SAYISAL.finditer(k):
        gun, ay = int(m.group(1)), int(m.group(2))
        if 1 <= ay <= 12:
            g = _gun_kur(yil_sec(m.group(3), ay), ay, gun)
            if g:
                bulunan.append((m.start(), g))
    return sorted(bulunan)


def tarih_coz(metin: str, yayin: date, okul_araligi: tuple[date, date]) -> TarihCozumu:
    k = katla(metin)
    bas, son = okul_araligi
    acik = _acik_tarihler(k, bas.year)
    for _, g in acik:
        if bas <= g <= son and g >= yayin:
            return TarihCozumu(g, None, False)

    gun_adi = _GUN_ADI.search(k)
    if _YARIN.search(k):
        return TarihCozumu(yayin + timedelta(days=1), None, False)
    if _BUGUN.search(k):
        return TarihCozumu(yayin, None, False)
    if _GELECEK_HAFTA.search(k):
        haftabasi = pazartesi(yayin) + timedelta(days=7)
        if gun_adi:
            return TarihCozumu(haftabasi + timedelta(days=_GUNLER[gun_adi.group(1)]), None, False)
        return TarihCozumu(None, haftabasi, False)
    if gun_adi:
        fark = (_GUNLER[gun_adi.group(1)] - yayin.weekday()) % 7 or 7
        return TarihCozumu(yayin + timedelta(days=fark), None, False)
    if _BU_HAFTA.search(k):
        return TarihCozumu(None, pazartesi(yayin), False)
    return TarihCozumu(None, None, bool(acik))
```

- [ ] **Adım 5: Testlerin geçtiğini gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_sinav_tarihi.py`
Expected: PASS (24 test)

- [ ] **Adım 6: Commit**

```bash
git add src/sinav_tarihi.py tests/test_sinav_tarihi.py
git commit -m "feat(sinav): tarih ifadelerini yayın bağlamıyla çözen saf modül

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Görev 2: Aday toplayıcı ve ön süzgeç (`src/sinav_kaynaklari.py`)

**Files:**
- Create: `src/sinav_kaynaklari.py`, `tests/sinav_fikstur.py`
- Test: `tests/test_sinav_kaynaklari.py`

**Interfaces:**
- Consumes: Görev 1 `katla`, `okul_yili`, `hafta_etiketi_araligi`, `yayin_tarihi`; `src.course_names.normalize_course`; `src.portal_susu.temiz_metin`
- Produces:
  - `@dataclass Aday(metin: str, ders: str | None, yayin: date | None, tur: str, konumlar: list[dict])` — `tur` ∈ `ders_karti | odev | duyuru | ek`; özellik `anahtar -> str` = `sha256(katla(metin))` hex
  - `on_suzgec(metin: str) -> bool`
  - `adaylar(veri: dict, bugun: date, ek_metinleri: dict[str, tuple[str, date | None]] | None = None, odev_ilk_gorulme: dict[str, str] | None = None, en_eski_gun: int = 45) -> list[Aday]` — yalnız ön süzgeçten geçenler, kopyaları birleşmiş, en yeni yayın önce
  - `kaynak_verisi(kok: Path) -> tuple[dict[str, tuple[str, date | None]], dict[str, str]]` — `(ek_metinleri, odev_ilk_gorulme)`
  - `tests/sinav_fikstur.py`: `KTT_KARTI`, `KTT_GOVDE`, `FEN_KARTI`, `FEN_OGESI`, `ING_KARTI`, `FR_KARTI`, `haftalar_verisi() -> dict`, `TAKVIM_SINAV: list[dict]`

- [ ] **Adım 1: Fikstürleri yaz** — `tests/sinav_fikstur.py` (canlı verinin 2026-10-16 biçimi; öğretmen adları silindi)

```python
"""Real-shape fixtures for the exam detector, measured on live data 2026-10-16.
Teacher names are replaced; the texts are otherwise the portal's own."""

KTT_KARTI = (
    "KTT-1 KONULARI\nÖğretmen A | 05.10.2026\nMATEMATİK KONU TARAMA TESTİ (KTT) KONULARI\n"
    "Sevgili Öğrencilerim,\n"
    "15 EKİM PERŞEMBE günü yapılacak olan Matematik KTT konu başlıkları aşağıdaki gibidir:\n"
    "TAM SAYILAR FARKLI GÖSTERİMLERİ\nRASYONEL SAYILAR VE FARKLI GÖSTERİMLERİ\n"
    "RASYONEL SAYILARIN SAYI DOĞRUSU ÜZERİNDE GÖSTERİMİ\nMUTLAK DEĞER\n"
    "RASYONEL SAYILARDA KARŞILAŞTIRMA VE SIRALAMA\nKısa sınav 20 soru test olacaktır.\n"
    "Hepinize iyi çalışmalar ve başarılar dilerim.")
# The portal renders each post twice: once with its title, once without.
KTT_GOVDE = KTT_KARTI.split("\n", 1)[1]
FEN_KARTI = (
    "5. hafta\nÖğretmen B | 05.10.2026\nSevgili Öğrenciler, 🌟\n"
    "Geçtiğimiz hafta hep birlikte keyifli bir yolculuğa çıkarak \"Uzay Çağı\" ünitemizi başarıyla tamamladık.\n"
    "Büyük Quiz Zamanı! 📝\nBu hafta ilk ünitemizin tamamını kapsayan bir quiz olacaksınız. "
    "Sınavda en yüksek başarıyı yakalamak için konu tekrarlarınızı düzenli yapmayı ve bol bol soru "
    "çözmeyi sakın unutmayın.")
FEN_OGESI = "Büyük Quiz Zamanı! 📝"
ING_KARTI = (
    "Week 2 / QUIZ\nÖğretmen C | 21.09.2026\nDear Students,\n\nThis week, we started the Present "
    "Perfect Tense. We learned the rules and practiced using common time expressions.\n"
    "Next week, you will have an Irregular Verbs Quiz, so please study the list that I shared on PORTAL.")
FR_KARTI = "Semaine 3 - Logements\nÖğretmen D | 28.09.2026\n\nQuizlet için linke tıkla : https://quizlet.com/join/x"


def haftalar_verisi() -> dict:
    return {
        "ders_icerikleri_haftalar": {
            "2. Hafta 21 Eyl. - 27 Eyl.": {
                "İngilizce Language": {"cards": [ING_KARTI, ING_KARTI.split("\n", 1)[1]], "items": [], "text": ""}},
            "3. Hafta 28 Eyl. - 04 Eki.": {
                "2. Yabancı Dil (F)": {"cards": [FR_KARTI], "items": [], "text": ""}},
            "4. Hafta 05 Eki. - 11 Eki.": {
                "Matematik": {"cards": ["Başka bir duyuru", KTT_KARTI, KTT_GOVDE], "items": [], "text": ""},
                "Fen Bilimleri": {"cards": [FEN_KARTI], "items": [FEN_OGESI], "text": ""}},
            "5. Hafta 12 Eki. - 18 Eki.": {
                "Matematik": {"cards": ["Başka bir duyuru", KTT_KARTI, KTT_GOVDE], "items": [], "text": ""}},
        },
        # The live open-week section carries a Selenium error for "Genel": no cards.
        "ders_icerikleri": {"Genel": {"tab_id": "tab_genel", "error": "Message: no such element"}},
        "odevlerim": {"homework": {"rows": []}},
        "duyurular": {"announcements": []},
        "takvim": [],
    }


def _takvim(baslik, bas, son="", tur="sinav"):
    return {"title": baslik, "start": bas, "end": son, "allDay": False, "backgroundColor": "",
            "extendedProps": {"calendar": tur}}


TAKVIM_SINAV = [
    _takvim("5-6-7. Sınıflar Özdebir Gelişim İzleme Sınavı GİS-1 (Türkiye Geneli) / 5-6-7th Grades "
            "Özdebir Monitoring Exam (Türkiye-wide)", "2026-10-23T09:00:00+03:00", "2026-10-23T12:10:00+03:00"),
    _takvim("5-6-7-8. Sınıflar Sebit Vcloud Kazanım Değerlendirme Uygulaması-1_TM / 5-6-7-8th Grades "
            "Sebit Vcloud Learning Outcome Assessment Application-1_TM", "2027-01-14T08:55:00+03:00",
            "2027-01-14T12:00:00+03:00"),
    _takvim("5-6-7-8. Sınıflar MEB 1. Dönem 2. Yazılı Sınav Haftası Başlangıcı / 5-6-7-8th Grades "
            "Beginning of MEB 1st Term 2nd Written Exam Week", "2027-01-04T08:00:00+03:00"),
    _takvim("Grade 7 English  (English Language)", "2026-10-13T16:00:00+03:00", tur="kisisel"),
]
```

- [ ] **Adım 2: Başarısız testi yaz** — `tests/test_sinav_kaynaklari.py`

```python
"""src/sinav_kaynaklari: free-text exam candidates with their source location and
publication date; the free keyword prefilter; the portal's duplicate cards merged."""
import json
from datetime import date

import pytest

from src.sinav_kaynaklari import Aday, adaylar, kaynak_verisi, on_suzgec
from tests.sinav_fikstur import FEN_KARTI, ING_KARTI, KTT_KARTI, haftalar_verisi

BUGUN = date(2026, 10, 16)


@pytest.mark.parametrize("metin", [
    "Matematik KTT konuları", "Büyük Quiz Zamanı!", "Cuma kısa sınav", "SINAV haftası",
    "Türkçe Ortak Yazılı", "Irregular Verbs Quiz", "20 soru test olacaktır", "GİS-1 uygulaması",
    "final exam", "konu tarama testi", "deneme sınavı", "ünite değerlendirme",
])
def test_on_suzgec_sinav_dili(metin):
    assert on_suzgec(metin)


@pytest.mark.parametrize("metin", [
    "Quizlet için linke tıkla", "Ödev Durumu: Değerlendirilmemiş", "Ders kitabını getirin", "contest",
])
def test_on_suzgec_sinav_dili_degil(metin):
    assert not on_suzgec(metin)


def test_ktt_kopyalari_tek_aday():
    sonuc = [a for a in adaylar(haftalar_verisi(), BUGUN) if a.ders == "Matematik"]
    assert len(sonuc) == 1
    assert sonuc[0].metin == KTT_KARTI
    assert sonuc[0].tur == "ders_karti"
    assert sonuc[0].yayin == date(2026, 10, 5)
    assert sonuc[0].konumlar == [
        {"bolum": "ders_icerikleri_haftalar", "hafta": "4. Hafta 05 Eki. - 11 Eki.", "ders": "Matematik", "sira": 1},
        {"bolum": "ders_icerikleri_haftalar", "hafta": "5. Hafta 12 Eki. - 18 Eki.", "ders": "Matematik", "sira": 1},
    ]


def test_fen_ogesi_kartin_icinde_kalir():
    fen = [a for a in adaylar(haftalar_verisi(), BUGUN) if a.ders == "Fen Bilimleri"]
    assert [a.metin for a in fen] == [FEN_KARTI]


def test_ders_adi_normalize_ve_quizlet_suzulur():
    sonuc = adaylar(haftalar_verisi(), BUGUN)
    assert {a.ders for a in sonuc} == {"Matematik", "Fen Bilimleri", "İngilizce"}
    ing = next(a for a in sonuc if a.ders == "İngilizce")
    assert ing.metin == ING_KARTI and ing.yayin == date(2026, 9, 21)


def test_en_yeni_once_ve_eski_yayin_atlanir():
    sonuc = adaylar(haftalar_verisi(), BUGUN)
    assert [a.yayin for a in sonuc] == sorted([a.yayin for a in sonuc], reverse=True)
    # 2026-11-10 − 45 gün = 2026-09-26: 21.09'daki İngilizce kartı düşer, 05.10'dakiler kalır.
    assert {a.ders for a in adaylar(haftalar_verisi(), date(2026, 11, 10))} == {"Matematik", "Fen Bilimleri"}


def test_imzasiz_kart_hafta_baslangicini_yayin_sayar():
    veri = haftalar_verisi()
    veri["ders_icerikleri_haftalar"]["4. Hafta 05 Eki. - 11 Eki."]["Türkçe"] = {
        "cards": ["Türkçe yazılı sınavı Cuma günü"], "items": [], "text": ""}
    tr = next(a for a in adaylar(veri, BUGUN) if a.ders == "Türkçe")
    assert tr.yayin == date(2026, 10, 5)


def test_kartsiz_sekmenin_metni_aday_kartliysa_degil():
    veri = haftalar_verisi()
    hafta = veri["ders_icerikleri_haftalar"]["4. Hafta 05 Eki. - 11 Eki."]
    hafta["Sosyal Bilgiler"] = {"cards": [], "items": [], "text": "Sosyal yazılı sınavı haftaya"}
    hafta["Matematik"]["text"] = KTT_KARTI + "\nBaşka bir duyuru"
    sonuc = adaylar(veri, BUGUN)
    sosyal = next(a for a in sonuc if a.ders == "Sosyal Bilgiler")
    assert sosyal.konumlar[0]["metin"] is True and sosyal.yayin == date(2026, 10, 5)
    assert [a.metin for a in sonuc if a.ders == "Matematik"] == [KTT_KARTI]


def test_odev_duyuru_ek_adaylari():
    veri = haftalar_verisi()
    veri["odevlerim"]["homework"]["rows"] = [{
        "Ders Adı": "Matematik", "Ödev Başlığı": "KTT Hazırlık", "Ödev Son Teslim Tarihi": "16.10.2026 08:00",
        "detail": {"description": "Cuma günü kısa sınav var.", "attachments": []}}]
    veri["duyurular"]["announcements"] = [{"Başlık": "7. sınıflar deneme sınavı", "Tarih": "10.10.2026",
                                          "Başlık_url": "https://x"}]
    sonuc = adaylar(veri, BUGUN,
                    ek_metinleri={"abc": ("Fen yazılı konuları: Uzay Çağı", date(2026, 10, 10))},
                    odev_ilk_gorulme={"KTT Hazırlık": "2026-10-12T09:00:00"})
    odev = next(a for a in sonuc if a.tur == "odev")
    assert (odev.ders, odev.yayin) == ("Matematik", date(2026, 10, 12))
    assert odev.konumlar == [{"bolum": "odev", "baslik": "KTT Hazırlık", "teslim": "16.10.2026 08:00"}]
    duyuru = next(a for a in sonuc if a.tur == "duyuru")
    assert duyuru.yayin == date(2026, 10, 10) and "https://x" not in duyuru.metin
    ek = next(a for a in sonuc if a.tur == "ek")
    assert (ek.ders, ek.yayin, ek.konumlar) == (None, date(2026, 10, 10), [{"bolum": "ek", "id": "abc"}])


def test_anahtar_katlanmis_metnin_ozeti():
    a = Aday("Matematik  KTT", "Matematik", None, "ders_karti", [])
    b = Aday("MATEMATİK KTT", "Matematik", None, "ders_karti", [])
    assert a.anahtar == b.anahtar and len(a.anahtar) == 64


def test_kaynak_verisi_dosyalardan(tmp_path):
    (tmp_path / "output").mkdir()
    (tmp_path / "content/portal-ekleri").mkdir(parents=True)
    (tmp_path / "output/portal_ekleri.json").write_text(json.dumps(
        {"ekler": {"abc": {"id": "abc", "first_seen": "2026-10-10T08:00:00"},
                   "yok": {"id": "yok", "first_seen": "2026-10-11T08:00:00"}}}), encoding="utf-8")
    (tmp_path / "content/portal-ekleri/abc.txt").write_text("x" * 5000, encoding="utf-8")
    (tmp_path / "output/homework_first_seen.json").write_text('{"Ödev": "2026-10-12T09:00:00"}', encoding="utf-8")
    ekler, ilk = kaynak_verisi(tmp_path)
    assert list(ekler) == ["abc"]
    assert ekler["abc"] == ("x" * 4000, date(2026, 10, 10))
    assert ilk == {"Ödev": "2026-10-12T09:00:00"}


def test_kaynak_verisi_dosya_yoksa_bos(tmp_path):
    assert kaynak_verisi(tmp_path) == ({}, {})
```

- [ ] **Adım 3: Testin başarısız olduğunu gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_sinav_kaynaklari.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.sinav_kaynaklari'`

- [ ] **Adım 4: Uygula** — `src/sinav_kaynaklari.py`

```python
"""Serbest metin sınav adayları (spec §5 "Adaylar", "Ön süzgeç").

Her aday metniyle, dersiyle, yayın tarihiyle ve portaldaki konum(lar)ıyla gelir.
Portal her yazıyı iki kart olarak verir (başlıklı ve başlıksız) ve yazı sonraki
haftaya taşınır: aynı katlanmış metin tek aday olur, konumları birleşir; başka
bir kartın içinde kalan kart ve öğe atılır. Ön süzgeç ücretsizdir: eşleşmeyen
parça modele gitmez."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.course_names import normalize_course
from src.portal_susu import temiz_metin
from src.sinav_tarihi import hafta_etiketi_araligi, katla, okul_yili, yayin_tarihi

EK_KARAKTER_SINIRI = 4000
_SUZGEC = re.compile(
    r"\b(sinav\w*|yazili\w*|quiz(?:zes)?|ktt|konu tarama\w*|deneme\w*|test(?:i|ler|leri|s)?"
    r"|exam\w*|degerlendirme\b|gis)\b")
_TARIH = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b")


@dataclass
class Aday:
    metin: str
    ders: str | None
    yayin: date | None
    tur: str
    konumlar: list[dict] = field(default_factory=list)

    @property
    def anahtar(self) -> str:
        return hashlib.sha256(katla(self.metin).encode("utf-8")).hexdigest()


def on_suzgec(metin: str) -> bool:
    return bool(_SUZGEC.search(katla(metin)))


def _gun(deger: Any) -> date | None:
    try:
        return datetime.fromisoformat(str(deger)[:19]).date()
    except (TypeError, ValueError):
        return None


def _ilk_tarih(metin: str) -> date | None:
    m = _TARIH.search(metin)
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _ders_parcalari(bolum: Any, etiket: str | None, aralik: tuple[date, date] | None,
                    bolum_adi: str) -> list[Aday]:
    sonuc: list[Aday] = []
    if not isinstance(bolum, dict):
        return sonuc
    for sekme, icerik in bolum.items():
        if not isinstance(icerik, dict):
            continue
        ders = normalize_course(sekme) or sekme
        kartlar = icerik.get("cards") or []
        parcalar = [("kart", c) for c in kartlar] + [("oge", o) for o in icerik.get("items") or []]
        # `text` is every card of the tab run together: with cards it would only
        # swallow them (and their locations); without cards it is the only text.
        if not kartlar and isinstance(icerik.get("text"), str):
            parcalar.append(("metin", icerik["text"]))
        for sira, (tip, ham) in enumerate(parcalar):
            metin = temiz_metin(ham if isinstance(ham, str) else json.dumps(ham, ensure_ascii=False))
            if not metin.strip():
                continue
            yayin = yayin_tarihi(metin) or (aralik[0] if aralik else None)
            konum = {"bolum": bolum_adi, "hafta": etiket, "ders": sekme, "sira": sira}
            if tip != "kart":
                konum[tip] = True
            sonuc.append(Aday(metin, ders, yayin, "ders_karti", [konum]))
    return sonuc


def _odevler(veri: dict, ilk_gorulme: dict[str, str]) -> list[Aday]:
    satirlar = ((veri.get("odevlerim") or {}).get("homework") or {}).get("rows") or []
    sonuc = []
    for r in satirlar:
        if not isinstance(r, dict):
            continue
        baslik = str(r.get("Ödev Başlığı") or "").strip()
        aciklama = temiz_metin((r.get("detail") or {}).get("description") if isinstance(r.get("detail"), dict) else "")
        metin = "\n".join(x for x in (baslik, aciklama) if x)
        if not metin:
            continue
        sonuc.append(Aday(metin, normalize_course(r.get("Ders Adı") or "") or None,
                          _gun(ilk_gorulme.get(baslik)), "odev",
                          [{"bolum": "odev", "baslik": baslik, "teslim": r.get("Ödev Son Teslim Tarihi")}]))
    return sonuc


def _duyurular(veri: dict) -> list[Aday]:
    satirlar = (veri.get("duyurular") or {}).get("announcements") or []
    sonuc = []
    for sira, r in enumerate(satirlar):
        if not isinstance(r, dict):
            continue
        degerler = [str(v) for k, v in r.items() if not str(k).endswith("_url") and v]
        metin = temiz_metin("\n".join(degerler))
        if metin.strip():
            sonuc.append(Aday(metin, None, _ilk_tarih(metin), "duyuru", [{"bolum": "duyuru", "sira": sira}]))
    return sonuc


def _birlestir(liste: list[Aday]) -> list[Aday]:
    tekil: dict[str, Aday] = {}
    for a in liste:
        if a.anahtar in tekil:
            tekil[a.anahtar].konumlar.extend(k for k in a.konumlar if k not in tekil[a.anahtar].konumlar)
        else:
            tekil[a.anahtar] = Aday(a.metin, a.ders, a.yayin, a.tur, list(a.konumlar))
    kalan = list(tekil.values())
    katli = {id(a): katla(a.metin) for a in kalan}
    sonuc = []
    for a in kalan:
        kapsayan = any(b is not a and b.ders == a.ders and katli[id(a)] in katli[id(b)]
                       and len(katli[id(b)]) > len(katli[id(a)]) for b in kalan)
        if not kapsayan:
            sonuc.append(a)
    return sonuc


def adaylar(veri: dict, bugun: date, ek_metinleri: dict[str, tuple[str, date | None]] | None = None,
            odev_ilk_gorulme: dict[str, str] | None = None, en_eski_gun: int = 45) -> list[Aday]:
    bas_yil = okul_yili(bugun)[0].year
    ham: list[Aday] = []
    haftalar = veri.get("ders_icerikleri_haftalar") or {}
    if isinstance(haftalar, dict):
        for etiket, bolum in haftalar.items():
            ham += _ders_parcalari(bolum, etiket, hafta_etiketi_araligi(etiket, bas_yil), "ders_icerikleri_haftalar")
    ham += _ders_parcalari(veri.get("ders_icerikleri"), None, None, "ders_icerikleri")
    ham += _odevler(veri, odev_ilk_gorulme or {})
    ham += _duyurular(veri)
    for ek_id, (metin, ilk) in (ek_metinleri or {}).items():
        ham.append(Aday(metin, None, ilk, "ek", [{"bolum": "ek", "id": ek_id}]))

    sinir = bugun - timedelta(days=en_eski_gun)
    suzulmus = [a for a in ham if on_suzgec(a.metin) and (a.yayin is None or a.yayin >= sinir)]
    sonuc = _birlestir(suzulmus)
    return sorted(sonuc, key=lambda a: a.yayin or bugun, reverse=True)


def _json(yol: Path) -> Any:
    try:
        return json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def kaynak_verisi(kok: Path) -> tuple[dict[str, tuple[str, date | None]], dict[str, str]]:
    ekler: dict[str, tuple[str, date | None]] = {}
    dizin = _json(kok / "output/portal_ekleri.json")
    kayitlar = (dizin or {}).get("ekler") if isinstance(dizin, dict) else None
    for ek_id, kayit in (kayitlar or {}).items():
        yol = kok / "content/portal-ekleri" / f"{ek_id}.txt"
        try:
            metin = yol.read_text(encoding="utf-8")[:EK_KARAKTER_SINIRI]
        except OSError:
            continue
        if metin.strip():
            ekler[ek_id] = (metin, _gun((kayit or {}).get("first_seen")))
    ilk = _json(kok / "output/homework_first_seen.json")
    return ekler, (ilk if isinstance(ilk, dict) else {})
```

- [ ] **Adım 5: Testlerin geçtiğini gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_sinav_kaynaklari.py tests/test_sinav_tarihi.py`
Expected: PASS. `test_on_suzgec_sinav_dili[ünite değerlendirme]` kırmızıysa `_SUZGEC`'teki `degerlendirme\b` ile katlanmış "degerlendirme"yi karşılaştır; "Değerlendirilmemiş" negatif kalmalı.

- [ ] **Adım 6: Commit**

```bash
git add src/sinav_kaynaklari.py tests/sinav_fikstur.py tests/test_sinav_kaynaklari.py
git commit -m "feat(sinav): serbest metin adayları, ön süzgeç ve portal kopyalarının birleşmesi

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Görev 3: Çıkarım — Haiku okuyucusu, önbellek, bütçe defteri, uydurma kapısı (`src/sinav_cikarimi.py`)

**Files:**
- Create: `src/sinav_cikarimi.py`
- Test: `tests/test_sinav_cikarimi.py`

**Interfaces:**
- Consumes: Görev 1 `katla`, `okul_yili`, `tarih_coz`; Görev 2 `Aday`; `src.ocr_katmani.OcrDefteri(yol, tavan, simdi)` (`izin_var()`, `yaz(motor, girdi, cikti)`, `harcanan()`); `src.claude_api.istemci`, `metin`, `ClaudeYapilandirilmamis`; `src.course_names.normalize_course`
- Produces:
  - Sabitler: `ISTEM_SURUMU = 1`, `SINAV_VARSAYILAN_MODEL = "claude-haiku-4-5"`, `AYLIK_TAVAN_USD` (env `TEDY_SINAV_AYLIK_USD`, 2), `SINAV_TURLERI`, `TUR_ADI: dict[str, str]`, `CIKARIM_SEMASI`, `ONBELLEK`, `DEFTER` (PurePosixPath)
  - `class CikarimHatasi(RuntimeError)`
  - `@dataclass OkumaSonucu(satirlar: list[dict], girdi: int, cikti: int)`
  - `class ClaudeSinavOkuyucu(istemci_fabrikasi=claude_api.istemci, model: str | None = None)` — `.model: str`, `.oku(aday: Aday, bugun: date, zaman_asimi: float) -> OkumaSonucu`
  - `@dataclass Bulgu(ders: str, tur: str, baslik: str, tarih: date | None, hafta: date | None, saat: str | None, konular: list[str], alinti: str, aday: Aday)`
  - `uydurma_kapisi(satirlar: list[dict], aday: Aday, bugun: date) -> list[Bulgu]`
  - `@dataclass CikarimSonucu(bulgular: list[Bulgu], aday: int, incelenen: int, incelenmedi: int, butce_usd: float, hatalar: list[str])`
  - `class SinavCikarici(kok: Path, okuyucu, tavan: float = AYLIK_TAVAN_USD, saat=time.monotonic, simdi=datetime.now)` — `.cikar(adaylar: list[Aday], bugun: date, bitis: float) -> CikarimSonucu`

- [ ] **Adım 1: Başarısız testi yaz** — `tests/test_sinav_cikarimi.py`

```python
"""src/sinav_cikarimi: the Haiku reader (fake client), the cache, the monthly
ledger and the deterministic anti-fabrication gate. No test reaches the API."""
import json
from datetime import date
from types import SimpleNamespace

import pytest

import src.sinav_cikarimi as sc
from src.claude_api import ClaudeYapilandirilmamis
from src.sinav_cikarimi import (Bulgu, CikarimHatasi, ClaudeSinavOkuyucu, OkumaSonucu, SinavCikarici,
                                uydurma_kapisi)
from src.sinav_kaynaklari import Aday
from tests.sinav_fikstur import ING_KARTI, KTT_KARTI

BUGUN = date(2026, 10, 16)
KTT = Aday(KTT_KARTI, "Matematik", date(2026, 10, 5), "ders_karti", [{"bolum": "ders_icerikleri_haftalar"}])
ING = Aday(ING_KARTI, "İngilizce", date(2026, 9, 21), "ders_karti", [])


def _satir(**kw):
    s = {"ders": "Matematik", "tur": "konu_tarama", "baslik": "Matematik KTT",
         "tarih_ifadesi": "15 EKİM PERŞEMBE", "tarih": "2026-10-16", "saat": "",
         "konular": ["Tam sayılar farklı gösterimleri", "Mutlak değer", "Üslü sayılar"],
         "alinti": "15 EKİM PERŞEMBE günü yapılacak olan Matematik KTT"}
    s.update(kw)
    return s


# --- uydurma kapısı ------------------------------------------------------------

def test_kapi_bizim_tarihimiz_kazanir_konu_kaynakta_olmali():
    [b] = uydurma_kapisi([_satir()], KTT, BUGUN)
    assert (b.ders, b.tur, b.baslik, b.tarih, b.hafta, b.saat) == \
        ("Matematik", "konu_tarama", "Matematik KTT", date(2026, 10, 15), None, None)
    assert b.konular == ["Tam sayılar farklı gösterimleri", "Mutlak değer"]
    assert b.aday is KTT


def test_kapi_kaynakta_olmayan_alinti_kaydi_atar():
    assert uydurma_kapisi([_satir(alinti="Yarın Matematik yazılısı var")], KTT, BUGUN) == []


def test_kapi_kaynakta_olmayan_tarih_ifadesi_alintiya_duser():
    [b] = uydurma_kapisi([_satir(tarih_ifadesi="16 Ekim Cuma")], KTT, BUGUN)
    assert b.tarih == date(2026, 10, 15)


def test_kapi_goreli_hafta():
    [b] = uydurma_kapisi([_satir(ders="İngilizce", tur="kisa_sinav", baslik="Irregular Verbs Quiz",
                                 tarih_ifadesi="Next week", tarih="", konular=["Modal verbs"],
                                 alinti="Next week, you will have an Irregular Verbs Quiz")], ING, BUGUN)
    assert (b.tarih, b.hafta, b.konular, b.baslik) == (None, date(2026, 9, 28), [], "Irregular Verbs Quiz")


def test_kapi_yalniz_gecmis_tarih_kaydi_atar():
    aday = Aday("Öğretmen | 16.10.2026\n15 Ekim'de yapılan KTT sonuçları açıklandı.", "Matematik",
                date(2026, 10, 16), "ders_karti", [])
    satir = _satir(tarih_ifadesi="15 Ekim'de", alinti="15 Ekim'de yapılan KTT sonuçları açıklandı.", konular=[])
    assert uydurma_kapisi([satir], aday, BUGUN) == []


def test_kapi_saat_kaynakta_yoksa_atilir_varsa_tutulur():
    [b] = uydurma_kapisi([_satir(saat="09:00")], KTT, BUGUN)
    assert b.saat is None
    aday = Aday("Matematik yazılısı 20 Ekim 10.30'da", "Matematik", date(2026, 10, 12), "ders_karti", [])
    [b] = uydurma_kapisi([_satir(tur="yazili", baslik="Matematik yazılısı", tarih_ifadesi="20 Ekim",
                                 saat="10.30", konular=[], alinti="Matematik yazılısı 20 Ekim 10.30'da")],
                         aday, BUGUN)
    assert (b.tarih, b.saat) == (date(2026, 10, 20), "10:30")


def test_kapi_baslik_kaynakta_yoksa_turden_kurulur():
    [b] = uydurma_kapisi([_satir(baslik="Matematik 2. Yazılı")], KTT, BUGUN)
    assert b.baslik == "Matematik KTT"


def test_kapi_bilinmeyen_tur_diger():
    [b] = uydurma_kapisi([_satir(tur="quiz")], KTT, BUGUN)
    assert b.tur == "diger"


def test_kapi_ek_dersi_metinde_gecmeli():
    ek = Aday("Fen yazılı konuları 20 Ekim: Uzay Çağı", None, date(2026, 10, 12), "ek", [])
    satir = _satir(ders="Fen Bilimleri", tur="yazili", baslik="Fen yazılı", tarih_ifadesi="20 Ekim",
                   konular=["Uzay Çağı"], alinti="Fen yazılı konuları 20 Ekim")
    [b] = uydurma_kapisi([satir], ek, BUGUN)
    assert b.ders == "Fen Bilimleri"
    [b] = uydurma_kapisi([dict(satir, ders="Matematik")], ek, BUGUN)
    assert b.ders == "Genel"


def test_kapi_ders_kartinin_dersi_esastir():
    [b] = uydurma_kapisi([_satir(ders="Fen Bilimleri")], KTT, BUGUN)
    assert b.ders == "Matematik"


# --- okuyucu -------------------------------------------------------------------

class SahteIstemci:
    def __init__(self, yanit=None, hata=None):
        self.cagrilar, self.yanit, self.hata = [], yanit, hata
        self.messages = self

    def create(self, **kw):
        self.cagrilar.append(kw)
        if self.hata:
            raise self.hata
        return self.yanit


def _yanit(satirlar, stop="end_turn"):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps({"sinavlar": satirlar}))],
                           stop_reason=stop, usage=SimpleNamespace(input_tokens=2000, output_tokens=300))


def test_okuyucu_yapilandirilmis_cikti_ister(monkeypatch):
    monkeypatch.delenv("TEDY_SINAV_MODEL", raising=False)
    istemci = SahteIstemci(_yanit([_satir()]))
    okuyucu = ClaudeSinavOkuyucu(istemci_fabrikasi=lambda timeout, max_retries: istemci)
    sonuc = okuyucu.oku(KTT, BUGUN, zaman_asimi=20)
    assert sonuc == OkumaSonucu([_satir()], 2000, 300)
    [cagri] = istemci.cagrilar
    assert cagri["model"] == "claude-haiku-4-5" == okuyucu.model
    assert cagri["output_config"] == {"format": {"type": "json_schema", "schema": sc.CIKARIM_SEMASI}}
    istem = cagri["messages"][0]["content"]
    assert "2026-10-16" in istem and "2026-10-05" in istem and "Matematik" in istem and "MUTLAK DEĞER" in istem


def test_okuyucu_model_ortamdan(monkeypatch):
    monkeypatch.setenv("TEDY_SINAV_MODEL", "baska-model")
    assert ClaudeSinavOkuyucu(istemci_fabrikasi=lambda **k: None).model == "baska-model"


@pytest.mark.parametrize("istemci", [
    SahteIstemci(_yanit([], stop="refusal")),
    SahteIstemci(SimpleNamespace(content=[SimpleNamespace(type="text", text="json değil")],
                                 stop_reason="end_turn", usage=SimpleNamespace(input_tokens=1, output_tokens=1))),
])
def test_okuyucu_hatasi_cikarim_hatasi(istemci):
    okuyucu = ClaudeSinavOkuyucu(istemci_fabrikasi=lambda timeout, max_retries: istemci)
    with pytest.raises(CikarimHatasi):
        okuyucu.oku(KTT, BUGUN, zaman_asimi=20)


def test_okuyucu_anahtar_yoksa_cikarim_hatasi():
    def fabrika(timeout, max_retries):
        raise ClaudeYapilandirilmamis("ANTHROPIC_API_KEY ayarlı değil")
    with pytest.raises(CikarimHatasi):
        ClaudeSinavOkuyucu(istemci_fabrikasi=fabrika).oku(KTT, BUGUN, zaman_asimi=20)


# --- çıkarıcı: önbellek, defter, süre ---------------------------------------------

class SahteOkuyucu:
    model = "claude-haiku-4-5"

    def __init__(self, satirlar=None, hata_metni=None):
        self.cagrilar, self.satirlar, self.hata_metni = [], satirlar, hata_metni

    def oku(self, aday, bugun, zaman_asimi):
        self.cagrilar.append(aday.anahtar)
        if self.hata_metni and self.hata_metni in aday.metin:
            raise CikarimHatasi("ağ")
        return OkumaSonucu(self.satirlar if self.satirlar is not None else [_satir()], 2000, 300)


class Saat:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def _cikarici(tmp_path, okuyucu, tavan=2.0):
    return SinavCikarici(tmp_path, okuyucu, tavan=tavan, saat=Saat())


def test_cikarici_onbellek_ikinci_turda_ucret_yok(tmp_path):
    okuyucu = SahteOkuyucu()
    ilk = _cikarici(tmp_path, okuyucu).cikar([KTT], BUGUN, bitis=2000)
    assert (ilk.aday, ilk.incelenen, ilk.incelenmedi, len(ilk.bulgular)) == (1, 1, 0, 1)
    assert ilk.butce_usd == pytest.approx((2000 * 1.0 + 300 * 5.0) / 1_000_000)
    ikinci = _cikarici(tmp_path, okuyucu).cikar([KTT], BUGUN, bitis=2000)
    assert len(okuyucu.cagrilar) == 1
    assert (ikinci.incelenen, len(ikinci.bulgular)) == (1, 1)
    assert ikinci.butce_usd == pytest.approx(ilk.butce_usd)


def test_cikarici_istem_surumu_degisince_yeniden_sorar(tmp_path, monkeypatch):
    okuyucu = SahteOkuyucu()
    _cikarici(tmp_path, okuyucu).cikar([KTT], BUGUN, bitis=2000)
    monkeypatch.setattr(sc, "ISTEM_SURUMU", sc.ISTEM_SURUMU + 1)
    _cikarici(tmp_path, okuyucu).cikar([KTT], BUGUN, bitis=2000)
    assert len(okuyucu.cagrilar) == 2


def test_cikarici_tavan_dolunca_incelenmedi(tmp_path):
    okuyucu = SahteOkuyucu()
    sonuc = _cikarici(tmp_path, okuyucu, tavan=0.0).cikar([KTT, ING], BUGUN, bitis=2000)
    assert (okuyucu.cagrilar, sonuc.incelenen, sonuc.incelenmedi, sonuc.bulgular) == ([], 0, 2, [])


def test_cikarici_sure_bitince_incelenmedi(tmp_path):
    okuyucu = SahteOkuyucu()
    sonuc = _cikarici(tmp_path, okuyucu).cikar([KTT], BUGUN, bitis=1005)
    assert (okuyucu.cagrilar, sonuc.incelenmedi) == ([], 1)


def test_cikarici_model_hatasi_digerlerini_durdurmaz(tmp_path):
    okuyucu = SahteOkuyucu(satirlar=[], hata_metni="KTT-1")
    sonuc = _cikarici(tmp_path, okuyucu).cikar([KTT, ING], BUGUN, bitis=2000)
    assert (sonuc.incelenen, sonuc.incelenmedi, sonuc.hatalar) == (1, 1, ["ağ"])
    assert not (tmp_path / "output/sinav_cikarim_onbellegi.json").read_text(encoding="utf-8").count(KTT.anahtar)
```

- [ ] **Adım 2: Testin başarısız olduğunu gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_sinav_cikarimi.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.sinav_cikarimi'`

- [ ] **Adım 3: Uygula** — `src/sinav_cikarimi.py`

```python
"""Serbest metinden sınav çıkarımı (spec §5): Claude Haiku yapılandırılmış çıktı,
önbellek, aylık bütçe ve deterministik uydurma kapısı.

Model yalnız ön süzgeçten geçen, önbellekte olmayan metni görür. Kapı modelin
dediğini kaynağa karşı sınar: alıntı ve her konu kaynakta geçmeli; tarih yalnız
kaynakta doğrulanan ifadeden bizim çözümleyicimizle çıkar (model tarihi tek
başına kullanılmaz); saat kaynakta yazmalı; başlığın sözcükleri kaynakta yoksa
başlık türden kurulur."""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from src import claude_api
from src.course_names import normalize_course
from src.json_utils import atomic_json_dump
from src.ocr_katmani import OcrDefteri
from src.sinav_kaynaklari import Aday
from src.sinav_tarihi import katla, okul_yili, tarih_coz

ISTEM_SURUMU = 1
SINAV_VARSAYILAN_MODEL = "claude-haiku-4-5"
AYLIK_TAVAN_USD = float(os.environ.get("TEDY_SINAV_AYLIK_USD", "2"))
ONBELLEK = PurePosixPath("output/sinav_cikarim_onbellegi.json")
DEFTER = PurePosixPath("output/sinav_cikarim_defteri.json")
CAGRI_EN_AZ_SURE = 8.0
CAGRI_EN_COK_SURE = 30.0
METIN_SINIRI = 6000
SINAV_TURLERI = ["yazili", "kisa_sinav", "konu_tarama", "deneme", "ortak_sinav", "diger"]
TUR_ADI = {"yazili": "Yazılı", "kisa_sinav": "Kısa sınav", "konu_tarama": "KTT", "deneme": "Deneme",
           "ortak_sinav": "Ortak sınav", "diger": "Sınav"}
_ALANLAR = ["ders", "tur", "baslik", "tarih_ifadesi", "tarih", "saat", "konular", "alinti"]
CIKARIM_SEMASI = {
    "type": "object", "additionalProperties": False, "required": ["sinavlar"],
    "properties": {"sinavlar": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": _ALANLAR,
        "properties": {
            "ders": {"type": "string"}, "tur": {"type": "string", "enum": SINAV_TURLERI},
            "baslik": {"type": "string"}, "tarih_ifadesi": {"type": "string"},
            "tarih": {"type": "string"}, "saat": {"type": "string"},
            "konular": {"type": "array", "items": {"type": "string"}}, "alinti": {"type": "string"},
        }}}},
}
_SAAT = re.compile(r"^(\d{1,2})[:.](\d{2})$")
_SOZCUK = re.compile(r"[0-9a-z]{3,}")

ISTEM = """Sen bir okul duyurusu okuyucususun. Aşağıdaki metin 7. sınıf öğrencisi Işık'ın okul portalından.
Metinde DUYURULAN, yapılacak ya da yakında yapılacak sınavları çıkar: yazılı, kısa sınav/quiz,
konu tarama testi (KTT), deneme, ortak sınav.

Bugün: {bugun} · Metnin yayın tarihi: {yayin} · Metnin dersi: {ders}

Her sınav için:
- ders: metnin dersi; metin başka bir ders söylüyorsa o ders; ders dışı ortak sınavsa "Genel".
- tur: yazili | kisa_sinav | konu_tarama | deneme | ortak_sinav | diger
- baslik: kısa ad, metindeki sözcüklerle (ör. "Matematik KTT", "Irregular Verbs Quiz").
- tarih_ifadesi: metinde sınavın zamanını söyleyen ifade, metindeki gibi birebir ("15 EKİM PERŞEMBE",
  "Next week", "bu hafta"). Yoksa boş.
- tarih: tarih_ifadesi açık bir gün söylüyorsa YYYY-AA-GG, yoksa boş.
- saat: metinde yazıyorsa SS:DD, yoksa boş.
- konular: metinde sınavın konusu olarak sayılan başlıklar, metindeki sözcüklerle; yoksa boş liste.
- alinti: sınavı duyuran cümle, metinden birebir kopya (en çok 300 karakter).

Kurallar:
- Metinde olmayan bir şeyi yazma, tahmin etme. Emin değilsen alanı boş bırak.
- Geçmiş bir sınavın sonucu, ödev, etkinlik ya da "Quizlet" gibi bir uygulama sınav değildir.
- Sınav yoksa boş liste döndür.

METİN:
<<<
{metin}
>>>"""


class CikarimHatasi(RuntimeError):
    """The model call failed or answered something unusable; nothing is cached."""


@dataclass
class OkumaSonucu:
    satirlar: list[dict]
    girdi: int
    cikti: int


class ClaudeSinavOkuyucu:
    def __init__(self, istemci_fabrikasi: Callable[..., Any] = claude_api.istemci, model: str | None = None):
        self._fabrika = istemci_fabrikasi
        self.model = model or os.environ.get("TEDY_SINAV_MODEL", "").strip() or SINAV_VARSAYILAN_MODEL

    def oku(self, aday: Aday, bugun: date, zaman_asimi: float) -> OkumaSonucu:
        istem = ISTEM.format(bugun=bugun.isoformat(), yayin=aday.yayin.isoformat() if aday.yayin else "bilinmiyor",
                             ders=aday.ders or "belirtilmemiş", metin=aday.metin[:METIN_SINIRI])
        try:
            istemci = self._fabrika(timeout=zaman_asimi, max_retries=0)
            yanit = istemci.messages.create(
                model=self.model, max_tokens=2000,
                messages=[{"role": "user", "content": istem}],
                output_config={"format": {"type": "json_schema", "schema": CIKARIM_SEMASI}})
        except Exception as e:  # anthropic.APIError, ClaudeYapilandirilmamis, timeouts
            raise CikarimHatasi(str(e)[:120] or type(e).__name__) from e
        if getattr(yanit, "stop_reason", "") == "refusal":
            raise CikarimHatasi("model reddetti")
        try:
            veri = json.loads(claude_api.metin(yanit))
        except ValueError as e:
            raise CikarimHatasi("model çıktısı JSON değil") from e
        satirlar = [s for s in (veri.get("sinavlar") or []) if isinstance(s, dict)] if isinstance(veri, dict) else []
        kullanim = getattr(yanit, "usage", None)
        return OkumaSonucu(satirlar, int(getattr(kullanim, "input_tokens", 0) or 0),
                           int(getattr(kullanim, "output_tokens", 0) or 0))


@dataclass
class Bulgu:
    ders: str
    tur: str
    baslik: str
    tarih: date | None
    hafta: date | None
    saat: str | None
    konular: list[str]
    alinti: str
    aday: Aday


def _ders(aday: Aday, model_dersi: Any, kaynak: str) -> str:
    if aday.tur in ("ders_karti", "odev") and aday.ders and aday.ders != "Genel":
        return aday.ders
    aday_ders = normalize_course(str(model_dersi or "")) or ""
    ilk = katla(aday_ders).split()[:1]
    if ilk and re.search(rf"\b{re.escape(ilk[0])}\b", kaynak):
        return aday_ders
    return "Genel"


def _baslik(model_basligi: Any, ders: str, tur: str, kaynak: str) -> str:
    baslik = " ".join(str(model_basligi or "").split())[:80]
    sozcukler = _SOZCUK.findall(katla(baslik))
    if sozcukler and all(s in kaynak or s in katla(ders) for s in sozcukler):
        return baslik
    return f"{ders} {TUR_ADI[tur]}" if ders != "Genel" else TUR_ADI[tur]


def uydurma_kapisi(satirlar: list[dict], aday: Aday, bugun: date) -> list[Bulgu]:
    kaynak = katla(aday.metin)
    yayin = aday.yayin or bugun
    aralik = okul_yili(bugun)
    sonuc = []
    for s in satirlar:
        alinti = " ".join(str(s.get("alinti") or "").split())
        if not alinti or katla(alinti) not in kaynak:
            continue
        ifade = str(s.get("tarih_ifadesi") or "").strip()
        cozum = tarih_coz(ifade if ifade and katla(ifade) in kaynak else alinti, yayin, aralik)
        if cozum.gun is None and cozum.hafta is None and cozum.gecersiz:
            continue
        m = _SAAT.match(str(s.get("saat") or "").strip())
        saat = f"{int(m.group(1)):02d}:{m.group(2)}" if m and str(s.get("saat")).strip() in aday.metin else None
        konular: list[str] = []
        for k in s.get("konular") or []:
            k = " ".join(str(k).split())
            if k and katla(k) in kaynak and k not in konular:
                konular.append(k)
        tur = s.get("tur") if s.get("tur") in SINAV_TURLERI else "diger"
        ders = _ders(aday, s.get("ders"), kaynak)
        sonuc.append(Bulgu(ders, tur, _baslik(s.get("baslik"), ders, tur, kaynak), cozum.gun, cozum.hafta,
                           saat, konular, alinti[:300], aday))
    return sonuc


@dataclass
class CikarimSonucu:
    bulgular: list[Bulgu]
    aday: int
    incelenen: int
    incelenmedi: int
    butce_usd: float
    hatalar: list[str] = field(default_factory=list)


class SinavCikarici:
    def __init__(self, kok: Path, okuyucu: Any, tavan: float = AYLIK_TAVAN_USD,
                 saat: Callable[[], float] = time.monotonic, simdi: Callable[[], datetime] = datetime.now):
        self.kok = Path(kok)
        self.okuyucu = okuyucu
        self.saat = saat
        self.defter = OcrDefteri(self.kok / DEFTER, tavan=tavan, simdi=simdi)
        self._onbellek_yolu = self.kok / ONBELLEK
        try:
            veri = json.loads(self._onbellek_yolu.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            veri = {}
        self._onbellek: dict[str, Any] = veri if isinstance(veri, dict) else {}

    def cikar(self, adaylar: list[Aday], bugun: date, bitis: float) -> CikarimSonucu:
        bulgular: list[Bulgu] = []
        incelenen = incelenmedi = 0
        hatalar: list[str] = []
        degisti = False
        for aday in adaylar:
            anahtar = f"{ISTEM_SURUMU}:{aday.anahtar}"
            kayit = self._onbellek.get(anahtar)
            if isinstance(kayit, dict) and isinstance(kayit.get("satirlar"), list):
                satirlar = kayit["satirlar"]
            else:
                kalan = bitis - self.saat()
                if kalan < CAGRI_EN_AZ_SURE or not self.defter.izin_var():
                    incelenmedi += 1
                    continue
                try:
                    okuma = self.okuyucu.oku(aday, bugun, zaman_asimi=min(CAGRI_EN_COK_SURE, kalan))
                except CikarimHatasi as e:
                    incelenmedi += 1
                    hatalar.append(str(e)[:120])
                    continue
                self.defter.yaz(self.okuyucu.model, okuma.girdi, okuma.cikti)
                satirlar = okuma.satirlar
                self._onbellek[anahtar] = {"satirlar": satirlar, "zaman": datetime.now().isoformat(timespec="seconds")}
                degisti = True
            incelenen += 1
            bulgular.extend(uydurma_kapisi(satirlar, aday, bugun))
        if degisti or not self._onbellek_yolu.exists():
            atomic_json_dump(self._onbellek, str(self._onbellek_yolu))
        return CikarimSonucu(bulgular, len(adaylar), incelenen, incelenmedi,
                             round(self.defter.harcanan(), 6), hatalar)
```

- [ ] **Adım 4: Testlerin geçtiğini gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_sinav_cikarimi.py tests/test_sinav_kaynaklari.py tests/test_sinav_tarihi.py tests/test_ocr_katmani.py`
Expected: PASS. (`OcrDefteri.izin_var` bir OCR sayfasının en kötü maliyetini (~0,025 USD) ayırır; sınav çağrısı için muhafazakâr ama tavan 2 USD'de sorun değil — `Ruling` gerekmez, spec "OCR defteri deseni" diyor.)

- [ ] **Adım 5: Commit**

```bash
git add src/sinav_cikarimi.py tests/test_sinav_cikarimi.py
git commit -m "feat(sinav): Haiku çıkarımı, önbellek, aylık bütçe ve uydurma kapısı

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Görev 4: Birleştirme, kimlik, sürüm ve `sinavlar.json` (`src/sinav_tespiti.py`)

**Files:**
- Create: `src/sinav_tespiti.py`
- Test: `tests/test_sinav_tespiti.py`

**Interfaces:**
- Consumes: Görev 3 `Bulgu`, `SinavCikarici`, `ClaudeSinavOkuyucu`, `CikarimSonucu`; Görev 2 `adaylar`, `kaynak_verisi`, `Aday`; Görev 1 `katla`
- Produces:
  - Sabitler: `SURUM = 1`, `SINAVLAR = PurePosixPath("output/sinavlar.json")`, `GECMIS_GUN = 30`, `TARIHSIZ_OMUR_GUN = 21`, `BAGLAMA_GUN = 14`
  - `takvim_turu(baslik: str) -> str`
  - `birlestir(taban: list[dict], bulgular: list[Bulgu], onceki: dict | None, simdi: datetime) -> list[dict]` — kayıt alanları: `id, ders, tur, baslik, tarih (ISO|None), saat (HH:MM|None), hafta (ISO|None), konular, kaynaklar [{tur, konum, alinti}], ilk_tespit (ISO|None), icerik_surumu, degisti (ISO|None), sentetik (bool), taban (dict|None), son_yayin (ISO|None)`
  - `gecerli_belge(veri: Any) -> dict | None`, `oku(kok: Path) -> dict | None`, `yaz(kok: Path, belge: dict) -> None`
  - `tespit_et(kok: Path, veri: dict, taban: list[dict], simdi: datetime, bitis: float, okuyucu=None) -> dict` — belge `{uretildi, surum, sinavlar, ozet: {aday, incelenen, incelenmedi, butce_usd, hatalar}}`

Kararlar (spec'i somutlaştırır; Görev 12'de kullanıcıya bildirilir):
- **İlk kurulum:** önceki dosya yoksa (ilk koşu) her kaydın `ilk_tespit`'i `None` olur — "kurulumda zaten vardı". Böylece kurulum günü her sınav "Yeni" etiketi almaz ve geç-tespit kuralı hatırlatmaları kesmez. Sonraki koşularda yeni kayıt `ilk_tespit = simdi` alır.
- **Hafta:** "Next week", "bu hafta" gibi gün vermeyen ifade `tarih: null` + `hafta: <pazartesi>` olur (spec veri modeline eklenen alan). Hafta-yalnız kayıt, aynı dersin o hafta içindeki tek tarihli kaydına bağlanır.
- **Ortak sınav:** ders "Genel" olan bulgu, aynı gündeki takvim kaydına bağlanır.
- **Tarihsiz ve haftasız** kayıt, son kaynağının yayınından 21 gün sonra düşer.

- [ ] **Adım 1: Başarısız testi yaz** — `tests/test_sinav_tespiti.py`

```python
"""src/sinav_tespiti: merging takvim + grade-table exams with text findings into
output/sinavlar.json — ids, content versions, first-seen and retention."""
import hashlib
import json
from datetime import date, datetime

import pytest

from src.sinav_cikarimi import Bulgu
from src.sinav_kaynaklari import Aday
from src.sinav_tespiti import SURUM, birlestir, gecerli_belge, oku, takvim_turu, yaz

SIMDI = datetime(2026, 10, 16, 10, 0)


def taban(id_, course, title, date_, all_day=False):
    return {"id": id_, "course": course, "title": title, "rawTitle": title, "courseColor": "#000",
            "courseFamily": "blue", "examNumber": None, "date": date_, "endDate": None, "allDay": all_day,
            "status": "upcoming", "grade": None, "relatedHomework": [], "relatedContent": []}


def bulgu(ders="Matematik", tur="konu_tarama", tarih=None, hafta=None, konular=(), baslik=None,
          yayin=date(2026, 10, 5), konum=None, metin="metin", aday_tur="ders_karti"):
    aday = Aday(metin, ders, yayin, aday_tur, [konum or {"bolum": "ders_icerikleri_haftalar", "hafta": "4. Hafta",
                                                         "ders": ders, "sira": 1}])
    return Bulgu(ders, tur, baslik or f"{ders} KTT", tarih, hafta, None, list(konular), "alıntı", aday)


GIS = taban("gis1", "Özdebir GİS", "Özdebir GİS · İzleme Sınavı", "2026-10-23T09:00:00")
TR = taban("tr1", "Türkçe", "Türkçe · Ortak Yazılı", "2027-01-05T10:30:00")
NOTLU = dict(taban("not1", "Matematik", "Matematik · 1. Sınav", None), status="past", grade="85")


@pytest.mark.parametrize("baslik,tur", [
    ("Özdebir GİS · İzleme Sınavı", "deneme"), ("Türkçe · Ortak Yazılı", "ortak_sinav"),
    ("Matematik KTT", "konu_tarama"), ("Fen · Yazılı", "yazili"), ("Irregular Verbs Quiz", "kisa_sinav"),
    ("Sebit Vcloud Kazanım Değerlendirme Uygulaması-1_TM", "deneme"), ("Okul gezisi", "diger"),
])
def test_takvim_turu(baslik, tur):
    assert takvim_turu(baslik) == tur


def test_takvim_kaydi_kimligini_ve_tabanini_korur():
    [k] = birlestir([GIS], [], None, SIMDI)
    assert (k["id"], k["ders"], k["tur"], k["tarih"], k["saat"], k["sentetik"]) == \
        ("gis1", "Özdebir GİS", "deneme", "2026-10-23", "09:00", False)
    assert k["kaynaklar"] == [{"tur": "takvim", "konum": {"id": "gis1"}, "alinti": GIS["rawTitle"]}]
    assert k["taban"] == GIS and k["ilk_tespit"] is None and k["degisti"] is None


def test_notlu_sentetik_kayit():
    [k] = birlestir([NOTLU], [], None, SIMDI)
    assert (k["sentetik"], k["tarih"], k["kaynaklar"][0]["tur"]) == (True, None, "not_tablosu")


def test_bulgu_ayni_ders_ayni_gun_takvime_baglanir():
    tr_bulgu = bulgu("Türkçe", "ortak_sinav", tarih=date(2027, 1, 5), konular=["Fiilimsiler"])
    [k, _] = sorted(birlestir([TR, GIS], [tr_bulgu], None, SIMDI), key=lambda k: k["id"] != "tr1")
    assert k["id"] == "tr1" and k["konular"] == ["Fiilimsiler"]
    assert [x["tur"] for x in k["kaynaklar"]] == ["takvim", "ders_karti"]


def test_genel_bulgu_ayni_gundeki_takvime_baglanir():
    kayitlar = birlestir([GIS], [bulgu("Genel", "deneme", tarih=date(2026, 10, 23), konular=["Tüm konular"])],
                         None, SIMDI)
    assert len(kayitlar) == 1 and kayitlar[0]["konular"] == ["Tüm konular"]


def test_ayni_ders_ayni_gun_iki_bulgu_tek_kayit():
    b1 = bulgu(tarih=date(2026, 10, 15), konular=["Mutlak değer"])
    b2 = bulgu(tarih=date(2026, 10, 15), konular=["Mutlak değer", "Tam sayılar"],
               konum={"bolum": "odev", "baslik": "KTT", "teslim": None}, aday_tur="odev")
    [k] = birlestir([], [b1, b2], None, SIMDI)
    assert k["id"] == hashlib.md5("Matematik|konu_tarama|2026-10-15".encode()).hexdigest()[:12]
    assert k["konular"] == ["Mutlak değer", "Tam sayılar"]
    assert [x["tur"] for x in k["kaynaklar"]] == ["ders_karti", "odev"]
    assert (k["tarih"], k["saat"], k["baslik"]) == ("2026-10-15", None, "Matematik KTT")


def test_hafta_yalniz_bulgu_haftadaki_tek_sinava_baglanir():
    fen = taban("fen1", "Fen Bilimleri", "Fen · Yazılı", "2026-10-21T09:00:00")
    [k] = birlestir([fen], [bulgu("Fen Bilimleri", "kisa_sinav", hafta=date(2026, 10, 19), konular=["Uzay"])],
                    None, SIMDI)
    assert k["id"] == "fen1" and k["konular"] == ["Uzay"]


def test_hafta_yalniz_bulgu_eslesme_yoksa_ayri_kayit():
    [k] = birlestir([], [bulgu("İngilizce", "kisa_sinav", hafta=date(2026, 10, 19))], None, SIMDI)
    assert (k["tarih"], k["hafta"]) == (None, "2026-10-19")
    assert k["id"] == hashlib.md5("İngilizce|kisa_sinav|hafta:2026-10-19".encode()).hexdigest()[:12]


def test_tarihsiz_bulgu_konu_ortusmesiyle_baglanir():
    tarihli = bulgu(tarih=date(2026, 10, 20), konular=["Mutlak değer"])
    tarihsiz = bulgu(konular=["mutlak değer", "Oran"], yayin=date(2026, 10, 12), metin="başka")
    [k] = birlestir([], [tarihli, tarihsiz], None, SIMDI)
    assert k["konular"] == ["Mutlak değer", "Oran"]


def test_tarihsiz_bulgu_ortusme_yoksa_tarih_belirsiz_kayit():
    kayitlar = birlestir([], [bulgu(tarih=date(2026, 10, 20), konular=["Mutlak değer"]),
                              bulgu(konular=["Oran"], yayin=date(2026, 10, 12), metin="başka")], None, SIMDI)
    assert [k["tarih"] for k in kayitlar] == ["2026-10-20", None]


def test_icerik_surumu_degisince_degisti_ilk_tespit_korunur():
    onceki = {"surum": SURUM, "sinavlar": birlestir([], [bulgu(tarih=date(2026, 10, 20), konular=["A"])],
                                                    {"surum": SURUM, "sinavlar": []}, datetime(2026, 10, 10, 9))}
    assert onceki["sinavlar"][0]["ilk_tespit"] == "2026-10-10T09:00:00"
    ayni = birlestir([], [bulgu(tarih=date(2026, 10, 20), konular=["A"])], onceki, SIMDI)[0]
    assert (ayni["ilk_tespit"], ayni["degisti"]) == ("2026-10-10T09:00:00", None)
    yeni = birlestir([], [bulgu(tarih=date(2026, 10, 20), konular=["A", "B"])], onceki, SIMDI)[0]
    assert (yeni["ilk_tespit"], yeni["degisti"]) == ("2026-10-10T09:00:00", "2026-10-16T10:00:00")
    assert yeni["icerik_surumu"] != ayni["icerik_surumu"] and len(yeni["icerik_surumu"]) == 12


def test_ilk_kurulumda_ilk_tespit_bos_sonra_simdi():
    assert birlestir([GIS], [], None, SIMDI)[0]["ilk_tespit"] is None
    assert birlestir([GIS], [], {"surum": SURUM, "sinavlar": []}, SIMDI)[0]["ilk_tespit"] == "2026-10-16T10:00:00"


def test_saklama_suresi():
    eski = taban("eski", "Fen", "Fen · Yazılı", "2026-09-15T09:00:00")
    yakin = taban("yakin", "Fen", "Fen · Yazılı", "2026-09-17T09:00:00")
    tarihsiz_eski = bulgu("Fen", "diger", konular=["X"], yayin=date(2026, 9, 24), metin="eski")
    tarihsiz_taze = bulgu("Fen", "diger", konular=["Y"], yayin=date(2026, 9, 26), metin="taze")
    idler = [k["id"] for k in birlestir([eski, yakin, NOTLU], [tarihsiz_eski, tarihsiz_taze], None, SIMDI)]
    assert "eski" not in idler and "yakin" in idler and "not1" in idler
    assert len(idler) == 3   # yakin, taze, not1 — eski takvim (31 gün) ve eski tarihsiz (22 gün) düştü


def test_siralama_tarihli_tarihsiz_sentetik():
    kayitlar = birlestir([NOTLU, TR, GIS], [bulgu("Fen", "diger", konular=["Y"])], None, SIMDI)
    assert [k["id"] for k in kayitlar][:2] == ["gis1", "tr1"]
    assert kayitlar[2]["tarih"] is None and not kayitlar[2]["sentetik"]
    assert kayitlar[3]["id"] == "not1"


def test_yaz_oku_ve_gecersiz_belge(tmp_path):
    belge = {"uretildi": "2026-10-16T10:00:00", "surum": SURUM, "sinavlar": [], "ozet": {}}
    yaz(tmp_path, belge)
    assert oku(tmp_path) == belge
    assert gecerli_belge({"surum": SURUM + 1, "sinavlar": []}) is None
    assert gecerli_belge({"surum": SURUM, "sinavlar": "x"}) is None
    (tmp_path / "output/sinavlar.json").write_text("{bozuk", encoding="utf-8")
    assert oku(tmp_path) is None
```

- [ ] **Adım 2: Testin başarısız olduğunu gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_sinav_tespiti.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.sinav_tespiti'`

- [ ] **Adım 3: Uygula** — `src/sinav_tespiti.py` (CLI ve `tespit_et` Görev 5'te bu dosyaya eklenir)

```python
"""Sınav tespiti (spec §4, §5 "Birleştirme"): takvim + not tablosu tabanı ile
serbest metin bulgularını tek listede birleştirir ve output/sinavlar.json'u
yazar. Kayıt kimliği: takvimde varsa takvimin kendi kimliği (modüller bağlı,
değişmez), yoksa ders+tür+tarih özeti."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any

from src.json_utils import atomic_json_dump
from src.sinav_cikarimi import Bulgu
from src.sinav_tarihi import katla

SURUM = 1
SINAVLAR = PurePosixPath("output/sinavlar.json")
GECMIS_GUN = 30
TARIHSIZ_OMUR_GUN = 21
BAGLAMA_GUN = 14
KONU_SINIRI = 15
KAYNAK_SINIRI = 6


def takvim_turu(baslik: str) -> str:
    k = katla(baslik)
    if "ortak" in k:
        return "ortak_sinav"
    if "ktt" in k or "konu tarama" in k:
        return "konu_tarama"
    if any(s in k for s in ("deneme", "gis", "izleme", "hazirbulunusluk", "kazanim degerlendirme")):
        return "deneme"
    if "yazili" in k:
        return "yazili"
    if "quiz" in k or "kisa sinav" in k:
        return "kisa_sinav"
    return "diger"


def _md5(metin: str) -> str:
    return hashlib.md5(metin.encode("utf-8")).hexdigest()[:12]


def _tabandan(e: dict) -> dict:
    tarih_saat = str(e.get("date") or "")
    sentetik = not tarih_saat
    saat = tarih_saat[11:16] if len(tarih_saat) >= 16 and not e.get("allDay") else None
    kaynak = ({"tur": "not_tablosu", "konum": {"id": e.get("id")}, "alinti": str(e.get("rawTitle") or "")[:300]}
              if sentetik else
              {"tur": "takvim", "konum": {"id": e.get("id")}, "alinti": str(e.get("rawTitle") or "")[:300]})
    return {"id": e.get("id"), "ders": e.get("course") or "Genel", "tur": takvim_turu(e.get("title") or ""),
            "baslik": e.get("title") or e.get("rawTitle") or "Sınav", "tarih": tarih_saat[:10] or None,
            "saat": saat, "hafta": None, "konular": [], "kaynaklar": [kaynak], "sentetik": sentetik,
            "taban": e, "son_yayin": None}


def _bulgudan(b: Bulgu, kimlik: str) -> dict:
    return {"id": kimlik, "ders": b.ders, "tur": b.tur, "baslik": b.baslik,
            "tarih": b.tarih.isoformat() if b.tarih else None, "saat": b.saat,
            "hafta": b.hafta.isoformat() if b.hafta and not b.tarih else None,
            "konular": [], "kaynaklar": [], "sentetik": False, "taban": None, "son_yayin": None}


def _ekle(kayit: dict, b: Bulgu) -> None:
    for k in b.konular:
        if katla(k) not in {katla(x) for x in kayit["konular"]}:
            kayit["konular"].append(k)
    for konum in b.aday.konumlar:
        kaynak = {"tur": b.aday.tur, "konum": konum, "alinti": b.alinti[:300]}
        if kaynak not in kayit["kaynaklar"]:
            kayit["kaynaklar"].append(kaynak)
    if b.saat and not kayit["saat"]:
        kayit["saat"] = b.saat
    if b.aday.yayin and (kayit["son_yayin"] is None or b.aday.yayin.isoformat() > kayit["son_yayin"]):
        kayit["son_yayin"] = b.aday.yayin.isoformat()


def _konu_ortusur(a: list[str], b: list[str]) -> bool:
    ka, kb = [katla(x) for x in a], [katla(x) for x in b]
    return any(x and y and (x in y or y in x) for x in ka for y in kb)


def _tek(adaylar: list[dict]) -> dict | None:
    return adaylar[0] if len(adaylar) == 1 else None


def _surum(k: dict) -> str:
    govde = f"{k['tarih']}|{k['saat']}|{k['hafta']}|" + "|".join(k["konular"])
    return hashlib.sha256(govde.encode("utf-8")).hexdigest()[:12]


def birlestir(taban: list[dict], bulgular: list[Bulgu], onceki: dict | None, simdi: datetime) -> list[dict]:
    kayitlar = [_tabandan(e) for e in taban if isinstance(e, dict) and e.get("id")]
    tarihliler = [b for b in bulgular if b.tarih]
    tarihsizler = [b for b in bulgular if not b.tarih]

    for b in tarihliler:
        gun = b.tarih.isoformat()
        eslesen = next((k for k in kayitlar if not k["sentetik"] and k["tarih"] == gun
                        and (katla(k["ders"]) == katla(b.ders) or (b.ders == "Genel" and k["taban"]))), None)
        if eslesen is None:
            eslesen = _bulgudan(b, _md5(f"{b.ders}|{b.tur}|{gun}"))
            kayitlar.append(eslesen)
        _ekle(eslesen, b)

    for b in tarihsizler:
        ayni_ders = [k for k in kayitlar if k["tarih"] and not k["sentetik"] and katla(k["ders"]) == katla(b.ders)]
        hedef = None
        if b.hafta:
            son = b.hafta + timedelta(days=6)
            hedef = _tek([k for k in ayni_ders if b.hafta.isoformat() <= k["tarih"] <= son.isoformat()])
        elif b.konular and b.aday.yayin:
            son = b.aday.yayin + timedelta(days=BAGLAMA_GUN)
            hedef = _tek([k for k in ayni_ders if b.aday.yayin.isoformat() <= k["tarih"] <= son.isoformat()
                          and _konu_ortusur(k["konular"], b.konular)])
        if hedef is None:
            ek = f"hafta:{b.hafta.isoformat()}" if b.hafta else b.aday.anahtar[:12]
            kimlik = _md5(f"{b.ders}|{b.tur}|{ek}")
            hedef = next((k for k in kayitlar if k["id"] == kimlik), None)
            if hedef is None:
                hedef = _bulgudan(b, kimlik)
                kayitlar.append(hedef)
        _ekle(hedef, b)

    bugun = simdi.date()
    kalan = []
    for k in kayitlar:
        if k["sentetik"]:
            kalan.append(k)
        elif k["tarih"]:
            if date.fromisoformat(k["tarih"]) >= bugun - timedelta(days=GECMIS_GUN):
                kalan.append(k)
        elif k["hafta"]:
            if date.fromisoformat(k["hafta"]) + timedelta(days=6) >= bugun - timedelta(days=GECMIS_GUN):
                kalan.append(k)
        elif k["son_yayin"] and date.fromisoformat(k["son_yayin"]) >= bugun - timedelta(days=TARIHSIZ_OMUR_GUN):
            kalan.append(k)

    eski = {k.get("id"): k for k in ((onceki or {}).get("sinavlar") or []) if isinstance(k, dict)}
    an = simdi.isoformat(timespec="seconds")
    for k in kalan:
        k["konular"] = k["konular"][:KONU_SINIRI]
        k["kaynaklar"] = k["kaynaklar"][:KAYNAK_SINIRI]
        k["icerik_surumu"] = _surum(k)
        o = eski.get(k["id"])
        if o is not None:
            k["ilk_tespit"] = o.get("ilk_tespit")
            k["degisti"] = an if o.get("icerik_surumu") != k["icerik_surumu"] else o.get("degisti")
        else:
            k["ilk_tespit"] = None if onceki is None else an
            k["degisti"] = None

    def sira(k: dict) -> tuple:
        if k["sentetik"]:
            return (2, "")
        if k["tarih"]:
            return (0, f"{k['tarih']}T{k['saat'] or '00:00'}")
        return (1, k["hafta"] or "9999")
    return sorted(kalan, key=sira)


def gecerli_belge(veri: Any) -> dict | None:
    if not isinstance(veri, dict) or veri.get("surum") != SURUM or not isinstance(veri.get("sinavlar"), list):
        return None
    return veri


def oku(kok: Path) -> dict | None:
    try:
        return gecerli_belge(json.loads((Path(kok) / SINAVLAR).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None


def yaz(kok: Path, belge: dict) -> None:
    atomic_json_dump(belge, str(Path(kok) / SINAVLAR))
```

- [ ] **Adım 4: Testlerin geçtiğini gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_sinav_tespiti.py`
Expected: PASS. `test_saklama_suresi`'nde `idler` tam olarak `["yakin", <taze kimliği>, "not1"]` olmalı (eski takvim kaydı 31 gün önce, eski tarihsiz yayın 22 gün önce düşer).

- [ ] **Adım 5: Commit**

```bash
git add src/sinav_tespiti.py tests/test_sinav_tespiti.py
git commit -m "feat(sinav): takvim, not tablosu ve metin bulgularını tek listede birleştir

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Görev 5: `run_sync` adımı, `--kuru` CLI, takvim etiketi, sağlık özeti

**Files:**
- Modify: `src/sinav_tespiti.py` (sona `tespit_et`, `kuru_rapor`, `main`)
- Modify: `src/dashboard_api.py:2294` (`_is_exam_event`) ve `_sinav_listesi` içindeki çağrı
- Modify: `src/run_sync.py` (`_ekleri_esitle_adimi`'nden sonra yeni adım; `health` sözlüğü)
- Modify: `tests/conftest.py`
- Test: `tests/test_sinav_adimi.py`, `tests/test_exams.py` (ekleme)

**Interfaces:**
- Consumes: Görev 2 `adaylar`, `kaynak_verisi`; Görev 3 `SinavCikarici`, `ClaudeSinavOkuyucu`, `AYLIK_TAVAN_USD`; Görev 4 `birlestir`, `oku`, `yaz`, `SURUM`; `dashboard_api._sinav_listesi(data, now=None)`
- Produces:
  - `sinav_tespiti.tespit_et(kok, veri, taban, simdi, bitis, okuyucu=None) -> dict`
  - `sinav_tespiti.kuru_rapor(belge: dict) -> str`
  - `sinav_tespiti.main(argv: list[str] | None = None) -> int` — `python -m src.sinav_tespiti [--kuru] [--sure N]`
  - `run_sync._sinav_tespiti_adimi(start_time, simdi=None) -> dict` ve `run_sync._sinav_uyari_durumu() -> dict`; `health["sinav_tespiti"]`, `health["sinav_uyari"]`
  - `dashboard_api._is_exam_event(title, takvim_turu=None) -> bool`
  - Uyarı durum dosyası adı (Görev 8 yazar): `output/sinav_uyari_durumu.json`

- [ ] **Adım 1: Başarısız testleri yaz** — `tests/test_sinav_adimi.py`

```python
"""run_sync's exam-detection step, the --kuru CLI and the health summary.
Nothing here reaches the model: the step's entry point is patched."""
import json
import time
from datetime import datetime

import src.run_sync as run_sync
import src.sinav_tespiti as st
# Taken at collection, before conftest's autouse fixture replaces st.tespit_et
# with a refusal: the end-to-end test below wants the real one.
from src.sinav_tespiti import tespit_et as GERCEK_TESPIT

BELGE = {"uretildi": "2026-10-16T10:00:00", "surum": st.SURUM,
         "sinavlar": [{"id": "a1", "ders": "Matematik", "tur": "konu_tarama", "baslik": "Matematik KTT",
                       "tarih": "2026-10-20", "saat": None, "hafta": None, "konular": ["Mutlak değer"],
                       "kaynaklar": [{"tur": "ders_karti", "konum": {"hafta": "4. Hafta"}, "alinti": "KTT"}],
                       "ilk_tespit": None, "icerik_surumu": "abc", "degisti": None, "sentetik": False,
                       "taban": None, "son_yayin": "2026-10-05"}],
         "ozet": {"aday": 3, "incelenen": 2, "incelenmedi": 1, "butce_usd": 0.01, "hatalar": []}}


def _kok(tmp_path, monkeypatch):
    (tmp_path / "output").mkdir()
    (tmp_path / "output/scraped_data.json").write_text(json.dumps({"takvim": []}), encoding="utf-8")
    monkeypatch.setattr(run_sync, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(run_sync, "OUTPUT_DIR", str(tmp_path / "output"))
    return tmp_path


def test_adim_dosyayi_yazar_ozet_doner(tmp_path, monkeypatch):
    kok = _kok(tmp_path, monkeypatch)
    cagri = {}

    def sahte(kok_, veri, taban, simdi, bitis, okuyucu=None):
        cagri.update(kok=kok_, veri=veri, taban=taban, kalan=bitis - time.monotonic())
        return BELGE
    monkeypatch.setattr(st, "tespit_et", sahte)
    ozet = run_sync._sinav_tespiti_adimi(start_time=time.time())
    assert ozet == {**BELGE["ozet"], "sinav": 1, "sure": 45}
    assert json.loads((kok / "output/sinavlar.json").read_text(encoding="utf-8")) == BELGE
    assert cagri["veri"] == {"takvim": []} and cagri["taban"] == [] and 40 < cagri["kalan"] <= 45


def test_adim_sure_kalmadiysa_yine_yazar_model_suresi_sifir(tmp_path, monkeypatch):
    _kok(tmp_path, monkeypatch)
    kalanlar = []
    monkeypatch.setattr(st, "tespit_et", lambda k, v, t, s, bitis, okuyucu=None:
                        kalanlar.append(bitis - time.monotonic()) or BELGE)
    ozet = run_sync._sinav_tespiti_adimi(start_time=time.time() - 590)
    assert ozet["sure"] == 0 and kalanlar[0] <= 0


def test_adim_hatasi_senkronu_bozmaz(tmp_path, monkeypatch):
    _kok(tmp_path, monkeypatch)

    def patla(*a, **k):
        raise RuntimeError("bir şey oldu")
    monkeypatch.setattr(st, "tespit_et", patla)
    assert run_sync._sinav_tespiti_adimi(start_time=time.time()) == {"hata": "bir şey oldu"}
    assert not (tmp_path / "output/sinavlar.json").exists()


def test_uyari_durumu_okunur(tmp_path, monkeypatch):
    kok = _kok(tmp_path, monkeypatch)
    assert run_sync._sinav_uyari_durumu() == {}
    (kok / "output/sinav_uyari_durumu.json").write_text('{"son_tur": "x", "gonderilen": 2}', encoding="utf-8")
    assert run_sync._sinav_uyari_durumu() == {"son_tur": "x", "gonderilen": 2}


def test_kuru_rapor_okunur_metin():
    metin = st.kuru_rapor(BELGE)
    assert "Matematik · konu_tarama · 2026-10-20" in metin
    assert "Konular: Mutlak değer" in metin and "ders_karti" in metin
    assert "aday 3 · incelenen 2 · incelenmedi 1 · bütçe 0.01 USD" in metin


def test_cli_kuru_dosya_yazmaz(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(st, "PROJE_KOKU", tmp_path)
    (tmp_path / "output").mkdir()
    (tmp_path / "output/scraped_data.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(st, "_taban", lambda veri: [])
    monkeypatch.setattr(st, "tespit_et", lambda *a, **k: BELGE)
    assert st.main(["--kuru"]) == 0
    assert "Matematik KTT" in capsys.readouterr().out
    assert not (tmp_path / "output/sinavlar.json").exists()
    assert st.main([]) == 0
    assert (tmp_path / "output/sinavlar.json").exists()


def test_tespit_et_uctan_uca_sahte_okuyucuyla(tmp_path):
    from datetime import date
    from src.sinav_cikarimi import OkumaSonucu
    from tests.sinav_fikstur import haftalar_verisi

    class Okuyucu:
        model = "claude-haiku-4-5"

        def oku(self, aday, bugun, zaman_asimi):
            if "KTT" not in aday.metin:
                return OkumaSonucu([], 10, 1)
            return OkumaSonucu([{"ders": "Matematik", "tur": "konu_tarama", "baslik": "Matematik KTT",
                                 "tarih_ifadesi": "15 EKİM PERŞEMBE", "tarih": "", "saat": "",
                                 "konular": ["MUTLAK DEĞER"], "alinti": "15 EKİM PERŞEMBE günü yapılacak olan Matematik KTT"}],
                               100, 10)
    belge = GERCEK_TESPIT(tmp_path, haftalar_verisi(), [], datetime(2026, 10, 16, 10), time.monotonic() + 60,
                          okuyucu=Okuyucu())
    [k] = belge["sinavlar"]
    assert (k["ders"], k["tarih"], k["konular"]) == ("Matematik", "2026-10-15", ["MUTLAK DEĞER"])
    assert len(k["kaynaklar"]) == 2   # 4. ve 5. hafta
    assert belge["ozet"]["aday"] == 3 and belge["ozet"]["incelenmedi"] == 0
```

`tests/test_exams.py`'ye, `test_sinav_keyword` testinin bulunduğu (`_is_exam_event`'i sınayan) sınıfın sonuna ekle:

```python
    def test_takvim_sinav_etiketi_baslik_sozcugu_olmadan(self):
        assert dashboard_api._is_exam_event(
            "5-6-7-8. Sınıflar Sebit Vcloud Kazanım Değerlendirme Uygulaması-1_TM", "sinav")

    def test_takvim_sinav_etiketi_baslangic_bitis_disarida(self):
        assert not dashboard_api._is_exam_event(
            "MEB 1. Dönem 2. Yazılı Sınav Haftası Başlangıcı", "sinav")

    def test_baska_etiket_eski_kural(self):
        assert not dashboard_api._is_exam_event("Grade 7 English", "kisisel")
```

ve dosyanın sonuna:

```python
def test_sinav_listesi_takvim_etiketli_kaydi_alir():
    from tests.sinav_fikstur import TAKVIM_SINAV
    sonuc = dashboard_api._sinav_listesi({"takvim": TAKVIM_SINAV}, now=datetime(2026, 10, 16, 10))
    basliklar = [e["rawTitle"] for e in sonuc["exams"]]
    assert any("Sebit Vcloud" in b for b in basliklar)
    assert any("GİS-1" in b for b in basliklar)
    assert not any("Başlangıcı" in b for b in basliklar)
    assert not any("Grade 7 English" in b for b in basliklar)
```

- [ ] **Adım 2: Testlerin başarısız olduğunu gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_sinav_adimi.py tests/test_exams.py`
Expected: FAIL — `tests/test_sinav_adimi.py` toplanırken `ImportError: cannot import name 'tespit_et'`; `test_exams.py`'deki yeni testler `_is_exam_event() takes 1 positional argument but 2 were given`.

- [ ] **Adım 3: `_is_exam_event`'i genişlet** — `src/dashboard_api.py:2294`

```python
def _is_exam_event(title, takvim_turu=None):
    """A takvim event is an exam when the portal tags it "sinav" (its own
    calendar field — "Sebit Vcloud Kazanım Değerlendirme Uygulaması" carries
    no exam word) or its title says so; week start/end markers never are."""
    lower = _turkish_lower(title)
    if any(ex in lower for ex in _SINAV_EXCLUDE):
        return False
    if takvim_turu == "sinav":
        return True
    if any(kw in lower for kw in _SINAV_KEYWORDS):
        return True
    return bool(_SINAV_WORD_RE.search(title))
```

`_sinav_listesi` içindeki döngüde:

```python
        title = evt.get("title", "")
        props = evt.get("extendedProps") if isinstance(evt.get("extendedProps"), dict) else {}
        if not _is_exam_event(title, props.get("calendar")):
            continue
```

- [ ] **Adım 4: `tespit_et`, `kuru_rapor`, `main`'i ekle** — `src/sinav_tespiti.py` sonuna

```python
PROJE_KOKU = Path(__file__).resolve().parents[1]


def tespit_et(kok: Path, veri: dict, taban: list[dict], simdi: datetime, bitis: float,
              okuyucu: Any = None) -> dict:
    from src.sinav_cikarimi import ClaudeSinavOkuyucu, SinavCikarici
    from src.sinav_kaynaklari import adaylar, kaynak_verisi

    kok = Path(kok)
    ekler, ilk_gorulme = kaynak_verisi(kok)
    liste = adaylar(veri, simdi.date(), ek_metinleri=ekler, odev_ilk_gorulme=ilk_gorulme)
    sonuc = SinavCikarici(kok, okuyucu or ClaudeSinavOkuyucu()).cikar(liste, simdi.date(), bitis)
    kayitlar = birlestir(taban, sonuc.bulgular, oku(kok), simdi)
    return {"uretildi": simdi.isoformat(timespec="seconds"), "surum": SURUM, "sinavlar": kayitlar,
            "ozet": {"aday": sonuc.aday, "incelenen": sonuc.incelenen, "incelenmedi": sonuc.incelenmedi,
                     "butce_usd": sonuc.butce_usd, "hatalar": sonuc.hatalar[:5]}}


def kuru_rapor(belge: dict) -> str:
    satirlar = []
    for k in belge.get("sinavlar") or []:
        zaman = k.get("tarih") or (f"{k['hafta']} haftası" if k.get("hafta") else "tarih belirsiz")
        if k.get("saat"):
            zaman += f" {k['saat']}"
        satirlar.append(f"- {k.get('ders')} · {k.get('tur')} · {zaman} · {k.get('baslik')}"
                        + (" (not tablosu)" if k.get("sentetik") else ""))
        if k.get("konular"):
            satirlar.append("  Konular: " + "; ".join(k["konular"]))
        for x in k.get("kaynaklar") or []:
            satirlar.append(f"  Kaynak: {x.get('tur')} {json.dumps(x.get('konum'), ensure_ascii=False)}"
                            f" — {str(x.get('alinti') or '')[:120]}")
    o = belge.get("ozet") or {}
    satirlar.append(f"Özet: {len(belge.get('sinavlar') or [])} sınav · aday {o.get('aday', 0)} · incelenen "
                    f"{o.get('incelenen', 0)} · incelenmedi {o.get('incelenmedi', 0)} · bütçe "
                    f"{o.get('butce_usd', 0)} USD")
    return "\n".join(satirlar)


def _taban(veri: dict) -> list[dict]:
    from src.dashboard_api import _sinav_listesi  # Flask app: imported only where it is needed
    return _sinav_listesi(veri)["exams"]


def main(argv: list[str] | None = None) -> int:
    import argparse
    import time

    from src.env_loader import load_env
    load_env()
    p = argparse.ArgumentParser(description="Sınav tespiti: sinavlar.json üretir")
    p.add_argument("--kuru", action="store_true", help="dosyaya yazmadan bulunanları yazdır")
    p.add_argument("--sure", type=float, default=300.0, help="model çağrıları için saniye")
    a = p.parse_args(argv)
    veri = json.loads((PROJE_KOKU / "output/scraped_data.json").read_text(encoding="utf-8"))
    belge = tespit_et(PROJE_KOKU, veri, _taban(veri), datetime.now(), time.monotonic() + a.sure)
    print(kuru_rapor(belge))
    if not a.kuru:
        yaz(PROJE_KOKU, belge)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Adım 5: `run_sync` adımı ve sağlık** — `src/run_sync.py`, `_kisa_hata`'dan sonra:

```python
SINAV_SURE = int(os.environ.get("TEDY_SINAV_SURE", "45"))
# Health and the reindex still have to fit after the step.
SINAV_YEDEK_SURE = 120


def _sinav_tespiti_adimi(start_time, simdi=None):
    """Build output/sinavlar.json (spec 2026-10-16 §4). Never raises. With no
    time left the step still runs — takvim, grade table and cached findings cost
    nothing — and only the model calls wait for the next run."""
    simdi = time.time() if simdi is None else simdi
    sure = max(0, int(min(SINAV_SURE, start_time + SYNC_SURE_SINIRI - SINAV_YEDEK_SURE - simdi)))
    try:
        from src import sinav_tespiti
        with open(os.path.join(OUTPUT_DIR, "scraped_data.json"), encoding="utf-8") as f:
            veri = json.load(f)
        taban = sinav_tespiti._taban(veri)
        belge = sinav_tespiti.tespit_et(Path(PROJECT_ROOT), veri, taban, datetime.now(), time.monotonic() + sure)
        sinav_tespiti.yaz(Path(PROJECT_ROOT), belge)
        ozet = {**belge["ozet"], "sinav": len(belge["sinavlar"]), "sure": sure}
        print(f"[SINAV] sinav={ozet['sinav']} aday={ozet['aday']} incelenen={ozet['incelenen']}"
              f" incelenmedi={ozet['incelenmedi']} butce={ozet['butce_usd']} (süre {sure} s)")
        return ozet
    except Exception as e:
        print(f"[WARN] Sınav tespiti: {_kisa_hata(e)}")
        return {"hata": _kisa_hata(e)}


def _sinav_uyari_durumu():
    """The alert timer's last round (src/sinav_uyari.py writes it), for health.json."""
    try:
        with open(os.path.join(OUTPUT_DIR, "sinav_uyari_durumu.json"), encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError):
        return {}
    return veri if isinstance(veri, dict) else {}
```

`test_adim_dosyayi_yazar_ozet_doner` `_taban`'ı da çağırır; testte `scraped_data.json` boş takvimli olduğu için `_sinav_listesi` gerçek çalışır ve `[]` döner (dashboard_api import'u `.env` symlink'iyle `DASHBOARD_SECRET_KEY` bulur). `from pathlib import Path` `run_sync.py`'de yoksa ekle.

`main()` içinde, `ekler_ozeti = _ekleri_esitle_adimi(...)` satırından hemen sonra:

```python
    # 5c. Exam detection — after attachments (their text is a source), before
    # health (which reports it) and the reindex.
    sinav_ozeti = _sinav_tespiti_adimi(start_time)
```

`health = {...}` sözlüğüne `"ekler": ekler_ozeti,` satırından sonra:

```python
        "sinav_tespiti": sinav_ozeti,
        "sinav_uyari": _sinav_uyari_durumu(),
```

- [ ] **Adım 6: Testte gerçek tespit yok** — `tests/conftest.py` sonuna

```python
@pytest.fixture(autouse=True)
def _canli_sinav_tespiti_yok(monkeypatch):
    """run_sync.main() runs exam detection since 2026-10-16 (plan sinav-uyari,
    Görev 5). A test that drives main() must not reach Claude nor write the live
    output/sinavlar.json; the step turns this refusal into {"hata": …}. Tests of
    the step patch tespit_et again on purpose."""
    import src.sinav_tespiti as tespit

    def _yasak(*a, **k):
        raise RuntimeError("testte gerçek sınav tespiti yok")
    monkeypatch.setattr(tespit, "tespit_et", _yasak)
```

(`test_tespit_et_uctan_uca_sahte_okuyucuyla` gerçek işlevi toplama anında aldığı `GERCEK_TESPIT` ile çağırır; bu fikstür ona dokunmaz.)

- [ ] **Adım 7: Testlerin geçtiğini gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_sinav_adimi.py tests/test_exams.py tests/test_sinav_tespiti.py tests/test_run_sync*.py`
Expected: PASS. `tests/test_run_sync*.py` yoksa `grep -l "run_sync" tests/*.py` ile bulunan dosyaları çalıştır; `main()`'i süren testler `sinav_tespiti: {"hata": "testte gerçek sınav tespiti yok"}` ile geçmeli.

- [ ] **Adım 8: Commit**

```bash
git add src/sinav_tespiti.py src/run_sync.py src/dashboard_api.py tests/conftest.py tests/test_sinav_adimi.py tests/test_exams.py
git commit -m "feat(sinav): senkronda sınav tespiti adımı, --kuru CLI ve takvimin sınav etiketi

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Görev 6: `/api/exams` `sinavlar.json`'dan; asistan gerçek konuları okur

**Files:**
- Modify: `src/dashboard_api.py` (`_sinav_listesi` → `aiSummary`/`studyGuide` ve `exam_content_map`/`enrichment_cache` okuması kalkar; yeni `_sinav_api_listesi`; `/api/exams` rotası; `_canli_sinavlar`)
- Modify: `src/assistant_tools.py:813` (`sinavlar_metni`)
- Modify: `dashboard/src/types.ts:312` (`ExamItem`, `ExamsApiResponse`)
- Modify: `tests/conftest.py` (`_canli_sinavlar_dosyasi_yok`)
- Test: `tests/test_sinav_api.py`; mevcut `tests/test_exams.py`, `tests/test_assistant_alistirma_araclari.py` beklentileri

**Interfaces:**
- Consumes: Görev 4 `gecerli_belge`, kayıt alanları; `_load_json`, `_portal_zamani`, `_course_color`, `subject_themes.family_of`
- Produces:
  - `dashboard_api._sinavlar_belgesi() -> dict | None` (dosya yok/bozuk/eski sürüm → None)
  - `dashboard_api._sinav_api_listesi(data, now) -> {"exams", "stats", "tespit"}` — `tespit = {"uretildi", "incelenmedi"} | None`
  - ExamItem yeni alanları: `tur: str | None`, `konular: list[str]`, `kaynaklar: [{tur, etiket, alinti, baglanti}]`, `ilkTespit: str | None`, `degisti: str | None`, `hafta: str | None`, `tarihBelirsiz: bool`; `aiSummary` ve `studyGuide` yok
  - TS: `export interface SinavKaynagi { tur: string; etiket: string; alinti: string; baglanti: string | null }`; `ExamItem`'a opsiyonel `tur?`, `konular?`, `kaynaklar?`, `ilkTespit?`, `degisti?`, `hafta?`, `tarihBelirsiz?`; `ExamsApiResponse.tespit?: { uretildi: string; incelenmedi: number } | null`

- [ ] **Adım 1: Başarısız testi yaz** — `tests/test_sinav_api.py`

```python
"""/api/exams reads output/sinavlar.json (spec §4): status per request on the
Istanbul clock, the new fields, and the fallback to the takvim computation."""
import os
from datetime import datetime

import pytest

os.environ["TEST_AUTH_BYPASS"] = "1"
import src.dashboard_api as api  # noqa: E402
from src.assistant_tools import sinavlar_metni  # noqa: E402
from src.sinav_tespiti import SURUM  # noqa: E402

SIMDI = datetime(2026, 10, 16, 10, 0)


def kayit(**kw):
    k = {"id": "k1", "ders": "Matematik", "tur": "konu_tarama", "baslik": "Matematik KTT", "tarih": "2026-10-20",
         "saat": None, "hafta": None, "konular": ["Mutlak değer"],
         "kaynaklar": [{"tur": "ders_karti", "konum": {"bolum": "ders_icerikleri_haftalar",
                                                        "hafta": "4. Hafta 05 Eki. - 11 Eki.", "ders": "Matematik",
                                                        "sira": 1}, "alinti": "15 EKİM … KTT"}],
         "ilk_tespit": "2026-10-15T09:00:00", "icerik_surumu": "abc", "degisti": None, "sentetik": False,
         "taban": None, "son_yayin": "2026-10-05"}
    k.update(kw)
    return k


# Taken at collection: conftest replaces api._sinavlar_belgesi with "no file" for every test.
GERCEK_BELGE = api._sinavlar_belgesi


def _dosya(monkeypatch, belge, scraped=None):
    from src.sinav_tespiti import gecerli_belge
    monkeypatch.setattr(api, "_sinavlar_belgesi", lambda: gecerli_belge(belge))
    monkeypatch.setattr(api, "_scraped", lambda: scraped if scraped is not None else {"takvim": []})


def _belge(*kayitlar, incelenmedi=0):
    return {"uretildi": "2026-10-16T09:45:00", "surum": SURUM, "sinavlar": list(kayitlar),
            "ozet": {"aday": 1, "incelenen": 1, "incelenmedi": incelenmedi, "butce_usd": 0.0}}


def test_metin_kaydi_examitem_olur(monkeypatch):
    _dosya(monkeypatch, _belge(kayit(), incelenmedi=2))
    sonuc = api._sinav_api_listesi(api._scraped(), SIMDI)
    [e] = sonuc["exams"]
    assert (e["id"], e["course"], e["title"], e["date"], e["allDay"], e["status"]) == \
        ("k1", "Matematik", "Matematik KTT", "2026-10-20", True, "upcoming")
    assert (e["tur"], e["konular"], e["ilkTespit"], e["degisti"], e["hafta"], e["tarihBelirsiz"]) == \
        ("konu_tarama", ["Mutlak değer"], "2026-10-15T09:00:00", None, None, False)
    assert e["kaynaklar"] == [{"tur": "ders_karti", "etiket": "Matematik ders içeriği · 4. Hafta 05 Eki. - 11 Eki.",
                               "alinti": "15 EKİM … KTT",
                               "baglanti": "/dersler?hafta=4.%20Hafta%2005%20Eki.%20-%2011%20Eki."}]
    assert "aiSummary" not in e and "studyGuide" not in e
    assert e["relatedHomework"] == [] and e["relatedContent"] == []
    assert sonuc["tespit"] == {"uretildi": "2026-10-16T09:45:00", "incelenmedi": 2}
    assert sonuc["stats"] == {"upcoming": 1, "past": 0, "averageGrade": None}


@pytest.mark.parametrize("kw,durum", [
    ({"tarih": "2026-10-15"}, "past"),
    ({"tarih": "2026-10-16"}, "upcoming"),
    ({"tarih": "2026-10-16", "saat": "09:00"}, "past"),
    ({"tarih": None, "hafta": "2026-10-12"}, "upcoming"),
    ({"tarih": None, "hafta": "2026-10-05"}, "past"),
    ({"tarih": None}, "upcoming"),
])
def test_durum_istek_aninda(monkeypatch, kw, durum):
    _dosya(monkeypatch, _belge(kayit(**kw)))
    [e] = api._sinav_api_listesi(api._scraped(), SIMDI)["exams"]
    assert e["status"] == durum


def test_tarih_belirsiz_ve_hafta(monkeypatch):
    _dosya(monkeypatch, _belge(kayit(tarih=None, hafta="2026-10-19")))
    [e] = api._sinav_api_listesi(api._scraped(), SIMDI)["exams"]
    assert (e["date"], e["hafta"], e["tarihBelirsiz"]) == (None, "2026-10-19", True)


def test_takvim_tabanli_kayit_tabani_korur(monkeypatch):
    taban = {"id": "gis1", "course": "Özdebir GİS", "title": "Özdebir GİS · İzleme Sınavı", "rawTitle": "GİS-1",
             "courseColor": "#123456", "courseFamily": "teal", "examNumber": 1, "date": "2026-10-23T09:00:00",
             "endDate": "2026-10-23T12:10:00", "allDay": False, "status": "upcoming", "grade": None,
             "relatedHomework": [{"title": "Deneme", "deadline": "", "status": ""}], "relatedContent": []}
    _dosya(monkeypatch, _belge(kayit(id="gis1", taban=taban, tarih="2026-10-23", saat="09:00",
                                     kaynaklar=[{"tur": "takvim", "konum": {"id": "gis1"}, "alinti": "GİS-1"}])))
    [e] = api._sinav_api_listesi(api._scraped(), SIMDI)["exams"]
    assert (e["courseColor"], e["rawTitle"], e["endDate"], e["examNumber"]) == ("#123456", "GİS-1", "2026-10-23T12:10:00", 1)
    assert e["relatedHomework"] == taban["relatedHomework"]
    assert e["kaynaklar"] == [{"tur": "takvim", "etiket": "Okul takvimi", "alinti": "GİS-1", "baglanti": "/takvim"}]


def test_kaynak_baglantilari(monkeypatch):
    kaynaklar = [{"tur": "odev", "konum": {"bolum": "odev", "baslik": "KTT"}, "alinti": "a"},
                 {"tur": "duyuru", "konum": {"bolum": "duyuru", "sira": 0}, "alinti": "b"},
                 {"tur": "ek", "konum": {"bolum": "ek", "id": "abc123"}, "alinti": "c"},
                 {"tur": "not_tablosu", "konum": {"id": "n"}, "alinti": "d"}]
    _dosya(monkeypatch, _belge(kayit(kaynaklar=kaynaklar)))
    [e] = api._sinav_api_listesi(api._scraped(), SIMDI)["exams"]
    assert [(k["etiket"], k["baglanti"]) for k in e["kaynaklar"]] == [
        ("Ödev · KTT", "/isler"), ("Okul duyurusu", "/duyurular"), ("Portal eki", "/api/ekler/abc123"),
        ("Not tablosu", "/notlar")]


def test_bozuk_dosyada_eski_hesaba_duser(monkeypatch):
    from tests.sinav_fikstur import TAKVIM_SINAV
    _dosya(monkeypatch, "bozuk", scraped={"takvim": TAKVIM_SINAV})
    sonuc = api._sinav_api_listesi(api._scraped(), SIMDI)
    assert sonuc["tespit"] is None and len(sonuc["exams"]) == 2
    assert all(e["konular"] == [] and e["kaynaklar"] == [] and e["tarihBelirsiz"] is False for e in sonuc["exams"])


def test_bozuk_dosya_okunurken_500_degil_none(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "OUTPUT_DIR", str(tmp_path))
    assert GERCEK_BELGE() is None                                  # dosya yok
    (tmp_path / "sinavlar.json").write_text("{bozuk", encoding="utf-8")
    assert GERCEK_BELGE() is None                                  # JSONDecodeError yutulur
    (tmp_path / "sinavlar.json").write_text(
        '{"surum": %d, "sinavlar": [], "uretildi": "x", "ozet": {}}' % SURUM, encoding="utf-8")
    assert GERCEK_BELGE()["sinavlar"] == []


def test_eski_surumde_eski_hesaba_duser(monkeypatch):
    from tests.sinav_fikstur import TAKVIM_SINAV
    _dosya(monkeypatch, {**_belge(kayit()), "surum": SURUM + 1}, scraped={"takvim": TAKVIM_SINAV})
    assert api._sinav_api_listesi(api._scraped(), SIMDI)["tespit"] is None


def test_rota_dosyayi_okur(monkeypatch):
    _dosya(monkeypatch, _belge(kayit()))
    api.app.config["TESTING"] = True
    with api.app.test_client() as c:
        veri = c.get("/api/exams").get_json()
    assert veri["exams"][0]["konular"] == ["Mutlak değer"] and "tespit" in veri


def test_asistan_gercek_konulari_yazar():
    e = {"course": "Matematik", "title": "Matematik KTT", "rawTitle": "Matematik KTT", "date": "2026-10-20",
         "allDay": True, "status": "upcoming", "konular": ["Mutlak değer", "Tam sayılar"],
         "kaynaklar": [{"tur": "ders_karti", "etiket": "Matematik ders içeriği · 4. Hafta", "alinti": "KTT konuları",
                        "baglanti": "/dersler"}], "relatedContent": [{"title": "Haftanın kartı"}]}
    metin = sinavlar_metni([e], SIMDI)
    assert "Konular: Mutlak değer; Tam sayılar" in metin
    assert "Haftanın kartı" not in metin
    assert "Kaynak: Matematik ders içeriği · 4. Hafta — “KTT konuları”" in metin


def test_asistan_tarih_belirsiz():
    e = {"course": "İngilizce", "title": "Irregular Verbs Quiz", "rawTitle": "Irregular Verbs Quiz", "date": None,
         "allDay": False, "status": "upcoming", "konular": [], "kaynaklar": [], "hafta": "2026-10-19",
         "tarihBelirsiz": True}
    metin = sinavlar_metni([e], SIMDI)
    assert "tarih belirsiz (19.10 haftası)" in metin and "Konular: yok" in metin
```

- [ ] **Adım 2: Testin başarısız olduğunu gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_sinav_api.py`
Expected: FAIL — `AttributeError: module 'src.dashboard_api' has no attribute '_sinav_api_listesi'`

- [ ] **Adım 3: Uygula — `src/dashboard_api.py`**

`_sinav_listesi`'ten `content_map` ve `enrichment` okumasını, `ai_summary`/`study_guide` hesabını ve iki ExamItem sözlüğündeki `"studyGuide"`, `"aiSummary"` anahtarlarını sil (spec §8: boş alanlar kalkar; yazarları 2bd7ad3'te silinmişti). `_sinav_listesi`'ten hemen sonra ekle:

```python
_KAYNAK_ETIKETI = {"takvim": "Okul takvimi", "duyuru": "Okul duyurusu", "ek": "Portal eki",
                   "not_tablosu": "Not tablosu"}


def _sinav_kaynagi(k):
    """A source as the dashboard shows it: a label, a short quote and where it opens."""
    tur = str(k.get("tur") or "")
    konum = k.get("konum") if isinstance(k.get("konum"), dict) else {}
    if tur == "ders_karti":
        hafta = konum.get("hafta")
        etiket = f"{normalize_course(konum.get('ders') or '') or konum.get('ders') or 'Ders'} ders içeriği"
        etiket += f" · {hafta}" if hafta else ""
        baglanti = f"/dersler?hafta={quote(hafta)}" if hafta else "/dersler"
    elif tur == "odev":
        etiket, baglanti = f"Ödev · {konum.get('baslik') or ''}".rstrip(" ·"), "/isler"
    else:
        etiket = _KAYNAK_ETIKETI.get(tur, "Kaynak")
        baglanti = {"takvim": "/takvim", "duyuru": "/duyurular", "not_tablosu": "/notlar"}.get(tur)
        if tur == "ek" and konum.get("id"):
            baglanti = f"/api/ekler/{konum['id']}"
    return {"tur": tur, "etiket": etiket, "alinti": str(k.get("alinti") or "")[:300], "baglanti": baglanti}


def _sinav_durumu(k, taban, now):
    if k.get("sentetik"):
        return "past"
    if taban and taban.get("date"):
        an = _portal_zamani(taban["date"])
        return "upcoming" if an is not None and an > now else "past"
    if k.get("tarih"):
        saat = k.get("saat") or "23:59"
        return "upcoming" if datetime.fromisoformat(f"{k['tarih']}T{saat}") > now else "past"
    if k.get("hafta"):
        son = datetime.fromisoformat(k["hafta"]) + timedelta(days=6, hours=23, minutes=59)
        return "upcoming" if son > now else "past"
    return "upcoming"


def _kayittan_sinav(k, now):
    taban = k.get("taban") if isinstance(k.get("taban"), dict) else None
    if taban:
        e = {key: v for key, v in taban.items() if key not in ("aiSummary", "studyGuide")}
    else:
        ders = k.get("ders") or "Genel"
        tarih_saat = f"{k['tarih']}T{k['saat']}:00" if k.get("tarih") and k.get("saat") else k.get("tarih")
        e = {"id": k.get("id"), "course": ders, "title": k.get("baslik") or "Sınav",
             "rawTitle": k.get("baslik") or "Sınav", "courseColor": _course_color(ders),
             "courseFamily": subject_themes.family_of(ders), "examNumber": None, "date": tarih_saat,
             "endDate": None, "allDay": bool(k.get("tarih") and not k.get("saat")), "grade": None,
             "relatedHomework": [], "relatedContent": []}
    e["status"] = _sinav_durumu(k, taban, now)
    e.update({
        "tur": k.get("tur"), "konular": list(k.get("konular") or []),
        "kaynaklar": [_sinav_kaynagi(x) for x in (k.get("kaynaklar") or []) if isinstance(x, dict)],
        "ilkTespit": k.get("ilk_tespit"), "degisti": k.get("degisti"), "hafta": k.get("hafta"),
        "tarihBelirsiz": not e.get("date") and not k.get("sentetik"),
    })
    return e


def _sinavlar_belgesi():
    """output/sinavlar.json, validated; None when absent, unreadable or of another
    version. Its own function so tests can stand in for the live file
    (tests/conftest.py `_canli_sinavlar_dosyasi_yok`)."""
    from src.sinav_tespiti import gecerli_belge
    try:
        return gecerli_belge(_load_json("sinavlar.json"))
    except (OSError, ValueError):
        return None


def _sinav_api_listesi(data, now=None):
    """/api/exams: output/sinavlar.json when it is readable (the sync step's
    single source, spec 2026-10-16 §4), else today's takvim + grade-table
    computation — the list is never empty for want of the file."""
    now = now or datetime.now()
    belge = _sinavlar_belgesi()
    if belge is None:
        eski = _sinav_listesi(data, now=now)
        for e in eski["exams"]:
            e.update({"tur": None, "konular": [], "kaynaklar": [], "ilkTespit": None, "degisti": None,
                      "hafta": None, "tarihBelirsiz": False})
        return {**eski, "tespit": None}
    sinavlar = [_kayittan_sinav(k, now) for k in belge["sinavlar"] if isinstance(k, dict) and k.get("id")]

    def anahtar(e):
        return e.get("date") or (e.get("hafta") or "9999") + "T99"
    upcoming = sorted([e for e in sinavlar if e["status"] == "upcoming"], key=anahtar)
    past = sorted([e for e in sinavlar if e["status"] == "past"], key=lambda e: e.get("date") or "", reverse=True)
    notlar = [int(e["grade"]) for e in sinavlar if str(e.get("grade") or "").isdigit()]
    ozet = belge.get("ozet") if isinstance(belge.get("ozet"), dict) else {}
    return {"exams": upcoming + past,
            "stats": {"upcoming": len(upcoming), "past": len(past),
                      "averageGrade": round(sum(notlar) / len(notlar), 1) if notlar else None},
            "tespit": {"uretildi": belge.get("uretildi"), "incelenmedi": int(ozet.get("incelenmedi") or 0)}}
```

Dosyanın modül düzeyi import'larına `from pathlib import Path` ve `from urllib.parse import quote` ekle (bugün `quote` yalnız bir fonksiyonun içinde import ediliyor, `Path` hiç yok; Görev 7 de `Path`'i kullanır). `timedelta` zaten import'lu.

`tests/conftest.py` sonuna (canlı checkout'ta testler gerçek `output/sinavlar.json`'u görmesin — `_scraped`'i taklit eden her `/api/exams` testi yoksa canlı sınavları alırdı):

```python
@pytest.fixture(autouse=True)
def _canli_sinavlar_dosyasi_yok(monkeypatch):
    """/api/exams reads output/sinavlar.json since 2026-10-16 (plan sinav-uyari,
    Görev 6). In the live checkout that file exists, and a test that patches
    _scraped would get the live exams instead of its own. Every test sees "no
    file" — the takvim fallback — unless it patches _sinavlar_belgesi itself."""
    api = sys.modules.get("src.dashboard_api")
    if api is not None:
        monkeypatch.setattr(api, "_sinavlar_belgesi", lambda: None)
``` `/api/exams` rotasında `_sinav_listesi(_scraped())` → `_sinav_api_listesi(_scraped())`; `_canli_sinavlar` içinde `_sinav_listesi(_scraped(), now=istanbul_simdi())["exams"]` → `_sinav_api_listesi(_scraped(), now=istanbul_simdi())["exams"]`. `grep -n "_sinav_listesi(" src/*.py src/mcp_server/*.py` ile başka çağıran varsa (ör. modül bağlama) aynı değişikliğin gerekip gerekmediğini kontrol et; `sinav_tespiti._taban` **eskiyi** çağırmaya devam eder (taban hesabı).

- [ ] **Adım 4: Uygula — `src/assistant_tools.py` `sinavlar_metni`**

`satir()` iç fonksiyonunu değiştir:

```python
    def satir(e: dict[str, Any], ham_ad: bool) -> str:
        ders = str(e.get("course") or "").strip() or "Ders belirsiz"
        baslik = str(e.get("title") or "").strip()
        tur = baslik.split(" · ", 1)[1] if " · " in baslik else (baslik or "Sınav")
        if e.get("tarihBelirsiz"):
            hafta = _zaman_oku(e.get("hafta")) if e.get("hafta") else None
            zaman = f"tarih belirsiz ({hafta.strftime('%d.%m')} haftası)" if hafta else "tarih belirsiz"
        else:
            zaman = _tarih_yaz(e.get("date"), simdi, bool(e.get("allDay")))
        metin = f"- {ders} — {tur} · {zaman}"
        if str(e.get("grade") or "").strip():
            metin += f" · not {e['grade']}"
        ham = " ".join(str(e.get("rawTitle") or "").split())
        if ham_ad and ham and ham != baslik:
            metin += f"\n  Portaldaki adı: {_kirp(ham, 140)}"
        if ham_ad:
            konular = [str(k).strip() for k in (e.get("konular") or []) if str(k).strip()]
            metin += "\n  Konular: " + ("; ".join(konular[:10])[:2000] if konular else "yok")
            kaynak = next((k for k in (e.get("kaynaklar") or [])
                           if isinstance(k, dict) and k.get("tur") != "takvim"), None)
            if kaynak:
                metin += f"\n  Kaynak: {kaynak.get('etiket')} — “{_kirp(str(kaynak.get('alinti') or ''), 160)}”"
        return metin
```

`parcalar`'ın ilk satırındaki parantezi güncelle: `" (Sınavlar sayfasının listesi: portal takvimi, ders duyuruları ve not tablosu)"`. `_zaman_oku` aynı modülde tanımlı (`_tarih_yaz` kullanıyor); `_kirp(..., 160)` imzası `_kirp(metin, sinir)`.

- [ ] **Adım 5: Uygula — `dashboard/src/types.ts`**

```ts
export interface SinavKaynagi {
  tur: string
  etiket: string
  alinti: string
  /** Pano içi yol ya da ek indirme adresi; yoksa null. */
  baglanti: string | null
}

export interface ExamItem {
  id: string
  course: string
  title: string
  rawTitle: string
  /** Subject mark colour (light-theme accent of the subject family). */
  courseColor: string
  /** Tedy ders renk ailesi (Carbon Tag family) — see theme/subjects.ts. */
  courseFamily?: SubjectFamily
  examNumber: number | null
  date: string | null
  endDate: string | null
  allDay: boolean
  status: 'upcoming' | 'past'
  grade: string | null
  relatedHomework: { title: string; deadline: string; status: string }[]
  relatedContent: { title: string; type: string }[]
  /** sinavlar.json (2026-10-16): yazili | kisa_sinav | konu_tarama | deneme | ortak_sinav | diger */
  tur?: string | null
  /** Kaynakta sınavın konusu olarak sayılanlar — "bu haftanın kartları" değil. */
  konular?: string[]
  kaynaklar?: SinavKaynagi[]
  ilkTespit?: string | null
  degisti?: string | null
  /** Gün değil yalnız hafta biliniyorsa haftanın pazartesisi (YYYY-MM-DD). */
  hafta?: string | null
  tarihBelirsiz?: boolean
}

export interface ExamsApiResponse {
  exams: ExamItem[]
  stats: { upcoming: number; past: number; averageGrade: number | null }
  /** Son tespit turu; sinavlar.json okunamadıysa null. */
  tespit?: { uretildi: string; incelenmedi: number } | null
}
```

`ExamTimeline.tsx`'teki `exam.aiSummary || exam.studyGuide ||` ve iki "🤖" bölümünü sil (bölüm Görev 10'da yeniden kurulur; şimdilik derlenmesi yeter). `grep -rn "aiSummary\|studyGuide" dashboard/src dashboard/tests` → e2e fikstürlerindeki (`_bugun-fixtures.ts` `SINAV`, `_gorsel-fixtures.ts`) bu iki alanı da sil.

- [ ] **Adım 6: Testlerin geçtiğini gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_sinav_api.py tests/test_exams.py tests/test_assistant_ogrenci_araclari.py tests/test_assistant_alistirma_araclari.py tests/test_mcp_baglam.py tests/test_reader_role.py tests/test_portal_saati.py`
Expected: PASS, şu dört eski test güncellendikten sonra (plan doğrulamasında ölçüldü, 2026-10-16):
- `tests/test_exams.py::TestExamsEndpoint::test_exam_has_required_fields` — zorunlu anahtar listesinden `studyGuide` ve `aiSummary`'yi çıkar, `tur`, `konular`, `kaynaklar`, `tarihBelirsiz`'i ekle.
- `tests/test_exams.py::TestRealPortalExamTitles::test_content_map_key_tries_legacy_then_resolved` ve `test_content_map_key_also_tries_resolved_course` — sil: `exam_content_map.json` okuması kalktı (yazarı 2bd7ad3'te silinmişti).
- `tests/test_assistant_alistirma_araclari.py::test_sinav_konulari_yalniz_yaklasanlarda_ve_en_fazla_on` — fikstürdeki `"relatedContent": [{"title": …}]` yerine `"konular": [...]`; iddialar aynı kalır.

Her birini ledger'a `Ruling:` olarak yaz. Taban kırmızıları (bu planla ilgisiz, temiz HEAD'de de kırmızı, tarihe bağlı fikstür): `tests/test_assistant_odev_listesi.py::test_arac_sonucu_okunur_atifla_doner`, `tests/test_assistant_yerel_kaynaklar.py::test_arac_sebit_kaynagiyla_baglanir_ve_kaynak_hatasi_ana_listeyi_bozmaz`.
Run: `cd dashboard && npx tsc -b --noEmit && npm run lint`
Expected: hata yok.

- [ ] **Adım 7: Commit**

```bash
git add src/dashboard_api.py src/assistant_tools.py dashboard/src/types.ts dashboard/src/components/ExamTimeline.tsx dashboard/tests/e2e/_bugun-fixtures.ts dashboard/tests/e2e/_gorsel-fixtures.ts tests/conftest.py tests/test_sinav_api.py tests/test_exams.py tests/test_assistant_alistirma_araclari.py
git commit -m "feat(sinav): /api/exams sinavlar.json'dan; asistan gerçek konuları okur

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

(Değişmeyen test dosyalarını `git add`'e koyma; `git status --short` ile kontrol et.)

---

### Görev 7: Web push modülü ve abonelik uçları

**Files:**
- Create: `src/web_push.py`
- Modify: `requirements.txt`, `src/dashboard_api.py` (dört uç)
- Test: `tests/test_web_push.py`, `tests/test_bildirim_api.py`

**Interfaces:**
- Consumes: `src.json_utils.atomic_json_dump`; `src.mcp_server.env_prep.read_env/set_value/write_env/EnvPrepError`; `roles.is_full`; Görev 8'in `sinav_uyari.kisiyi_tohumla(kok, email, simdi) -> int` (uç onu tembel import eder; Görev 8 bitene kadar uç testi bunu `monkeypatch` ile sağlar)
- Produces:
  - `BILINEN_PUSH_ALANLARI: tuple[str, ...]`, `OLU_KODLAR = {403, 404, 410}`, `TTL = 12 * 3600`, `VAPID_KONU_VARSAYILAN = "https://tedy.online"`, `ABONELIKLER = PurePosixPath("output/bildirim_abonelikleri.json")`
  - `@dataclass(frozen=True) VapidAyarlari(public: str, private: str, subject: str)`; `vapid_ayarlari() -> VapidAyarlari | None`
  - `anahtar_uret() -> tuple[str, str]` (public b64url 65 bayt, private b64url 32 bayt)
  - `abonelik_dogrula(govde: Any) -> dict | None` → `{"endpoint", "keys": {"p256dh", "auth"}, "cihaz"}`
  - `class AbonelikDeposu(yol: Path, simdi=datetime.now)` — `ekle(email, abonelik) -> bool` (yeni cihazsa True), `sil(email, endpoint) -> bool`, `kisinin(email) -> list[dict]` (öğe: `{"abonelik": {endpoint, keys}, "cihaz", "eklendi"}`), `hepsi() -> dict[str, list[dict]]`, `endpoint_sil(endpoint) -> int`
  - `@dataclass(frozen=True) GonderimSonucu(durum: str, kod: int | None, mesaj: str)` — `durum` ∈ `ok | olu | hata`
  - `gonder(abonelik: dict, yuk: dict, vapid: VapidAyarlari, webpush_fn=None) -> GonderimSonucu`
  - CLI: `python -m src.web_push anahtar-uret [--degistir]` (`.env`'e `TEDY_VAPID_PUBLIC`, `TEDY_VAPID_PRIVATE` yazar; değer basmaz)
  - Uçlar: `GET /api/bildirim/anahtar` → `{"anahtar": str|null, "acik": bool}`; `POST /api/bildirim/abonelik` → 201 `{"ok": true}` / 400; `DELETE /api/bildirim/abonelik` (`{"endpoint"}`) → 200 / 404; `POST /api/bildirim/deneme` → `{"gonderilen": n}` / 404 (cihaz yok) / 503 (VAPID yok)

- [ ] **Adım 1: Bağımlılığı ekle — KULLANICI ONAYI GEREKİR**

`requirements.txt`'te `anthropic>=1.8,<2` satırından sonra:

```
# Web push (sınav uyarıları, plan 2026-10-16-sinav-tespiti-ve-uyari Görev 7)
pywebpush>=2,<3
```

`.venv` canlı checkout'la paylaşılır: kurulum canlı ortamı değiştirir. **Dur ve kullanıcıya sor:** "`pywebpush`'u paylaşılan `.venv`'e kurayım mı? (yalnız ekleme; mevcut paketler değişmez)". Onay gelince:

```bash
.venv/bin/python -m pip install 'pywebpush>=2,<3' > /tmp/sinav-pip.log 2>&1; tail -2 /tmp/sinav-pip.log
.venv/bin/python -c "import pywebpush, py_vapid; print('ok')"
```

Expected: `ok`. Onay gelmezse bu görevin testlerinden `test_vapid_anahtari_py_vapid_ile_okunur` atlanır (`pytest.importorskip`) ve ledger'a `Ruling` yazılır; diğer testler pywebpush'a dokunmaz.

- [ ] **Adım 2: Başarısız testi yaz** — `tests/test_web_push.py`

```python
"""src/web_push: VAPID keys, subscription validation and store, sending.
No network: sending goes through a fake webpush callable."""
import base64
import json
from types import SimpleNamespace

import pytest

from src.web_push import (AbonelikDeposu, GonderimSonucu, VapidAyarlari, abonelik_dogrula, anahtar_uret, gonder,
                          vapid_ayarlari)

P256 = base64.urlsafe_b64encode(b"\x04" + b"a" * 64).rstrip(b"=").decode()
AUTH = base64.urlsafe_b64encode(b"b" * 16).rstrip(b"=").decode()


def abonelik(endpoint="https://fcm.googleapis.com/fcm/send/abc", cihaz="Android"):
    return {"endpoint": endpoint, "keys": {"p256dh": P256, "auth": AUTH}, "cihaz": cihaz}


def test_anahtar_uret_bicim():
    acik, ozel = anahtar_uret()
    assert len(base64.urlsafe_b64decode(acik + "==")) == 65
    assert len(base64.urlsafe_b64decode(ozel + "==")) == 32
    assert anahtar_uret() != (acik, ozel)


def test_vapid_anahtari_py_vapid_ile_okunur():
    py_vapid = pytest.importorskip("py_vapid")
    from cryptography.hazmat.primitives import serialization
    acik, ozel = anahtar_uret()
    v = py_vapid.Vapid01.from_string(ozel)
    nokta = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    assert base64.urlsafe_b64encode(nokta).rstrip(b"=").decode() == acik


def test_vapid_ayarlari_ortamdan(monkeypatch):
    monkeypatch.delenv("TEDY_VAPID_PUBLIC", raising=False)
    assert vapid_ayarlari() is None
    monkeypatch.setenv("TEDY_VAPID_PUBLIC", "pub")
    monkeypatch.setenv("TEDY_VAPID_PRIVATE", "priv")
    monkeypatch.delenv("TEDY_VAPID_SUBJECT", raising=False)
    assert vapid_ayarlari() == VapidAyarlari("pub", "priv", "https://tedy.online")


@pytest.mark.parametrize("endpoint", [
    "https://fcm.googleapis.com/fcm/send/x", "https://updates.push.services.mozilla.com/wpush/v2/x",
    "https://web.push.apple.com/QGx", "https://wns2-par02p.notify.windows.com/w/?token=x",
])
def test_dogrula_bilinen_servisler(endpoint):
    assert abonelik_dogrula(abonelik(endpoint))["endpoint"] == endpoint


@pytest.mark.parametrize("govde", [
    None, "x", {}, abonelik("http://fcm.googleapis.com/x"), abonelik("https://evil.example.com/x"),
    abonelik("https://fcm.googleapis.com.evil.com/x"),
    {**abonelik(), "keys": {"p256dh": "kısa", "auth": AUTH}},
    {**abonelik(), "keys": {"p256dh": P256}},
    {**abonelik(), "endpoint": "https://fcm.googleapis.com/" + "x" * 2100},
])
def test_dogrula_reddeder(govde):
    assert abonelik_dogrula(govde) is None


def test_dogrula_cihaz_adi_kirpilir():
    assert abonelik_dogrula(abonelik(cihaz="x" * 200))["cihaz"] == "x" * 80
    assert abonelik_dogrula({**abonelik(), "cihaz": None})["cihaz"] == "Tarayıcı"


def test_depo_ekle_sil_kisinin(tmp_path):
    d = AbonelikDeposu(tmp_path / "a.json")
    assert d.ekle("isik@x", abonelik_dogrula(abonelik())) is True
    assert d.ekle("isik@x", abonelik_dogrula(abonelik(cihaz="Yeni ad"))) is False   # same endpoint: replaced
    assert [c["cihaz"] for c in d.kisinin("isik@x")] == ["Yeni ad"]
    d.ekle("anne@x", abonelik_dogrula(abonelik("https://web.push.apple.com/Q")))
    assert set(d.hepsi()) == {"isik@x", "anne@x"}
    assert d.sil("anne@x", "https://fcm.googleapis.com/fcm/send/abc") is False      # not hers
    assert d.sil("isik@x", "https://fcm.googleapis.com/fcm/send/abc") is True
    assert set(d.hepsi()) == {"anne@x"}


def test_depo_iki_ornek_birbirini_ezmez(tmp_path):
    a, b = AbonelikDeposu(tmp_path / "a.json"), AbonelikDeposu(tmp_path / "a.json")
    a.ekle("isik@x", abonelik_dogrula(abonelik()))
    b.ekle("anne@x", abonelik_dogrula(abonelik("https://web.push.apple.com/Q")))
    assert set(a.hepsi()) == {"isik@x", "anne@x"}


def test_depo_endpoint_sil_her_kisiden(tmp_path):
    d = AbonelikDeposu(tmp_path / "a.json")
    d.ekle("isik@x", abonelik_dogrula(abonelik()))
    d.ekle("anne@x", abonelik_dogrula(abonelik()))
    assert d.endpoint_sil("https://fcm.googleapis.com/fcm/send/abc") == 2
    assert d.hepsi() == {}


def test_depo_bozuk_dosya_bos_sayilir(tmp_path):
    (tmp_path / "a.json").write_text("{bozuk", encoding="utf-8")
    assert AbonelikDeposu(tmp_path / "a.json").hepsi() == {}


VAPID = VapidAyarlari("pub", "priv", "https://tedy.online")


def test_gonder_basari_ve_yuk():
    cagrilar = []

    def sahte(**kw):
        cagrilar.append(kw)
        return SimpleNamespace(status_code=201)
    sonuc = gonder({"endpoint": "https://e", "keys": {"p256dh": P256, "auth": AUTH}},
                   {"baslik": "Sınav", "govde": "Yarın"}, VAPID, webpush_fn=sahte)
    assert sonuc == GonderimSonucu("ok", 201, "")
    [kw] = cagrilar
    assert json.loads(kw["data"]) == {"baslik": "Sınav", "govde": "Yarın"}
    assert kw["vapid_private_key"] == "priv" and kw["vapid_claims"] == {"sub": "https://tedy.online"}
    assert kw["ttl"] == 12 * 3600 and kw["subscription_info"]["endpoint"] == "https://e"


@pytest.mark.parametrize("kod,durum", [(410, "olu"), (404, "olu"), (403, "olu"), (500, "hata"), (None, "hata")])
def test_gonder_hata_siniflari(kod, durum):
    def sahte(**kw):
        hata = RuntimeError("push failed")
        hata.response = SimpleNamespace(status_code=kod) if kod else None
        raise hata
    sonuc = gonder({"endpoint": "https://e", "keys": {}}, {}, VAPID, webpush_fn=sahte)
    assert (sonuc.durum, sonuc.kod) == (durum, kod)
```

- [ ] **Adım 3: Testin başarısız olduğunu gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_web_push.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.web_push'`

- [ ] **Adım 4: Uygula** — `src/web_push.py`

```python
"""Web push (spec §7): VAPID keys, the subscription store and sending.

Keys are generated once (`python -m src.web_push anahtar-uret`) into .env
through env_prep, never printed. The store is per person (email) and per
device, written under flock because gunicorn runs two workers. A 403/404/410
from the push service means the subscription is dead: it is removed."""
from __future__ import annotations

import base64
import fcntl
import json
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator
from urllib.parse import urlsplit

from src.json_utils import atomic_json_dump

BILINEN_PUSH_ALANLARI = ("fcm.googleapis.com", "push.services.mozilla.com", "push.apple.com",
                         "notify.windows.com")
OLU_KODLAR = {403, 404, 410}
TTL = 12 * 3600
VAPID_KONU_VARSAYILAN = "https://tedy.online"
ABONELIKLER = PurePosixPath("output/bildirim_abonelikleri.json")
_ENDPOINT_SINIRI = 2000
_CIHAZ_SINIRI = 80


def _b64(veri: bytes) -> str:
    return base64.urlsafe_b64encode(veri).rstrip(b"=").decode("ascii")


def _b64_bayt(deger: Any) -> bytes | None:
    if not isinstance(deger, str) or not deger or len(deger) > 200:
        return None
    try:
        return base64.urlsafe_b64decode(deger + "=" * (-len(deger) % 4))
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True)
class VapidAyarlari:
    public: str
    private: str
    subject: str


def vapid_ayarlari() -> VapidAyarlari | None:
    acik = os.environ.get("TEDY_VAPID_PUBLIC", "").strip()
    ozel = os.environ.get("TEDY_VAPID_PRIVATE", "").strip()
    if not acik or not ozel:
        return None
    return VapidAyarlari(acik, ozel, os.environ.get("TEDY_VAPID_SUBJECT", "").strip() or VAPID_KONU_VARSAYILAN)


def anahtar_uret() -> tuple[str, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    ozel = ec.generate_private_key(ec.SECP256R1())
    acik = ozel.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return _b64(acik), _b64(ozel.private_numbers().private_value.to_bytes(32, "big"))


def _bilinen_alan(host: str) -> bool:
    return any(host == a or host.endswith("." + a) for a in BILINEN_PUSH_ALANLARI)


def abonelik_dogrula(govde: Any) -> dict | None:
    if not isinstance(govde, dict):
        return None
    endpoint = govde.get("endpoint")
    if not isinstance(endpoint, str) or len(endpoint) > _ENDPOINT_SINIRI:
        return None
    parca = urlsplit(endpoint)
    if parca.scheme != "https" or not parca.hostname or not _bilinen_alan(parca.hostname.lower()):
        return None
    anahtarlar = govde.get("keys") if isinstance(govde.get("keys"), dict) else {}
    p256 = _b64_bayt(anahtarlar.get("p256dh"))
    auth = _b64_bayt(anahtarlar.get("auth"))
    if p256 is None or len(p256) != 65 or auth is None or len(auth) != 16:
        return None
    cihaz = " ".join(str(govde.get("cihaz") or "").split())[:_CIHAZ_SINIRI] or "Tarayıcı"
    return {"endpoint": endpoint, "keys": {"p256dh": anahtarlar["p256dh"], "auth": anahtarlar["auth"]},
            "cihaz": cihaz}


class AbonelikDeposu:
    def __init__(self, yol: str | Path, simdi: Callable[[], datetime] = datetime.now):
        self.yol = Path(yol)
        self.simdi = simdi

    @contextmanager
    def _kilitli(self) -> Iterator[None]:
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        with open(self.yol.with_name(self.yol.name + ".lock"), "a") as kilit:
            fcntl.flock(kilit, fcntl.LOCK_EX)
            yield

    def _oku(self) -> dict[str, list[dict]]:
        try:
            veri = json.loads(self.yol.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        kisiler = veri.get("kisiler") if isinstance(veri, dict) else None
        return {e: [c for c in v if isinstance(c, dict)] for e, v in (kisiler or {}).items() if isinstance(v, list)}

    def _yaz(self, kisiler: dict[str, list[dict]]) -> None:
        atomic_json_dump({"kisiler": {e: v for e, v in kisiler.items() if v}}, str(self.yol))

    def ekle(self, email: str, abonelik: dict) -> bool:
        with self._kilitli():
            kisiler = self._oku()
            cihazlar = [c for c in kisiler.get(email, []) if c.get("abonelik", {}).get("endpoint") != abonelik["endpoint"]]
            yeni = len(cihazlar) == len(kisiler.get(email, []))
            cihazlar.append({"abonelik": {"endpoint": abonelik["endpoint"], "keys": abonelik["keys"]},
                             "cihaz": abonelik.get("cihaz") or "Tarayıcı",
                             "eklendi": self.simdi().isoformat(timespec="seconds")})
            kisiler[email] = cihazlar
            self._yaz(kisiler)
            return yeni

    def sil(self, email: str, endpoint: str) -> bool:
        with self._kilitli():
            kisiler = self._oku()
            once = kisiler.get(email, [])
            sonra = [c for c in once if c.get("abonelik", {}).get("endpoint") != endpoint]
            if len(sonra) == len(once):
                return False
            kisiler[email] = sonra
            self._yaz(kisiler)
            return True

    def endpoint_sil(self, endpoint: str) -> int:
        with self._kilitli():
            kisiler = self._oku()
            silinen = 0
            for email, cihazlar in list(kisiler.items()):
                kalan = [c for c in cihazlar if c.get("abonelik", {}).get("endpoint") != endpoint]
                silinen += len(cihazlar) - len(kalan)
                kisiler[email] = kalan
            if silinen:
                self._yaz(kisiler)
            return silinen

    def kisinin(self, email: str) -> list[dict]:
        return list(self._oku().get(email, []))

    def hepsi(self) -> dict[str, list[dict]]:
        return {e: v for e, v in self._oku().items() if v}


@dataclass(frozen=True)
class GonderimSonucu:
    durum: str
    kod: int | None
    mesaj: str


def gonder(abonelik: dict, yuk: dict, vapid: VapidAyarlari, webpush_fn: Callable[..., Any] | None = None) -> GonderimSonucu:
    if webpush_fn is None:
        from pywebpush import webpush as webpush_fn
    try:
        yanit = webpush_fn(subscription_info={"endpoint": abonelik.get("endpoint"), "keys": abonelik.get("keys") or {}},
                           data=json.dumps(yuk, ensure_ascii=False), vapid_private_key=vapid.private,
                           vapid_claims={"sub": vapid.subject}, ttl=TTL, timeout=10)
        return GonderimSonucu("ok", getattr(yanit, "status_code", None), "")
    except Exception as e:  # pywebpush.WebPushException, requests errors
        kod = getattr(getattr(e, "response", None), "status_code", None)
        return GonderimSonucu("olu" if kod in OLU_KODLAR else "hata", kod, str(e)[:160])


def main(argv: list[str] | None = None) -> int:
    import argparse
    from src.mcp_server import env_prep
    p = argparse.ArgumentParser(description="TEDY web push")
    alt = p.add_subparsers(dest="komut", required=True)
    uret = alt.add_parser("anahtar-uret", help="VAPID anahtar çiftini .env'e yaz (değer basılmaz)")
    uret.add_argument("--degistir", action="store_true", help="var olan anahtarı değiştir (abonelikler geçersizleşir)")
    a = p.parse_args(argv)
    env = env_prep.PROJECT_ROOT / ".env"
    acik, ozel = anahtar_uret()
    try:
        satirlar = env_prep.read_env(env)
        satirlar = env_prep.set_value(satirlar, "TEDY_VAPID_PUBLIC", acik, replace=a.degistir)
        satirlar = env_prep.set_value(satirlar, "TEDY_VAPID_PRIVATE", ozel, replace=a.degistir)
    except env_prep.EnvPrepError as e:
        print(f"hata: {e}", file=sys.stderr)
        return 1
    env_prep.write_env(env, satirlar)
    print("TEDY_VAPID_PUBLIC ve TEDY_VAPID_PRIVATE .env'e yazıldı; ted-dashboard yeniden başlatılmalı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

(`env_prep.EnvPrepError`'ün adı `grep -n "class EnvPrepError" src/mcp_server/env_prep.py` ile doğrulanır.)

- [ ] **Adım 5: web_push testlerinin geçtiğini gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_web_push.py`
Expected: PASS (pywebpush kurulmadıysa `test_vapid_anahtari_py_vapid_ile_okunur` SKIPPED).

- [ ] **Adım 6: Uç testini yaz** — `tests/test_bildirim_api.py`

```python
"""Notification endpoints: session + full role only, own devices only,
validated bodies, and a new person's devices seeded so they get no backlog."""
import base64
import os

import pytest

os.environ.setdefault("TEST_AUTH_BYPASS", "1")
import src.dashboard_api as api  # noqa: E402
import src.web_push as wp  # noqa: E402

P256 = base64.urlsafe_b64encode(b"\x04" + b"a" * 64).rstrip(b"=").decode()
AUTH = base64.urlsafe_b64encode(b"b" * 16).rstrip(b"=").decode()
GOVDE = {"endpoint": "https://fcm.googleapis.com/fcm/send/abc", "keys": {"p256dh": P256, "auth": AUTH},
         "cihaz": "Android"}
TAM = next(e for e, r in api.USER_ROLES.items() if r == api.ROLE_FULL)
OKUR = next((e for e, r in api.USER_ROLES.items() if r == api.ROLE_READER), None)


@pytest.fixture
def ortam(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "TEST_AUTH_BYPASS", False)
    monkeypatch.setattr(api, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("TEDY_VAPID_PUBLIC", "PUB")
    monkeypatch.setenv("TEDY_VAPID_PRIVATE", "PRIV")
    tohum = []
    import src.sinav_uyari as su
    monkeypatch.setattr(su, "kisiyi_tohumla", lambda kok, email, simdi: tohum.append(email) or 0)
    gonderilen = []
    monkeypatch.setattr(wp, "gonder", lambda abonelik, yuk, vapid, webpush_fn=None:
                        gonderilen.append((abonelik["endpoint"], yuk)) or wp.GonderimSonucu("ok", 201, ""))
    api.app.config["TESTING"] = True
    with api.app.test_client() as c:
        yield c, tmp_path, tohum, gonderilen


def _giris(c, email):
    with c.session_transaction() as s:
        s["user_email"] = email


def test_anahtar_oturumsuz_401(ortam):
    c, *_ = ortam
    assert c.get("/api/bildirim/anahtar").status_code == 401


def test_anahtar_tam_rol(ortam, monkeypatch):
    c, *_ = ortam
    _giris(c, TAM)
    monkeypatch.setenv("TEDY_SINAV_UYARI", "1")
    assert c.get("/api/bildirim/anahtar").get_json() == {"anahtar": "PUB", "acik": True}


@pytest.mark.skipif(OKUR is None, reason="kadroda okuyucu yok")
def test_okuyucu_403(ortam):
    c, *_ = ortam
    _giris(c, OKUR)
    assert c.get("/api/bildirim/anahtar").status_code == 403
    assert c.post("/api/bildirim/abonelik", json=GOVDE).status_code == 403


def test_api_anahtari_ile_reddedilir(ortam, monkeypatch):
    c, *_ = ortam
    monkeypatch.setattr(api, "_validate_api_key", lambda k: "etiket")
    r = c.post("/api/bildirim/abonelik", json=GOVDE, headers={"Authorization": "Bearer x"})
    assert r.status_code == 403


def test_ilk_abonelik_kisiyi_tohumlar(ortam):
    c, kok, tohum, _ = ortam
    _giris(c, TAM)
    assert c.post("/api/bildirim/abonelik", json=GOVDE).status_code == 201
    assert tohum == [TAM]
    assert c.post("/api/bildirim/abonelik", json={**GOVDE, "endpoint": GOVDE["endpoint"] + "2"}).status_code == 201
    assert tohum == [TAM]                       # second device of the same person: no reseed
    assert len(wp.AbonelikDeposu(kok / wp.ABONELIKLER).kisinin(TAM)) == 2


def test_gecersiz_govde_400(ortam):
    c, *_ = ortam
    _giris(c, TAM)
    assert c.post("/api/bildirim/abonelik", json={**GOVDE, "endpoint": "https://evil.example/x"}).status_code == 400


def test_baskasinin_aboneligi_silinemez(ortam):
    c, kok, *_ = ortam
    wp.AbonelikDeposu(kok / wp.ABONELIKLER).ekle("baska@x", wp.abonelik_dogrula(GOVDE))
    _giris(c, TAM)
    assert c.delete("/api/bildirim/abonelik", json={"endpoint": GOVDE["endpoint"]}).status_code == 404
    assert wp.AbonelikDeposu(kok / wp.ABONELIKLER).kisinin("baska@x")


def test_kendi_aboneligini_siler(ortam):
    c, kok, *_ = ortam
    _giris(c, TAM)
    c.post("/api/bildirim/abonelik", json=GOVDE)
    assert c.delete("/api/bildirim/abonelik", json={"endpoint": GOVDE["endpoint"]}).status_code == 200
    assert wp.AbonelikDeposu(kok / wp.ABONELIKLER).kisinin(TAM) == []


def test_deneme_yalniz_kendi_cihazlarina(ortam):
    c, kok, _, gonderilen = ortam
    wp.AbonelikDeposu(kok / wp.ABONELIKLER).ekle("baska@x", wp.abonelik_dogrula(
        {**GOVDE, "endpoint": "https://web.push.apple.com/Q"}))
    _giris(c, TAM)
    assert c.post("/api/bildirim/deneme").status_code == 404           # no device yet
    c.post("/api/bildirim/abonelik", json=GOVDE)
    r = c.post("/api/bildirim/deneme")
    assert r.get_json() == {"gonderilen": 1}
    assert [e for e, _ in gonderilen] == [GOVDE["endpoint"]]
    assert gonderilen[0][1]["url"] == "/sinavlar#uyarilar"


def test_deneme_vapid_yoksa_503(ortam, monkeypatch):
    c, *_ = ortam
    monkeypatch.delenv("TEDY_VAPID_PUBLIC")
    _giris(c, TAM)
    c.post("/api/bildirim/abonelik", json=GOVDE)
    assert c.post("/api/bildirim/deneme").status_code == 503


def test_okuyucu_uc_listesinde_degil():
    assert not any("bildirim" in e for e in api.READER_ENDPOINTS)
```

`src/sinav_uyari.py` henüz yok; `import src.sinav_uyari as su` için Görev 8'den önce bu dosyayı en az şu içerikle oluştur (Görev 8 Adım 3 tamamını yazar):

```python
"""Sınav uyarıları (Görev 8'de tamamlanır)."""


def kisiyi_tohumla(kok, email, simdi):
    return 0
```

- [ ] **Adım 7: Uçları uygula** — `src/dashboard_api.py`, `/api/exams` rotasından sonra

```python
# --- Sınav uyarıları: web push abonelikleri (spec 2026-10-16 §7) ---
# Session and full role only: require_auth lets an API key through, so each
# route also wants a session email — a key has no person and no device.

def _bildirim_kisisi():
    if TEST_AUTH_BYPASS:
        return "test@tedy"
    email = str(session.get("user_email", "") or "").lower().strip()
    return email if email and USER_ROLES.get(email) == ROLE_FULL else None


def _abonelik_deposu():
    from src import web_push
    return web_push.AbonelikDeposu(Path(PROJECT_ROOT) / web_push.ABONELIKLER)


@app.route("/api/bildirim/anahtar", methods=["GET"])
@require_auth
def bildirim_anahtar():
    if not _bildirim_kisisi():
        return jsonify({"error": "yalnız oturumla"}), 403
    from src import web_push
    vapid = web_push.vapid_ayarlari()
    return jsonify({"anahtar": vapid.public if vapid else None,
                    "acik": os.environ.get("TEDY_SINAV_UYARI", "0") == "1"})


@app.route("/api/bildirim/abonelik", methods=["POST", "DELETE"])
@require_auth
def bildirim_abonelik():
    email = _bildirim_kisisi()
    if not email:
        return jsonify({"error": "yalnız oturumla"}), 403
    govde = request.get_json(silent=True)
    depo = _abonelik_deposu()
    if request.method == "DELETE":
        endpoint = govde.get("endpoint") if isinstance(govde, dict) else None
        if not isinstance(endpoint, str) or not depo.sil(email, endpoint):
            return jsonify({"error": "abonelik bulunamadı"}), 404
        return jsonify({"ok": True})
    from src import web_push
    abonelik = web_push.abonelik_dogrula(govde)
    if abonelik is None:
        return jsonify({"error": "geçersiz abonelik"}), 400
    ilk_cihaz = not depo.kisinin(email)
    depo.ekle(email, abonelik)
    if ilk_cihaz:
        # A person who turns alerts on gets what happens from now on, not a
        # notification for every exam already known (plan Review Focus 3).
        from src import sinav_uyari
        sinav_uyari.kisiyi_tohumla(Path(PROJECT_ROOT), email, datetime.now())
    return jsonify({"ok": True}), 201


@app.route("/api/bildirim/deneme", methods=["POST"])
@require_auth
def bildirim_deneme():
    email = _bildirim_kisisi()
    if not email:
        return jsonify({"error": "yalnız oturumla"}), 403
    from src import web_push
    vapid = web_push.vapid_ayarlari()
    if vapid is None:
        return jsonify({"error": "bildirim anahtarı ayarlı değil"}), 503
    depo = _abonelik_deposu()
    cihazlar = depo.kisinin(email)
    if not cihazlar:
        return jsonify({"error": "bu hesapta açık cihaz yok"}), 404
    yuk = {"baslik": "TEDY deneme bildirimi", "govde": "Sınav uyarıları bu cihazda çalışıyor.",
           "etiket": "deneme", "url": "/sinavlar#uyarilar"}
    gonderilen = 0
    for c in cihazlar:
        sonuc = web_push.gonder(c["abonelik"], yuk, vapid)
        if sonuc.durum == "ok":
            gonderilen += 1
        elif sonuc.durum == "olu":
            depo.endpoint_sil(c["abonelik"]["endpoint"])
    return jsonify({"gonderilen": gonderilen})
```

`TEST_AUTH_BYPASS` iken `_bildirim_kisisi` "test@tedy" döner; bu yalnız Playwright test sunucusu içindir (e2e uçları zaten taklit eder). `Path` ve `datetime` import'larını doğrula.

- [ ] **Adım 8: Testlerin geçtiğini gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_bildirim_api.py tests/test_web_push.py tests/test_reader_role.py`
Expected: PASS. `test_api_anahtari_ile_reddedilir` 401 dönüyorsa `_validate_api_key` adını `grep -n "def _validate_api_key" src/dashboard_api.py` ile doğrula.

- [ ] **Adım 9: Commit**

```bash
git add requirements.txt src/web_push.py src/sinav_uyari.py src/dashboard_api.py tests/test_web_push.py tests/test_bildirim_api.py
git commit -m "feat(bildirim): VAPID web push, abonelik deposu ve oturuma bağlı uçlar

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Görev 8: Uyarı zamanlayıcısı (`src/sinav_uyari.py`) ve systemd unit'leri

**Files:**
- Modify (tamamen yazılır): `src/sinav_uyari.py`
- Create: `tedy-sinav-uyari.service`, `tedy-sinav-uyari.timer`
- Test: `tests/test_sinav_uyari.py`

**Interfaces:**
- Consumes: Görev 4 `sinav_tespiti.oku`; Görev 7 `web_push.AbonelikDeposu`, `ABONELIKLER`, `vapid_ayarlari`, `gonder`, `GonderimSonucu`; `roles.is_full`, `roles.okur_turu`; `katla`
- Produces:
  - Sabitler: `SESSIZ_BAS = time(22, 0)`, `SESSIZ_SON = time(7, 30)`, `HATIRLATMA = {"gun_7": (7, time(18, 0)), "gun_2": (2, time(18, 0)), "aksam": (1, time(19, 0))}`, `DEFTER = PurePosixPath("output/bildirim_defteri.jsonl")`, `DURUM = PurePosixPath("output/sinav_uyari_durumu.json")`
  - `vadesi_gelen_turler(sinav: dict, simdi: datetime, sessiz_saat: bool = True) -> list[str]`
  - `@dataclass(frozen=True) Bildirim(email: str, sinav: dict, turler: tuple[str, ...])`
  - `planla(sinavlar: list[dict], alicilar: list[str], gonderilmis: set[tuple], simdi: datetime) -> list[Bildirim]`
  - `gun_ifadesi(hedef: date, bugun: date) -> str`, `kisa_ad(sinav: dict) -> str`
  - `metin_kur(sinav: dict, okur: str, turler: tuple[str, ...], simdi: datetime) -> tuple[str, str]` (başlık ≤ 80, gövde ≤ 300)
  - `class BildirimDefteri(yol)` — `anahtarlar() -> set[tuple[str, str, str, str]]`, `yaz(email, sinav, turler, simdi) -> None`
  - `gonder_turu(kok: Path, simdi: datetime, gonderici=None) -> dict` (durum dosyasını yazar)
  - `kisiyi_tohumla(kok: Path, email: str, simdi: datetime) -> int`, `tohumla(kok: Path, simdi: datetime) -> int`
  - `main(argv) -> int` — `python -m src.sinav_uyari gonder|tohumla`

- [ ] **Adım 1: Başarısız testi yaz** — `tests/test_sinav_uyari.py`

```python
"""src/sinav_uyari: which alert is due (pure), the wording, the ledger and one
timer round with a fake sender. 2026-10-19 is a Monday."""
import json
from datetime import date, datetime

import pytest

import src.sinav_uyari as su
import src.web_push as wp
from src.sinav_tespiti import SURUM, yaz as sinavlari_yaz

ISIK = "isikkurtx@gmail.com"


def sinav(**kw):
    s = {"id": "s1", "ders": "Matematik", "tur": "konu_tarama", "baslik": "Matematik KTT", "tarih": "2026-10-26",
         "saat": None, "hafta": None, "konular": ["Tam sayılar", "Rasyonel sayılar", "Mutlak değer"],
         "kaynaklar": [], "ilk_tespit": "2026-10-10T09:00:00", "icerik_surumu": "v1", "degisti": None,
         "sentetik": False, "taban": None, "son_yayin": None}
    s.update(kw)
    return s


@pytest.mark.parametrize("simdi,beklenen", [
    (datetime(2026, 10, 19, 17, 59), ["tespit"]),
    (datetime(2026, 10, 19, 18, 0), ["tespit", "gun_7"]),
    (datetime(2026, 10, 24, 18, 5), ["tespit", "gun_7", "gun_2"]),
    (datetime(2026, 10, 25, 19, 0), ["tespit", "gun_7", "gun_2", "aksam"]),
])
def test_vade_hesabi(simdi, beklenen):
    assert su.vadesi_gelen_turler(sinav(), simdi) == beklenen


def test_sessiz_saatte_hicbir_sey_gitmez():
    assert su.vadesi_gelen_turler(sinav(), datetime(2026, 10, 25, 22, 0)) == []
    assert su.vadesi_gelen_turler(sinav(), datetime(2026, 10, 26, 7, 29)) == []
    assert su.vadesi_gelen_turler(sinav(), datetime(2026, 10, 25, 22, 0), sessiz_saat=False) != []


def test_baslamis_sinava_uyari_yok():
    assert su.vadesi_gelen_turler(sinav(saat="09:00"), datetime(2026, 10, 26, 9, 0)) == []
    assert su.vadesi_gelen_turler(sinav(), datetime(2026, 10, 26, 8, 0)) == []        # no time: school starts 08:00
    assert su.vadesi_gelen_turler(sinav(), datetime(2026, 10, 26, 7, 45)) != []


def test_gec_tespitte_eski_hatirlatma_atlanir():
    gec = sinav(ilk_tespit="2026-10-23T10:00:00")
    assert su.vadesi_gelen_turler(gec, datetime(2026, 10, 24, 18, 0)) == ["tespit", "gun_2"]


def test_kurulumda_bulunan_ilk_tespit_bos():
    assert "gun_7" in su.vadesi_gelen_turler(sinav(ilk_tespit=None), datetime(2026, 10, 19, 18, 0))


def test_tarihsiz_ve_sentetik():
    assert su.vadesi_gelen_turler(sinav(tarih=None), datetime(2026, 10, 19, 18, 0)) == ["tespit"]
    assert su.vadesi_gelen_turler(sinav(tarih=None, hafta="2026-10-05"), datetime(2026, 10, 19, 18, 0)) == []
    assert su.vadesi_gelen_turler(sinav(sentetik=True, tarih=None), datetime(2026, 10, 19, 18, 0)) == []


def test_planla_defteri_ve_surumu_dikkate_alir():
    s = sinav()
    simdi = datetime(2026, 10, 24, 18, 5)
    plan = su.planla([s], [ISIK, "anne@x"], {(ISIK, "s1", "tespit", "v1"), (ISIK, "s1", "gun_7", "v1")}, simdi)
    assert [(b.email, b.turler) for b in plan] == [(ISIK, ("gun_2",)), ("anne@x", ("tespit", "gun_7", "gun_2"))]
    yeni = su.planla([sinav(icerik_surumu="v2")], [ISIK], {(ISIK, "s1", "tespit", "v1")}, simdi)
    assert yeni[0].turler == ("tespit", "gun_7", "gun_2")


def test_gun_ifadesi():
    b = date(2026, 10, 19)
    assert [su.gun_ifadesi(date(2026, 10, d), b) for d in (19, 20, 23, 26)] == \
        ["Bugün", "Yarın", "Cuma", "26 Ekim Pazartesi"]


def test_kisa_ad():
    assert su.kisa_ad(sinav()) == "Matematik KTT"
    assert su.kisa_ad(sinav(baslik="Irregular Verbs Quiz", ders="İngilizce")) == "İngilizce Irregular Verbs Quiz"
    assert su.kisa_ad(sinav(baslik="Özdebir GİS · İzleme Sınavı", ders="Genel")) == "Özdebir GİS · İzleme Sınavı"


def test_metin_isik_ve_aile():
    s = sinav(konular=["Tam sayılar", "Rasyonel sayılar", "Mutlak değer", "Oran"])
    baslik, govde = su.metin_kur(s, "ogrenci", ("gun_7",), datetime(2026, 10, 19, 18, 0))
    assert baslik == "Sınav: Matematik KTT · 26 Ekim Pazartesi"
    assert govde == "26 Ekim Pazartesi Matematik KTT var — Tam sayılar, Rasyonel sayılar, Mutlak değer … Bugün 10 dakikayla başla?"
    _, aile = su.metin_kur(s, "aile", ("gun_2",), datetime(2026, 10, 24, 18, 0))
    assert aile == "Işık'ın Pazartesi Matematik KTT sınavı var. Konular: Tam sayılar, Rasyonel sayılar, Mutlak değer …"


def test_metin_aksam_ve_degisti():
    _, govde = su.metin_kur(sinav(), "ogrenci", ("aksam",), datetime(2026, 10, 25, 19, 0))
    assert govde.startswith("Yarın Matematik KTT var") and govde.endswith("Çantanı hazırla, erken uyu.")
    baslik, _ = su.metin_kur(sinav(degisti="2026-10-20T08:00:00"), "aile", ("tespit",), datetime(2026, 10, 20, 8, 5))
    assert baslik.startswith("Sınav güncellendi: Matematik KTT")


def test_kacan_aksam_sabah_bugun_metniyle():
    s = sinav(saat="10:00")
    turler = tuple(su.vadesi_gelen_turler(s, datetime(2026, 10, 26, 7, 30)))
    assert "aksam" in turler
    baslik, govde = su.metin_kur(s, "ogrenci", turler, datetime(2026, 10, 26, 7, 30))
    assert "· Bugün" in baslik and govde.startswith("Bugün Matematik KTT var") and govde.endswith("Başarılar!")


def test_metin_tarihsiz_ve_sinav_sozcugu_tekrarlanmaz():
    _, govde = su.metin_kur(sinav(tarih=None, hafta="2026-10-26", konular=[]), "aile", ("tespit",),
                            datetime(2026, 10, 20, 9, 0))
    assert govde == "Işık'ın Matematik KTT sınavı duyuruldu (26 Ekim haftası)."
    _, govde = su.metin_kur(sinav(baslik="Özdebir GİS · İzleme Sınavı", ders="Genel", konular=[]), "aile",
                            ("gun_7",), datetime(2026, 10, 19, 18, 0))
    assert govde == "Işık'ın 26 Ekim Pazartesi Özdebir GİS · İzleme Sınavı var."


def test_uzun_konular_yuk_siniri():
    s = sinav(baslik="X" * 2000, konular=[f"Konu {i} " + "y" * 200 for i in range(30)])
    baslik, govde = su.metin_kur(s, "ogrenci", ("gun_7",), datetime(2026, 10, 19, 18, 0))
    assert len(baslik) <= 80 and len(govde) <= 300
    assert "X…" in baslik and govde.count("Konu ") == 3 and govde.count("…") >= 4   # ad + 3 konu kesildi
    yuk = json.dumps({"baslik": baslik, "govde": govde, "etiket": "s1", "url": "/sinavlar?sinav=s1"},
                     ensure_ascii=False).encode()
    assert len(yuk) < 4096


def test_defter_anahtarlari(tmp_path):
    d = su.BildirimDefteri(tmp_path / "d.jsonl")
    assert d.anahtarlar() == set()
    d.yaz(ISIK, sinav(), ("tespit", "gun_7"), datetime(2026, 10, 19, 18, 0))
    with (tmp_path / "d.jsonl").open("a", encoding="utf-8") as f:
        f.write("bozuk satır\n")
    assert d.anahtarlar() == {(ISIK, "s1", "tespit", "v1"), (ISIK, "s1", "gun_7", "v1")}


# --- bir tur ---------------------------------------------------------------------

@pytest.fixture
def kok(tmp_path, monkeypatch):
    monkeypatch.setenv("TEDY_SINAV_UYARI", "1")
    monkeypatch.setenv("TEDY_VAPID_PUBLIC", "PUB")
    monkeypatch.setenv("TEDY_VAPID_PRIVATE", "PRIV")
    monkeypatch.setattr(su, "is_full", lambda e: e in (ISIK, "anne@x"))
    monkeypatch.setattr(su, "okur_turu", lambda e: "ogrenci" if e == ISIK else "aile")
    sinavlari_yaz(tmp_path, {"uretildi": "x", "surum": SURUM, "sinavlar": [sinav()], "ozet": {}})
    depo = wp.AbonelikDeposu(tmp_path / wp.ABONELIKLER)
    for email, endpoint in ((ISIK, "https://fcm.googleapis.com/a"), ("anne@x", "https://web.push.apple.com/b"),
                            ("yabanci@x", "https://fcm.googleapis.com/c")):
        depo.ekle(email, {"endpoint": endpoint, "keys": {"p256dh": "p", "auth": "a"}, "cihaz": "T"})
    return tmp_path


class Gonderici:
    def __init__(self, sonuclar=None):
        self.cagrilar, self.sonuclar = [], sonuclar or {}

    def __call__(self, abonelik, yuk, vapid):
        self.cagrilar.append((abonelik["endpoint"], yuk))
        return self.sonuclar.get(abonelik["endpoint"], wp.GonderimSonucu("ok", 201, ""))


def test_tur_gonderir_deftere_yazar_tekrarlamaz(kok):
    g = Gonderici()
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=g)
    assert sorted(e for e, _ in g.cagrilar) == ["https://fcm.googleapis.com/a", "https://web.push.apple.com/b"]
    yuk = dict(g.cagrilar)["https://fcm.googleapis.com/a"]
    assert yuk["etiket"] == "s1" and yuk["url"] == "/sinavlar?sinav=s1" and "Bugün 10 dakikayla" in yuk["govde"]
    assert durum["gonderilen"] == 2 and durum["kapali"] is False
    assert json.loads((kok / su.DURUM).read_text(encoding="utf-8"))["gonderilen"] == 2
    g2 = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 10), gonderici=g2)
    assert g2.cagrilar == []


def test_bayrak_kapaliyken_gonderim_yok(kok, monkeypatch):
    monkeypatch.setenv("TEDY_SINAV_UYARI", "0")
    g = Gonderici()
    assert su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=g)["kapali"] is True
    assert g.cagrilar == []


def test_olu_abonelik_silinir_hata_tekrar_denenir(kok):
    g = Gonderici({"https://fcm.googleapis.com/a": wp.GonderimSonucu("olu", 410, "gone"),
                   "https://web.push.apple.com/b": wp.GonderimSonucu("hata", 500, "boom")})
    durum = su.gonder_turu(kok, datetime(2026, 10, 19, 18, 0), gonderici=g)
    assert durum["olu_silinen"] == 1 and durum["hatalar"]
    assert wp.AbonelikDeposu(kok / wp.ABONELIKLER).kisinin(ISIK) == []
    assert su.BildirimDefteri(kok / su.DEFTER).anahtarlar() == set()
    g2 = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 10), gonderici=g2)
    assert [e for e, _ in g2.cagrilar] == ["https://web.push.apple.com/b"]


def test_kisiyi_tohumla_eski_tespitleri_gondermez(kok):
    assert su.kisiyi_tohumla(kok, ISIK, datetime(2026, 10, 19, 18, 0)) == 2   # tespit + gun_7
    g = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 19, 18, 5), gonderici=g)
    assert [e for e, _ in g.cagrilar] == ["https://web.push.apple.com/b"]
    g2 = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 24, 18, 0), gonderici=g2)
    assert sorted(e for e, _ in g2.cagrilar) == ["https://fcm.googleapis.com/a", "https://web.push.apple.com/b"]


def test_tohumla_herkesi_isaretler(kok):
    assert su.tohumla(kok, datetime(2026, 10, 19, 23, 0)) == 4   # 2 kişi × (tespit, gun_7); sessiz saat yok sayılır
    g = Gonderici()
    su.gonder_turu(kok, datetime(2026, 10, 20, 9, 0), gonderici=g)
    assert g.cagrilar == []
```

- [ ] **Adım 2: Testin başarısız olduğunu gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_sinav_uyari.py`
Expected: FAIL — `AttributeError: module 'src.sinav_uyari' has no attribute 'vadesi_gelen_turler'`

- [ ] **Adım 3: Uygula** — `src/sinav_uyari.py` (Görev 7'deki taslağın yerine)

```python
"""Sınav uyarıları (spec §6): hangi uyarının vadesi geldiğini hesaplar (saf),
metni hitapla kurar, web push ile yollar ve defterine yazar.

systemd zamanlayıcısıyla 10 dakikada bir koşar; senkron kilidini almaz,
sinavlar.json'u yalnız okur. Bir kişiye bir sınav için aynı turda vadesi gelen
uyarılar tek bildirimde birleşir; defter anahtarı (email, sinav_id, tur,
icerik_surumu) olduğundan aynı uyarı iki kez gitmez, sınav değişirse yeni
sürüm yeniden "tespit" doğurur. 22:00–07:30 arası hiçbir şey gitmez."""
from __future__ import annotations

import fcntl
import json
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator

from src import sinav_tespiti, web_push
from src.json_utils import atomic_json_dump
from src.roles import is_full, okur_turu
from src.sinav_tarihi import katla

SESSIZ_BAS = time(22, 0)
SESSIZ_SON = time(7, 30)
OKUL_BASI = time(8, 0)
HATIRLATMA = {"gun_7": (7, time(18, 0)), "gun_2": (2, time(18, 0)), "aksam": (1, time(19, 0))}
DEFTER = PurePosixPath("output/bildirim_defteri.jsonl")
DURUM = PurePosixPath("output/sinav_uyari_durumu.json")
BASLIK_SINIRI = 80
GOVDE_SINIRI = 300
GUN_ADLARI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
AY_ADLARI = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim",
             "Kasım", "Aralık"]


def _sessiz(an: datetime) -> bool:
    return an.time() >= SESSIZ_BAS or an.time() < SESSIZ_SON


def _baslangic(s: dict) -> datetime | None:
    if not s.get("tarih"):
        return None
    saat = time.fromisoformat(s["saat"]) if s.get("saat") else OKUL_BASI
    return datetime.combine(date.fromisoformat(s["tarih"]), saat)


def _yerel(deger: Any) -> datetime | None:
    try:
        an = datetime.fromisoformat(str(deger))
    except (TypeError, ValueError):
        return None
    return an.replace(tzinfo=None)


def vadesi_gelen_turler(sinav: dict, simdi: datetime, sessiz_saat: bool = True) -> list[str]:
    if sinav.get("sentetik"):
        return []
    bas = _baslangic(sinav)
    if bas is not None and simdi >= bas:
        return []
    if bas is None and sinav.get("hafta") and date.fromisoformat(sinav["hafta"]) + timedelta(days=6) < simdi.date():
        return []
    if sessiz_saat and _sessiz(simdi):
        return []
    turler = ["tespit"]
    if bas is None:
        return turler
    ilk = _yerel(sinav.get("ilk_tespit"))
    for tur, (gun, saat) in HATIRLATMA.items():
        hedef = datetime.combine(bas.date() - timedelta(days=gun), saat)
        if hedef <= simdi and (ilk is None or hedef >= ilk):
            turler.append(tur)
    return turler


@dataclass(frozen=True)
class Bildirim:
    email: str
    sinav: dict
    turler: tuple[str, ...]


def planla(sinavlar: list[dict], alicilar: list[str], gonderilmis: set[tuple], simdi: datetime) -> list[Bildirim]:
    plan = []
    for s in sinavlar:
        vadeli = vadesi_gelen_turler(s, simdi)
        for email in alicilar:
            yeni = tuple(t for t in vadeli if (email, s["id"], t, s["icerik_surumu"]) not in gonderilmis)
            if yeni:
                plan.append(Bildirim(email, s, yeni))
    return plan


def _kirp(metin: str, sinir: int) -> str:
    metin = " ".join(metin.split())
    return metin if len(metin) <= sinir else metin[: sinir - 1].rstrip() + "…"


def gun_ifadesi(hedef: date, bugun: date) -> str:
    fark = (hedef - bugun).days
    if fark == 0:
        return "Bugün"
    if fark == 1:
        return "Yarın"
    if 1 < fark < 7:
        return GUN_ADLARI[hedef.weekday()]
    return f"{hedef.day} {AY_ADLARI[hedef.month - 1]} {GUN_ADLARI[hedef.weekday()]}"


def kisa_ad(sinav: dict) -> str:
    ders, baslik = str(sinav.get("ders") or ""), str(sinav.get("baslik") or "Sınav")
    ad = baslik if ders == "Genel" or katla(baslik).startswith(katla(ders)) else f"{ders} {baslik}"
    return _kirp(ad, 50)


def _konu_ozeti(konular: list[str]) -> str:
    ilk = [_kirp(k, 60) for k in konular[:3]]
    return ", ".join(ilk) + (" …" if len(konular) > 3 else "")


def metin_kur(sinav: dict, okur: str, turler: tuple[str, ...], simdi: datetime) -> tuple[str, str]:
    ad = kisa_ad(sinav)
    konu = _konu_ozeti(list(sinav.get("konular") or []))
    sinav_sozu = "" if "sinav" in katla(ad) else " sınavı"
    if not sinav.get("tarih"):
        hafta = sinav.get("hafta")
        zaman = (f"{date.fromisoformat(hafta).day} {AY_ADLARI[date.fromisoformat(hafta).month - 1]} haftası"
                 if hafta else "tarihi belli değil")
        baslik = f"Yeni sınav: {ad}"
        if okur == "ogrenci":
            govde = f"{ad} duyuruldu ({zaman})" + (f" — {konu}" if konu else "") + ". Ayrıntı TEDY'de."
        else:
            govde = f"Işık'ın {ad}{sinav_sozu} duyuruldu ({zaman})." + (f" Konular: {konu}" if konu else "")
        return _kirp(baslik, BASLIK_SINIRI), _kirp(govde, GOVDE_SINIRI)

    gun = gun_ifadesi(date.fromisoformat(sinav["tarih"]), simdi.date())
    degisti = "tespit" in turler and bool(sinav.get("degisti"))
    baslik = f"{'Sınav güncellendi' if degisti else 'Sınav'}: {ad} · {gun}"
    if okur == "ogrenci":
        if gun == "Bugün":
            son = "Başarılar!"
        elif "aksam" in turler:
            son = "Çantanı hazırla, erken uyu."
        else:
            son = "Bugün 10 dakikayla başla?"
        govde = f"{gun} {ad} var" + (f" — {konu}" if konu else "") + f". {son}"
        if konu.endswith("…"):
            govde = f"{gun} {ad} var — {konu} {son}"
    else:
        gun_sozu = gun.lower() if gun in ("Bugün", "Yarın") else gun
        govde = f"Işık'ın {gun_sozu} {ad}{sinav_sozu} var." + (f" Konular: {konu}" if konu else "")
    return _kirp(baslik, BASLIK_SINIRI), _kirp(govde, GOVDE_SINIRI)


class BildirimDefteri:
    def __init__(self, yol: str | Path):
        self.yol = Path(yol)

    @contextmanager
    def _kilitli(self) -> Iterator[None]:
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        with open(self.yol.with_name(self.yol.name + ".lock"), "a") as kilit:
            fcntl.flock(kilit, fcntl.LOCK_EX)
            yield

    def anahtarlar(self) -> set[tuple[str, str, str, str]]:
        sonuc = set()
        try:
            satirlar = self.yol.read_text(encoding="utf-8").splitlines()
        except OSError:
            return sonuc
        for satir in satirlar:
            try:
                k = json.loads(satir)
                sonuc.add((k["email"], k["sinav_id"], k["tur"], k["icerik_surumu"]))
            except (ValueError, KeyError, TypeError):
                continue
        return sonuc

    def yaz(self, email: str, sinav: dict, turler: tuple[str, ...], simdi: datetime) -> None:
        with self._kilitli(), self.yol.open("a", encoding="utf-8") as f:
            for tur in turler:
                f.write(json.dumps({"zaman": simdi.isoformat(timespec="seconds"), "email": email,
                                    "sinav_id": sinav["id"], "tur": tur,
                                    "icerik_surumu": sinav["icerik_surumu"]}, ensure_ascii=False) + "\n")


def _alicilar(depo: web_push.AbonelikDeposu) -> list[str]:
    return sorted(e for e in depo.hepsi() if is_full(e))


def _durum_yaz(kok: Path, durum: dict) -> dict:
    atomic_json_dump(durum, str(kok / DURUM))
    return durum


def gonder_turu(kok: Path, simdi: datetime, gonderici: Callable[..., web_push.GonderimSonucu] | None = None) -> dict:
    kok = Path(kok)
    durum = {"son_tur": simdi.isoformat(timespec="seconds"), "kapali": False, "gonderilen": 0,
             "olu_silinen": 0, "hatalar": [], "abone_kisi": 0}
    if os.environ.get("TEDY_SINAV_UYARI", "0") != "1":
        return _durum_yaz(kok, {**durum, "kapali": True})
    belge = sinav_tespiti.oku(kok)
    vapid = web_push.vapid_ayarlari()
    if belge is None or vapid is None:
        return _durum_yaz(kok, {**durum, "hatalar": ["sinavlar.json yok" if belge is None else "VAPID ayarlı değil"]})
    gonderici = gonderici or web_push.gonder
    depo = web_push.AbonelikDeposu(kok / web_push.ABONELIKLER)
    defter = BildirimDefteri(kok / DEFTER)
    alicilar = _alicilar(depo)
    durum["abone_kisi"] = len(alicilar)
    for b in planla(belge["sinavlar"], alicilar, defter.anahtarlar(), simdi):
        baslik, govde = metin_kur(b.sinav, okur_turu(b.email), b.turler, simdi)
        yuk = {"baslik": baslik, "govde": govde, "etiket": b.sinav["id"], "url": f"/sinavlar?sinav={b.sinav['id']}"}
        basarili = False
        for cihaz in depo.kisinin(b.email):
            sonuc = gonderici(cihaz["abonelik"], yuk, vapid)
            if sonuc.durum == "ok":
                basarili = True
            elif sonuc.durum == "olu":
                durum["olu_silinen"] += depo.endpoint_sil(cihaz["abonelik"]["endpoint"])
            else:
                durum["hatalar"].append(f"{sonuc.kod}: {sonuc.mesaj}"[:160])
        if basarili:
            defter.yaz(b.email, b.sinav, b.turler, simdi)
            durum["gonderilen"] += 1
    durum["hatalar"] = durum["hatalar"][:5]
    return _durum_yaz(kok, durum)


def _tohum(kok: Path, emails: list[str], simdi: datetime) -> int:
    belge = sinav_tespiti.oku(Path(kok))
    if belge is None:
        return 0
    defter = BildirimDefteri(Path(kok) / DEFTER)
    eski = defter.anahtarlar()
    sayi = 0
    for s in belge["sinavlar"]:
        vadeli = vadesi_gelen_turler(s, simdi, sessiz_saat=False)
        for email in emails:
            yeni = tuple(t for t in vadeli if (email, s["id"], t, s["icerik_surumu"]) not in eski)
            if yeni:
                defter.yaz(email, s, yeni, simdi)
                sayi += len(yeni)
    return sayi


def kisiyi_tohumla(kok: Path, email: str, simdi: datetime) -> int:
    """A person's first device: mark what is already due as sent."""
    return _tohum(Path(kok), [email], simdi)


def tohumla(kok: Path, simdi: datetime) -> int:
    """Rollout: mark everything already due for every subscriber as sent."""
    depo = web_push.AbonelikDeposu(Path(kok) / web_push.ABONELIKLER)
    return _tohum(Path(kok), _alicilar(depo), simdi)


def main(argv: list[str] | None = None) -> int:
    from src.env_loader import load_env
    load_env()
    kok = Path(__file__).resolve().parents[1]
    komut = (argv if argv is not None else sys.argv[1:])[:1]
    if komut == ["gonder"]:
        durum = gonder_turu(kok, datetime.now())
        print(json.dumps(durum, ensure_ascii=False))
        return 0
    if komut == ["tohumla"]:
        print(f"tohumlanan uyarı: {tohumla(kok, datetime.now())}")
        return 0
    print("kullanım: python -m src.sinav_uyari gonder|tohumla", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Adım 4: Testlerin geçtiğini gör**

Run: `unshare -rn .venv/bin/python -m pytest -q tests/test_sinav_uyari.py tests/test_bildirim_api.py`
Expected: PASS. `test_metin_isik_ve_aile`'deki gövde: konu özeti "…" ile bittiğinde `". "` yerine boşluk konur (çift noktalama olmaz); bu dalı `metin_kur` kapsıyor. `test_uzun_konular_yuk_siniri`'nde başlık 80'de, her konu 60'ta kesilir; gövde 300'ü geçerse orada da "…" ile kesilir.

- [ ] **Adım 5: Unit dosyalarını yaz** — repo kökünde

`tedy-sinav-uyari.service`:

```ini
[Unit]
Description=TEDY sınav uyarıları (web push turu)
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/mnt/thunderbolt/workspaces/TED
Environment=PATH=/mnt/thunderbolt/workspaces/TED/.venv/bin:/usr/bin:/bin
# Istanbul time, not the host's UTC: see src/env_loader.py. Before any
# EnvironmentFile line, which would override it if .env ever set TZ.
Environment=TZ=Europe/Istanbul
EnvironmentFile=/mnt/thunderbolt/workspaces/TED/.env
ExecStart=/mnt/thunderbolt/workspaces/TED/.venv/bin/python -m src.sinav_uyari gonder
TimeoutStartSec=120
```

`tedy-sinav-uyari.timer`:

```ini
[Unit]
Description=TEDY sınav uyarıları — 10 dakikada bir

[Timer]
OnCalendar=*:0/10
Persistent=true
RandomizedDelaySec=30

[Install]
WantedBy=timers.target
```

Doğrula (kurmadan): `systemd-analyze --user verify ./tedy-sinav-uyari.service ./tedy-sinav-uyari.timer` → çıktı yok ya da yalnız "WorkingDirectory" uyarısı (canlı yol bu worktree değil, beklenir).

- [ ] **Adım 6: Commit**

```bash
git add src/sinav_uyari.py tests/test_sinav_uyari.py tedy-sinav-uyari.service tedy-sinav-uyari.timer
git commit -m "feat(sinav): uyarı zamanlaması, hitaplı metin, gönderim defteri ve zamanlayıcı unit'leri

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Görev 9: PWA — servis çalışanı, manifest, ikonlar, bildirim yardımcıları ve "Sınav uyarıları" kartı

**Files:**
- Create: `dashboard/public/sw.js`, `dashboard/public/manifest.webmanifest`, `dashboard/public/tedy-192.png`, `dashboard/public/tedy-512.png`
- Modify: `dashboard/index.html`
- Create: `dashboard/src/utils/bildirim.ts`, `dashboard/src/components/SinavUyarilari.tsx`, `dashboard/src/components/SinavUyarilari.scss`
- Modify: `dashboard/src/components/ExamTimeline.tsx` (kartı en üste koy), `dashboard/src/components/DahaFazla.tsx` (bağlantı)
- Test: `dashboard/tests/bildirim.test.ts`, `dashboard/tests/e2e/sinav-uyari.spec.ts` (ilk bölüm)

**Interfaces:**
- Consumes: Görev 7 uçları (`/api/bildirim/anahtar` → `{anahtar, acik}`, `/api/bildirim/abonelik` POST/DELETE, `/api/bildirim/deneme`)
- Produces:
  - `bildirim.ts`: `type BildirimDurumu = 'acik' | 'kapali' | 'reddedildi' | 'desteklenmiyor' | 'ios-ana-ekran'`; `interface BildirimOrtami { destek: boolean; izin: 'default' | 'granted' | 'denied'; abone: boolean; ios: boolean; ekranda: boolean }`; `bildirimDurumu(o): BildirimDurumu`; `DURUM_METNI: Record<BildirimDurumu, string>`; `anahtarBaytlari(b64url: string): Uint8Array`; `cihazAdi(ua: string): string`; `ortamiOku(): Promise<BildirimOrtami>`; `bildirimiAc(): Promise<void>`; `bildirimiKapat(): Promise<void>`; `denemeGonder(): Promise<number>`; `class BildirimHatasi extends Error { kod: string }`
  - `SinavUyarilari` (default export), kök `<section id="uyarilar" className="sinav-uyarilari" aria-labelledby="sinav-uyarilari-baslik">`

- [ ] **Adım 1: Başarısız birim testini yaz** — `dashboard/tests/bildirim.test.ts`

```ts
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { anahtarBaytlari, bildirimDurumu, cihazAdi, DURUM_METNI } from '../src/utils/bildirim.ts'
import type { BildirimOrtami } from '../src/utils/bildirim.ts'

const TAM: BildirimOrtami = { destek: true, izin: 'granted', abone: true, ios: false, ekranda: false }

test('açık: izin verilmiş ve abone', () => {
  assert.equal(bildirimDurumu(TAM), 'acik')
})

test('kapalı: izin var ama abonelik yok ya da izin sorulmamış', () => {
  assert.equal(bildirimDurumu({ ...TAM, abone: false }), 'kapali')
  assert.equal(bildirimDurumu({ ...TAM, izin: 'default', abone: false }), 'kapali')
})

test('reddedildi', () => {
  assert.equal(bildirimDurumu({ ...TAM, izin: 'denied', abone: false }), 'reddedildi')
})

test('desteklenmiyor', () => {
  assert.equal(bildirimDurumu({ ...TAM, destek: false }), 'desteklenmiyor')
})

test('iPhone ana ekrana eklenmemiş: destek olmasa da önce bu söylenir', () => {
  assert.equal(bildirimDurumu({ ...TAM, destek: false, ios: true, ekranda: false }), 'ios-ana-ekran')
  assert.equal(bildirimDurumu({ ...TAM, ios: true, ekranda: true }), 'acik')
})

test('her durumun metni var ve renk değil sözcük taşır', () => {
  for (const d of ['acik', 'kapali', 'reddedildi', 'desteklenmiyor', 'ios-ana-ekran'] as const) {
    assert.ok(DURUM_METNI[d].length > 10)
  }
  assert.match(DURUM_METNI['ios-ana-ekran'], /Ana Ekrana Ekle/)
  assert.match(DURUM_METNI.reddedildi, /tarayıcı ayarlarından/i)
})

test('anahtar baytları: base64url → 65 bayt', () => {
  const b64 = Buffer.from(Uint8Array.from([4, ...Array(64).fill(7)])).toString('base64url')
  const sonuc = anahtarBaytlari(b64)
  assert.equal(sonuc.length, 65)
  assert.equal(sonuc[0], 4)
  assert.equal(sonuc[64], 7)
})

test('cihaz adı kullanıcı aracısından', () => {
  assert.equal(cihazAdi('Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X)'), 'iPhone')
  assert.equal(cihazAdi('Mozilla/5.0 (Linux; Android 14; Pixel 8)'), 'Android')
  assert.equal(cihazAdi('Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4)'), 'Mac')
  assert.equal(cihazAdi('Mozilla/5.0 (Windows NT 10.0; Win64; x64)'), 'Windows')
  assert.equal(cihazAdi('curl/8'), 'Tarayıcı')
})
```

- [ ] **Adım 2: Testin başarısız olduğunu gör**

Run: `cd dashboard && node --test tests/bildirim.test.ts`
Expected: FAIL — `Cannot find module '…/src/utils/bildirim.ts'`

- [ ] **Adım 3: `dashboard/src/utils/bildirim.ts`'i yaz**

```ts
// Sınav uyarıları: bu cihazda web push aç/kapat (spec 2026-10-16 §7, §8).
// Saf kısım (durum, metin, anahtar çözme, cihaz adı) node:test ile; tarayıcı
// akışları e2e ile sınanır. Servis çalışanı yalnız bildirim içindir.

export type BildirimDurumu = 'acik' | 'kapali' | 'reddedildi' | 'desteklenmiyor' | 'ios-ana-ekran'

export interface BildirimOrtami {
  destek: boolean
  izin: 'default' | 'granted' | 'denied'
  abone: boolean
  ios: boolean
  ekranda: boolean
}

export class BildirimHatasi extends Error {
  kod: string
  constructor(kod: string, mesaj: string) {
    super(mesaj)
    this.kod = kod
  }
}

export const DURUM_METNI: Record<BildirimDurumu, string> = {
  acik: 'Bu cihazda açık. Sınav duyurulunca ve yaklaşınca bildirim gelir.',
  kapali: 'Bu cihazda kapalı.',
  reddedildi: 'Bildirim izni reddedilmiş. Tarayıcı ayarlarından bu siteye bildirim izni verilmeli.',
  desteklenmiyor: 'Bu tarayıcı bildirim desteklemiyor.',
  'ios-ana-ekran': "iPhone'da bildirim için TEDY ana ekrana eklenmeli: Paylaş → Ana Ekrana Ekle, sonra oradan açılır.",
}

export function bildirimDurumu(o: BildirimOrtami): BildirimDurumu {
  if (o.ios && !o.ekranda) return 'ios-ana-ekran'
  if (!o.destek) return 'desteklenmiyor'
  if (o.izin === 'denied') return 'reddedildi'
  return o.izin === 'granted' && o.abone ? 'acik' : 'kapali'
}

export function anahtarBaytlari(b64url: string): Uint8Array {
  const b64 = (b64url + '='.repeat((4 - (b64url.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/')
  const ham = atob(b64)
  return Uint8Array.from(ham, c => c.charCodeAt(0))
}

export function cihazAdi(ua: string): string {
  if (/iPhone|iPad|iPod/.test(ua)) return 'iPhone'
  if (/Android/.test(ua)) return 'Android'
  if (/Macintosh/.test(ua)) return 'Mac'
  if (/Windows/.test(ua)) return 'Windows'
  return 'Tarayıcı'
}

function iosMu(): boolean {
  return /iPhone|iPad|iPod/.test(navigator.userAgent)
    || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}

function ekrandaMi(): boolean {
  return window.matchMedia?.('(display-mode: standalone)').matches
    || (navigator as Navigator & { standalone?: boolean }).standalone === true
}

function destekVar(): boolean {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}

async function mevcutAbonelik(): Promise<PushSubscription | null> {
  if (!destekVar()) return null
  const kayit = await navigator.serviceWorker.getRegistration('/')
  return kayit ? kayit.pushManager.getSubscription() : null
}

export async function ortamiOku(): Promise<BildirimOrtami> {
  const destek = destekVar()
  return {
    destek,
    izin: destek ? Notification.permission : 'default',
    abone: destek ? (await mevcutAbonelik()) !== null : false,
    ios: iosMu(),
    ekranda: ekrandaMi(),
  }
}

export async function bildirimiAc(): Promise<void> {
  const izin = await Notification.requestPermission()
  if (izin !== 'granted') throw new BildirimHatasi(izin === 'denied' ? 'reddedildi' : 'kapali', 'İzin verilmedi')
  const kayit = await navigator.serviceWorker.register('/sw.js')
  await navigator.serviceWorker.ready
  const yanit = await fetch('/api/bildirim/anahtar', { credentials: 'include' })
  const { anahtar } = (await yanit.json()) as { anahtar: string | null }
  if (!yanit.ok || !anahtar) throw new BildirimHatasi('sunucu', 'Bildirim anahtarı alınamadı')
  const abonelik = await kayit.pushManager.subscribe({
    userVisibleOnly: true, applicationServerKey: anahtarBaytlari(anahtar),
  })
  const kayitYaniti = await fetch('/api/bildirim/abonelik', {
    method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...abonelik.toJSON(), cihaz: cihazAdi(navigator.userAgent) }),
  })
  if (!kayitYaniti.ok) {
    await abonelik.unsubscribe()
    throw new BildirimHatasi('sunucu', 'Abonelik kaydedilemedi')
  }
}

export async function bildirimiKapat(): Promise<void> {
  const abonelik = await mevcutAbonelik()
  if (!abonelik) return
  await fetch('/api/bildirim/abonelik', {
    method: 'DELETE', credentials: 'include', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ endpoint: abonelik.endpoint }),
  })
  await abonelik.unsubscribe()
}

export async function denemeGonder(): Promise<number> {
  const yanit = await fetch('/api/bildirim/deneme', { method: 'POST', credentials: 'include' })
  if (!yanit.ok) throw new BildirimHatasi('sunucu', 'Deneme bildirimi gönderilemedi')
  return ((await yanit.json()) as { gonderilen: number }).gonderilen
}
```

- [ ] **Adım 4: Birim testinin geçtiğini gör**

Run: `cd dashboard && node --test tests/bildirim.test.ts`
Expected: PASS (8 test)

- [ ] **Adım 5: Servis çalışanı, manifest, ikonlar**

`dashboard/public/sw.js`:

```js
// TEDY servis çalışanı — yalnız bildirim (spec 2026-10-16 §7). Çevrimdışı
// önbellek yapmaz: fetch olayı dinlenmez, sayfa ağdan gelir.
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()))

self.addEventListener('push', event => {
  let veri = {}
  try {
    veri = event.data ? event.data.json() : {}
  } catch {
    veri = { govde: event.data ? event.data.text() : '' }
  }
  event.waitUntil(self.registration.showNotification(veri.baslik || 'TEDY', {
    body: veri.govde || '',
    tag: veri.etiket || 'tedy',
    renotify: true,
    icon: '/tedy-192.png',
    badge: '/tedy-192.png',
    data: { url: veri.url || '/sinavlar' },
  }))
})

self.addEventListener('notificationclick', event => {
  event.notification.close()
  const hedef = new URL((event.notification.data && event.notification.data.url) || '/sinavlar',
    self.location.origin).href
  event.waitUntil((async () => {
    const pencereler = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
    for (const p of pencereler) {
      if (new URL(p.url).origin === self.location.origin && 'focus' in p) {
        await p.focus()
        if ('navigate' in p) await p.navigate(hedef)
        return
      }
    }
    await self.clients.openWindow(hedef)
  })())
})
```

`dashboard/public/manifest.webmanifest`:

```json
{
  "name": "TEDY",
  "short_name": "TEDY",
  "lang": "tr",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#0f2a4a",
  "icons": [
    { "src": "/tedy-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any" },
    { "src": "/tedy-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any" }
  ]
}
```

`theme_color`'ı `dashboard/src/theme/ted-theme.scss`'teki marka lacivertinin hex'iyle (`grep -n "brand\|navy\|lacivert" dashboard/src/theme/ted-theme.scss | head`) eşle; değer farklıysa onu kullan.

İkonlar:

```bash
cd dashboard/public
rsvg-convert -w 192 -h 192 tedy-icon.svg -o tedy-192.png
rsvg-convert -w 512 -h 512 tedy-icon.svg -o tedy-512.png
file tedy-192.png tedy-512.png   # beklenen: PNG image data, 192 x 192 / 512 x 512
```

`dashboard/index.html` `<head>`'e, `apple-touch-icon` satırından sonra:

```html
    <link rel="manifest" href="/manifest.webmanifest" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-title" content="TEDY" />
```

- [ ] **Adım 6: Kartı yaz** — `dashboard/src/components/SinavUyarilari.tsx`

```tsx
import { useCallback, useEffect, useState } from 'react'
import { Button, InlineNotification } from '@carbon/react'
import {
  bildirimDurumu, bildirimiAc, bildirimiKapat, BildirimHatasi, denemeGonder, DURUM_METNI, ortamiOku,
} from '../utils/bildirim'
import type { BildirimDurumu } from '../utils/bildirim'
import './SinavUyarilari.scss'

// "Sınav uyarıları" (spec §8): bu cihazda aç/kapat, deneme, durum. Durum metinle
// söylenir; renk tek başına anlam taşımaz.
export default function SinavUyarilari() {
  const [durum, setDurum] = useState<BildirimDurumu | null>(null)
  const [mesgul, setMesgul] = useState(false)
  const [bilgi, setBilgi] = useState<{ tur: 'success' | 'error'; metin: string } | null>(null)

  const yenile = useCallback(async () => setDurum(bildirimDurumu(await ortamiOku())), [])
  useEffect(() => { void yenile() }, [yenile])

  const yap = async (is: () => Promise<string | void>) => {
    setMesgul(true)
    setBilgi(null)
    try {
      const metin = await is()
      if (metin) setBilgi({ tur: 'success', metin })
    } catch (e) {
      const kod = e instanceof BildirimHatasi ? e.kod : ''
      setBilgi({ tur: 'error', metin: kod === 'reddedildi' ? DURUM_METNI.reddedildi : 'İşlem tamamlanamadı; biraz sonra yeniden denenebilir.' })
    } finally {
      await yenile()
      setMesgul(false)
    }
  }

  return (
    <section id="uyarilar" className="sinav-uyarilari" aria-labelledby="sinav-uyarilari-baslik">
      <h2 id="sinav-uyarilari-baslik" className="sinav-uyarilari__baslik">Sınav uyarıları</h2>
      <p className="sinav-uyarilari__durum" aria-live="polite">{durum ? DURUM_METNI[durum] : 'Denetleniyor…'}</p>
      <div className="sinav-uyarilari__dugmeler">
        {durum === 'kapali' && (
          <Button size="sm" kind="primary" disabled={mesgul} onClick={() => yap(async () => { await bildirimiAc() })}>
            Bu cihazda aç
          </Button>
        )}
        {durum === 'acik' && (
          <>
            <Button size="sm" kind="tertiary" disabled={mesgul}
              onClick={() => yap(async () => `Deneme bildirimi ${await denemeGonder()} cihaza gönderildi.`)}>
              Deneme bildirimi gönder
            </Button>
            <Button size="sm" kind="ghost" disabled={mesgul} onClick={() => yap(async () => { await bildirimiKapat() })}>
              Bu cihazda kapat
            </Button>
          </>
        )}
      </div>
      {bilgi && (
        <InlineNotification lowContrast hideCloseButton kind={bilgi.tur} title={bilgi.metin}
          className="sinav-uyarilari__bilgi" />
      )}
    </section>
  )
}
```

`dashboard/src/components/SinavUyarilari.scss`:

```scss
@use '@carbon/react/scss/spacing' as spacing;
@use '@carbon/react/scss/type' as type;

.sinav-uyarilari {
  margin-block-end: spacing.$spacing-07;
  padding: spacing.$spacing-05;
  border: 1px solid var(--cds-border-subtle);
  border-radius: var(--ted-radius-card);
  background: var(--cds-layer);

  &__baslik {
    @include type.type-style('heading-compact-02');
    margin: 0 0 spacing.$spacing-03;
  }

  &__durum {
    @include type.type-style('body-compact-01');
    margin: 0 0 spacing.$spacing-04;
    color: var(--cds-text-secondary);
  }

  &__dugmeler {
    display: flex;
    flex-wrap: wrap;
    gap: spacing.$spacing-03;
  }

  &__bilgi {
    margin-block-start: spacing.$spacing-04;
  }
}
```

(Projede `@use` yolları farklıysa — `grep -rn "@use '@carbon" dashboard/src/components/*.scss | head -3` — mevcut kalıbı kullan.)

`ExamTimeline.tsx`: `import SinavUyarilari from './SinavUyarilari'`; hem boş durumda hem dolu durumda en üste `<SinavUyarilari />` koy (boş liste dalı `<><SinavUyarilari /><EmptyLine>…</EmptyLine></>` olur).

`DahaFazla.tsx`: liste `</ul>`'den önce, route öğelerinden sonra (yalnız tam rol — `user.role === 'full'`):

```tsx
        {user.role === 'full' && (
          <li>
            <Link to="/sinavlar#uyarilar" className="daha-fazla__oge">
              <Notification aria-hidden="true" />
              <span>Sınav uyarıları</span>
            </Link>
          </li>
        )}
```

(`import { Notification } from '@carbon/icons-react'`; `useAuth`'taki rol değerinin adı `grep -n "role" dashboard/src/hooks/useAuth.ts | head` ile doğrulanır.) `ExamTimeline` hash'e kaydırmayı Görev 10'da `?sinav=` ile birlikte ekler.

- [ ] **Adım 7: e2e testini yaz** — `dashboard/tests/e2e/sinav-uyari.spec.ts` (ilk bölüm; Görev 10 aynı dosyaya ekler)

```ts
import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { mock, LIVE } from './_audit-fixtures'

// Sınav uyarıları kartı: tarayıcının bildirim API'leri taklit edilir; sunucu
// uçları route ile karşılanır. Gerçek push servisine gidilmez.

type Taklit = { izin: 'default' | 'granted' | 'denied'; abone: boolean; destek?: boolean; ios?: boolean }

async function bildirimTaklidi(page: Page, t: Taklit) {
  await page.addInitScript((t: Taklit) => {
    const w = window as unknown as Record<string, unknown>
    if (t.ios) Object.defineProperty(navigator, 'userAgent', { value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X)' })
    if (t.destek === false) { delete w.PushManager; return }
    let abone = t.abone
    const abonelik = {
      endpoint: 'https://fcm.googleapis.com/fcm/send/test',
      toJSON: () => ({ endpoint: 'https://fcm.googleapis.com/fcm/send/test', keys: { p256dh: 'p', auth: 'a' } }),
      unsubscribe: async () => { abone = false; return true },
    }
    const pushManager = {
      getSubscription: async () => (abone ? abonelik : null),
      subscribe: async () => { abone = true; return abonelik },
    }
    const kayit = { pushManager }
    Object.defineProperty(navigator, 'serviceWorker', { value: {
      getRegistration: async () => kayit, register: async () => kayit, ready: Promise.resolve(kayit),
    } })
    w.PushManager = function PushManager() {}
    let izin = t.izin
    w.Notification = { get permission() { return izin }, requestPermission: async () => { izin = 'granted'; return izin } }
  }, t)
}

async function sinavlarAc(page: Page, t: Taklit) {
  await bildirimTaklidi(page, t)
  await mock(page, { ...LIVE, 'bildirim/anahtar': { anahtar: 'BAAA', acik: true } })
  await page.route('**/api/bildirim/abonelik', r => r.fulfill({ status: 201, json: { ok: true } }))
  await page.route('**/api/bildirim/deneme', r => r.fulfill({ json: { gonderilen: 1 } }))
  await page.goto('/sinavlar')
  await page.locator('#uyarilar').waitFor()
}

test.describe('Sınav uyarıları kartı', () => {
  test('kapalıdan açığa, deneme ve kapatma', async ({ page }) => {
    await sinavlarAc(page, { izin: 'default', abone: false })
    const kart = page.locator('#uyarilar')
    await expect(kart.getByText('Bu cihazda kapalı.', { exact: true })).toBeVisible()
    const kayit = page.waitForRequest(r => r.url().endsWith('/api/bildirim/abonelik') && r.method() === 'POST')
    await kart.getByRole('button', { name: 'Bu cihazda aç' }).click()
    const govde = (await kayit).postDataJSON()
    expect(govde.endpoint).toBe('https://fcm.googleapis.com/fcm/send/test')
    expect(govde.cihaz).toBeTruthy()
    await expect(kart.getByText(/^Bu cihazda açık\./)).toBeVisible()
    await kart.getByRole('button', { name: 'Deneme bildirimi gönder' }).click()
    await expect(kart.getByText('Deneme bildirimi 1 cihaza gönderildi.')).toBeVisible()
    await kart.getByRole('button', { name: 'Bu cihazda kapat' }).click()
    await expect(kart.getByText('Bu cihazda kapalı.', { exact: true })).toBeVisible()
  })

  test('izin reddedilmiş', async ({ page }) => {
    await sinavlarAc(page, { izin: 'denied', abone: false })
    await expect(page.locator('#uyarilar')).toContainText('Tarayıcı ayarlarından')
    await expect(page.locator('#uyarilar').getByRole('button')).toHaveCount(0)
  })

  test('desteklenmiyor', async ({ page }) => {
    await sinavlarAc(page, { izin: 'default', abone: false, destek: false })
    await expect(page.locator('#uyarilar')).toContainText('Bu tarayıcı bildirim desteklemiyor.')
  })

  test('iPhone ana ekrana eklenmemiş', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await sinavlarAc(page, { izin: 'default', abone: false, ios: true })
    await expect(page.locator('#uyarilar')).toContainText('Paylaş → Ana Ekrana Ekle')
  })

  test('axe: kart ihlalsiz', async ({ page }) => {
    await sinavlarAc(page, { izin: 'default', abone: false })
    const sonuc = await new AxeBuilder({ page }).include('#uyarilar')
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa', 'best-practice']).analyze()
    expect(sonuc.violations).toEqual([])
  })

  test('manifest ve servis çalışanı sunuluyor', async ({ request }) => {
    const manifest = await request.get('/manifest.webmanifest')
    expect(manifest.ok()).toBeTruthy()
    expect((await manifest.json()).icons).toHaveLength(2)
    const sw = await request.get('/sw.js')
    expect(sw.ok()).toBeTruthy()
    expect(await sw.text()).toContain("addEventListener('push'")
    expect((await request.get('/tedy-192.png')).ok()).toBeTruthy()
  })
})
```

- [ ] **Adım 8: e2e'nin geçtiğini gör**

Run: `cd dashboard && npm run build:carbon-ai > /tmp/sinav-build.log 2>&1 && TEDY_E2E_PORT=8391 env -u ANTHROPIC_API_KEY npx playwright test sinav-uyari --retries=0 --reporter=list`
Expected: 6 passed. (`mock` `/api/bildirim/anahtar`'ı `bildirim/anahtar` anahtarıyla karşılar.)
Run: `cd dashboard && npm run lint && npx tsc -b --noEmit && npm run test:birim`
Expected: hata yok; birim testleri yeşil.

- [ ] **Adım 9: Commit**

```bash
git add dashboard/public/sw.js dashboard/public/manifest.webmanifest dashboard/public/tedy-192.png dashboard/public/tedy-512.png dashboard/index.html dashboard/src/utils/bildirim.ts dashboard/src/components/SinavUyarilari.tsx dashboard/src/components/SinavUyarilari.scss dashboard/src/components/ExamTimeline.tsx dashboard/src/components/DahaFazla.tsx dashboard/tests/bildirim.test.ts dashboard/tests/e2e/sinav-uyari.spec.ts
git commit -m "feat(pano): PWA servis çalışanı ve Sınav uyarıları kartı

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Görev 10: Pano — Bugün önizlemesi, İşler etiketleri, sınav ayrıntısı, `?sinav=` ve `?hafta=`

**Files:**
- Create: `dashboard/src/utils/sinav.ts`, `dashboard/src/components/SinavKarti.tsx`, `dashboard/src/components/SinavKarti.scss`
- Modify: `dashboard/src/components/TodaySchedule.tsx:535-545,686-705`, `HomeworkTracker.tsx:202-210,320-360`, `ExamTimeline.tsx`, `CourseContent.tsx:139`
- Test: `dashboard/tests/sinav.test.ts`, `dashboard/tests/e2e/sinav-uyari.spec.ts` (ikinci bölüm)

**Interfaces:**
- Consumes: Görev 6 `ExamItem` yeni alanları, `ExamsApiResponse.tespit`; `utils/formatters.kisaTeslim(d: Date, now: Date)`, `MONTHS_SHORT`
- Produces:
  - `sinav.ts`: `sinavEtiketi(e: ExamItem, nowMs: number): 'Yeni' | 'Değişti' | null`; `enYakinSinav(exams: ExamItem[], nowMs: number, haric: Set<string>): ExamItem | null`; `konuOzeti(konular: string[] | undefined, n?: number): string`; `zamanMetni(e: ExamItem): string`
  - `SinavKarti.tsx`: `SinavOnizleme({ exam, now, onAc })`, `SinavEtiketi({ exam, nowMs })`, `SinavAyrintisi({ exam })`

- [ ] **Adım 1: Başarısız birim testini yaz** — `dashboard/tests/sinav.test.ts`

```ts
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { enYakinSinav, konuOzeti, sinavEtiketi, zamanMetni } from '../src/utils/sinav.ts'
import type { ExamItem } from '../src/types.ts'

const SIMDI = new Date('2026-10-16T10:00:00').getTime()
const s = (kw: Partial<ExamItem>): ExamItem => ({
  id: 'x', course: 'Matematik', title: 'Matematik KTT', rawTitle: 'Matematik KTT', courseColor: '#000',
  examNumber: null, date: '2026-10-20', endDate: null, allDay: true, status: 'upcoming', grade: null,
  relatedHomework: [], relatedContent: [], ...kw,
})

test('Yeni: son 48 saatte tespit', () => {
  assert.equal(sinavEtiketi(s({ ilkTespit: '2026-10-15T11:00:00' }), SIMDI), 'Yeni')
  assert.equal(sinavEtiketi(s({ ilkTespit: '2026-10-14T09:00:00' }), SIMDI), null)
  assert.equal(sinavEtiketi(s({ ilkTespit: null }), SIMDI), null)
})

test('Değişti Yeni’den önce gelir', () => {
  assert.equal(sinavEtiketi(s({ ilkTespit: '2026-10-15T11:00:00', degisti: '2026-10-16T09:00:00' }), SIMDI), 'Değişti')
})

test('en yakın sınav: 7 gün içinde, tarihli, hariç tutulan dışında', () => {
  const liste = [s({ id: 'a', date: '2026-10-25' }), s({ id: 'b', date: '2026-10-19T09:00:00', allDay: false }),
    s({ id: 'c', date: null, tarihBelirsiz: true }), s({ id: 'd', date: '2026-10-17', status: 'past' })]
  assert.equal(enYakinSinav(liste, SIMDI, new Set())?.id, 'b')
  assert.equal(enYakinSinav(liste, SIMDI, new Set(['b'])), null)
})

test('konu özeti ilk üç', () => {
  assert.equal(konuOzeti(['A', 'B', 'C', 'D', 'E']), 'A, B, C +2 konu')
  assert.equal(konuOzeti(['A']), 'A')
  assert.equal(konuOzeti(undefined), '')
})

test('zaman metni: gün, hafta, belirsiz', () => {
  assert.equal(zamanMetni(s({ date: '2026-10-20' })), '20 Eki')
  assert.equal(zamanMetni(s({ date: '2026-10-20T09:30:00', allDay: false })), '20 Eki 09:30')
  assert.equal(zamanMetni(s({ date: null, hafta: '2026-10-19', tarihBelirsiz: true })), '19 Eki haftası')
  assert.equal(zamanMetni(s({ date: null, tarihBelirsiz: true })), 'Tarih belirsiz')
})
```

- [ ] **Adım 2: Testin başarısız olduğunu gör**

Run: `cd dashboard && node --test tests/sinav.test.ts`
Expected: FAIL — modül yok

- [ ] **Adım 3: `dashboard/src/utils/sinav.ts`'i yaz**

```ts
import type { ExamItem } from '../types.ts'
import { MONTHS_SHORT } from './formatters.ts'

const SAAT_48 = 48 * 3600 * 1000
const GUN_7 = 7 * 24 * 3600 * 1000

function an(s?: string | null): number {
  return s ? new Date(s).getTime() : NaN
}

/** "Yeni"/"Değişti" — metinli etiket; renk tek başına anlam taşımaz (spec §8). */
export function sinavEtiketi(e: ExamItem, nowMs: number): 'Yeni' | 'Değişti' | null {
  const d = nowMs - an(e.degisti)
  if (d >= 0 && d < SAAT_48) return 'Değişti'
  const i = nowMs - an(e.ilkTespit)
  if (i >= 0 && i < SAAT_48) return 'Yeni'
  return null
}

export function enYakinSinav(exams: ExamItem[], nowMs: number, haric: Set<string>): ExamItem | null {
  const adaylar = exams
    .filter(e => e.status === 'upcoming' && e.date && !haric.has(e.id))
    .map(e => ({ e, t: an(e.date) }))
    .filter(x => !isNaN(x.t) && x.t - nowMs <= GUN_7)
    .sort((a, b) => a.t - b.t)
  return adaylar[0]?.e ?? null
}

export function konuOzeti(konular: string[] | undefined, n = 3): string {
  const liste = (konular ?? []).filter(Boolean)
  if (liste.length <= n) return liste.join(', ')
  return `${liste.slice(0, n).join(', ')} +${liste.length - n} konu`
}

export function zamanMetni(e: ExamItem): string {
  const gun = (iso: string) => {
    const [, a, g] = iso.slice(0, 10).split('-').map(Number)
    return `${g} ${MONTHS_SHORT[a - 1]}`
  }
  if (e.date) {
    const saat = !e.allDay && e.date.length >= 16 ? ` ${e.date.slice(11, 16)}` : ''
    return gun(e.date) + saat
  }
  if (e.hafta) return `${gun(e.hafta)} haftası`
  return 'Tarih belirsiz'
}
```

(`.ts` uzantılı import node:test için gerekir; `formatters.ts` ilk satırından `MONTHS_SHORT`'u dışa verir. node onu çözemezse — dosya değer olarak başka modül import ediyorsa — `MONTHS_SHORT`'u `sinav.ts`'te yerel sabit yap ve ledger'a yaz.)

- [ ] **Adım 4: Birim testinin geçtiğini gör**

Run: `cd dashboard && node --test tests/sinav.test.ts`
Expected: PASS (5 test)

- [ ] **Adım 5: Bileşenleri yaz** — `dashboard/src/components/SinavKarti.tsx`

```tsx
import { Link as CarbonLink, Tag } from '@carbon/react'
import { useNavigate } from 'react-router-dom'
import type { ExamItem } from '../types'
import { kisaTeslim } from '../utils/formatters'
import { konuOzeti, sinavEtiketi, zamanMetni } from '../utils/sinav'
import SubjectLabel from './SubjectLabel'
import './SinavKarti.scss'

/** Bugün: 7 gün içindeki en yakın sınav — sessiz, tek satırlık özet (İ1, İ6). */
export function SinavOnizleme({ exam, now, onAc }: { exam: ExamItem; now: Date; onAc: () => void }) {
  const konu = konuOzeti(exam.konular)
  const kaynak = exam.kaynaklar?.find(k => k.tur !== 'takvim')
  return (
    <section className="sinav-onizleme" aria-label="Yaklaşan sınav">
      <div className="today-also__head">
        <span className="today-also__title">YAKLAŞAN SINAV</span>
      </div>
      <button type="button" className="today-also__item" onClick={onAc}>
        <span className="today-also__name">
          <SubjectLabel course={exam.course} family={exam.courseFamily}>{exam.title || exam.rawTitle}</SubjectLabel>
        </span>
        <span className="today-also__due">{exam.date ? kisaTeslim(new Date(exam.date), now) : zamanMetni(exam)}</span>
      </button>
      {konu && <p className="sinav-onizleme__konular">Konular: {konu}</p>}
      <p className="sinav-onizleme__baglantilar">
        {kaynak?.baglanti && (
          <CarbonLink href={kaynak.baglanti} size="sm">Kaynak: {kaynak.etiket}</CarbonLink>
        )}
        <CarbonLink href="/sinavlar#uyarilar" size="sm">Sınav uyarıları</CarbonLink>
      </p>
    </section>
  )
}

/** İşler: son 48 saatte bulunan ya da değişen sınav için gri, metinli etiket. */
export function SinavEtiketi({ exam, nowMs }: { exam: ExamItem; nowMs: number }) {
  const etiket = sinavEtiketi(exam, nowMs)
  return etiket ? <Tag type="gray" size="sm" className="sinav-etiketi">{etiket}</Tag> : null
}

/** Sınavlar: kaynaktaki konular ve kaynaklar, kısa alıntıyla (spec §8). */
export function SinavAyrintisi({ exam }: { exam: ExamItem }) {
  const navigate = useNavigate()
  const konular = exam.konular ?? []
  const kaynaklar = exam.kaynaklar ?? []
  if (konular.length === 0 && kaynaklar.length === 0 && !exam.tarihBelirsiz) return null
  return (
    <div className="sinav-ayrinti">
      {exam.tarihBelirsiz && <p className="sinav-ayrinti__not">Tarih belirsiz: duyuruda gün yazmıyor.</p>}
      {konular.length > 0 && (
        <div className="exam-card__section">
          <div className="exam-card__section-title">Konular</div>
          <ul className="exam-card__list">{konular.map(k => <li key={k}><span>{k}</span></li>)}</ul>
        </div>
      )}
      {kaynaklar.length > 0 && (
        <div className="exam-card__section">
          <div className="exam-card__section-title">Kaynaklar</div>
          <ul className="sinav-ayrinti__kaynaklar">
            {kaynaklar.map((k, i) => (
              <li key={i}>
                {k.baglanti ? (
                  <CarbonLink href={k.baglanti} onClick={e => {
                    if (k.baglanti?.startsWith('/') && !k.baglanti.startsWith('/api/')) {
                      e.preventDefault(); navigate(k.baglanti)
                    }
                  }}>{k.etiket}</CarbonLink>
                ) : <span>{k.etiket}</span>}
                {k.alinti && <blockquote className="sinav-ayrinti__alinti">{k.alinti}</blockquote>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
```

`SubjectLabel`'ın export biçimini (`default` mı adlandırılmış mı) `grep -n "export" dashboard/src/components/SubjectLabel.tsx` ile doğrula; `kisaTeslim`'in imzası `(tarih: Date, simdi: Date)` — `grep -n "export function kisaTeslim" dashboard/src/utils/formatters.ts`.

`dashboard/src/components/SinavKarti.scss`:

```scss
@use '@carbon/react/scss/spacing' as spacing;
@use '@carbon/react/scss/type' as type;

.sinav-onizleme {
  &__konular {
    @include type.type-style('body-compact-01');
    margin: spacing.$spacing-02 0 0;
    color: var(--cds-text-secondary);
  }

  &__baglantilar {
    display: flex;
    flex-wrap: wrap;
    gap: spacing.$spacing-05;
    margin: spacing.$spacing-02 0 0;
  }
}

.sinav-etiketi {
  margin-inline-start: spacing.$spacing-03;
}

.sinav-ayrinti {
  &__not {
    @include type.type-style('body-compact-01');
    margin: 0 0 spacing.$spacing-03;
    color: var(--cds-text-secondary);
  }

  &__kaynaklar {
    margin: 0;
    padding: 0;
    list-style: none;

    li + li {
      margin-block-start: spacing.$spacing-03;
    }
  }

  &__alinti {
    @include type.type-style('helper-text-01');
    margin: spacing.$spacing-02 0 0;
    padding-inline-start: spacing.$spacing-03;
    border-inline-start: 2px solid var(--cds-border-subtle);
    color: var(--cds-text-secondary);
  }
}
```

- [ ] **Adım 6: Yerleştir**

`TodaySchedule.tsx` (satır ~535): `yaklasanSinavlar`, `yarinSinavlari` hesabından sonra:

```tsx
  // The nearest exam within a week gets a line of its own with its topics — the
  // same quiet voice as "Ayrıca"; one the evening's "Yarın" already leads with
  // is not said twice (İ4), and it leaves the list below.
  const onizleme = enYakinSinav(examData.exams || [], nowMs, new Set(yarinSinavlari.map(x => x.e.id)))
  const listeSinavlari = yaklasanSinavlar
    .filter(x => !yarinSinavlari.includes(x) && x.e.id !== onizleme?.id).slice(0, 3)
```

(eski `listeSinavlari` tanımının yerine). `{listeSinavlari.length > 0 && (<section className="today-exams" …` bloğundan hemen önce:

```tsx
      {onizleme && <SinavOnizleme exam={onizleme} now={now} onAc={() => navigate(`/sinavlar?sinav=${onizleme.id}`)} />}
```

Import'lar: `import { enYakinSinav } from '../utils/sinav'`, `import { SinavOnizleme } from './SinavKarti'`. `nowMs` sayfanın dakikalık referans saati (zaten tanımlı).

`HomeworkTracker.tsx`: `const { data: examData } = useApi<{ exams: ExamItem[] }>(…)` tipini `useApi<ExamsApiResponse>('/api/exams', { exams: [], stats: { upcoming: 0, past: 0, averageGrade: null } })` yap. Sınav satırında başlıktan sonra `<SinavEtiketi exam={e} nowMs={Date.now()} />`; `when` yoksa `e.hafta || e.tarihBelirsiz` için `<span className="exams-ahead__when tedy-time">{zamanMetni(e)}</span>`. `exams-ahead__list`'ten sonra:

```tsx
          {(examData.tespit?.incelenmedi ?? 0) > 0 && (
            <p className="exams-ahead__not">Bazı ders duyuruları incelenemedi; sınav listesi eksik olabilir.</p>
          )}
```

`.exams-ahead__not` stilini HomeworkTracker'ın mevcut SCSS dosyasına (`grep -ln "exams-ahead" dashboard/src --include=*.scss`) `@include type.type-style('helper-text-01'); color: var(--cds-text-secondary); margin-block-start: spacing.$spacing-03;` ile ekle.

`ExamTimeline.tsx`:
- `ExamCard`'a `baslangicAcik?: boolean` prop'u; `useState(baslangicAcik ?? false)`; `hasDetails` = `!focusMode && (exam.relatedHomework.length > 0 || (exam.konular?.length ?? 0) > 0 || (exam.kaynaklar?.length ?? 0) > 0 || !!exam.tarihBelirsiz)`.
- Ayrıntıda `relatedContent` bölümünün ("İlgili Ders İçerikleri") yerine `<SinavAyrintisi exam={exam} />` — `relatedContent` artık gösterilmez (bu haftanın kart başlıkları sınavın konusu değildi, spec §3). `Document` icon import'u kullanılmıyorsa kaldır.
- Tarih satırı: `{exam.date ? <span className="exam-card__date">{formatExamDate(exam.date)}</span> : (exam.hafta || exam.tarihBelirsiz) && <span className="exam-card__date">{zamanMetni(exam)}</span>}`.
- Kartın `<Tile>`'ına `id={`sinav-${exam.id}`}`.
- `ExamTimeline` içinde:

```tsx
  const [searchParams] = useSearchParams()
  const acilacak = searchParams.get('sinav')
  const { hash } = useLocation()
  useEffect(() => {
    const hedef = acilacak ? document.getElementById(`sinav-${acilacak}`) : hash === '#uyarilar' ? document.getElementById('uyarilar') : null
    hedef?.scrollIntoView({ block: 'start' })
  }, [acilacak, hash, data.exams.length])
```

ve kartlara `baslangicAcik={exam.id === acilacak}`. (`useSearchParams`, `useLocation` `react-router-dom`'dan.)

`CourseContent.tsx:139`: `const [searchParams] = useSearchParams()` ve `useState<string | null>(() => searchParams.get('hafta'))`. Var olmayan hafta adı zaten `aktifHafta` hesabında `haftalik.current`'a düşer (satır 147-149).

- [ ] **Adım 7: e2e'yi genişlet** — `dashboard/tests/e2e/sinav-uyari.spec.ts` sonuna

```ts
import { bugunAc, SINAV } from './_bugun-fixtures'

const KTT = {
  ...SINAV('ktt', 'Matematik KTT', '2026-09-28T09:00:00'), course: 'Matematik',
  konular: ['Tam sayılar', 'Rasyonel sayılar', 'Mutlak değer', 'Oran'],
  kaynaklar: [{ tur: 'ders_karti', etiket: 'Matematik ders içeriği · 2. Hafta 21 Eyl. - 27 Eyl.',
    alinti: '28 EYLÜL PAZARTESİ günü yapılacak olan Matematik KTT', baglanti: '/dersler?hafta=2.%20Hafta' }],
  ilkTespit: '2026-09-24T08:00:00', degisti: null, tarihBelirsiz: false,
}
const QUIZ = { ...SINAV('quiz', 'Irregular Verbs Quiz', null as unknown as string), course: 'İngilizce', date: null,
  hafta: '2026-09-28', tarihBelirsiz: true, konular: [], kaynaklar: [], ilkTespit: '2026-09-20T08:00:00',
  degisti: '2026-09-24T07:00:00' }
const SINAVLAR = { exams: [KTT, QUIZ], stats: { upcoming: 2, past: 0, averageGrade: null },
  tespit: { uretildi: '2026-09-24T10:00:00', incelenmedi: 2 } }

test.describe('Sınavlar panoda', () => {
  test('Bugün: en yakın sınav konularıyla, renkli çip yok', async ({ page }) => {
    await bugunAc(page, '2026-09-24T10:15', { exams: SINAVLAR })
    const onizleme = page.locator('.sinav-onizleme')
    await expect(onizleme).toContainText('Matematik KTT')
    await expect(onizleme).toContainText('Konular: Tam sayılar, Rasyonel sayılar, Mutlak değer +1 konu')
    await expect(onizleme.getByRole('link', { name: /Kaynak: Matematik ders içeriği/ })).toBeVisible()
    await expect(onizleme.getByRole('link', { name: 'Sınav uyarıları' })).toHaveAttribute('href', '/sinavlar#uyarilar')
    await expect(onizleme.locator('.cds--tag')).toHaveCount(0)
    await expect(page.locator('.today-exams', { hasText: 'Matematik KTT' })).toHaveCount(0)
    await onizleme.getByRole('button').click()
    await expect(page).toHaveURL(/\/sinavlar\?sinav=ktt$/)
    await expect(page.locator('#sinav-ktt')).toContainText('Mutlak değer')
  })

  test('İşler: Yeni ve Değişti etiketleri ve incelenemedi notu', async ({ page }) => {
    await page.clock.setFixedTime(new Date('2026-09-24T10:30:00'))
    await mock(page, { ...LIVE, exams: SINAVLAR })
    await page.goto('/isler')
    const satir = (ad: string) => page.locator('.exams-ahead__row', { hasText: ad })
    await expect(satir('Matematik KTT').getByText('Yeni', { exact: true })).toBeVisible()
    await expect(satir('Irregular Verbs Quiz').getByText('Değişti', { exact: true })).toBeVisible()
    await expect(satir('Irregular Verbs Quiz')).toContainText('28 Eyl haftası')
    await expect(page.getByText('Bazı ders duyuruları incelenemedi; sınav listesi eksik olabilir.')).toBeVisible()
  })

  test('Sınavlar: tarih belirsiz ve kaynak alıntısı', async ({ page }) => {
    await bildirimTaklidi(page, { izin: 'default', abone: false })
    await page.clock.setFixedTime(new Date('2026-09-24T10:30:00'))
    await mock(page, { ...LIVE, exams: SINAVLAR, 'bildirim/anahtar': { anahtar: 'BAAA', acik: true } })
    await page.goto('/sinavlar?sinav=quiz')
    const kart = page.locator('#sinav-quiz')
    await expect(kart).toContainText('Tarih belirsiz: duyuruda gün yazmıyor.')
    await page.goto('/sinavlar?sinav=ktt')
    await expect(page.locator('#sinav-ktt blockquote')).toContainText('28 EYLÜL PAZARTESİ')
    const sonuc = await new AxeBuilder({ page }).include('#sinav-ktt').withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze()
    expect(sonuc.violations).toEqual([])
  })
})
```

(`SINAV`'ın imzası `(id, title, date)`; `import` satırını dosyanın başındaki import'larla birleştir.)

- [ ] **Adım 8: Doğrula**

Run: `cd dashboard && node --test tests/*.test.ts > /tmp/sinav-birim.log 2>&1; tail -5 /tmp/sinav-birim.log`
Expected: tüm birim testleri pass.
Run: `cd dashboard && npm run lint && npx tsc -b --noEmit`
Expected: hata yok.
Run: `cd dashboard && npm run build:carbon-ai > /tmp/sinav-build.log 2>&1 && TEDY_E2E_PORT=8391 env -u ANTHROPIC_API_KEY npx playwright test sinav-uyari sinav-ve-hata isler today bugun-duzen tasarim-denetimi ibm-erisilebilirlik --retries=0 --reporter=list > /tmp/sinav-e2e.log 2>&1; grep -E "passed|failed|✘" /tmp/sinav-e2e.log | tail -15`
Expected: hepsi passed. Sonra görsel/aria süitleri: `npx playwright test gorsel-regresyon aria-yapisi --retries=0` — Sınavlar sayfası (yeni kart) ve fikstür sınavı 7 gün içindeyse Bugün değişir. Farkı oku (`test-results/*-diff.png`, `.aria.yml` diff); yalnız beklenen bölgeler değiştiyse `--update-snapshots` ile güncelle ve ledger'a hangi snapshot'ların neden değiştiğini yaz. Beklenmeyen fark → hata, düzelt.

- [ ] **Adım 9: Commit**

```bash
git add dashboard/src/utils/sinav.ts dashboard/src/components/SinavKarti.tsx dashboard/src/components/SinavKarti.scss dashboard/src/components/TodaySchedule.tsx dashboard/src/components/HomeworkTracker.tsx dashboard/src/components/ExamTimeline.tsx dashboard/src/components/CourseContent.tsx dashboard/tests/sinav.test.ts dashboard/tests/e2e/sinav-uyari.spec.ts
# HomeworkTracker'ın SCSS'i ve güncellenen snapshot'lar varsa onları da adıyla ekle
git commit -m "feat(pano): Bugün sınav önizlemesi, İşler etiketleri, sınav konuları ve kaynakları

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Görev 11: Belgeler ve tam doğrulama

**Files:**
- Modify: `CLAUDE.md` (Key Modules tablosu, Data Flow, Deployment, bir "Sınav tespiti ve uyarılar" maddesi)

**Interfaces:**
- Consumes: Görev 1–10'un adları ve komutları
- Produces: belgelenmiş işletim (yalnız metin)

- [ ] **Adım 1: `CLAUDE.md`'yi güncelle**

Key Modules tablosuna altı satır (`src/sinav_tarihi.py`, `src/sinav_kaynaklari.py`, `src/sinav_cikarimi.py`, `src/sinav_tespiti.py`, `src/web_push.py`, `src/sinav_uyari.py`), her biri tek cümle. Data Flow'a:

```
Sınavlar → run_sync._sinav_tespiti_adimi (ekten sonra, health'ten önce; 45 s) → takvim + not tablosu (_sinav_listesi) + metin adayları → ön süzgeç → Haiku (önbellek, 2 USD/ay) → uydurma kapısı → output/sinavlar.json → /api/exams, asistan sinavlar
Uyarılar → tedy-sinav-uyari.timer (10 dk, TEDY_SINAV_UYARI=1) → sinavlar.json + output/bildirim_abonelikleri.json + output/bildirim_defteri.jsonl → web push (VAPID)
```

Deployment bölümüne:

```bash
# Sınav uyarıları zamanlayıcısı (repo kökündeki unit'ler kaynak)
install -m 644 tedy-sinav-uyari.service tedy-sinav-uyari.timer ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now tedy-sinav-uyari.timer
.venv/bin/python -m src.sinav_tespiti --kuru          # canlı veride bulunanları yazdır, dosyaya yazma
.venv/bin/python -m src.sinav_uyari tohumla           # bildirimleri açmadan önce: bilinenleri "gönderildi" say
.venv/bin/python -m src.web_push anahtar-uret         # VAPID çifti .env'e (bir kez; değer basmaz)
```

Bir madde: sınav tespiti ve uyarıların kuralları — `sinavlar.json` tek kaynak ve dosyasız düşüş; kimlik kuralı (takvim kimliği değişmez); uydurma kapısının dört kuralı; ilk kurulumda `ilk_tespit: null`; hafta alanı; uyarı zamanları ve sessiz saat; defter anahtarı; ilk cihazda kişinin tohumlanması; `TEDY_SINAV_UYARI` bayrağı, geri dönüş (`systemctl --user disable --now tedy-sinav-uyari.timer` + bayrağı `0`); iPhone'da bildirimin yalnız Ana Ekran'dan açılan PWA'da çalıştığı; test korumaları (`tests/conftest.py` `_canli_sinav_tespiti_yok`).

- [ ] **Adım 2: Tam doğrulama**

Run: `unshare -rn .venv/bin/python -m pytest -q > /tmp/sinav-tum.log 2>&1; tail -5 /tmp/sinav-tum.log`
Expected: Görev 1 Adım 1'deki taban kadar ya da fazlası geçer; yeni kırmızı yok. Taban kırmızıları adıyla rapora girer.
Run: `cd dashboard && npm run lint && npx tsc -b --noEmit && npm run test:birim`
Expected: hata yok.

- [ ] **Adım 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): sınav tespiti ve uyarılar maddesi, işletim komutları

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Görev 12: Yayın — kuru koşu kapısı ve kullanıcı onaylı açılış

Bu görevde kod yazılmaz; her adım **kullanıcının açık onayını** bekler (spec §12, Global Constraints). Onay yoksa durulur.

- [ ] **Adım 1: Kuru koşu (canlı veri, dosya yazmaz)** — kullanıcıya sor: "Canlı veride `--kuru` koşusu yapayım mı? Haiku'ya en çok ~50 metin gider (≈0,1 USD, aylık 2 USD tavanı içinde); önbellek ve defter yazılır, `sinavlar.json` yazılmaz." Onayla, worktree'den:

```bash
cd /mnt/thunderbolt/workspaces/TED/.claude/worktrees/sinav-uyari    # worktree'nin kodu, canlı veri
.venv/bin/python -c "import pathlib, src.sinav_tespiti as st; st.PROJE_KOKU = pathlib.Path('/mnt/thunderbolt/workspaces/TED'); raise SystemExit(st.main(['--kuru', '--sure', '300']))" > /tmp/sinav-kuru.txt 2>&1; tail -60 /tmp/sinav-kuru.txt
```

Kod worktree'den, veri canlı `output/scraped_data.json` ve portal eklerinden okunur; önbellek (`sinav_cikarim_onbellegi.json`) ve bütçe defteri **canlı** `output/`'a yazılır (bir sonraki gerçek tespit aynı metinler için ücret ödemez), `sinavlar.json` yazılmaz — bu, onay sorusunda kullanıcıya söylenir. Sonucu kullanıcıya göster: bulunan sınavlar, tarihleri, konuları, kaynakları; Matematik KTT (15 Ekim, beş konu), Fen quiz (5 Ekim haftası), İngilizce quiz'ler, GİS-1/GİS-2, Türkçe Ortak Yazılı, Sebit TM/FS beklenir. Kaçan ya da yanlış varsa kural/istem düzeltilir (yeni TDD döngüsü), kuru koşu tekrarlanır.

- [ ] **Adım 2: Dalı birleştir ve panoyu dağıt** — kullanıcıya sor. Onayla: paylaşılan checkout kuralı (ancestry-guarded fast-forward, `main`'i başka oturum ilerletmişse rebase) ile `main`'e al; canlı checkout'ta `cd dashboard && npm run build:carbon-ai` (asistan bayrağı `.env.production`'da) ve `systemctl --user restart ted-dashboard`. Bir sonraki senkronda `sinavlar.json` oluşur; `/api/exams` ve panoyu kontrol et. Bildirim hâlâ kapalı.

- [ ] **Adım 3: VAPID, pywebpush, zamanlayıcı** — kullanıcıya sor. Onayla (canlı checkout'ta):

```bash
.venv/bin/python -m src.web_push anahtar-uret
.venv/bin/python -m src.mcp_server.env_prep durum | grep -i vapid
systemctl --user restart ted-dashboard
install -m 644 tedy-sinav-uyari.service tedy-sinav-uyari.timer ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now tedy-sinav-uyari.timer
systemctl --user list-timers | grep sinav
```

Kullanıcı ve bir aile üyesi kendi telefonlarında Sınavlar → "Sınav uyarıları" → "Bu cihazda aç" → "Deneme bildirimi gönder" yapar (iPhone'da önce Ana Ekrana Ekle).

- [ ] **Adım 4: Bildirimleri aç** — kullanıcıya sor. Onayla:

```bash
.venv/bin/python -m src.sinav_uyari tohumla          # bilinen sınavlar için sel yok
.venv/bin/python -m src.mcp_server.env_prep ayarla TEDY_SINAV_UYARI --stdin <<< "1"
systemctl --user restart ted-dashboard
systemctl --user start tedy-sinav-uyari.service && cat output/sinav_uyari_durumu.json
```

Geri dönüş: `systemctl --user disable --now tedy-sinav-uyari.timer` ve `env_prep ayarla TEDY_SINAV_UYARI --stdin --degistir <<< "0"`.

- [ ] **Adım 5: Belleği güncelle** — `~/.claude/projects/-mnt-thunderbolt-workspaces/memory/` altında TEDY sınav uyarısı durumu (tarih, commit, açık/kapalı, geri dönüş) tek dosya + `MEMORY.md` satırı.
