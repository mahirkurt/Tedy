"""Akşam çalışma planı bildirimleri (spec §5.3, §6.6, §6.8; ruling R24): dakikalık tur.

Işık'a blok başına en çok iki bildirim ("Süre doldu", "Mola bitti"); seçilen aile üyelerine akşam
başına birer kez "başlamadı", "takıldı", "sığmıyor". Olaylar her turda plandan yeniden hesaplanır
(`olaylar`, saf); yeniden deneme kuyruğu yoktur: bir kişinin en az bir cihazı kabul edince defter
satırı yazılır (`(gun, tur, blok_id, email)`), hepsi geçici hata verirse olay vadesi sürdükçe
sonraki dakika yeniden denenir. Ölü cihaz silinir. Sessiz saat 21:00–07:30.

`sinav_uyari.py` ile aynı yapı: durum dosyası her turda yazılır, tur kişi ve cihaz başına yalıtılır,
`main` ölümcül hatada 1 ile çıkar. Bayraklar: `TEDY_AKSAM_BILDIRIM=1` ve `TEDY_AKSAM_PLANI=1`
ikisi de açık değilse tur hiçbir şey göndermez."""
from __future__ import annotations

import fcntl
import json
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator, Literal

from src import aksam_duzeni, web_push
from src.aksam_plani import PlanDeposu, _dk
from src.json_utils import atomic_json_dump
from src.roles import OGRENCI_EMAILS, is_full

SESSIZ_BAS = time(21, 0)
SESSIZ_SON = time(7, 30)
MOLA_KISA, MOLA_UZUN = 5, 10          # aksam_plani'ndakiyle aynı: iki bloktan sonra uzun mola
DEFTER = PurePosixPath("output/aksam_bildirim_defteri.jsonl")
DURUM = PurePosixPath("output/aksam_bildirim_durumu.json")
DUZEN = PurePosixPath("output/aksam_duzeni.json")
ODAK_ESKI = PurePosixPath("output/odak_penceresi.json")
HATA_LISTESI_SINIRI = 5
KOK_PLAN_YOK = "plan okunamadı"
KOK_VAPID_YOK = "VAPID ayarlı değil"


@dataclass(frozen=True)
class Olay:
    tur: Literal["sure_doldu", "mola_bitti", "baslamadi", "takildi", "sigmiyor"]
    alici: Literal["ogrenci", "aile"]
    blok_id: str | None
    baslik: str
    govde: str


def _sessiz(an: datetime) -> bool:
    return an.time() >= SESSIZ_BAS or an.time() < SESSIZ_SON


def _saat(dk: int) -> str:
    return f"{dk // 60:02d}:{dk % 60:02d}"


def _basla(blok: Any, gunluk: dict) -> int:
    kayit = gunluk.get(blok.id) if isinstance(gunluk.get(blok.id), dict) else {}
    dk = _dk(kayit.get("basla"))
    return blok.bas if dk is None else dk


def _bitis(blok: Any, gunluk: dict) -> int:
    kayit = gunluk.get(blok.id) if isinstance(gunluk.get(blok.id), dict) else {}
    dk = _dk(kayit.get("bitti"))
    return blok.bit if dk is None else dk


def olaylar(plan: Any, gunluk: dict, duzen: dict, simdi: datetime) -> list[Olay]:
    """Şu an vadesi gelmiş olaylar (defter süzgeci dışarıda). Saf: dosya, saat ve ağ yok."""
    if _sessiz(simdi) or gunluk.get("aksam_yok") or plan.durum != "akis":
        return []        # kapali/okulsuz/plansiz/bitti/onizleme: konuşacak akış yok
    simdi_dk = simdi.hour * 60 + simdi.minute
    calisma = sorted((b for b in plan.bloklar if b.tur == "calisma"), key=lambda b: (b.bas, b.bit))
    sonuc: list[Olay] = []

    suruyor = [b for b in calisma if b.durum == "suruyor"]
    for b in suruyor:
        basla = _basla(b, gunluk)
        ders = b.ders or "Bu iş"
        if simdi_dk >= basla + b.tahmin_dk:
            sonuc.append(Olay("sure_doldu", "ogrenci", b.id, "Süre doldu",
                              f"{ders} için tahmin ettiğin süre bitti. Bitti mi, biraz daha mı?"))
        if simdi_dk > basla + b.tahmin_dk + int(duzen["takildi_esik_dk"]):     # "geçti": eşiğin kendisi değil
            sonuc.append(Olay("takildi", "aile", b.id, f"{ders} bloğu uzadı",
                              f"Başlayalı {simdi_dk - basla} dakika oldu, henüz bitti işaretlenmedi."))

    bitenler = [b for b in calisma if b.durum == "bitti"]
    siradaki = next((b for b in calisma if b.durum in ("bekliyor", "ertelendi")), None)
    if bitenler and not suruyor and siradaki is not None:
        son = max(bitenler, key=lambda b: (_bitis(b, gunluk), b.bas))
        mola = MOLA_UZUN if len(bitenler) % 2 == 0 else MOLA_KISA
        if simdi_dk >= _bitis(son, gunluk) + mola:
            sonuc.append(Olay("mola_bitti", "ogrenci", son.id, "Mola bitti",
                              f"Sırada {siradaki.ders or 'sıradaki iş'}: {siradaki.adim}."))

    hazir = aksam_duzeni.dakika(duzen["odeve_hazir"])
    esik = hazir + int(duzen["baslamadi_esik_dk"])
    if calisma and simdi_dk >= esik and not any(b.durum in ("suruyor", "bitti") for b in calisma):
        sonuc.append(Olay("baslamadi", "aile", None, "Işık henüz başlamadı",
                          f"Saat {_saat(esik)}; bu akşamın ilk işi {calisma[0].ders or 'ödev'}."))

    if plan.sigmayan:
        s = plan.sigmayan[0]
        sonuc.append(Olay("sigmiyor", "aile", None, "Bu akşama sığmıyor",
                          f"{s.get('ders') or 'Ödev'}: {s.get('baslik') or ''} yarın teslim; plana sığmadı."))
    return sonuc


class Defter:
    """`(gun, tur, blok_id, email)` satırları; eklemeli JSONL, `flock` altında."""

    def __init__(self, yol: str | Path):
        self.yol = Path(yol)

    @contextmanager
    def _kilitli(self) -> Iterator[None]:
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        with open(self.yol.with_name(self.yol.name + ".lock"), "a") as kilit:
            fcntl.flock(kilit, fcntl.LOCK_EX)
            yield

    def satirlar(self) -> set[tuple[str, str, str | None, str]]:
        sonuc = set()
        try:
            metin = self.yol.read_text(encoding="utf-8")
        except OSError:
            return sonuc
        for satir in metin.splitlines():
            try:
                k = json.loads(satir)
                sonuc.add((k["gun"], k["tur"], k.get("blok_id"), k["email"]))
            except (ValueError, KeyError, TypeError):
                continue
        return sonuc

    def yaz(self, gun: str, olay: Olay, email: str, simdi: datetime) -> None:
        with self._kilitli(), self.yol.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"zaman": simdi.isoformat(timespec="seconds"), "gun": gun, "tur": olay.tur,
                                "blok_id": olay.blok_id, "email": email}, ensure_ascii=False) + "\n")


def _gonderildi(satirlar: set, gun: str, olay: Olay, email: str) -> bool:
    if olay.alici == "ogrenci":
        return (gun, olay.tur, olay.blok_id, email) in satirlar
    # Ebeveyn olayları akşam başına bir kez: hangi blok olduğuna bakılmaz.
    return any(g == gun and t == olay.tur and e == email for g, t, _b, e in satirlar)


def alicilar(duzen: dict) -> dict[str, list[str]]:
    """Işık ve aile. Aile: ayardaki liste ∩ şu anki tam rollü, öğrenci olmayan üyeler (her turda
    yeniden denetlenir: kayıtlı bir e-posta aileden çıkmış olabilir)."""
    ogrenci = sorted(OGRENCI_EMAILS)
    aile = [e for e in duzen.get("haber_alacaklar") or []
            if isinstance(e, str) and is_full(e) and e.strip().lower() not in OGRENCI_EMAILS]
    return {"ogrenci": ogrenci, "aile": aile}


def _olumcul(durum: dict, mesaj: str) -> None:
    durum["_olumcul"].append(mesaj[:160])


def _sil(depo: web_push.AbonelikDeposu, endpoint: str, durum: dict) -> int:
    try:
        return depo.endpoint_sil(endpoint)
    except OSError as exc:
        _olumcul(durum, f"abonelik silinemedi: {exc}")
        return 0


def _cihaza_gonder(abonelik: dict, yuk: dict, vapid: Any, gonderici: Callable[..., web_push.GonderimSonucu],
                   depo: web_push.AbonelikDeposu, durum: dict) -> str:
    if not web_push.kayitli_abonelik_gecerli(abonelik):
        durum["gecersiz_silinen"] += _sil(depo, abonelik.get("endpoint", ""), durum)
        return "gecersiz"
    try:
        sonuc = gonderici(abonelik, yuk, vapid)
    except Exception as exc:  # noqa: BLE001 - bir cihaz turu düşürmez
        durum["hatalar"].append(f"gönderim: {type(exc).__name__}: {exc}"[:160])
        return "hata"
    if sonuc.durum == "ok":
        return "ok"
    if sonuc.durum == "olu":
        durum["olu_silinen"] += _sil(depo, abonelik["endpoint"], durum)
        return "olu"
    durum["hatalar"].append(f"{sonuc.kod}: {sonuc.mesaj}"[:160])
    return "hata"


def _gonder_kisiye(olay: Olay, email: str, depo: web_push.AbonelikDeposu, defter: Defter, vapid: Any,
                   gonderici: Callable[..., web_push.GonderimSonucu], gun: str, simdi: datetime,
                   durum: dict) -> None:
    yuk = {"baslik": olay.baslik, "govde": olay.govde, "etiket": f"aksam-{olay.tur}-{olay.blok_id or gun}",
           "url": "/"}
    sonuclar = [_cihaza_gonder(c["abonelik"], yuk, vapid, gonderici, depo, durum) for c in depo.kisinin(email)]
    if "ok" not in sonuclar:
        return       # hiçbir cihaz almadı: defter yok, olay vadesi sürdükçe sonraki dakika yeniden denenir
    defter.yaz(gun, olay, email, simdi)
    durum["gonderilen"] += 1


def _tur(kok: Path, simdi: datetime, gonderici: Callable[..., web_push.GonderimSonucu] | None,
         plan_kaynagi: Callable[[datetime], Any] | None, durum: dict) -> None:
    if os.environ.get("TEDY_AKSAM_BILDIRIM") != "1" or os.environ.get("TEDY_AKSAM_PLANI") != "1":
        durum["kapali"] = True
        return
    vapid = web_push.vapid_ayarlari()
    if vapid is None:
        _olumcul(durum, KOK_VAPID_YOK)
        return
    gonderici = gonderici or web_push.gonder
    if plan_kaynagi is None:
        from src.dashboard_api import bugunku_plan as plan_kaynagi
    try:
        plan = plan_kaynagi(simdi)
    except Exception as exc:  # noqa: BLE001
        _olumcul(durum, f"{KOK_PLAN_YOK}: {type(exc).__name__}: {exc}")
        return
    gun = simdi.date().isoformat()
    gunluk = PlanDeposu(kok).gunluk(gun)
    duzen = aksam_duzeni.oku(kok / DUZEN, eski=kok / ODAK_ESKI)
    alici = alicilar(duzen)
    durum["aile_alici"] = len(alici["aile"])
    depo = web_push.AbonelikDeposu(kok / web_push.ABONELIKLER)
    defter = Defter(kok / DEFTER)
    satirlar = defter.satirlar()
    for olay in olaylar(plan, gunluk, duzen, simdi):
        for email in alici[olay.alici]:
            if _gonderildi(satirlar, gun, olay, email):
                continue
            try:
                _gonder_kisiye(olay, email, depo, defter, vapid, gonderici, gun, simdi, durum)
            except Exception as exc:  # noqa: BLE001 - bir kişi turu düşürmez
                durum["hatalar"].append(f"{olay.tur}: {type(exc).__name__}: {exc}"[:160])


def tur(simdi: datetime | None = None, gonderici: Callable[..., web_push.GonderimSonucu] | None = None, *,
        kok: Path | None = None, plan_kaynagi: Callable[[datetime], Any] | None = None) -> dict:
    """Bir tur. `gonderici` yoksa çağrı anında `web_push.gonder` (testler onu yasaklar); `plan_kaynagi`
    yoksa `dashboard_api.bugunku_plan` (tek plan kaynağı)."""
    simdi = simdi or datetime.now()
    kok = Path(kok) if kok else Path(__file__).resolve().parents[1]
    durum: dict = {"son_tur": simdi.isoformat(timespec="seconds"), "kapali": False, "gonderilen": 0,
                   "olu_silinen": 0, "gecersiz_silinen": 0, "aile_alici": 0, "hatalar": [], "_olumcul": []}
    try:
        _tur(kok, simdi, gonderici, plan_kaynagi, durum)
    except Exception as exc:  # noqa: BLE001 - durum dosyası yine ne olduğunu söylesin
        _olumcul(durum, f"tur: {type(exc).__name__}: {exc}")
    finally:
        olumcul = durum.pop("_olumcul")
        tum = olumcul + durum["hatalar"]
        durum["hata_sayisi"] = len(tum)
        durum["hatalar"] = list(dict.fromkeys(tum))[:HATA_LISTESI_SINIRI]
        durum["olumcul"] = bool(olumcul)
        try:
            atomic_json_dump(durum, str(kok / DURUM))
        except OSError as exc:
            durum["hatalar"] = (durum["hatalar"] + [f"durum yazılamadı: {exc}"[:160]])[:HATA_LISTESI_SINIRI]
            durum["hata_sayisi"] += 1
    return durum


def main(argv: list[str] | None = None) -> int:
    from src.env_loader import load_env
    load_env()
    komut = (argv if argv is not None else sys.argv[1:])[:1]
    if komut == ["tur"]:
        durum = tur()
        print(json.dumps(durum, ensure_ascii=False))
        return 1 if durum.get("olumcul") else 0       # bayrak kapalı ve cihaz hatası 0
    print("kullanım: python -m src.aksam_bildirim tur", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
