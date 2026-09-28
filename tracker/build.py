#!/usr/bin/env python3
"""Feed a Salesforce "All Listings for Listing Dashboard" export into the tracker.

Usage:  python3 tracker/build.py path/to/All_Listings_...xlsx

Writes tracker/listings.json, stamps its version into tracker/index.html
(cache-busting), and updates the available count on the App hub tile.
"""
import sys, json, re, datetime, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = sys.argv[1]
raw = pd.read_excel(src, header=None, dtype=object)

hi = next(i for i in range(len(raw)) if raw.iloc[i].astype(str).str.contains("Ref No", case=False).any())
hdr = raw.iloc[hi]
idx = [i for i, h in hdr.items() if pd.notna(h) and str(h).strip()]
as_of = next((str(v) for v in raw.iloc[:hi].values.ravel() if isinstance(v, str) and v.lower().startswith("as of")), "")

def cv(v):
    if pd.isna(v): return None
    if isinstance(v, float) and v.is_integer(): return int(v)
    return v if isinstance(v, (int, float)) else str(v).strip()

header = [str(hdr[i]).strip() for i in idx]
rows = [[cv(r[i]) for i in idx] for _, r in raw.iloc[hi + 1:].iterrows()]
rows = [r for r in rows if any(v is not None for v in r)]
data = {"asOf": as_of, "header": header, "rows": rows}
(ROOT / "tracker/listings.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))

# available count (same rules as the page: CAP refs, no test records)
col = lambda pat: next(i for i, h in enumerate(header) if re.search(pat, h, re.I))
cref, cst, cpj, ccm, cun = col("ref no"), col("^status$"), col("project name"), col("^comm"), col("unit number")
test = re.compile(r"\btest\b|test (sales|res|comm)", re.I)
avail = sum(1 for r in rows if str(r[cref] or "").upper().startswith("CAP-") and r[cst] == "Available"
            and not test.search(f"{r[cpj] or ''} {r[ccm] or ''} {r[cun] or ''}"))

ver = re.sub(r"\D", "", as_of)[:14] or datetime.datetime.now().strftime("%Y%m%d%H%M%S")
page = ROOT / "tracker/index.html"
page.write_text(re.sub(r'const FEED_VERSION="[^"]*"', f'const FEED_VERSION="{ver}"', page.read_text()))
hub = ROOT / "app/index.html"
if hub.exists():
    h = hub.read_text()
    h = re.sub(r'(id="listingsTile".*?<span class="card-area">)[\d,]+ available', rf"\g<1>{avail:,} available", h, flags=re.S)
    h = re.sub(r'(id="listingsTile".*?<span class="u-area">)[\d,]+ available', rf"\g<1>{avail:,} available", h, flags=re.S)
    hub.write_text(h)
print(f"{len(rows)} listings, {avail} available, {as_of}, version {ver}")
