"""Zet een icoon (PNG of ICO, welke naam dan ook) om naar een correcte icon.ico
zodat PyInstaller het als .exe-icoon kan gebruiken. Maakt ook logo.png aan."""
import os, glob
try:
    from PIL import Image
except Exception:
    print("[icoon] Pillow ontbreekt - sla icoon-stap over (app gebruikt ingebouwd logo).")
    raise SystemExit(0)
OUT_ICO, OUT_PNG = "icon.ico", "logo.png"
ordered = ["icon.png", "icoon.png", "logo.png"]
ordered += sorted(p for p in glob.glob("*.png") if p not in ordered)
ordered += ["icon.ico", "icoon.ico", "logo.ico"]
ordered += sorted(p for p in glob.glob("*.ico") if p not in ordered)
seen=set(); cands=[c for c in ordered if not (c in seen or seen.add(c)) and os.path.exists(c)]
img=used=None
for src in cands:
    try:
        im=Image.open(src); im.load(); img=im.convert("RGBA"); used=src; break
    except Exception:
        continue
if img is None:
    print("[icoon] Geen bruikbaar icoon (.png of .ico) gevonden. App gebruikt ingebouwd logo.")
    raise SystemExit(0)
w,h=img.size
if w!=h:
    side=max(w,h); c=Image.new("RGBA",(side,side),(0,0,0,0)); c.paste(img,((side-w)//2,(side-h)//2)); img=c
try:
    img.save(OUT_ICO, sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    img.save(OUT_PNG)
    print(f"[icoon] OK: '{used}' -> {OUT_ICO} (+ {OUT_PNG}). Wordt meegebakken in de .exe.")
except Exception as e:
    print(f"[icoon] Kon het icoon niet schrijven ({e}). App gebruikt ingebouwd logo.")
    raise SystemExit(0)
