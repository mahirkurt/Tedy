"""Ödül ve rekabet çerçevesi yok (Modül Tasarım Kanunu M2.6, M2.7; KB-21, 2026-10-23).

Şablon sefer haritası, "Son N durak" hedef metni, "Yarışma"/"Mini Yarışma" başlığı ve "Meydan Oku"
düğmesi taşımaz; G-WELLBEING öğrenci yüzeyindeki rekabet çerçevesinde FAIL verir; `rewards` iç
sayıdır, isteğe bağlıdır ve `badges` şemada yoktur.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.mcp_server import derleme, gates, ornekler
from src.mcp_server.derleme import DerlemeHatasi

ORIGIN = "https://tedy.online"
SABLON = Path("src/mcp_server/vendor/assets/module-template.html").read_text(encoding="utf-8")
# Kanunun adını verdiği çerçeve; yorumlar ve CSS dahil şablonda hiç geçmez.
REKABET = re.compile(r"yar[ıi]şma|meydan\s+oku|sefer\s+haritas|son\s+\S+\s+durak|karma\s+geri-getirme", re.I)


def _mcq(data):
    return next(s for s in data["segments"] if s["type"] == "mcq")


def test_sablonda_rekabet_cercevesi_ve_sefer_haritasi_yok():
    bulunan = sorted({m.group(0) for m in REKABET.finditer(SABLON)})
    assert bulunan == [], bulunan
    # M2.6'nın denetimi: sefer haritası, hedef metni ve ProgressBar şablonda 0 kez.
    for kalinti in ("quest-map", "questMap", "renderQuestMap", "D.meta.quest", "railGoal",
                    'role="progressbar"', "<progress"):
        assert kalinti not in SABLON, kalinti


@pytest.mark.parametrize("mode", ornekler.MODES)
def test_derlenmis_ciktida_rekabet_yok_ve_g_wellbeing_gecer(mode):
    html = derleme.derle(ornekler.ornek(mode), {}, ORIGIN)
    assert not REKABET.search(html), REKABET.search(html).group(0)
    assert gates.run_gates(html)["G-WELLBEING"]["status"] != "FAIL"


@pytest.mark.parametrize("ad", ["Mini Yarışma", "YARIŞMA", "Meydan oku", "Son 3 durak", "Sefer haritası"])
def test_g_wellbeing_ogrenci_yuzeyindeki_rekabet_cercevesinde_duser(ad):
    data = ornekler.ornek("QUIZ")
    _mcq(data)["title"] = ad
    rapor = gates.run_gates(derleme.derle(data, {}, ORIGIN))
    assert rapor["G-WELLBEING"]["status"] == "FAIL"
    assert "rekabet" in rapor["G-WELLBEING"]["detail"]


def test_icerikteki_cekimli_sozcuk_ve_yazar_katmani_dusurmez():
    # Tarih anlatısındaki çekimli fiil bir çerçeve değildir; kaynak künyesi öğrenci yüzeyi değildir.
    data = ornekler.ornek("QUIZ")
    _mcq(data)["questions"][0]["explanation"] = "Kurtuluş Savaşı'nda ordu işgale meydan okudu."
    data["meta"]["sourceCitation"] += " Bilim Olimpiyatları yarışma soruları."
    assert gates.run_gates(derleme.derle(data, {}, ORIGIN))["G-WELLBEING"]["status"] != "FAIL"


def test_rewards_istege_baglidir():
    data = ornekler.ornek("QUIZ")
    data.pop("rewards")
    html = derleme.derle(data, {}, ORIGIN)
    assert gates.run_gates(html)["G-INTERACT"]["status"] != "FAIL"
    data["rewards"] = {}
    derleme.derle(data, {}, ORIGIN)


@pytest.mark.parametrize("rewards, parca", [
    ({"xpPerCorrect": 10, "badges": [{"id": "b1"}]}, "rewards.badges"),
    ([], "rewards"),
    ({"xpPerCorrect": "on"}, "rewards.xpPerCorrect"),
    ({"xpPerCorrect": True}, "rewards.xpPerCorrect"),
    ({"firstTryBonus": -1}, "rewards.firstTryBonus"),
    ({"puan": 3}, "rewards.puan"),
])
def test_rewards_yalniz_ic_sayidir(rewards, parca):
    data = ornekler.ornek("QUIZ")
    data["rewards"] = rewards
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {}, ORIGIN)
    assert exc.value.status == "sema_hatasi"
    assert any(parca in h for h in exc.value.detay["hatalar"]), exc.value.detay["hatalar"]


def test_meta_quest_yazilmaz():
    data = ornekler.ornek("QUIZ")
    data["meta"]["quest"] = {"stations": [{"id": "t1", "label": "Başla"}]}
    with pytest.raises(DerlemeHatasi) as exc:
        derleme.derle(data, {}, ORIGIN)
    assert any("meta.quest" in h for h in exc.value.detay["hatalar"])


@pytest.mark.skipif(shutil.which("node") is None, reason="node yok")
@pytest.mark.parametrize("rewards", ["yok", {}, {"xpPerCorrect": 4, "firstTryBonus": 1}])
def test_motor_rewards_olmadan_sonlu_ic_sayi_tutar(rewards):
    """Bugün `{}` geçerli yazılıyordu ama motor `undefined + 0` ile NaN XP biriktiriyordu."""
    bas = SABLON.index("  const ODUL")
    son = SABLON.index("\n", SABLON.index("function addXP", bas))
    girdi = "{}" if rewards == "yok" else "{rewards:" + json.dumps(rewards) + "}"
    kod = "\n".join([
        f"const D={girdi}; const state={{xp:0}}; function persistSession(){{}} function playSound(){{}}",
        SABLON[bas:son],
        "addXP(ODUL.xpPerCorrect + ODUL.firstTryBonus); addXP(ODUL.xpPerCorrect);",
        "process.stdout.write(JSON.stringify(state.xp));",
    ])
    xp = json.loads(subprocess.run([shutil.which("node"), "-e", kod], capture_output=True, text=True,
                                   check=True, timeout=30).stdout)
    assert isinstance(xp, (int, float)) and xp > 0
    if isinstance(rewards, dict) and rewards:
        assert xp == 4 + 1 + 4


# ── Son inceleme (Küçük 5): tarama arayüz metnine sınırlı ───────────────────

def test_anlatidaki_yarisma_ve_sefer_haritasi_dusurmez():
    """M2.7 "arayüz metni" der: yazarın gövde anlatısı (body, stem, explanation …) taranmaz. Eskiden Osmanlı'nın
    "sefer haritası" ya da "bir yarışma düzenlendi" diyen bir tarih anlatısı G-WELLBEING'den düşüyordu."""
    data = ornekler.ornek("QUIZ")
    teach = next(s for s in data["segments"] if s["type"] == "teach")
    teach["body"] = ["<p>Osmanlı ordusunun sefer haritası Mohaç'a uzanıyordu.</p>",
                     "<p>Okulda bir yarışma düzenlendi; öğrenciler turnuva için hazırlandı.</p>"]
    _mcq(data)["questions"][0]["explanation"] = "Meydan okuma bir cesaret örneğidir."
    assert gates.run_gates(derleme.derle(data, {}, ORIGIN))["G-WELLBEING"]["status"] != "FAIL"


@pytest.mark.parametrize("alan, deger", [
    ("kicker", "Yarışma"), ("instructions", "Meydan oku: en hızlı sen ol!"), ("title", "Kesirler Yarışması"),
    ("title", "Kesir Turnuvası"), ("title", "Liderlik tablosu"), ("title", "Yarış"),
    ("title", "Skor tablosu"), ("kicker", "Sıralama tablosu"), ("title", "Kesir Düellosu"),
])
def test_arayuz_alanlarindaki_rekabet_cercevesi_duser(alan, deger):
    data = ornekler.ornek("QUIZ")
    _mcq(data)[alan] = deger
    rapor = gates.run_gates(derleme.derle(data, {}, ORIGIN))
    assert rapor["G-WELLBEING"]["status"] == "FAIL", (alan, deger)


def test_asama_adi_ve_oz_degerlendirme_secenegi_arayuz_metnidir():
    data = ornekler.ornek("QUIZ")
    ids = [s["id"] for s in data["segments"]]
    data["meta"]["milestones"] = [{"atSegmentId": ids[0], "title": "Keşfet"}, {"atSegmentId": ids[1], "title": "Yarış"},
                                  {"atSegmentId": ids[2], "title": "Pekiştir"}]
    assert gates.run_gates(derleme.derle(data, {}, ORIGIN))["G-WELLBEING"]["status"] == "FAIL"
    data = ornekler.ornek("QUIZ")
    next(s for s in data["segments"] if s["type"] == "checkpoint")["selfAssess"] = ["Yarışmayı kazandım", "Tekrar"]
    assert gates.run_gates(derleme.derle(data, {}, ORIGIN))["G-WELLBEING"]["status"] == "FAIL"


# ── İkinci inceleme (Küçük c): etiket türü arayüz alanları da arayüz metnidir ──

def _wellbeing(module_data: str) -> str:
    """Yalnız G-WELLBEING, derlenmiş modülün biçiminde: içerik MODULE_DATA'da, motor işaretinden önce."""
    vm = gates.validator()
    html = (f"<!doctype html><html lang=\"tr\"><body><script>\nconst MODULE_DATA = {module_data};\n"
            "/* ==========\n   MOTOR (ENGINE) — DEĞİŞTİRMEYİN */\n</script></body></html>")
    sonuc = vm.Result()
    vm.gate_wellbeing(html, sonuc)
    return next(s for g, s, _ in sonuc.rows if g == "G-WELLBEING")


@pytest.mark.parametrize("segment", [
    # Etkileşimli sayı doğrusunun tutamaç etiketi ve okuması
    '{type:"numberline",title:"Sayılar",numberline:{min:0,max:10,interactive:true,interactiveLabel:"Skor tablosu"}}',
    # Simülasyon kaydırıcısının etiketi
    '{type:"sim",title:"Sarkaç",simType:"pendulum",params:[{key:"v",label:"Yarış hızı",min:0,max:10}]}',
    # Sınıflandırmanın kutu adları (düğmeler)
    '{type:"sorting",title:"Ayır",bins:["Turnuva grubu","Antrenman"],items:[{label:"Koşu",bin:0}]}',
    # Tablonun sütun başlığı
    '{type:"teach",title:"Tablo",body:[],visual:{kind:"table",columns:[{label:"Liderlik tablosu"}],rows:[]}}',
])
def test_etiket_turu_arayuz_alanlari_taranir(segment):
    assert _wellbeing("{meta:{title:\"Kesirler\"},segments:[" + segment + "]}") == "FAIL", segment


@pytest.mark.parametrize("segment", [
    # İçerik etiketleri anlatıdır: grafik verisi, sayı doğrusu noktasının adı, sıralanan öğe, seçenek.
    '{type:"teach",title:"Spor",body:[],visual:{kind:"chart",data:[{label:"Yarışma katılımcıları",value:3}]}}',
    '{type:"numberline",title:"Sayılar",numberline:{min:0,max:10,points:[{value:3,label:"Yarış"}]}}',
    '{type:"sorting",title:"Ayır",bins:["Bireysel","Takım"],items:[{label:"Turnuva tenisi",bin:0}]}',
    '{type:"mcq",title:"Soru",questions:[{stem:"Hangisi?",options:["Yarışma","Sergi"],correctIndex:1}]}',
])
def test_icerik_etiketleri_taranmaz(segment):
    assert _wellbeing("{meta:{title:\"Kesirler\"},segments:[" + segment + "]}") != "FAIL", segment
