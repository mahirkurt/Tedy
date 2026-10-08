/** Yeni (Carbon AI Chat) asistan arayüzü. Derleme zamanında sabitlenir: Görev 20'ye kadar canlı
 *  derlemede kapalı, `npm run build:carbon-ai` ve geliştirme sunucusunda açık. */
export const CARBON_AI_ACIK = import.meta.env.VITE_ASISTAN_CARBON_AI === '1'
