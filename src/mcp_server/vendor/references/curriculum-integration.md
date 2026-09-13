# Müfredat MCP Entegrasyonu — Orkestrasyon, Kazanım Çekme ve Beceri-Etkileşim Haritalaması

> Bu referans, `carbon-edupedia`'nın **Müfredat MCP** sunucusunu kullanarak
> Türkiye Yüzyılı Maarif Modeli (MEB, 2024) kazanımlarını kaynak ve doğrulama
> katmanı olarak modüle bağlamasını anlatır. Üç işlevi kapsar:
> **(1) keşif + kazanım çekme**, **(2) resmî beceri → etkileşim deseni haritalama**,
> **(3) kazanım izlenebilirliği (provenans) + doğrulama**.
>
> **Temel ilke:** MCP verisi `SKILL.md §7`'deki kaynak-sadakati kuralının
> *primer kaynağıdır*. Çekilen kazanım/program metni tek doğruluk kaynağı olur;
> modüldeki her olgusal iddia bir kazanıma veya çekilen program/ders kitabı
> metnine **izlenebilir** olmalıdır. MCP *çekememe* durumu bir başarısızlık
> değildir; o zaman skill, kullanıcının verdiği metinle (offline) çalışmaya
> geri döner ve durumu açıkça bildirir.

## İçindekiler
1. Ne zaman Müfredat MCP kullanılır
2. Araç envanteri ve rolleri — kimlik biçimi + PDF temizleme uyarıları (plugin: `../../../CONNECTORS.md` normatif)
2.1 Görüntü-dayanak politikası (Tier-1 / Tier-2) — plugin düzeyi, additif
3. Keşif → çekme → haritalama → doğrulama iş akışı
4. **Beceri → etkileşim deseni haritalama tablosu** (çekirdek katma değer)
4.1 Keşif Döngüsü ile açılış (opsiyonel `hook`) — motivasyonel sarmalayıcı, beceri-eşlemesini değiştirmez
5. `curriculum` veri bloğu şeması (MODULE_DATA uzantısı)
6. Provenans ve G-CURRICULUM kapısı
7. Kaynak-sadakati: MCP verisine özel kurallar
8. Hata/erişilemezlik ve geri-dönüş (graceful degradation) + token ekonomisi
9. Çalışılmış örnek (Fen 5 — Hücre)

---

## 1. Ne zaman Müfredat MCP kullanılır

Müfredat MCP **opsiyoneldir**; çağrı kararı niyete göre verilir:

| Kullanıcı sinyali | MCP kullanımı |
|---|---|
| "5. sınıf fen *müfredatından* hücre konusunu öğret" | **Evet** — kazanım çek, beceri haritala |
| "şu kazanımla modül yap: FB.5.3.1.1" | **Evet** — kazanım kodunu doğrula + çek |
| "MEB kazanımlarına göre / programa uygun olsun" | **Evet** — program + kazanım çek |
| "bu konuya hangi kazanımlar denk geliyor?" | **Evet** — yalnız haritalama/keşif |
| Kullanıcı kendi ders notunu/metnini yapıştırdı | **Hayır** (varsayılan) — ama opsiyonel olarak ilgili kazanımı bulup **hizalama** önerilebilir |
| "müfredat" / "kazanım" / "MEB" / "Maarif" / ders+sınıf geçiyor | **Evet** (güçlü sinyal) |

**Disambiguation:** Müfredat MCP yalnızca **Türkiye MEB** müfredatını kapsar.
Yabancı müfredat (IB, Cambridge), üniversite içeriği veya genel konu anlatımı
için MCP çağrılmaz; kullanıcının kaynağı veya yerleşik bilgi kullanılır (SKILL.md §7).

## 2. Araç envanteri ve rolleri

> **Plugin-entegrasyon notu (edupedia).** Bu skill `edupedia` plugin'i altında paketlendiğinde,
> connector envanterinin, kimlik/PDF uyarılarının ve provenans standardının **normatif kaynağı
> `../../../CONNECTORS.md`'dir**; bu bölüm oraya referans verir. CONNECTORS.md canlı introspeksiyonla
> (2026-07-06) **otoritatif 21 araç** bildirir — aşağıdaki dokümante "19-araç" tabanına ek olarak
> `search_figures` **ve** `get_figure` da canlıdır (bu ikisi Tier-2 görsel yolunu mümkün kılar,
> §2.1). Aşağıdaki tablo pedagojik referans olarak korunur; connector adı/parametre değişikliği
> yalnızca CONNECTORS.md'de güncellenir. Standalone (plugin dışı) kullanımda bu bölüm kendi
> başına yeterlidir.

Araçlar dört işlevsel kümeye ayrılır. **Çoğu modül için 3–6 çağrı yeterlidir**
(keşif → kazanım çekme → opsiyonel program metni). Tümünü her seferinde çağırmayın.

> **Kimlik biçimi tuzakları (boş sonuç döndüren parametre hataları):**
> - **Ders slug'ını ASLA isimden uydurma.** "Matematik" ortaokulda
>   `ortaokul-matematik-dersi`, ilkokulda `ilkokul-matematik-dersi`; "Türkçe"
>   benzer biçimde ayrışır; "Fen" → `fen-bilimleri-dersi`. Her zaman önce
>   `list_subjects(q="…")` ile doğru slug'ı al.
> - **Sınıf etiketi `5.Sınıf` biçimindedir** — nokta sonrası **boşluk yok**, "Sınıf"
>   büyük S. `5. Sınıf` veya `5.sinif` boş sonuç döndürebilir. `get_subject.grades`
>   geçerli etiketleri verir.
> - **Çerçeve slug'ı yol-biçimlidir:** `beceriler/kavramsal-beceriler` (eğik çizgili).
> - **Belge id (`document_id`) tamsayıdır**, slug değil (`get_subject`/arama döndürür).
>
> **PDF-türevi metin temizliği (zorunlu):** Kazanım `text` alanları program PDF'inden
> çıkarıldığı için artefakt taşır: tireli satır kırpması ("rasyo- nel" → "rasyonel"),
> kesik son cümle ("...d) Problem"), ve gömülü "İÇERİK ÇERÇEVESİ / Anahtar Kavramlar /
> ÖĞRENME KANITLARI" başlıkları. Modüle koymadan önce: (1) tireli bölünmeleri birleştir,
> (2) içerik-çerçevesi + anahtar-kavram kuyruğunu **ayrıştır** ve ilgili teach
> segmentine olgu/terim kaynağı olarak yerleştir, (3) yarım kalan cümleyi **tamamlama** —
> eksikse o kısmı atla. Süreç bileşenleri (a/b/c/ç) modülde alt-hedef veya etkileşim
> adımı olabilir.

### A. Keşif / navigasyon (hangi ders, hangi sınıf, ne var?)
| Araç | Ne döner | Tipik kullanım |
|---|---|---|
| `server_info` | Korpus sürümü, build tarihi, sayımlar | Provenans damgası için sürüm öğrenme |
| `list_education_levels` | İki seviye (`temel-egitim`, `ortaogretim`) + ders sayısı | En üst seviye keşif |
| `list_subjects` | 60 ders (slug + ad + seviye + sınıf sayısı); `q` ile isim filtresi | **Ders slug'ını bulma** (kritik ilk adım) |
| `get_subject` | Bir dersin programları, sınıfları, ders kitapları, kanonik `outcome_count` (yalnız `fragment_type='outcome'`; eski tüm-parça toplamı `fragment_count`'ta) | Ders profilini doğrulama |
| `list_curriculum_programs` | Program belgeleri (subject/grade filtreli) | Program belge id'sini bulma |
| `get_curriculum_program` | Program belgesi + varsayılan hafif `toc` (ünite/bölüm başlıkları; belge metni yüklenmez). Ağır sayfa-başı dizini yalnız `page_index=true` ile `page_index` alanında | Ünite/bölüm yapısını görme |

### B. Kazanım (öğrenme çıktısı) erişimi — **modülün çekirdek kaynağı**
| Araç | Ne döner | Tipik kullanım |
|---|---|---|
| `list_learning_outcomes` | Bir dersin kazanımları (kod, metin, sınıf, sayfa) — `{items, included_fragment_types, offset, limit, has_more}` zarfında; `limit` varsayılan **100**, tavan **200** (eski 1000 reddedilir); varsayılan yalnız kanonik `outcome` satırları. `distinct_codes:true` ile kod başına tek kanonik satır | **Birincil çekme** — konu/ünite kazanımlarını listele; **`has_more:true` iken `offset += limit` ile döngü** |
| `search_learning_outcomes` | Tam-metin kazanım araması (`q`); ders/sınıf/seviye filtresi | Konu adından kazanım bulma ("hücre", "kesir") |
| `search` | Birleşik FTS: program sayfaları + çerçeveler + kazanımlar (`kind` filtresi) | Geniş keşif; konunun program metnindeki yeri |

> **Kazanım kodu anatomisi (Maarif 2024):** `FB.5.3.1.1` = Ders(FB=Fen) ·
> Sınıf(5) · Ünite(3) · Bölüm(1) · Çıktı(1). 3–4. sınıflarda bölüm yoktur
> (`DERS.SINIF.ÜNİTE.ÇIKTI`). Kazanım metni genelde bir **üst-fiil**
> ("...karşılaştırabilme") + alt süreç bileşenleri (a, b, c, ç...) içerir.
> Bu **üst-fiil**, beceri haritalamasının anahtarıdır (§4).

### C. Beceri/çerçeve katmanı — **pedagojik haritalama kaynağı**
| Araç | Ne döner | Tipik kullanım |
|---|---|---|
| `list_frameworks` | 13 çerçeve (Kavramsal Beceriler, SDÖB, Erdem-Değer-Eylem, Okuryazarlık, Eğilimler, Alan Becerileri...) + madde sayısı | Hangi beceri çerçeveleri var |
| `get_framework` | Çerçevenin tüm maddeleri (kod, başlık, açıklama) | **Beceri kodu → etkileşim eşlemesi** için (§4) |

> **En önemli çerçeve: `beceriler/kavramsal-beceriler`** (38 madde). 20 bütünleşik
> beceri (KB2.1–KB2.20) + 3 üst düzey (KB3.1–KB3.3) + 12 temel (KB1.x). Kazanım
> fiilleri büyük ölçüde bu becerilere karşılık gelir; §4 tablosu bunu etkileşim
> desenlerine bağlar.

### D. Destek belgeleri (opsiyonel zenginleştirme)
| Araç | Ne döner | Tipik kullanım |
|---|---|---|
| `list_document_kinds` | Belge türleri + sayıları | `list_documents` öncesi tür keşfi |
| `list_documents` | Her tür belge (program/textbook/guide/material/...) | İlgili materyal/farklılaştırma belgesi bulma |
| `get_document_text` | Belge sayfa metni (`page` / `page_range`, maks 25 sayfa). **DERS KİTAPLARI DA TAM METİN DÖNER** — aşağıdaki düzeltmeye bakın | **Ders kitabı gövdesini BİRİNCİL içerik olarak okuma**; program/kılavuz metni |
| `list_textbooks` | Ders kitabı kataloğu — `subject`+`grade` filtreli; her satırda **`page_count`** | Hedef ders+sınıfın kitabını bulma (kitabın KENDİSİ içeriktir, yalnız atıf değil) |
| `list_guides` / `list_reports` | Kılavuz / TYMM rapor belgeleri | Pedagojik kılavuz desteği |
| `list_videos` / `get_video` | Eğitim/tanıtım videoları | Opsiyonel görsel kaynak referansı (modüle gömülmez; atıf) |

## 2.1 Görüntü-dayanak politikası (Tier-1 / Tier-2) — plugin düzeyi, additif

> ⚠️ **ÖNCELİK 2026-07-17'de TERSİNE ÇEVRİLDİ.** Bu tablo eskiden Tier-1'i (yazar-üretimli
> SVG) "varsayılan ve zorunlu", Tier-2'yi (ders kitabının kendi figürü) "opsiyonel, asla
> kritik yol değil" diye tanımlıyordu. Bu, **"ders kitapları okunamaz" yanlış inancının**
> bir sonucuydu (bkz. §3 Adım 3 kutusu). Ölçüldü: **22.414 figür ders+sınıf filtreli
> aramaya açık** ve her biri caption + `page_no` taşır. Öğrencinin **kendi kitabındaki**
> görsel, öğrenme transferi için yazar çizimine üstündür. Kullanıcı sözleşmesi (2026-07-17):
> "ders kitabı içeriğindeki eğitsel görseller hazırlanan içeriğe entegre edilmeli."

> Bu alt-bölüm, `edupedia` plugin sarmalayıcısının görüntü-dayanak sözleşmesini netleştirir.
> Skill'in görsel arketipleri (`svgFigure`, `labeledFigure`, `vizTable`, `numberLine`,
> `fractionBar`, `relationFlow`; bkz. `svg-authoring.md`) **MCP'siz akışta** ve resmî figür
> bulunmayan kavramlarda yegâne yoldur. Tam normatif metin: `../../../CONNECTORS.md §3` +
> `../../../shared/canonical-cache-contract.md §4`.

| Katman | Tanım | Durum | Davranış |
|---|---|---|---|
| **Tier-2a** | `get_figure(..., include_image=false)` → **metadata**: `caption`, `page_no`, `bbox`, `pdf_url` | **ÖNCELİKLİ** (MCP bağlıyken) | `search_figures(query, subject, grade)` ile ara. `page_no` **en ucuz sayfa bulucudur** (§3 Adım 3). `include_image=true` ayrıca görseli **modelin GÖRMESİNİ** sağlar → yazar-SVG orijinale bakılarak çizilir. |
| **Tier-2b** | `pdf_url` + `page_no` + `bbox` → PDF'ten yeniden çıkarma → base64 JPEG | **Best-effort, yerel dosya sistemi + Python** | `scripts/fetch_figure.py` (`figures` bloğu + `@@FIG:<key>@@`). Native yol Claude Code/Cursor'dadır; diğer hostlarda ancak script açıkça yerelde çalıştırılabiliyorsa mümkündür. Öğrenci o görseli kitabında görüyor. Hata → yer tutucu yerinde kalır, `tier2_status` **raporlanır — sessizce atlanmaz**. claude.ai'de native yol yoktur. |
| **Tier-1** | Kazanım koduna/program metnine izlenebilir olgular + **yazar-üretimli tema-duyarlı SVG** (token-renkli, `role="img"`+başlık, WCAG 2.1 AA) | **Garanti — yedek** | Uygun resmî figür **yoksa**, MCP bağlı değilse, veya Tier-2 düşerse. `validate_module.py` G-SVG + G-CURRICULUM ile denetlenir. MCP'nin görsel çekememesi **başarısızlık değildir**: Tier-1 tek başına tam işlevseldir (`svg-authoring.md` doktrini) — üretim asla bloke olmaz. |

**Yetenek-probu (kanonik akış):**
1. `get_figure` araç listesinde **yok** → Tier-2 devre dışı (`tier2_status: unavailable`); Tier-1'de kal.
2. **Ara:** `search_figures(query=<konu>, subject=<slug>, grade=<sınıf>)` → aday `figure_id`'ler.
   Sonuçları **hedef ders+sınıfın kitabına** göre ele: `document_id` Adım 3'te açtığın kitapsa
   o figür birinci sınıf dayanaktır. Her sonuç `page_no` taşır → sayfa bulucu olarak da kullan.
3. **Göm (Tier-2b, yerel dosya sistemi + Python):** `get_figure(figure_id, include_image=false)`'ın
   verdiği `pdf_url` + `page_no` + `bbox` ile bir `figures` girdisi yaz ve görselin yerine
   `@@FIG:<key>@@` koy; sonra `python3 scripts/fetch_figure.py <html> --in-place` çalıştır
   (`tier2_status: embedded`; kaynak damgasına `pdf_url` + sayfa ekle). Hata → yer tutucu
   yerinde kalır, Tier-1'e düş (`tier2_status: degraded`) ve **bunu raporla**.
   > **DİKKAT — `include_image=true` base64 VERMEZ.** Görseli MCP ImageContent olarak döndürür:
   > model onu **görür** (bu Tier-2a'nın değeridir) ama base64'ünü metin olarak **almaz**,
   > dolayısıyla HTML'e yazamaz. Bu belge eskiden "base64 göm" diyordu — 2026-07-31'de
   > ölçülüp düzeltildi. Gerçek gömme yolu yukarıdaki script'tir
   > (tam sözleşme: `../../../CONNECTORS.md §3.2`).
4. `include_image=false` varyantı **ucuz ön-eleme** içindir (başlık, sayfa, `caption`,
   kazanım-bağı) — figürün konuya uyup uymadığını gömme maliyetine girmeden ölç.

> **Ders kitabı gövdesi artık modüle TAŞINIR** — `get_document_text` ile (§3 Adım 3): kitap
> hem çerçeveyi çizer hem birincil içerik kaynağıdır. Eskiden burada "kitaplar yalnız
> `pdf_url` ile referanslanır" yazıyordu; o cümle, kitap metninin okunamadığı sanılan
> döneme aitti ve **artık geçersizdir**. `pdf_url` yine atıf/derin-bağlantı için verilir.

## 3. Keşif → çekme → haritalama → doğrulama iş akışı

CURRICULUM modunda (veya Müfredat-duyarlı herhangi bir modda) bu sırayı izleyin.
Her adımda **en az çağrı** ilkesi geçerlidir.

**Adım 0 — KAPI: sınıf + ders kesinleşmeden ÜRETİM BAŞLAMAZ.** (Kullanıcı sözleşmesi,
2026-07-17.) Sınıf ve ders, modülün derinliğini ve kapsamını belirleyen şeydir; tahminle
üretilen modül yanlış sınıfa hitap eder ve bu **sessiz bir hatadır** — çıktı doğru görünür.

> ⚠️ **Bu belgede eskiden "koddan ders/sınıf/ünite çıkarılabilir" YAZIYORDU. YANLIŞTI.**
> `FB.5.3.1.1` → "Fen · 5. sınıf" bir **string tahminidir**, veri değil. Kod kalıbı
> derslere/yıllara göre değişir ve sessizce yanlış çözülür.

- **Kod verildiyse:** koddan **ÇIKARMA — DOĞRULA.** Otorite, `search_learning_outcomes`'un
  döndürdüğü kaydın `subject` + `grade` alanlarıdır (**`q` parametresi** — `query` değil).
  Kod çözülmezse **uydurma**: kullanıcıya bildir ve sor.
- **Kod YOKSA** (örn. "hücre hakkında modül") veya çözülen ders/sınıf belirsizse: **SOR.**
  Claude Code'da `AskUserQuestion`, claude.ai'da düz soru. "Muhtemelen 5. sınıftır" **deme**.
- Doğrulanan ders+sınıf `curriculum` ve `verification.frame_source` bloklarına yazılır.

Niyet ayrımı: kazanım kodu mu verildi (`FB.5.3.1.1`), yoksa ders+sınıf+konu mu ("5. sınıf
fen, hücre")? İkisi de aynı akışa girer; fark yalnız Adım 2'nin sorgusudur.

**Adım 1 — Ders slug'ını bul.** `list_subjects` (gerekiyorsa `q` ile) → doğru
`slug`'ı al (örn. `fen-bilimleri-dersi`). Slug olmadan kazanım çekilemez.

**Adım 2 — Kazanımları çek.**
- Konu adı varsa: `search_learning_outcomes(q="hücre", subject=<slug>, grade=<sınıf>)`
  → ilgili kazanım kodlarını bul.
- Tüm ünite gerekiyorsa: `list_learning_outcomes(subject=<slug>, grade=<sınıf>,
  distinct_codes=true)` → hedef kazanımları (ve İÇERİK ÇERÇEVESİ / Anahtar
  Kavramlar bloklarını) seç.
- **Sayfalamayı bitir (ZORUNLU):** yanıt `{items, …, offset, limit, has_more}`
  zarfıdır ve `limit` varsayılan 100 / tavan 200'dür. `has_more:true` iken aynı
  çağrıyı `offset += limit` ile tekrarla ve `items`'ları birleştir; `has_more:false`
  gelmeden kümeyi tam sayma — kısmi bir kazanım kümesiyle sessizce çalışılmaz.
- Kullanıcı kod verdiyse: aynı araçla kodu doğrula + tam metni al.

**Adım 3 — ÇERÇEVEYİ ÇİZ: ders kitabını AÇ (ZORUNLU, opsiyonel değil).**

> ### ⚠️ Eski bu belgede yazan "ders kitapları metin döndürmez" İDDİASI YANLIŞTI
> Ölçüldü (2026-07-17, canlı korpus): **105 ders kitabının 103'ü tam metin indekslidir.**
> `list_textbooks` her satırda `page_count` verir; `page_count > 0` olan her kitap için
> `get_document_text(document_id, page_range=…)` **gerçek sayfa metnini** döndürür — kazanım
> kodları, kavramsal beceriler, değerler, İÇERİK ÇERÇEVESİ blokları dahil. Yalnız `page_count=0`
> olan 2 kitap (Multi English 5 (1), Tarih 10) `pdf_url` notuna düşer.
> O yanlış iddia yüzünden elimizdeki **en otoriter kaynak** hiç açılmıyordu.

1. `list_textbooks(subject=<slug>, grade=<sınıf>)` → hedef ders+sınıfın kitabını bul.
   Birden çok cilt olabilir ("1.Kitap"/"2.Kitap") — konunun geçtiğini bulana kadar bak.
2. `search(q=<konu>)` veya `search_figures(query=<konu>, subject=…)` ile konunun **hangi
   sayfada** olduğunu tespit et (figür sonuçları `page_no` verir — en ucuz sayfa bulucu).
3. `get_document_text(document_id, page_range="112-120")` → **çerçeveyi bu metin çizer**:
   hangi kavramlar var, hangi derinlikte, hangi sırayla, hangi örneklerle.
4. `page_count = 0` ise (yalnız 2 kitap) veya ders+sınıf için kitap yoksa: **öğretim
   programına düş** (`get_curriculum_program` / `get_document_text`) ve bunu modülün
   `verification.frame_source` alanında **dürüstçe** belirt — asla "ders kitabına dayandı" deme.

**Çerçeve, üretimin sınırıdır (§6.1 Kapsam kapısı):** bu metinde/programda yer almayan bir
konuyu modüle KOYMA. Kitap "hücre zarı, sitoplazma, çekirdek" diyorsa mitokondri iç zar
kıvrımlarını anlatma — doğru olsa bile **o sınıfın çerçevesi dışındadır**.

**Adım 4 — Beceri çerçevesini haritala.** Her hedef kazanımın **üst-fiilini**
çıkar (örn. "karşılaştırabilme"). `get_framework("beceriler/kavramsal-beceriler")`
ile bütünleşik beceri koduna bağla (örn. KB2.7 Karşılaştırma) ve §4 tablosundan
uygun **etkileşim desenini** seç (örn. `match` + `vizTable`). Bu adım modülün
pedagojik omurgasını kazanımın gerektirdiği bilişsel sürece hizalar.

**Adım 5 — `curriculum` bloğunu doldur** (§5 şeması): her kazanım için kod,
metin, beceri kodu ve hangi segment id'lerine bağlandığı (`mappedTo`).

**Adım 5.5 — KAPSAM + DOĞRULUK DENETİMİ (ZORUNLU; §6.1'in `verification` bloğunu ÜRET).**
Kullanıcı sözleşmesi: içerik denetlenmeden canlıya alınmaz. **Denetimi sen (model) yaparsın
— ama dayanakla, sezgiyle değil.** İki eksen:
- **(a) Kapsam:** ürettiğin her şey Adım 3'te açtığın çerçevenin **İÇİNDE** mi? Dışında
  kalanı **çıkar** ve `verification.scope.excluded[]`'a yaz. Doğru olması yetmez — o sınıfın
  çerçevesinde yoksa yeri yok. `scope.in_frame:false` ise **üretme**.
- **(b) Doğruluk + tutarlılık:** her olgusal iddiayı ders kitabı metnine karşı sına; modül
  kendi içinde çelişmesin (bir segmentte kurduğunu başka segmentte bozma).

Sonucu **§6.1 şemasındaki `verification` bloğuna** yaz: her iddia için `claim` +
`grounding` (`document_id` + `page`) + `verdict`. **Dayanağını gösteremediğin iddiayı ya
kaynağına bağla ya modülden çıkar** — `verdict:"general_knowledge"` bir kaçış deliği değil,
bir **borçtur** (kapı WARN verir; çoğunluk öyleyse FAIL).

**Adım 5.6 — ÖĞRENCİ YÜZEYİ: NİHAİ DİL (ZORUNLU; G-VOICE).**
`verification` ve `sourceCitation` **yazar katmanıdır** — öğrenci bunları görmez. Öğrenciye
görünen `body` / `stem` / `explanation` / `recap` / `prompt` / `keyTerms` kitaba, sayfaya
veya "ünitede gördüğün"e göndermez. Kavramı bu modülün kendi tamamlanmış cümleleriyle yaz:
"Hücre, canlının en küçük yapı birimidir." — **değil** "Kitabın tanımı: …" veya "Kitaptaki
yazıyı hatırla." Kitaptan kopyalanmış cümleyi atıfla sarmalama; pedagojik olarak yeniden yaz.
PhET CC BY-NC künyesi lisans atfıdır (görünür kalır). Tam kural: SKILL.md §7.

**Adım 6 — Modülü kur, doğrula, sun.** Normal `carbon-edupedia` iş akışına dön
(SKILL.md §8 Adım 2 ve sonrası): segmentleri kazanımlara göre kurgula, şablona yerleştir,
kaydet (yüzeye göre — SKILL.md §8 Adım 6). `meta.sourceCitation` çekilen kazanım
kodlarını + korpus sürümünü içermeli.

> **Kapıların otoritesi yerel `validate_module.py`'dir** (G-CURRICULUM + **G-VERIFY**
> + **G-VOICE** dâhil). Plugin yayınlamaz. `verification` bloğunu "kapıyı geçmek için"
> değil, **denetimi gerçekten yaptığın için** yaz: kapı dayanağın GÖSTERİLDİĞİNİ ölçer,
> iddianın DOĞRU olduğunu **ölçemez** (çevrimdışı, MCP erişimi yok).

## 4. Beceri → etkileşim deseni haritalama tablosu  ← ÇEKİRDEK KATMA DEĞER

Maarif Modeli'nin **Kavramsal Beceriler** çerçevesindeki bütünleşik beceriler,
`carbon-edupedia`'nın etkileşim desenleriyle doğrudan örtüşür. Kazanım üst-fiilini
tespit et → beceri koduna eşle → **birincil** etkileşim desenini seç (yanına
**destek** görseli ekle). Bu eşleme, etkileşimi kazanımın gerektirdiği bilişsel
süreçle hizalar (yapıcı hizalama / constructive alignment).

### Bütünleşik beceriler (KB2.x)
| Kazanım üst-fiili (örnek) | Maarif beceri kodu | Birincil etkileşim | Destek görseli |
|---|---|---|---|
| karşılaştır(abilme), ayırt et | **KB2.7** Karşılaştırma | `match` (terim↔grup) | `vizTable` (karşılaştırma), `labeledFigure` |
| sınıflandır, grupla, ayrıştır, etiketle | **KB2.5** Sınıflandırma | `sorting` (kategori kutuları) | `infoCards`, `vizTable` |
| sırala, yapılandır, hiyerarşik ilişki kur | **KB2.13** Yapılandırma | `order` (sıradakini-seç) | `relationFlow`, `labeledFigure` |
| özetle, ana hatları çıkar | **KB2.3** Özetleme | `fillblank` (anahtar terim) | özet `teach` + `infoCards` |
| sorgula, soru sor, anlamlı soru üret | **KB2.8** Sorgulama | `mcq` (sokratik/neden) | `callout` ipucu |
| çıkarım yap, sonuca ulaş | **KB2.10** Çıkarım | `mcq` (gerekçeli) + `order` (adım) | `relationFlow` |
| genelle, örüntüden yargıya | **KB2.9** Genelleme | `mcq` (örüntü) + `fillblank` | `vizChart` (örüntü) |
| yorumla, kendi cümleyle açıkla | **KB2.14** Yorumlama | `flashcards` (terim→açıklama) | `teach` görseli |
| (veriye/gözleme dayalı) tahmin et | **KB2.11 / KB2.12** Tahmin | `mcq` (tahmin→doğrula) | `vizChart`/`vizTable` (veri) |
| ölç, değerlendir, ölçütle karşılaştır | **KB2.17** Değerlendirme | `checkpoint` (öz-değerlendirme) | `vizTable` (ölçüt) |
| ilişkilendir, neden-sonuç kur | (Yapılandırma/Çözümleme) | `match` + `relationFlow` | `relationFlow` |

### Üst düzey düşünme (KB3.x) ve temel beceriler (KB1.x)
| Kazanım üst-fiili | Maarif kodu | Birincil etkileşim | Not |
|---|---|---|---|
| problem çöz, çözüm stratejisi kur | **KB3.2** Problem Çözme | `order` (adımlar) + `mcq` (doğrulama) | Mat. çok-adımlı problem |
| karar ver, seçenekleri tart | **KB3.1** Karar Verme | `mcq` (senaryo) + `sorting` (ölçüt) | Sosyal/yurttaşlık |
| eleştirel düşün, sorgula-yargıla | **KB3.3** Eleştirel Düşünme | `mcq` (kanıt) + `fillblank` | Üst sınıf |
| say, oku, çiz, ölç, eşle, işaretle | **KB1.x** Temel Beceriler | doğrudan `mcq`/`match`/`hotspot` | Görsel/sayısal temel |

### Derse-özel beceri sinyalleri (subject-packs.md ile birleştir)
- **Matematik** ("hesapla", "çöz", "ispatla"): `order` (adım) + `mathExpr`/
  `numberLine`/`fractionBar` görselleri (subject-packs §2/§11.5).
- **Fen** ("gözlemle", "deney", "model oluştur"): `labeledFigure` (etiketli
  diyagram) + `relationFlow` (süreç) + `vizChart`/`vizTable` (deney verisi).
- **Sosyal/Din/Yurttaşlık** ("kavra", "değer", "hak", "olay"): `relationFlow`
  (sebep-sonuç), `infoCards` (kavram/değer), `timeline` (olay/belge).
- **Dil (Türkçe/İng/Fr)** ("çözümle", "kullan", "üret"): `glossSentence`
  (satır-arası), `dialogue`, `infoCards`, `flashcards`.

> **Kural:** Haritalama bir *öneri eşlemesidir*, mutlak değil. Bir kazanım birden
> çok beceri içerebilir; o zaman teach segmentini bir etkileşim, kontrol noktasını
> başka bir beceriyle eşleştir. **Her hedef kazanım için en az bir etkileşim**
> o kazanımın üst-fiiliyle hizalı olmalı (yapıcı hizalama). Asla kazanımın
> gerektirdiğinden daha düşük bir bilişsel düzeye indirgeme (örn. "karşılaştır"
> kazanımını yalnız tanıma quiz'iyle geçiştirme).

### 4.1 Keşif Döngüsü ile açılış (opsiyonel `hook`)

`gamified-flows.md` §2.1'deki **Keşif Döngüsü** şablonu (`hook → teach →
interaction → mikro-kazanım`), CURRICULUM modunda yukarıdaki beceri-eşlemesini
**değiştirmez** — üstüne opsiyonel bir motivasyonel sarmalayıcı ekler. Bir
kazanımın teach+etkileşim çiftini bir `hook` ile açmak istiyorsanız:

- `hook.question` kazanımın **öz** sorusunu meraklandırıcı biçimde sorar (ör.
  "Sence hücrenin enerji santrali hangisi?" → FB.7.2.1.3 mitokondri kazanımı);
  olgu **uydurmaz**, yalnız kazanımın kendi konusunu çerçeveler (SKILL.md §7).
- `hook.resolvesIn`, o kazanımı öğreten `teach` segmentinin `id`'sini gösterir;
  motor bu teach render edildiğinde kancayı **aynı akış içinde** kapatır
  (`gamified-flows.md` §3.1). Bu, `curriculum.outcomes[].mappedTo` ile **ayrı
  bir izlenebilirlik katmanıdır**: `mappedTo` kazanımı **hangi segmentin
  öğrettiğini/sınadığını** işaretler (G-CURRICULUM), `resolvesIn` ise **hangi
  kancanın nerede kapandığını** işaretler (G-FLOW). Kancanın kendi `id`'si
  **`mappedTo`'ya eklenmez** — kanca kazanımı öğretmez/sınamaz, yalnızca ona
  giriş yapar; hedeflenen `teach`/etkileşim id'leri `mappedTo`'da kalır.
- `hook.predict.options` kullanılıyorsa yukarıdaki "(veriye/gözleme dayalı)
  tahmin et → **KB2.11/KB2.12**" satırıyla doğal olarak eşleşir: kanca
  **notsuz** bir ön-tahmin toplar, ardındaki `mcq` (tahmin→doğrula) aynı
  kazanımı **puanlı** sınar — ikisi çelişmez, kanca sınavın ısınma turudur.

Şema/mekanik/erişilebilirlik normatif kaynakları bu belgenin dışındadır:
`module-architecture.md` §2 (`hook` alan şeması), `interaction-patterns.md`
(mekanik özeti) ve `gamified-flows.md` §2.1/§3.1 (akış + kanıt). Bu alt-bölüm
yalnız CURRICULUM-özel izlenebilirlik ayrımını (`mappedTo` vs `resolvesIn`)
belgeler; blok yoksa/hook kullanılmıyorsa hiçbir etkisi yoktur (opsiyonel).

## 5. `curriculum` veri bloğu şeması (MODULE_DATA uzantısı)

Müfredat-temelli modüllerde `MODULE_DATA`'ya **opsiyonel** bir `curriculum`
bloğu eklenir. Bu blok provenansı taşır ve G-CURRICULUM kapısınca okunur. Motoru
değiştirmez; bilgilendirici/izlenebilirlik katmanıdır (motor bunu görmezden gelebilir
veya özet ekranında gösterebilir; mevcut motorla geriye dönük uyumludur).

```js
const MODULE_DATA = {
  meta:{
    // ...
    mode:"CURRICULUM",                       // yeni mod (veya başka mod + curriculum bloğu)
    sourceCitation:"MEB Türkiye Yüzyılı Maarif Modeli — Fen Bilimleri Öğretim "
      + "Programı (2024), 5. Sınıf, 3. Ünite. Kazanımlar: FB.5.3.1.1, FB.5.3.1.2. "
      + "Kaynak: tymm.meb.gov.tr / Müfredat MCP (corpus v1, build 2026-06-09)."
  },

  curriculum:{                                // ← opsiyonel provenans bloğu
    framework:"Türkiye Yüzyılı Maarif Modeli (2024)",
    subjectSlug:"fen-bilimleri-dersi",        // list_subjects'ten
    grade:"5.Sınıf",
    corpusVersion:"1",                        // server_info'dan (opsiyonel)
    outcomes:[                                // hedef kazanımlar
      { code:"FB.5.3.1.1",
        text:"Bitki ve hayvan hücrelerini ... karşılaştırabilme",  // kazanım metni (kısaltılabilir)
        skill:"KB2.7 Karşılaştırma Becerisi", // §4 haritalaması
        mappedTo:["m1","tb1"] },              // bu kazanıma hizmet eden segment id'leri
      { code:"FB.5.3.1.2",
        text:"Hücre-doku-organ-sistem-organizma ... yapılandırabilme",
        skill:"KB2.13 Yapılandırma Becerisi",
        mappedTo:["o1"] }
    ]
  },

  // objectives / rewards / segments ... (normal şema)
};
```

**Şema notları:**
- `outcomes[].code` resmî kazanım kodudur (doğrulanabilirlik anahtarı).
- `outcomes[].mappedTo` o kazanımı *gerçekten* sınayan/öğreten segment id'lerine
  işaret eder; bu id'ler `segments[]`'te bulunmalı (G-CURRICULUM bunu denetler).
- `skill` alanı §4 haritalamasını belgeler (insan-okunur; zorunlu değil ama önerilir).
- Blok yoksa modül normal çalışır; CURRICULUM modunda blok **zorunludur**.

## 6.1 KAPSAM + DOĞRULAMA kapısı — `verification` bloğu (v3.6.0)

Kullanıcı sözleşmesi (2026-07-17): *"üretilen içeriklerin doğruluk ve tutarlılık denetimi
yapılmadan canlıya alınmamalı"*, iki eksende: **(a) kapsam** — içerik müfredat/ders kitabının
çizdiği çerçevenin içinde mi; **(b) doğruluk** — bilimsel/eğitsel olarak doğru-geçerli ve
tutarlı mı.

### Yargıyı MODEL yapar, yapıyı KAPI denetler

Bu ayrım pazarlık konusu değil. Python "bilimsel olarak doğru mu" diye karar veremez; bir kapı
ancak **kaydın var ve eksiksiz olduğunu** ölçebilir. Tersine, modelin "denetledim" beyanına da
güvenilemez — biçim kapılarının `--json` çıktısından başka bir "PASS" beyanı
kabul etmemesinin sebebi tam olarak budur.

Çözüm: modül, her olgusal iddianın **hangi ders kitabı sayfasına dayandığını** gösteren bir
`verification` bloğu taşır. Model yargılar; kapı, her iddianın bir dayanağı olduğunu ve
dayanakların gerçek belge/sayfaya çözüldüğünü denetler. **Dayanaksız iddia = FAIL.** Böylece
"kontrol ettim" tiyatrosu yapısal olarak imkânsızlaşır: iddiayı yazmak, dayanağını yazmayı
zorunlu kılar.

### Blok şeması

```jsonc
"verification": {
  "frame_source": {                 // çerçeveyi ÇİZEN kaynak — Adım 3'te açtığın metin
    "kind": "textbook",             // "textbook" | "program"  ("program" = kitap yok/page_count 0
    "document_id": 197,             //                          → dürüstçe belirt, kitap deme)
    "pages": "112-120",
    "title": "Fen Bilimleri 5.Sınıf Ders Kitabı (1.Kitap)"
  },
  "scope": {
    "in_frame": true,               // false ise ÜRETME
    "excluded": [                   // çerçeve dışı kaldığı için BİLEREK atılanlar
      "mitokondri iç zar kıvrımları — 5. sınıf çerçevesinde yok"
    ]
  },
  "claims": [                       // modüldeki her OLGUSAL iddia (pedagojik yönerge değil)
    { "claim": "Hücre zarı seçici geçirgendir",
      "grounding": { "document_id": 197, "page": 115 },
      "verdict": "supported" },     // "supported" | "supported_by_program" | "supported_by_source" | "general_knowledge"
    // ders kitabı OLMAYAN sınıf (frame_source.kind:"program") — alternatif kaynak dayanağı;
    // grounding `document_id` DEĞİL, kaynak künyesi + `license` taşır (izlenebilirlik):
    { "claim": "Fotosentez ışık enerjisini kimyasal bağ enerjisine çevirir",
      "grounding": { "source": "PhET: Fotosentez", "url": "https://phet.colorado.edu/...", "license": "CC BY-NC 4.0", "quote_allowed": true },
      "verdict": "supported_by_source" }
  ]
}
```

### Kapı: **G-VERIFY** — ne denetler, ne DENETLEYEMEZ

`validate_module.py` **çevrimdışı** çalışır ve **MCP erişimi yoktur**; denetimi salt-metin
(regex) yapar — tıpkı G-CURRICULUM gibi. Bu sınırı bilerek okuyun:

**Denetler (FAIL/WARN üretir):**
- `verification` bloğu **zorunlu** (CURRICULUM modunda / ders+sınıf verilmiş üretimde).
- `frame_source` bir `document_id` + `kind` taşımalı.
- `scope.in_frame` **true** olmalı; `false` → **FAIL**, üretilmez.
- `claims[]` boş olmamalı; **her** öğede `claim` + `grounding` + `verdict` olmalı.
- `verdict:"general_knowledge"` → **WARN** (dayanaksız; ya kaynağını bul ya çıkar).
  Olgusal iddiaların çoğunluğu `general_knowledge` ise → **FAIL**.
- `verdict:"supported_by_source"` (v3.6.0) — **ders kitabı OLMAYAN sınıflar için** (3,4,7,8,11,12;
  TYMM kademeli yürürlüğü henüz kitap yayınlamadı, ama kazanım çerçevesi 12 sınıfın tamamında
  var). Programın kapsamadığı olgu, alternatif kaynaktan (egitim-kaynak: PhET/Vikipedi) dayanaklanır.
  **Kanıtlı sayılır** (`general_knowledge` cezası YOK) — ama grounding'i `document_id` yerine
  **kaynak künyesi + `license`** taşımalı; `license` yoksa → **FAIL** (izlenebilir değil).
  **Yalnız `frame_source.kind:"program"` çerçevesinde meşru**: ders-kitabı çerçevesinde
  kullanılırsa azınlık → **WARN**, çoğunluk → **FAIL** (kitap varken omurga `supported` olmalı).
  Çelişkide öncelik: **ders kitabı > program > kaynak**. Görünür atıf (PhET CC BY-NC 4.0 zorunlu
  kılar) **yazarın sorumluluğudur** — kapı içeriği izler ama görünür atfı dayatmaz.

**DENETLEYEMEZ — bunlara güvenmeyin:**
- `document_id`'nin gerçekten var olduğunu (validator katalogu göremez),
- `kind:"textbook"` yazan belgenin `page_count > 0` olduğunu (2 kitapta 0'dır → orada
  `kind:"program"` yazmak MODELİN sorumluluğudur; kapı bu yalanı yakalayamaz),
- iddianın gösterilen sayfada gerçekten geçtiğini,
- iddianın **doğru** olduğunu.

**Dürüst sınır:** kapı, iddianın DOĞRU olduğunu değil, **dayanağının GÖSTERİLDİĞİNİ** kanıtlar.
Doğruluk yargısı modelindir ve **insan denetimine tabidir**. Kapının değeri şudur: iddiayı
yazmak, dayanağını yazmayı zorunlu kılar — "denetledim" demek ucuzken, "şu sayfada geçiyor"
demek kontrol edilebilirdir. Tiyatroyu imkânsız kılar, doğruluğu garanti etmez.

## 6. Provenans ve G-CURRICULUM kapısı

`scripts/validate_module.py` yeni bir **G-CURRICULUM** kapısı içerir (yalnız
`curriculum` bloğu varsa veya mod CURRICULUM ise tetiklenir):

- **G-CURRICULUM (WARN→FAIL koşullu):**
  - `mode:"CURRICULUM"` ise `curriculum` bloğu **zorunlu** (yoksa FAIL).
  - `curriculum.outcomes[]` boş olmamalı; her öğede `code` ve `text` olmalı.
  - Her `outcomes[].mappedTo` içindeki segment id'si `segments[]`'te **var olmalı**
    (kazanım→segment izlenebilirliği; eksik eşleme FAIL).
  - `meta.sourceCitation` kazanım kodu/korpus referansı içermeli (yoksa WARN).
  - `curriculum` bloğu yoksa ve mod CURRICULUM değilse: kapı **atlanır** (geriye
    dönük uyum; mevcut modüller etkilenmez).

Bu kapı, MCP-temelli modüllerin "müfredata uygun" iddiasını **denetlenebilir**
kılar: her kazanım kodu bir segmente bağlıdır, kaynak damgalanmıştır.

## 7. Kaynak-sadakati: MCP verisine özel kurallar

`SKILL.md §7`'nin tüm kuralları geçerlidir; MCP verisine ek olarak:

- **Çekilen kazanım metni primer kaynaktır.** Modüldeki olgular kazanım metnine,
  Anahtar Kavramlar / İÇERİK ÇERÇEVESİ bloklarına veya çekilen program/ders kitabı
  metnine dayanmalı. Kazanım metni süreç-odaklıdır ("...karşılaştırabilme a)...");
  somut olgular için gerekirse program metnini (`get_document_text`) veya kullanıcı
  kaynağını çek. **Eksik olguyu uydurma** — yerleşik müfredat bilgisi kullanılıyorsa
  açıkça etiketle ve doğrulama iste.
- **Kazanım kodlarını çarpıtma.** Bir kodu yanlış konuya bağlama; `mappedTo`
  yalnızca o kazanımı gerçekten sınayan segmentleri göstermeli.
- **Beceri etiketini abartma.** Bir kazanımı sınamadığı bir beceriyle (örn. "üst
  düzey eleştirel düşünme") etiketleme; üst-fiil ne ise o.
- **Korpus güncelliği.** `server_info`'dan `corpus_version`/`build_date` al;
  kaynak damgasına ekle. Korpus periyodik güncellenir; modül üretim anındaki
  sürümü yansıtır.
- **Yaş uygunluğu korunur.** MCP yalnız MEB içeriği verir; yine de hedef sınıf
  düzeyine sadeleştirme ve `carbon-edupedia` çocuk-güvenliği kuralları geçerlidir.

## 8. Hata / erişilemezlik ve geri-dönüş (graceful degradation)

Müfredat MCP **derleme anında** çağrılır; her zaman erişilebilir olmayabilir.

- **MCP erişilemiyorsa / araç hata dönerse:** Modül üretimini durdurma. Kullanıcıya
  kısaca bildir ("Müfredat verisine şu an ulaşılamadı; verdiğiniz içerikle / yerleşik
  müfredat bilgisiyle devam ediyorum") ve **offline** yola dön: kullanıcı kaynağı
  veya etiketli yerleşik bilgi (doğrulama isteyerek). `curriculum` bloğu kısmi
  doldurulabilir veya atlanabilir; mod CURRICULUM yerine MODULE'a düşebilir.
- **Kazanım bulunamadıysa** (`search_learning_outcomes` boş): Önce sorguyu
  genişlet/yeniden ifade et (eş anlamlı, daha kısa terim), gerekirse `list_learning_outcomes`
  ile üniteyi tara (`has_more:true` iken `offset += limit` ile tüm sayfaları). Hâlâ yoksa kullanıcıya doğru ders/sınıf/konu sor.
- **Yanlış slug:** `list_subjects` çıktısındaki slug'ları **birebir** kullan;
  slug'ı ezberden yazma/uydurma. Hatalı parametre boş sonuç döndürür → slug'ı doğrula.
- **Ders kitabı metni boş:** Beklenen davranıştır (`get_document_text` ders
  kitaplarında `pdf_url` döner, metin değil). Program belgesini veya kullanıcı
  kaynağını kullan.

> **Altın kural:** MCP bir *zenginleştirme ve doğrulama katmanıdır*, tek nokta
> bağımlılık değil. `carbon-edupedia`'nın çekirdek değeri (kaynaktan etkileşimli,
> erişilebilir, DEHB-dostu modül) MCP olmadan da çalışır.

### 8.1 Token ekonomisi — gereksiz çağrıdan kaçın
- **Tipik modül 3–4 çağrı:** `list_subjects` → `get_subject` →
  (`search_learning_outcomes` **veya** `list_learning_outcomes`) → gerekirse
  `get_framework`. Beceri haritalaması için §4 tablosu çoğu durumda yeter;
  `get_framework`'ü yalnız resmî beceri kodu/tanımı **modülde gösterilecekse** çağır.
- **`distinct_codes:true` kullan** (`list_learning_outcomes`): PDF parçalaması aynı
  kodu birden çok kez döndürür; bu bayrak kod başına tek kanonik satır verir = boşa
  token engellenir. Sayfalama yine geçerlidir: `has_more:true` ise `offset += limit`
  ile devam et (token tasarrufu için sayfa atlanmaz).
- **`get_document_text`'i dar al:** maks 25 sayfa, ama `page_range` ile 2–4 sayfa
  genelde yeter; yalnız kazanım metni olgu için yetersizse çağır.
- **Keşif sonuçlarını yeniden kullan:** Aynı oturumda birden çok modül üretiliyorsa
  ders slug'ı ve sınıf listesi değişmez — tekrar çağırma.

## 9. Çalışılmış örnek (Fen 5 — Hücre)

**Niyet:** "5. sınıf fen müfredatından hücre konusunu öğret + oyunlaştır."

1. `list_subjects(q="fen")` → slug `fen-bilimleri-dersi`.
2. `search_learning_outcomes(q="hücre", subject="fen-bilimleri-dersi",
   grade="5.Sınıf")` → ünite 3 kazanımları görünür.
3. `list_learning_outcomes(subject="fen-bilimleri-dersi", grade="5.Sınıf",
   distinct_codes=true)` → `has_more:true` ise `offset=100` ile tekrar çağrılıp
   `items` birleştirilir; hedef kazanımlar seçilir:
   - **FB.5.3.1.1** — "Bitki ve hayvan hücrelerini ... *karşılaştırabilme*"
   - **FB.5.3.1.2** — "Hücre-doku-organ-sistem-organizma ... *yapılandırabilme*"
   - İÇERİK ÇERÇEVESİ / Anahtar Kavramlar blokları olgu kaynağı olarak not edilir.
4. `get_framework("beceriler/kavramsal-beceriler")` → üst-fiiller eşlenir:
   - "karşılaştırabilme" → **KB2.7 Karşılaştırma** → `match` + `vizTable`
   - "yapılandırabilme" → **KB2.13 Yapılandırma** → `order` + `relationFlow`
5. `curriculum` bloğu doldurulur (`mappedTo: m1/tb1` ve `o1`).
6. Segmentler kurulur: teach (hücre kısımları, `labeledFigure`) → flashcards →
   mcq → teach (bitki/hayvan, `vizTable`) → **match (KB2.7)** → brainbreak →
   teach (yapı düzeyleri, `relationFlow`) → **order (KB2.13)** → fillblank →
   checkpoint. `validate_module.py` (G-CURRICULUM dâhil) ile doğrulanır.

Bu örneğin tam uygulaması `assets/`'taki şablonla üretilebilir; sonuç tek-dosya,
9 kalite kapısını geçen, kazanım-izlenebilir bir modüldür.
