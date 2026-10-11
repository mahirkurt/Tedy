import { TreeView, TreeNode } from '@carbon/react'
import { useNavigate } from 'react-router-dom'
import { asistanaSor } from '../asistan/sayfaBaglami'
import { useAcikDallar } from '../hooks/useAcikDallar'
import SubjectLabel from './SubjectLabel'
import type { MufredatDers, MufredatKonu } from '../types'

/**
 * Ders → ünite → ders kitabı alt başlığı ağacı.
 *
 * Carbon tek düzey iç içelikte ağacı dışlar; buradaki hiyerarşi iki düzeydir ve bileşen
 * rehberi §1.39 bu vakayı (ders → ünite → konu) `TreeView size="sm"` olarak karara bağlamıştır.
 *
 * `enableTreeViewControllable` bayrağı KULLANILMAZ: ölçüldü (TreeNode.js, 1.114.0) — bayrak
 * kapalıyken `onToggle` tetiklenir ve `isExpanded` prop'u değiştiğinde iç durum ona
 * senkronlanır; bayrak açıkken `onToggle` hiç çağrılmaz, yani açık dalları saklayamazdık.
 */

/** Dal etiketi sayacı: sayı, katlanmış içeriğin büyüklüğünü söyler (yüzey §2.5), cümle düzeninde. */
function sayac(konu: number, hazir: number): string {
  return `${konu} konu · ${hazir} hazır`
}

/** Yaprağın üst veri satırı. Sayfa yalnız kaynağı varsa yazılır; yoksa uydurulmaz (D4). */
function ustVeri(konu: MufredatKonu, kitapAdi: string): string {
  const parcalar = kitapAdi ? [kitapAdi] : []
  if (konu.sayfa) parcalar.push(`s.${konu.sayfa[0]}–${konu.sayfa[1]}`)
  parcalar.push(...konu.kazanimlar)
  parcalar.push(konu.modul ? 'Hazır' : 'Hazır değil')
  return parcalar.join(' · ')
}

/** Olay klavyeden mi geldi (React'in sentetik klavye olayı `key` taşır, fare olayı taşımaz). */
function klavyeden(olay: React.MouseEvent | React.KeyboardEvent): boolean {
  return 'key' in olay
}

export default function MufredatAgaci({ dersler }: { dersler: MufredatDers[] }) {
  const gezin = useNavigate()
  const { acik, degistir } = useAcikDallar()

  /**
   * Dalın satır tıklamasıyla açılması.
   *
   * Carbon `Enter`'da HEM `onToggle` HEM `handleClick` (→ `onSelect`) tetikliyor; ikisi de
   * aynı toggle'a bağlıyken dal açılıp hemen kapanıyor ve `localStorage` boş kalıyordu
   * (ölçüldü). Klavye yolunu `onToggle` zaten doğru yürütüyor, bu yüzden `onSelect`
   * yalnız fare tıklamasına karşılık verir.
   */
  function dalaTiklandi(olay: React.MouseEvent | React.KeyboardEvent, dalId: string) {
    if (!klavyeden(olay)) degistir(dalId)
  }

  // Yaprağın tek eylemi düğümün etkinleştirilmesidir: ARIA ağacında treeitem içine düğme
  // konmaz. Modülü olan yaprak gezinir (B58), olmayan konu asistana bağlam olur (B78).
  function konuyaGit(ders: MufredatDers, konu: MufredatKonu) {
    if (konu.modul) {
      gezin(`/moduller/${konu.modul.slug}/v${konu.modul.version}`)
      return
    }
    const karsilandi = asistanaSor({
      tur: 'konu', id: konu.id, etiket: `${ders.ders} · ${konu.ad}`,
    })
    if (!karsilandi) gezin('/asistan?sayfa=moduller')
  }

  return (
    <TreeView className="module-tree" label="Tüm müfredat" size="sm">
      {dersler.map(ders => (
        <TreeNode
          key={ders.slug}
          id={ders.slug}
          label={
            <span className="module-tree__dal">
              <SubjectLabel course={ders.ders} />
              <span className="module-tree__sayac">{sayac(ders.konu_sayisi, ders.hazir_sayisi)}</span>
            </span>
          }
          isExpanded={acik.has(ders.slug)}
          onToggle={() => degistir(ders.slug)}
          // Carbon'da yalnız chevron açar (`handleToggleClick`, stopPropagation'lı); satırın
          // kendi `onClick`'i yalnız seçer. Dalı satırın tamamı açar: telefonda 16 px'lik
          // chevron dokunma hedefi değildir.
          onSelect={(olay: React.MouseEvent | React.KeyboardEvent) => dalaTiklandi(olay, ders.slug)}
        >
          {ders.uniteler.length === 0 ? (
            // D3: eşiğe takılıp üretilmeyen ders sessizce eksilmez, bir cümle söyler.
            <TreeNode id={`${ders.slug}-yok`} label="Bu dersin haritası henüz hazır değil." />
          ) : ders.uniteler.map(unite => {
            const dalId = `${ders.slug}-u${unite.no}`
            return (
              <TreeNode
                key={dalId}
                id={dalId}
                label={
                  <span className="module-tree__dal">
                    <span>{unite.no}. {unite.ad}</span>
                    <span className="module-tree__sayac">
                      {sayac(unite.konular.length, unite.hazir_sayisi)}
                    </span>
                  </span>
                }
                isExpanded={acik.has(dalId)}
                onToggle={() => degistir(dalId)}
                onSelect={(olay: React.MouseEvent | React.KeyboardEvent) => dalaTiklandi(olay, dalId)}
              >
                {/* D3: konusu olmayan ünite açılıp boş bir gruba inmez, bir cümle söyler. */}
                {unite.konular.length === 0 ? (
                  <TreeNode id={`${dalId}-yok`} label="Bu ünitenin konuları henüz eşlenmedi." />
                ) : unite.konular.map(konu => {
                  const kitap = ders.kitaplar.find(k => k.document_id === konu.kitap)
                  return (
                    <TreeNode
                      key={konu.id}
                      id={konu.id}
                      label={
                        <span className="module-tree__yaprak">
                          <span className="module-tree__ad">{konu.ad}</span>
                          <span className="module-tree__ust-veri">
                            {ustVeri(konu, kitap?.kisa ?? '')}
                          </span>
                        </span>
                      }
                      href={konu.modul
                        ? `/moduller/${konu.modul.slug}/v${konu.modul.version}`
                        : undefined}
                      onSelect={(olay: React.MouseEvent | React.KeyboardEvent) => {
                        // Carbon `Enter`'da href'li düğüm için önce düğümün kendi `click()`'ini
                        // çağırıyor, sonra `handleClick`'i — yani `onSelect` iki kez gelir ve
                        // iki `navigate` bir geri tuşunu yutuyordu (ölçüldü). Sentetik tıklama
                        // işi zaten yaptığı için klavye çağrısı yoksayılır.
                        if (konu.modul && klavyeden(olay)) return
                        olay.preventDefault()
                        konuyaGit(ders, konu)
                      }}
                    />
                  )
                })}
              </TreeNode>
            )
          })}
        </TreeNode>
      ))}
    </TreeView>
  )
}
