# -*- coding: utf-8 -*-
"""
esik_kontrol.py - Uc nokta isaretlerinin (la abn, lvedd abn, qtc abn, qrs abn) hangi esikle
konuldugunu ham veriden kontrol eder. Hasta adi/numarasi YAZDIRMAZ; yalnizca sayilar.
KULLANIM: ▶ veya  py esik_kontrol.py
"""
import os, sys, re
import pandas as pd
KLASOR = os.path.dirname(os.path.abspath(__file__))
def bul(ad):
    k = KLASOR
    while True:
        for a in (os.path.join(k, ad), os.path.join(k, "07_Analiz", ad)):
            if os.path.exists(a): return a
        u = os.path.dirname(k)
        if u == k: sys.exit("bulunamadi: " + ad)
        k = u
raw = pd.read_excel(bul("aiveri2026_haz.xlsx"))
cins = pd.to_numeric(raw.get("CİNSİYET"), errors="coerce") if "CİNSİYET" in raw.columns else None
print("Cinsiyet kodlari ve sayilari:", None if cins is None else cins.value_counts().to_dict())
ANAHTAR = {"la": ["la", "atr", "atriy"], "lvedd": ["lvedd", "lved", "diyastol", "edd"], "qtc": ["qtc", "qt"],
           "qrs": ["qrs"], "ef": ["ef", "ejek"]}
print("Ilgili olabilecek tum sutun adlari (yalnizca basliklar):")
for c in raw.columns:
    lc = str(c).lower()
    if any(k in lc for ks in ANAHTAR.values() for k in ks if len(k) > 2) or re.search(r"\b(la|ef)\b", lc):
        v = pd.to_numeric(raw[c], errors="coerce")
        print("   %-35s dolu(sayisal) %4d  min %s  max %s" % (c, v.notna().sum(), v.min(), v.max()))
for kok in ["la", "lvedd", "qtc", "qrs", "ef"]:
    bayrak = [c for c in raw.columns if str(c).strip().lower() == kok + " abn"]
    deger = [c for c in raw.columns if str(c).strip().lower() != kok + " abn"
             and any(k in str(c).lower() for k in ANAHTAR[kok] if len(k) > 2 or re.search(r"\b%s\b" % k, str(c).lower()))
             and pd.to_numeric(raw[c], errors="coerce").notna().sum() > 50
             and pd.to_numeric(raw[c], errors="coerce").max() > 2]
    print("\n=== %s | deger sutunlari: %s | isaret sutunu: %s" % (kok.upper(), deger, bayrak))
    for dc in deger:
        v = pd.to_numeric(raw[dc], errors="coerce")
        print("  %s: dolu %d, min %s, max %s" % (dc, v.notna().sum(), v.min(), v.max()))
        if not bayrak: continue
        f = (pd.to_numeric(raw[bayrak[0]], errors="coerce").fillna(0) > 0)
        # her olasi esik icin: isaretli olup degeri esigin altinda kalan / isaretsiz olup ustunde kalan
        tab = pd.DataFrame({"v": v, "f": f, "s": cins if cins is not None else 0}).dropna(subset=["v"])
        for s, g in tab.groupby("s"):
            pos = g[g.f]["v"]; neg = g[~g.f]["v"]
            print("   cinsiyet=%s: isaretli en kucuk deger %s | isaretsiz en buyuk deger %s | n isaretli %d"
                  % (s, pos.min() if len(pos) else "-", neg.max() if len(neg) else "-", len(pos)))
print("\nBitti. Bu ciktiyi oldugu gibi yapistirin.")
