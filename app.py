#!/usr/bin/env python3
"""Wedstrijddata - Flashscore scraper voor FC Utrecht."""

from flask import Flask, render_template_string, request, jsonify
from playwright.sync_api import sync_playwright
import re
import json
import unicodedata

app = Flask(__name__)

HTML = """<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FC Utrecht – Wedstrijddata</title>
  <style>
    :root {
      --red:    #C8102E;
      --red-dk: #a00d24;
      --red-lt: #fdf0f2;
      --grey:   #f5f5f5;
      --border: #e0e0e0;
      --text:   #1a1a1a;
      --muted:  #666;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
      background: var(--grey); min-height: 100vh;
      display: flex; flex-direction: column; align-items: center;
    }

    /* ── Header bar ─────────────────────────────── */
    .top-bar {
      width: 100%; background: var(--red);
      display: flex; align-items: center; gap: 14px;
      padding: 0 32px; height: 56px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.18);
    }
    .top-bar .crest {
      width: 34px; height: 34px; flex-shrink: 0;
      background: white; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-weight: 900; font-size: 13px; color: var(--red); letter-spacing: -0.5px;
    }
    .top-bar .club-name {
      font-size: 17px; font-weight: 700; color: white; letter-spacing: 0.3px;
    }
    .top-bar .club-name span { font-weight: 400; opacity: 0.75; }

    /* ── Card ───────────────────────────────────── */
    .card {
      background: white; border-radius: 0 0 12px 12px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.09);
      padding: 36px 40px 40px; width: 100%; max-width: 740px;
    }

    /* ── Form elements ──────────────────────────── */
    label { display: block; font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 8px; }
    .subtitle { color: var(--muted); font-size: 13px; margin-bottom: 28px; margin-top: 4px; }
    .input-row { display: flex; gap: 10px; margin-bottom: 24px; }
    input[type="text"] {
      flex: 1; padding: 11px 15px; border: 1.5px solid var(--border);
      border-radius: 8px; font-size: 14px; outline: none;
      transition: border-color 0.18s; color: var(--text);
    }
    input[type="text"]:focus { border-color: var(--red); }
    input[type="text"]::placeholder { color: #bbb; }

    button {
      padding: 11px 20px; border: none; border-radius: 8px;
      font-size: 14px; font-weight: 600; cursor: pointer;
      transition: background 0.18s, opacity 0.18s;
    }
    #btn-fetch { background: var(--red); color: white; }
    #btn-fetch:hover { background: var(--red-dk); }
    #btn-fetch:disabled { opacity: 0.45; cursor: not-allowed; }

    #btn-copy { background: var(--grey); color: var(--text); display: none; border: 1.5px solid var(--border); }
    #btn-copy:hover { background: #eaeaea; }
    #btn-copy.copied { background: #e6f4ea; color: #2e7d32; border-color: #b2dfdb; }

    #btn-copy-html { background: var(--red-lt); color: var(--red); display: none; border: 1.5px solid #f5c6cc; }
    #btn-copy-html:hover { background: #fce0e4; }
    #btn-copy-html.copied { background: #e6f4ea; color: #2e7d32; border-color: #b2dfdb; }

    .result-label {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 8px;
    }
    .btn-group { display: flex; gap: 8px; }

    textarea {
      width: 100%; height: 360px; padding: 14px 16px;
      border: 1.5px solid var(--border); border-radius: 8px;
      font-family: 'Courier New', monospace; font-size: 13px;
      line-height: 1.75; resize: vertical; outline: none;
      color: var(--text); background: #fafafa;
      transition: border-color 0.18s;
    }
    textarea:focus { border-color: var(--red); }

    .status { margin-top: 12px; font-size: 13px; color: var(--muted); min-height: 20px; }
    .status.error { color: #c0392b; }

    .spinner {
      display: inline-block; width: 13px; height: 13px;
      border: 2px solid #ddd; border-top-color: var(--red);
      border-radius: 50%; animation: spin 0.7s linear infinite;
      margin-right: 6px; vertical-align: middle;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* ── Divider ────────────────────────────────── */
    .divider {
      border: none; border-top: 1px solid var(--border); margin: 28px 0;
    }
  </style>
</head>
<body>
  <div class="top-bar">
    <div class="crest">FCU</div>
    <div class="club-name">FC Utrecht <span>· Wedstrijddata</span></div>
  </div>
  <div class="card">
    <label for="url">Flashscore- of Sofascore-link</label>
    <p class="subtitle">Plak de wedstrijd-URL hieronder en klik op Ophalen.</p>
    <div class="input-row">
      <input type="text" id="url"
        placeholder="https://www.flashscore.nl/wedstrijd/..."
        onkeydown="if(event.key==='Enter') fetchData()">
      <button id="btn-fetch" onclick="fetchData()">Ophalen</button>
    </div>
    <hr class="divider">
    <div class="result-label">
      <label for="result" style="margin-bottom:0">Resultaat</label>
      <div class="btn-group">
        <button id="btn-copy" onclick="copyResult()">Kopiëren</button>
        <button id="btn-copy-html" onclick="copyHtml()">Kopiëren als HTML</button>
      </div>
    </div>
    <textarea id="result" readonly placeholder="De wedstrijddata verschijnt hier…"></textarea>
    <div class="status" id="status"></div>
  </div>
  <script>
    let _lastHtml = '';

    async function fetchData() {
      const url = document.getElementById('url').value.trim();
      if (!url) { setStatus('Vul een Flashscore-link in.', true); return; }
      const btn = document.getElementById('btn-fetch');
      btn.disabled = true;
      document.getElementById('result').value = '';
      document.getElementById('btn-copy').style.display = 'none';
      document.getElementById('btn-copy-html').style.display = 'none';
      _lastHtml = '';
      setStatus('<span class="spinner"></span>Bezig met ophalen… (kan ~30 seconden duren)', false, true);
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 120000);
      try {
        const resp = await fetch('/ophalen', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url }),
          signal: controller.signal
        });
        clearTimeout(timer);
        const data = await resp.json();
        if (data.error) {
          setStatus('Fout: ' + data.error, true);
        } else {
          document.getElementById('result').value = data.result;
          _lastHtml = data.html || '';
          document.getElementById('btn-copy').style.display = 'inline-block';
          if (_lastHtml) document.getElementById('btn-copy-html').style.display = 'inline-block';
          setStatus('Klaar.');
        }
      } catch (e) {
        clearTimeout(timer);
        if (e.name === 'AbortError') {
          setStatus('Time-out: het ophalen duurde te lang. Probeer opnieuw.', true);
        } else {
          setStatus('Verbindingsfout: ' + e.message, true);
        }
      } finally {
        btn.disabled = false;
      }
    }
    function copyResult() {
      const ta = document.getElementById('result');
      ta.select();
      document.execCommand('copy');
      const btn = document.getElementById('btn-copy');
      btn.textContent = 'Gekopieerd!';
      btn.classList.add('copied');
      setTimeout(() => { btn.textContent = 'Kopieren'; btn.classList.remove('copied'); }, 2000);
    }
    async function copyHtml() {
      if (!_lastHtml) return;
      const btn = document.getElementById('btn-copy-html');
      try {
        await navigator.clipboard.write([
          new ClipboardItem({ 'text/html': new Blob([_lastHtml], { type: 'text/html' }) })
        ]);
        btn.textContent = 'Gekopieerd!';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = 'Kopieren als HTML'; btn.classList.remove('copied'); }, 2000);
      } catch(e) {
        // Fallback: copy plain text
        document.getElementById('result').select();
        document.execCommand('copy');
        btn.textContent = 'Gekopieerd (tekst)';
        setTimeout(() => { btn.textContent = 'Kopieren als HTML'; }, 2000);
      }
    }
    function setStatus(msg, isError=false, html=false) {
      const el = document.getElementById('status');
      el.className = 'status' + (isError ? ' error' : '');
      if (html) el.innerHTML = msg; else el.textContent = msg;
    }
  </script>
</body>
</html>"""


# ── Lineup name parser ─────────────────────────────────────────────────────────

def _parse_group_text(text: str, new_group: bool = False) -> list:
    """Parse players from one positional-group block of lf__side innerText."""
    NUMBER_RE = re.compile(r'^\d+$')
    ROLE_RE   = re.compile(r'^\(([A-Z])\)$')
    RATING_RE = re.compile(r'^\d+\.\d+$')
    MINUTE_RE = re.compile(r"^\d+[+]?\d*'$")

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    players = []
    i = 0
    first_in_group = True
    while i < len(lines):
        if NUMBER_RE.match(lines[i]):
            num = lines[i]
            i += 1
            name_parts = []
            while i < len(lines):
                ln = lines[i]
                if (NUMBER_RE.match(ln) or ROLE_RE.match(ln)
                        or RATING_RE.match(ln) or MINUTE_RE.match(ln)):
                    break
                name_parts.append(ln)
                i += 1
            role = ""
            if i < len(lines):
                rm = ROLE_RE.match(lines[i])
                if rm:
                    role = rm.group(1)
                    i += 1
            if i < len(lines) and RATING_RE.match(lines[i]):
                i += 1
            if name_parts:
                is_first = first_in_group and new_group
                first_in_group = False
                players.append({
                    "name": " ".join(name_parts),
                    "number": num,
                    "role": role,
                    "new_group": is_first,
                })
        else:
            i += 1
    return players


def _parse_starters(text: str) -> list:
    """Parse starter players from lf__side innerText.

    If the JS returned ___GROUP___ separators (positional line groups),
    parse each group separately and mark the first player of each group
    so format_lineup can insert semicolons between lines.
    """
    GROUP_SEP = '___GROUP___'
    if GROUP_SEP in text:
        groups = text.split(GROUP_SEP)
        players = []
        for gi, grp in enumerate(groups):
            grp = grp.strip()
            if grp:
                players.extend(_parse_group_text(grp, new_group=(gi > 0)))
        return players
    else:
        return _parse_group_text(text, new_group=False)


# ── API name map ──────────────────────────────────────────────────────────────

def _strip_accents(s: str) -> str:
    """Remove diacritical marks for accent-insensitive comparison.

    'Zagré' → 'Zagre', 'Chávez' → 'Chavez'
    NFC input: len(_strip_accents(s)) == len(s), so character offsets stay
    aligned and we can map matches back to the original accented string.
    """
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )


def _full_name_from_ict(abbrev: str, ict: str) -> str:
    """Extract full name from a Flashscore Dutch description (ICT field).

    Example:
        abbrev='Sorensen E.'
        ict='...Elias Sorensen (PEC Zwolle) scoort!'
        → 'Elias Sorensen'

    Strategy: find [Word] [Surname] where Word starts with the same initial
    as the last token of abbrev.
    """
    if not abbrev or not ict:
        return ""
    parts = abbrev.split()
    if len(parts) < 2:
        return ""
    initial = parts[-1].rstrip('.').upper()
    if len(initial) != 1 or not initial.isalpha():
        return ""
    surname = " ".join(parts[:-1])

    # Search accent-insensitively so "Zagre" matches "Zagré" in the ICT text.
    # NFC strings have the property len(_strip_accents(s)) == len(s), so
    # match offsets in the stripped text align 1:1 with the original.
    surname_plain = _strip_accents(surname)
    ict_plain     = _strip_accents(ict)

    pattern = re.compile(
        r'\b([A-ZÀ-Ÿ][a-zà-ÿA-ZÀ-Ÿ\-]+)\s+' + re.escape(surname_plain) + r'\b',
        re.UNICODE,
    )
    for m in pattern.finditer(ict_plain):
        firstname_plain = m.group(1)
        if firstname_plain[0].upper() == initial:
            # Recover accented original from ict using the same offsets
            if len(ict_plain) == len(ict):
                orig = ict[m.start():m.end()]
                return orig   # e.g. "Arthur Zagré"
            # Fallback when lengths diverge (exotic Unicode)
            return f"{firstname_plain} {surname}"
    return ""


def _full_name_from_slug(abbrev: str, url: str) -> str:
    """Extract full name from a Flashscore player profile URL slug.

    Example:
        abbrev='Sorensen E.'
        url='/speler/sorensen-elias/nRObfo4d/'
        → 'Elias Sorensen'

    Flashscore slug order: surname-parts first, then firstname.
    We identify the firstname slug-part by matching the initial from abbrev.
    """
    if not abbrev or not url:
        return ""
    m = re.search(r'/(?:speler|player)/([a-z][a-z0-9-]+)/[A-Za-z0-9]{4,}', url)
    if not m:
        return ""
    slug = m.group(1)
    parts = abbrev.split()
    if len(parts) < 2:
        return ""
    initial = parts[-1].rstrip('.').upper()
    if len(initial) != 1 or not initial.isalpha():
        return ""
    slug_parts = slug.split('-')
    surname_words = [w.lower() for w in parts[:-1]]
    # Find the first slug-part that matches the initial and is not a surname word
    fn_idx = -1
    for si, sp in enumerate(slug_parts):
        if sp[0].upper() == initial and len(sp) > 1 and sp.lower() not in surname_words:
            fn_idx = si
            break
    if fn_idx < 0:
        return ""
    # Collect ALL consecutive parts from fn_idx as the firstname
    # (handles hyphenated names like Ro-Zangelo from slug 'daal-ro-zangelo')
    fn_parts = []
    for sp in slug_parts[fn_idx:]:
        if sp.lower() in surname_words:
            break
        fn_parts.append(sp)
    firstname = '-'.join(p.capitalize() for p in fn_parts)
    surname = " ".join(parts[:-1])
    return _fix_particles(f"{firstname} {surname}")


_LOWERCASE_PARTICLES = {"van", "de", "den", "der", "het", "di", "da", "del", "el", "le", "la"}


def _referee_full_name(slug: str, abbrev: str) -> str:
    """Convert Flashscore referee slug + abbreviated name to full name.

    Examples:
        slug='makkelie-danny', abbrev='Makkelie D.' → 'Danny Makkelie'
        slug='lindhout-bas',   abbrev='Lindhout B.' → 'Bas Lindhout'
    """
    slug_parts = slug.split('-')
    parts = abbrev.strip().split()

    if len(parts) >= 2:
        initial = parts[-1].rstrip('.').upper()
        if len(initial) == 1 and initial.isalpha():
            surname_words = [w.lower() for w in parts[:-1]]
            candidates = [sp for sp in slug_parts
                          if sp[0].upper() == initial and len(sp) > 1
                          and sp.lower() not in surname_words]
            if candidates:
                firstname = candidates[0].capitalize()
                surname   = ' '.join(parts[:-1])
                return f"{firstname} {surname}"

    # Fallback: capitalise all slug parts (keep particles lowercase)
    return ' '.join(w if w in _LOWERCASE_PARTICLES else w.capitalize()
                    for w in slug_parts)


def parse_api_meta(texts: list) -> dict:
    """Extract match metadata (referee, venue, etc.) from Flashscore MIT/MIV pairs.

    Response 5 ends with records like:
        MIT÷REF¬MIV÷Lindhout A.¬MIT÷VEN¬MIV÷De Grolsch Veste¬...
    MIT = metadata type key, MIV = metadata value.
    Returns dict, e.g. {'referee': 'Lindhout A.', 'venue': 'De Grolsch Veste'}.

    Also scans all ÷-records for referee profile URLs (IU÷/scheidsrechter/slug/...)
    to enable full-name reconstruction via _referee_full_name().
    """
    KEY_MAP = {"REF": "referee", "VEN": "venue", "TWN": "city", "ATT": "attendance"}
    meta: dict = {}
    for text in texts:
        try:
            for record in text.split('~'):
                record = record.strip()
                if not record:
                    continue
                pairs = []
                for pair in record.split('¬'):
                    if '÷' in pair:
                        k, v = pair.split('÷', 1)
                        pairs.append((k.strip(), v.strip()))

                # ── MIT/MIV metadata pairs ──────────────────────────────────
                if 'MIT' in record:
                    i = 0
                    while i < len(pairs):
                        k, v = pairs[i]
                        if k == 'MIT' and v in KEY_MAP and i + 1 < len(pairs):
                            nk, nv = pairs[i + 1]
                            if nk == 'MIV' and nv:
                                meta[KEY_MAP[v]] = nv
                        i += 1

                # ── Referee profile URL (IU÷/scheidsrechter/slug/ID/) ───────
                if 'referee_slug' not in meta:
                    for k, v in pairs:
                        if k == 'IU':
                            m = re.search(
                                r'/(?:scheidsrechter|referee)/([a-z][a-z0-9-]+)/[A-Za-z0-9]+',
                                v)
                            if m:
                                meta['referee_slug'] = m.group(1)
                                break
        except Exception:
            pass

    # If we found both the abbreviated name and a slug, upgrade to full name
    if meta.get('referee_slug') and meta.get('referee'):
        full = _referee_full_name(meta['referee_slug'], meta['referee'])
        if ' ' in full:   # has both first and last name
            meta['referee'] = full

    return meta


def _fix_particles(name: str) -> str:
    """Lowercase Dutch name particles that follow a firstname.

    'Jari De Busser'   → 'Jari de Busser'
    'Davy Van Den Berg' → 'Davy van den Berg'
    Leaves particles at the START (before the firstname) untouched:
    'van Rooij Bart' is handled by _fix_json_name_order → 'Bart van Rooij'.
    """
    words = name.split()
    if len(words) < 3:
        return name
    result = [words[0]]  # voornaam blijft zoals het is
    for w in words[1:]:
        result.append(w.lower() if w.lower() in _LOWERCASE_PARTICLES else w)
    return ' '.join(result)


def _fix_json_name_order(full: str, short: str) -> str:
    """Detect and fix Flashscore JSON name order.

    Flashscore's JSON API stores player names as "Achternaam Voornaam"
    (surname first), e.g. "Unnerstall Lars" for abbreviated "Unnerstall L."
    We detect this by checking if the LAST word starts with the initial from
    the abbreviated name, and reverse to "Voornaam Achternaam" if so.

    Works for particles too:
        "van der Haar D." + "van der Haar Damian" → "Damian van der Haar"
    """
    if not full or not short:
        return full
    abbrev_parts = short.strip().split()
    if len(abbrev_parts) < 2:
        return full
    initial = abbrev_parts[-1].rstrip('.').upper()
    if len(initial) != 1 or not initial.isalpha():
        return full
    full_parts = full.split()
    if len(full_parts) < 2:
        return full
    last = full_parts[-1]
    if last and last[0].upper() == initial:
        # Last word = voornaam → "Achternaam Voornaam" format → omdraaien
        return f"{last} {' '.join(full_parts[:-1])}"
    # First word al = voornaam → al goede volgorde
    return full


def _extract_json_names(obj, name_map: dict, depth: int = 0) -> None:
    """Recursively walk a JSON object looking for full/short name pairs."""
    if depth > 12 or not obj:
        return
    if isinstance(obj, dict):
        # Common patterns: {"name": "Unnerstall Lars", "shortName": "Unnerstall L."}
        full_keys  = ('name', 'playerName', 'fullName', 'displayName', 'longName')
        short_keys = ('shortName', 'displayShortName', 'nameShort', 'shortDisplayName',
                      'shortNameDisplay')
        full  = next((obj[k] for k in full_keys  if k in obj and isinstance(obj[k], str)), '')
        short = next((obj[k] for k in short_keys if k in obj and isinstance(obj[k], str)), '')
        if full and short and full != short and len(full) > len(short):
            # Flashscore JSON: "Achternaam Voornaam" → "Voornaam Achternaam", daarna particles
            fixed = _fix_particles(_fix_json_name_order(full, short))
            name_map[short] = fixed
            stripped = short.rstrip('.')
            if stripped != short:
                name_map[stripped] = fixed
        for v in obj.values():
            if isinstance(v, (dict, list)):
                _extract_json_names(v, name_map, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                _extract_json_names(item, name_map, depth + 1)


def parse_json_lineup_names(json_texts: list) -> dict:
    """Parse full player names from non-÷ JSON responses (e.g. Flashscore lineup data).

    Called with the contents of window.__fsJsonData — fetch responses that did NOT
    contain '÷'. If Flashscore delivers lineup data as JSON, it ends up here.
    """
    name_map: dict = {}
    for text in json_texts:
        try:
            data = json.loads(text)
            _extract_json_names(data, name_map)
        except Exception:
            pass
    return name_map


def parse_api_names(texts: list) -> dict:
    """Parse Flashscore ÷-delimited API responses for player full names.

    Handles two record types:
    1. Roster records:  NA÷Surname¬FI÷Firstname¬
    2. Event records:   IF÷Abbrev¬IU÷/speler/slug/ID/¬ICT÷Dutch description¬
       (substitutions have TWO IF+IU+ICT groups in one '~'-delimited record)

    Returns dict mapping abbreviated names to full names:
        'Sorensen E.'  → 'Elias Sorensen'
        'van Rooij B.' → 'Bart van Rooij'
    """
    name_map: dict = {}

    def register(abbrev: str, full: str) -> None:
        if not abbrev or not full:
            return
        # Skip if full name is actually shorter or the same
        if len(full.replace(" ", "")) <= len(abbrev.replace(" ", "").replace(".", "")):
            return
        name_map[abbrev] = full
        stripped = abbrev.rstrip(".")
        if stripped != abbrev:
            name_map[stripped] = full

    for text in texts:
        try:
            for record in text.split('~'):
                record = record.strip()
                if not record:
                    continue

                # Parse KEY÷VALUE pairs in order (preserves duplicate keys)
                pairs: list = []
                for pair in record.split('¬'):
                    if '÷' in pair:
                        k, v = pair.split('÷', 1)
                        k, v = k.strip(), v.strip()
                        if k:
                            pairs.append((k, v))

                # ── Source 1: roster records (NA + FI) ────────────────────
                fields = {k: v for k, v in pairs}
                surname   = fields.get('NA', '')
                firstname = fields.get('FI', '')
                if surname and firstname and len(firstname) > 1:
                    full = _fix_particles(f"{firstname} {surname}")
                    register(f"{surname} {firstname[0]}.", full)
                    register(f"{surname} {firstname[0]}",  full)

                # ── Source 2: event records (IF + IU + ICT) ───────────────
                # Walk sequentially so substitution records (two IF groups)
                # are handled correctly without the second overwriting the first.
                cur_if = cur_iu = cur_ict = None

                def flush_group() -> None:
                    if not cur_if:
                        return
                    full = (_full_name_from_ict(cur_if, cur_ict or '')
                            or _full_name_from_slug(cur_if, cur_iu or ''))
                    if full:
                        register(cur_if, _fix_particles(full))

                for k, v in pairs:
                    if k == 'IF':
                        flush_group()
                        cur_if, cur_iu, cur_ict = v, None, None
                    elif k == 'IU' and cur_if is not None:
                        cur_iu = v
                    elif k == 'ICT' and cur_if is not None:
                        cur_ict = v

                flush_group()

        except Exception:
            pass

    return name_map


# ── In-page XHR/fetch monitor script ──────────────────────────────────────────
# Injected before page load; captures all ÷-containing responses from within
# the browser itself (correct cookies/headers, no double-fetch, no server blocks).
_FS_MONITOR = """\
(function () {
    'use strict';
    var DIV = '÷';
    var has = function (t) { return typeof t === 'string' && t.indexOf(DIV) >= 0; };
    var _d = [];
    var _all = [];
    var _json = [];  // non-÷ fetch responses (lineup JSON etc.)

    // Patch XMLHttpRequest (exact original logic — proven to capture 6 responses)
    var _xSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function () {
        this.addEventListener('load', function () {
            try {
                if (has(this.responseText)) {
                    _d.push(this.responseText);
                } else if (this.responseText && this.responseText.length > 30) {
                    var u = '';
                    try { u = this.responseURL || ''; } catch (e2) {}
                    if (u && !(/\\.(js|css|png|jpg|gif|svg|woff|ico)(\\?|$)/i.test(u))) {
                        _all.push({ url: u.slice(0, 300), body: this.responseText.slice(0, 30000) });
                    }
                }
            } catch (e) {}
        });
        return _xSend.apply(this, arguments);
    };

    // Patch fetch — outer function IDENTICAL to original (do NOT change _fetch.apply call).
    // Only the inner .then() adds an else-if to capture non-÷ responses; this cannot
    // affect the returned promise because the inner callback runs asynchronously and
    // the outer .then() returns r immediately.
    var _fetch = window.fetch;
    window.fetch = function () {
        return _fetch.apply(this, arguments).then(function (r) {
            r.clone().text().then(function (t) {
                if (has(t)) {
                    _d.push(t);
                } else if (t && t.length > 50 && t.length < 500000) {
                    // Capture JSON responses (e.g. lineup data) — fire-and-forget,
                    // no effect on the outer promise or Flashscore's own fetch usage.
                    _json.push(t.slice(0, 30000));
                }
            }).catch(function () {});
            return r;
        });
    };

    window.__fsApiData  = _d;
    window.__fsAllResp  = _all;
    window.__fsJsonData = _json;
})();
"""


# ── Event extraction ───────────────────────────────────────────────────────────

def extract_events(page) -> dict:
    data = {
        "home_team": "", "away_team": "",
        "score": "", "halftime_score": "",
        "events": [],
    }

    # ── Team names: try title first, then DOM ──────────────────────────────────
    title = page.title()

    # Flashscore title formats:
    #   "| FC Utrecht - AZ 15/08/" (legacy)
    #   "FC Utrecht - AZ | eredivisie | ..."
    #   "FC Utrecht – AZ 1-4 | ..."
    for pat in [
        r"\|\s*(.+?)\s*[-–]\s*(.+?)\s*\d{2}/\d{2}/",
        r"^(.+?)\s*[-–]\s*(.+?)(?:\s+\d+[:\-]\d+|\s*\|)",
        r"^(.+?)\s*[-–]\s*(.+)",
    ]:
        tm = re.search(pat, title)
        if tm:
            data["home_team"] = tm.group(1).strip()
            away_raw = tm.group(2).strip()
            away_raw = re.sub(r'\s+\d+[:\-]\d+.*', '', away_raw).strip()
            away_raw = re.sub(r'\s*\|.*', '', away_raw).strip()
            data["away_team"] = away_raw
            if data["home_team"] and data["away_team"]:
                break

    # DOM fallback for team names
    if not data["home_team"] or not data["away_team"]:
        try:
            teams = page.evaluate("""(function() {
                var sels = [
                    '[class*="participant__participantName"]',
                    '[class*="participantName"]',
                    '[class*="teamName"]',
                    '[class*="team-name"]',
                ];
                for (var i = 0; i < sels.length; i++) {
                    var els = document.querySelectorAll(sels[i]);
                    if (els.length >= 2) {
                        return {
                            home: (els[0].innerText || els[0].textContent || '').trim(),
                            away: (els[1].innerText || els[1].textContent || '').trim()
                        };
                    }
                }
                return null;
            })()""")
            if teams and teams.get('home') and teams.get('away'):
                if not data["home_team"]:
                    data["home_team"] = teams['home']
                if not data["away_team"]:
                    data["away_team"] = teams['away']
        except Exception:
            pass

    # ── Score: title first, then DOM ──────────────────────────────────────────
    sm = re.search(r'\b(\d+)\s*[-:]\s*(\d+)\b', title)
    if sm:
        # Make sure it looks like a realistic score (not a date like 15-08)
        h, a = int(sm.group(1)), int(sm.group(2))
        if h <= 20 and a <= 20:
            data["score"] = f"{h}-{a}"

    if not data["score"]:
        try:
            score_text = page.evaluate("""(function() {
                var sels = [
                    '[class*="detailScore"]',
                    '[class*="eventScore"]',
                    '[class*="matchScore"]',
                    '[class*="scoreValue"]',
                    '[class*="score__score"]',
                ];
                for (var i = 0; i < sels.length; i++) {
                    var el = document.querySelector(sels[i]);
                    if (el) {
                        var t = (el.innerText || el.textContent || '').trim();
                        if (/\\d/.test(t)) return t;
                    }
                }
                return '';
            })()""")
            if score_text:
                nums = re.findall(r'\d+', score_text)
                if len(nums) >= 2:
                    data["score"] = f"{nums[0]}-{nums[1]}"
        except Exception:
            pass

    # ── Referee: try profile link for full name ───────────────────────────────
    try:
        ref_link = page.evaluate("""(function() {
            var links = document.querySelectorAll('a[href]');
            for (var i = 0; i < links.length; i++) {
                var href = links[i].getAttribute('href') || '';
                if (/\\/scheidsrechter\\/|\\/referee\\//.test(href)) {
                    var m = href.match(/\\/(?:scheidsrechter|referee)\\/([a-z][a-z0-9-]+)\\/[A-Za-z0-9]+/);
                    if (m) {
                        return {
                            slug: m[1],
                            text: (links[i].innerText || links[i].textContent || '').trim()
                        };
                    }
                }
            }
            return null;
        })()""")
        if ref_link and ref_link.get('slug'):
            data['referee'] = _referee_full_name(
                ref_link['slug'], ref_link.get('text', ''))
    except Exception:
        pass

    # ── Events: parse body text ────────────────────────────────────────────────
    try:
        body = page.inner_text("body")
    except Exception:
        return data

    lines = [l.strip() for l in body.split('\n') if l.strip()]

    SCORE_PAT  = re.compile(r'^(\d+)\s*-\s*(\d+)$')
    MINUTE_PAT = re.compile(r"^(\d+(?:\+\d+)?)\s*['’ʼ]$")
    REASON_PAT = re.compile(r'^\(([^)]+)\)$')
    RATING_PAT = re.compile(r'^\d+\.\d+$')

    prev_home = 0
    prev_away = 0
    skip_next_score = False
    i = 0

    while i < len(lines):
        line = lines[i]

        if line == '1E HELFT' or line.startswith('1E HELFT '):
            # Score may be on next line (finished match) or inline (live match format)
            rest = line[len('1E HELFT'):].strip()
            hsm = SCORE_PAT.match(rest) if rest else None
            if hsm:
                data["halftime_score"] = f"{hsm.group(1)}-{hsm.group(2)}"
                i += 1
                continue
            if i + 1 < len(lines):
                hsm = SCORE_PAT.match(lines[i + 1])
                if hsm:
                    data["halftime_score"] = f"{hsm.group(1)}-{hsm.group(2)}"
                    i += 2
                    continue
            i += 1
            continue

        if line == '2E HELFT' or line.startswith('2E HELFT '):
            skip_next_score = True
            i += 1
            continue

        if skip_next_score and SCORE_PAT.match(line):
            skip_next_score = False
            i += 1
            continue

        mm = MINUTE_PAT.match(line)
        if mm:
            minute = mm.group(1)
            j = i + 1
            if j >= len(lines):
                i += 1
                continue

            next_line = lines[j]
            goal_m = SCORE_PAT.match(next_line)

            if goal_m:
                new_home = int(goal_m.group(1))
                new_away = int(goal_m.group(2))
                running = f"{new_home}-{new_away}"
                team = "home" if new_home > prev_home else "away"
                prev_home = new_home
                prev_away = new_away
                j += 1

                scorer = ""
                if j < len(lines):
                    nl = lines[j]
                    if (not MINUTE_PAT.match(nl) and not SCORE_PAT.match(nl)
                            and nl not in ('1E HELFT', '2E HELFT')
                            and not RATING_PAT.match(nl)
                            and not REASON_PAT.match(nl)):
                        scorer = nl
                        j += 1

                assist = ""
                if j < len(lines) and REASON_PAT.match(lines[j]):
                    assist = REASON_PAT.match(lines[j]).group(1)
                    j += 1

                if scorer:
                    data["events"].append({
                        "minute": minute, "type": "goal",
                        "player": scorer, "assist": assist,
                        "score": running, "team": team,
                    })
                i = j

            else:
                names = []
                reason = None
                k = j

                while k < len(lines):
                    kl = lines[k]
                    if MINUTE_PAT.match(kl):
                        break
                    if kl in ('1E HELFT', '2E HELFT'):
                        break
                    if SCORE_PAT.match(kl):
                        break
                    if RATING_PAT.match(kl):
                        k += 1
                        continue
                    rm = REASON_PAT.match(kl)
                    if rm:
                        reason = rm.group(1)
                        k += 1
                        break
                    names.append(kl)
                    k += 1

                if len(names) >= 2:
                    data["events"].append({
                        "minute": minute, "type": "substitution",
                        "player": names[0], "player_out": names[1],
                        "team": None,
                    })
                elif len(names) == 1 and reason:
                    is_trainer = "veld" in reason.lower()
                    data["events"].append({
                        "minute": minute, "type": "yellow_card",
                        "player": names[0], "reason": reason,
                        "team": None, "is_trainer": is_trainer,
                    })

                i = k
        else:
            i += 1

    # Derive final score from last goal if still missing
    if not data["score"]:
        for ev in reversed(data["events"]):
            if ev["type"] == "goal":
                data["score"] = ev["score"]
                break

    return data


# ── Lineup extraction ──────────────────────────────────────────────────────────

def extract_lineups(page, summary: dict, api_name_map: dict = None) -> dict:
    """Extract starting elevens from the OPSTELLINGEN tab."""
    data = {"home_starters": [], "away_starters": []}

    # Wait for goalkeeper marker to confirm lineup has fully rendered
    try:
        page.wait_for_function(
            "() => document.body.innerText.includes('(K)')",
            timeout=12000
        )
    except Exception:
        pass

    try:
        raw = page.evaluate(r"""
        (function() {
            // Only elements whose classList contains exactly 'lf__side' as one class
            // (excludes lf__sidesBox, lf__sides which are containers)
            var pureSides = Array.from(document.querySelectorAll('[class*="lf__side"]'))
                .filter(function(el) {
                    return Array.from(el.classList).some(function(c) { return c === 'lf__side'; });
                });

            // Starter sides have exactly ONE (K) goalkeeper marker + jersey numbers
            var starterSides = pureSides.filter(function(el) {
                var text = (el.innerText || el.textContent || '').trim();
                var kCount = (text.match(/\(K\)/g) || []).length;
                return kCount === 1 && /^\d+$/m.test(text);
            });

            if (starterSides.length < 2) {
                var filled = pureSides.filter(function(s) {
                    return (s.innerText || '').trim().length > 20;
                });
                if (filled.length >= 2) starterSides = filled;
                else return { home: '', away: '' };
            }

            // Build a map of abbreviated name -> full name from multiple sources
            var nameMap = {};

            // Source 1: React component fiber data (Flashscore is a React SPA)
            (function() {
                try {
                    var root = document.querySelector('#app,#root,[id*="root"]');
                    if (!root) return;
                    var fkey = Object.keys(root).find(function(k) {
                        return k.indexOf('__reactFiber') === 0 || k.indexOf('__reactContainer') === 0;
                    });
                    if (!fkey) return;
                    function walk(node, depth) {
                        if (!node || depth > 30) return;
                        var p = node.memoizedProps || node.pendingProps || {};
                        // Various field names Flashscore might use
                        ['playerName','name','fullName','participantName'].forEach(function(fn) {
                            ['shortName','displayName','nameShort','shortDisplayName'].forEach(function(sn) {
                                if (p[fn] && p[sn] && p[fn] !== p[sn]) {
                                    nameMap[p[sn]] = p[fn];
                                }
                            });
                        });
                        walk(node.child, depth + 1);
                        walk(node.sibling, depth + 1);
                    }
                    walk(root[fkey], 0);
                } catch(e) {}
            })();

            // Source 2: player profile link URL slugs in lf__side elements
            // Flashscore slug order is surname-first, e.g. sorensen-elias → "Elias Sorensen"
            // We use the initial from the abbreviated display name to identify the firstname part.
            var PARTICLES = {van:1,de:1,den:1,der:1,het:1,di:1,da:1,del:1,el:1,le:1,la:1};

            function slugToFull(slug, short) {
                // short = abbreviated name like "Unnerstall L." or "van Rooij B."
                // slug  = flashscore slug like "unnerstall-lars" or "van-rooij-bart"
                // Returns full name like "Lars Unnerstall" or "Bart van Rooij",
                // using the original surname spelling from `short` (preserves diacritics).
                var slugParts = slug.split('-');
                var shortParts = short.trim().split(/\s+/);
                var lastToken  = shortParts[shortParts.length - 1].replace(/\.$/, '');
                var surnameFromAbbrev = shortParts.slice(0, -1).join(' '); // e.g. "Pröpper" (keeps ö)

                if (lastToken.length === 1 && /^[a-zA-Z]$/.test(lastToken)) {
                    var initial = lastToken.toLowerCase();
                    // surname words lowercased for exclusion check
                    var surnameWords = shortParts.slice(0, -1).map(function(w) { return w.toLowerCase(); });
                    // Also include ASCII-folded versions (e.g. "pröpper" → "propper")
                    surnameWords = surnameWords.concat(surnameWords.map(function(w) {
                        return w.replace(/[äàáâãå]/g,'a').replace(/[ëèéê]/g,'e')
                                .replace(/[ïìíî]/g,'i').replace(/[öòóôõø]/g,'o')
                                .replace(/[üùúû]/g,'u').replace(/ñ/g,'n').replace(/ç/g,'c');
                    }));
                    var fnIdx = -1;
                    for (var si = 0; si < slugParts.length; si++) {
                        var sp = slugParts[si];
                        if (sp.length > 1 && sp[0] === initial && surnameWords.indexOf(sp) < 0) {
                            fnIdx = si;
                            break;
                        }
                    }
                    if (fnIdx < 0) return '';
                    // Collect ALL parts from fnIdx onwards that are not surname parts
                    // This handles hyphenated names like Ro-Zangelo (slug: daal-ro-zangelo)
                    var fnParts = [];
                    for (var fi = fnIdx; fi < slugParts.length; fi++) {
                        if (surnameWords.indexOf(slugParts[fi]) >= 0) break;
                        fnParts.push(slugParts[fi].charAt(0).toUpperCase() + slugParts[fi].slice(1));
                    }
                    var firstname = fnParts.join('-');
                    // Use the original abbreviated surname to preserve diacritics (e.g. ö, ü)
                    return firstname + ' ' + surnameFromAbbrev;
                } else {
                    // No initial pattern — title-case the whole slug (less reliable)
                    return slugParts.map(function(w) {
                        return PARTICLES[w] ? w : w.charAt(0).toUpperCase() + w.slice(1);
                    }).join(' ');
                }
            }

            function extractNameFromAnchor(a) {
                // Flashscore sometimes wraps number + name in one <a>; isolate the name part.
                var rawText = (a.innerText || a.textContent || '').trim();
                if (!rawText) return '';
                // Split by newline and pick the first line that looks like a player name:
                // contains at least one letter, is not purely numeric, not a role marker like (K)
                var lines = rawText.split(/[\r\n]+/).map(function(l) { return l.trim(); });
                for (var li = 0; li < lines.length; li++) {
                    var l = lines[li];
                    if (l && /[A-Za-zÀ-ÖØ-öø-ÿ]/.test(l) && !/^\d+$/.test(l) && !/^\(\w\)$/.test(l) && !/^\d+[.'']/.test(l)) {
                        return l;
                    }
                }
                return rawText; // fallback: use full text
            }

            [starterSides[0], starterSides[1]].forEach(function(el) {
                el.querySelectorAll('a[href]').forEach(function(a) {
                    var href = a.getAttribute('href') || '';
                    var m = href.match(/\/(?:speler|player)\/([a-z][a-z0-9-]+)\/[A-Za-z0-9]{4,}/i);
                    if (!m) return;
                    var slug = m[1];
                    if (slug.indexOf('-') < 0) return;
                    var short = extractNameFromAnchor(a);
                    if (!short || short.length < 2) return;
                    var full = slugToFull(slug, short);
                    if (full && full !== short) nameMap[short] = full;
                });
            });

            // Source 3b: scan ALL player links on the page (catches players not in lf__side links)
            document.querySelectorAll('a[href*="/speler/"],a[href*="/player/"]').forEach(function(a) {
                var href = a.getAttribute('href') || '';
                var m = href.match(/\/(?:speler|player)\/([a-z][a-z0-9-]+)\/[A-Za-z0-9]{4,}/i);
                if (!m) return;
                var slug = m[1];
                if (slug.indexOf('-') < 0) return;
                var short = extractNameFromAnchor(a);
                if (!short || short.length < 2) return;
                // Only use if it looks like an abbreviated name (ends with letter + optional dot)
                if (!/[A-Z][a-z]/.test(short)) return;
                if (nameMap[short]) return; // already have it
                var full = slugToFull(slug, short);
                if (full && full !== short) nameMap[short] = full;
            });

            // Source 3: title / aria-label / data-* attributes on any child element
            [starterSides[0], starterSides[1]].forEach(function(el) {
                el.querySelectorAll('*').forEach(function(child) {
                    var inner = (child.childElementCount === 0
                        ? (child.innerText || child.textContent || '')
                        : '').trim();
                    if (!inner || inner.length < 3) return;
                    var candidates = [
                        child.getAttribute('title'),
                        child.getAttribute('aria-label'),
                        child.getAttribute('data-name'),
                        child.getAttribute('data-player-name'),
                        child.getAttribute('data-fullname'),
                    ];
                    candidates.forEach(function(attr) {
                        if (!attr || attr.length <= inner.length) return;
                        // Attribute looks like a full name (has a space, starts with letter)
                        if (!/^[A-Za-z]/.test(attr) || attr.indexOf(' ') < 0) return;
                        // Attribute shares a meaningful word with the inner text
                        var innerWords = inner.split(/[\s.]+/).filter(function(w) { return w.length > 2; });
                        var overlap = innerWords.some(function(w) {
                            return attr.toLowerCase().indexOf(w.toLowerCase()) >= 0;
                        });
                        if (overlap) nameMap[inner] = attr;
                    });
                });
            });

            function enrich(el) {
                var text = (el.innerText || el.textContent || '').trim();
                // Apply replacements longest-key-first to avoid partial overwrites
                Object.keys(nameMap)
                    .sort(function(a, b) { return b.length - a.length; })
                    .forEach(function(short) {
                        var full = nameMap[short];
                        if (text.indexOf(short) >= 0) {
                            text = text.split(short).join(full);
                        }
                    });
                return text;
            }

            // Try to detect positional line groups (lf__line containers).
            // If found, return groups joined by ___GROUP___ so Python can add
            // semicolons between goalkeeper / defenders / midfielders / forwards.
            function enrichWithGroups(sideEl) {
                try {
                    // Try multiple selector patterns Flashscore may use
                    var SELECTORS = [
                        '[class*="lf__line"]',
                        '[class*="lineUp__line"]',
                        '[class*="lineup__line"]',
                        '[class*="formation__line"]',
                        '[class*="fieldLine"]',
                    ];
                    var lineEls = null;
                    for (var si = 0; si < SELECTORS.length; si++) {
                        var cands = Array.from(sideEl.querySelectorAll(SELECTORS[si]))
                            .filter(function(e) {
                                return (e.innerText || '').trim().length > 2;
                            });
                        if (cands.length >= 2) { lineEls = cands; break; }
                    }
                    if (lineEls && lineEls.length >= 2) {
                        return lineEls.map(function(le) { return enrich(le); })
                                      .join('\n___GROUP___\n');
                    }
                } catch(e2) {}
                return enrich(sideEl);
            }

            // Flashscore DOM order: home team = index 0, away team = index 1
            // Store diagnostics globally so Python can read them after evaluate()
            window.__lastNmSize      = Object.keys(nameMap).length;
            window.__lastNmKeys      = Object.keys(nameMap).slice(0, 20);
            window.__lastPlayerLinks = document.querySelectorAll('a[href*="/speler/"],a[href*="/player/"]').length;

            return {
                home: enrichWithGroups(starterSides[0]),
                away: enrichWithGroups(starterSides[1]),
                nameMapSize:  Object.keys(nameMap).length,
                playerLinks:  window.__lastPlayerLinks,
                nameMapKeys:  window.__lastNmKeys,
            };
        })()
        """)
    except Exception:
        raw = {"home": "", "away": ""}

    # Apply API-derived full names (most reliable source — from XHR responses)
    if api_name_map:
        for side in ("home", "away"):
            txt = raw.get(side, "")
            if not txt:
                continue
            for abbrev in sorted(api_name_map, key=len, reverse=True):
                if abbrev in txt:
                    txt = txt.replace(abbrev, api_name_map[abbrev])
            raw[side] = txt

    if raw.get("home") and len(raw["home"]) > 10:
        data["home_starters"] = _parse_starters(raw["home"])
    if raw.get("away") and len(raw["away"]) > 10:
        data["away_starters"] = _parse_starters(raw["away"])

    return data


# ── Team assignment ────────────────────────────────────────────────────────────

def assign_teams(events: list, lineups: dict) -> None:
    home_players = {p["name"] for p in lineups.get("home_starters", [])}
    away_players = {p["name"] for p in lineups.get("away_starters", [])}

    def find_team(name):
        if not name:
            return None
        if name in home_players:
            return "home"
        if name in away_players:
            return "away"
        # Word-based matching: handles "Koopmeiners P." vs "Peer Koopmeiners"
        # Extract significant words (>2 chars, strip trailing dot so "P." is ignored)
        words = [w.rstrip('.').lower() for w in name.split() if len(w.rstrip('.')) > 2]
        for word in words:
            if any(word in p.lower() for p in home_players):
                return "home"
            if any(word in p.lower() for p in away_players):
                return "away"
        return None

    # First pass
    for ev in events:
        if ev.get("team") is not None:
            continue
        if ev["type"] == "substitution":
            team = find_team(ev.get("player_out")) or find_team(ev.get("player"))
        else:
            team = find_team(ev.get("player"))
        ev["team"] = team or "unknown"

    # Extend player sets with substitutes (for chain propagation)
    for ev in events:
        if ev["type"] == "substitution" and ev.get("team") in ("home", "away"):
            target = home_players if ev["team"] == "home" else away_players
            target.add(ev.get("player", ""))

    # Second pass: retry unknowns
    for ev in events:
        if ev.get("team") == "unknown":
            if ev["type"] == "substitution":
                team = find_team(ev.get("player_out")) or find_team(ev.get("player"))
            else:
                team = find_team(ev.get("player"))
            if team:
                ev["team"] = team


# ── Report formatting ──────────────────────────────────────────────────────────

def _fmt_player_with_sub(p: dict, sub_map: dict) -> str:
    """Return player name, optionally with substitution info."""
    name = p["name"]
    sub_info = sub_map.get(name)
    if not sub_info:
        name_words = {w.rstrip('.').lower() for w in name.split() if len(w.rstrip('.')) > 2}
        for key, val in sub_map.items():
            key_words = {w.rstrip('.').lower() for w in key.split() if len(w.rstrip('.')) > 2}
            if name_words & key_words:
                sub_info = val
                break
    if sub_info:
        m_min, pin = sub_info
        return f"{name} ({m_min}. {pin})"
    return name


def format_report(summary: dict, lineups: dict) -> str:
    home   = summary.get("home_team", "Thuisploeg")
    away   = summary.get("away_team", "Uitploeg")
    score  = summary.get("score", "?-?")
    ht     = summary.get("halftime_score", "?-?")
    events = summary.get("events", [])

    out = []
    out.append(f"{home} – {away} {score} ({ht})")

    for ev in events:
        if ev["type"] == "goal":
            out.append(f"{ev['minute']}. {ev['player']} {ev['score']}")

    out.append("")

    # Scheidsrechter — geen punt meer aan het einde; NIET rstrip omdat "Makkelie D."
    # anders "Makkelie D" geeft (initiaalstip weggehaald).
    ref = summary.get("referee") or "onbekend"
    out.append(f"Scheidsrechter: {ref}")

    # Yellow cards — comma-separated, club in parentheses once per team block
    home_yellows = [ev["player"] for ev in events
                    if ev["type"] == "yellow_card"
                    and ev.get("team") == "home"
                    and not ev.get("is_trainer")]
    away_yellows = [ev["player"] for ev in events
                    if ev["type"] == "yellow_card"
                    and ev.get("team") == "away"
                    and not ev.get("is_trainer")]
    card_parts = []
    if home_yellows:
        card_parts.append(f"{', '.join(home_yellows)} ({home})")
    if away_yellows:
        card_parts.append(f"{', '.join(away_yellows)} ({away})")
    if card_parts:
        out.append("Gele kaarten: " + ", ".join(card_parts))

    # Red cards
    home_reds = [ev["player"] for ev in events
                 if ev["type"] == "red_card" and ev.get("team") == "home"]
    away_reds = [ev["player"] for ev in events
                 if ev["type"] == "red_card" and ev.get("team") == "away"]
    red_parts = []
    if home_reds:
        red_parts.append(f"{', '.join(home_reds)} ({home})")
    if away_reds:
        red_parts.append(f"{', '.join(away_reds)} ({away})")
    if red_parts:
        out.append("Rode kaarten: " + ", ".join(red_parts))

    # Toeschouwers — Dutch thousands separator (dot)
    att = summary.get("attendance", "")
    if att:
        try:
            # Flashscore kan "22 738" (spatie), "22,738" (komma) of "22.738" (punt) sturen
            att_int = int(str(att).replace('.', '').replace(',', '').replace(' ', ''))
            att_str = f"{att_int:,}".replace(',', '.')
        except Exception:
            att_str = str(att)
        out.append(f"Toeschouwers: {att_str}")

    # Substitution maps (player_out -> (minute, player_in))
    home_sub_map: dict = {}
    away_sub_map: dict = {}
    for ev in events:
        if (ev["type"] == "substitution"
                and ev.get("minute") and ev.get("player") and ev.get("player_out")):
            if ev.get("team") == "home":
                home_sub_map[ev["player_out"]] = (ev["minute"], ev["player"])
            elif ev.get("team") == "away":
                away_sub_map[ev["player_out"]] = (ev["minute"], ev["player"])

    def format_lineup(starters, sub_map):
        if not starters:
            return "(niet beschikbaar)"

        # Check if we have positional group info (from lf__line detection)
        has_groups = any(p.get("new_group") for p in starters)
        if has_groups:
            groups: list = [[]]
            for p in starters:
                if p.get("new_group"):
                    groups.append([])
                groups[-1].append(p)
            group_strs = [", ".join(_fmt_player_with_sub(p, sub_map) for p in g)
                          for g in groups if g]
            return "; ".join(group_strs) + "."

        # Flat list (no group data)
        return ", ".join(_fmt_player_with_sub(p, sub_map) for p in starters) + "."

    out.append("")
    out.append(f"Opstelling {home}: " + format_lineup(lineups.get("home_starters", []), home_sub_map))
    out.append(f"Opstelling {away}: " + format_lineup(lineups.get("away_starters", []), away_sub_map))

    return "\n".join(out)


def format_report_html(plain_text: str) -> str:
    """Convert plain report text to HTML with bold labels for copy-paste into Outlook/Word."""
    import html as _html
    lines = plain_text.split('\n')
    html_lines = []
    for i, line in enumerate(lines):
        esc = _html.escape(line)
        if i == 0 and line:
            # Match header line → full bold
            html_lines.append(f"<strong>{esc}</strong>")
        elif line.startswith("Scheidsrechter:"):
            label, _, rest = line.partition(":")
            html_lines.append(f"<strong>{_html.escape(label)}:</strong>{_html.escape(rest)}")
        elif line.startswith("Gele kaarten:"):
            label, _, rest = line.partition(":")
            html_lines.append(f"<strong>{_html.escape(label)}:</strong>{_html.escape(rest)}")
        elif line.startswith("Rode kaarten:"):
            label, _, rest = line.partition(":")
            html_lines.append(f"<strong>{_html.escape(label)}:</strong>{_html.escape(rest)}")
        elif line.startswith("Toeschouwers:"):
            label, _, rest = line.partition(":")
            html_lines.append(f"<strong>{_html.escape(label)}:</strong>{_html.escape(rest)}")
        else:
            html_lines.append(esc)
    return "<br>\n".join(html_lines)


# ── Helper: apply full-name map to event player names ─────────────────────────

def apply_names_to_events(events: list, name_map: dict) -> None:
    """Enrich abbreviated player names in events using the API name map."""
    if not name_map:
        return
    for ev in events:
        for key in ("player", "player_out"):
            name = ev.get(key, "")
            if not name:
                continue
            if name in name_map:
                ev[key] = name_map[name]
                continue
            # Try without trailing dot: "Barkas V" matches "Barkas V."
            if name + "." in name_map:
                ev[key] = name_map[name + "."]
                continue
            if name.rstrip(".") in name_map:
                ev[key] = name_map[name.rstrip(".")]


# ── Sofascore scraper (page.route → guaranteed body capture) ──────────────────

def scrape_sofascore(url: str) -> str:
    """Scrape match data from Sofascore via directe API-aanroepen (geen browser nodig).

    Stap 1: haal de pagina-HTML op om het numerieke event-ID te vinden.
    Stap 2: roep api.sofascore.com rechtstreeks aan voor event, incidents en lineups.
    Dit omzeilt Cloudflare-botdetectie die headless browsers blokkeert.
    """
    import requests as _req

    sess = _req.Session()
    sess.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    # ── Stap 1: Numeriek event-ID ophalen uit pagina-HTML ────────────────────
    event_id = None
    try:
        page_r = sess.get(
            url,
            headers={
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                "Referer": "https://www.google.nl/",
            },
            timeout=20,
            allow_redirects=True,
        )
        text = page_r.text

        # Probeer Next.js __NEXT_DATA__ (meest betrouwbaar)
        ndata_m = re.search(
            r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
            text, re.DOTALL
        )
        if ndata_m:
            try:
                ndata = json.loads(ndata_m.group(1))

                def _find_event_id(obj, depth=0):
                    if depth > 15 or not obj:
                        return None
                    if isinstance(obj, dict):
                        eid = obj.get('id')
                        if isinstance(eid, int) and eid > 100000:
                            if 'homeTeam' in obj or 'homeScore' in obj or 'awayTeam' in obj:
                                return str(eid)
                        for v in obj.values():
                            r2 = _find_event_id(v, depth + 1)
                            if r2:
                                return r2
                    elif isinstance(obj, list):
                        for item in obj:
                            r2 = _find_event_id(item, depth + 1)
                            if r2:
                                return r2
                    return None

                event_id = _find_event_id(ndata)
            except Exception:
                pass

        # Fallback: zoek numeriek ID in HTML met diverse patronen
        if not event_id:
            for pat in [
                r'"id"\s*:\s*(\d{7,})\s*,\s*"customId"',
                r'"event"\s*:\s*\{[^{}]{0,200}"id"\s*:\s*(\d{7,})',
                r'"id"\s*:\s*(\d{7,})',
            ]:
                m2 = re.search(pat, text)
                if m2:
                    event_id = m2.group(1)
                    break
    except Exception:
        pass

    if not event_id:
        raise ValueError(
            "Geen data ontvangen van Sofascore. "
            "Controleer de URL of probeer een Flashscore-link."
        )

    # ── Stap 2: Sofascore API rechtstreeks aanroepen ──────────────────────────
    api_hdrs = {
        "Accept": "*/*",
        "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com",
        "Cache-Control": "no-cache",
    }

    def _api_get(path):
        r = sess.get(
            f"https://api.sofascore.com/api/v1/{path}",
            headers=api_hdrs,
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    captured: dict = {}
    try:
        captured['event'] = _api_get(f"event/{event_id}").get('event')
    except Exception as e:
        raise ValueError(f"Sofascore API onbereikbaar: {e}")

    try:
        captured['incidents'] = _api_get(f"event/{event_id}/incidents").get('incidents', [])
    except Exception:
        captured['incidents'] = []

    try:
        captured['lineups'] = _api_get(f"event/{event_id}/lineups")
    except Exception:
        captured['lineups'] = {}

    if not captured.get('event') and not captured.get('incidents'):
        raise ValueError(
            "Geen data ontvangen van Sofascore. "
            "Controleer de URL of probeer een Flashscore-link."
        )

    # ── Build summary ──────────────────────────────────────────────────────────
    ev = captured.get('event') or {}
    home_team = (ev.get("homeTeam") or {}).get("name", "Thuisploeg")
    away_team = (ev.get("awayTeam") or {}).get("name", "Uitploeg")

    hs  = ev.get("homeScore") or {}
    aws = ev.get("awayScore") or {}
    score    = f"{hs.get('current', '?')}-{aws.get('current', '?')}"
    ht_score = f"{hs.get('period1', '?')}-{aws.get('period1', '?')}"

    ref_obj = ev.get("referee") or {}
    referee = ref_obj.get("name", "onbekend") if ref_obj else "onbekend"

    # ── Process incidents ──────────────────────────────────────────────────────
    events = []
    for inc in (captured.get("incidents") or []):
        inc_type  = inc.get("incidentType", "")
        inc_class = inc.get("incidentClass", "")
        minute    = inc.get("time", 0)
        added     = inc.get("addedTime")
        min_str   = f"{minute}+{added}" if added else str(minute)
        is_home   = inc.get("isHome", True)
        team      = "home" if is_home else "away"

        if inc_type == "goal" and inc_class not in ("missedPenalty",):
            player    = (inc.get("player") or {}).get("name", "")
            h         = inc.get("homeScore", 0)
            a         = inc.get("awayScore", 0)
            goal_team = ("away" if is_home else "home") if inc_class == "ownGoal" else team
            events.append({
                "minute": min_str, "type": "goal",
                "player": player, "score": f"{h}-{a}", "team": goal_team,
            })

        elif inc_type == "card" and inc_class in ("yellow", "yellowRed"):
            player = (inc.get("player") or {}).get("name", "")
            events.append({
                "minute": min_str, "type": "yellow_card",
                "player": player, "team": team, "is_trainer": False,
            })

        elif inc_type == "card" and inc_class == "red":
            player = (inc.get("player") or {}).get("name", "")
            events.append({
                "minute": min_str, "type": "red_card",
                "player": player, "team": team,
            })

        elif inc_type == "substitution":
            pin  = (inc.get("playerIn")  or {}).get("name", "")
            pout = (inc.get("playerOut") or {}).get("name", "")
            events.append({
                "minute": min_str, "type": "substitution",
                "player": pin, "player_out": pout, "team": team,
            })

    # ── Process lineups ────────────────────────────────────────────────────────
    home_starters, away_starters = [], []
    lineup_raw = captured.get("lineups") or {}
    pos_order  = {"G": 0, "D": 1, "M": 2, "F": 3}

    for side_key, starters in [("home", home_starters), ("away", away_starters)]:
        side_data   = lineup_raw.get(side_key) or {}
        raw_players = [pl for pl in side_data.get("players", [])
                       if not pl.get("substitute", False)]
        raw_players.sort(key=lambda pl: pos_order.get(pl.get("position", "M"), 2))
        prev_pos = None
        for pl in raw_players:
            name   = (pl.get("player") or {}).get("name", "")
            number = str(pl.get("shirtNumber", ""))
            pos    = pl.get("position", "")
            new_group = (pos != prev_pos and bool(prev_pos))
            prev_pos = pos
            starters.append({"name": name, "number": number, "role": pos, "new_group": new_group})

    summary = {
        "home_team": home_team, "away_team": away_team,
        "score": score, "halftime_score": ht_score,
        "events": events, "referee": referee,
    }
    lineups = {"home_starters": home_starters, "away_starters": away_starters}
    return format_report(summary, lineups)


# ── Browser scraping ───────────────────────────────────────────────────────────

def scrape_match(url: str) -> str:
    if "sofascore" in url.lower():
        return scrape_sofascore(url)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="nl-NL",
            # Block service workers so Flashscore's sw.js cannot cache API responses
            # before our _FS_MONITOR fetch/XHR patches intercept them. This is the
            # main fix for live-match data being empty.
            service_workers="block",
        )
        page = context.new_page()

        # Inject monitor script BEFORE navigation so it patches fetch/XHR from
        # the very first request. Capturing inside the browser avoids the
        # double-fetch problem that caused Flashscore to block our route handler.
        page.add_init_script(_FS_MONITOR)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)

            # Dismiss cookie banner
            try:
                page.click("button#onetrust-accept-btn-handler", timeout=3000)
                page.wait_for_timeout(600)
            except Exception:
                pass

            # Navigate to SAMENVATTING tab and wait for match events to load
            summary_loaded = False
            for label in ("SAMENVATTING", "Samenvatting", "SUMMARY", "Summary"):
                try:
                    page.get_by_text(label, exact=True).first.click(timeout=3000)
                    summary_loaded = True
                    break
                except Exception:
                    pass

            if summary_loaded:
                # Wait until summary content is visible (look for halftime marker)
                try:
                    page.wait_for_function(
                        "() => document.body.innerText.includes('1E HELFT') "
                        "   || document.body.innerText.includes('2E HELFT')",
                        timeout=8000
                    )
                except Exception:
                    page.wait_for_timeout(2500)
            else:
                page.wait_for_timeout(2500)

            summary = extract_events(page)

            # ── Enrich event player names from SAMENVATTING slug links ────────────
            # Player profile links (/speler/surname-firstname/ID/) are present on the
            # SAMENVATTING tab for goal scorers / card recipients.  Extracting full
            # names here means we don't need ÷-API data for live-match events.
            _samenvatting_slug_map: dict = {}
            try:
                _samenvatting_slug_map = page.evaluate(r"""(function() {
                    var nameMap = {};
                    document.querySelectorAll('a[href*="/speler/"],a[href*="/player/"]')
                        .forEach(function(a) {
                            var href = a.getAttribute('href') || '';
                            var m = href.match(
                                /\/(?:speler|player)\/([a-z][a-z0-9-]+)\/[A-Za-z0-9]{4,}/i);
                            if (!m) return;
                            var slug = m[1];
                            if (slug.indexOf('-') < 0) return;
                            // Extract displayed (abbreviated) name from the link text
                            var rawText = (a.innerText || a.textContent || '').trim();
                            var lines = rawText.split(/[\r\n]+/).map(function(l){return l.trim();});
                            var short = '';
                            for (var li = 0; li < lines.length; li++) {
                                var l = lines[li];
                                if (l && /[A-Za-zÀ-ɏ]/.test(l)
                                       && !/^\d+$/.test(l)
                                       && !/^\(\w\)$/.test(l)
                                       && !/^\d+[.']/.test(l)) {
                                    short = l; break;
                                }
                            }
                            if (!short || short.length < 2) return;
                            // Convert slug to full name using the initial from abbreviated name
                            var slugParts = slug.split('-');
                            var shortParts = short.trim().split(/\s+/);
                            var lastToken  = shortParts[shortParts.length - 1].replace(/\.$/, '');
                            var surnameFromAbbrev = shortParts.slice(0, -1).join(' ');
                            if (lastToken.length === 1 && /^[a-zA-Z]$/.test(lastToken)) {
                                var initial = lastToken.toLowerCase();
                                var surnameWords = shortParts.slice(0, -1)
                                    .map(function(w){ return w.toLowerCase(); });
                                var fnIdx = -1;
                                for (var si = 0; si < slugParts.length; si++) {
                                    var sp = slugParts[si];
                                    if (sp.length > 1 && sp[0] === initial
                                            && surnameWords.indexOf(sp) < 0) {
                                        fnIdx = si; break;
                                    }
                                }
                                if (fnIdx < 0) return;
                                var fnParts = [];
                                for (var fi = fnIdx; fi < slugParts.length; fi++) {
                                    if (surnameWords.indexOf(slugParts[fi]) >= 0) break;
                                    fnParts.push(slugParts[fi].charAt(0).toUpperCase()
                                                 + slugParts[fi].slice(1));
                                }
                                var firstname = fnParts.join('-');
                                var full = firstname + ' ' + surnameFromAbbrev;
                                if (full && full.length > short.length) nameMap[short] = full;
                            } else if (short.indexOf(' ') >= 0) {
                                // Already a full name (e.g. "Weslley Patati") — keep it
                                nameMap[short] = short;
                            }
                        });
                    return nameMap;
                })()""")
                if _samenvatting_slug_map:
                    apply_names_to_events(summary["events"], _samenvatting_slug_map)
            except Exception:
                _samenvatting_slug_map = {}

            # Navigate to OPSTELLINGEN tab
            clicked = False
            for label in ("OPSTELLINGEN", "Opstellingen", "LINEUPS", "Lineups"):
                try:
                    page.get_by_text(label, exact=True).first.click(timeout=3000)
                    clicked = True
                    break
                except Exception:
                    pass
            if not clicked:
                # Try without exact match
                for label in ("OPSTELLINGEN", "Opstellingen"):
                    try:
                        page.get_by_text(label).first.click(timeout=3000)
                        clicked = True
                        break
                    except Exception:
                        pass

            lineups = {"home_starters": [], "away_starters": []}
            if clicked:
                # Step 1: wait for lineup DOM to render.
                lineups = extract_lineups(page, summary, api_name_map=None)

                # Step 2: give async fetch/clone().text() promises a moment to resolve,
                # then read all captured API data from the in-page monitor.
                page.wait_for_timeout(800)
                api_data  = page.evaluate("() => Array.from(window.__fsApiData  || [])")
                json_data = page.evaluate("() => Array.from(window.__fsJsonData || [])")

                # Step 3: parse names + match metadata from captured data.
                api_name_map = parse_api_names(api_data)
                api_meta     = parse_api_meta(api_data)

                # Step 3b: also check non-÷ JSON responses (e.g. lineup API via fetch).
                # These are merged into api_name_map; existing entries win.
                json_name_map = parse_json_lineup_names(json_data)
                for k, v in json_name_map.items():
                    if k not in api_name_map:
                        api_name_map[k] = v

                # Use API-derived referee for Flashscore matches (Sofascore has its own path).
                # DOM-extracted full name (from extract_events) takes priority.
                if api_meta.get('referee') and not summary.get('referee'):
                    summary['referee'] = api_meta['referee']

                # Try referee profile link on OPSTELLINGEN page (often visible here)
                if not summary.get('referee') or summary.get('referee') == api_meta.get('referee'):
                    try:
                        ref_link2 = page.evaluate("""(function() {
                            var links = document.querySelectorAll('a[href]');
                            for (var i = 0; i < links.length; i++) {
                                var href = links[i].getAttribute('href') || '';
                                if (/\\/scheidsrechter\\/|\\/referee\\//.test(href)) {
                                    var m = href.match(/\\/(?:scheidsrechter|referee)\\/([a-z][a-z0-9-]+)\\/[A-Za-z0-9]+/);
                                    if (m) {
                                        return { slug: m[1], text: (links[i].innerText || links[i].textContent || '').trim() };
                                    }
                                }
                            }
                            return null;
                        })()""")
                        if ref_link2 and ref_link2.get('slug'):
                            full_ref = _referee_full_name(ref_link2['slug'], ref_link2.get('text', ''))
                            # Only upgrade if we got a fuller name (has space = firstname + surname)
                            if ' ' in full_ref:
                                summary['referee'] = full_ref
                    except Exception:
                        pass

                # Attendance from API meta
                if api_meta.get('attendance') and not summary.get('attendance'):
                    summary['attendance'] = api_meta['attendance']

                # Step 4: enrich events (goals, cards, subs).
                apply_names_to_events(summary["events"], api_name_map)

                # Step 4: enrich lineup player names.
                # Use combined map: SAMENVATTING slug map + ÷-API map (API takes priority).
                _lineup_name_map = dict(_samenvatting_slug_map)
                _lineup_name_map.update(api_name_map)
                for side in ("home_starters", "away_starters"):
                    for p in lineups.get(side, []):
                        name = p["name"]
                        if name in _lineup_name_map:
                            p["name"] = _lineup_name_map[name]
                        elif (name + ".") in _lineup_name_map:
                            p["name"] = _lineup_name_map[name + "."]
                        elif name.rstrip(".") in _lineup_name_map:
                            p["name"] = _lineup_name_map[name.rstrip(".")]

            # Debug: schrijf API-data naar bestand naast app.py.
            try:
                import os as _os
                _debug = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                       'debug_api.txt')
                _ad  = locals().get('api_data', [])
                _anm = locals().get('api_name_map', {})
                _amt = locals().get('api_meta', {})
                _wider   = page.evaluate("() => Array.from(window.__fsAllResp  || [])")
                _jdata   = page.evaluate("() => Array.from(window.__fsJsonData || [])")
                _nm_sz   = page.evaluate("() => window.__lastNmSize     || 0")
                _pl_lnk  = page.evaluate("() => window.__lastPlayerLinks || 0")
                _nm_keys = page.evaluate("() => window.__lastNmKeys     || []")
                _jnm     = locals().get('json_name_map', {})
                with open(_debug, 'w', encoding='utf-8') as _f:
                    _f.write(f"Gevangen ÷-responses: {len(_ad)}\n")
                    _f.write(f"Gevangen JSON-responses (fetch, geen ÷): {len(_jdata)}\n")
                    _f.write(f"Gevangen overige XHR-responses (geen ÷): {len(_wider)}\n")
                    _f.write(f"Naam-map grootte (÷-API): {len(_anm)}\n")
                    _f.write(f"Naam-map grootte (JSON): {len(_jnm)}\n")
                    _f.write(f"API meta: {_amt}\n")
                    _f.write(f"JS nameMap grootte: {_nm_sz}\n")
                    _f.write(f"JS nameMap sleutels: {_nm_keys}\n")
                    _f.write(f"Spelerlinks in DOM: {_pl_lnk}\n")
                    _f.write(f"÷-naam-map inhoud: {dict(list(_anm.items())[:20])}\n")
                    _f.write(f"JSON-naam-map inhoud: {dict(list(_jnm.items())[:20])}\n\n")
                    for _i, _d in enumerate(_ad):
                        _f.write(f"=== ÷-Response {_i + 1} (len={len(_d)}) ===\n")
                        _f.write(_d)
                        _f.write("\n\n")
                    if _jdata:
                        _f.write("=== JSON fetch-responses (geen ÷) ===\n")
                        for _ji, _jt in enumerate(_jdata):
                            _f.write(f"--- JSON {_ji+1} (len={len(_jt)}) ---\n")
                            _f.write(_jt[:2000])
                            _f.write("\n\n")
                    if _wider:
                        _f.write("=== Overige XHR responses (geen ÷) ===\n")
                        for _w in _wider:
                            _f.write(f"URL: {_w.get('url','')}\n")
                            _f.write(f"Body: {_w.get('body','')[:1000]}\n\n")
            except Exception:
                pass

            browser.close()

            assign_teams(summary["events"], lineups)
            return format_report(summary, lineups)

        except Exception as e:
            try:
                browser.close()
            except Exception:
                pass
            raise e


# ── Flask routes ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/ophalen", methods=["POST"])
def ophalen():
    body = request.get_json(silent=True) or {}
    url = (body.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Geen URL opgegeven."}), 400
    if "flashscore" not in url and "sofascore" not in url:
        return jsonify({"error": "Alleen Flashscore- of Sofascore-links worden ondersteund."}), 400
    try:
        result = scrape_match(url)
        return jsonify({"result": result, "html": format_report_html(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    print(f"Wedstrijddata draait op http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
