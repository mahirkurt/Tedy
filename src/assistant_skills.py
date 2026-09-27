"""Öğretmen skill'leri (B1): src/assistant_skills/<ad>/SKILL.md + references/*.md.

Spec: docs/superpowers/specs/2026-09-28-asistan-ogretmen-modlari-design.md §1. Bir skill,
Işık'ın bir dersteki öğretmen tanımıdır: ön bilgi (seçici, tema, karşılama) ve gövde (modele
ikinci sistem bloğu olarak giden öğretmen tanımı). Anthropic Agent Skills API değil; depodaki
dosyalardır.

Bozuk bir skill açılışta SkillHatasi yükseltir — hangi skill, hangi dosya, neden. Sessizce
atlanmaz: atlanan bir öğretmen, seçicide görünmeyen ya da yarım tanımla konuşan bir modeldir.

Ön bilgi YAML'ın belgelenmiş küçük bir alt kümesidir (depoda PyYAML yok, eklenmiyor):
    anahtar: değer
    anahtar:
      alt: değer
      alt:
        - madde
Sekme, yorum, tırnak, çok satırlı değer yok. Değer ilk ': ' ayırıcısından sonrasıdır.
"""
from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src import subject_themes

SKILL_DIZINI = Path(__file__).resolve().parent / "assistant_skills"
GENEL = "genel"
# Seçicideki sıra (spec: Genel · Türkçe · Fen · Sosyal · Matematik). Listede olmayan bir skill
# bunların ardından, ada göre gelir.
SIRA = ("turkce", "fen", "sosyal", "matematik")
ZORUNLU_ALANLAR = ("name", "kisa_ad", "description", "ders", "renk_ailesi", "ogretmen_adi",
                   "karsilama", "hizli_sorular")
DUZ_ALANLAR = ("name", "kisa_ad", "description", "ders", "renk_ailesi", "ogretmen_adi")
OKURLAR = ("ogrenci", "aile")
ZORUNLU_BASLIKLAR = ("Rol ve ses", "Ders akışı", "Maarif Modeli bağı",
                     "Derse özgü anlatım teknikleri", "Sık kavram yanılgıları",
                     "Araç kullanımı", "Sınırlar")
ZORUNLU_KAYNAKLAR = ("kavram-yanilgilari.md", "soru-kaliplari.md", "unite-haritasi.md")
OGRETMEN_SONEKI = " öğretmeni"
# skill_kaynagi bir notu bu boyda sayfalara böler: chat_with_tools araç sonucunu 4.000
# karakterde keser, başlık ve "Devamı" satırı da o bütçeden yer.
SAYFA_SINIRI = 3600
_AD = re.compile(r"^[a-z]+$")
_KAYNAK_ADI = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
_CUMLE_SONU = re.compile(r"[.!?]\s+[A-ZÇĞİÖŞÜ]")


class SkillHatasi(ValueError):
    """Bozuk bir skill. İleti skill'i ve nedeni adlandırır; okura değil log'a gider."""


@dataclass(frozen=True, eq=False)
class Skill:
    ad: str
    kisa_ad: str
    aciklama: str
    ders: str
    renk_ailesi: str
    ogretmen_adi: str
    karsilama: dict[str, str]
    hizli_sorular: dict[str, tuple[str, ...]]
    govde: str
    kaynaklar: tuple[str, ...]
    dizin: Path

    @property
    def gecis_sorusu(self) -> str:
        """'Matematik öğretmeni' -> 'Matematik öğretmenine geçelim mi?' (ad 'öğretmeni' ile biter)."""
        return f"{self.ogretmen_adi}ne geçelim mi?"

    def kaynak_oku(self, ad: str) -> str:
        """Bir references/ dosyası. Yalnız listedeki adlar: girdiden hiçbir yol kurulmaz."""
        if ad not in self.kaynaklar:
            raise KeyError(ad)
        return (self.dizin / "references" / ad).read_text(encoding="utf-8")

    def kaynak_sayfasi(self, ad: str, sayfa: int = 1) -> tuple[str, int]:
        """(sayfanın metni, toplam sayfa). Sayfa 1'den başlar; aralık dışı IndexError."""
        sayfalar = sayfalara_bol(self.kaynak_oku(ad))
        if not 1 <= sayfa <= len(sayfalar):
            raise IndexError(sayfa)
        return sayfalar[sayfa - 1], len(sayfalar)

    def sistem_blogu(self) -> str:
        """Modele giden ikinci sistem bloğu. Saat ya da okur içermez: önbelleklenir."""
        notlar = ", ".join(f"`{k}`" for k in self.kaynaklar)
        return (
            f"# Öğretmen modu: {self.ogretmen_adi}\n\n"
            f"Bu konuşmada Işık'ın {self.ders} öğretmenisin. Aşağıdaki tanım bu mod içindir; "
            "yukarıdaki istemin Hitap, Uydurma yasağı, Atıf ve Biçim kuralları burada da "
            "geçerlidir — bu tanım açıkça bir istisna koymadıkça.\n\n"
            f"Öğretmen notların `skill_kaynagi` aracıyla açılır: {notlar}. Uzun bir not sayfa "
            "sayfa gelir. Notlar senin içindir: okura kaynak diye gösterilmez, adları okura "
            "söylenmez, onlardan aldığın cümleye [S] işareti konmaz.\n\n"
            + self.govde.strip() + "\n"
        )

    def secici_ozeti(self) -> dict[str, Any]:
        """GET /api/assistant/ogretmenler'in bir satırı."""
        return {
            "id": self.ad,
            "kisa_ad": self.kisa_ad,
            "ogretmen_adi": self.ogretmen_adi,
            "ders": self.ders,
            "renk_ailesi": self.renk_ailesi,
            "karsilama": dict(self.karsilama),
            "hizli_sorular": {okur: list(s) for okur, s in self.hizli_sorular.items()},
        }


def sayfalara_bol(metin: str, sinir: int = SAYFA_SINIRI) -> list[str]:
    """Paragraf sınırlarında, her biri `sinir`i aşmayan sayfalar. Tek paragraf sınırı aşarsa
    satır sonundan, satır da aşarsa karakterden bölünür."""
    parcalar: list[str] = []
    for paragraf in re.split(r"\n\s*\n", metin.strip()):
        while len(paragraf) > sinir:
            kesim = paragraf.rfind("\n", 0, sinir)
            kesim = kesim if kesim > 0 else sinir
            parcalar.append(paragraf[:kesim].rstrip())
            paragraf = paragraf[kesim:].lstrip("\n")
        parcalar.append(paragraf)
    sayfalar: list[str] = []
    for parca in parcalar:
        if sayfalar and len(sayfalar[-1]) + 2 + len(parca) <= sinir:
            sayfalar[-1] += "\n\n" + parca
        else:
            sayfalar.append(parca)
    return sayfalar or [""]


def _anahtar_deger(satir: str, yer: str) -> tuple[str, str]:
    m = re.match(r"^([a-z_]+):(?:\s+(.*))?$", satir)
    if not m:
        raise SkillHatasi(f"{yer}: 'anahtar: değer' bekleniyordu: {satir[:40]!r}")
    return m.group(1), (m.group(2) or "").strip()


def on_bilgi_coz(satirlar: list[str], kaynak: str, ilk_satir: int = 2) -> dict[str, Any]:
    """Belgelenmiş alt küme (modül belgesine bakın). Her bozukluk dosya:satır adlandırır."""
    sonuc: dict[str, Any] = {}
    ust: str | None = None
    alt: str | None = None
    for no, ham in enumerate(satirlar, start=ilk_satir):
        yer = f"{kaynak}:{no}"
        if not ham.strip():
            continue
        if "\t" in ham:
            raise SkillHatasi(f"{yer}: sekme kullanılamaz; iki boşluk girinti kullan")
        girinti = len(ham) - len(ham.lstrip(" "))
        satir = ham.strip()
        if girinti == 0:
            anahtar, deger = _anahtar_deger(satir, yer)
            if anahtar in sonuc:
                raise SkillHatasi(f"{yer}: '{anahtar}' iki kez yazılmış")
            sonuc[anahtar] = deger if deger else {}
            ust, alt = (None if deger else anahtar), None
        elif girinti == 2 and ust is not None:
            anahtar, deger = _anahtar_deger(satir, yer)
            blok = sonuc[ust]
            if anahtar in blok:
                raise SkillHatasi(f"{yer}: '{ust}.{anahtar}' iki kez yazılmış")
            blok[anahtar] = deger if deger else []
            alt = None if deger else anahtar
        elif girinti == 4 and ust is not None and alt is not None and satir.startswith("- "):
            madde = satir[2:].strip()
            if not madde:
                raise SkillHatasi(f"{yer}: boş liste maddesi")
            sonuc[ust][alt].append(madde)
        else:
            raise SkillHatasi(f"{yer}: beklenmeyen girinti ya da biçim: {satir[:40]!r}")
    return sonuc


def _on_bilgi_ayir(metin: str, kaynak: str) -> tuple[list[str], str]:
    if not metin.startswith("---\n"):
        raise SkillHatasi(f"{kaynak}: ön bilgi '---' satırıyla başlamalı")
    son = metin.find("\n---\n", 3)
    if son < 0:
        raise SkillHatasi(f"{kaynak}: ön bilgi kapanmamış (ikinci '---' satırı yok)")
    return metin[4:son].split("\n"), metin[son + 5:]


def _govde_bolumleri(govde: str, kaynak: str) -> dict[str, str]:
    """'## ' başlıkları ZORUNLU_BASLIKLAR'la aynı sırada, her biri bir kez ve dolu olmalı."""
    parcalar = re.split(r"(?m)^## (.+?)\s*$", govde)
    basliklar = parcalar[1::2]
    if tuple(basliklar) != ZORUNLU_BASLIKLAR:
        raise SkillHatasi(f"{kaynak}: '## ' başlıkları tam olarak şu sırada olmalı: "
                          f"{' | '.join(ZORUNLU_BASLIKLAR)} — bulunan: {' | '.join(basliklar) or 'yok'}")
    bolumler = dict(zip(basliklar, parcalar[2::2]))
    for baslik, metin in bolumler.items():
        if not metin.strip():
            raise SkillHatasi(f"{kaynak}: '## {baslik}' bölümü boş")
    return bolumler


def govde_bolumleri(skill: Skill) -> dict[str, str]:
    """Gövdenin başlık -> metin haritası (içerik testleri okur)."""
    return _govde_bolumleri(skill.govde, f"{skill.ad}/SKILL.md")


def _kaynaklari_denetle(dizin: Path, ad: str) -> tuple[str, ...]:
    kok = dizin / "references"
    if kok.is_symlink() or not kok.is_dir():
        raise SkillHatasi(f"{ad}: references/ dizini yok")
    adlar = []
    for yol in sorted(kok.iterdir()):
        if yol.is_symlink() or not yol.is_file() or not _KAYNAK_ADI.match(yol.name):
            raise SkillHatasi(f"{ad}: references/{yol.name} kabul edilmez "
                              "(yalnız küçük harfli, tireli .md dosyaları; bağlantı ya da dizin yok)")
        try:
            metin = yol.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise SkillHatasi(f"{ad}: references/{yol.name} UTF-8 değil") from exc
        if not metin.strip():
            raise SkillHatasi(f"{ad}: references/{yol.name} boş")
        adlar.append(yol.name)
    eksik = [k for k in ZORUNLU_KAYNAKLAR if k not in adlar]
    if eksik:
        raise SkillHatasi(f"{ad}: references/ eksik: {', '.join(eksik)}")
    return tuple(adlar)


def skill_yukle(dizin: Path) -> Skill:
    ad = dizin.name
    kaynak = f"{ad}/SKILL.md"
    dosya = dizin / "SKILL.md"
    if dizin.is_symlink() or dosya.is_symlink() or not dosya.is_file():
        raise SkillHatasi(f"{ad}: SKILL.md yok (ya da bir bağlantı)")
    satirlar, govde = _on_bilgi_ayir(dosya.read_text(encoding="utf-8"), kaynak)
    ob = on_bilgi_coz(satirlar, kaynak)

    eksik = [k for k in ZORUNLU_ALANLAR if k not in ob]
    fazla = [k for k in ob if k not in ZORUNLU_ALANLAR]
    if eksik or fazla:
        raise SkillHatasi(f"{kaynak}: eksik alan: {', '.join(eksik) or '-'}; "
                          f"bilinmeyen alan: {', '.join(fazla) or '-'}")
    for k in DUZ_ALANLAR:
        if not isinstance(ob[k], str):
            raise SkillHatasi(f"{kaynak}: '{k}' tek satırlık bir değer olmalı")
    if ob["name"] != ad or not _AD.match(ad) or ad == GENEL:
        raise SkillHatasi(f"{kaynak}: name '{ob['name']}' dizin adıyla ('{ad}') aynı, küçük "
                          f"harfli ve '{GENEL}' dışında olmalı")
    if not ob["description"].endswith(".") or _CUMLE_SONU.search(ob["description"]):
        raise SkillHatasi(f"{kaynak}: description tek cümle olmalı ve nokta ile bitmeli")
    beklenen = subject_themes.family_of(ob["ders"])
    if ob["renk_ailesi"] != beklenen:
        raise SkillHatasi(f"{kaynak}: renk_ailesi '{ob['renk_ailesi']}', ders '{ob['ders']}' için "
                          f"'{beklenen}' olmalı (src/subject_themes.py)")
    if not ob["ogretmen_adi"].endswith(OGRETMEN_SONEKI):
        raise SkillHatasi(f"{kaynak}: ogretmen_adi '{OGRETMEN_SONEKI.strip()}' ile bitmeli "
                          "(geçiş düğmesi '…öğretmenine geçelim mi?' ondan kurulur)")

    karsilama = ob["karsilama"]
    if not isinstance(karsilama, dict) or sorted(karsilama) != sorted(OKURLAR) \
            or not all(isinstance(v, str) and v for v in karsilama.values()):
        raise SkillHatasi(f"{kaynak}: karsilama tam olarak 'ogrenci' ve 'aile' cümlelerini taşımalı")
    sorular = ob["hizli_sorular"]
    if not isinstance(sorular, dict) or sorted(sorular) != sorted(OKURLAR):
        raise SkillHatasi(f"{kaynak}: hizli_sorular tam olarak 'ogrenci' ve 'aile' listelerini taşımalı")
    for okur, liste in sorular.items():
        if not isinstance(liste, list) or not 3 <= len(liste) <= 4 or len(set(liste)) != len(liste):
            raise SkillHatasi(f"{kaynak}: hizli_sorular.{okur} 3–4 farklı maddeden oluşmalı")

    _govde_bolumleri(govde, kaynak)
    return Skill(
        ad=ad, kisa_ad=ob["kisa_ad"], aciklama=ob["description"], ders=ob["ders"],
        renk_ailesi=ob["renk_ailesi"], ogretmen_adi=ob["ogretmen_adi"],
        karsilama={okur: karsilama[okur] for okur in OKURLAR},
        hizli_sorular={okur: tuple(sorular[okur]) for okur in OKURLAR},
        govde=govde.strip() + "\n", kaynaklar=_kaynaklari_denetle(dizin, ad), dizin=dizin,
    )


def yukle(kok: Path = SKILL_DIZINI) -> dict[str, Skill]:
    """Dizindeki bütün skill'ler, seçici sırasıyla. Biri bozuksa SkillHatasi (hepsi durur)."""
    if not kok.is_dir():
        raise SkillHatasi(f"skill dizini yok: {kok}")
    skiller = {}
    for alt in sorted(kok.iterdir()):
        if alt.name.startswith((".", "_")):
            continue
        if not alt.is_dir():
            raise SkillHatasi(f"{alt.name}: skill dizininde beklenmeyen dosya")
        skill = skill_yukle(alt)
        skiller[skill.ad] = skill
    sira = {ad: i for i, ad in enumerate(SIRA)}
    return dict(sorted(skiller.items(), key=lambda kv: (sira.get(kv[0], len(sira)), kv[0])))


@functools.lru_cache(maxsize=1)
def varsayilan() -> dict[str, Skill]:
    """Depodaki skill'ler, süreç başına bir kez. Hata önbelleğe alınmaz: her çağrı yeniden dener
    ve yeniden yükseltir."""
    return yukle()
