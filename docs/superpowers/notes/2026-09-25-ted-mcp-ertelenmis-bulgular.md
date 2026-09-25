# ted-mcp — ertelenmiş bulgular ve açık kabul ölçütü

Kaynak: alt proje 2 SDD ledger'ı (`.superpowers/sdd/2026-09-13-ted-mcp-orkestrator-cekirdegi/progress.md`,
411 satır) ve alt proje 6 ön-kabul kanıtı (`.superpowers/sdd/2026-09-14-edupedia-1-0-yuzey-paketleri/kanit/`).
İkisi de git-dışı karalama alanıydı; silinmeden önce kalıcı kayıt için buraya taşındı (2026-09-25).

Hiçbir bulgu kritik ya da önemli değildir. Her biri ilgili görevin incelemesinde Minor olarak işaretlenip bilinçli
ertelendi ya da park edildi.

Durum sütunu:
- **açık** — 2026-09-25'te `main` kodunda yoklandı, hâlâ duruyor.
- **kapandı** — yoklandı, artık kodda yok.
- **yoklanmadı** — yalnız ledger kaydı; güncel kodda doğrulanmadı, sonraki düzeltme turlarında kapanmış olabilir.

## Davranış ve sağlamlık

| # | Bulgu | Yer | Durum |
|---|---|---|---|
| 1 | Portsuz köşeli IPv6 `Host: [::1]` → `:` olarak ayrıştırılır, 400 döner | `http_app.py` HostGuard | yoklanmadı |
| 2 | Redirect netloc küçük harfe çevrilmeden karşılaştırılır; `https://Claude.AI/cb` reddedilir (güvenli yönde) | `oauth_redirect.py` | yoklanmadı |
| 3 | `TED_MCP_ALLOWED_HOSTS` büyük harf içerirse 400 (hostlar küçük harfe çevrilmez, gelen Host çevrilir) | `config.py` | yoklanmadı |
| 4 | `read_form_state`: süre kontrolü `try` dışında, `isinstance(data, dict)` savunması yok (imzalı yük hep dict olduğundan erişilemez) | `http_app.py` | yoklanmadı |
| 5 | S256 normalizasyonu iki yerde ayrı türetilir; küçük harf `s256` için regresyon testi yok | `http_app.py`, `oauth_store.py` | yoklanmadı |
| 6 | Yalnız boşluktan oluşan `code_challenge` kabul edilir (sömürülemez) | `http_app.py` | yoklanmadı |
| 7 | `_HEALTH_CALLS[name]`: sağlık çağrısı tanımsız sunucu eklenirse `canli=True` KeyError | `tools.py` | kapandı |
| 8 | `Tools.rehber(ara='')` rehbere düşer, `ara='   '` ise `gecersiz_sorgu` alır | `tools.py` | yoklanmadı |
| 9 | `_pieces` döngüsü `PART_MAX_BYTES < 4` olsa sonsuza girer; savunma assert'i yok (bugün erişilemez) | `rehber.py` | yoklanmadı |
| 10 | `resolve_subject` tam-slug dalı büyük/küçük harfe duyarlı | `kapsam.py` | yoklanmadı |
| 11 | Aynı kazanım kodu için birden çok satır dönerse otorite `rows[0]`; satırlar ders/sınıfta ayrışırsa seçim keyfi | `kapsam.py` | yoklanmadı |
| 12 | `get_document_text` `error=invalid_range` dönerse `coverage` maarif-mufredat `hit` kalır (`degraded` olmalı) | `kapsam.py` `_frame` | yoklanmadı |
| 13 | Anamnesis degrade nedeni sabit `anamnesis_degraded`; upstream'in özgül nedeni (`vector_unavailable`) kaybolur | `kaynak_oku.py` | açık |
| 14 | RFC 7009 `/oauth/revoke` ucu yok; `tdyM_` anahtarlarında son kullanma tarihi yok | OAuth yüzeyi | yoklanmadı |
| 15 | Kök liste e-posta karşılaştırmasında Unicode uyumluluk katlaması yok (e-posta yalnız Google imzalı token'dan gelir, sömürülemez) | kimlik | yoklanmadı |
| 16 | Content-Length'siz, sınırı aşan `/mcp` gövdesinde MCP SDK istek başına traceback log'lar (yalnız geçerli token sahibi tetikler) | `/mcp` | yoklanmadı |
| 17 | `OAuthStore(":memory:")` çalışmaz; çalışma dizininde başıboş dosya yaratır | `oauth_store.py` | yoklanmadı |
| 18 | Başlangıç temizliği SQLite hatasında lifespan'i düşürür (systemd `Restart=on-failure` toparlar) | `http_app.py` | yoklanmadı |
| 19 | Onay sayfası `client_name`'i doğrulanmış kimlik gibi sunar ("kendini X olarak tanıtan uygulama" olmalı) | `http_app.py` | yoklanmadı |
| 20 | `invalid_client` 400 döner; RFC 6749 §5.2 istemci kimlik doğrulaması başarısızlığında 401 der | `http_app.py` | yoklanmadı |
| 21 | İstemci tahliyesi kayıt yaşına göre; tablo 50 000'de doluyken geç onaylanan akış 400 `invalid_client` alabilir | `oauth_store.py` | yoklanmadı |
| 22 | Sabit bir kaynak dosyası eksikse `vendor_sync --check` listeye yazmak yerine `FileNotFoundError` fırlatır | `vendor_sync.py` | yoklanmadı |

## Test ve kod temizliği

| # | Bulgu | Yer | Durum |
|---|---|---|---|
| 23 | Kullanılmayan `import pytest` | `tests/test_roles.py` | açık |
| 24 | Kullanılmayan `from pathlib import Path` | `tests/test_mcp_federation.py` | açık |
| 25 | `except (ValueError, UnicodeEncodeError)` — ikincisi zaten `ValueError` alt sınıfı | `http_app.py` | açık |
| 26 | `ClientLimitReached` docstring'i hâlâ "purged" der | `oauth_store.py:116` | açık |
| 27 | İngilizce yorum içinde Türkçe "bölüm" | `rehber.py:13` | açık |
| 28 | `MCP_HEADERS` sözlüğü üç test dosyasında tekrarlanır | `tests/test_mcp_*` | yoklanmadı |
| 29 | Vendor gidiş-dönüş testi yalnız `drift:` dalını sınar | `tests/test_mcp_vendor.py` | yoklanmadı |
| 30 | `Federation.call(beklenen="liste")` için çoklu nesne ve tek JSON dizisi uçtan uca testsiz | `tests/test_mcp_federation.py` | yoklanmadı |
| 31 | `redeem_code` ASCII dışı `code_verifier` dalı testsiz | `tests/test_mcp_oauth_store.py` | yoklanmadı |
| 32 | `keys.py` iptal dalı açık `elif` yerine eleme ile (argparse `required=True` sayesinde güvenli) | `keys.py` | yoklanmadı |
| 33 | Eşzamanlılık testinde `release.set()` `try/finally` içinde değil; iddia düşerse iş parçacığı 10 sn bekler | `tests/test_mcp_server.py` | yoklanmadı |
| 34 | Ders yeniden çözümlemesinin hata yolu testsiz | `kapsam.py` | yoklanmadı |
| 35 | Tek-getirme testi `wait(0.2)` yüklü makinede kilitsiz bir sürümü de geçirebilir | `tests/test_mcp_google_identity.py` | yoklanmadı |
| 36 | CORS listesi `vscode.dev` kökenlerini yalnız `/mcp` için tutar (bilinçli; belgelenmeli) | `oauth_redirect.py` | yoklanmadı |

## Park edilen kararlar

- `mcp_client` `malformed_result` logundaki `%r` biçimi değiştirilmedi: istemci canlı dashboard ile paylaşılıyor,
  log biçimini değiştirmek onun log davranışını da değiştirir. Bedeli: bozuk bir filo yanıtında uzun tek satır log.
- `kapsam.py` `^[0-9]+$` deseni sondaki `\n`'i kabul eder (`'7\n'` → 7); kesme ya da çakışma yaratmaz.
- İki yarışsızlık testi sınırlı iddiada kaldı: biri durumu elle kurar (gerçekten eşzamanlı değil), öteki
  "kendi yakalanan kimliğini kullanır" diye iddia etmez.

## Alt proje 6 canlı ön-kabul (2026-09-18) ve açık kabul ölçütü

Denetleyici ön-kabulü (2026-09-18T16:26:50Z):
- canlı 14 araç, adlar bootstrap ile eşleşir; kapı sayısı 18, rol `full`, rehber `ok`;
- DCR geri-çağırma: claude.ai, claude.com, chatgpt, grok, gemini ve loopback 201; vscode.dev 400 (red log'a yazılır);
- katalog o an boştu (0 aktif modül).

2026-09-25 ölçümü (`edupedia_katalog`): 1 aktif modül — `mat7-tam-sayilar` v1, 2026-09-19, kapılar 17 geçti / 0 uyarı /
0 kaldı.

**Açık:** Spec §14 kabul ölçütü 4 — "dört yüzeyin her birinde bir modül üretilip tedy.online'da açılır" — kapanmadı.
Katalogda tek modül var; Codex, Grok ve Gemini Spark yüzeylerinden canlı üretim kanıtı yok. Bu adım her yüzeyde
insanın Google onayıyla `mcp.tedy.online`'a bağlanmasını gerektirir.
