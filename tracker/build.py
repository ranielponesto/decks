#!/usr/bin/env python3
"""Feed a Salesforce "All Listings for Listing Dashboard" export into the tracker.

Usage:  python3 tracker/build.py path/to/All_Listings_...xlsx --passcode <this week's passcode>
        python3 tracker/build.py --passcode <new passcode>      (rotate only, re-uses current data)

The listings are gzipped and encrypted (AES-256-GCM, key from PBKDF2-SHA256)
into tracker/listings.enc, so the data is unreadable without the passcode.
Also stamps the feed version into tracker/index.html (cache-busting) and
updates the available count on the App hub tile.
"""
import sys, json, re, datetime, pathlib, gzip, os, base64, argparse
import pandas as pd
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ROOT = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("export", nargs="?")
ap.add_argument("--passcode", required=True)
args = ap.parse_args()
ITER = 310000
enc_path = ROOT / "tracker/listings.enc"
plain_cache = pathlib.Path(os.environ.get("TRACKER_CACHE", "/tmp/tracker-listings.json"))

def encrypt(obj, pw):
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(hashes.SHA256(), 32, salt, ITER).derive(pw.encode())
    ct = AESGCM(key).encrypt(iv, gzip.compress(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode(), 9), None)
    b = lambda x: base64.b64encode(x).decode()
    return {"v": 1, "kdf": "PBKDF2-SHA256", "iter": ITER, "salt": b(salt), "iv": b(iv), "ct": b(ct)}

def decrypt(env, pw):
    d = lambda x: base64.b64decode(x)
    key = PBKDF2HMAC(hashes.SHA256(), 32, d(env["salt"]), env["iter"]).derive(pw.encode())
    return json.loads(gzip.decompress(AESGCM(key).decrypt(d(env["iv"]), d(env["ct"]), None)))

if not args.export:  # rotate passcode only
    if not plain_cache.exists():
        sys.exit(f"No cached data at {plain_cache}. Re-run with the Salesforce export.")
    data = json.loads(plain_cache.read_text())
    enc_path.write_text(json.dumps(encrypt(data, args.passcode)))
    print("Passcode rotated; data unchanged, as of", data["asOf"]); sys.exit()

src = args.export
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
enc_path.write_text(json.dumps(encrypt(data, args.passcode)))
plain_cache.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))  # local only, never committed
old = ROOT / "tracker/listings.json"
if old.exists(): old.unlink()

# available count (same rules as the page: CAP refs, no test records)
col = lambda pat: next(i for i, h in enumerate(header) if re.search(pat, h, re.I))
cref, cst, cpj, ccm, cun = col("ref no"), col("^status$"), col("project name"), col("^comm"), col("unit number")
test = re.compile(r"\btest\b|test (sales|res|comm)", re.I)
avail = sum(1 for r in rows if str(r[cref] or "").upper().startswith("CAP-") and r[cst] == "Available"
            and not test.search(f"{r[cpj] or ''} {r[ccm] or ''} {r[cun] or ''}"))

ver = re.sub(r"\D", "", as_of)[:14] or datetime.datetime.now().strftime("%Y%m%d%H%M%S")
hub = ROOT / "app/index.html"
if hub.exists():
    h = hub.read_text()
    h = re.sub(r'(id="listingsTile".*?<span class="card-area">)[\d,]+ available', rf"\g<1>{avail:,} available", h, flags=re.S)
    h = re.sub(r'(id="listingsTile".*?<span class="u-area">)[\d,]+ available', rf"\g<1>{avail:,} available", h, flags=re.S)
    hub.write_text(h)
print(f"{len(rows)} listings, {avail} available, {as_of}, version {ver}")
