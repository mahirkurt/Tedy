"""ted-mcp's module engine: the vendored edupedia template plus anchored patches.

The vendored file stays byte-identical to its source (vendor_sync --check, PROVENANCE.json).
Everything ted-mcp adds — the progress bridge (spec §5.5), image/video/audio rendering from the
embedded asset block, and the asset/attribution slots — is inserted at an anchor that must occur
exactly once. A drifted template raises TemplateDriftError instead of silently compiling a
module without its bridge.
"""
from __future__ import annotations

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
  function edupediaAssetFigure(v){
    if(v.kind === "image"){
      const img = edupediaAssetUri(v.asset, "data:image/");
      return img ? `<figure class="viz"><img src="${esc(img)}" alt="${esc(v.alt||"")}" style="max-width:100%;height:auto"></figure>` : "";
    }
    const vid = edupediaAssetUri(v.asset, "data:video/");
    return vid ? `<figure class="viz"><video controls preload="none" src="${esc(vid)}" aria-label="${esc(v.alt||"Video")}" style="max-width:100%"></video></figure>` : "";
  }
  function edupediaAudio(a){
    if(!a) return "";
    const aud = edupediaAssetUri(a.asset, "data:audio/");
    return aud ? `<div class="edupedia-audio"><audio controls preload="none" src="${esc(aud)}" aria-label="${esc(a.label||"Seslendirme")}"></audio></div>` : "";
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
      const xpNode = $("#xpValue"); if(xpNode) xpNode.textContent = state.xp;
      render();
    }
    if(active){
      window.addEventListener("message", function(e){
        if(e.source!==window.parent) return;
        if(e.origin!==EDUPEDIA_PARENT_ORIGIN) return;
        const d = e.data;
        if(!d || d.type !== "edupedia:restore" || d.v !== 1) return;
        applyRestore(d.state);
      });
    }
    return {
      answer: function(segmentId, item, correct, attempts){
        queueMicrotask(function(){ emit("answer", {segmentId:segmentId, item:item, correct:!!correct, attempts:attempts}); });
      },
      segmentComplete: function(segmentId){ emit("segment_complete", {segmentId:segmentId}); },
      moduleComplete: function(){ if(completed) return; completed = true; emit("module_complete", {}); },
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
    ("complete", '    awardByCondition("module-complete"); playSound("reward");\n',
     "    EDUPEDIA_BRIDGE.moduleComplete();\n", "after"),
    ("ready", "\n  init();\n", "  EDUPEDIA_BRIDGE.ready();\n", "after"),
    ("visual", '    if(s.visual && s.visual.kind==="svg") html+=svgFigure(s.visual.ref, s.visual.caption);\n',
     '    if(s.visual && (s.visual.kind==="image"||s.visual.kind==="video")) html+=edupediaAssetFigure(s.visual);\n    else',
     "before"),
    ("audio", "    stage.innerHTML=html;\n    // merak-boşluğu kapanışı", "    html+=edupediaAudio(s.audio);\n", "before"),
    ("slots", "\n<script>\n/* ==========================================================================\n   İÇERİK",
     "\n" + ASSETS_SLOT + "\n" + ATTRIB_SLOT, "before"),
)


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
                          ("ORIGIN_TOKEN", ORIGIN_TOKEN)):
        if text.count(marker) != 1:
            raise TemplateDriftError(f"{label}: occurs {text.count(marker)} times")
    return text


def engine_template(parent_origin: str) -> str:
    """Patched template with the bridge's parent origin baked in as a JSON string literal."""
    if not isinstance(parent_origin, str) or not PARENT_ORIGIN_RE.fullmatch(parent_origin):
        raise ValueError("parent_origin must be an http(s) origin with no path")
    return _patched_with_token().replace(ORIGIN_TOKEN, json.dumps(parent_origin), 1)
