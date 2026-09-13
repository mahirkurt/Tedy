# Ses Sistemi — Earcon Tasarımı, Kanıt ve Sorumlu Kullanım

Bu belge, modüllerdeki **işitsel geri bildirim** (earcon) katmanının tasarım ilkelerini,
kanıt temelini ve DEHB-odaklı güvenlik sınırlarını tanımlar. Ses **ikincil ve eşli** bir
katmandır: her işitsel ipucu daima bir görsel geri bildirimle birlikte verilir; ses tek
başına hiçbir bilgi taşımaz (erişilebilirlik + işitme engeli + sessizde tam işlevsellik).

## 1. Tasarım ilkeleri (özet)

1. **Kısa, ayrık olay-earcon'ları** — sürekli müzik/gürültü YOK. Her ses < ~300 ms, yumuşak
   zarf (attack/decay), düşük tepe kazancı (~0.06–0.11).
2. **Pozitif değerlik** — başarı/ödül sesleri hoş, yükselen motifler; "yanlış" sesi alçak,
   nazik ve **cezalandırıcı değil** (sert/alçak-değerlikli ses gerilim artırır → kaçınılır).
3. **Görselle eşli** — earcon, görsel geri bildirimin (işaret, XP patlaması, rozet) yanında.
4. **Opsiyonel ve susturulabilir** — üst çubukta hoparlör düğmesi; durum bellekte tutulur.
5. **Reduced-motion duyarlı** — `prefers-reduced-motion: reduce` ise ses **varsayılan kapalı**
   (duyusal yükü azaltma tercihinin makul bir vekili); kullanıcı dilerse açar.
6. **Düşük ses + tarayıcı-yerel** — Web Audio ile sentezlenir (harici dosya yok, çevrimdışı,
   tek-dosya bütünlüğü korunur). İlk kullanıcı etkileşiminde `AudioContext` devreye alınır
   (autoplay engeli aşılır).

## 2. Earcon kataloğu

| Olay | Earcon | Karakter | Tetikleyici |
| --- | --- | --- | --- |
| `correct` | E5→B5, iki nota, sine | kısa, yükselen, hoş | her doğru/ödüllendirme (`addXP`) |
| `retry`   | tek alçak nota (Eb4), sine | yumuşak, nazik, **cezasız** | yanlış cevap dalları |
| `reward`  | E5→Ab5→Eb6 arpej, triangle | kutlama | modül tamamlama / özet |
| `notify`  | iki notalı nazik çan | bilgilendirici | mola hatırlatıcı; ses açılınca onay |

Tüm tepe kazançları düşük tutulur; sesler kısa ve örtüşmesiz tasarlanır. "Yanlış" sesi
bilinçli olarak alçak ve kısa — başarısızlığı vurgulamaz, yeniden denemeye davet eder.

## 3. Görsel oyunlaştırma geri bildirimi (ses ile eşli)

- **XP patlaması** — doğru cevapta XP sayacının yanında yükselip sönen "+N XP" çipi + sayaç
  nabzı (`pulseEl`). Reduced-motion'da yalnız sayı güncellenir (animasyon yok).
- **Rozet kutlaması** — yeni kazanılan rozet `badge--new` ile ölçeklenerek belirir.
- **Doğru/yanlış işaretleri** — mevcut `feedback--ok/--no` + seçenek vurguları (renk DAİMA
  ikon/metinle birlikte; CVD-güvenli).
- Tüm animasyonlar `@media (prefers-reduced-motion: no-preference)` altında; aksi hâlde statik.

## 4. Kanıt temeli

### 4.1 Oyunlaştırmada ses ve çok-duyulu geri bildirim
Sistematik derleme, ses efektlerinin **geri bildirim ve katılımı** güçlendirdiğini, müziğin
motivasyon/biliş üzerinde etkili olduğunu, ancak **dikkatli tasarım** gerektiğini bildirir
(Cao ve ark. 2025, [Consensus](https://consensus.app/papers/details/d7a1406f041a574ba444f773521ca341/)). Görsel ve işitsel öğelerin
**birleştirilmesi** akış (flow) durumunu olumlu etkiler ve katılımcılarca **tercih edilir**
(Schubhan ve ark. 2024, [Consensus](https://consensus.app/papers/details/4d5440b260c85100a53796b9224b9270/)). Kritik uyarı: **alçak-değerlikli/
sert sesler** puan ödüllerinde gerilimi artırır ve **kaçınılmalıdır** (Altmeyer ve ark. 2022,
CHI, [Consensus](https://consensus.app/papers/details/f111f5d2a9ad508bb8a6d168061635ab/)); arka plan müziği yoğunlaşmayı destekleyebilse de
**kişiselleştirilmiş, dikkatli** tasarım ister (de Freitas ve ark. 2024,
[Consensus](https://consensus.app/papers/details/142d4705afeb587b8ac58f86282d3ece/)). Seslendirmeler katılımı artırabilir (Byun ve ark. 2015,
[Consensus](https://consensus.app/papers/details/bd2ee9112bdb5a8780e5d437023c3db8/)); oyunlaştırma genelinde bilişsel etki küçük-ortadır
(Sailer ve ark. 2019, g=.49, [Consensus](https://consensus.app/papers/details/848fef56a8d352b49110b45b36b4e4f2/)).

### 4.2 DEHB ve işitsel uyaran
DEHB'li çocuklar **sürekli/alakasız** işitsel dikkat dağıtıcılara karşı daha kırılgandır;
bu etki çalışma belleği yükü altında belirginleşir (Kong ve ark. 2025,
[Consensus](https://consensus.app/papers/details/94a299afeba758a3b09ef34573f77d1f/); Blomberg 2022, [Consensus](https://consensus.app/papers/details/b9dab9ace23754659fb6a3e06e0b5a89/);
Söderlund ve ark. 2012, [Consensus](https://consensus.app/papers/details/8ffd18690d3b574b8ff6033e8db6ef71/)). Buna karşın **kısa, göreve-ilgisiz YENİ
sesler** dikkat performansını DEHB'de (ve tipik gelişimde) **geçici olarak iyileştirebilir** —
uyarılma/yönelim ağları üzerinden (Tegelbeckers ve ark. 2016,
[Consensus](https://consensus.app/papers/details/b4286a77cc675581ae51171c6770ee2b/); 2022, [Consensus](https://consensus.app/papers/details/d4c812288ea25921bec1ce559dc5af0d/)).
Beyaz gürültünün yararı ise **bireye göre değişir**: orta-beyin-uyarılma modeli uyarınca bazı
(daha dikkatsiz profilli) çocukları desteklerken hiperaktif/dürtüsel profili ve tipik gelişen
çocukları olumsuz etkileyebilir (Söderlund ve ark. 2024, [Consensus](https://consensus.app/papers/details/708c254103715895897a682d65904240/);
Lin 2022, [Consensus](https://consensus.app/papers/details/5f73c4dec64c5bd5b3425f079894c4fd/); Chen ve ark. 2022,
[Consensus](https://consensus.app/papers/details/cbd95eeeb4cb5bada88fc99ce0dde9ec/); Baijot ve ark. 2016, [Consensus](https://consensus.app/papers/details/0214cdf3b9d15535abe5f9d9eed677e3/)).

### 4.3 Tasarıma çevirisi
Bu kanıt birlikte şu tasarımı meşrulaştırır: **kısa, hoş-değerlikli, görselle eşli olay-earcon'ları**
(yeni-ses uyarılma yararı + çok-duyulu tercih); **sürekli arka plan müziği/gürültüsü YOK**
(bireysel değişkenlik + dağıtıcılık riski); **opsiyonel + kolay susturma + düşük ses +
reduced-motion'da varsayılan kapalı** (bireysel farklar ve duyusal yük). "Yanlış" earcon'unun
nazik/alçak tutulması, düşük-değerlikli ses uyarısıyla (Altmeyer 2022) ve duygu-düzenleme
kırılganlığıyla (bkz. `adhd-pedagogy.md` §3) tutarlıdır.

> Not: Bu kanıt eğitim/klinik literatüründendir (Consensus üzerinden erişilen hakemli
> çalışmalar). Doğrulama: `scripts/validate_module.py` **G-AUDIO** kapısı — ses varsa
> susturma kontrolü + reduced-motion + autoplay/loop yokluğunu zorunlu kılar.

## 5. Sesli okuma alt-sistemi (TTS) — v1.8.0

Earcon katmanından ayrı, ikinci ve **tamamen opsiyonel** bir işitsel katman: tarayıcının
`speechSynthesis` API'siyle metni sesli okuma. Earcon "olay sinyali" verirken TTS "içerik
erişilebilirliği" sağlar; ikisi farklı amaçlara hizmet eder ve G-AUDIO'da ayrı denetlenir.

### 5.1 Tasarım ilkeleri
- **Varsayılan KAPALI, talep-üzerine.** Üst çubukta kulaklık düğmesi (`#ttsBtn`); `data-tts="off"`
  başlangıç değeriyle açılır. **Otomatik okuma yoktur** — hiçbir metin kullanıcı istemeden seslenmez.
- **"Oku" düğmeleri** yalnız TTS açıkken görünür (`[data-tts="on"] .tts-oku`): `teach` anlatımı,
  soru kökü, `gloss`, `dialogue` ve `flashcard` arkası. Tek bir olay delegasyonu (`[data-speak]`).
- **Durdurulabilir.** Aynı düğmeye yeniden basınca okuma durur; mod kapatılınca `speechSynthesis.cancel`
  ile tüm okuma iptal edilir; yeni okuma öncesi önceki iptal edilir (üst üste binme yok).
- **Dil otomatik, geçersiz-kılınabilir.** Öğretim metni öğretim dilinde (`meta.ttsLang` || `tr-TR`);
  hedef-dil içeriği ders konusundan türetilir (Fransızca→`fr-FR`, İngilizce→`en-US`) ya da
  `spec.lang` / `card.lang` ile ayrı verilir. Okuma hızı öğrenenler için hafif yavaştır (varsayılan 0.95).
- **Görselle çelişmez, görseli değiştirmez.** TTS açmak/kapamak quiz ilerlemesini etkilemez (yeniden
  render yok); metin daima ekranda kalır — ses **eşlik eder**, yerine geçmez.

### 5.2 Kanıt temeli
Metin-konuşma / sesli-okuma araçları, okuma güçlüğü olan öğrencilerde okuduğunu anlamayı destekler:
bir meta-analiz TTS/sesli-okuma araçlarının okuduğunu anlamada ortalama olumlu bir etki bildirir
(ağırlıklı etki büyüklüğü ≈ .35; %95 GA .14–.56) ([Wood ve ark. 2017, TTS meta-analizi, *J Learn Disabil*](https://consensus.app/papers/details/89d12d947e22529d8487d1a570c933f8/)).
8–12 yaş okuma/dil güçlüğü olan çocuklarda TTS, TTS'siz okumaya kıyasla anlamayı anlamlı biçimde
yükseltmiş; vurgulama (highlighting) olan ve olmayan TTS arasında anlamlı fark çıkmamıştır
([Keelor ve ark. 2023, *Ann Dyslexia*](https://consensus.app/papers/details/a8758195bdf151ef817da94a54b49620/)).
Sesli okuma ile yazılı metni eşleştirmenin yararı **işitsel-görsel bütünleşme** kuramıyla açıklanır;
gaze-contingent bir sesli-okuma aracı disleksili çocuklarda anlamayı %24 artırmış, en yanlış okuyanlar
daha çok yararlanmıştır ([Schiavo ve ark. 2021, *J Comput Assist Learn*](https://consensus.app/papers/details/d6e72faf112f568d8361941666017593/)).
TTS bir **telafi (compensatory)** aracı olarak okuma hızını, akıcılığı ve içerik tutmayı iyileştirir,
öz-yeterlik ve motivasyonu artırır ([Raffoul ve ark. 2023, *Can J Learn Technol*](https://consensus.app/papers/details/bfc63bda67ec5b69be45179546e1672e/);
[Svensson ve ark. 2019, AT etkileri](https://consensus.app/papers/details/133e71a4cbbe56e0810295c2a9c9fa0b/)).

### 5.3 Dürüst denge / uyarı
TTS **herkese tek-beden değildir**: bir çalışmada yalnızca disleksik profilli (dinleme-anlaması
çözümlemesinden yüksek) öğrenciler anlamlı kazanç göstermiş, diğer profiller göstermemiştir
([Silvestri ve ark. 2021, *J Spec Educ Technol*](https://consensus.app/papers/details/7ff9500611b55dc2b3f5c7487c50dfb8/)).
Ayrıca TTS, **öğretmen öğretiminin yerine değil tamamlayıcısı** olarak en yararlıdır; bir çalışmada
insan okuyucu, dinleme-anlamada sentetik sesi geçmiştir ([Brunow ve ark. 2021, *Computers in the Schools*](https://consensus.app/papers/details/cf934cd5bb5f57488209584799edcf33/)).
Bu nedenle carbon-edupedia'da TTS **opsiyonel, varsayılan kapalı, kullanıcı-denetimli** bir destektir;
metni gizlemez ve otomatik okumaz — birey farklılığını ve "destek, ikame değil" ilkesini onurlandırır.

> Doğrulama: G-AUDIO kapısı v1.8.0'da iki-katmanlıdır. TTS kullanılıyorsa `toggleTTS`/`#ttsBtn`
> kullanıcı kontrolü, `speechSynthesis.cancel` ile durdurma ve `data-tts="off"` varsayılanı
> **zorunludur**; eksikse FAIL. Bu kanıt eğitim/klinik literatüründendir (Consensus üzerinden
> erişilen hakemli çalışmalar).
