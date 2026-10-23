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
