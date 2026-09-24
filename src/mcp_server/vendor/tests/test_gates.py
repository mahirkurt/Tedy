# tests/test_gates.py
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import validate_module as vm

def run_gate(gate_fn, html):
    R = vm.Result(); gate_fn(html, R); return R.rows

def status_of(rows, gate_id):
    for g, s, _ in rows:
        if g == gate_id: return s
    return None

def test_harness_imports_existing_gate():
    # mevcut gate_emoji importlanır ve emojisiz girdiye PASS verir
    rows = run_gate(vm.gate_emoji, "<html><body><p>merhaba</p></body></html>")
    assert status_of(rows, "G-EMOJI") == "PASS"

def test_gflow_skips_when_no_gamification():
    rows = run_gate(vm.gate_flow, open("tests/fixtures/minimal_pass.html").read())
    assert status_of(rows, "G-FLOW") == "PASS"  # imza yok → uygulanmaz/PASS

def test_gflow_fail_on_open_curiosity_gap():
    rows = run_gate(vm.gate_flow, open("tests/fixtures/flow_fail_openhook.html").read())
    assert status_of(rows, "G-FLOW") == "FAIL"

def test_gflow_fail_on_loss_streak_language():
    rows = run_gate(vm.gate_flow, open("tests/fixtures/flow_fail_lossstreak.html").read())
    assert status_of(rows, "G-FLOW") == "FAIL"

def test_gflow_pass_on_wellformed_flow():
    rows = run_gate(vm.gate_flow, open("tests/fixtures/flow_pass.html").read())
    assert status_of(rows, "G-FLOW") == "PASS"

def test_gflow_skip_branch_when_truly_no_signature():
    rows = run_gate(vm.gate_flow, open("tests/fixtures/flow_skip_nogami.html").read())
    assert status_of(rows, "G-FLOW") == "PASS"
    # skip branch specifically: message says the gate is not applicable
    msg = next(m for g, s, m in rows if g == "G-FLOW")
    assert "imza yok" in msg or "uygulanmaz" in msg

def test_gcarbongrid_fail_on_static_card_shadow():
    rows = run_gate(vm.gate_carbon_grid, open("tests/fixtures/grid_fail_shadow.html").read())
    assert status_of(rows, "G-CARBON-GRID") == "FAIL"

def test_gcarbongrid_pass_on_layered_flat():
    rows = run_gate(vm.gate_carbon_grid, open("tests/fixtures/grid_pass.html").read())
    assert status_of(rows, "G-CARBON-GRID") in ("PASS", "WARN")

def test_hook_segment_renders_and_closes():
    # hook_pass.html: hand-marked fixture — data-seg="hook" (kanca render'ı) + ayrı
    # data-hook-resolved (hedef teach'in kapanış işareti); gerçek SPA'da bu ikisi hiç
    # aynı statik dosyada bulunmaz (runtime marker'lar), fixture ikisini simüle eder.
    html = open("tests/fixtures/hook_pass.html").read()
    assert 'data-seg="hook"' in html and "data-hook-resolved" in html
    rows = run_gate(vm.gate_flow, html); assert status_of(rows, "G-FLOW") == "PASS"

def test_gain_only_streak_no_reset_language():
    # v3.0.0 Task 9: resetStreak() artık state.streak'i sıfırlamaz (gain-only);
    # yalnızca nötr "korundu" (data-held) işaretine alır — kayıp/ceza dili yok.
    html = open("tests/fixtures/streak_gainonly.html").read()
    rows = run_gate(vm.gate_flow, html); assert status_of(rows, "G-FLOW") == "PASS"
    assert "streak=0" not in html.lower().replace(" ", "")  # resetStreak artık 0'a set etmez

def test_pacingdisk_no_countdown():
    # Task 10: pacing-disk render edilir, data-countdown YOK (sayısız/kesintisiz disk) → G-FLOW PASS
    html = open("tests/fixtures/pacing_pass.html").read()
    rows = run_gate(vm.gate_flow, html); assert status_of(rows, "G-FLOW") == "PASS"

def test_pacingdisk_fail_on_countdown_attribute():
    # değişmez kanıtı: aynı disk öğesine data-countdown eklenirse G-FLOW FAIL vermeli
    html = open("tests/fixtures/pacing_fail_countdown.html").read()
    rows = run_gate(vm.gate_flow, html); assert status_of(rows, "G-FLOW") == "FAIL"

def test_gcarbongrid_spaced_css_shadow_handling():
    # genuine spaced elevation shadow on a static card -> FAIL
    r1 = run_gate(vm.gate_carbon_grid, "<style>.card{box-shadow: 0 2px 6px rgba(0,0,0,.2);}</style>")
    assert status_of(r1, "G-CARBON-GRID") == "FAIL"
    # explicit no-shadow (spaced) must NOT FAIL
    r2 = run_gate(vm.gate_carbon_grid, "<style>.card{box-shadow: none;}</style>")
    assert status_of(r2, "G-CARBON-GRID") != "FAIL"
    # inset border-sim (spaced) must NOT FAIL
    r3 = run_gate(vm.gate_carbon_grid, "<style>.card{box-shadow: inset 0 0 0 2px var(--accent);}</style>")
    assert status_of(r3, "G-CARBON-GRID") != "FAIL"

def test_worked_segment_fixture_has_signature():
    # Task 11: worked_pass.html hand-marked static — renderWorked()'in gerçek çıktısını taklit
    # eder: fadeFrom öncesi salt-görünür adım + fadeFrom sonrası <input aria-label> boşluk.
    html = open("tests/fixtures/worked_pass.html").read()
    assert 'data-seg="worked"' in html
    assert "worked-step--solved" in html and "worked-step--blank" in html
    assert '<input' in html and 'aria-label=' in html

def test_worked_segment_ginteract_ga11y_no_regression():
    # worked bir MCQ değildir (stem/correctIndex yok) → G-INTERACT'in "uygulanmaz" WARN
    # dalına düşmesi regresyon SAYILMAZ (bkz. brief: "do not regress", literal PASS değil —
    # stems==0 iken gate_interact zaten hiçbir modülde FAIL veremez, bkz. validate_module.py).
    # G-A11Y ise bu fixture'ın kendi taşıdığı lang/title/reduced-motion/aria-live/aria-hidden
    # işaretleriyle gerçek PASS almalı (fixture bunun için elle donatıldı).
    html = open("tests/fixtures/worked_pass.html").read()
    rows_i = run_gate(vm.gate_interact, html)
    assert status_of(rows_i, "G-INTERACT") != "FAIL"
    rows_a = run_gate(vm.gate_a11y, html)
    assert status_of(rows_a, "G-A11Y") == "PASS"

def test_worked_zero_blank_not_counted_in_mastery():
    src = open("assets/module-template.html", encoding="utf-8").read()
    # worked contributes to the mastery denominator ONLY when it has a real blank step
    assert 's.fadeFrom < (s.steps||[]).length' in src
    # and the naive always-+1 form must be gone
    assert 'if(s.type==="worked") return n+1;' not in src

def test_selfexplain_segment_fixture_has_signature():
    # Task 12: selfexplain_pass.html hand-marked static — renderSelfExplain()'in gerçek
    # çıktısını taklit eder: istem + serbest/notsuz <textarea aria-label> + "Modeli gör"
    # aç/kapa düğmesi (aria-expanded, klavye-erişilebilir <button>).
    html = open("tests/fixtures/selfexplain_pass.html").read()
    assert 'data-seg="selfExplain"' in html
    assert "<textarea" in html and "aria-label=" in html
    assert 'aria-expanded="false"' in html and "se-reveal" in html

def test_selfexplain_gwellbeing_pass_and_ga11y_no_regression():
    # düşük-baskı metakognisyon: puanlama/ceza dili yok → G-WELLBEING gerçek PASS
    # (yalnızca "uygulanmaz" değil). Fixture kendi lang/title/reduced-motion/aria-live/
    # aria-hidden işaretleriyle G-A11Y'yi de gerçek PASS almalı (elle donatıldı).
    html = open("tests/fixtures/selfexplain_pass.html").read()
    rows_w = run_gate(vm.gate_wellbeing, html)
    assert status_of(rows_w, "G-WELLBEING") == "PASS"
    rows_a = run_gate(vm.gate_a11y, html)
    assert status_of(rows_a, "G-A11Y") == "PASS"

def test_selfexplain_engine_no_scoring_hooks():
    # motorun renderSelfExplain'i addXP/markMastered/bumpStreak'e dokunmamalı (notsuz/ungraded)
    # ve dispatch haritasına bağlanmış olmalı.
    src = open("assets/module-template.html", encoding="utf-8").read()
    i = src.index("function renderSelfExplain")
    j = src.index("\n  }\n", i)
    body = src[i:j]
    assert "addXP(" not in body and "markMastered(" not in body and "bumpStreak(" not in body
    assert "selfExplain:renderSelfExplain" in src

def test_adaptive_difficulty_fixture_has_signature():
    # Task 13: adaptive_pass.html hand-marked static — runQuestionSet()/renderFillblank()'ın
    # tier-uyarlamalı çıktısını taklit eder: ipucu-önce callout (data-adaptive="hint", nötr
    # "İpucu" başlığı) + opsiyonel/atlanabilir meydan okuma butonu (data-adaptive="challenge").
    html = open("tests/fixtures/adaptive_pass.html").read()
    assert 'data-seg="mcq"' in html
    assert 'data-adaptive="hint"' in html and "İpucu" in html
    assert 'data-adaptive="challenge"' in html and "Meydan Oku" in html

def test_adaptive_difficulty_gflow_pass_no_labeling():
    # Taban-korumalı uyarlanır zorluk kullanıcıyı ASLA etiketlemez. Fixture kasıtlı olarak
    # streakChip imzası taşır ki G-FLOW "imza yok → uygulanmaz" atlama dalına değil, gerçek
    # FLOW_LABEL_RE/FLOW_LOSS_RE taramasına girsin — yalnızca o zaman bu test anlamlıdır.
    html = open("tests/fixtures/adaptive_pass.html").read()
    assert "streakChip" in html  # gate_flow'un gerçek tarama dalına girdiğini garanti eder
    rows = run_gate(vm.gate_flow, html)
    assert status_of(rows, "G-FLOW") == "PASS"
    assert not vm.FLOW_LABEL_RE.search(html)
    assert not vm.FLOW_LOSS_RE.search(html)

def test_adaptive_difficulty_gwellbeing_pass():
    # Cezalandırıcı/süre-baskısı dili yok → G-WELLBEING gerçek PASS (yalnızca "uygulanmaz" değil).
    html = open("tests/fixtures/adaptive_pass.html").read()
    rows = run_gate(vm.gate_wellbeing, html)
    assert status_of(rows, "G-WELLBEING") == "PASS"

def test_engine_has_perf_window_and_tier_helpers():
    # state.perf oturumluk depodan güvenle geri yüklenen yuvarlanan pencere +
    # tier/uyarlama yardımcı fonksiyonları motor kaynağında var.
    src = open("assets/module-template.html", encoding="utf-8").read()
    assert "perf:savedSession.perf" in src.replace(" ", "")
    assert 'perf:Array.isArray(obj.perf)?obj.perf.filter(x=>typeofx==="boolean").slice(-5):[]' in src.replace(" ", "")
    for fn in ("function itemTier(", "function perfPush(", "function perfTrailingRun(",
               "function perfMissSignal(", "function perfChallengeSignal(",
               "function tierAdaptSwap(", "function hasTierAhead("):
        assert fn in src

def test_engine_adaptive_layer_gated_by_hastiers():
    # Uyarlama katmanı (hint-önce/tier-takas/meydan-okuma) yalnız segmentte gerçek tier(2|3)
    # varsa erişilebilir — tier'sız modüllerde (mevcutların tamamı) davranış birebir korunur.
    src = open("assets/module-template.html", encoding="utf-8").read()
    flat = src.replace(" ", "").replace("\n", "")
    assert "hasTiers=questions.some(q=>q.tier===2||q.tier===3)" in flat
    assert "hasTiers=s.items.some(x=>x.tier===2||x.tier===3)" in flat
    # hem ipucu/takas hem meydan-okuma dalları hasTiers/missSignal (hasTiers'tan türer) ile korunur
    assert flat.count("hasTiers&&perfChallengeSignal()") == 2
    assert flat.count("missSignal=hasTiers&&perfMissSignal()") == 2

def test_engine_no_labeling_language_in_source():
    # Motor KAYNAĞININ kendisinde de (yalnızca render edilmiş çıktıda değil) FLOW_LABEL_RE'ye
    # eşleşen hiçbir dize yok — uyarlama sessiz kalır (gamified-flows.md §3.3).
    src = open("assets/module-template.html", encoding="utf-8").read()
    assert not vm.FLOW_LABEL_RE.search(src)

def test_engine_untiered_gradekey_identity_preserved():
    # Geriye-uyum kanıtı: gradeKey artık `oi` (order[qi]) üzerinden kurulur, `qi` üzerinden değil —
    # ama tier'sız kümede order kimlik izdüşümünde kaldığından (hasTiers=false → swap hep no-op)
    # oi===qi her zaman doğrudur, yani üretilen gradeKey dizgisi ESKİ modüllerle birebir aynıdır.
    src = open("assets/module-template.html", encoding="utf-8").read()
    assert 'gradeKey=s.id+"#"+oi' in src.replace(" ", "")
    assert 'gk=s.id+"#"+oi' in src.replace(" ", "")

def test_new_segments_have_tts_coverage():
    # Task 14: renderHook, renderWorked, renderSelfExplain her biride ttsRow(...)
    # asil metne uygulu — hook: s.question; worked: steps[0].text; selfExplain: s.prompt.
    src = open("assets/module-template.html", encoding="utf-8").read()
    for func_name in ("renderHook", "renderWorked", "renderSelfExplain"):
        # isimden başlayarak sonraki function'e kadar kesit al
        start_idx = src.index(f"function {func_name}(")
        # sonraki "function " bulana kadar gitme (body'nin sonu)
        next_fn_start = src.index("\n  function ", start_idx + 1)
        body = src[start_idx:next_fn_start]
        # ttsRow çağrısı bu render'da olmalı
        assert "ttsRow(" in body, f"{func_name} ttsRow() çağrısı yok"

def test_spacedrep_degrades_without_storage():
    # Task 15: çapraz-oturum Leitner kutu sistemi — localStorage erişimi HER ZAMAN
    # try/catch ile sarılı olmalı (private mod / kota aşımı / file:// engeli → sessizce
    # null/no-op, asla fırlatmaz) ve IndexedDB KESİNLİKLE kullanılmamalı (file:// üzerinde
    # bloklu bir global kısıt — brief §"Global Constraints").
    src = open("assets/module-template.html", encoding="utf-8").read()
    assert "localStorage" in src, "Leitner localStorage kalıcılığı henüz uygulanmadı"
    # Case-insensitive: gerçek API yüzeyi küçük harfle başlar (indexedDB/IDB*),
    # yalnız "IndexedDB" büyük-küçük eşleşmesi yanlış güven verir.
    assert re.search(r"indexeddb", src, re.I) is None, "IndexedDB motor kaynağında YASAK (file:// bloklu)"
    # en az bir try{...localStorage...}catch bloğu olmalı (lsGet/lsSet güvenli sarmalayıcılar)
    assert re.search(r"try\s*\{[^{}]*localStorage[^{}]*\}\s*catch", src), \
        "localStorage erişimi try/catch ile sarılı değil (degrade-safe olmalı)"

def test_leitner_boxes_persist_and_move_correctly():
    # Task 15: renderFlashcards artık Leitner kutu numarasını (1..5) doğru/tekrar
    # tuşlarında günceller ve her güncellemeden sonra lsSet ile kalıcı hale getirir;
    # motor modül id'sini D.meta.title'dan kararlı biçimde türetir (açık id alanı yok).
    src = open("assets/module-template.html", encoding="utf-8").read()
    start_idx = src.index("function renderFlashcards(")
    next_fn_start = src.index("\n  function ", start_idx + 1)
    body = src[start_idx:next_fn_start]
    assert "lsSet(" in body, "renderFlashcards lsSet() ile kalıcılaştırmıyor"
    assert "state.leitner" in body, "renderFlashcards state.leitner'ı kullanmıyor"
    assert "Math.min(5" in body, "kutu üst sınırı (5) yok — doğru tuşu üst kutuya taşımıyor"
    # D.meta.title'dan kararlı modül-anahtarı türetimi (açık modül id'si yok)
    assert re.search(r"D\.meta\s*&&\s*D\.meta\.title", src), \
        "modül kimliği D.meta.title'dan türetilmeli"
    assert '"edupedia:"' in src and '":leitner"' in src

def test_leitner_degrade_preserves_card_count():
    # Backward-compat/degrade garantisi: kutu-öncelikli sıralama kart SAYISINI hiçbir
    # zaman değiştirmez/atlamaz — yalnız gösterim SIRASINI önceliklendirir. Bu yüzden
    # totalGradeable/mastery paydası (s.cards.length) motor içinde DEĞİŞMEDEN kalmalı.
    src = open("assets/module-template.html", encoding="utf-8").read()
    assert 'if(s.type==="flashcards") return n+s.cards.length;' in src

def test_mathml_fixture_ga11y_and_selfcontained_pass():
    # Task 16: mathml_pass.html — teach body'sine gömülü inline native <math> (kök formülü)
    # + visual:{kind:"mathml"} eşdeğeri bir <figure class="viz"> matris bloğu içerir.
    # Motor `body`'yi ham (esc()'siz) innerHTML olarak yazdığından (bkz. investigation notu
    # aşağıda) hiçbir whitelist değişikliği gerekmedi; bu test yalnızca MathML'in gate'leri
    # gerçekten GEÇTİĞİNİ kanıtlar: G-A11Y (lang/title/reduced-motion/aria-live/aria-hidden)
    # ve G-SELFCONTAINED (MathML sıfır src/href taşır — tarayıcı-yerli, harici bağımlılık yok).
    html = open("tests/fixtures/mathml_pass.html").read()
    assert "<math" in html and "</math>" in html
    rows_a = run_gate(vm.gate_a11y, html)
    assert status_of(rows_a, "G-A11Y") == "PASS"
    rows_s = run_gate(vm.gate_selfcontained, html)
    assert status_of(rows_s, "G-SELFCONTAINED") == "PASS"

def test_mathml_fixture_no_interactive_or_link_attributes():
    # Güvenlik: MathML içeriği yalnız yapısal etiketlerdir — olay-tutucu (on*) veya
    # href/xlink:href YOK (body ham-HTML olduğundan sanitizer yok; disiplin yazar
    # sorumluluğudur — brief'in "no XSS surface introduced" şartı).
    # Not: HTML yorumları (açıklayıcı prova metni "<math>"/"href" sözcüklerinden söz
    # edebilir) taramadan ÖNCE çıkarılır — yoksa yorum-metni yanlış-pozitif üretir.
    html = open("tests/fixtures/mathml_pass.html").read()
    html_no_comments = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    math_blocks = re.findall(r"<math\b.*?</math>", html_no_comments, re.S)
    assert math_blocks, "fixture'da <math> bloğu bulunamadı"
    for block in math_blocks:
        assert not re.search(r'\bon[a-z]+\s*=', block, re.I), "MathML içinde olay-tutucu (on*) bulundu"
        assert "href" not in block.lower(), "MathML içinde href/xlink:href bulundu"
        assert "<script" not in block.lower()

def test_engine_mathml_helper_wired_and_mathexpr_default_unchanged():
    # Task 16 investigation: renderTeach()'in `.body` işleyişi ham join + innerHTML'dir
    # (esc()'ten GEÇMEZ) — bu yüzden <math> zaten motor değişikliği olmadan render olur.
    # Bu test iki şeyi kanıtlar: (1) yeni mathmlFigure() yardımcısı tanımlı ve
    # visual:{kind:"mathml"} dispatch'ine bağlı; (2) mathExpr()'in KENDİSİ (varsayılan
    # dizgi motoru) satır satır değişmeden kalmış — yalnız mathFigure'dan SONRA katkı
    # olarak eklendi, mevcut "math" kind dalına dokunulmadı.
    src = open("assets/module-template.html", encoding="utf-8").read()
    # (1) yeni yardımcı tanımlı ve visual:{kind:"mathml"} dispatch'ine bağlı
    assert "function mathmlFigure(mathml, caption)" in src
    assert 'html+=mathmlFigure(s.visual.math||s.visual.ref||"", s.visual.caption);' in src
    # (2) mathExpr varsayılan dal ve gövdesi dokunulmadan duruyor (satır satır aynı)
    assert 'kind==="math") html+=mathFigure(s.visual.expr||s.visual.ref||"", s.visual.caption);' in src
    i = src.index("function mathExpr(src)")
    j = src.index("\n  }\n", i)
    body = src[i:j]
    assert "esc(String(src))" in body
    assert "sqrt" in body
    assert "\\frac" in body  # kaynaktaki gerçek iki-ters-eğik-çizgi dizisi (regex literal \\frac)
    # .body render yolu: raw join, esc() YOK (whitelist/sanitizer olmadığının kanıtı)
    assert 'html += `<div class="seg-body">${(s.body||[]).join("")}</div>`;' in src

def test_sim_fixture_has_signature():
    # Task 17: sim_pass.html hand-marked static — renderSim()'in gerçek çıktısını
    # taklit eder: data-seg="sim" + klavye-erişilebilir <input type=range aria-label>
    # kaydırıcı(lar) + canlı <output aria-live="polite"> değer okuması + role="img"
    # taşıyan SVG kanvası (gerçek motorda SIM_PRESETS tarafından çizilir).
    html = open("tests/fixtures/sim_pass.html").read()
    assert 'data-seg="sim"' in html
    assert '<input type="range"' in html and "aria-label=" in html
    assert "<output" in html and 'aria-live="polite"' in html
    assert 'id="simSvg"' in html and 'role="img"' in html and "<title" in html

def test_sim_fixture_ga11y_and_gsvg_pass():
    # G-A11Y: lang/title/reduced-motion/aria-live/rol işaretleri elle donatıldı ki
    # bu fixture gerçek PASS alsın (yalnızca "uygulanmaz" değil). G-SVG: sim
    # kanvası role="img" + <title> taşır; dekoratif ikon svg'leri aria-hidden ile
    # doğru dışlanır (ham hex renk yok — token'lı).
    html = open("tests/fixtures/sim_pass.html").read()
    rows_a = run_gate(vm.gate_a11y, html)
    assert status_of(rows_a, "G-A11Y") == "PASS"
    rows_s = run_gate(vm.gate_svg, html)
    assert status_of(rows_s, "G-SVG") == "PASS"

def test_sim_engine_wired_and_presets_defined():
    # SIM_PRESETS motor-içi SABİT bir preset kütüphanesidir (MODULE_DATA kod
    # taşımaz — yalnız simType+params seçer); renderSim dispatch'e bağlıdır;
    # 5 başlangıç preset'inin tamamı tanımlı.
    src = open("assets/module-template.html", encoding="utf-8").read()
    assert "const SIM_PRESETS" in src
    for name in ("pendulum", "projectile", "wave", "numberScale", "functionPlot"):
        assert re.search(re.escape(name) + r"\s*:\s*\(", src), f"SIM_PRESETS.{name} tanımlı değil"
    assert "sim:renderSim" in src
    assert "function renderSim(stage,s)" in src

def test_sim_unknown_simtype_graceful_no_crash():
    # Bilinmeyen simType → nazik/uydurmasız not, kaydırıcı/SVG hiç kurulmaz —
    # çökme yok (brief: "no fabrication, no crash"). Segment keşfedici/puanlanmaz:
    # addXP/markMastered/bumpStreak dokunuşu yok (selfExplain ile aynı ilke).
    src = open("assets/module-template.html", encoding="utf-8").read()
    start_idx = src.index("function renderSim(stage,s)")
    next_fn_start = src.index("\n  function ", start_idx + 1)
    body = src[start_idx:next_fn_start]
    assert "Bu simülasyon için hazır şablon yok." in body
    assert "if(!preset)" in body
    assert "addXP(" not in body and "markMastered(" not in body and "bumpStreak(" not in body

def test_sim_presets_no_raw_hex_colors():
    # Token yetkesi: preset'ler yalnız var(--...)/currentColor kullanır, ham hex renk yok.
    src = open("assets/module-template.html", encoding="utf-8").read()
    i = src.index("const SIM_PRESETS")
    j = src.index("function renderSim(stage,s)", i)
    block = src[i:j]
    assert not re.search(r'(?:fill|stroke)\s*=\s*"#[0-9a-fA-F]{3,6}"', block)

def test_sim_new_segment_has_tts_coverage():
    # Task 14'ün "Task 17/18 renderer'lar ttsRow taşımalı" notu (bkz. render()
    # üstü yorum) — renderSim birincil metne (instructions/title) ttsRow uygular.
    src = open("assets/module-template.html", encoding="utf-8").read()
    start_idx = src.index("function renderSim(stage,s)")
    next_fn_start = src.index("\n  function ", start_idx + 1)
    body = src[start_idx:next_fn_start]
    assert "ttsRow(" in body

def test_sim_unknown_simtype_uses_ownproperty_guard():
    # Prototype collision guard: builtin-named simType (e.g. "constructor", "toString",
    # "hasOwnProperty") must not bypass the graceful-note guard by resolving to
    # inherited Object.prototype members. The lookup must use an own-property + function-type guard.
    src = open("assets/module-template.html", encoding="utf-8").read()
    # builtin-named simType must not bypass — guard must be in place
    assert "Object.prototype.hasOwnProperty.call(SIM_PRESETS" in src
    # unsafe direct lookup must be gone
    assert "const preset = SIM_PRESETS[s.simType];" not in src

def test_conceptmap_fixture_has_signature():
    # Task 18: conceptmap_pass.html hand-marked static — renderConceptMap()'in gerçek
    # çıktısını taklit eder: data-seg="conceptMap" + klavye-erişilebilir düğüm
    # <button aria-label> (aria-pressed durum) + kenar metin listesi (her satırda
    # klavye-erişilebilir "kaldır" <button aria-label>) + "Kontrol et" düğmesi.
    html = open("tests/fixtures/conceptmap_pass.html").read()
    assert 'data-seg="conceptMap"' in html
    assert 'class="cmap-node' in html and "aria-pressed=" in html
    assert html.count("<button") >= 4 + 2 + 1  # >=4 düğüm + >=2 kaldır + 1 Kontrol et
    assert 'id="cmapEdgeList"' in html and 'id="cmapCheckBtn"' in html

def test_conceptmap_fixture_not_drag_dependent():
    # KRİTİK erişilebilirlik şartı: sürükle-bırak İMZASI fixture'da hiç YOK —
    # klavye/tıklama (gerçek <button>) TEK yol olarak kanıtlanır (drag-only = FAIL).
    # Not: HTML yorumları (açıklayıcı prova metni "draggable" sözcüğünden söz
    # edebilir) taramadan ÖNCE çıkarılır — yoksa yorum-metni yanlış-pozitif üretir
    # (mathml_pass.html testindeki aynı desen, bkz. test_mathml_fixture_no_interactive_or_link_attributes).
    html = open("tests/fixtures/conceptmap_pass.html").read()
    html_no_comments = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    low = html_no_comments.lower()
    for token in ("draggable", "dragstart", "dragover", "ondrop", "data-drag"):
        assert token not in low, f"fixture'da sürükle-bırak izi bulundu: {token}"
    # düğümler gerçek <button> — role=button taklidi (div+tabindex) değil
    assert '<button type="button" class="cmap-node' in html

def test_conceptmap_fixture_ga11y_pass():
    # G-A11Y: lang/title/reduced-motion/aria-live/görsel-rol işaretleri elle
    # donatıldı ki bu fixture gerçek PASS alsın (yalnızca "uygulanmaz" değil).
    html = open("tests/fixtures/conceptmap_pass.html").read()
    rows = run_gate(vm.gate_a11y, html)
    assert status_of(rows, "G-A11Y") == "PASS"

def test_conceptmap_fixture_gwellbeing_pass():
    # Eksik/fazla kenar geri bildirimi nazik/cezasız metin taşır → G-WELLBEING PASS.
    html = open("tests/fixtures/conceptmap_pass.html").read()
    rows = run_gate(vm.gate_wellbeing, html)
    assert status_of(rows, "G-WELLBEING") == "PASS"

def test_conceptmap_engine_wired_and_dispatch():
    # renderConceptMap tanımlı ve dispatch haritasına conceptMap anahtarıyla bağlı.
    src = open("assets/module-template.html", encoding="utf-8").read()
    assert "function renderConceptMap(stage,s)" in src
    assert "conceptMap:renderConceptMap" in src

def test_conceptmap_no_dragdrop_code_keyboard_is_the_path():
    # Motorun renderConceptMap GÖVDESİ hiçbir sürükle-bırak olay-tutucusu
    # taşımamalı — klavye/tıklama (gerçek <button> + native click) BİRİCİK
    # yoldur, sürükle-bırak bu sürümde hiç eklenmedi (brief: "drag-only = FAIL",
    # burada tam tersi kanıtlanıyor: drag YOK, klavye tek/tam yol).
    src = open("assets/module-template.html", encoding="utf-8").read()
    start_idx = src.index("function renderConceptMap(stage,s)")
    next_fn_start = src.index("\n  function ", start_idx + 1)
    body = src[start_idx:next_fn_start]
    for token in ("dragstart", "dragover", "ondrop", "draggable", "addEventListener(\"drag"):
        assert token not in body, f"renderConceptMap gövdesinde sürükle-bırak kodu bulundu: {token}"
    # düğümler gerçek <button> olarak render edilir (Enter/Space native click üretir)
    assert '<button type="button" class="cmap-node"' in body

def test_conceptmap_edge_removal_is_keyboard_operable_button():
    # "Kaldır" kontrolü gerçek bir <button aria-label> olmalı (klavye-erişilebilir);
    # yalnızca tıklamayla çalışan bir div/span değil.
    src = open("assets/module-template.html", encoding="utf-8").read()
    start_idx = src.index("function renderConceptMap(stage,s)")
    next_fn_start = src.index("\n  function ", start_idx + 1)
    body = src[start_idx:next_fn_start]
    assert 'class="cmap-edge__remove"' in body
    assert '<button type="button" class="cmap-edge__remove"' in body

def test_conceptmap_edgeeq_order_independent_and_totalgradeable_pairing():
    # Task 18 brief: order-independent kenar eşitliği ([A,B]===[B,A]) + worked'in
    # fadeFrom-boş-korumasıyla BİREBİR aynı totalGradeable/markMastered eşleme
    # ilkesi (gerçek bir targetEdges varsa +1, yoksa +0 — alt-öğe başına DEĞİL).
    src = open("assets/module-template.html", encoding="utf-8").read()
    assert 'if(s.type==="conceptMap") return n + ((s.targetEdges&&s.targetEdges.length)?1:0);' in src
    start_idx = src.index("function renderConceptMap(stage,s)")
    next_fn_start = src.index("\n  function ", start_idx + 1)
    body = src[start_idx:next_fn_start]
    assert "function edgeEq(e1,e2){ return (e1[0]===e2[0]&&e1[1]===e2[1])||(e1[0]===e2[1]&&e1[1]===e2[0]); }" in body
    # gk=s.id (worked ile aynı — tek/toplu grade-key, kenar başına DEĞİL)
    assert "const gk=s.id;" in body
    assert "markMastered();" in body
    assert "state.awarded.has(gk)" in body

def test_conceptmap_no_award_unless_all_correct_and_no_extra():
    # "Tümü doğru" = eksiksiz VE fazlasız (missing.length ve extra.length ikisi de
    # sıfır) — yalnızca eksik==0 kontrolü YETERSİZ olurdu (fazla kenarları görmezden
    # gelirdi). addXP/markMastered çağrısı bu koşulun İÇİNDE olmalı.
    src = open("assets/module-template.html", encoding="utf-8").read()
    start_idx = src.index("function renderConceptMap(stage,s)")
    next_fn_start = src.index("\n  function ", start_idx + 1)
    body = src[start_idx:next_fn_start]
    i = body.index("if(!missing.length && !extra.length){")
    j = body.index("markMastered();", i)
    assert j > i  # markMastered yalnızca eksiksiz+fazlasız dalının İÇİNDE çağrılır

def test_conceptmap_graceful_no_crash_on_insufficient_data():
    # En az 2 düğüm veya boş targetEdges → nazik/uydurmasız bilgi notu (sim'in
    # bilinmeyen-simType dalıyla aynı desen), çökme yok; next hep etkin.
    src = open("assets/module-template.html", encoding="utf-8").read()
    start_idx = src.index("function renderConceptMap(stage,s)")
    next_fn_start = src.index("\n  function ", start_idx + 1)
    body = src[start_idx:next_fn_start]
    assert "if(nodes.length<2 || !targets.length){" in body
    assert "Bu kavram haritası için yeterli veri yok." in body
    assert "addXP(" not in body.split("if(nodes.length<2")[0]  # guard öncesinde ödül yok

def test_conceptmap_new_segment_has_tts_coverage():
    # Task 14'ün ttsRow-hatırlatma yorumu artık gereksiz (Task 18 tamamlandı) —
    # renderConceptMap birincil metne (instructions/title) ttsRow uygular.
    src = open("assets/module-template.html", encoding="utf-8").read()
    start_idx = src.index("function renderConceptMap(stage,s)")
    next_fn_start = src.index("\n  function ", start_idx + 1)
    body = src[start_idx:next_fn_start]
    assert "ttsRow(" in body

def test_conceptmap_forward_note_retired():
    # Task 14 motorda bıraktığı "Task 18 ... henüz yapılmadı" ileri-referans yorumu
    # artık YOK — Task 18 tamamlandığından iz bırakılmadı (sim'in Task 17'de kendi
    # notunu güncellemesiyle aynı disiplin).
    src = open("assets/module-template.html", encoding="utf-8").read()
    assert "Task 18 (conceptMap renderer)" not in src

def test_conceptmap_css_no_raw_hex_colors():
    # Token yetkesi: .cmap-* kuralları yalnız var(--...) kullanır, ham hex renk yok.
    src = open("assets/module-template.html", encoding="utf-8").read()
    i = src.index(".cmap-field{")
    j = src.index("/* ===== işlevsel renk: etkinlik-tipine göre wayfinding", i)
    block = src[i:j]
    assert not re.search(r':\s*#[0-9a-fA-F]{3,6}\b', block)

def test_conceptmap_css_no_static_card_shadow():
    # G-CARBON-GRID: .cmap-* kuralları yalnız inset box-shadow kullanır (statik
    # kartta gerçek drop-shadow yok — layer-elevation ihlali olmaz).
    src = open("assets/module-template.html", encoding="utf-8").read()
    i = src.index(".cmap-field{")
    j = src.index("/* ===== işlevsel renk: etkinlik-tipine göre wayfinding", i)
    block = src[i:j]
    for m in re.finditer(r'box-shadow\s*:\s*([^;]+);', block):
        assert m.group(1).strip().startswith("inset"), f"non-inset box-shadow: {m.group(1)}"

def test_conceptmap_wayfinding_accent_added():
    # conceptMap, "senin sıran" wayfinding grubundadır (match/order/sorting/hotspot ile aynı
    # görsel dil): ikon karosu ders ailesinin dolu aksanı, ikon onAccent (color-system.md §3).
    src = open("assets/module-template.html", encoding="utf-8").read()
    assert ('.stage[data-seg="hotspot"],.stage[data-seg="conceptMap"],.stage[data-seg="flashcards"]'
            '{--seg-ic-bg:var(--subject-accent);--seg-ic-fg:var(--subject-on-accent)}') in src

def test_validate_module_conceptmap_aspect_ratio_flips_warning_to_pass():
    # Yan-etki: .cmap-field{aspect-ratio:3/2} eklenmesiyle G-CARBON-GRID'in
    # önceden var olan (Task 7/9/16'dan beri izlenen) "aspect-ratio kullanılmıyor"
    # UYARISI artık PASS'e döner — regresyon değil, gerçek bir iyileştirme.
    html = open("assets/module-template.html", encoding="utf-8").read()
    rows = run_gate(vm.gate_carbon_grid, html)
    assert status_of(rows, "G-CARBON-GRID") == "PASS"

def test_numberline_interactive_fixture_has_signature():
    # Task 19: numberline_interactive_pass.html hand-marked static — numberLine()'ın
    # interactive:true dalının gerçek çıktısını taklit eder: dıştaki svg'ye
    # data-nl-handle/-min/-max/-step öznitelikleri + gerçek bir role="slider"
    # tabindex="0" <circle> + aria-valuemin/max/now + aria-label, ve görünür bir
    # aria-live okuma satırı (nl-readout).
    html = open("tests/fixtures/numberline_interactive_pass.html").read()
    assert 'data-seg="numberline"' in html
    assert 'data-nl-handle=' in html and 'data-nl-min=' in html and 'data-nl-max=' in html and 'data-nl-step=' in html
    assert 'class="nl-handle"' in html and 'role="slider"' in html and 'tabindex="0"' in html
    assert 'aria-valuemin=' in html and 'aria-valuemax=' in html and 'aria-valuenow=' in html and 'aria-label=' in html
    assert 'class="nl-readout"' in html and 'aria-live="polite"' in html

def test_numberline_interactive_not_drag_dependent():
    # WCAG 2.1 AA: pointer sürükle yalnız isteğe bağlı bir zenginleştirme olabilir,
    # asla TEK yol olamaz. Bu fixture kasıtlı olarak hiçbir draggable/dragstart
    # işareti taşımaz — klavye (role=slider + tabindex + ok-tuşu) BİRİNCİL/TAM yoldur.
    html = open("tests/fixtures/numberline_interactive_pass.html").read()
    html_no_comments = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    low = html_no_comments.lower()
    for token in ("draggable", "dragstart", "dragover", "ondrop", "data-drag"):
        assert token not in low, f"fixture'da sürükle-bırak izi bulundu: {token}"

def test_numberline_interactive_ga11y_and_gsvg_pass():
    # G-A11Y: lang/title/reduced-motion/aria-live/görsel-rol işaretleri elle
    # donatıldı ki bu fixture gerçek PASS alsın. G-SVG: figür svg role="img" +
    # <title> taşır; handle dolgusu token'lı (ham hex yok).
    html = open("tests/fixtures/numberline_interactive_pass.html").read()
    rows_a = run_gate(vm.gate_a11y, html)
    assert status_of(rows_a, "G-A11Y") == "PASS"
    rows_s = run_gate(vm.gate_svg, html)
    assert status_of(rows_s, "G-SVG") == "PASS"

def test_numberline_engine_interactive_branch_gated_by_spec_interactive():
    # numberLine(spec)'in interactive üretimi TAMAMEN `if(spec.interactive){...}`
    # bloğunun içinde olmalı — bayrak yoksa handle/readout/nlAttrs boş dizge kalır.
    src = open("assets/module-template.html", encoding="utf-8").read()
    i = src.index("function numberLine(spec)")
    j = src.index("\n  function wireNumberlineInteractive", i)
    body = src[i:j]
    assert 'if(spec.interactive){' in body
    assert 'let handle="", readout="", nlAttrs="";' in body
    # svg açılış etiketi interactive olmayanda hiçbir ek öznitelik almaz (nlAttrs="")
    assert 'aria-labelledby="${tid} ${did}"${nlAttrs}>' in body
    assert 'return svgFigure(svg, spec.caption) + readout;' in body

def test_numberline_static_path_byte_unchanged_when_interactive_absent():
    # Geriye-uyum: interactive olmayan çağrıda (spec.interactive absent/false)
    # numberLine()'ın ürettiği SVG, Task 19 öncesi ile BYTE-İÇİN-BYTE aynı olmalı —
    # yani interactive dalı çalıştırılmadığında handle/readout/nlAttrs katkısı
    # tamamen boş dizgedir ve orijinal svg açılış/gövde şablonu hiç değişmemiştir.
    src = open("assets/module-template.html", encoding="utf-8").read()
    assert (
        'const svg=`<svg class="viz" viewBox="0 0 ${W} ${H}" role="img" '
        'aria-labelledby="${tid} ${did}"${nlAttrs}><title id="${tid}">${esc(spec.title||"Sayı doğrusu")}</title>'
        '<desc id="${did}">${esc(spec.desc||spec.title||"")}</desc>${hi}${axis}${ticks}${pts}${handle}</svg>`;'
    ) in src
    # handle/readout/nlAttrs `let ...="";` ile boş başlar ve YALNIZ aşağıdaki
    # `if(spec.interactive){...}` bloğunun İÇİNDE yeniden atanır — bloğun dışında
    # koşulsuz bir atama yoksa spec.interactive=false/absent iken üçü de "" kalır,
    # yani svg şablonuna hiçbir katkı yapmazlar (yukarıdaki şablon dizgesiyle kanıtlı).
    i = src.index("function numberLine(spec)")
    j = src.index("\n  function wireNumberlineInteractive", i)
    body = src[i:j]
    assert 'let handle="", readout="", nlAttrs="";' in body
    block_start = body.index("if(spec.interactive){")
    block_end = body.index("\n    }\n", block_start)
    before_block = body[:block_start]
    inner_block = body[block_start:block_end]
    after_block = body[block_end:]
    for name in ("handle=", "readout=", "nlAttrs="):
        assert name in inner_block.replace(" ", ""), f"{name} interactive bloğunda atanmıyor"
        assert name not in before_block.replace(" ", "").replace('lethandle="",readout="",nlAttrs="";', "")
        assert name not in after_block.replace(" ", "")

def test_numberline_engine_wired_and_keyboard_mandatory():
    # renderNumberline dispatch'e bağlı ve interactive iken wireNumberlineInteractive
    # çağrılır; klavye (ArrowLeft/ArrowRight/Home/End) ZORUNLU/birincil yol, pointer
    # sürükle yalnız yanında opsiyonel bir zenginleştirmedir.
    src = open("assets/module-template.html", encoding="utf-8").read()
    assert "numberline:renderNumberline" in src
    assert "if(nlSpec.interactive) wireNumberlineInteractive(stage, nlSpec);" in src
    start_idx = src.index("function wireNumberlineInteractive(stage, spec)")
    next_fn_start = src.index("\n  function ", start_idx + 1)
    body = src[start_idx:next_fn_start]
    for key in ("ArrowRight", "ArrowLeft", "Home", "End"):
        assert key in body, f"klavye adımı {key} eksik"
    assert 'addEventListener("keydown"' in body
    assert 'addEventListener("pointerdown"' in body  # opsiyonel zenginleştirme, klavyenin yanında

def test_numberline_reduce_motion_instant():
    # reduceMotion() reuse edilir: hareket-azaltma tercih edilince handle.style.transition
    # anında ("none") ayarlanır (CSS'teki prefers-reduced-motion:no-preference geçiş
    # kısıtlamasının JS tarafındaki ikinci/açık garantisi).
    src = open("assets/module-template.html", encoding="utf-8").read()
    start_idx = src.index("function wireNumberlineInteractive(stage, spec)")
    next_fn_start = src.index("\n  function ", start_idx + 1)
    body = src[start_idx:next_fn_start]
    assert 'if(reduceMotion()) handle.style.transition = "none";' in body
    # CSS: .nl-handle geçişi yalnız hareket-azaltma TERCİH EDİLMEDİĞİNDE tanımlı
    css_i = src.index(".nl-handle{")
    css_block = src[css_i:src.index("\n.nl-readout{", css_i)]
    assert "@media (prefers-reduced-motion:no-preference){" in css_block

def test_numberline_css_no_raw_hex_colors():
    # Token yetkesi: .nl-* kuralları yalnız var(--...) kullanır, ham hex renk yok.
    src = open("assets/module-template.html", encoding="utf-8").read()
    i = src.index(".nl-handle{")
    j = src.index(".viz-legend i{") if src.index(".viz-legend i{") < i else src.index("\n.nl-readout{", i)
    # .nl-* bloğu .viz-legend i{...} kuralından SONRA eklendi; sınırları doğrudan al
    block_start = src.index(".nl-handle{")
    block_end = src.index("/* yüksek-etki ama sakin", block_start)
    block = src[block_start:block_end]
    assert not re.search(r':\s*#[0-9a-fA-F]{3,6}\b', block)

def test_numberline_css_no_static_card_shadow():
    # G-CARBON-GRID: .nl-* kuralları statik kartta gerçek drop-shadow taşımaz
    # (bu görsel öğe için hiç box-shadow tanımlanmadı — zaten inset dahi yok).
    src = open("assets/module-template.html", encoding="utf-8").read()
    block_start = src.index(".nl-handle{")
    block_end = src.index("/* yüksek-etki ama sakin", block_start)
    block = src[block_start:block_end]
    assert "box-shadow" not in block or all(
        m.group(1).strip().startswith("inset") for m in re.finditer(r'box-shadow\s*:\s*([^;]+);', block)
    )

def test_full_template_passes_13_gates_with_new_segments():
    # Task 22: 13-kapı tam entegrasyon — module-template.html'in demo MODULE_DATA'sı
    # artık hook/worked/selfExplain/sim/conceptMap'in birer canlı örneğini taşır ve
    # tüm 13 kapıdan (11 orijinal + G-FLOW + G-CARBON-GRID) sıfır İHLAL ile geçer.
    import subprocess
    r = subprocess.run(["python3", "scripts/validate_module.py", "assets/module-template.html"],
                        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout   # hiç FAIL yok
    for g in ["G-FLOW", "G-CARBON-GRID"]:
        assert g in r.stdout

def test_teach_numberline_visual_forces_static():
    # WCAG 2.1.1 regression guard: renderTeach's generic visual.kind==="numberline"
    # path calls numberLine(...) inline but is never followed by
    # wireNumberlineInteractive(...) — so an author-supplied interactive:true spec
    # would otherwise produce a focusable role="slider" handle with zero keyboard/
    # pointer handlers ("dead slider"). This path must strip interactive before
    # calling numberLine, regardless of what the author's spec says.
    src = open("assets/module-template.html", encoding="utf-8").read()
    assert 'numberLine(Object.assign({}, s.visual, {interactive:false}))' in src
    # the real type:"numberline" segment (renderNumberline) must stay wired and untouched
    assert 'html+=numberLine(nlSpec);' in src
    assert 'if(nlSpec.interactive) wireNumberlineInteractive(stage, nlSpec);' in src

def test_gsvg_ignores_svg_fragments_inside_comments():
    # Deferred-minor Fix 2: gate_svg's SVG_BLOCK_RE is non-greedy but scans the
    # WHOLE file text, so an illustrative <svg>...</svg> fragment sitting inside a
    # /* ... */ JS block comment (or an <!-- ... --> HTML comment) could bleed to a
    # distant real </svg> and trip a false G-SVG finding. The scan must run on a
    # comment-stripped working copy so comment-embedded fragments are ignored.
    html_js_comment = '''<html><body>
    <script>
    /* örnek şekil, gerçek DOM değil: <svg viewBox="0 0 10 10"><rect/></svg> */
    var x = 1;
    </script>
    </body></html>'''
    rows = run_gate(vm.gate_svg, html_js_comment)
    assert status_of(rows, "G-SVG") == "PASS"
    msg = next(m for g, s, m in rows if g == "G-SVG")
    assert "Figür SVG yok" in msg  # checked==0 dalı — yorumdaki parça hiç sayılmadı

    html_html_comment = '''<html><body>
    <!-- örnek: <svg viewBox="0 0 10 10"><rect/></svg> -->
    <p>içerik</p>
    </body></html>'''
    rows2 = run_gate(vm.gate_svg, html_html_comment)
    assert status_of(rows2, "G-SVG") == "PASS"

def test_gsvg_still_catches_real_inaccessible_svg_outside_comments():
    # Guard against the comment-stripping fix (Fix 2) accidentally neutering the
    # gate for genuine, non-commented figure SVGs.
    html = '''<html><body>
    <svg viewBox="0 0 10 10"><rect fill="var(--accent)"/></svg>
    </body></html>'''
    rows = run_gate(vm.gate_svg, html)
    assert status_of(rows, "G-SVG") == "FAIL"

def test_numberline_w_padx_share_one_constant_source():
    # Deferred-minor Fix 4: wireNumberlineInteractive used to hardcode its own
    # W=480/PADX=28 literals, duplicating numberLine's X(v) scale constants — a
    # silent-drift risk if one changes without the other. Both must now read a
    # single shared source (NL_W/NL_PADX), and the scale itself must stay 480/28.
    src = open("assets/module-template.html", encoding="utf-8").read()
    assert "const NL_W=480, NL_PADX=28;" in src, "paylaşımlı NL_W/NL_PADX sabiti bulunamadı"

    i = src.index("function numberLine(spec)")
    j = src.index("\n  function wireNumberlineInteractive", i)
    numberline_body = src[i:j].replace(" ", "")
    assert "W=NL_W" in numberline_body and "PADX=NL_PADX" in numberline_body
    assert "W=480" not in numberline_body and "PADX=28" not in numberline_body

    k = src.index("function wireNumberlineInteractive(stage, spec)")
    next_fn = src.index("\n  function ", k + 1)
    wire_body = src[k:next_fn].replace(" ", "")
    assert "W=NL_W" in wire_body and "PADX=NL_PADX" in wire_body
    assert "W=480" not in wire_body and "PADX=28" not in wire_body


# ── G-VERIFY (v3.5.0) ────────────────────────────────────────────────────────
# Kullanıcı sözleşmesi (2026-07-17): içerik KAPSAM + DOĞRULUK denetiminden geçmeden
# canlıya alınmaz. Yargıyı MODEL yapar (Python "bilimsel olarak doğru mu" diyemez);
# bu kapı YAPIYI denetler — her iddianın dayanağı GÖSTERİLMİŞ mi. Kapının değeri:
# iddiayı yazmak dayanağını yazmayı zorunlu kılar → "denetledim" tiyatrosu imkânsızlaşır.
#
# Kapı DOĞRULUĞU kanıtlamaz; bunu iddia eden bir test yazmak kapıya fazla güven yükler.

_VERIF_OK = '''
  meta: { sourceCitation: "MEB Fen Bilimleri 5, s. 115" },
  mode: "CURRICULUM",
  curriculum: { outcomes: [{ code: "FB.5.3.1.1", text: "...", mappedTo: ["s1"] }] },
  verification: {
    frame_source: { kind: "textbook", document_id: 197, pages: "112-120" },
    scope: { in_frame: true, excluded: [] },
    claims: [
      { claim: "Hucre zari secici gecirgendir",
        grounding: { document_id: 197, page: 115 }, verdict: "supported" }
    ]
  },
'''

def _mod(body):
    return '<html><body><script>const MODULE_DATA = {' + body + '};</script></body></html>'


def test_gverify_skips_for_non_curriculum_module():
    rows = run_gate(
        vm.gate_verify,
        _mod(
            'meta: { sourceCitation: "Kullanıcının sağladığı ders notu" }, '
            'mode: "FREEFORM", segments: [{id:"s1"}]'
        ),
    )
    assert status_of(rows, "G-VERIFY") in (None, "PASS")


def test_gverify_fails_when_verification_block_missing():
    """CURRICULUM modunda denetim kaydı yoksa yayınlanamaz."""
    rows = run_gate(
        vm.gate_verify,
        _mod(
            'meta: { sourceCitation: "MEB Fen Bilimleri 5" }, '
            'mode: "CURRICULUM", curriculum: { outcomes: [] },'
        ),
    )
    assert status_of(rows, "G-VERIFY") == "FAIL"
    assert "verification" in next(message for gate, _, message in rows if gate == "G-VERIFY")


def test_gverify_passes_on_wellformed_block():
    rows = run_gate(vm.gate_verify, _mod(_VERIF_OK))
    assert status_of(rows, "G-VERIFY") == "PASS"


def test_gverify_fails_when_out_of_frame():
    """scope.in_frame:false = 'cerceve disinda' → uretilmemeli, yayinlanmamali."""
    rows = run_gate(vm.gate_verify, _mod(_VERIF_OK.replace("in_frame: true", "in_frame: false")))
    assert status_of(rows, "G-VERIFY") == "FAIL"


def test_gverify_fails_on_claim_without_grounding():
    """Asil koruma: dayanaksiz iddia gecemez."""
    body = _VERIF_OK.replace(
        'grounding: { document_id: 197, page: 115 }, verdict: "supported"',
        'verdict: "supported"')
    rows = run_gate(vm.gate_verify, _mod(body))
    assert status_of(rows, "G-VERIFY") == "FAIL"


def test_gverify_fails_on_empty_claims():
    body = _VERIF_OK.replace(
        '''claims: [
      { claim: "Hucre zari secici gecirgendir",
        grounding: { document_id: 197, page: 115 }, verdict: "supported" }
    ]''', 'claims: []')
    rows = run_gate(vm.gate_verify, _mod(body))
    assert status_of(rows, "G-VERIFY") == "FAIL"


def test_gverify_warns_on_ungrounded_general_knowledge():
    body = _VERIF_OK.replace('verdict: "supported"', 'verdict: "general_knowledge"')
    rows = run_gate(vm.gate_verify, _mod(body))
    assert status_of(rows, "G-VERIFY") == "FAIL"   # tek iddia → %100 çoğunluk


def test_gverify_fails_when_frame_source_has_no_document():
    body = _VERIF_OK.replace('frame_source: { kind: "textbook", document_id: 197, pages: "112-120" }',
                             'frame_source: { kind: "textbook" }')
    rows = run_gate(vm.gate_verify, _mod(body))
    assert status_of(rows, "G-VERIFY") == "FAIL"


# ── G-VERIFY · supported_by_source (v3.6.0) — ders kitabı OLMAYAN sınıflar ──────
# TYMM kademeli yürürlük: 3,4,7,8,11,12'de ders kitabı henüz yayınlanmadı; çerçeve
# zorunlu PROGRAM'dır (kazanım çerçevesi 12 sınıfın tamamında var). Bu sınıflarda
# programın kapsamadığı olgu, alternatif kaynaktan (egitim-kaynak: PhET/Vikipedi)
# dayanaklanır → dördüncü verdict `supported_by_source`.
# Kararlar: (Q1) kanıtlı sayılır (general_knowledge cezası YOK) ama grounding'i kaynak
# künyesi + `license` taşımalı (izlenebilirlik); görünür atıf kapıyla dayatılmaz.
# (Q2) meşruiyet YALNIZ program-çerçeveli modülde; ders-kitabı çerçevesinde
# supported_by_source → azınlık WARN / çoğunluk FAIL (omurga `supported` olmalı).

_VERIF_PROGRAM = '''
  meta: { sourceCitation: "MEB Biyoloji 11 öğretim programı + PhET Fotosentez" },
  mode: "CURRICULUM",
  curriculum: { outcomes: [{ code: "BIY.11.1.3", text: "...", mappedTo: ["s1"] }] },
  verification: {
    frame_source: { kind: "program", document_id: 47, pages: "228-232" },
    scope: { in_frame: true, excluded: [] },
    claims: [
      { claim: "Fotosentez isik enerjisini kimyasal baga cevirir",
        grounding: { source: "PhET Fotosentez", url: "https://phet.colorado.edu/x", license: "CC BY-NC 4.0", quote_allowed: true },
        verdict: "supported_by_source" }
    ]
  },
'''


def test_gverify_passes_supported_by_source_under_program_frame():
    """Kitapsiz sinif: program cercevesi + kunye/lisansli supported_by_source → PASS."""
    rows = run_gate(vm.gate_verify, _mod(_VERIF_PROGRAM))
    assert status_of(rows, "G-VERIFY") == "PASS"


def test_gverify_source_not_penalized_as_general_knowledge():
    """supported_by_source general_knowledge sayilmaz — tek-kaynak program modulu FAIL degil."""
    rows = run_gate(vm.gate_verify, _mod(_VERIF_PROGRAM))
    assert status_of(rows, "G-VERIFY") != "FAIL"


def test_gverify_fails_supported_by_source_without_license():
    """Kanitli olmali: grounding `license` tasimayan supported_by_source izlenebilir degil → FAIL."""
    body = _VERIF_PROGRAM.replace(', license: "CC BY-NC 4.0"', '')
    rows = run_gate(vm.gate_verify, _mod(body))
    assert status_of(rows, "G-VERIFY") == "FAIL"


def test_gverify_fails_supported_by_source_majority_under_textbook_frame():
    """Ders kitabi olan sinifta olgusal omurga cogunlukla supported_by_source olamaz → FAIL."""
    body = _VERIF_PROGRAM.replace('kind: "program"', 'kind: "textbook"')
    rows = run_gate(vm.gate_verify, _mod(body))
    assert status_of(rows, "G-VERIFY") == "FAIL"


def test_gverify_warns_supported_by_source_minority_under_textbook_frame():
    """Ders kitabi cercevesinde azinlik supported_by_source → WARN (bloklamaz, isaretler)."""
    body = '''
  meta: { sourceCitation: "MEB Fen Bilimleri 5, s. 115 + PhET" },
  mode: "CURRICULUM",
  curriculum: { outcomes: [{ code: "FB.5.3.1.1", text: "...", mappedTo: ["s1"] }] },
  verification: {
    frame_source: { kind: "textbook", document_id: 197, pages: "112-120" },
    scope: { in_frame: true, excluded: [] },
    claims: [
      { claim: "iddia bir", grounding: { document_id: 197, page: 115 }, verdict: "supported" },
      { claim: "iddia iki", grounding: { document_id: 197, page: 116 }, verdict: "supported" },
      { claim: "ek ornek", grounding: { source: "PhET", url: "https://phet.colorado.edu/y", license: "CC BY-NC 4.0" }, verdict: "supported_by_source" }
    ]
  },
'''
    rows = run_gate(vm.gate_verify, _mod(body))
    assert status_of(rows, "G-VERIFY") == "WARN"


# ---------------------------------------------------------------------------
# G-EXAM (v3.7.0) — sınav sorusu asistanı (EXAM modu) yapısal denetimi
# Fixture dosyası YOK: G-EXAM yalnız MODULE_DATA metnini okur, render edilmiş
# HTML işareti aramaz — satır içi string yeterli (bkz. plan "Dosya Yapısı").
# ---------------------------------------------------------------------------

EXAM_OK = '''<html lang="tr"><body><script>
const MODULE_DATA = {
  meta: { mode: "EXAM", title: "Kesir Problemi", sourceCitation: "MEB Matematik 6" },
  exam: {
    stem: "3/4 kg elma 24 TL ise 2/3 kg elma kac TL'dir?",
    options: ["12 TL", "14 TL", "16 TL", "18 TL"],
    source: "ogrenci fotografi - okul yazilisi",
    integrity: "sound",
    integrityNote: "",
    transcriptionCheck: "tc1",
    distractorAnalysis: "d1",
    chain: [
      { concept: "birim fiyat", outcomeCode: "MAT.6.1.4.1", mappedTo: ["t1"] },
      { concept: "kesirle bolme", outcomeCode: "MAT.6.1.4.2", mappedTo: ["w1"] }
    ]
  },
  segments: [
    { type: "teach", id: "s1", title: "Soruyu okuyalim" },
    { type: "selfExplain", id: "tc1", prompt: "Bir yeri farkliysa yaz." },
    { type: "teach", id: "t1", title: "Birim fiyat" },
    { type: "worked", id: "w1", title: "Cozum",
      steps: [ { text: "24 : 3/4 = 32" }, { text: "32 x 2/3 = ?", answer: ["21,33"] } ],
      fadeFrom: 1 },
    { type: "mcq", id: "d1",
      questions: [ { stem: "B sikki neden cazip ama yanlis?", correctIndex: 1 } ] }
  ]
};
</script></body></html>'''


def test_gexam_skips_when_not_exam_module():
    rows = run_gate(vm.gate_exam, "<html><body><p>merhaba</p></body></html>")
    assert status_of(rows, "G-EXAM") == "PASS"
    msg = next(m for g, s, m in rows if g == "G-EXAM")
    assert "uygulanmaz" in msg


def test_gexam_fail_when_mode_exam_without_block():
    html = '<html><body><script>const MODULE_DATA = { meta: { mode: "EXAM" } };</script></body></html>'
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "FAIL"


def test_gexam_pass_on_wellformed():
    rows = run_gate(vm.gate_exam, EXAM_OK)
    assert status_of(rows, "G-EXAM") == "PASS"


def test_gexam_fail_on_empty_stem():
    html = EXAM_OK.replace(
        'stem: "3/4 kg elma 24 TL ise 2/3 kg elma kac TL\'dir?"', 'stem: ""')
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "FAIL"
    assert "exam.stem" in next(m for g, s, m in rows if g == "G-EXAM")


def test_gexam_fail_when_worked_reveals_full_answer():
    # fadeFrom 1 -> 2: iki adimin ikisi de gorunur, ogrenciye bos birakilan adim yok
    html = EXAM_OK.replace("fadeFrom: 1", "fadeFrom: 2")
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "FAIL"
    assert "fadeFrom" in next(m for g, s, m in rows if g == "G-EXAM")


def test_gexam_fail_on_missing_transcription_check():
    html = EXAM_OK.replace('transcriptionCheck: "tc1",', "")
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "FAIL"
    assert "transcriptionCheck" in next(m for g, s, m in rows if g == "G-EXAM")


def test_gexam_fail_on_dangling_transcription_check_id():
    html = EXAM_OK.replace('transcriptionCheck: "tc1"', 'transcriptionCheck: "yok99"')
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "FAIL"


def test_gexam_fail_on_dangling_chain_mapped_id():
    html = EXAM_OK.replace('mappedTo: ["w1"]', 'mappedTo: ["olmayan-segment"]')
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "FAIL"
    assert "olmayan-segment" in next(m for g, s, m in rows if g == "G-EXAM")


def test_gexam_fail_on_empty_chain():
    html = EXAM_OK.replace('chain: [', 'chain: [] , unusedChain: [')
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "FAIL"
    assert "chain" in next(m for g, s, m in rows if g == "G-EXAM")


def test_gexam_fail_on_invalid_integrity_value():
    html = EXAM_OK.replace('integrity: "sound"', 'integrity: "belki"')
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "FAIL"


def test_gexam_fail_on_flawed_without_note():
    html = EXAM_OK.replace('integrity: "sound"', 'integrity: "flawed"')
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "FAIL"
    assert "integrityNote" in next(m for g, s, m in rows if g == "G-EXAM")


def test_gexam_pass_on_flawed_with_note():
    html = (EXAM_OK
            .replace('integrity: "sound"', 'integrity: "flawed"')
            .replace('integrityNote: ""',
                     'integrityNote: "B ve C siklarinin ikisi de dogru; tek cevap yok."'))
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "PASS"


def test_gexam_warn_on_missing_source():
    html = EXAM_OK.replace('source: "ogrenci fotografi - okul yazilisi",', "")
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "WARN"


def test_gexam_warn_on_options_without_distractor_analysis():
    html = EXAM_OK.replace('distractorAnalysis: "d1",', "")
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "WARN"
    assert "distractorAnalysis" in next(m for g, s, m in rows if g == "G-EXAM")


def test_ginteract_ignores_exam_stem():
    # exam.stem bir QUIZ sorusu DEGILDIR - sinav sorusunun metnidir ve cevap
    # anahtari tasimaz (o worked.answer + celdirici mcq'sunde yasar).
    # EXAM_OK'da 2 "stem:" var (exam.stem + mcq) ama 1 correctIndex; exam blogu
    # sayimdan cikarilmazsa G-INTERACT sahte bir "cevapsiz soru" FAIL'i uretir.
    rows = run_gate(vm.gate_interact, EXAM_OK)
    assert status_of(rows, "G-INTERACT") == "PASS"


# ---------------------------------------------------------------------------
# G-EXAM (v3.10.0) — çoklu soru: topics[] + exams[]
# ---------------------------------------------------------------------------

EXAM_MULTI = '''<html lang="tr"><body><script>
const MODULE_DATA = {
  meta: { mode: "EXAM", title: "Kesir ve oran", sourceCitation: "MEB Matematik 6" },
  topics: [
    { id: "t-kesir", title: "Kesirle carpma",
      chain: [
        { concept: "birim fiyat", outcomeCode: "MAT.6.1.4.1", mappedTo: ["t-kesir-1"] }
      ] },
    { id: "t-oran", title: "Oran",
      chain: [
        { concept: "oran", outcomeCode: "MAT.6.1.5.1", mappedTo: ["t-oran-1"] }
      ] }
  ],
  exams: [
    { id: "q1", topicId: "t-kesir",
      stem: "3/4 kg elma 24 TL ise 2/3 kg kac TL?",
      options: ["12 TL", "16 TL", "18 TL"],
      source: "ogrenci fotografi",
      integrity: "sound",
      transcriptionCheck: "tc-q1",
      distractorAnalysis: "d-q1",
      workedId: "w-q1" },
    { id: "q2", topicId: "t-kesir",
      stem: "1/2 kg armut 10 TL ise 3/4 kg kac TL?",
      options: ["12 TL", "15 TL", "20 TL"],
      source: "ogrenci fotografi",
      integrity: "sound",
      transcriptionCheck: "tc-q2",
      distractorAnalysis: "d-q2",
      workedId: "w-q2" },
    { id: "q3", topicId: "t-oran",
      stem: "12 kiside 3 kirmizi top varsa 20 kiside kac kirmizi top?",
      source: "ogrenci fotografi",
      integrity: "sound",
      transcriptionCheck: "tc-q3",
      workedId: "w-q3" }
  ],
  segments: [
    { type: "teach", id: "t-kesir-1", title: "Birim fiyat" },
    { type: "selfExplain", id: "tc-q1", prompt: "Boyle okudum." },
    { type: "worked", id: "w-q1", title: "Cozum 1",
      steps: [ { text: "24 : 3/4 = 32" }, { text: "32 x 2/3 = ?", answer: ["21,33"] } ],
      fadeFrom: 1 },
    { type: "mcq", id: "d-q1",
      questions: [ { stem: "B sikki neden cazip ama yanlis?", correctIndex: 1 } ] },
    { type: "selfExplain", id: "tc-q2", prompt: "Boyle okudum." },
    { type: "worked", id: "w-q2", title: "Cozum 2",
      steps: [ { text: "10 : 1/2 = 20" }, { text: "20 x 3/4 = ?", answer: ["15"] } ],
      fadeFrom: 1 },
    { type: "mcq", id: "d-q2",
      questions: [ { stem: "A sikki neden yanlis?", correctIndex: 0 } ] },
    { type: "teach", id: "t-oran-1", title: "Oran" },
    { type: "selfExplain", id: "tc-q3", prompt: "Boyle okudum." },
    { type: "worked", id: "w-q3", title: "Cozum 3",
      steps: [ { text: "3/12 = 1/4" }, { text: "20 x 1/4 = ?", answer: ["5"] } ],
      fadeFrom: 1 }
  ]
};
</script></body></html>'''


def test_gexam_pass_on_multi_topics_exams():
    rows = run_gate(vm.gate_exam, EXAM_MULTI)
    assert status_of(rows, "G-EXAM") == "PASS"


def test_gexam_fail_when_one_worked_id_lacks_fade():
    # q1 ve q3 fadeFrom tasir; yalniz q2'nin worked'i tam acik. Eski kural
    # (modülde HERHANGI bir worked yeter) bunu PASS verirdi — cokluda yasak.
    html = EXAM_MULTI.replace(
        '{ type: "worked", id: "w-q2", title: "Cozum 2",\n'
        '      steps: [ { text: "10 : 1/2 = 20" }, { text: "20 x 3/4 = ?", answer: ["15"] } ],\n'
        '      fadeFrom: 1 }',
        '{ type: "worked", id: "w-q2", title: "Cozum 2",\n'
        '      steps: [ { text: "10 : 1/2 = 20" }, { text: "20 x 3/4 = ?", answer: ["15"] } ],\n'
        '      fadeFrom: 2 }',
    )
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "FAIL"
    msg = next(m for g, s, m in rows if g == "G-EXAM")
    assert "q2" in msg
    assert "fadeFrom" in msg


def test_gexam_fail_on_broken_topic_id():
    html = EXAM_MULTI.replace('topicId: "t-oran"', 'topicId: "t-yok"')
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "FAIL"
    msg = next(m for g, s, m in rows if g == "G-EXAM")
    assert "t-yok" in msg


def _five_exams_html():
    items = []
    segs = ['{ type: "teach", id: "t-k", title: "Konu" }']
    for i in range(1, 6):
        qid = f"q{i}"
        items.append(
            f'{{ id: "{qid}", topicId: "t-k",'
            f' stem: "Soru {qid} metni.",'
            f' source: "ogrenci fotografi",'
            f' integrity: "sound",'
            f' transcriptionCheck: "tc-{qid}",'
            f' workedId: "w-{qid}" }}'
        )
        segs.append(f'{{ type: "selfExplain", id: "tc-{qid}", prompt: "okudum" }}')
        segs.append(
            f'{{ type: "worked", id: "w-{qid}", title: "Cozum {qid}",'
            f' steps: [ {{ text: "a" }}, {{ text: "b", answer: ["1"] }} ],'
            f' fadeFrom: 1 }}'
        )
    return f'''<html lang="tr"><body><script>
const MODULE_DATA = {{
  meta: {{ mode: "EXAM", title: "Bes soru" }},
  topics: [ {{ id: "t-k", title: "Konu",
    chain: [ {{ concept: "temel", mappedTo: ["t-k"] }} ] }} ],
  exams: [ {", ".join(items)} ],
  segments: [ {", ".join(segs)} ]
}};
</script></body></html>'''


def test_gexam_warn_when_more_than_four_exams():
    rows = run_gate(vm.gate_exam, _five_exams_html())
    assert status_of(rows, "G-EXAM") == "WARN"
    msg = next(m for g, s, m in rows if g == "G-EXAM")
    assert "> 4" in msg


def test_gexam_empty_exams_array_falls_back_to_legacy():
    html = EXAM_OK.replace(
        "const MODULE_DATA = {",
        "const MODULE_DATA = {\n  exams: [],",
    )
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "PASS"


def test_gexam_fail_when_mode_exam_empty_exams_and_no_exam_block():
    html = '''<html><body><script>
const MODULE_DATA = { meta: { mode: "EXAM" }, exams: [] };
</script></body></html>'''
    rows = run_gate(vm.gate_exam, html)
    assert status_of(rows, "G-EXAM") == "FAIL"


def test_ginteract_ignores_exams_stems():
    # EXAM_MULTI: 3 exams[].stem + 2 mcq stem; 2 correctIndex.
    # exams[] cikarilmazsa G-INTERACT sahte "cevapsiz soru" FAIL uretir.
    rows = run_gate(vm.gate_interact, EXAM_MULTI)
    assert status_of(rows, "G-INTERACT") == "PASS"


# ---------------------------------------------------------------------------
# G-VOICE (v3.8.0) — öğrenci yüzeyinde kaynak-meta atıf yok; nihai dil
# ---------------------------------------------------------------------------

def test_gvoice_fails_on_kitabin_tanimi():
    html = _mod('segments: [{ type: "teach", id: "t1", body: ["<p>Kitabın tanımı: hücre canlının en küçük birimidir.</p>"] }]')
    rows = run_gate(vm.gate_voice, html)
    assert status_of(rows, "G-VOICE") == "FAIL"
    assert "kitab" in next(m for g, s, m in rows if g == "G-VOICE").casefold()


def test_gvoice_fails_on_kitaptaki_yaziyi_hatirla():
    html = _mod('segments: [{ type: "mcq", id: "q1", questions: [{ stem: "Kitaptaki yazıyı hatırla: mitokondri ne işe yarar?", correctIndex: 0 }] }]')
    rows = run_gate(vm.gate_voice, html)
    assert status_of(rows, "G-VOICE") == "FAIL"


def test_gvoice_fails_on_ders_kitabinda():
    html = _mod('segments: [{ type: "teach", id: "t1", explanation: "Ders kitabında anlatıldığı gibi fotosentez ışık ister." }]')
    rows = run_gate(vm.gate_voice, html)
    assert status_of(rows, "G-VOICE") == "FAIL"


def test_gvoice_ignores_source_citation_backstage():
    """meta.sourceCitation yazar katmanıdır — 'ders kitabı' orada meşru, öğrenci görmez."""
    html = _mod('meta: { sourceCitation: "MEB Fen 5 ders kitabı, s. 112 / FB.5.3.1.1" }, segments: [{ type: "teach", id: "t1", body: ["<p>Hücre, canlının en küçük yapı birimidir.</p>"] }]')
    rows = run_gate(vm.gate_voice, html)
    assert status_of(rows, "G-VOICE") == "PASS"


def test_gvoice_ignores_verification_backstage():
    html = _mod('''
      verification: {
        frame_source: { kind: "textbook", document_id: 197, pages: "112-120" },
        claims: [{ claim: "x", grounding: { document_id: 197, page: 115 }, verdict: "supported" }]
      },
      segments: [{ type: "teach", id: "t1", body: ["<p>Hücre, canlının en küçük yapı birimidir.</p>"] }]
    ''')
    rows = run_gate(vm.gate_voice, html)
    assert status_of(rows, "G-VOICE") == "PASS"


def test_gvoice_allows_literary_kitap():
    """Türkçe dersinde edebi eser olarak 'kitap' meşrudur; 'kitabın tanımı' değil."""
    html = _mod(
        'segments: [{ type: "teach", id: "t1", '
        'body: ["<p>Bu kitabın yazarı Yaşar Kemaldir. Romanın konusu Toroslardır.</p>"] }]'
    )
    rows = run_gate(vm.gate_voice, html)
    assert status_of(rows, "G-VOICE") == "PASS"


def test_gvoice_allows_retrieval_without_textbook():
    """'Hatırla' tek başına (geri getirme) meşru; yasak olan kitaba bağlanan hatırlatmadır."""
    html = _mod('segments: [{ type: "hook", id: "h1", question: "Enerji santralini hatırla: hangisi?" }]')
    rows = run_gate(vm.gate_voice, html)
    assert status_of(rows, "G-VOICE") == "PASS"


def test_gvoice_passes_minimal_fixture():
    rows = run_gate(vm.gate_voice, open("tests/fixtures/minimal_pass.html").read())
    assert status_of(rows, "G-VOICE") == "PASS"


def test_gvoice_allows_phet_attribution():
    html = _mod('segments: [{ type: "teach", id: "t1", body: ["<p>Simülasyon: PhET Fotosentez (CC BY-NC 4.0, Colorado Üniversitesi).</p>"] }]')
    rows = run_gate(vm.gate_voice, html)
    assert status_of(rows, "G-VOICE") == "PASS"


# ---------------------------------------------------------------------------
# G-SELFCONTAINED — yalnız inline/data runtime kaynakları
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "html",
    [
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans">',
        '<style>@import "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans";</style>',
        '<style>@font-face{src:url("https://fonts.gstatic.com/plex.woff2") format("woff2")}</style>',
        '<img src="https://example.org/diagram.png" alt="">',
        '<img src="data:image/png;base64,AA==" srcset="https://example.org/diagram@2x.png 2x" alt="">',
        '<script src="https://example.org/app.js"></script>',
        '<img src="//cdn.example.org/diagram.png" alt="">',
        '<img src="./assets/diagram.png" alt="">',
        '<svg><image href="https://example.org/diagram.svg"></image></svg>',
        '<object data="/assets/activity.svg"></object>',
        '<input type="image" src="icons/submit.png" alt="Gönder">',
    ],
)
def test_gselfcontained_rejects_runtime_dependencies(html):
    rows = run_gate(vm.gate_selfcontained, html)
    assert status_of(rows, "G-SELFCONTAINED") == "FAIL"


@pytest.mark.parametrize(
    "html",
    [
        '<iframe src="https://example.org/embed"></iframe>',
        '<iframe srcdoc="<p>inline ama desteklenmeyen alt belge</p>"></iframe>',
        '<link rel="preload" as="image" imagesrcset="https://example.org/a.png 1x">',
        '<form action="https://example.org/submit"></form>',
        '<button form="f" formaction="/submit">Gönder</button>',
        '<base href="https://example.org/assets/">',
        '<meta http-equiv="refresh" content="0; url=https://example.org/next">',
        '<html manifest="/offline.appcache"></html>',
        '<body background="images/paper.png"></body>',
        '<a href="#ok" ping="https://example.org/audit">Git</a>',
    ],
)
def test_gselfcontained_rejects_expanded_html_dependency_matrix(html):
    rows = run_gate(vm.gate_selfcontained, html)
    assert status_of(rows, "G-SELFCONTAINED") == "FAIL"


@pytest.mark.parametrize(
    "attr",
    [
        'fill="url(https://example.org/fill.svg#paint)"',
        'stroke="url(//example.org/stroke.svg#paint)"',
        'filter="url(./filters.svg#blur)"',
        'clip-path="url(/clips.svg#clip)"',
        'mask="url(https://example.org/masks.svg#m)"',
        'marker-start="url(https://example.org/markers.svg#start)"',
        'marker-mid="url(https://example.org/markers.svg#mid)"',
        'marker-end="url(https://example.org/markers.svg#end)"',
    ],
)
def test_gselfcontained_rejects_external_svg_paint_server_urls(attr):
    rows = run_gate(vm.gate_selfcontained, f"<svg><path {attr}/></svg>")
    assert status_of(rows, "G-SELFCONTAINED") == "FAIL"


def test_gselfcontained_allows_internal_svg_paint_server_fragments():
    html = """
    <svg>
      <defs>
        <linearGradient id="paint"><stop offset="0"/></linearGradient>
        <filter id="blur"><feGaussianBlur stdDeviation="1"/></filter>
      </defs>
      <path fill="url(#paint)" filter="url(#blur)" marker-end="url(#arrow)"/>
    </svg>
    """
    rows = run_gate(vm.gate_selfcontained, html)
    assert status_of(rows, "G-SELFCONTAINED") == "PASS"


@pytest.mark.parametrize(
    "html",
    [
        '<style>.hero{background-image:image-set("https://example.org/a.png" 1x)}</style>',
        '<style>.hero{background-image:-webkit-image-set("./a.png" 1x)}</style>',
        '<div style="background-image:image-set(\'//example.org/a.png\' 1x)"></div>',
    ],
)
def test_gselfcontained_rejects_css_image_set_dependencies(html):
    rows = run_gate(vm.gate_selfcontained, html)
    assert status_of(rows, "G-SELFCONTAINED") == "FAIL"


@pytest.mark.parametrize(
    "script",
    [
        'fetch("https://example.org/data.json")',
        'const xhr = new XMLHttpRequest(); xhr.open("GET", "/data.json")',
        'new WebSocket("wss://example.org/socket")',
        'new EventSource("/events")',
        'navigator.sendBeacon("/audit", "done")',
        'new Worker("./worker.js")',
        'new SharedWorker("./shared-worker.js")',
        'import("./lesson.js")',
        'const img = document.createElement("img"); img.src = "/image.png"',
        'node.href = "https://example.org/theme.css"',
        'node.setAttribute("src", "./runtime.js")',
        'node.setAttribute("href", "//example.org/runtime.css")',
        'node.setAttribute("aria-label", fetch("/runtime.json"))',
        'const message = `${fetch("/runtime.json")}`',
        'globalThis["fetch"]("/runtime.json")',
        'fetch?.("/runtime.json")',
    ],
)
def test_gselfcontained_rejects_inline_js_runtime_loaders(script):
    rows = run_gate(vm.gate_selfcontained, f"<script>{script};</script>")
    assert status_of(rows, "G-SELFCONTAINED") == "FAIL"


@pytest.mark.parametrize(
    "module_code",
    [
        'import "./lesson.js";',
        'import lesson from "https://example.org/lesson.js";',
        'import { lesson as current } from "./lesson.js";',
        'import "lesson-package";',
        'export { lesson } from "./lesson.js";',
        'export * from "lesson-package";',
        'export * as lesson from "//example.org/lesson.js";',
    ],
)
def test_gselfcontained_rejects_static_esm_dependencies(module_code):
    rows = run_gate(vm.gate_selfcontained, f'<script type="module">{module_code}</script>')
    assert status_of(rows, "G-SELFCONTAINED") == "FAIL"


def test_gselfcontained_rejects_event_handler_runtime_loader():
    rows = run_gate(
        vm.gate_selfcontained,
        '<button onclick="fetch(\'/answer.json\')">Yanıt</button>',
    )
    assert status_of(rows, "G-SELFCONTAINED") == "FAIL"


def test_gselfcontained_allows_data_font_and_image():
    html = """
    <style>
      @font-face {
        font-family: "Inline Plex";
        src: url(data:font/woff2;base64,d09GMgABAAAA) format("woff2");
      }
    </style>
    <img src="data:image/svg+xml;base64,PHN2Zy8+" alt="Gömülü şekil">
    """
    rows = run_gate(vm.gate_selfcontained, html)
    assert status_of(rows, "G-SELFCONTAINED") == "PASS"


def test_gselfcontained_allows_external_navigation_and_non_resource_links():
    html = """
    <a href="https://example.org/reference">Kaynak sayfası</a>
    <a href="mailto:teacher@example.org">E-posta</a>
    <a href="tel:+901234567890">Telefon</a>
    <a href="#ozet">Özete git</a>
    """
    rows = run_gate(vm.gate_selfcontained, html)
    assert status_of(rows, "G-SELFCONTAINED") == "PASS"


def test_gselfcontained_ignores_comments_and_prose_examples():
    html = """
    <!-- Örnek, gerçek kaynak değil: <img src="https://example.org/comment.png"> -->
    <style>/* url("https://example.org/comment.woff2") yalnız açıklama */</style>
    <p>Dokümantasyonda src="images/example.png" yazımı anlatılıyor.</p>
    """
    rows = run_gate(vm.gate_selfcontained, html)
    assert status_of(rows, "G-SELFCONTAINED") == "PASS"


def test_gselfcontained_ignores_javascript_comments_and_string_prose():
    html = """
    <script>
      // fetch("https://example.org/not-a-call")
      // import "./not-a-module.js"; export * from "./not-a-reexport.js";
      /* new Worker("./not-a-worker.js"); node.src = "/not-an-assignment"; */
      const prose = "XMLHttpRequest WebSocket EventSource sendBeacon import('./not.js')";
      const example = "node.setAttribute('src', './not-runtime.js')";
      const moduleExample = "import x from './not-a-module.js'; export * from './not.js';";
    </script>
    """
    rows = run_gate(vm.gate_selfcontained, html)
    assert status_of(rows, "G-SELFCONTAINED") == "PASS"


def test_gselfcontained_pass_message_does_not_accept_cdn():
    rows = run_gate(
        vm.gate_selfcontained,
        '<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=" alt="">',
    )
    assert status_of(rows, "G-SELFCONTAINED") == "PASS"
    message = next(message for gate, _, message in rows if gate == "G-SELFCONTAINED")
    assert "cdn" not in message.casefold()


# ---------------------------------------------------------------------------
# G-VERIFY — kaynak künyesi + JS-ish dengeli provenans ayrıştırması
# ---------------------------------------------------------------------------

_ALL_MODES = (
    "MODULE",
    "QUIZ",
    "FLASHCARDS",
    "GAME",
    "EXPLAINER",
    "ASSESSMENT",
    "SERIES",
    "CURRICULUM",
    "EXAM",
)


@pytest.mark.parametrize("mode", _ALL_MODES)
def test_gverify_rejects_missing_source_citation_in_every_mode(mode):
    html = _mod(f'meta: {{ mode: "{mode}" }}, segments: []')
    rows = run_gate(vm.gate_verify, html)
    assert status_of(rows, "G-VERIFY") == "FAIL"
    assert "sourceCitation" in next(message for gate, _, message in rows if gate == "G-VERIFY")


@pytest.mark.parametrize(
    "citation",
    [
        "",
        "   ",
        "ÖRNEK",
        "todo: kaynak",
        "buraya yaz",
        "REPLACE_ME",
        "Placeholder",
        "TBD",
        "unknown",
        "N/A",
        "N-A",
        "örnek kaynak",
        "örnek metin",
        "örnek citation",
    ],
)
def test_gverify_rejects_empty_or_placeholder_source_citation(citation):
    html = _mod(
        f'meta: {{ mode: "MODULE", sourceCitation: "{citation}" }}, segments: []'
    )
    rows = run_gate(vm.gate_verify, html)
    assert status_of(rows, "G-VERIFY") == "FAIL"


@pytest.mark.parametrize("raw", ["false", "null"])
def test_gverify_rejects_nonstring_source_citation(raw):
    html = _mod(f'meta: {{ mode: "MODULE", sourceCitation: {raw} }}, segments: []')
    rows = run_gate(vm.gate_verify, html)
    assert status_of(rows, "G-VERIFY") == "FAIL"


def test_gverify_allows_legitimate_ornek_source_title():
    html = _mod(
        'meta: { mode: "MODULE", sourceCitation: "MEB Örnek Sorular 2025" }, segments: []'
    )
    rows = run_gate(vm.gate_verify, html)
    assert status_of(rows, "G-VERIFY") != "FAIL"


@pytest.mark.parametrize(
    "body",
    [
        'meta: { mode: "MODULE", sourceCitation: `MEB ${edition} Fen 5` }, segments: []',
        _VERIF_OK.replace('pages: "112-120"', 'locator: `Sayfa ${page}`'),
        _VERIF_OK.replace("page: 115", 'locator: `Sayfa ${page}`'),
    ],
)
def test_gverify_rejects_interpolated_template_provenance(body):
    rows = run_gate(vm.gate_verify, _mod(body))
    assert status_of(rows, "G-VERIFY") == "FAIL"


def test_gverify_allows_interpolation_free_backtick_provenance():
    body = _VERIF_OK.replace(
        'sourceCitation: "MEB Fen Bilimleri 5, s. 115"',
        "sourceCitation: `MEB Örnek Sorular 2025, sayfa 115`",
    ).replace('pages: "112-120"', "locator: `Sayfa 112-120`").replace(
        "page: 115", "locator: `Sayfa 115, paragraf 2`"
    )
    rows = run_gate(vm.gate_verify, _mod(body))
    assert status_of(rows, "G-VERIFY") == "PASS"


def test_gverify_fails_on_empty_verification_object():
    html = _mod(
        'meta: { sourceCitation: "MEB Fen Bilimleri 5" }, '
        'mode: "CURRICULUM", curriculum: { outcomes: [] }, verification: {}'
    )
    rows = run_gate(vm.gate_verify, html)
    assert status_of(rows, "G-VERIFY") == "FAIL"


def test_gverify_fails_on_whitespace_claim():
    html = _mod(_VERIF_OK.replace('"Hucre zari secici gecirgendir"', '"   "'))
    rows = run_gate(vm.gate_verify, html)
    assert status_of(rows, "G-VERIFY") == "FAIL"


def test_gverify_fails_on_empty_grounding_object():
    html = _mod(
        _VERIF_OK.replace("grounding: { document_id: 197, page: 115 }", "grounding: {}")
    )
    rows = run_gate(vm.gate_verify, html)
    assert status_of(rows, "G-VERIFY") == "FAIL"


def test_gverify_fails_on_unknown_verdict():
    html = _mod(_VERIF_OK.replace('verdict: "supported"', 'verdict: "looks_right"'))
    rows = run_gate(vm.gate_verify, html)
    assert status_of(rows, "G-VERIFY") == "FAIL"


def test_gverify_fails_on_unknown_frame_source_kind():
    html = _mod(_VERIF_OK.replace('kind: "textbook"', 'kind: "memory"'))
    rows = run_gate(vm.gate_verify, html)
    assert status_of(rows, "G-VERIFY") == "FAIL"


def test_gverify_fails_when_supported_claim_has_no_locator():
    html = _mod(
        _VERIF_OK.replace(
            "grounding: { document_id: 197, page: 115 }",
            "grounding: { document_id: 197 }",
        )
    )
    rows = run_gate(vm.gate_verify, html)
    assert status_of(rows, "G-VERIFY") == "FAIL"


@pytest.mark.parametrize(
    "old,new",
    [
        ("document_id: 197, pages: \"112-120\"", "document_id: false, pages: \"112-120\""),
        ("document_id: 197, pages: \"112-120\"", "document_id: null, pages: \"112-120\""),
        ("document_id: 197, pages: \"112-120\"", "document_id: 197, locator: \"unknown\""),
        ("document_id: 197, page: 115", "document_id: false, page: 115"),
        ("document_id: 197, page: 115", "document_id: 197, page: false"),
        ("document_id: 197, page: 115", "document_id: 197, page: 0"),
        ("document_id: 197, page: 115", "document_id: 197, locator: \"N/A\""),
    ],
)
def test_gverify_rejects_invalid_document_identity_or_locator_types(old, new):
    rows = run_gate(vm.gate_verify, _mod(_VERIF_OK.replace(old, new)))
    assert status_of(rows, "G-VERIFY") == "FAIL"


@pytest.mark.parametrize(
    "old,new",
    [
        ('source: "PhET Fotosentez"', "source: false"),
        ('source: "PhET Fotosentez"', 'source: "unknown"'),
        ('license: "CC BY-NC 4.0"', "license: null"),
        ('license: "CC BY-NC 4.0"', 'license: "TBD"'),
        ('license: "CC BY-NC 4.0"', 'license: "CC BY-NC 4.0", provenance: "unknown"'),
        ('url: "https://phet.colorado.edu/x"', 'locator: "N-A"'),
    ],
)
def test_gverify_rejects_invalid_source_identity_license_or_locator(old, new):
    rows = run_gate(vm.gate_verify, _mod(_VERIF_PROGRAM.replace(old, new)))
    assert status_of(rows, "G-VERIFY") == "FAIL"


def test_gverify_accepts_positive_integer_and_precise_string_provenance():
    body = _VERIF_OK.replace(
        'frame_source: { kind: "textbook", document_id: 197, pages: "112-120" }',
        'frame_source: { kind: "textbook", document_id: "MEB-FEN-5", '
        'locator: "Bölüm 3, sayfa 112-120" }',
    ).replace(
        "grounding: { document_id: 197, page: 115 }",
        'grounding: { document_id: 197, locator: "Sayfa 115, paragraf 2" }',
    )
    rows = run_gate(vm.gate_verify, _mod(body))
    assert status_of(rows, "G-VERIFY") == "PASS"


def test_gverify_accepts_supported_and_reasoned_unverified_claims():
    body = _VERIF_OK.replace(
        """{ claim: "Hucre zari secici gecirgendir",
        grounding: { document_id: 197, page: 115 }, verdict: "supported" }""",
        """{ claim: "Hucre zari secici gecirgendir",
        grounding: { document_id: 197, page: 115 }, verdict: "supported" },
      { claim: "Ek örneğin kaynağı doğrulanamadı",
        grounding: { reason: "İlgili kaynak sayfasına erişilemedi" },
        verdict: "unverified" }""",
    )
    rows = run_gate(vm.gate_verify, _mod(body))
    assert status_of(rows, "G-VERIFY") == "WARN"


def test_gverify_fails_on_placeholder_unverified_reason():
    body = _VERIF_OK.replace(
        """grounding: { document_id: 197, page: 115 }, verdict: "supported" }""",
        """grounding: { reason: "unknown" }, verdict: "unverified" }""",
    )
    rows = run_gate(vm.gate_verify, _mod(body))
    assert status_of(rows, "G-VERIFY") == "FAIL"


def test_gverify_unsupported_verdict_is_fail():
    body = _VERIF_OK.replace(
        """grounding: { document_id: 197, page: 115 }, verdict: "supported" }""",
        """grounding: { reason: "Kaynak iddiayı çürütüyor" }, verdict: "unsupported" }""",
    )
    rows = run_gate(vm.gate_verify, _mod(body))
    assert status_of(rows, "G-VERIFY") == "FAIL"


@pytest.mark.parametrize(
    ("verdict", "expected_status", "expected_exit"),
    [
        ("unsupported", "FAIL", 1),
        ("unverified", "WARN", 0),
    ],
)
def test_gverify_cli_exit_matches_verdict_policy(tmp_path, verdict, expected_status, expected_exit):
    skill_root = Path(__file__).parents[1]
    html = (skill_root / "assets" / "module-template.html").read_text(encoding="utf-8")
    html = html.replace('subject:"Fen Bilimleri", gradeLevel:"5. Sınıf", mode:"MODULE",',
                        'subject:"Fen Bilimleri", gradeLevel:"5. Sınıf", mode:"CURRICULUM",')
    verification = f'''
  curriculum:{{outcomes:[{{code:"FB.5.3.1.1",text:"Hücreyi açıklar",mappedTo:["t1"]}}]}},
  verification:{{
    frame_source:{{kind:"textbook",document_id:197,page:115}},
    scope:{{in_frame:true}},
    claims:[{{claim:"İddia",grounding:{{reason:"Kaynak doğrulaması tamamlanamadı"}},
             verdict:"{verdict}"}}]
  }},
'''
    html = html.replace("  learner:{", verification + "  learner:{", 1)
    module_path = tmp_path / f"{verdict}.html"
    module_path.write_text(html, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_module.py", "--json", str(module_path)],
        cwd=skill_root,
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(result.stdout)
    assert payload["G-VERIFY"]["status"] == expected_status
    assert result.returncode == expected_exit, result.stdout


def test_gverify_balanced_extractor_ignores_strings_and_comments():
    body = _VERIF_OK.replace(
        'claim: "Hucre zari secici gecirgendir",',
        '''claim: "Metindeki } ve claim: sahte metin ayrıştırmayı bozmamalı",
        /* } ], claim: "yorum içi sahte iddia" */''',
    )
    rows = run_gate(vm.gate_verify, _mod(body))
    assert status_of(rows, "G-VERIFY") == "PASS"


# ---------------------------------------------------------------------------
# Runtime hardening — çevrimdışı IBM Plex, depolama, odak ve zamanlayıcılar
# ---------------------------------------------------------------------------

SKILL_ROOT = Path(__file__).parents[1]
TEMPLATE_PATH = SKILL_ROOT / "assets" / "module-template.html"
FONT_MANIFEST_PATH = SKILL_ROOT / "assets" / "fonts-manifest.json"
FONT_LICENSE_PATH = SKILL_ROOT / "assets" / "ibm-plex-OFL.txt"
FONT_HELPER_PATH = SKILL_ROOT / "scripts" / "embed_ibm_plex_fonts.py"


def _template_source():
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def _carbon_shell(font_css):
    return f"""
    <style>
      {font_css}
      :root {{
        --cds-text-primary:#161616; --cds-background:#ffffff;
        --cds-interactive:#0f62fe; --cds-support-success:#24a148;
        --cds-support-error:#da1e28;
        --font-sans:'IBM Plex Sans',sans-serif;
        --font-serif:'IBM Plex Serif',serif;
        --font-mono:'IBM Plex Mono',monospace;
      }}
      body {{ color:var(--cds-text-primary); font-family:var(--font-sans); }}
    </style>
    """


def _dummy_inline_face(family):
    return (
        "@font-face{"
        f"font-family:'{family}';font-style:normal;font-weight:400;"
        'src:url("data:font/woff2;base64,d09GMgABAAAA") format("woff2");'
        "}"
    )


def test_gcarbon_rejects_family_names_without_embedded_font_faces():
    rows = run_gate(vm.gate_carbon, _carbon_shell(""))
    assert status_of(rows, "G-CARBON") == "FAIL"
    assert "@font-face" in next(message for gate, _, message in rows if gate == "G-CARBON")


def test_gcarbon_accepts_inline_registered_plex_families():
    css = "".join(
        _dummy_inline_face(family)
        for family in ("IBM Plex Sans", "IBM Plex Serif", "IBM Plex Mono")
    )
    rows = run_gate(vm.gate_carbon, _carbon_shell(css))
    assert status_of(rows, "G-CARBON") == "PASS"


def test_gcarbon_rejects_remote_only_plex_faces():
    css = "".join(
        "@font-face{"
        f"font-family:'{family}';font-style:normal;font-weight:400;"
        f'src:url("https://fonts.example/{family.replace(" ", "-")}.woff2") format("woff2");'
        "}"
        for family in ("IBM Plex Sans", "IBM Plex Serif", "IBM Plex Mono")
    )
    rows = run_gate(vm.gate_carbon, _carbon_shell(css))
    assert status_of(rows, "G-CARBON") == "FAIL"


def test_template_font_manifest_matches_every_embedded_blob():
    assert FONT_MANIFEST_PATH.exists(), "assets/fonts-manifest.json henüz üretilmedi"
    assert FONT_LICENSE_PATH.exists(), "IBM Plex OFL lisans metni eksik"

    source = _template_source()
    manifest = json.loads(FONT_MANIFEST_PATH.read_text(encoding="utf-8"))
    blocks = re.findall(
        r"/\*\s*font-id:\s*([a-z0-9-]+)\s*\*/\s*@font-face\s*\{(.*?)\}",
        source,
        flags=re.S | re.I,
    )
    assert blocks, "Şablonda kimlikli inline @font-face bloğu yok"

    embedded = {}
    for font_id, body in blocks:
        match = re.search(
            r'url\(["\']data:font/woff2;base64,([A-Za-z0-9+/=]+)["\']\)',
            body,
        )
        assert match, f"{font_id}: data:font/woff2 blobu yok"
        blob = base64.b64decode(match.group(1), validate=True)
        assert blob[:4] == b"wOF2", f"{font_id}: WOFF2 magic geçersiz"
        embedded[font_id] = blob

    entries = manifest["fonts"]
    assert {entry["id"] for entry in entries} == set(embedded)
    assert len(entries) == len(embedded) == 20
    for entry in entries:
        blob = embedded[entry["id"]]
        assert entry["bytes"] == len(blob)
        assert entry["sha256"] == hashlib.sha256(blob).hexdigest()

    expected_faces = {
        ("IBM Plex Sans", "normal", 400),
        ("IBM Plex Sans", "normal", 500),
        ("IBM Plex Sans", "normal", 600),
        ("IBM Plex Sans", "normal", 700),
        ("IBM Plex Serif", "normal", 400),
        ("IBM Plex Serif", "normal", 600),
        ("IBM Plex Serif", "italic", 400),
        ("IBM Plex Mono", "normal", 400),
        ("IBM Plex Mono", "normal", 600),
        ("IBM Plex Mono", "normal", 700),
    }
    assert {
        (entry["family"], entry["style"], entry["weight"]) for entry in entries
    } == expected_faces
    assert {entry["subset"] for entry in entries} == {"Latin1", "Latin2"}
    assert manifest["source"]["package"] == "@ibm/plex"
    assert manifest["source"]["version"] == "6.4.1"
    assert "fonts-manifest.json" in source and "ibm-plex-OFL.txt" in source
    license_text = FONT_LICENSE_PATH.read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE Version 1.1" in license_text
    assert "Reserved Font Name \"Plex\"" in license_text


def test_font_embed_helper_check_mode_is_deterministic():
    assert FONT_HELPER_PATH.exists(), "font gömme yardımcısı henüz yok"
    result = subprocess.run(
        [sys.executable, str(FONT_HELPER_PATH), "--check"],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_runtime_persistence_uses_local_allowlist_and_session_state():
    source = _template_source()
    assert "sessionStorage" in source
    assert "THEME_STORE_KEY" in source
    assert "LEITNER_STORE_KEY" in source
    assert "SESSION_STORE_KEY" in source
    assert "function persistSession(" in source
    assert "ssGet(SESSION_STORE_KEY)" in source
    assert "answers:Array.from(state.awarded)" in source.replace(" ", "")
    assert "lsSet(THEME_STORE_KEY" in source
    assert "lsSet(LEITNER_STORE_KEY" in source
    assert "lsSet(SESSION_STORE_KEY" not in source

    local_calls = re.findall(r"(?<!function )lsSet\(\s*([A-Z_]+)", source)
    assert set(local_calls) == {"THEME_STORE_KEY", "LEITNER_STORE_KEY"}
    local_reads = re.findall(r"(?<!function )lsGet\(\s*([A-Z_]+)", source)
    assert set(local_reads) == {"THEME_STORE_KEY", "LEITNER_STORE_KEY"}
    session_calls = re.findall(r"(?<!function )ssSet\(\s*([A-Z_]+)", source)
    session_reads = re.findall(r"(?<!function )ssGet\(\s*([A-Z_]+)", source)
    assert set(session_calls) == {"SESSION_STORE_KEY"}
    assert set(session_reads) == {"SESSION_STORE_KEY"}
    assert source.count("localStorage.getItem(") == 1
    assert source.count("localStorage.setItem(") == 1
    assert re.search(r"try\s*\{[^{}]*localStorage\.getItem", source)
    assert re.search(r"try\s*\{[^{}]*sessionStorage\.getItem", source)


def test_leitner_storage_key_prefers_explicit_meta_id():
    source = _template_source()
    assert re.search(r"D\.meta\s*&&\s*D\.meta\.id", source)
    assert "MODULE_STORE_ID" in source
    assert re.search(
        r'LEITNER_STORE_KEY\s*=\s*"edupedia:"\s*\+\s*MODULE_STORE_ID\s*\+\s*":leitner"',
        source,
    )


def test_runtime_timers_are_symmetric_and_lifecycle_cleaned():
    source = _template_source()
    assert source.count("setInterval(") == source.count("clearInterval(")
    assert source.count("setTimeout(") == source.count("clearTimeout(")
    assert "function clearSectionTimers(" in source
    assert "function teardownRuntime(" in source
    assert 'addEventListener("pagehide", teardownRuntime' in source
    assert re.search(r"function render\(\)\s*\{\s*clearSectionTimers\(\)", source)
    assert "sectionInterval(" in source


def test_runtime_focus_handoff_and_retry_contract_is_explicit():
    source = _template_source()
    assert 'data-stage-heading="true"' in source
    assert "function focusStageHeading(" in source
    assert re.search(r"\(fn\|\|renderTeach\)\(stage,s\);\s*focusStageHeading\(stage\)", source)
    assert "focusFirstUsableOption(stage)" in source
    assert "focusActionButton(" in source


def test_objectives_have_visible_intro_and_summary_paths():
    source = _template_source()
    assert "function objectivesBlock(" in source
    assert "function mountObjectives(" in source
    assert re.search(r"state\.idx===0[^;]+mountObjectives\(stage\)", source)
    summary_start = source.index("function renderSummary(stage)")
    summary_end = source.index("\n  /* ---- flashcards", summary_start)
    assert "objectivesBlock(" in source[summary_start:summary_end]


def test_template_limits_live_regions_to_essential_feedback():
    source = _template_source()
    assert source.count('aria-live="polite"') <= 10
    stage_tag = re.search(r'<main class="stage"[^>]*>', source).group(0)
    assert "aria-live" not in stage_tag
    assert 'id="wellbeing" role="status" aria-live="polite"' in source
