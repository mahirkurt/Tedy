# DEHB-Odaklı Öğretim Tasarımı — Kanıt Tabanı ve Tasarım İlkeleri

> Bu dosya `carbon-edupedia` yetkinliğinin **entelektüel çekirdeğidir**. Her modül
> üretiminden önce okunmalıdır. Aşağıdaki her tasarım ilkesi, belirtilen
> kuramsal/ampirik kaynaklara bağlıdır. İlkeler, modülün `MODULE_DATA` planına ve
> etkileşim seçimine doğrudan çevrilir (bkz. §9 Uygulama Köprüsü).

## İçindekiler
1. DEHB'nin nöro-bilişsel modelleri (neden farklı öğretmeliyiz)
2. Sekiz çekirdek tasarım ilkesi (her biri kaynaklı)
3. Yarışma/ödül mekaniğinin etik sınırları
4. Yaş ve müfredat çerçevesi (ortaokul, ~12 yaş)
5. Erişilebilirlik ve nörofarklılık örtüşmesi
6. Ölçme: ustalık (mastery) ve öz-izleme
7. Tuzaklar (anti-patterns)
8. Kaynakça
9. Uygulama köprüsü (ilke → modül kararı)

---

## 1. DEHB'nin nöro-bilişsel modelleri

DEHB öğretim tasarımı, bozukluğun yalnız "dikkatsizlik" değil, çok-yollu bir
**öz-düzenleme ve motivasyon** farklılığı olduğu kavrayışına dayanır. Üç model
tasarımı yönlendirir:

- **Yürütücü işlev / davranışsal inhibisyon modeli (Barkley).** DEHB, davranışsal
  inhibisyon eksikliğinin yürütücü işlevleri (çalışma belleği, duyguların öz-
  düzenlenmesi, içselleştirilmiş konuşma, yeniden yapılandırma) ikincil olarak
  bozduğu bir tablodur. Barkley'in vurgusu: yürütücü işlev bir "bilme" değil,
  bir **performans** sorunudur — çocuk *ne* yapacağını bilir ama *o an* yapamaz.
  Tasarım sonucu: yürütücü işlevi **dışsallaştır** (görünür hedefler, ilerleme
  rayı, görünür zaman, bölünmüş adımlar). [Barkley 1997; Barkley 2015]

- **Çift-yol modeli (Sonuga-Barke).** İki nispeten bağımsız yol: (a) yürütücü
  işlev bozukluğu, (b) **motivasyonel yol / gecikme itimi (delay aversion)** —
  gecikmeli ödüle karşı isteksizlik. Çocuk gecikmiş büyük ödül yerine ani küçük
  ödülü yeğler. Tasarım sonucu: ödül **gecikmesiz** ve **sık** verilir; uzun
  vadeli kazanım kısa döngülere bölünür. [Sonuga-Barke 2002, 2003]

- **Optimal uyarılma / aşağı-uyarılma kuramı.** DEHB beyni belirli görevlerde
  yetersiz uyarılır; sıkıcı/tekrarlı görevlerde performans düşer, yenilik ve
  uyaran performansı toparlar. Tasarım sonucu: **temiz ama uyarıcı** arayüz —
  dikkat dağıtıcıyı azalt (düşük dış yük) ama yenilik/renk/hareket/etkileşimle
  uyarılmayı koru. Bu, Carbon'un berrak yapısı ile canlı aksan/piktogram/hareket
  dengesinin neden ideal olduğunu açıklar. [Sergeant 2005 — kognitif-enerjetik
  model; Zentall & Zentall 1983]

Bu modeller birlikte, tek bir çıkarımı zorunlu kılar: **bilgiyi yoğun bloklar
hâlinde sunup pasif okuma beklemek DEHB'de başarısız olur.** Bilgi parçalanmalı,
etkileşimle dokunmalı, anında ödüllenmeli ve yürütücü destekle çerçevelenmelidir.

---

## 2. Sekiz çekirdek tasarım ilkesi

### İlke 1 — Parçalama ve mikro-öğrenme (Chunking)
Her öğretim segmenti **tek bir kazanıma** odaklanır ve ~3–6 dakikalık bilişsel
yükü aşmaz. Bilişsel yük kuramı: çalışma belleği sınırlıdır; DEHB'de bu sınır
işlevsel olarak daha kısıtlıdır. İçeriği küçük, kendi içinde tam birimlere böl;
her birimin sonunda etkileşim/ödül yerleştir. [Sweller 1988; Sweller, Ayres &
Kalyuga 2011]
- **Modül kararı:** `MODULE_DATA.segments` dizisinde hiçbir `teach` segmenti tek
  ekranda 4–6 kısa paragrafı/maddeyi aşmaz; aşıyorsa böl.

### İlke 2 — Sık aktif yanıtlama (High Opportunities to Respond, OTR)
Öğrenci ne kadar sık aktif yanıt verirse (tıklama, seçme, eşleştirme), dikkat ve
öğrenme o kadar artar; pasif dinleme/okuma DEHB'de en zayıf moddur. Sınıf
araştırmaları yüksek OTR oranının (dakikada birden fazla yanıt fırsatı) görev-içi
davranışı ve doğru yanıtı belirgin artırdığını gösterir. [DuPaul & Stoner 2014;
Council for Exceptional Children — yüksek-kaldıraçlı uygulamalar]
- **Modül kararı:** İki `teach` segmenti arasına **mutlaka** en az bir etkileşim
  segmenti girer; saf okuma zinciri yasaktır.

### İlke 3 — Anında ve sık geri bildirim + ödül
Gecikme itimi ve dopaminerjik ödül farklılığı nedeniyle geri bildirim **anında**
verilmeli; ödül (XP, rozet, ilerleme) gecikmesiz ve görünür olmalı. Anında
düzeltici geri bildirim hatayı kalıcı öğrenmeye çevirir. [Sonuga-Barke 2003;
retrieval+feedback: Roediger & Karpicke 2006]
- **Modül kararı:** Her yanıttan sonra anında doğru/yanlış + **açıklama** göster;
  XP'yi o anda artır; ilerleme rayını güncelle. Toplu/sonda geri bildirim yetmez.

### İlke 4 — Yürütücü işlev dışsallaştırma
DEHB bir performans bozukluğu olduğundan, yürütücü desteği ortama göm: açık
öğrenme hedefleri (başta), **görünür ilerleme** (nerede olduğum/ne kadar kaldığı),
**görünür zaman** (DEHB'de zaman algısı bozuktur — opsiyonel sayaç), adım-adım
yapı, "sonraki adım" yönlendirmesi. [Barkley 2015; Meltzer 2018 — yürütücü
işlev ve öğrenme]
- **Modül kararı:** Üstte sabit ilerleme rayı + segment sayacı; başta hedef
  listesi ("Bu modülde…"); her segment sonunda net "Devam" eylemi.

### İlke 5 — Düşük dış yük ↔ yüksek uyarılma dengesi
Dikkat dağıtıcı öğeleri (gereksiz süs, yanıp sönme, kalabalık ekran) azalt;
**aynı anda tek görev** göster. Ama monotonluktan kaçın: yenilik, kategori-renk,
piktogram, ölçülü hareket ile uyarılmayı koru. [Zentall 1975; Sergeant 2005;
çoklu temsil için aşağıda İlke 7]
- **Modül kararı:** Ekran başına tek odak; Carbon beyaz/katman zemini; aksan
  rengi anlam taşır (kategori/durum), dekor değil; hareket `prefers-reduced-motion`
  ile kapatılabilir.

### İlke 6 — Özerklik, yeterlik, ilişkililik (Öz-belirleme kuramı)
İçsel motivasyon üç ihtiyacın doyumuyla artar: **özerklik** (seçim),
**yeterlik** (ulaşılabilir başarı), **ilişkililik** (sıcak, teşvik edici ton).
Dışsal ödül (XP/rozet) içsel motivasyonu desteklemeli, yerine geçmemeli — bu
yüzden ödül *bilgilendirici* (ilerleme/ustalık geri bildirimi) olmalı, *kontrol
edici* değil. [Deci & Ryan 1985, 2000; Ryan & Deci 2020]
- **Modül kararı:** Mümkünse yol/konu seçtir (SERIES/menü); zorluğu kademeli
  yükselt (erken başarı garanti); ton teşvik edici; rozet "ustalık" anlatır.

### İlke 7 — Çoklu temsil ve ikili kodlama (UDL + Dual Coding)
Bilgi hem **görsel** hem **sözel** kodlandığında daha iyi hatırlanır (ikili
kodlama). Evrensel Tasarım (UDL) çoklu temsil/katılım/ifade yollarını şart koşar;
DEHB ve diğer nörofarklılıklar için kapsayıcıdır. Bu, kullanıcının "bol görsel,
ikon, piktogram, SVG" talebinin pedagojik temelidir. [Paivio 1986; Mayer 2009 —
çoklu ortam öğrenme ilkeleri; CAST UDL Guidelines 2018]
- **Modül kararı:** Her kavramı sözel + görsel sun (piktogram/şema/SVG);
  anahtar terimleri görsel işaretle; karmaşık süreçleri etiketli SVG diyagramla.

### İlke 8 — Geri-getirme pratiği ve aralıklı tekrar (Retrieval & Spacing)
Bilgiyi yeniden okumak değil, **hatırlamaya çalışmak** (test etkisi) kalıcılığı
artırır; tekrarlar zamana yayıldığında (spacing) etki güçlenir. Quiz/flashcard
sadece "ölçme" değil, **öğretme** aracıdır. [Roediger & Karpicke 2006; Cepeda
ve ark. 2006; Dunlosky ve ark. 2013 — en etkili teknikler: pratik test + aralıklı
tekrar]
- **Modül kararı:** Quiz'leri öğretimin *parçası* yap; FLASHCARDS modunda
  aralıklı tekrar mantığı (biliyorum→ertele, bilmiyorum→yakında tekrar);
  modül sonunda karma "geri-getirme" kontrol noktası.

---

## 3. Yarışma / ödül mekaniğinin etik sınırları

Oyunlaştırma motive eder ama yanlış kurgulanırsa zarar verir (kaygı, dışsal
motivasyona bağımlılık, utandırma). Kanıt: oyunlaştırmanın etkisi bağlama ve
tasarıma bağlıdır; "rozet/puan/sıralama" üçlüsü tek başına garanti değildir.
[Hamari, Koivisto & Sarsa 2014; Deterding ve ark. 2011; Sailer & Homner 2020 —
meta-analiz: olumlu ama orta etkili, tasarıma duyarlı]

**Kurallar:**
- **Öz-rekabet önceliklidir.** Yarışma kişisel rekora (önceki skoru geçme) veya
  düşük-baskılı, isteğe bağlı sıralamaya dayanır. Akran utandıran küresel
  liderlik tablosu **varsayılan değildir**.
- **Ceza yok.** Yanlış yanıt XP düşürmez/"can" almaz biçimde cezalandırılmaz;
  düzeltici açıklama + tekrar fırsatı sunulur. (Gecikme itimi olan çocukta ceza
  kaçınma davranışını tetikler.)
- **Ödül bilgilendiricidir.** Rozet/XP ilerleme ve ustalığı anlatır; performansı
  "kontrol" eden bir sopa-havuç değildir (Öz-belirleme kuramı, İlke 6).
- **Erken başarı garanti.** İlk etkileşimler kolaydır (yeterlik duygusu); zorluk
  kademeli artar (akış / Zone of Proximal Development). [Vygotsky 1978;
  Csikszentmihalyi 1990 — akış]
- **Süre opsiyoneldir.** Sayaç motive edebilir ama kaygı yaratabilir; varsayılan
  kapalı veya kapatılabilir. DEHB'de zaman görünürlüğü destek olabilir ama baskı
  olmamalı.

---

## 4. Yaş ve müfredat çerçevesi (~12 yaş, ortaokul)

- **Bilişsel düzey:** Somut işlemlerden soyut işlemlere geçiş (Piaget). Soyut
  kavramlar **somut görsel/analoji** ile desteklenmeli; saf soyutlama erken.
  [Piaget; ama katı evre yorumundan kaçın — bireysel değişkenlik yüksek]
- **Dil:** Yaşa uygun, net, sıcak Türkçe. Cümleler kısa-orta; terimler tanımlı
  ve görsel destekli. Kaynak terminolojisi korunur ama açıklanır.
- **Süre:** Tek oturum 15–25 dk hedef; daha uzunsa SERIES'e böl. DEHB'de oturum
  içi mola (brain-break) ~her 8–10 dk.
- **Müfredat hizalama:** Türkiye MEB ortaokul müfredatı kazanımlarıyla
  ilişkilendirilebilir; ama yetkinlik **kaynak-temelli**dir — kazanım metni veya
  ders materyali kullanıcı tarafından sağlanır. (Işık gibi Frankofon müfredatta
  ise içerik dili buna göre `francais-coach` ile köprülenir.)

---

## 5. Erişilebilirlik ve nörofarklılık örtüşmesi

DEHB-dostu tasarım, daha geniş erişilebilirlikle örtüşür ve onu zorunlu kılar:
- **Klavye + ekran okuyucu:** Tüm etkileşimler klavyeyle yapılabilir; ARIA
  rolleri/etiketleri doğru. [WCAG 2.1 AA; WAI-ARIA Authoring Practices]
- **Hareket duyarlılığı:** `prefers-reduced-motion` ile tüm animasyon kapatılır
  (vestibüler bozukluk + dikkat). Yanıp sönme/parıltı **yasak** (foto-duyarlılık).
- **Disleksi örtüşmesi:** Yeterli satır aralığı, sol hizalı metin, net font
  (IBM Plex iyi okunur), uzun bloklardan kaçınma. (DEHB ve disleksi sık birlikte.)
- **Kontrast:** Metin/zemin ≥ 4.5:1 (normal), ≥ 3:1 (büyük). Renk tek başına
  anlam taşımaz (durum hem renk hem ikon/metinle).
- **Dokunma hedefi:** ≥ 44×44 px (motor + dürtüsellik). [WCAG 2.5.5]

---

## 6. Ölçme: ustalık (mastery) ve öz-izleme

- **Ustalık öğrenmesi (Bloom).** İlerleme "tamamlama" değil **ustalık** ile
  ölçülür; bir kazanımda eşik altı kalan öğrenci nazikçe tekrara yönlendirilir
  (ceza değil). [Bloom 1968 — Learning for Mastery; Guskey 2010]
- **Öz-izleme / üstbiliş.** Modül sonunda öğrenci kendi öğrenmesini işaretler
  ("Bunu öğrendim / tekrar etmeliyim"); bu üstbilişsel beceri DEHB'de zayıftır,
  dolayısıyla *dışsal* desteklenmelidir. [Meltzer 2018; Dunlosky 2013]
- **Çıktı:** Özet ekranı: ulaşılan ustalık, kazanılan rozetler, tekrar önerisi,
  öz-değerlendirme. Skor *bilgilendirici* sunulur, etiketleyici değil.

---

## 7. Tuzaklar (Anti-patterns) — bunlardan kaçın

- **Bilgi duvarı:** Uzun, bölünmemiş metin blokları. → Parçala (İlke 1).
- **Pasif zincir:** Arka arkaya okuma, etkileşimsiz. → OTR ekle (İlke 2).
- **Gecikmiş ödül:** Geri bildirim/ödülü sona saklamak. → Anında ver (İlke 3).
- **Ceza mekaniği:** Can kaybı, XP düşürme, "kaybettin" ekranı. → Yasak (§3).
- **Aşırı uyaran:** Yanıp sönen, kalabalık, parlak kaos. → Temiz + ölçülü (İlke 5).
- **Emoji bağımlılığı:** Anlamı emojiyle taşımak. → Carbon ikon/piktogram/SVG.
- **Soyut-only:** Görselsiz soyut anlatım. → İkili kodlama (İlke 7).
- **Kaynak uydurma:** Eksik kaynağı uydurmayla doldurma. → SKILL.md §7 (sadakat).
- **Tek-beden:** Sabit zorluk. → Kademeli + seçim (İlke 6).

---

## 8. Kaynakça (seçilmiş, hakemli/standart)

- Barkley, R. A. (1997). *Behavioral inhibition, sustained attention, and executive
  functions: Constructing a unifying theory of ADHD.* Psychological Bulletin, 121(1).
- Barkley, R. A. (2015). *Attention-Deficit Hyperactivity Disorder: A Handbook for
  Diagnosis and Treatment* (4th ed.). Guilford Press.
- Sonuga-Barke, E. J. S. (2002, 2003). *The dual pathway model of AD/HD.* Behavioural
  Brain Research / Neuroscience & Biobehavioral Reviews.
- Sergeant, J. A. (2005). *Modeling attention-deficit/hyperactivity disorder: A
  critical appraisal of the cognitive-energetic model.* Biological Psychiatry.
- Zentall, S. S. (1975; & Zentall, 1983). *Optimal stimulation theory and ADHD.*
- DuPaul, G. J., & Stoner, G. (2014). *ADHD in the Schools: Assessment and Intervention
  Strategies* (3rd ed.). Guilford Press.
- Sweller, J. (1988); Sweller, Ayres & Kalyuga (2011). *Cognitive Load Theory.* Springer.
- Paivio, A. (1986). *Mental Representations: A Dual Coding Approach.* Oxford.
- Mayer, R. E. (2009). *Multimedia Learning* (2nd ed.). Cambridge University Press.
- CAST (2018). *Universal Design for Learning Guidelines v2.2.* udlguidelines.cast.org.
- Deci, E. L., & Ryan, R. M. (1985, 2000); Ryan & Deci (2020). *Self-Determination
  Theory.* Contemporary Educational Psychology.
- Roediger, H. L., & Karpicke, J. D. (2006). *Test-enhanced learning.* Psychological
  Science.
- Cepeda, N. J. ve ark. (2006). *Distributed practice: A meta-analysis.* Psychological
  Bulletin.
- Dunlosky, J. ve ark. (2013). *Improving students' learning with effective learning
  techniques.* Psychological Science in the Public Interest.
- Hamari, Koivisto & Sarsa (2014). *Does gamification work? A literature review.* HICSS.
  Sailer & Homner (2020). *The gamification of learning: a meta-analysis.* Educational
  Psychology Review.
- Vygotsky, L. S. (1978). *Mind in Society* (ZPD). Csikszentmihalyi, M. (1990). *Flow.*
- Bloom, B. S. (1968). *Learning for Mastery.* Guskey, T. (2010). *Mastery learning.*
- Meltzer, L. (2018). *Executive Function in Education* (2nd ed.). Guilford.
- WCAG 2.1 (W3C); WAI-ARIA Authoring Practices Guide (W3C).
- Klinik bağlam: APA DSM-5-TR (2022); NICE NG87 (ADHD, 2018, güncel.); AAP Clinical
  Practice Guideline for ADHD (Wolraich ve ark. 2019, Pediatrics).

> **Not:** Yukarıdaki kaynaklar tasarım ilkelerinin gerekçesidir. Modülün **konu
> içeriği** ise her zaman kullanıcının sağladığı **ders kaynağından** gelir
> (SKILL.md §7). Bu iki kaynak türünü karıştırma.

---


**Klinik kanıt (PubMed; medical-research v7.1 ile derlendi, 2026):**
- Thorell LB ve ark. (2022). Longitudinal digital media & ADHD: systematic review. *Eur Child Adolesc Psychiatry*. https://doi.org/10.1007/s00787-022-02130-3
- Rodrigo-Yanguas M ve ark. (2022). Serious Video Games in ADHD: angels or demons? *Front Psychiatry*. https://doi.org/10.3389/fpsyt.2022.798480
- Eirich R ve ark. (2022). Screen time & internalizing/externalizing problems (meta-analiz). *JAMA Psychiatry*. https://doi.org/10.1001/jamapsychiatry.2022.0155
- Groves NB ve ark. (2021). Executive functioning & emotion regulation in ADHD. *Res Child Adolesc Psychopathol*. https://doi.org/10.1007/s10802-021-00883-0
- Tripp G, Wickens JR (2009). Neurobiology of ADHD (gecikmeli pekiştirme). *Neuropharmacology*. https://doi.org/10.1016/j.neuropharm.2009.07.026
- Wu F ve ark. (2024). Stimulants normalize attention/reward regions. *Neuropsychopharmacology*. https://doi.org/10.1038/s41386-024-01831-4
- Zhu F ve ark. (2023). Physical exercise & executive functions (ağ meta-analizi). *Front Public Health*. https://doi.org/10.3389/fpubh.2023.1133727
- Qiu H ve ark. (2023). Non-pharmacological interventions & EF (SR-MA). *Asian J Psychiatry*. https://doi.org/10.1016/j.ajp.2023.103692
- Zhao L ve ark. (2024). BrainFit gamified cognitive-physical RCT. *J Med Internet Res*. https://doi.org/10.2196/55569
- Cibrian FL ve ark. (2024). Digital assessments for ADHD: scoping review. *Front Digit Health*. https://doi.org/10.3389/fdgth.2024.1440701


**Ek üçgenleme (PubMed; Consensus/Scholar Gateway erişilemedi, 2026):**
- Broad AA ve ark. (2021). Classroom Activity Breaks & On-Task Behavior (RCT). *Res Q Exerc Sport*. https://doi.org/10.1080/02701367.2021.1980189
- Ruhland S, Lange KW (2021). Classroom-based PA & attention/on-task (SR). *Sports Med Health Sci*. https://doi.org/10.1016/j.smhs.2021.08.003
- Donnelly JE ve ark. (2016). PA, fitness, cognition & academic achievement (ACSM SR). *Med Sci Sports Exerc*. https://doi.org/10.1249/MSS.0000000000000901
- Weinstein A, Lejoyeux M (2020). Neurobiology of internet gaming disorder. *Dialogues Clin Neurosci*. https://doi.org/10.31887/DCNS.2020.22.2/aweinstein
- Schou Andreassen C ve ark. (2016). Addictive social media/gaming & psychiatric symptoms (N=23,533). *Psychol Addict Behav*. https://doi.org/10.1037/adb0000160
- Marin MG ve ark. (2020). Internet Addiction & Attention in Adolescents (SR). *Cyberpsychol Behav Soc Netw*. https://doi.org/10.1089/cyber.2019.0698
- Brand M ve ark. (2024). Behavioral Addictions: research to practice (review). *Am J Psychiatry*. https://doi.org/10.1176/appi.ajp.20240092


**İşlevsel renk / ipucu kanıtı (PubMed):**
- Superbia-Guimarães L ve ark. (2022). Attentional Orienting in Working Memory in Children with ADHD. *Dev Neuropsychol*. https://doi.org/10.1080/87565641.2022.2155164
- Wu KK, Anderson V, Castiello U (2006). ADHD and working memory: a task switching paradigm (Stroop). *J Clin Exp Neuropsychol*. https://doi.org/10.1080/13803390500477267

## 9. Uygulama köprüsü — İlke → modül kararı (hızlı tablo)

| İlke | `MODULE_DATA` / motor kararı |
|---|---|
| 1 Parçalama | `teach` segmentleri kısa; uzun konu çok segmente bölünür |
| 2 OTR | `teach`–`teach` arası ≥1 etkileşim; saf okuma zinciri yok |
| 3 Anında ödül | Yanıt sonrası anında doğru/yanlış+açıklama; XP/ray güncellenir |
| 4 Yürütücü destek | Üstte ilerleme rayı + sayaç; başta hedefler; net "Devam" |
| 5 Yük/uyarılma | Tek-odak ekran; aksan=anlam; reduced-motion; yanıp sönme yok |
| 6 Özerklik/yeterlik | Yol/konu seçimi; kademeli zorluk; bilgilendirici rozet |
| 7 İkili kodlama | Her kavram görsel+sözel; etiketli SVG/piktogram |
| 8 Geri-getirme | Quiz=öğretim aracı; FLASHCARDS aralıklı tekrar; sonda karma kontrol |
| §3 Etik | Ceza yok; öz-rekabet; erken başarı; süre opsiyonel |
| §5 Erişilebilirlik | Klavye+ARIA; kontrast AA; ≥44px hedef; renk tek başına anlam değil |

## 10. Klinik kanıt temelli özen ilkeleri (medical-research ile derlenen)

> Bu bölüm, `medical-research` protokolüyle **PubMed** üzerinden taranan hakemli
> kanıta dayanır (atıflar DOI bağlantılıdır). DEHB'ye yönelik **etkileşimli dijital
> öğrenim materyali** tasarımında özen gösterilmesi gereken hususları ve her birinin
> `carbon-edupedia` motorundaki karşılığını eşler. Kanıt düzeyleri Tier 0–3 (sistematik
> derleme/meta-analiz > RCT > gözlemsel/mekanistik) olarak işaretlenmiştir.

| # | Özen ilkesi (kanıt) | Kanıt (PubMed; DOI) | Düzey | Motordaki karşılık |
|---|---|---|---|---|
| Ö1 | **Aşırı/problemli kullanım yatkınlığı** — DEHB'li çocuklar hem problemli dijital medya kullanımına daha yatkın hem de medya sonradan DEHB semptomlarını etkileyebilir (çift yönlü); zarar "ekran süresi"nden çok **problemli kullanım** ile ilişkili. Ciddi oyunlar yardımcı olsa da aynı popülasyonda **oyun bağımlılığı** riski vardır. | Thorell 2022 (Eur Child Adolesc Psychiatry) [DOI](https://doi.org/10.1007/s00787-022-02130-3); Rodrigo-Yanguas 2022 (Front Psychiatry) [DOI](https://doi.org/10.3389/fpsyt.2022.798480); Eirich 2022 (JAMA Psychiatry) [DOI](https://doi.org/10.1001/jamapsychiatry.2022.0155) | Tier 0–1 | Sınırlı/öngörülebilir oturum; **nazik mola hatırlatıcı** (`breakReminderMin`); **sağlıklı kapanış** (özet "bugünlük yeterli", "başka modül" baskısı yok); **sabit-cetvel XP** (kumar-benzeri değişken ödül yok); otomatik-ilerleme/otomatik-oynatma yok; varsayılan süre baskısı yok; **G-WELLBEING** kapısı |
| Ö2 | **Çalışan bellek (ÇB) yükünü en aza indir** — ÇB defisiti DEHB'de merkezîdir ve duygu-düzenlemeyi de yordar; birinci-basamak tedaviler ÇB'yi hedeflemez. | Groves 2021 (Res Child Adolesc Psychopathol) [DOI](https://doi.org/10.1007/s10802-021-00883-0) | Tier 3 | Ekran başına **tek görev**; soru kökü yanıtlanırken ekranda kalır; parçalama (İlke 1/4); çok-adımlı, akılda-tutmalı yönerge yok |
| Ö3 | **Anında, sık, ÖNGÖRÜLEBİLİR pekiştirme; gecikmeli ödülden kaçın** — gecikmeye duyarlılık güvenilir bir bulgudur (dopamin "transfer" defisiti); ödül/saliyans bölgelerinde yapısal atipiklik. Dış ödülü tek itki yapmamaya özen göster. | Tripp & Wickens 2009 (Neuropharmacology) [DOI](https://doi.org/10.1016/j.neuropharm.2009.07.026); Wu 2024 (Neuropsychopharmacology) [DOI](https://doi.org/10.1038/s41386-024-01831-4) | Tier 3–4 | Öğe-başına **anında** geri bildirim; **sabit-cetvel** XP (değişken-oran değil); ustalık + öz-değerlendirme (içsel motivasyon, İlke 6); yanlışta ceza yok |
| Ö4 | **Hatada ceza yok; başarısızlık → nazik tekrar** — DEHB'de duygu-düzenleme kırılganlığı ÇB ile bağlantılıdır; başarısızlık/etiketleme dili kaçınılmalı. | Groves 2021 [DOI](https://doi.org/10.1007/s10802-021-00883-0) | Tier 3 | "Ceza yok" ilkesi her etkileşimde; ipucu + tekrar; etiketleyici-olmayan özet (<%70 → nazik tekrar daveti); **G-WELLBEING** cezalandırıcı/süre-baskısı dilini FAIL eder |
| Ö5 | **Hareket/mola; keyifli, açık-beceri etkinlik EF'yi ve uyumu artırır** — fiziksel egzersiz (özellikle açık-beceri) yürütücü işlevleri belirgin iyileştirir; uyum için **çocuğun en sevdiği** etkinlik teşvik edilmeli. | Zhu 2023 (Front Public Health, ağ meta-analizi) [DOI](https://doi.org/10.3389/fpubh.2023.1133727); Qiu 2023 (Asian J Psychiatry, SR-MA) [DOI](https://doi.org/10.1016/j.ajp.2023.103692) | Tier 0 | **brainbreak** segmentleri (hareket yönergeli); uzun modülde mola kuralı (**G-WELLBEING** WARN, ped §4); çeşitli/keyifli etkileşim türleri (uyum) |
| Ö6 | **Yapılandırılmış, EF-hedefli, kaynağa-sadık öğretim** — oyunlaştırma yardımcı olabilir; en güçlü kanıt **EF-müfredatı + bilişsel/oyun-temelli** yapılandırılmış programlardadır (RCT'de semptom + EF iyileşmesi, ciddi advers olay yok). | Qiu 2023 [DOI](https://doi.org/10.1016/j.ajp.2023.103692); Zhao 2024 BrainFit RCT (J Med Internet Res) [DOI](https://doi.org/10.2196/55569) | Tier 0–2 | Kaynak-sadakati (§7); yapılandırılmış akış (teach → etkileşim → checkpoint); EF dışsallaştırma (stepper, tek-görev) |
| Ö7 | **Kullanıcı-merkezli, yetenek-temelli, erişilebilir tasarım; çocukla birlikte tasarla** — alan, katılımcı ve yetenek-temelli çerçeveler ile paydaşların erken katılımını vurgular. | Cibrian 2024 (Front Digit Health, kapsam derlemesi) [DOI](https://doi.org/10.3389/fdgth.2024.1440701) | Tier 1 | WCAG 2.1 AA (**G-A11Y**); klavye/dokunma; `prefers-reduced-motion`; disleksi-örtüşmesi için yazı tipi özeni (§5); gerçek öğreniciyle (Işık) ortak-tasarım |
| Ö8 | **Uyku ve çevrimdışı/sosyal yaşamı koru** — medya etkileri kısmen **uyku** ve **sosyal ilişkiler** üzerinden işler. | Thorell 2022 [DOI](https://doi.org/10.1007/s00787-022-02130-3) | Tier 0–1 | Bakım-veren rehberi (§11): günün erken saati, yatmadan önce değil; öğretmen/aile/akran etkileşiminin **yerine geçmez, tamamlar**; sınırlı oturum; akşam-çekişi/bildirim yok |
| Ö9 | **Aşırı görsel/duyusal uyarımı azalt; tek odak; sakin renk** — düşük dış-yük ↔ uyarılma dengesi (İlke 5) ve dikkat-dağınıklığı ile uyumlu; çeşitlilik **yapılandırılmış olmalı, gürültü değil**. | İlke 5 + Eirich 2022 [DOI](https://doi.org/10.1001/jamapsychiatry.2022.0155) (dışsallaştırma ilişkisi) | Tier 0 / kuram | Sakin Carbon yüzey sistemi (v1.2.1: anlamlı mod-ipucu, gökkuşağı değil); `prefers-reduced-motion`; tek odak görevi; süs-kalabalığı yok |

**Sentez.** Kanıt, `carbon-edupedia`'nın mevcut tasarım felsefesini büyük ölçüde
**doğrular** (anında geri bildirim, parçalama, ceza-yok, mola, erişilebilirlik) ve
en güçlü **yeni** vurguyu **aşırı/problemli kullanım koruması** ile **öngörülebilir
(kumar-benzeri-olmayan) ödül** üzerine ekler — bu nedenle v1.3.0 nazik mola
hatırlatıcısı, sağlıklı kapanış ve G-WELLBEING kapısını getirir. Önemli sınır:
kanıtın çoğu Tier 0–3 olsa da doğrudan "Carbon-stilli HTML modül" üzerinde RCT
yoktur; bulgular **dijital DEHB müdahaleleri** genelinden bu tasarıma aktarılmıştır.

## 10.1 Ek kanıt — mola dozu ve problemli kullanım mekanizması

> Consensus ve Scholar Gateway bağlayıcıları bu oturumda çağrı anında onay
> vermediğinden, Ö1 ve Ö5'i derinleştirmek için **PubMed** üzerinden ek üçgenleme
> yapılmıştır (atıflar DOI'lidir).

**Ö5 — Mola dozu (parametreleştirme).** Sınıf-içi fiziksel aktivite molalarının
dozu artık nicelenebilir: bir RCT, Tabata biçiminde **20 sn iş / 10 sn dinlenme × 8
≈ 4 dakikalık** mola ile görev-üstü davranışın günün her saatinde arttığını
(sabah Δ%10,4; öğleden sonra Δ%10,5; ikisi birden Δ%14) ve en büyük yararın
**başlangıçta en çok dağılan** çocuklarda görüldüğünü; **günde iki mola**nın en
yüksek kazancı verdiğini göstermiştir (Broad ve ark. 2021, *Res Q Exerc Sport*
[DOI](https://doi.org/10.1080/02701367.2021.1980189)). Sistematik derleme, sınıf-içi
aktivite molalarının dikkat ve görev-üstü davranışa yararını doğrular ama yöntem
heterojenliğini vurgular (Ruhland & Lange 2021, *Sports Med Health Sci*
[DOI](https://doi.org/10.1016/j.smhs.2021.08.003)); ACSM duruş-belgesi fiziksel
aktivitenin bilişe yararını "B" düzeyinde destekler, akademik başarı etkisini ise
"C" (karışık) olarak işaretler (Donnelly ve ark. 2016, *Med Sci Sports Exerc*
[DOI](https://doi.org/10.1249/MSS.0000000000000901)). **Tasarım kuralı:** `brainbreak`
`durationSec` değeri **~120–240 sn** ve hareket-yönergeli olmalı; uzun bir modülde
(örn. ≥8 segment veya ~20+ dk) **en az iki** mola dağıtılmalıdır.

**Ö1 — Problemli kullanım: mekanizma, tanım ve tarama.** İnternet oyun bozukluğu
(IGD) madde-bağımlılığına benzer nörobiyoloji paylaşır (ödül bölgelerinde
aktivasyon, dürtü-kontrol/karar-verme zayıflaması, bilişsel-kontrol ağlarında
azalmış bağlantısallık); kritik olarak **DEHB'deki yürütücü-kontrol ağı zayıflığı
IGD geliştirme yatkınlığını artırabilir** (Weinstein & Lejoyeux 2020, *Dialogues
Clin Neurosci* [DOI](https://doi.org/10.31887/DCNS.2020.22.2/aweinstein)). "Bağımlı
kullanım", süreden çok **olumsuz sonuçlarla giden zorlantılı/aşırı kullanım** olarak
tanımlanır ve DEHB belirtileri bu kullanımdaki varyansı açıklar (Schou Andreassen ve
ark. 2016, *Psychol Addict Behav* [DOI](https://doi.org/10.1037/adb0000160)). Ergen
literatüründe en yaygın tarama aracı **Young İnternet Bağımlılığı Testi**'dir ve
problemli kullanım uyku, ağırlık ve saldırganlıkla ilişkilenir (Marin ve ark. 2020,
*Cyberpsychol Behav Soc Netw* [DOI](https://doi.org/10.1089/cyber.2019.0698)).
Nozolojik olarak DSM-5'te yalnızca kumar bozukluğu tanınır; IGD "daha fazla araştırma
gerektiren" durumdur, davranışsal bağımlılıklar DEHB ile sıklıkla birlikte görülür ve
en kanıtlı tedavi **BDT**'dir (Brand ve ark. 2024, *Am J Psychiatry*
[DOI](https://doi.org/10.1176/appi.ajp.20240092)). **Tasarım sonucu:** craving/işaret
(cue) döngüleri ve değişken-oran ödül kullanma; ödülü sabit tut; oturumu sınırla;
bakım-vereni "dakika" değil **olumsuz-sonuç işaretleri** (uyku, sosyal geri çekilme,
işlevsellik) açısından uyar.

## 11. Sorumlu kullanım (bakım-veren/öğretmen notu)

- **Tıbbi cihaz veya tedavi değildir.** `carbon-edupedia` modülleri eğitim-destek
  materyalidir; DEHB tanı/tedavisinin, klinik değerlendirmenin ya da bireyselleştirilmiş
  eğitim planının yerine geçmez (Ö6, Ö8).
- **Tamamlar, yerine geçmez.** Öğretmen, akran ve aile etkileşiminin yerini almamalı;
  ekran-temelli öğrenme çevrimdışı etkinlik ve oyunu **azaltmamalıdır** (Ö8).
- **Sınırlı ve erken.** Kısa oturumlar; mümkünse günün erken saatinde, **yatmadan
  hemen önce değil** (uyku koruması, Ö1/Ö8). `breakReminderMin` nazik bir hatırlatıcıdır.
- **Baskısız.** Süre/yarış baskısı varsayılan olarak kapalıdır; ödül sabittir; "devam
  et" zorlaması yoktur. Çocuğun temposu esastır (Ö1/Ö3).

## 12. İşlevsel renk politikası (renk: dağıtıcı değil, yönlendirici)

DEHB'de **alakasız** görsel karmaşa ve renk, Stroop-tipi girişim ve dış-uyaran
duyarlılığı nedeniyle dikkati dağıtabilir; bu, nötr tuval ve düşük bilişsel yük
gerekçesini destekler (Sweller bilişsel yük; Mayer tutarlılık ilkesi). Ancak renk
**işlevsel** kullanıldığında — yani neye bakılacağını işaretleyen geçerli bir ipucu
olarak — yarar sağlar: çocuklarda geçerli **konum ipuçları** (ön-ipucu ve geri-ipucu)
çalışan bellekte performansı artırır ve bu yarar DEHB'li çocuklarda tipik gelişen
akranlarıyla **aynı** ölçüdedir; yani DEHB'de dikkati yönlendirme (orienting) bozuk
değildir (Superbia-Guimarães ve ark. 2022, *Dev Neuropsychol*
[DOI](https://doi.org/10.1080/87565641.2022.2155164)). Bu, Mayer'in **sinyalleme/işaret
(signaling/cueing)** ilkesiyle örtüşür. Ayrıca DEHB'de **az-uyarılma ve durum
düzenleme** güçlüğü belgelidir; uygun düzeyde yapı ve belirginlik (ne aşırı ne düz)
katılımı destekler, ama aynı görevde renk **alakasızsa** güçlü bir çeldiriciye dönüşür
(Wu, Anderson & Castiello 2006, *J Clin Exp Neuropsychol*
[DOI](https://doi.org/10.1080/13803390500477267)).

**Politika (tasarım kuralları):**
1. **Renk işlevle atanır, süslemeyle değil.** Her renk bir işi temsil eder: eylem
   (mavi buton/bağlantı), durum (Carbon support: başarı/bilgi/uyarı/hata), kategori
   (veri-viz `--viz-1..5`), ilerleme/ödül (sıcak altın `--reward`), **odak çıpası**
   (geçerli adım/seçim/etkin başlık için tek aksan tonu).
2. **Nötr tuval.** Zemin ve yüzeyler Carbon layer token'larıdır; büyük doygun alan yok.
3. **Artıklık (redundancy) + CVD güvenliği.** Renk **tek** ayırt edici olamaz; daima
   metin/ikon/şekil ile birlikte (UDL — çoklu temsil; CAST).
4. **Wayfinding aksanı.** Etkinlik türü (anlatım/quiz/mola/grafik) başlıkta tutarlı bir
   renkle imlenir; çocuk "burada ne yapacağım"ı renkten de okur (sinyalleme).
5. **Sakinlik korunur.** Animasyon tek ve `prefers-reduced-motion` ile kapalı; doygunluk
   ölçülü; kontrast WCAG AA. Renk **daha etkin** ama **daha gürültülü değil**.

## 13. Derse-özel görsel güçlerin kanıt temeli

Derse-özel araçlar (bkz. `subject-packs.md`) keyfi değildir; her biri öğrenme-bilimi kanıtına
dayanır. Tüm araçlar yine §12 işlevsel renk ve sakinlik sınırlarına uyar.

**Fen — etiketli/sinyallenmiş diyagram.** Etiketli illüstrasyonlar açıklayıcı bilgiyi hatırlamayı
ve aktarımı artırır (Mayer 1989, [DOI/Consensus](https://consensus.app/papers/details/f528ed4c778c52e782b762d9fbc04de8/)); metin-şekil
karşılıklarını sinyalleme bütünleştirmeyi destekler (Scheiter ve ark. 2015,
[link](https://consensus.app/papers/details/eb20830300ee5598af3582b2bcbf62f0/)); meta-analizler sinyallemenin (renk-kodu dâhil) küçük-orta
etkisini ve düşük ön-bilgide daha güçlü olduğunu gösterir (Richter ve ark. 2016,
[link](https://consensus.app/papers/details/8b6a5cad1440525dac1d92a1508c2a1a/); Alpizar ve ark. 2020, d≈.38,
[link](https://consensus.app/papers/details/acf7fda6dc485737a4b158c22d2757d0/)). Sade, yapı-vurgulu diyagramlar en iyisidir (Butcher 2006,
[link](https://consensus.app/papers/details/1fe20e33ac2953d1a099507e616ef830/)). Uyarı: genç/İngilizce-öğrenen örneklemde yarar her zaman
yinelenmez; baştan çıkarıcı ayrıntıdan kaçın (McTigue 2009,
[link](https://consensus.app/papers/details/47027d625c045f028df58db35c6d875f/)).

**Sosyal — kavram haritası / grafik düzenleyici.** Meta-analizler tutarlı yarar bildirir
(Schroeder ve ark. 2018, g=0.58; oluşturma g=0.72, [link](https://consensus.app/papers/details/5b2e2d1f20b05887a0d28f8a2249010d/);
Nesbit & Adesope 2006, [link](https://consensus.app/papers/details/be2bc5f0b65059f5843d1a9011102744/); Dexter & Hughes 2011,
[öğrenme güçlüğünde 4–12. sınıf](https://consensus.app/papers/details/fd77e2035aec568599e206836aa786f2/)); tarihte başarı ve ilgiyi artırır (Nair ve ark. 2017,
[link](https://consensus.app/papers/details/c38f5b11bdef52938e610618c08985c2/)); etkileşimli düzenleyiciler daha derin işleme yol açar
(Wang ve ark. 2021, [link](https://consensus.app/papers/details/b27391ed611f5e18960604fb51917cf9/)).

**Dil — renk-kodu + ikili kodlama.** Renk-kodlama dilbilgisel cinsiyet/yapıda etkili ve düşük
emeklidir (Arzt ve ark. 2016, [link](https://consensus.app/papers/details/a04fc7b48f1e5f71affe9955e4469946/); Kostiuk 2025 derleme, %30–45
daha hızlı tanıma, [link](https://consensus.app/papers/details/548429910bc85764bf2d723497def7c4/); Aljehani 2022, İngilizce artikel,
[link](https://consensus.app/papers/details/a0f23b85682e5a4d97694640ae249b18/)); ikili kodlama sözcük edinimi ve kalıcılığını destekler
(Wong ve ark. 2019, [link](https://consensus.app/papers/details/8e8c8927628f5ee9b1eb2c50a2b274b7/); Li ve ark. 2019,
[link](https://consensus.app/papers/details/320eec83f9915a428960e7ab47e674bc/)). Kritik koşul: **sistematik renk tutarlılığı** ve rengin
**daima etiketle** eşlenmesi (CVD-güvenliği).

> Not: Bu kanıt eğitim literatüründendir (Consensus üzerinden erişilen hakemli çalışmalar);
> PubMed yalnızca §12'deki biyomedikal/dikkat kanıtı için kullanılmıştır.

## 14. İşitsel geri bildirim kanıtı ve sınırları

İşitsel earcon katmanı (bkz. `audio-system.md`) eğitim ve DEHB literatürüne dayanır; tasarım,
yararı korurken dağıtıcılık riskini sınırlamak üzere kısıtlanmıştır.

**Oyunlaştırmada ses.** Ses efektleri geri bildirim/katılımı güçlendirir; görsel+işitsel
**birleşimi** akışı destekler ve tercih edilir (Schubhan 2024,
[link](https://consensus.app/papers/details/4d5440b260c85100a53796b9224b9270/); Cao 2025 sistematik derleme, [link](https://consensus.app/papers/details/d7a1406f041a574ba444f773521ca341/)).
Kritik: **alçak-değerlikli/sert sesler** ödülde gerilim artırır → kaçınılır (Altmeyer 2022 CHI,
[link](https://consensus.app/papers/details/f111f5d2a9ad508bb8a6d168061635ab/)); arka plan müziği dikkatli/kişiselleştirilmiş olmalıdır
(de Freitas 2024, [link](https://consensus.app/papers/details/142d4705afeb587b8ac58f86282d3ece/)).

**DEHB ve işitsel uyaran.** Kısa, göreve-ilgisiz **yeni sesler** dikkat performansını geçici
iyileştirebilir (Tegelbeckers 2016, [link](https://consensus.app/papers/details/b4286a77cc675581ae51171c6770ee2b/); 2022,
[link](https://consensus.app/papers/details/d4c812288ea25921bec1ce559dc5af0d/)); ancak **sürekli/alakasız** ses, özellikle çalışma belleği
yükünde, DEHB'de daha dağıtıcıdır (Kong 2025, [link](https://consensus.app/papers/details/94a299afeba758a3b09ef34573f77d1f/); Blomberg 2022,
[link](https://consensus.app/papers/details/b9dab9ace23754659fb6a3e06e0b5a89/); Söderlund 2012, [link](https://consensus.app/papers/details/8ffd18690d3b574b8ff6033e8db6ef71/)). Beyaz
gürültü yararı bireye göre değişir; hiperaktif/dürtüsel profili ve tipik gelişen çocukları
olumsuz etkileyebilir (Söderlund 2024, [link](https://consensus.app/papers/details/708c254103715895897a682d65904240/); Lin 2022,
[link](https://consensus.app/papers/details/5f73c4dec64c5bd5b3425f079894c4fd/); Chen 2022, [link](https://consensus.app/papers/details/cbd95eeeb4cb5bada88fc99ce0dde9ec/); Baijot 2016,
[link](https://consensus.app/papers/details/0214cdf3b9d15535abe5f9d9eed677e3/)).

**Tasarıma çevirisi:** kısa + hoş-değerlikli + görselle eşli olay-earcon'ları; **sürekli müzik/
gürültü yok**; opsiyonel + kolay susturma + düşük ses + reduced-motion'da varsayılan kapalı.
"Yanlış" earcon'u nazik/alçak (düşük-değerlik uyarısı + duygu-düzenleme kırılganlığı, §3).

## 15. Sesli okuma (TTS) kanıtı ve sınırları

İşitsel earcon'dan (sinyal) ayrı olarak, v1.8.0 **opsiyonel bir metin-konuşma (TTS) erişilebilirlik
katmanı** ekler (bkz. `audio-system.md` §5). Gerekçe: DEHB sıklıkla okuma güçlükleriyle birlikte
görülür ve kod-çözme yükü çalışma belleğini tüketerek anlamayı düşürür; sesli okuma bu yükü
hafifletip dinleme-anlama ile okumayı eşleştirebilir.

Kanıt: bir meta-analiz, okuma güçlüğü olan öğrencilerde TTS/sesli-okuma araçlarının okuduğunu
anlamada ortalama olumlu etki bildirir (ağırlıklı etki ≈ .35; %95 GA .14–.56) ([Wood ve ark. 2017,
*J Learn Disabil*](https://consensus.app/papers/details/89d12d947e22529d8487d1a570c933f8/)); 8–12 yaş
okuma/dil güçlüğü olan çocuklarda TTS, TTS'siz okumaya göre anlamayı anlamlı artırır ([Keelor ve ark.
2023, *Ann Dyslexia*](https://consensus.app/papers/details/a8758195bdf151ef817da94a54b49620/));
işitsel-görsel bütünleşmeyi destekleyen, **dikkat-güdümlü** (gaze-contingent) bir sesli-okuma aracı
disleksili çocuklarda anlamayı %24 artırmış ve en yanlış okuyanlar daha çok yararlanmıştır ([Schiavo
ve ark. 2021, *J Comput Assist Learn*](https://consensus.app/papers/details/d6e72faf112f568d8361941666017593/)).
TTS ayrıca öz-yeterlik ve motivasyonu artıran bir telafi aracı olarak rapor edilir ([Raffoul ve ark.
2023](https://consensus.app/papers/details/bfc63bda67ec5b69be45179546e1672e/)).

**Sınırlar / sorumlu kullanım.** Yarar herkese tek-beden değildir: yalnızca dinleme-anlaması
çözümlemesinden yüksek (disleksik) profiller anlamlı kazanç gösterebilir ([Silvestri ve ark. 2021,
*J Spec Educ Technol*](https://consensus.app/papers/details/7ff9500611b55dc2b3f5c7487c50dfb8/)); TTS
**öğretmen öğretiminin yerine değil tamamlayıcısıdır** ve insan okuyucu dinleme-anlamada sentetik sesi
geçebilir ([Brunow ve ark. 2021](https://consensus.app/papers/details/cf934cd5bb5f57488209584799edcf33/)).

**Tasarıma çevirisi:** TTS **varsayılan kapalı, talep-üzerine, kullanıcı-denetimli**; **otomatik
okuma yok**; metni gizlemez (ses eşlik eder, ikame etmez); durdurulabilir; dil içerikle eşleşir.
Bu, birey farklılığını, "destek değil ikame değil" ilkesini ve §3'teki düşük-yük/yüksek-uyarılma
dengesini onurlandırır. Doğrulama: genişletilmiş **G-AUDIO** kapısı (earcon + TTS).

