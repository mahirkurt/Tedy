# TEDY

Işık'ın okul portallarından (TED Rönesans, EBA, MEBI, SEBİTV, Achieve3000,
EnglishCentral) veri toplayan ve `tedy.online` panelinde sunan yerel otomasyon.

Google Classroom, Calendar ve Drive yazma yolu yoktur. Panel kimliği Google
Sign-In ile doğrulanır; sohbet asistanı Claude + BM25 + müfredat/OER MCP
kullanır.

## Çalıştırma

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Portal taraması (cron her 15 dakikada bir)
python src/run_sync.py

# Panel
python src/dashboard_api.py          # :8085
cd dashboard && npm run dev          # :3000, /api → :8085
```

`python -m src.main` üretim girişi değildir.

## Test

```bash
pytest
TEST_AUTH_BYPASS=1 pytest tests/test_dashboard_api.py
cd dashboard && npm run lint
cd dashboard && npm run build
cd dashboard && npx playwright test   # :8286, TEDY_E2E_PORT ile değişir
python src/check_books.py
```

## Asistan

Sohbet Anthropic Claude API üzerindendir; yerel model sunucusu gerekmez.
Bilgi indeksi BM25'tir. Öğretmen modları, sahipli dosya yükleme, kalıcı sohbetler,
alıştırmalar ve öğrenme günlüğü panel içinde çalışır. Öğrenci sohbetleri aileye
salt okunur açılır; özel yüklemeler genel bilgi indeksine girmez. Fotoğraftan
çıkarılan ödevler yalnız kullanıcı karttaki bilgileri onayladığında kaydedilir.

Sesli okuma tarayıcının Türkçe sesini kullanır. Mikrofon isteğe bağlıdır;
konuşma tanımanın Chrome/Android üzerinde sesi Google'a göndermesi arayüzde
onaydan önce açıklanır. Cevap denetimi bir Haiku çağrısıyla yapılır.

Bu sürüme geçerken `python src/reindex_assistant.py --full` ile indeks biçimi
3'e yenilenir. Yüklemeler ve sohbet deposu yeniden indekslemede dışarıda tutulur.
Altın soru değerlendirmesi `scripts/asistan_eval.py` ile ayrı, açık onaylı bir
komuttur; testler gerçek model çağrısı yapmaz.

```bash
python src/reindex_assistant.py
python src/assistant_ops.py verify-index --max-age-minutes 180
python src/assistant_ops.py generate-key --bytes 48 --env-line
```

MCP müfredat araçları `.env` içindeki `MUFREDAT_MCP_API_KEY` ve
`EGITIM_KAYNAK_MCP_API_KEY` ister — servis `EnvironmentFile=.env` okur,
kabuğu görmez. Anahtar yoksa asistan yerel kayıtlardan cevap verir.

Go-live: `docs/assistant-go-live.md`

## Belgeler

- `AGENTS.md` / `CLAUDE.md` — çalışma sözleşmesi ve mimari (kod çelişirse kod)
- `docs/frontend-design-principles.md` / `docs/frontend-surface-designs.md`
- `books/README.md` — Tedy Books yayın sözleşmesi
- `docs/api-guide.md` — üçüncü taraf REST (oturum veya `tdyK_` anahtarı)
- `docs/plans/*` — tarihli tasarımlar; mevcut durum kanıtı değildir
