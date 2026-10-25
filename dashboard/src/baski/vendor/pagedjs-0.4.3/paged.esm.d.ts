// Paged.js 0.4.3'ün kullandığımız yüzeyi (src/baski/sayfalama.ts). Kaynak: paged.esm.js'in son export satırı.
export interface Akis {
  /** Basılan sayfa sayısı. */
  total: number
}

export class Previewer {
  constructor(options?: Record<string, unknown>)
  /** content: sayfalanacak parça; stylesheets verilirse (URL ya da {adres: metin}) yalnız onlar işlenir ve belgedeki
   *  stil sayfaları yerinde kalır; verilmezse belgedeki bütün <link>/<style>'lar sökülüp işlenir. */
  preview(content?: DocumentFragment, stylesheets?: (string | Record<string, string>)[], renderTo?: HTMLElement): Promise<Akis>
}
