# -*- coding: utf-8 -*-
"""tum_sekilleri_ciz.py - tum Figure_*.py betiklerini sirayla calistirir.
KULLANIM:  py tum_sekilleri_ciz.py      (once: py 00_sekil_verisi_uret.py)"""
import glob, os, runpy, sys

def _py_kontrol():
    """VS Code calistir dugmesi sklearn'suz bir Python acarsa betigi 'py' ile yeniden baslatir."""
    import os, sys, shutil, subprocess
    try:
        import sklearn, statsmodels  # noqa: F401
        return
    except ImportError:
        pass
    if os.environ.get("KVH_YENIDEN") != "1" and shutil.which("py"):
        print("Bu Python'da sklearn/statsmodels yok (%s); 'py' ile yeniden calistiriliyor..." % sys.executable)
        env = dict(os.environ, KVH_YENIDEN="1")
        sys.exit(subprocess.call(["py", os.path.abspath(sys.argv[0])] + sys.argv[1:], env=env))
    sys.exit("HATA: sklearn/statsmodels bulunamadi. Terminalde 'py <dosya>.py' ile calistirin.")
_py_kontrol()
KL = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, KL)
hata = 0
for f in sorted(glob.glob(os.path.join(KL, "Figure_*.py")), key=lambda s: (("_S" in os.path.basename(s)), int("".join(c for c in os.path.basename(s).split("_")[1] if c.isdigit())))):
    print(os.path.basename(f))
    try:
        runpy.run_path(f, run_name="__main__")
    except Exception as e:
        hata += 1; print("   HATA:", e)
print("Bitti. Hata sayisi: %d" % hata)
