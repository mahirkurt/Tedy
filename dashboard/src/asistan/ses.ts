// Sayfanın okura hitabı (eski AssistantChat'teki VOICE, metinler birebir): öğrenciye "sen", aileye "siz".
export const VOICE = {
  ogrenci: {
    welcome: 'Merhaba! TEDY Asistan olarak sana yardımcı olabilirim. Ödevlerin, sınavların ve derslerin hakkında sorular sorabilir veya kişisel çalışma planı isteyebilirsin.',
    prompts: [
      { text: 'Bugün neye öncelik vermeliyim?', mode: 'chat' as const },
      { text: 'Çalışma planı hazırla', mode: 'plan' as const },
      { text: 'Eksik konularımı özetle', mode: 'chat' as const },
    ],
    placeholder: 'Bir soru sor veya çalışma planı iste...',
    sources: 'Her iddianın yanındaki numara, o cümlenin nereden geldiğini gösterir — MEB müfredatı, ders kitabın veya kendi okul verin. Numaraya dokunup kaynağı okuyabilirsin.',
    caution: 'Yapay zekâ yanılabilir. Bir şey tuhaf geldiyse kaynağa bak.',
    ogretmenHata: 'Öğretmen modları şu an yüklenemedi; Genel modda sorabilirsin.',
  },
  aile: {
    welcome: "Merhaba! TEDY Asistan olarak size yardımcı olabilirim. Işık'ın ödevleri, sınavları ve dersleri hakkında soru sorabilir veya onun için çalışma planı isteyebilirsiniz.",
    prompts: [
      { text: 'Işık bugün neye öncelik vermeli?', mode: 'chat' as const },
      { text: 'Işık için çalışma planı hazırla', mode: 'plan' as const },
      { text: "Işık'ın eksik konularını özetle", mode: 'chat' as const },
    ],
    placeholder: 'Bir soru sorun veya çalışma planı isteyin...',
    sources: "Her iddianın yanındaki numara, o cümlenin nereden geldiğini gösterir — MEB müfredatı, ders kitabı veya Işık'ın okul verisi. Numaraya dokunup kaynağı okuyabilirsiniz.",
    caution: 'Yapay zekâ yanılabilir. Bir şey tuhaf geldiyse kaynağa bakın.',
    ogretmenHata: 'Öğretmen modları şu an yüklenemedi; Genel modda sorabilirsiniz.',
  },
}