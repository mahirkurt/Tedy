"""Testler için geçerli bir öğretmen skill'i yazar.

Gerçek src/assistant_skills/ içeriğine bağlı değil: yükleyici, araçlar ve çalışma zamanı
testleri kendi küçük skill'lerini tmp_path'e yazar, böylece bir öğretmenin metni değişince
bu testler kırılmaz.
"""
from __future__ import annotations

from pathlib import Path

BASLIKLAR = ("Rol ve ses", "Ders akışı", "Maarif Modeli bağı", "Derse özgü anlatım teknikleri",
             "Sık kavram yanılgıları", "Araç kullanımı", "Sınırlar")
KAYNAKLAR = {
    "kavram-yanilgilari.md": "# Kavram yanılgıları\n\nPaydalar toplanmaz.\n",
    "soru-kaliplari.md": "# Soru kalıpları\n\nÇoktan seçmeli.\n",
    "unite-haritasi.md": "# Harita\n\n1. Sayılar ve Nicelikler\n",
}


def on_bilgi(ad: str = "matematik", ders: str = "Matematik", aile: str = "purple",
             kisa_ad: str = "Matematik", ogretmen_adi: str = "Matematik öğretmeni") -> str:
    return (
        "---\n"
        f"name: {ad}\n"
        f"kisa_ad: {kisa_ad}\n"
        f"description: {ders} dersinde 7. sınıf sorularında kullanılır.\n"
        f"ders: {ders}\n"
        f"renk_ailesi: {aile}\n"
        f"ogretmen_adi: {ogretmen_adi}\n"
        "karsilama:\n"
        "  ogrenci: Merhaba! Bir soruyu getir: adım adım bakalım.\n"
        "  aile: Merhaba! Işık'ın sorusunu sorabilirsiniz.\n"
        "hizli_sorular:\n"
        "  ogrenci:\n"
        "    - Birinci soru\n"
        "    - İkinci soru\n"
        "    - Üçüncü soru\n"
        "  aile:\n"
        "    - Işık için birinci soru\n"
        "    - Işık için ikinci soru\n"
        "    - Işık için üçüncü soru\n"
        "---\n"
    )


def govde(basliklar: tuple[str, ...] = BASLIKLAR) -> str:
    return "".join(f"## {b}\n\n{b} bölümünün metni.\n\n" for b in basliklar)


def skill_yaz(kok: Path, ad: str = "matematik", ders: str = "Matematik", aile: str = "purple",
              *, on: str | None = None, govde_metni: str | None = None,
              kaynaklar: dict[str, str] | None = None, **kw: str) -> Path:
    dizin = kok / ad
    (dizin / "references").mkdir(parents=True, exist_ok=True)
    (dizin / "SKILL.md").write_text(
        (on_bilgi(ad, ders, aile, **kw) if on is None else on)
        + (govde() if govde_metni is None else govde_metni), encoding="utf-8")
    for dosya, metin in (KAYNAKLAR if kaynaklar is None else kaynaklar).items():
        (dizin / "references" / dosya).write_text(metin, encoding="utf-8")
    return dizin


def iki_skill(kok: Path) -> dict:
    """Matematik ve Türkçe: araç ve çalışma zamanı testlerinin öğretmenleri."""
    from src import assistant_skills
    skill_yaz(kok, "matematik", "Matematik", "purple")
    skill_yaz(kok, "turkce", "Türkçe", "magenta", kisa_ad="Türkçe", ogretmen_adi="Türkçe öğretmeni")
    return assistant_skills.yukle(kok)
