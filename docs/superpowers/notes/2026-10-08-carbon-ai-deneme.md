# Carbon AI Chat risk denemesi — 2026-10-08

Plan: `docs/superpowers/plans/2026-10-08-asistan-carbon-ai-chat.md`, Görev 1. `@carbon/ai-chat` 1.22.0,
`@carbon/web-components` 2.65 (npm `^2.58.1` aralığını 2.65'e çözdü). Deneme sayfası `ChatCustomElement` +
`customSendMessage` ile Vite geliştirme sunucusunda Chromium'da ölçüldü; deneme kodu silindi.

| # | Nokta | Ölçülen | Karar |
|---|---|---|---|
| 1 | `answer_reset` → boş `complete_item`; `final_response` taslağın yerine geçer; `chain_of_thought` akışta; `user_defined`; geri bildirim düğmesi | "Önce müfredata bakayım." boş `complete_item` ile kayboldu; "TASLAK METİN" `final_response` ile yerini son metne bıraktı; `user_defined` kartı (light DOM) çizildi; araç adımı "Müfredat aranıyor" ✓ ile göründü — **varsayılan kapalı** bir "How did I get this answer?" düğmesinin altında; beğen/beğenme düğmeleri göründü. | TUTTU |
| 2 | `:::` kutusu + KaTeX eklenti çıktısı; tablo | Eklenti çıktısı light DOM'da (`.ac-kutu--kavram` seçiciyle bulundu, içinde `.katex` ve `<strong>`); sayfa yana kaymadı. Tablo Carbon'un `cds-table`'ıyla çizildi: "Filter table" arama kutusu ve indirme düğmesi ekliyor ve **erişilebilirlik ihlali** veriyor (5. satır). | Kutu/KaTeX TUTTU; tablo **YEDEK**: `markdown.customRenderers.table` ile kendi tablomuz (eski `ac-md__table` + `Kaydirilabilir`). |
| 3 | `--cds-button-primary` kökten gölge köke geçiyor mu | Kökte `rgb(1, 2, 3)` verilen değişken gönder düğmesinin `cds-button` ve iç `button` öğelerinde aynı değerle okundu (özel özellikler gölge köke miras geçiyor). Boş girişte düğme arka planı saydam (devre dışı görünüm), rengin uygulanışı Görev 17'de görsel testle doğrulanacak. | TUTTU |
| 4 | Türkçe metin | Denemede yalnız iki metin çevrildiği için kalan İngilizce metinler beklenen listeydi (Ek A paketi hepsini kapsıyor). Ayrıca: **`locale: 'tr'` desteklenmiyor** (konsol: desteklenenler `en`, `en-gb`, `de`, `fr`…; `en`'e düşüyor) → zaman damgaları "3:50 PM"; asistan adı "watsonx" ve watsonx simgesi görünüyor. | **YEDEK**: `locale: 'en-gb'` (24 saat "15:50"), `assistantName: 'TEDY Asistan'`, `hideAvatar: true`; Görev 11 e2e'si "AM/PM" ve "watsonx" geçmediğini doğrular. |
| 5 | axe/IBM gölge DOM içini görüyor mu | **Görüyorlar**: IBM yolları `#document-fragment` içinden geçiyor, axe hedefleri `cds-aichat-react` gölge kökü içinde. Carbon'un kendi bileşenlerinde ihlaller var: tablo (axe `aria-required-children` kritik, `aria-allowed-role`; IBM `aria_child_valid`, `element_tabbable_role_valid`, `label_content_exists`, `aria_role_valid`) ve başlıktaki Carbon AI etiketi (axe `nested-interactive`, ciddi). `landmark-one-main` ve `page-has-heading-one` deneme sayfasının kendisinden. | TUTTU (denetimler içeri bakıyor). Tablo ihlali 2. satırdaki kendi tablomuzla kalkar. Başlık AI etiketi: `header.showAiLabel: false`, açıklama penceresi kendi `@carbon/react` `AILabel`'ımızla `headerFixedActionsElement` yuvasında (eski arayüzde axe/IBM temizdi). Kalan Carbon iç ihlalleri Görev 19'da ortaya çıkarsa spec'e "bilinen boşluk" olarak yazılır ve kullanıcıya sorulur. |
| 6 | Paket boyutu, telemetri | Deneme sayfası paketi: ana parça 4.20 MB (gzip 835 KB); CodeMirror 330 KB (gzip 107 KB) ve tablo çalışma zamanı 286 KB (gzip 42 KB) zaten ayrı tembel parçalar; toplam JS gzip ≈ 1.49 MB, varlıklar 8.6 MB. Derlenmiş pakette `ibm-telemetry` geçmiyor; npm kurulum betiklerini zaten engelliyor (`install-scripts` uyarısı), telemetri betiği hiç çalışmadı. | Kabul: yalnız asistan açıldığında yüklenir (Görev 2 testleri). |

## Ek bulgular

- `ChatCustomElement` kapalı başlatıcı görünümünde açılıyor: gömülü sayfa için `openChatByDefault: true` ve `launcher: { isOn: false }` gerekli.
- `historyPanelElement` yuvasının içeriği panel kapalıyken sayfanın sol üstünde düz metin olarak görünüyordu: Görev 15'te panel açık/kapalı görünürlüğü sınanacak.

## Yedek yollar (uygulanan)
- Tablo → kendi çizicimiz (`customRenderers.table`), Görev 8/11.
- Yerel ayar → `en-gb` + `assistantName` + `hideAvatar`, Görev 10.
- Başlık AI etiketi → kendi `AILabel`'ımız, Görev 14.
