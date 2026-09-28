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
    L.append(f"URL:{url}")
    if c.get("website"): L.append(f"URL;TYPE=WORK:{c['website']}")
    if c.get("address"): L.append(f"ADR;TYPE=WORK:;;{esc(c['address'])};;;;")
    for k, v in (a.get("socials") or {}).items():
        if v and k in SOCIAL:
            L.append(f"X-SOCIALPROFILE;TYPE={k}:{SOCIAL[k][2](clean_handle(v))}")
    L.append(f"NOTE:{esc(c['name'])} property consultant. Digital card: {url}")
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
    if a.get("phone"): actions.append(f'<a class="act" href="tel:{E(a["phone"])}">{icon("phone")}<span data-en="Call" data-ar="اتصال">Call</span></a>')
    if a.get("email"): actions.append(f'<a class="act" href="mailto:{E(a["email"])}">{icon("mail")}<span data-en="Email" data-ar="بريد">Email</span></a>')

    wa_btn = (f'<a class="wa" href="https://wa.me/{wa}?text={wa_msg}" target="_blank" rel="noopener">{icon("whatsapp")}<span data-en="Message on WhatsApp" data-ar="راسلني على واتساب">Message on WhatsApp</span></a>' if wa else "")
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
    if c.get("website"): comp.append(row(c["website"], "globe", "Website", "الموقع الإلكتروني", re.sub(r"^https?://(www\.)?", "", c["website"]).rstrip("/")))
    if c.get("address"): comp.append(row(c.get("maps_url") or f"https://maps.google.com/?q={urllib.parse.quote(c['address'])}", "pin", "Office", "المكتب", c["address"], c.get("address_ar") or c["address"]))
    for k, v in (c.get("socials") or {}).items():
        v = clean_handle(v)
        if not v or k not in SOCIAL: continue
        lab, lab_ar, u, d = SOCIAL[k]
        disp = d(v); comp.append(row(u(v), k, lab, lab_ar, disp, SOC_AR_DISPLAY.get(disp, disp)))
    comp_html = (f'<section class="grp"><h2 data-en="{E(c["name"])}" data-ar="{E(c.get("name_ar") or c["name"])}">{E(c["name"])}</h2>{"".join(comp)}</section>'
                 if comp else "")

    desc = f"{a['name']} · {a.get('title','')} at {c['name']}"
    return f'''<!doctype html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(a["name"])} · {E(c["name"])}</title>
<meta name="description" content="{E(desc)}">
<meta name="theme-color" content="#0A1F3C">
<meta property="og:title" content="{E(a["name"])}">
<meta property="og:description" content="{E(a.get("title",""))} · {E(c["name"])}">
<meta property="og:url" content="{E(url)}">
<link rel="icon" href="../../favicon.ico">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=IBM+Plex+Sans+Arabic:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{--deep:#061428;--navy:#0A1F3C;--navy2:#12305A;--teal:#1FB6A6;--gold:#C9A77C;--gold-d:#9A7A4E;--mist:#8CA0B3;--paper:#F4F6F9;--ink:#0A1F3C;--line:#DCE3EB;--sub:#5C6B7A;
 --f:'Space Grotesk',system-ui,-apple-system,'Segoe UI',sans-serif;--fa:'IBM Plex Sans Arabic','Geeza Pro','Segoe UI',Tahoma,sans-serif}}
*{{box-sizing:border-box;margin:0}}
html{{background:var(--deep);-webkit-text-size-adjust:100%}}
body{{min-height:100svh;font-family:var(--f);color:#fff;background:var(--deep);
 background-image:repeating-linear-gradient(72deg,transparent 0 46px,rgba(201,167,124,.045) 46px 50px,transparent 50px 120px);
 display:flex;justify-content:center;padding:env(safe-area-inset-top,0) 0 env(safe-area-inset-bottom,0)}}
[dir=rtl] body,[dir=rtl] button{{font-family:var(--fa)}}
.card{{width:100%;max-width:460px;min-height:100svh;display:flex;flex-direction:column;background:var(--navy);position:relative;overflow:hidden}}
@media (min-width:560px){{body{{padding:40px 0}}.card{{min-height:0;border-radius:28px;box-shadow:0 30px 80px rgba(0,0,0,.45)}}}}
/* hero: the logo's slanted bars become the card face */
.face{{position:relative;padding:22px 24px 26px;isolation:isolate}}
.bars{{position:absolute;inset:0 -40px auto auto;height:330px;width:260px;z-index:-1;-webkit-mask-image:linear-gradient(#000 40%,transparent);mask-image:linear-gradient(#000 40%,transparent)}}
[dir=rtl] .bars{{inset:0 auto auto -40px;transform:scaleX(-1)}}
.top{{display:flex;justify-content:space-between;align-items:center}}
.logo{{width:124px;aspect-ratio:640/171;background:#fff;-webkit-mask:url(data:image/png;base64,{LOGO}) left center/contain no-repeat;mask:url(data:image/png;base64,{LOGO}) left center/contain no-repeat}}
[dir=rtl] .logo{{-webkit-mask-position:right center;mask-position:right center}}
.lang{{font:500 13px/1 var(--fa);color:var(--gold);background:none;border:1px solid rgba(201,167,124,.45);border-radius:99px;padding:8px 13px;cursor:pointer}}
[dir=rtl] .lang{{font-family:var(--f)}}
.who{{margin-top:44px}}
.ph{{width:104px;height:104px;border-radius:30px;overflow:hidden;background:var(--navy2);border:1.5px solid var(--gold);display:grid;place-items:center;transform:rotate(-4deg)}}
.ph img{{width:100%;height:100%;object-fit:cover;transform:rotate(4deg) scale(1.08)}}
.mono{{font:500 38px/1 var(--f);color:var(--gold);transform:rotate(4deg);letter-spacing:.02em}}
h1{{margin-top:22px;font-weight:600;font-size:clamp(30px,8.4vw,38px);line-height:1.05;letter-spacing:-.02em}}
[dir=rtl] h1{{letter-spacing:0;line-height:1.3}}
.ttl{{margin-top:8px;font-size:16px;color:var(--gold)}}
.meta{{margin-top:14px;display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13.5px;color:var(--mist)}}
.wa{{margin-top:28px;display:flex;align-items:center;justify-content:center;gap:10px;width:100%;padding:17px;border-radius:16px;background:#25D366;color:#062A17;font:600 17px/1 inherit;font-family:inherit;text-decoration:none;transition:transform .15s,background .15s}}
.wa:active{{transform:scale(.98)}}@media (hover:hover){{.wa:hover{{background:#3BE078}}}}
.wa .ic{{width:22px;height:22px}}
.wa+.save{{margin-top:10px}}
.save{{margin-top:28px;display:flex;align-items:center;justify-content:center;gap:10px;width:100%;padding:17px;border-radius:16px;background:var(--gold);color:var(--navy);
 font:600 17px/1 inherit;font-family:inherit;text-decoration:none;transition:transform .15s,background .15s}}
.save:active{{transform:scale(.98)}}@media (hover:hover){{.save:hover{{background:#D6B78E}}}}
.save .ic{{width:22px;height:22px}}
.acts{{margin-top:12px;display:grid;grid-template-columns:repeat(auto-fit,minmax(0,1fr));gap:10px}}
.act{{display:flex;flex-direction:column;align-items:center;gap:8px;padding:15px 6px 13px;border-radius:16px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.09);
 color:#fff;text-decoration:none;font-size:14px;transition:background .15s}}
.act .ic{{width:24px;height:24px;color:var(--teal)}}
@media (hover:hover){{.act:hover{{background:rgba(255,255,255,.11)}}}}
/* lower sheet */
.sheet{{flex:1;background:var(--paper);color:var(--ink);border-radius:26px 26px 0 0;padding:26px 20px 18px;display:flex;flex-direction:column;gap:22px}}
@media (min-width:560px){{.sheet{{border-radius:26px}}}}
.grp h2{{font-size:14px;font-weight:500;color:var(--sub);padding:0 6px 8px}}
.grp{{display:flex;flex-direction:column}}
.row{{display:flex;align-items:center;gap:14px;padding:14px 12px;background:#fff;color:var(--ink);text-decoration:none;border:1px solid var(--line);border-bottom-width:0}}
.row:first-of-type{{border-radius:14px 14px 0 0}}.row:last-child{{border-radius:0 0 14px 14px;border-bottom-width:1px}}
.row:first-of-type:last-child{{border-radius:14px}}
.row .ic{{width:22px;height:22px;flex:none;color:var(--gold-d)}}
.rl{{flex:none;font-weight:500;font-size:15px}}
.rv{{margin-inline-start:auto;unicode-bidi:isolate;font-size:14px;color:var(--sub);text-align:end;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}}
@media (hover:hover){{.row:hover{{background:#FAFBFC}}}}
.tools{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.tool{{display:flex;align-items:center;justify-content:center;gap:8px;padding:14px;border-radius:14px;border:1px solid var(--line);background:transparent;color:var(--ink);font:500 15px/1 var(--f);cursor:pointer}}
[dir=rtl] .tool{{font-family:var(--fa)}}
.tool .ic{{width:20px;height:20px}}
.foot{{text-align:center;font-size:12px;color:var(--sub);padding-top:2px}}
a:focus-visible,button:focus-visible{{outline:2px solid var(--teal);outline-offset:3px}}
/* QR sheet */
.qr{{position:fixed;inset:0;z-index:10;background:rgba(6,20,40,.72);backdrop-filter:blur(6px);display:grid;place-items:center;padding:24px;opacity:0;visibility:hidden;transition:opacity .2s,visibility 0s .2s}}
.qr.on{{opacity:1;visibility:visible;transition:opacity .2s}}
.qrbox{{position:relative;background:#fff;color:var(--ink);border-radius:24px;padding:52px 26px 22px;width:min(340px,100%);text-align:center;transform:translateY(12px);transition:transform .25s}}
.qr.on .qrbox{{transform:none}}
.qrbox svg.code{{width:100%;height:auto;display:block}}
.qrbox b{{display:block;margin-top:14px;font-size:18px;font-weight:600}}
.qrbox small{{display:block;margin-top:4px;color:var(--sub);font-size:13px}}
.x{{position:absolute;top:10px;inset-inline-end:10px;width:36px;height:36px;border-radius:50%;border:0;background:var(--paper);color:var(--ink);display:grid;place-items:center;cursor:pointer}}
.x .ic{{width:18px;height:18px}}
.toast{{position:fixed;left:50%;bottom:calc(24px + env(safe-area-inset-bottom,0px));transform:translate(-50%,20px);background:var(--ink);color:#fff;padding:11px 18px;border-radius:99px;font-size:14px;opacity:0;transition:.2s;pointer-events:none;z-index:11}}
.toast.on{{opacity:1;transform:translate(-50%,0)}}
@media (prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
</style>
</head>
<body>
<main class="card">
 <div class="face">
  <svg class="bars" viewBox="0 0 260 330" aria-hidden="true"><g fill="none" stroke="#C9A77C" stroke-opacity=".16" stroke-width="18" stroke-linecap="square">
   <path d="M70 330 150 -10"/><path d="M122 330 202 -10"/><path d="M174 330 254 -10"/><path d="M226 330 306 -10"/></g></svg>
  <div class="top"><span class="logo" role="img" aria-label="{E(c["name"])}"></span><button class="lang" id="lang" type="button" lang="ar">عربي</button></div>
  <div class="who">
   <div class="ph">{photo}</div>
   <h1 data-en="{E(a["name"])}" data-ar="{E(a.get("name_ar") or a["name"])}">{E(a["name"])}</h1>
   <p class="ttl" data-en="{E(a.get("title",""))}" data-ar="{E(a.get("title_ar") or a.get("title",""))}">{E(a.get("title",""))}</p>
   {meta_html}
  </div>
  {wa_btn}
  <a class="save" href="contact.vcf">{icon("save")}<span data-en="Save contact" data-ar="حفظ جهة الاتصال">Save contact</span></a>
  <nav class="acts">{"".join(actions)}</nav>
 </div>
 <div class="sheet">
  {soc_html}
  {comp_html}
  <div class="tools">
   <button class="tool" type="button" id="qrb">{icon("qr")}<span data-en="Show QR code" data-ar="رمز QR">Show QR code</span></button>
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
