#!/usr/bin/env python3
"""Build Capstone agent cards.

Reads card/agents.json and writes, for every agent:
  card/<slug>/index.html   self-contained page (the NFC / QR target)
  card/<slug>/contact.vcf  vCard 3.0 for "Save contact"
  card/<slug>/qr.svg       QR code for print / sharing
Photos are referenced as the original file placed in card/<slug>/ (never re-encoded).
Run from anywhere:  python3 card/build.py
"""
import json, os, html, base64, re, urllib.parse, io
import segno

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "agents.json"), encoding="utf-8"))
LOGO = base64.b64encode(open(os.path.join(HERE, "_logo.png"), "rb").read()).decode()
E = lambda s: html.escape(s or "", quote=True)

ICONS = {
 "save": '<path d="M15 19v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 3 17.5V19"/><circle cx="9" cy="7.5" r="3.5"/><path d="M19 8v6M16 11h6"/>',
 "phone": '<path d="M5 3.5h3l1.6 4-2 1.3a11 11 0 0 0 5.6 5.6l1.3-2 4 1.6v3A2 2 0 0 1 16.4 19 14.5 14.5 0 0 1 3 5.6 2 2 0 0 1 5 3.5Z"/>',
 "whatsapp": '<path d="M4 20l1.2-4.1A8.5 8.5 0 1 1 8.4 19Z"/><path d="M9 8.6c0 3.3 2.9 6.4 6.4 6.4l1.2-1.4-2-1.1-.9.8a4.3 4.3 0 0 1-2.9-2.9l.8-.9L10.4 7.5Z" stroke-width="1.3"/>',
 "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3.5 6 8.5 7 8.5-7"/>',
 "instagram": '<rect x="3.5" y="3.5" width="17" height="17" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.2" cy="6.8" r=".6" fill="currentColor"/>',
 "tiktok": '<path d="M14 3v11.5a3.5 3.5 0 1 1-3.5-3.5"/><path d="M14 3c.4 2.8 2.2 4.6 5 5"/>',
 "linkedin": '<rect x="3.5" y="3.5" width="17" height="17" rx="3"/><path d="M8 10.5V16M8 7.6v.1M11.5 16v-5.5M11.5 13c0-1.6 1-2.6 2.3-2.6s2.2.9 2.2 2.6V16"/>',
 "snapchat": '<path d="M12 3.5c-3 0-4.8 2.2-4.8 5v2.3l-1.9.4c.4 1 1.2 1.3 2 1.6-.6 1.6-1.8 2.8-3.3 3.3.7.7 1.8.7 2.5 1 .2.8.4 1.3 1 1.3.9 0 1.7-.5 2.8-.5 1.4 0 1.9 1.1 3.7 1.1s2.3-1.1 3.7-1.1c1.1 0 1.9.5 2.8.5.6 0 .8-.5 1-1.3.7-.3 1.8-.3 2.5-1-1.5-.5-2.7-1.7-3.3-3.3.8-.3 1.6-.6 2-1.6l-1.9-.4V8.5c0-2.8-1.8-5-4.8-5Z"/>',
 "x": '<path d="M4 4l16 16M20 4 4 20" /><path d="M4 4h4.5L20 20h-4.5Z" stroke-width="1.2"/>',
 "facebook": '<path d="M14.5 21v-7.5h2.6l.4-3h-3V8.6c0-.9.3-1.5 1.6-1.5h1.5V4.4a19 19 0 0 0-2.3-.1c-2.3 0-3.8 1.4-3.8 3.9v2.3H9v3h2.5V21"/>',
 "youtube": '<rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="m10 9.2 5 2.8-5 2.8Z"/>',
 "globe": '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.3 2.4 3.4 5.2 3.4 8.5s-1.1 6.1-3.4 8.5c-2.3-2.4-3.4-5.2-3.4-8.5S9.7 5.9 12 3.5Z"/>',
 "pin": '<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11Z"/><circle cx="12" cy="10" r="2.4"/>',
 "headset": '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><rect x="3" y="13" width="4" height="6" rx="1.5"/><rect x="17" y="13" width="4" height="6" rx="1.5"/><path d="M19 19c0 1.2-1.5 2-4 2h-2"/>',
 "qr": '<rect x="3.5" y="3.5" width="6" height="6" rx="1"/><rect x="14.5" y="3.5" width="6" height="6" rx="1"/><rect x="3.5" y="14.5" width="6" height="6" rx="1"/><path d="M14.5 14.5h2.5v2.5M20.5 14.5v.01M14.5 20.5h6v-3"/>',
 "share": '<path d="M12 15V3.5M7.5 8 12 3.5 16.5 8"/><path d="M5 12v6.5A1.5 1.5 0 0 0 6.5 20h11a1.5 1.5 0 0 0 1.5-1.5V12"/>',
 "close": '<path d="M6 6l12 12M18 6 6 18"/>',
}
def icon(n, cls="ic"):
    return f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[n]}</svg>'

SOCIAL = {  # key: (label, label_ar, url builder, display builder)
 "instagram": ("Instagram", "إنستغرام", lambda h: f"https://www.instagram.com/{h}", lambda h: "@" + h),
 "tiktok":    ("TikTok", "تيك توك", lambda h: f"https://www.tiktok.com/@{h}", lambda h: "@" + h),
 "snapchat":  ("Snapchat", "سناب شات", lambda h: f"https://www.snapchat.com/add/{h}", lambda h: h),
 "x":         ("X", "إكس", lambda h: f"https://x.com/{h}", lambda h: "@" + h),
 "linkedin":  ("LinkedIn", "لينكدإن", lambda h: h if h.startswith("http") else f"https://www.linkedin.com/in/{h}", lambda h: "View profile"),
 "facebook":  ("Facebook", "فيسبوك", lambda h: h if h.startswith("http") else f"https://www.facebook.com/{h}", lambda h: "View page"),
 "youtube":   ("YouTube", "يوتيوب", lambda h: h if h.startswith("http") else f"https://www.youtube.com/@{h}", lambda h: "Watch videos"),
}
SOC_AR_DISPLAY = {"View profile": "عرض الملف", "View page": "عرض الصفحة", "Watch videos": "مشاهدة الفيديوهات"}

def clean_handle(v):
    v = (v or "").strip()
    if v.startswith("http"): return v
    return v.lstrip("@").strip("/")

def fmt_qa(num):
    d = re.sub(r"\D", "", num or "")
    if d.startswith("974") and len(d) == 11:
        return f"+974 {d[3:7]} {d[7:]}"
    return num

def vcard(a, c, url):
    def esc(s): return (s or "").replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")
    parts = a["name"].split()
    first, last = (parts[0], " ".join(parts[1:])) if len(parts) > 1 else (a["name"], "")
    L = ["BEGIN:VCARD", "VERSION:3.0",
         f"N:{esc(last)};{esc(first)};;;", f"FN:{esc(a['name'])}",
         f"ORG:{esc(c['name'])}"]
    if a.get("title"): L.append(f"TITLE:{esc(a['title'])}")
    if a.get("phone"): L.append(f"TEL;TYPE=CELL,VOICE:{a['phone']}")
    wa = a.get("whatsapp") or a.get("phone")
    if wa and wa != a.get("phone"): L.append(f"TEL;TYPE=CELL:{wa}")
    if c.get("sales_phone"): L.append(f"TEL;TYPE=WORK,VOICE:{c['sales_phone']}")
    if a.get("email"): L.append(f"EMAIL;TYPE=INTERNET,WORK:{a['email']}")
    L.append(f"URL:{c.get('website') or 'https://www.capstoneproperty.com'}")
    if c.get("address"): L.append(f"ADR;TYPE=WORK:;;{esc(c['address'])};;;;")
    for k, v in (a.get("socials") or {}).items():
        if v and k in SOCIAL:
            L.append(f"X-SOCIALPROFILE;TYPE={k}:{SOCIAL[k][2](clean_handle(v))}")
    L.append("END:VCARD")
    return "\r\n".join(L) + "\r\n"

def row(href, ic, label, label_ar, value, value_ar=None, ext=True):
    tgt = ' target="_blank" rel="noopener"' if ext else ""
    va = value_ar if value_ar is not None else value
    dirattr = ' dir="ltr"' if va == value else ""
    return (f'<a class="row" href="{E(href)}"{tgt}>{icon(ic)}'
            f'<span class="rl"><span data-en="{E(label)}" data-ar="{E(label_ar)}">{E(label)}</span></span>'
            f'<span class="rv"{dirattr} data-en="{E(value)}" data-ar="{E(va)}">{E(value)}</span></a>')

def page(a, c, url, qr_svg):
    slug = a["slug"]
    wa = re.sub(r"\D", "", a.get("whatsapp") or a.get("phone") or "")
    first = a["name"].split()[0]
    wa_msg = urllib.parse.quote(f"Hi {first}, I got your details from your Capstone Property card.")
    initials = "".join(p[0] for p in a["name"].split()[:2]).upper()
    photo = (f'<img src="{E(a["photo"])}" alt="{E(a["name"])}">' if a.get("photo")
             else f'<span class="mono" aria-hidden="true">{E(initials)}</span>')
    langs, langs_ar = ", ".join(a.get("languages") or []), "، ".join(a.get("languages_ar") or a.get("languages") or [])

    meta = []
    if langs: meta.append(f'<span data-en="Speaks {E(langs)}" data-ar="يتحدث {E(langs_ar)}">Speaks {E(langs)}</span>')
    if a.get("license"): meta.append(f'<span data-en="Broker licence {E(a["license"])}" data-ar="رخصة وسيط {E(a["license"])}">Broker licence {E(a["license"])}</span>')
    meta_html = f'<p class="meta">{"".join(meta)}</p>' if meta else ""

    actions = []
    if a.get("phone"): actions.append(f'<a class="btn" href="tel:{E(a["phone"])}">{icon("phone")}<span data-en="Call" data-ar="اتصال">Call</span></a>')
    if a.get("email"): actions.append(f'<a class="btn" href="mailto:{E(a["email"])}">{icon("mail")}<span data-en="Email" data-ar="بريد">Email</span></a>')

    wa_btn = (f'<a class="btn wa" href="https://wa.me/{wa}?text={wa_msg}" target="_blank" rel="noopener">{icon("whatsapp")}<span data-en="Message on WhatsApp" data-ar="راسلني على واتساب">Message on WhatsApp</span></a>' if wa else "")
    soc = []
    for k, v in (a.get("socials") or {}).items():
        v = clean_handle(v)
        if not v or k not in SOCIAL: continue
        lab, lab_ar, u, d = SOCIAL[k]
        disp = d(v); soc.append(row(u(v), k, lab, lab_ar, disp, SOC_AR_DISPLAY.get(disp, disp)))
    soc_html = (f'<section class="grp"><h2 data-en="Follow {E(first)}" data-ar="تابع {E(a.get("name_ar","").split()[0] if a.get("name_ar") else first)}">Follow {E(first)}</h2>{"".join(soc)}</section>'
                if soc else "")

    comp = []
    if c.get("sales_phone"): comp.append(row(f"tel:{c['sales_phone']}", "headset", "Sales line", "خط المبيعات", fmt_qa(c["sales_phone"]), ext=False))
    if c.get("website"): comp.append(row(c["website"], "globe", "Website", "الموقع الإلكتروني", re.sub(r"^https?://", "", c["website"]).rstrip("/")))
    if c.get("address"): comp.append(row(c.get("maps_url") or f"https://maps.google.com/?q={urllib.parse.quote(c['address'])}", "pin", "Office", "المكتب", c["address"], c.get("address_ar") or c["address"]))
    for k, v in (c.get("socials") or {}).items():
        v = clean_handle(v)
        if not v or k not in SOCIAL: continue
        lab, lab_ar, u, d = SOCIAL[k]
        disp = d(v); comp.append(row(u(v), k, lab, lab_ar, disp, SOC_AR_DISPLAY.get(disp, disp)))
    comp_html = (f'<section class="grp"><h2 data-en="{E(c["name"])}" data-ar="{E(c.get("name_ar") or c["name"])}">{E(c["name"])}</h2>{"".join(comp)}</section>'
                 if comp else "")

    links = []
    for k, v in (a.get("socials") or {}).items():
        v = clean_handle(v)
        if v and k in SOCIAL:
            links.append((SOCIAL[k][2](v), k, SOCIAL[k][0]))
    if c.get("website"): links.append((c["website"], "globe", "Website"))
    for k, v in (c.get("socials") or {}).items():
        v = clean_handle(v)
        if v and k in SOCIAL:
            links.append((SOCIAL[k][2](v), k, c["name"] + " " + SOCIAL[k][0]))
    icons_html = ('<nav class="icons">' + "".join(
        f'<a class="icb" href="{E(h)}" target="_blank" rel="noopener" aria-label="{E(l)}" title="{E(l)}">{icon(i)}</a>' for h, i, l in links)
        + '</nav>') if links else ""
    desc = f"{a['name']} · {a.get('title','')} at {c['name']}"
    photo_hero = (f'<img class="hp" src="{E(a["photo"])}" alt="{E(a["name"])}">' if a.get("photo")
                  else f'<span class="hm" aria-hidden="true">{E(initials)}</span>')
    return f'''<!doctype html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(a["name"])} · {E(c["name"])}</title>
<meta name="description" content="{E(desc)}">
<meta name="theme-color" content="#071A26">
<meta property="og:title" content="{E(a["name"])}">
<meta property="og:description" content="{E(a.get("title",""))} · {E(c["name"])}">
<meta property="og:url" content="{E(url)}">
{f'<meta property="og:image" content="{E(url + a["photo"])}">' if a.get("photo") else ""}
<link rel="icon" href="../../favicon.ico">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500&family=IBM+Plex+Sans+Arabic:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root{{--bg:#071A26;--bg2:#0C2533;--line:rgba(255,255,255,.12);--txt:#fff;--sub:rgba(255,255,255,.58);--gold:#C9A77C;--wa:#25D366;
 --f:'Space Grotesk',system-ui,-apple-system,'Segoe UI',sans-serif;--fa:'IBM Plex Sans Arabic','Geeza Pro','Segoe UI',Tahoma,sans-serif}}
*{{box-sizing:border-box;margin:0}}
html{{background:#040F17;-webkit-text-size-adjust:100%}}
body{{min-height:100svh;font-family:var(--f);color:var(--txt);background:#040F17;display:flex;justify-content:center;padding-bottom:env(safe-area-inset-bottom,0)}}
[dir=rtl] body,[dir=rtl] button{{font-family:var(--fa)}}
.card{{width:100%;max-width:440px;height:100vh;height:100svh;background:var(--bg);position:relative;overflow:hidden;display:flex;flex-direction:column}}
@media (min-width:560px) and (min-height:700px){{body{{align-items:center}}.card{{height:min(900px,calc(100svh - 64px));border-radius:32px;box-shadow:0 40px 100px rgba(0,0,0,.55)}}}}
.hero{{position:relative;flex:1 1 0;min-height:110px;background:#0B3042;overflow:hidden}}
.hp{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 12%}}
.hm{{position:absolute;inset:0;display:grid;place-items:center;font:300 88px/1 var(--f);color:var(--gold)}}
.hero::after{{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(7,26,38,.55) 0,rgba(7,26,38,0) 22%,rgba(7,26,38,0) 55%,var(--bg) 100%)}}
.top{{position:absolute;z-index:2;inset:0 0 auto;display:flex;justify-content:space-between;align-items:center;padding:calc(20px + env(safe-area-inset-top,0px)) 22px 0}}
.logo{{width:112px;aspect-ratio:640/171;background:#fff;-webkit-mask:url(data:image/png;base64,{LOGO}) left center/contain no-repeat;mask:url(data:image/png;base64,{LOGO}) left center/contain no-repeat}}
[dir=rtl] .logo{{-webkit-mask-position:right center;mask-position:right center}}
.lang{{font:400 13px/1 var(--fa);color:#fff;background:rgba(7,26,38,.35);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,.25);border-radius:99px;padding:8px 14px;cursor:pointer}}
[dir=rtl] .lang{{font-family:var(--f)}}
.body{{position:relative;z-index:2;flex:none;margin-top:calc(-1 * clamp(48px,8svh,76px));padding:0 clamp(18px,6vw,26px) clamp(12px,2.2svh,24px);display:flex;flex-direction:column}}
h1{{font-weight:400;font-size:clamp(26px,min(9vw,4.6svh),40px);line-height:1.04;letter-spacing:-.025em}}
[dir=rtl] h1{{letter-spacing:0;line-height:1.3}}
.ttl{{margin-top:clamp(4px,1svh,10px);font-size:clamp(13px,1.8svh,15px);font-weight:300;color:var(--gold);letter-spacing:.01em}}
.meta{{margin-top:10px;display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13px;color:var(--sub)}}
.cta{{margin-top:clamp(12px,2.8svh,30px);display:grid;gap:clamp(6px,1.1svh,10px)}}
.btn{{display:flex;align-items:center;justify-content:center;gap:10px;height:clamp(42px,6.4svh,56px);border-radius:99px;font:500 clamp(14px,1.9svh,16px)/1 inherit;font-family:inherit;text-decoration:none;color:#fff;border:1px solid var(--line);background:transparent;transition:background .2s,transform .15s}}
.btn:active{{transform:scale(.985)}}
.btn .ic{{width:20px;height:20px}}
.btn.wa{{background:#fff;color:var(--bg);border-color:#fff}}
.btn.wa .ic{{color:#1DAA53;width:22px;height:22px}}
@media (hover:hover){{.btn:hover{{background:rgba(255,255,255,.06)}}.btn.wa:hover{{background:#EEF2F4}}}}
.pair{{display:grid;grid-template-columns:repeat(auto-fit,minmax(0,1fr));gap:clamp(6px,1.1svh,10px)}}
.grp{{margin-top:clamp(10px,2.4svh,30px)}}
.grp h2{{font-size:12px;font-weight:400;color:var(--sub);padding-bottom:clamp(0px,.5svh,6px)}}
.row{{display:flex;align-items:center;gap:14px;padding:clamp(8px,1.6svh,15px) 0;color:#fff;text-decoration:none;border-bottom:1px solid var(--line)}}
.row .ic{{width:20px;height:20px;flex:none;color:var(--gold)}}
.rl{{flex:none;font-size:clamp(14px,1.9svh,15px)}}
.rv{{margin-inline-start:auto;unicode-bidi:isolate;font-size:14px;color:var(--sub);text-align:end;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}}
@media (hover:hover){{.row:hover .rv{{color:#fff}}}}
.icons{{margin-top:clamp(16px,3.2svh,32px);display:flex;justify-content:center;gap:14px}}
.icb{{width:clamp(46px,6.4svh,54px);height:clamp(46px,6.4svh,54px);border-radius:50%;border:1px solid var(--line);display:grid;place-items:center;color:var(--gold);transition:background .2s,color .2s}}
.icb .ic{{width:22px;height:22px}}
@media (hover:hover){{.icb:hover{{background:rgba(255,255,255,.06);color:#fff}}}}
.tools{{margin-top:clamp(4px,1.2svh,14px);padding-top:clamp(6px,1.6svh,22px);display:flex;justify-content:center;gap:8px}}
.tool{{display:flex;align-items:center;gap:8px;padding:10px 16px;border:0;border-radius:99px;background:transparent;color:var(--sub);font:400 14px/1 var(--f);cursor:pointer;transition:color .2s,background .2s}}
[dir=rtl] .tool{{font-family:var(--fa)}}
.tool .ic{{width:18px;height:18px}}
@media (hover:hover){{.tool:hover{{color:#fff;background:rgba(255,255,255,.06)}}}}
.foot{{text-align:center;font-size:11px;color:rgba(255,255,255,.32);padding-top:clamp(2px,.8svh,10px)}}
@media (max-height:620px){{.foot{{display:none}}.grp h2{{display:none}}.grp+.grp{{margin-top:0}}}}
/* landscape phones: too short for one screen, fall back to scrolling */
@media (max-height:480px){{.card{{height:auto;min-height:100svh}}.hero{{flex:none;height:260px}}.foot{{display:block}}}}
a:focus-visible,button:focus-visible{{outline:2px solid var(--gold);outline-offset:3px}}
.qr{{position:fixed;inset:0;z-index:10;background:rgba(4,15,23,.8);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);display:grid;place-items:center;padding:24px;opacity:0;visibility:hidden;transition:opacity .2s,visibility 0s .2s}}
.qr.on{{opacity:1;visibility:visible;transition:opacity .2s}}
.qrbox{{position:relative;background:#fff;color:var(--bg);border-radius:28px;padding:52px 28px 24px;width:min(330px,100%);text-align:center;transform:translateY(12px);transition:transform .25s}}
.qr.on .qrbox{{transform:none}}
.qrbox svg.code{{width:100%;height:auto;display:block}}
.qrbox b{{display:block;margin-top:16px;font-size:18px;font-weight:500}}
.qrbox small{{display:block;margin-top:4px;color:#5C6B7A;font-size:13px}}
.x{{position:absolute;top:12px;inset-inline-end:12px;width:36px;height:36px;border-radius:50%;border:0;background:#F1F4F6;color:var(--bg);display:grid;place-items:center;cursor:pointer}}
.x .ic{{width:18px;height:18px}}
.toast{{position:fixed;left:50%;bottom:calc(24px + env(safe-area-inset-bottom,0px));transform:translate(-50%,20px);background:#fff;color:var(--bg);padding:11px 18px;border-radius:99px;font-size:14px;opacity:0;transition:.2s;pointer-events:none;z-index:11}}
.toast.on{{opacity:1;transform:translate(-50%,0)}}
@media (prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
</style>
</head>
<body>
<main class="card">
 <div class="hero">{photo_hero}
  <div class="top"><span class="logo" role="img" aria-label="{E(c["name"])}"></span><button class="lang" id="lang" type="button" lang="ar">عربي</button></div>
 </div>
 <div class="body">
  <h1 data-en="{E(a["name"])}" data-ar="{E(a.get("name_ar") or a["name"])}">{E(a["name"])}</h1>
  <p class="ttl" data-en="{E(a.get("title",""))}" data-ar="{E(a.get("title_ar") or a.get("title",""))}">{E(a.get("title",""))}</p>
  {meta_html}
  <div class="cta">
   {wa_btn}
   <a class="btn" href="contact.vcf">{icon("save")}<span data-en="Save contact" data-ar="حفظ جهة الاتصال">Save contact</span></a>
   <div class="pair">{"".join(actions)}</div>
  </div>
  {icons_html}
  <div class="tools">
   <button class="tool" type="button" id="qrb">{icon("qr")}<span data-en="QR code" data-ar="رمز QR">QR code</span></button>
   <button class="tool" type="button" id="shb">{icon("share")}<span data-en="Share card" data-ar="مشاركة البطاقة">Share card</span></button>
  </div>
  <p class="foot" data-en="© {E(c["name"])}" data-ar="© {E(c.get("name_ar") or c["name"])}">© {E(c["name"])}</p>
 </div>
</main>
<div class="qr" id="qr" role="dialog" aria-modal="true" aria-label="QR code">
 <div class="qrbox"><button class="x" type="button" id="qrx" aria-label="Close">{icon("close")}</button>
  {qr_svg}
  <b data-en="{E(a["name"])}" data-ar="{E(a.get("name_ar") or a["name"])}">{E(a["name"])}</b>
  <small data-en="Scan to open this card" data-ar="امسح لفتح البطاقة">Scan to open this card</small></div>
</div>
<div class="toast" id="toast" role="status"></div>
<script>
(function(){{
 var root=document.documentElement,btn=document.getElementById('lang'),L='en';
 function set(l){{L=l;root.lang=l;root.dir=l==='ar'?'rtl':'ltr';
  document.querySelectorAll('[data-en]').forEach(function(n){{n.textContent=n.getAttribute('data-'+l)}});
  btn.textContent=l==='ar'?'English':'عربي';btn.lang=l==='ar'?'en':'ar';
  try{{localStorage.setItem('cardLang',l)}}catch(e){{}}}}
 btn.onclick=function(){{set(L==='ar'?'en':'ar')}};
 var saved=null;try{{saved=localStorage.getItem('cardLang')}}catch(e){{}}
 if(saved==='ar'||(!saved&&/^ar/i.test(navigator.language||'')))set('ar');
 var qr=document.getElementById('qr');
 function tog(o){{qr.classList.toggle('on',o)}}
 document.getElementById('qrb').onclick=function(){{tog(true)}};
 document.getElementById('qrx').onclick=function(){{tog(false)}};
 qr.onclick=function(e){{if(e.target===qr)tog(false)}};
 document.addEventListener('keydown',function(e){{if(e.key==='Escape')tog(false)}});
 var t=document.getElementById('toast'),tt;
 function toast(m){{t.textContent=m;t.classList.add('on');clearTimeout(tt);tt=setTimeout(function(){{t.classList.remove('on')}},2200)}}
 var URL_={json.dumps(url)},NAME={json.dumps(a["name"])};
 document.getElementById('shb').onclick=function(){{
  if(navigator.share){{navigator.share({{title:NAME,text:NAME+' · {E(c["name"])}',url:URL_}}).catch(function(){{}});return}}
  (navigator.clipboard?navigator.clipboard.writeText(URL_):Promise.reject()).then(function(){{toast(L==='ar'?'تم نسخ الرابط':'Link copied')}},function(){{prompt('Copy link',URL_)}});
 }};
}})();
</script>
</body>
</html>
'''


def qr_svg(url):
    q = segno.make(url, error="m")
    buf = io.BytesIO(); q.save(buf, kind="svg", scale=1, border=0, dark="#0A1F3C", xmldecl=False, svgns=True, svgclass="code", nl=False)
    v = buf.getvalue().decode()
    n = q.symbol_size(scale=1, border=0)[0]
    return re.sub(r'width="\d+" height="\d+"', f'viewBox="0 0 {n} {n}" shape-rendering="crispEdges"', v, count=1)

def qr_print(url):
    q = segno.make(url, error="q")
    buf = io.BytesIO(); q.save(buf, kind="svg", scale=10, border=4, dark="#0A1F3C", xmldecl=True)
    return buf.getvalue().decode()

def main():
    c = DATA["company"]
    for a in DATA["agents"]:
        slug = a["slug"]; url = DATA["base_url"] + slug + "/"
        d = os.path.join(HERE, slug); os.makedirs(d, exist_ok=True)
        if a.get("photo") and not os.path.exists(os.path.join(d, a["photo"])):
            raise SystemExit(f"{slug}: photo {a['photo']} missing in card/{slug}/")
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page(a, c, url, qr_svg(url)))
        open(os.path.join(d, "contact.vcf"), "w", encoding="utf-8", newline="").write(vcard(a, c, url))
        open(os.path.join(d, "qr.svg"), "w", encoding="utf-8").write(qr_print(url))
        print("built", url)

if __name__ == "__main__":
    main()
