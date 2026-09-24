// Üretilir: scripts/gen_subject_themes.py — elle düzenlemeyin. Kaynak:
// src/mcp_server/vendor/assets/carbon-v11-authority.json → tedyLayer.subjectThemes.
//
// Ders adı → alan → Carbon Tag ailesi. Aynı tablo ve aynı katlama kuralı backend'de
// (src/subject_themes.py) ve modül şablonunda (subjectDomain()) çalışır.

export type SubjectFamily = "magenta" | "purple" | "teal" | "cyan" | "blue" | "warm-gray" | "cool-gray" | "gray"

export interface SubjectDomain {
  id: string
  label: string
  family: SubjectFamily
}

export const SUBJECT_FAMILIES: readonly SubjectFamily[] = ["magenta", "purple", "teal", "cyan", "blue", "warm-gray", "cool-gray", "gray"]

const DOMAINS: ReadonlyArray<SubjectDomain & { stems: readonly string[] }> = [
  {
    "id": "yabanci-dil",
    "label": "Yabancı diller",
    "family": "blue",
    "stems": [
      "ingilizce",
      "english",
      "fransizca",
      "french",
      "francais",
      "almanca",
      "german",
      "deutsch",
      "arapca",
      "arabic",
      "ispanyolca",
      "spanish",
      "italyanca",
      "rusca",
      "cince",
      "japonca",
      "yabanci dil",
      "foreign language"
    ]
  },
  {
    "id": "dil",
    "label": "Türkçe ve edebiyat",
    "family": "magenta",
    "stems": [
      "turkce",
      "turk dili",
      "edebiyat",
      "turkish",
      "dil ve anlatim",
      "okuma yazma",
      "ilk okuma",
      "masal"
    ]
  },
  {
    "id": "matematik",
    "label": "Matematik",
    "family": "purple",
    "stems": [
      "matematik",
      "math",
      "geometri",
      "cebir",
      "istatistik"
    ]
  },
  {
    "id": "fen",
    "label": "Fen bilimleri",
    "family": "teal",
    "stems": [
      "fen",
      "fizik",
      "kimya",
      "biyoloji",
      "physics",
      "chemistry",
      "biology",
      "science",
      "astronomi",
      "bilim uygulama"
    ]
  },
  {
    "id": "degerler",
    "label": "Din ve değerler",
    "family": "warm-gray",
    "stems": [
      "din kultur",
      "din bilgi",
      "temel dini",
      "ahlak",
      "degerler",
      "kur'an",
      "kuran",
      "peygamber",
      "siyer",
      "religion",
      "ethics"
    ]
  },
  {
    "id": "sosyal",
    "label": "Sosyal bilimler",
    "family": "cyan",
    "stems": [
      "sosyal",
      "social",
      "hayat bilgisi",
      "tarih",
      "history",
      "inkilap",
      "cografya",
      "geography",
      "felsefe",
      "philosophy",
      "sosyoloji",
      "psikoloji",
      "mantik",
      "vatandaslik",
      "yurttaslik",
      "insan haklari",
      "demokrasi",
      "civics"
    ]
  },
  {
    "id": "teknoloji",
    "label": "Bilişim ve teknoloji",
    "family": "cool-gray",
    "stems": [
      "bilisim",
      "teknoloji",
      "yazilim",
      "kodlama",
      "robotik",
      "informatics",
      "computer",
      "coding"
    ]
  },
  {
    "id": "sanat-spor",
    "label": "Sanat ve spor",
    "family": "gray",
    "stems": [
      "gorsel sanat",
      "sanat",
      "resim",
      "muzik",
      "music",
      "beden egitimi",
      "spor",
      "physical education",
      "fiziki etkinlik",
      "drama",
      "dans"
    ]
  }
]

const FALLBACK: SubjectDomain = {"id": "genel", "label": "Genel", "family": "gray"}

const FOLD: Record<string, string> = { ç: 'c', ğ: 'g', ı: 'i', ö: 'o', ş: 's', ü: 'u', â: 'a', î: 'i', û: 'u' }

export function foldSubject(value: string | null | undefined): string {
  return String(value ?? '')
    .toLocaleLowerCase('tr')
    .replace(/[çğıöşüâîû]/g, (c) => FOLD[c])
    .replace(/\s+/g, ' ')
    .trim()
}

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const PATTERNS = DOMAINS.map((d) => ({
  domain: { id: d.id, label: d.label, family: d.family } as SubjectDomain,
  re: new RegExp('(?:^|[^a-z0-9])(?:' + d.stems.map(escape).join('|') + ')'),
}))

export function subjectDomain(course: string | null | undefined): SubjectDomain {
  const folded = foldSubject(course)
  for (const p of PATTERNS) if (p.re.test(folded)) return p.domain
  return FALLBACK
}

export function subjectFamily(course: string | null | undefined): SubjectFamily {
  return subjectDomain(course).family
}
