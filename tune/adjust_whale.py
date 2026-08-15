#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate the whale color font + client.js from whale-config.json.

Adjust these in whale-config.json:
  scaleX       : visual width of the whale shape. Bigger => wider whale.
  scaleY       : visual height of the whale shape. Bigger => taller whale.
  yOffset      : vertical shift. Bigger => move the whale DOWN (lower on the line).
  advanceWidth : the horizontal slot the whale occupies in the sentence
                 (base 1000 = a normal full-width character). Bigger => more room.
  leftBearing  : empty space BEFORE the whale's head (left side). Bigger => push the
                 whale right, leaving more space on the left.
"""
import json, re, base64, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
SVG = os.path.join(HERE, 'favicon.svg')
OUT_FONT = os.path.join(HERE, 'whale-color.otf')
OUT_CLIENT = os.path.expanduser('~/.dsh/profiles/web/node_modules/dsh-whale-font/lib/client.js')

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.colorLib.builder import buildCOLR, buildCPAL

cfg = json.load(open(os.path.join(HERE, 'whale-config.json'), encoding='utf-8'))
SCALE_X = float(cfg.get('scaleX', 20))
SCALE_Y = float(cfg.get('scaleY', 26))
Y_OFFSET = float(cfg.get('yOffset', 90))
ADVANCE = float(cfg.get('advanceWidth', 1200))
LSB = float(cfg.get('leftBearing', 0))

raw = open(SVG, encoding='utf-8').read()
d = re.search(r'\sd="([^"]+)"', raw).group(1)

tokens = re.findall(r'[MCZ]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?', d)
contours, cur, cmd, args = [], [], None, []
for t in tokens:
    if t in ('M', 'C'):
        cmd, args = t, []
    elif t == 'Z':
        cur.append(('Z', [])); contours.append(cur); cur, cmd, args = [], None, []
    else:
        args.append(float(t))
        if cmd == 'M' and len(args) == 2:
            cur.append(('M', args[:])); cmd, args = None, []
        elif cmd == 'C' and len(args) == 6:
            cur.append(('C', args[:])); cmd, args = None, []
if cur:
    contours.append(cur)

# raw bounding box of the path (in SVG viewBox units, before tx)
_ox0 = _oy0 = float('inf')
_ox1 = _oy1 = float('-inf')
for _c in contours:
    for _s in _c:
        if _s[0] in ('M', 'C'):
            _p = _s[1]
            for _i in range(0, len(_p), 2):
                _ox0 = min(_ox0, _p[_i]); _ox1 = max(_ox1, _p[_i])
                _oy0 = min(_oy0, _p[_i + 1]); _oy1 = max(_oy1, _p[_i + 1])
RAW_W = _ox1 - _ox0
RAW_H = _oy1 - _oy0

# Split subpaths: the largest is the blue BODY (outer outline); everything else is
# the inner detail (belly + eye + mouth) which must be painted solid WHITE so it stays
# white in both light and dark mode instead of being a transparent hole (-> black belly).
def _bbox_area(c):
    _xs, _ys = [], []
    for _s in c:
        if _s[0] in ('M', 'C'):
            _p = _s[1]
            for _i in range(0, len(_p), 2):
                _xs.append(_p[_i]); _ys.append(_p[_i + 1])
    return (max(_xs) - min(_xs)) * (max(_ys) - min(_ys))

_body_idx = max(range(len(contours)), key=lambda i: _bbox_area(contours[i]))
body_contour = contours[_body_idx]
belly_contours = [c for i, c in enumerate(contours) if i != _body_idx]

def contour_to_d(c):
    _out = []
    for _s in c:
        _op = _s[0]
        if _op == 'M':
            _out.append('M%.6g,%.6g' % (_s[1][0], _s[1][1]))
        elif _op == 'C':
            _p = _s[1]
            _out.append('C%.6g,%.6g,%.6g,%.6g,%.6g,%.6g' % (_p[0], _p[1], _p[2], _p[3], _p[4], _p[5]))
        elif _op == 'Z':
            _out.append('Z')
    return ''.join(_out)

body_d = contour_to_d(body_contour)
belly_d = ''.join(contour_to_d(c) for c in belly_contours)

UPEM = 1000
def tx(x, y):
    return ((x - _ox0) * SCALE_X + LSB, (50.0 - y) * SCALE_Y - Y_OFFSET)

# diagnostic: transformed bounding box
_xs, _ys = [], []
for _c in contours:
    for _s in _c:
        if _s[0] in ('M', 'C'):
            _p = _s[1]
            for _i in range(0, len(_p), 2):
                _x, _y = tx(_p[_i], _p[_i+1])
                _xs.append(_x); _ys.append(_y)
print(f"glyph bbox x:[{min(_xs):.0f},{max(_xs):.0f}] y:[{min(_ys):.0f},{max(_ys):.0f}]  (yOffset={Y_OFFSET})")

def draw_contours(pen, clist):
    for contour in clist:
        for seg in contour:
            op = seg[0]
            if op == 'M':
                pen.moveTo(tx(seg[1][0], seg[1][1]))
            elif op == 'C':
                p = seg[1]
                pen.curveTo(tx(p[0], p[1]), tx(p[2], p[3]), tx(p[4], p[5]))
            elif op == 'Z':
                pen.closePath()

body_pen = T2CharStringPen(int(round(ADVANCE)), None)
draw_contours(body_pen, [body_contour])
body_cs = body_pen.getCharString()

belly_pen = T2CharStringPen(int(round(ADVANCE)), None)
draw_contours(belly_pen, belly_contours)
belly_cs = belly_pen.getCharString()

nd = T2CharStringPen(600, None)
nd.moveTo((0, 0)); nd.lineTo((0, 0)); nd.closePath()
notdef_cs = nd.getCharString()

charStrings = {'.notdef': notdef_cs, 'whale': body_cs, 'whale_body': body_cs, 'whale_belly': belly_cs}
fb = FontBuilder(UPEM, isTTF=False)
fb.setupGlyphOrder(['.notdef', 'whale', 'whale_body', 'whale_belly'])
fb.setupCharacterMap({0x6211: 'whale', 0x4F60: 'whale'})
fb.setupCFF('Whale-Regular', {'FullName': 'Whale Regular'}, charStrings, {})
_advance = int(round(ADVANCE))
_lsb = int(round(LSB))
fb.setupHorizontalMetrics({'.notdef': (600, 0), 'whale': (_advance, _lsb), 'whale_body': (_advance, _lsb), 'whale_belly': (_advance, _lsb)})
fb.setupHorizontalHeader(ascent=1200, descent=-100)
fb.setupNameTable({
    'familyName': 'Whale', 'styleName': 'Regular',
    'uniqueFontIdentifier': 'Whale-3.0', 'fullName': 'Whale Regular',
    'psName': 'Whale-Regular', 'version': 'Version 3.0',
})
fb.setupOS2(sTypoAscender=1200, sTypoDescender=-100, usWinAscent=1200, usWinDescent=100)
fb.setupPost()
fb.font['COLR'] = buildCOLR({'whale': [('whale_body', 0), ('whale_belly', 1)]})
fb.font['CPAL'] = buildCPAL([[(77/255, 107/255, 254/255, 1.0), (1.0, 1.0, 1.0, 1.0)]])
fb.save(OUT_FONT)

b64 = base64.b64encode(open(OUT_FONT, 'rb').read()).decode('ascii')
BASE = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif"
# The two @font-face rules live in the JS (so the base64 blob is emitted only once and
# reused for both unicode ranges); only the static container rules are inlined here.
css_static = (".Sxvs8a_root,.Sxvs8a_root *{font-family:'WhaleWo'," + BASE + " !important;}"
              ".Sxvs8a_root code,.Sxvs8a_root pre,.Sxvs8a_root pre *{font-family:var(--ds-font-family-code) !important;}"
              ".gdEzaW_bubble,.gdEzaW_bubble *{font-family:'WhaleNi'," + BASE + " !important;}"
              ".gdEzaW_bubble code,.gdEzaW_bubble pre,.gdEzaW_bubble pre *{font-family:var(--ds-font-family-code) !important;}")

# English I/me inline icon: mirror the FONT whale's exact visual size and vertical
# position. The font glyph occupies (RAW_W*SCALE_X)/1000 em wide, (RAW_H*SCALE_Y)/1000 em
# tall, with its bottom at ((50-RAW_bottom)*SCALE_Y - Y_OFFSET)/1000 em below the baseline.
icon_w = RAW_W * SCALE_X / 1000.0
icon_h = RAW_H * SCALE_Y / 1000.0
icon_va = ((50.0 - _oy1) * SCALE_Y - Y_OFFSET) / 1000.0
icon_advance = ADVANCE / 1000.0
icon_lsb = LSB / 1000.0
icon_viewbox = f"{_ox0:.4f} {_oy0:.4f} {RAW_W:.4f} {RAW_H:.4f}"
icon_style = f"display:inline-block;position:relative;overflow:hidden;width:{icon_advance:.3f}em;height:{icon_h:.3f}em;vertical-align:{icon_va:.3f}em;line-height:1;"

_js = r'''window.__ModuleLoader__.load({
  id: "dsh-whale-font",
  factory: (require) => {
    var module = { exports: {} };
    var exports = module.exports;
    Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
    var WHALE_PATH = "__PATH__";
    var BELLY_PATH = "__BELLY_PATH__";
    var FONT_B64 = "__FONT_B64__";
    var BASE = "__BASE__";
    var CSS_STATIC = "__CSS_STATIC__";
    function apply(ctx) {
      var style = document.createElement("style");
      style.setAttribute("data-whale-font", "1");
      style.textContent = "@font-face{font-family:'WhaleWo';src:url(data:font/otf;base64," + FONT_B64 + ") format('opentype');unicode-range:U+6211;}@font-face{font-family:'WhaleNi';src:url(data:font/otf;base64," + FONT_B64 + ") format('opentype');unicode-range:U+4F60;}" + CSS_STATIC;
      document.head.appendChild(style);
      var QUOTES = String.fromCharCode(0x201C, 0x201D, 0x2018, 0x2019, 0x22, 0x27, 0x300C, 0x300D, 0x300E, 0x300F);
      var iconTemplate = null;
      function makeIcon(label) {
        if (iconTemplate === null) {
          iconTemplate = document.createElement("span");
          iconTemplate.setAttribute("data-whale-i", "1");
          iconTemplate.style.cssText = "__ICON_STYLE__";
          var txt = document.createElement("span");
          txt.setAttribute("aria-hidden", "true");
          txt.style.cssText = "position:absolute;left:0;top:0;color:transparent;-webkit-text-fill-color:transparent;font-size:1em;line-height:1;white-space:nowrap;pointer-events:none;";
          var svg = document.createElement("span");
          svg.style.cssText = "position:absolute;left:__ICON_LSB__em;top:0;width:__ICON_W__em;height:100%;display:block;";
          svg.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="__VIEWBOX__" style="width:100%;height:100%;display:block"><path d="' + WHALE_PATH + '" fill="#4d6bfe"/><path d="' + BELLY_PATH + '" fill="#ffffff"/></svg>';
          iconTemplate.appendChild(txt);
          iconTemplate.appendChild(svg);
        }
        var el = iconTemplate.cloneNode(true);
        var kids = el.childNodes;
        for (var j = 0; j < kids.length; j++) {
          var k = kids[j];
          if (k.nodeType === 1 && k.getAttribute && k.getAttribute("aria-hidden") === "true") { k.textContent = label; break; }
        }
        return el;
      }
      function isWordCh(c) { return !!c && /[A-Za-z0-9_]/.test(c); }
      function inCode(node) {
        var el = node && node.nodeType === 1 ? node : node && node.parentElement;
        while (el && el.nodeType === 1) {
          var t = el.tagName;
          if (t === "CODE" || t === "PRE") return true;
          el = el.parentElement;
        }
        return false;
      }
      function inAssistant(node) {
        var el = node && node.nodeType === 1 ? node : node && node.parentElement;
        while (el && el.nodeType === 1) {
          if (el.getAttribute && (el.getAttribute("data-whale-i") === "1" || el.getAttribute("data-whale-quoted") === "1")) return false;
          var c = typeof el.className === "string" ? el.className : "";
          if (c.indexOf("Sxvs8a_") !== -1) return true;
          if (c.indexOf("uV2eYG_") !== -1 || c.indexOf("gdEzaW_") !== -1) return false;
          el = el.parentElement;
        }
        return false;
      }
      var inserted = new WeakMap();
      var suppress = new WeakSet();
      function stripInserts(node) {
        var list = inserted.get(node);
        if (list === undefined) return;
        for (var s = 0; s < list.length; s++) {
          var el = list[s];
          if (el.parentNode !== null) el.parentNode.removeChild(el);
        }
        inserted.set(node, []);
      }
      function processTextNode(node, fromData) {
        if (!node || node.nodeType !== 3) return;
        var parent = node.parentElement;
        if (!parent) return;
        if (!inAssistant(parent)) return;
        if (inCode(parent)) return;
        var text = node.nodeValue || "";
        if (/[我你]/.test(text) === false && text.indexOf("I") === -1 && text.indexOf("me") === -1) { if (fromData) stripInserts(node); return; }
        var frag = document.createDocumentFragment();
        var buf = "";
        var inQuote = false;
        var i = 0;
        var changed = false;
        function flush() { if (buf) { frag.appendChild(document.createTextNode(buf)); buf = ""; } }
        while (i < text.length) {
          var ch = text.charAt(i);
          if (QUOTES.indexOf(ch) !== -1) { flush(); frag.appendChild(document.createTextNode(ch)); inQuote = !inQuote; i++; continue; }
          if (inQuote) {
            var isCJK = (ch === "我" || ch === "你");
            var isI = (ch === "I" && !isWordCh(text.charAt(i - 1)) && !isWordCh(text.charAt(i + 1)));
            var isMe = (ch === "m" && text.substr(i, 2) === "me" && !isWordCh(text.charAt(i - 1)) && !isWordCh(text.charAt(i + 2)));
            if (isCJK || isI || isMe) {
              flush();
              var q = document.createElement("span");
              q.setAttribute("data-whale-quoted", "1");
              if (isCJK) q.style.cssText = "font-family:" + BASE + " !important;";
              q.textContent = isMe ? "me" : ch;
              frag.appendChild(q);
              changed = true;
              i += isMe ? 2 : 1;
              continue;
            }
          } else if (ch === "I" && !isWordCh(text.charAt(i - 1)) && !isWordCh(text.charAt(i + 1))) {
            flush(); frag.appendChild(makeIcon("I")); changed = true; i++; continue;
          } else if (ch === "m" && text.substr(i, 2) === "me" && !isWordCh(text.charAt(i - 1)) && !isWordCh(text.charAt(i + 2))) {
            flush(); frag.appendChild(makeIcon("me")); changed = true; i += 2; continue;
          }
          buf += ch;
          i++;
        }
        flush();
        if (!changed) {
          if (inserted.get(node) === undefined) return;
          stripInserts(node);
          return;
        }
        stripInserts(node);
        if (node.nodeValue !== "") {
          suppress.add(node);
          node.nodeValue = "";
        }
        var pieces = [];
        while (frag.firstChild !== null) { var c = frag.firstChild; frag.removeChild(c); pieces.push(c); }
        var ref = node.nextSibling;
        for (var p = 0; p < pieces.length; p++) parent.insertBefore(pieces[p], ref);
        inserted.set(node, pieces);
      }
      function processElement(root) {
        if (!root || root.nodeType !== 1) return;
        var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
        var nodes = [];
        var n;
        while ((n = walker.nextNode())) nodes.push(n);
        for (var k = 0; k < nodes.length; k++) processTextNode(nodes[k]);
      }
      var observer = new MutationObserver(function (muts) {
        for (var mi = 0; mi < muts.length; mi++) {
          var m = muts[mi];
          if (m.type === "childList") {
            for (var ri = 0; ri < m.removedNodes.length; ri++) {
              var r = m.removedNodes[ri];
              if (r.nodeType === 3) stripInserts(r);
            }
            for (var ai = 0; ai < m.addedNodes.length; ai++) {
              var a = m.addedNodes[ai];
              if (a.nodeType === 3) processTextNode(a);
              else if (a.nodeType === 1) processElement(a);
            }
          } else if (m.type === "characterData") {
            if (suppress.has(m.target) && m.target.nodeValue === "") continue;
            suppress.delete(m.target);
            processTextNode(m.target, true);
          }
        }
      });
      observer.observe(document.documentElement, { childList: true, characterData: true, subtree: true });
      processElement(document.documentElement);
      ctx.effect(function () { return function () { style.remove(); observer.disconnect(); }; });
    }
    exports.apply = apply;
    return module.exports;
  }
});
'''

client = (_js
          .replace('__BELLY_PATH__', belly_d)
          .replace('__PATH__', body_d)
          .replace('__FONT_B64__', b64)
          .replace('__CSS_STATIC__', css_static)
          .replace('__BASE__', BASE)
          .replace('__ICON_STYLE__', icon_style)
          .replace('__ICON_LSB__', f"{icon_lsb:.3f}")
          .replace('__ICON_W__', f"{icon_w:.3f}")
          .replace('__VIEWBOX__', icon_viewbox))

with open(OUT_CLIENT, 'w', encoding='utf-8', newline='\n') as f:
    f.write(client)

print(f"done. scaleX={SCALE_X} scaleY={SCALE_Y} yOffset={Y_OFFSET} advanceWidth={ADVANCE} leftBearing={LSB}")
print(f"raw path bbox: x[{_ox0:.2f},{_ox1:.2f}] y[{_oy0:.2f},{_oy1:.2f}]  -> icon {icon_w:.3f}em x {icon_h:.3f}em, va {icon_va:.3f}em, viewBox {icon_viewbox}")
print(f"font: {OUT_FONT} ({os.path.getsize(OUT_FONT)} bytes)")
print(f"client.js: {OUT_CLIENT}")
print("Now hard-refresh the browser (Ctrl+Shift+R).")
