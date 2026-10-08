// Başlatıcıda ve sayfa bağlamıyla açılan asistanda, bulunulan sayfaya göre hızlı sorular (iki hitapta).
const S: Record<string, { ogrenci: string[]; aile: string[] }> = {
  bugun: { ogrenci: ['Bugün neye öncelik vermeliyim?', 'Yarın için ne hazırlamalıyım?'], aile: ['Işık bugün neye öncelik vermeli?', 'Işık yarın için ne hazırlamalı?'] },
  isler: { ogrenci: ['Bugün hangisinden başlayayım?', 'Teslimi en yakın ödev hangisi?', 'Bu ödeve nasıl başlarım?'], aile: ['Işık bugün hangi işten başlamalı?', 'Teslimi en yakın ödev hangisi?', 'Bu ödevde Işık’a nasıl yardım edebilirim?'] },
  dersler: { ogrenci: ['Bu haftaki konuyu kısaca anlat', 'Bu hafta hangi derslerde yeni konu var?'], aile: ['Bu haftaki konuları kısaca özetler misiniz?', 'Işık bu hafta hangi derslerde yeni konuya geçiyor?'] },
  notlar: { ogrenci: ['Hangi derste zorlanıyorum?', 'Notlarımı nasıl yükseltebilirim?'], aile: ['Işık hangi derste zorlanıyor?', 'Işık’ın notları için neye odaklanmalıyız?'] },
  takvim: { ogrenci: ['Bu haftam nasıl görünüyor?', 'Yaklaşan bir sınav var mı?'], aile: ['Işık’ın bu haftası nasıl görünüyor?', 'Yaklaşan bir sınav var mı?'] },
  takimlar: { ogrenci: ['Takım etkinliklerim ne zaman?', 'Bu hafta takımda ne var?'], aile: ['Işık’ın takım etkinlikleri ne zaman?', 'Bu hafta takımda ne var?'] },
  ilerleme: { ogrenci: ['Bu hafta neler çalıştım?', 'Zayıf olduğum konular hangileri?'], aile: ['Işık bu hafta neler çalıştı?', 'Işık’ın zayıf konuları hangileri?'] },
  duyurular: { ogrenci: ['Beni ilgilendiren bir duyuru var mı?', 'Son duyuruları özetle'], aile: ['Bizi ilgilendiren bir duyuru var mı?', 'Son duyuruları özetler misiniz?'] },
  profil: { ogrenci: ['Ders programımı özetle', 'Bu dönem hangi derslerim var?'], aile: ['Işık’ın ders programını özetler misiniz?', 'Bu dönem hangi dersleri var?'] },
  moduller: { ogrenci: ['Hangi modülle çalışmalıyım?', 'Yarım kalan bir modülüm var mı?'], aile: ['Işık hangi modülle çalışmalı?', 'Yarım kalan bir modülü var mı?'] },
  kitaplar: { ogrenci: ['Okuduğum bölümü özetle', 'Bu bölümdeki zor kelimeler neler?'], aile: ['Işık’ın okuduğu bölümü özetler misiniz?', 'Bu bölümde konuşabileceğimiz sorular neler?'] },
  sinavlar: { ogrenci: ['Yaklaşan sınavım için plan yap', 'Bu sınavın konuları neler?'], aile: ['Yaklaşan sınav için Işık’a plan yapar mısınız?', 'Bu sınavın konuları neler?'] },
}
export function sayfaSorulari(ad: string, okur: 'ogrenci' | 'aile'): string[] { return S[ad]?.[okur] ?? [] }
