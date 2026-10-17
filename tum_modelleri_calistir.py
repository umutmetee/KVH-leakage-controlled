# -*- coding: utf-8 -*-
"""tum_modelleri_calistir.py - Model_*.py betiklerini sirayla calistirir (once makale 1-5, sonra ek S1-S9).
KULLANIM:  py tum_modelleri_calistir.py"""
import os, re, sys, glob, subprocess
K = os.path.dirname(os.path.abspath(__file__))
sira = lambda f: (1 if re.match(r"Model_S", os.path.basename(f)) else 0, int(re.findall(r"Model_S?(\d+)", os.path.basename(f))[0]))
py = "py" if sys.platform.startswith("win") else sys.executable
dosyalar = [f for f in glob.glob(os.path.join(K, "Model_*.py")) if re.match(r"Model_S?\d+_", os.path.basename(f))]  # Windows buyuk/kucuk harf ayirmaz: model_ortak.py elenir
for f in sorted(dosyalar, key=sira):
    print("=" * 70); print(os.path.basename(f)); sys.stdout.flush()
    r = subprocess.call([py, f], cwd=K)
    if r: print("HATA: %s (kod %d)" % (os.path.basename(f), r))
print("Bitti. Sonuclar: model_sonuclari.xlsx (sayfa 'ozet')")
