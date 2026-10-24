"""ted-mcp's module engine: the vendored edupedia template plus anchored patches.

The vendored file stays byte-identical to its source (vendor_sync --check, PROVENANCE.json).
Everything ted-mcp adds — the progress bridge (spec §5.5) and its appearance message (the
dashboard's Carbon theme, adopted through the template's adoptHostTheme), image/video/audio rendering from the
embedded asset block, and the asset/attribution slots — is inserted at an anchor that must occur
exactly once. A drifted template raises TemplateDriftError instead of silently compiling a
module without its bridge.
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache

from src.mcp_server.vendor_sync import VENDOR_DIR

TEMPLATE_PATH = VENDOR_DIR / "assets" / "module-template.html"
PARENT_ORIGIN_RE = re.compile(r"^https?://[a-z0-9.-]+(?::[0-9]{1,5})?$")
ORIGIN_TOKEN = "__EDUPEDIA_PARENT_ORIGIN__"
ASSETS_SLOT = "<!--edupedia:varliklar-->"
ATTRIB_SLOT = "<!--edupedia:atif-->"
MODULE_DATA_START = "const MODULE_DATA = {"
ENGINE_MARKER = ("\n/* ==========================================================================\n"
                 "   MOTOR (ENGINE)")
# The bridge's appearance handler calls this template function; a template without it would
# compile a bridge that throws on the dashboard's first message.
HOST_THEME_HOOK = "function adoptHostTheme(theme){"

BRIDGE_JS = r"""  /* ---- edupedia köprüsü ve varlıklar (ted-mcp sablon.py yaması; spec §5.5) ---- */
  const EDUPEDIA_PARENT_ORIGIN = __EDUPEDIA_PARENT_ORIGIN__;
  const EDUPEDIA_ASSETS = (function(){
    try {
      const node = document.getElementById("edupedia-varliklar");
      const parsed = node ? JSON.parse(node.textContent || "{}") : {};
      return (parsed && typeof parsed === "object") ? parsed : {};
    } catch(e){ return {}; }
  })();
  function edupediaAssetUri(id, prefix){
    const rec = Object.prototype.hasOwnProperty.call(EDUPEDIA_ASSETS, id) ? EDUPEDIA_ASSETS[id] : null;
    const uri = rec && typeof rec.uri === "string" ? rec.uri : "";
    return uri.indexOf(prefix) === 0 ? uri : "";
  }
  /* Kanun M3.6, M3.7 (KB-10, KB-11): raster figür figure + görünür figcaption içindedir; alt metin ve
     altyazı yazarındır (meta.assets[i].alt, .baslik). Boyutu şablonun CSS'i verir, satır içi stil yok. */
  function edupediaAssetFigure(v){
    const cap = v.caption ? `<figcaption>${esc(v.caption)}</figcaption>` : "";
    if(v.kind === "image"){
      const img = edupediaAssetUri(v.asset, "data:image/");
      return img ? `<figure class="viz viz--varlik"><img src="${esc(img)}" alt="${esc(v.alt||"")}">${cap}</figure>` : "";
    }
    const vid = edupediaAssetUri(v.asset, "data:video/");
    return vid ? `<figure class="viz viz--varlik"><video controls preload="none" src="${esc(vid)}" aria-label="${esc(v.alt||v.caption||"Video")}"></video>${cap}</figure>` : "";
  }
  /* Kanun M5.14 (KB-11, KB-49): yazarın ses varlığı görünür adlı, Carbon katmanında, şablonun kendi oynatıcısıyla çalar.
     Carbon'da ses oynatıcı yoktur; oynatıcı Carbon bileşenlerinden kurulur (davranış: şablonun sesOynatici'si):
     oynat/duraklat ve sessiz ghost ikon düğmeleri, konum için Slider anatomisi, mono süre, yükleniyor durumu ve
     InlineNotification dilinde hata. <audio> denetimsiz ve görünmezdir; ses yalnız okurun eylemiyle başlar. */
  function edupediaAudio(a){
    if(!a) return "";
    const aud = edupediaAssetUri(a.asset, "data:audio/");
    if(!aud) return "";
    const ad = esc(a.label||"Seslendirme");
    const kim = "ses-" + Math.random().toString(36).slice(2,8);
    return `<div class="edupedia-audio" role="group" aria-labelledby="${kim}" data-ses-durum="hazir">`
      + `<span class="edupedia-audio__ad" id="${kim}">${icon("ic-headphones")}${ad}</span>`
      + `<div class="ses-denetim">`
      + `<button class="ses-dugme ses-oynat" type="button" aria-label="Oynat">${icon("ic-play")}</button>`
      + `<div class="ses-kaydirici" role="slider" tabindex="0" aria-label="Konum" aria-valuemin="0" aria-valuemax="0"`
      + ` aria-valuenow="0" aria-valuetext="0 saniye"><span class="ses-kaydirici__iz"></span>`
      + `<span class="ses-kaydirici__dolgu"></span><span class="ses-kaydirici__tutamac"></span></div>`
      + `<span class="ses-sure" aria-hidden="true"><span class="ses-sure__gecen">0:00</span> / <span class="ses-sure__toplam">0:00</span></span>`
      + `<button class="ses-dugme ses-sessiz" type="button" aria-label="Seslendirmenin sesini kapat">${icon("ic-volume")}</button>`
      + `</div>`
      + `<p class="ses-yukleniyor" role="status" hidden><svg class="ses-donen" viewBox="0 0 16 16" aria-hidden="true" focusable="false">`
      + `<circle cx="8" cy="8" r="6"></circle></svg><span>Yükleniyor</span></p>`
      + `<div class="ses-hata" role="alert" hidden>${icon("ic-error-filled")}<span>Ses dosyası açılamadı</span></div>`
      + `<audio class="edupedia-audio__kaynak" preload="metadata" src="${esc(aud)}"></audio></div>`;
  }
  const EDUPEDIA_BRIDGE = (function(){
    const embedded = window.parent !== window;
    const found = String(location.pathname || "").match(/^\/m\/([a-z0-9]+(?:-[a-z0-9]+)*)\/v([1-9][0-9]{0,3})$/);
    const slug = found ? found[1] : "";
    const version = found ? Number(found[2]) : 0;
    const active = embedded && slug !== "";
    let restored = false, completed = false;
    function emit(event, extra){
      if(!active) return;
      const msg = Object.assign({type:"edupedia:progress", v:1, slug:slug, version:version, event:event, xp:state.xp, ts:Date.now()}, extra || {});
      try { window.parent.postMessage(msg, EDUPEDIA_PARENT_ORIGIN); } catch(e){ /* ebeveyn yoksa sessiz */ }
    }
    function applyRestore(st){
      if(restored || !st || typeof st !== "object") return;
      restored = true;
      const list = x => Array.isArray(x) ? x.filter(y => typeof y === "string" && y.length <= 80).slice(0, 500) : [];
      list(st.answers).forEach(k => state.awarded.add(k));
      list(st.done).forEach(k => state.done.add(k));
      if(Number.isFinite(st.xp) && st.xp > state.xp) state.xp = Math.floor(st.xp);
      const next = segs.findIndex(seg => !state.done.has(seg.id));
      state.idx = next < 0 ? segs.length : next;
      persistSession();
      render();
    }
  /* Panonun kök yazı boyu (spec §10.2). İsteğe bağlıdır: mesaj yoksa modül 16 px'te kalır,
     yani tek başına açılış ve eski pano bugünkü gibi çalışır. Okurun tarayıcı tercihi panonun
     clamp() tabanında (100%) zaten var, hesaplanmış değer onu taşır. Çerçeve opak kökenli
     olduğu için gelen değer yine de doğrulanır: sayı değilse yok sayılır, 12-48 px'e kıstırılır. */
  function adoptHostRootSize(rootPx){
    const n = typeof rootPx === "number" ? rootPx : NaN;
    if(!isFinite(n)) return false;
    const kistirilmis = Math.min(48, Math.max(12, n));
    document.documentElement.style.fontSize = kistirilmis + "px";
    return true;
  }
  /* Panoda akış yerleşimi (layout:"flow", 2026-10-19). Pano çerçeveyi içeriğin boyuna büyütür,
     sayfa tek parça kayar: modül kendi kabuğunu bırakır (şablondaki data-host-layout="flow"
     bloğu) ve gövde yüksekliğini bildirir. Yükseklik yalnız ebeveyne ve sabit origin'e gider;
     alan yoksa (eski pano) ya da tek başına açılışta bu yol hiç kurulmaz. .wrap'in 100vh tabanı
     akışta kalkar — yoksa çerçeve boyu içerik boyunu, içerik boyu çerçeve boyunu büyütürdü. */
  let flowOn = false, lastHeight = 0;
  function postSize(top){
    const h = Math.ceil(document.body.getBoundingClientRect().height);
    if(!top && h === lastHeight) return;
    lastHeight = h;
    const msg = {type:"edupedia:size", v:1, height:h};
    if(top) msg.top = true;
    try { window.parent.postMessage(msg, EDUPEDIA_PARENT_ORIGIN); } catch(e){ /* ebeveyn yoksa sessiz */ }
  }
  function adoptHostLayout(layout){
    if(layout !== "flow" || flowOn) return false;
    flowOn = true;
    document.documentElement.setAttribute("data-host-layout", "flow");
    if(typeof ResizeObserver === "function"){
      new ResizeObserver(function(){ postSize(false); }).observe(document.body);
    }
    postSize(false);
    return true;
  }
    if(embedded){
      window.addEventListener("message", function(e){
        if(e.source!==window.parent) return;
        if(e.origin!==EDUPEDIA_PARENT_ORIGIN) return;
        const d = e.data;
        if(!d || d.v !== 1) return;
        // Görünüm: pano kendi Carbon temasını, kök puntosunu ve yerleşimini bildirir (taslak
        // önizleme dahil); ilerleme yazmaz.
        if(d.type === "edupedia:appearance"){
          adoptHostTheme(d.theme); adoptHostRootSize(d.rootPx); adoptHostLayout(d.layout); return;
        }
        if(!active || d.type !== "edupedia:restore") return;
        applyRestore(d.state);
      });
    }
    return {
      answer: function(segmentId, item, correct, attempts){
        queueMicrotask(function(){ emit("answer", {segmentId:segmentId, item:item, correct:!!correct, attempts:attempts}); });
      },
      segmentComplete: function(segmentId){ emit("segment_complete", {segmentId:segmentId}); },
      moduleComplete: function(){ if(completed) return; completed = true; emit("module_complete", {}); },
      // Bölüm değişti: çerçevenin içi zaten başta; akışta sayfayı kaydıran panodur.
      toTop: function(){ if(flowOn) postSize(true); },
      ready: function(){ emit("ready", {}); }
    };
  })();

"""

PATCHES: tuple[tuple[str, str, str, str], ...] = (
    ("bridge", "  /* ---- başlat ---- */\n  function init(){\n", BRIDGE_JS, "before"),
    ("answer", "          const correct = i===q.correctIndex;\n",
     "          tried.n=(tried.n||0)+1; EDUPEDIA_BRIDGE.answer(s.id, oi, correct, tried.n);\n", "after"),
    ("segment", "    if(state.idx<segs.length){ state.done.add(segs[state.idx].id); }\n",
     "    if(state.idx<segs.length){ EDUPEDIA_BRIDGE.segmentComplete(segs[state.idx].id); }\n", "after"),
    # The summary segment is where a module completes (it no longer awards a badge or plays a
    # reward sound — talimatname S43, B73 — so the anchor is the segment marker itself).
    ("complete", '    stage.setAttribute("data-seg","summary");\n',
     "    EDUPEDIA_BRIDGE.moduleComplete();\n", "after"),
    ("ready", "\n  init();\n", "  EDUPEDIA_BRIDGE.ready();\n", "after"),
    # A segment change scrolls the module's own window to the top; in the dashboard's flow
    # layout the frame has no scroll of its own, so the bridge asks the host to do it.
    ("top", '    window.scrollTo({top:0,behavior:"instant"});\n', "    EDUPEDIA_BRIDGE.toTop();\n", "after"),
    ("visual", '    if(s.visual && s.visual.kind==="svg") html+=svgFigure(s.visual.ref, s.visual.caption);\n',
     '    if(s.visual && (s.visual.kind==="image"||s.visual.kind==="video")) html+=edupediaAssetFigure(s.visual);\n    else',
     "before"),
    ("audio", "    stage.innerHTML=html;\n    // merak-boşluğu kapanışı", "    html+=edupediaAudio(s.audio);\n", "before"),
    ("slots", "\n<script>\n/* ==========================================================================\n   İÇERİK",
     "\n" + ASSETS_SLOT + "\n" + ATTRIB_SLOT, "before"),
)


def sablon_parmak_izi() -> str:
    """Bugünkü motorun parmak izi: derlemenin kullandığı yamalı şablon metninin (`_patched_with_token`) sha256'sı.
    Vendored şablon da `PATCHES`/`BRIDGE_JS` da onu değiştirir; diskteki dosya değil sürecin bellekteki metni
    sayıldığı için `git pull` ile yeniden başlatma arasında derlenen taslak da kendi metninin izini taşır. Taslak kaydı
    bunu taşır; yayın, parmak izi bugünkünden farklı taslağı yeniden derletir (Kanun KB-48)."""
    return hashlib.sha256(_patched_with_token().encode("utf-8")).hexdigest()


class TemplateDriftError(RuntimeError):
    """The vendored template no longer matches the anchors ted-mcp patches."""


@lru_cache(maxsize=1)
def _patched_with_token() -> str:
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    for name, anchor, insertion, position in PATCHES:
        count = text.count(anchor)
        if count != 1:
            raise TemplateDriftError(f"{name}: anchor occurs {count} times")
        replacement = insertion + anchor if position == "before" else anchor + insertion
        text = text.replace(anchor, replacement, 1)
    for label, marker in (("MODULE_DATA_START", MODULE_DATA_START), ("ENGINE_MARKER", ENGINE_MARKER),
                          ("ORIGIN_TOKEN", ORIGIN_TOKEN), ("HOST_THEME_HOOK", HOST_THEME_HOOK)):
        if text.count(marker) != 1:
            raise TemplateDriftError(f"{label}: occurs {text.count(marker)} times")
    return text


def engine_template(parent_origin: str) -> str:
    """Patched template with the bridge's parent origin baked in as a JSON string literal."""
    if not isinstance(parent_origin, str) or not PARENT_ORIGIN_RE.fullmatch(parent_origin):
        raise ValueError("parent_origin must be an http(s) origin with no path")
    return _patched_with_token().replace(ORIGIN_TOKEN, json.dumps(parent_origin), 1)
