// Kurulu @carbon/ai-chat'in enLanguagePack anahtarlarını yazdırır (dil paketi testi bunu kullanır).
// Paket package.json'u dışa açmadığı için yol node_modules üzerinden kurulur.
import { readFileSync } from 'node:fs'
const yol = new URL('../node_modules/@carbon/ai-chat/dist/es/chat.languageUtils.js', import.meta.url)
const s = readFileSync(yol, 'utf8')
const bas = s.indexOf('var enLanguagePackData = {')
const blok = s.slice(bas, s.indexOf('};', bas))
console.log(JSON.stringify([...blok.matchAll(/^\s+([A-Za-z0-9_]+),?$/gm)].map(m => m[1])))
