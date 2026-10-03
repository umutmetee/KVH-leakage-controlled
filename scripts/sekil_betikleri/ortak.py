# -*- coding: utf-8 -*-
"""
ortak.py - tum Figure_*.py betiklerinin paylastigi stil ve yardimcilar.
Veri hesaplamaz; yalnizca sekil_verileri.xlsx dosyasini okur.
"""
import os, re, sys

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
import numpy as np
import pandas as pd
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

KLASOR = os.path.dirname(os.path.abspath(__file__))
VERI_XLSX = os.path.join(KLASOR, "sekil_verileri.xlsx")
OUT = os.path.join(KLASOR, "cikti_sekil")
for s in ("en", "tr"):
    os.makedirs(os.path.join(OUT, s), exist_ok=True)

C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"     # mavi, turuncu, su yesili
INK, INK2, GRID = "#0b0b0b", "#52514e", "#d9d8d4"
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 1.4, "savefig.dpi": 600, "savefig.bbox": "tight",
    "legend.frameon": False, "pdf.fonttype": 42,
})
W1, W2 = 3.5, 7.16    # tek / cift sutun genisligi (inc)
SEED = 42


def oku(sayfa):
    """sekil_verileri.xlsx icinden bir sayfayi okur."""
    if not os.path.exists(VERI_XLSX):
        sys.exit("HATA: %s yok. Once 00_sekil_verisi_uret.py calistirin." % VERI_XLSX)
    return pd.read_excel(VERI_XLSX, sheet_name=sayfa)


def ozet():
    """'ozet' sayfasini {ad: deger} sozlugu olarak dondurur."""
    o = oku("ozet")
    return dict(zip(o["ad"], o["deger"]))


def _virgul(fig):
    """Turkce figurlerde sayisal eksen etiketlerinde ondalik ayiraci virgul yapar."""
    from matplotlib.ticker import ScalarFormatter, FuncFormatter
    fig.canvas.draw()
    for ax in fig.get_axes():
        for eksen in (ax.xaxis, ax.yaxis):
            if not isinstance(eksen.get_major_formatter(), ScalarFormatter):
                continue
            yazilar = [t.get_text().replace("\u2212", "-") for t in eksen.get_ticklabels()]
            if not any(y.strip() for y in yazilar):
                continue          # gizli etiketli (paylasilan) eksen; digeri isler
            n = max([len(y.split(".")[1]) for y in yazilar if "." in y] or [0])
            eksen.set_major_formatter(FuncFormatter(lambda v, pos, n=n: ("%.*f" % (n, v)).replace(".", ",").replace("-", "\u2212")))


def kaydet(fig, ad, dil):
    if dil == "tr":
        _virgul(fig)
    for uz in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, dil, ad + "." + uz))
    plt.close(fig)
    print("   yazildi: cikti_sekil/%s/%s.png" % (dil, ad))


def dec(x, dil, n=3):
    s = ("%." + str(n) + "f") % x
    return s.replace(".", ",") if dil == "tr" else s


T = lambda en, tr, dil: en if dil == "en" else tr


def her_dil(fn):
    """Sekli once Ingilizce (makale), sonra Turkce (tez) cizer."""
    for dil in ("en", "tr"):
        fn(dil)

# Degisken adlari (EN / TR)
AD = {
 "ESK_tGFR CKD-EPİ": ("eGFR (CKD-EPI, earlier)", "eGFR (CKD-EPI, önc.)"),
 "YEN_tGFR CKD-EPİ": ("eGFR (CKD-EPI, latest)", "eGFR (CKD-EPI, gün.)"),
 "YAŞ": ("Age", "Yaş"),
 "ESK_Üre": ("Urea (earlier)", "Üre (önc.)"), "YEN_Üre": ("Urea (latest)", "Üre (gün.)"),
 "ESK_LYM%": ("Lymphocyte % (earlier)", "Lenfosit % (önc.)"), "YEN_LYM%": ("Lymphocyte % (latest)", "Lenfosit % (gün.)"),
 "ESK_HDL Kolesterol": ("HDL cholesterol (earlier)", "HDL kolesterol (önc.)"),
 "YEN_HDL Kolesterol": ("HDL cholesterol (latest)", "HDL kolesterol (gün.)"),
 "YEN_Kolesterol": ("Total cholesterol (latest)", "Total kolesterol (gün.)"),
 "ESK_RDW": ("RDW (earlier)", "RDW (önc.)"),
 "YEN_Ürik Asit": ("Uric acid (latest)", "Ürik asit (gün.)"), "ESK_Ürik Asit": ("Uric acid (earlier)", "Ürik asit (önc.)"),
 "YEN_PLT": ("Platelet count (latest)", "Trombosit (gün.)"), "ESK_PLT": ("Platelet count (earlier)", "Trombosit (önc.)"),
 "ESK_Kalsiyum (Ca)": ("Calcium (earlier)", "Kalsiyum (önc.)"),
 "diyabet süresi": ("Diabetes duration", "Diyabet süresi"),
 "ESK_PCT": ("Plateletcrit (earlier)", "Plateletkrit (önc.)"),
 "ESK_Tokluk Kan Şekeri (TKŞ)": ("Postprandial glucose (earlier)", "Tokluk glukoz (önc.)"),
 "YEN_Glukoz": ("Glucose (latest)", "Glukoz (gün.)"), "ESK_Glukoz": ("Glucose (earlier)", "Glukoz (önc.)"),
 "ESK_HBA1C (%)": ("HbA1c % (earlier)", "HbA1c % (önc.)"),
 "ESK_CRP": ("CRP (earlier)", "CRP (önc.)"),
 "YEN_P-LCR": ("P-LCR (latest)", "P-LCR (gün.)"),
 "ESK_Albumin": ("Albumin (earlier)", "Albumin (önc.)"),
 "ESK_NEU#": ("Neutrophil count (earlier)", "Nötrofil sayısı (önc.)"),
 "ESK_HGB": ("Haemoglobin (earlier)", "Hemoglobin (önc.)"),
 "YEN_MCHC": ("MCHC (latest)", "MCHC (gün.)"), "ESK_LYM#": ("Lymphocyte count (earlier)", "Lenfosit sayısı (önc.)"),
 "ESK_NEU%": ("Neutrophil % (earlier)", "Nötrofil % (önc.)"), "ESK_NLR": ("NLR (earlier)", "NLR (önc.)"),
}
def ad(c, dil):
    if c in AD: return AD[c][0 if dil == "en" else 1]
    s = re.sub(r"^(ESK_|YEN_)\s*", "", str(c)).strip()
    if dil == "en":
        return s + (" (earlier)" if str(c).startswith("ESK_") else " (latest)" if str(c).startswith("YEN_") else "")
    return s + (" (önc.)" if str(c).startswith("ESK_") else " (gün.)" if str(c).startswith("YEN_") else "")

MODEL_TR = {"Stacking": "Yığılmış topluluk", "Support Vector Machine": "Destek vektör makinesi",
            "Logistic Regression": "Lojistik regresyon", "Extra Trees": "Ekstra ağaçlar",
            "Soft Voting": "Yumuşak oylama", "Random Forest": "Rastgele orman", "Naive Bayes": "Naive Bayes",
            "Hist. Gradient Boosting": "Histogram grad. artırma", "AdaBoost": "AdaBoost",
            "Gradient Boosting": "Gradyan artırma", "K-Nearest Neighbours": "K-en yakın komşu",
            "Multilayer Perceptron": "Çok katmanlı algılayıcı", "Decision Tree": "Karar ağacı"}

def ad(c, dil):
    if c in AD: return AD[c][0 if dil == "en" else 1]
    s = re.sub(r"^(ESK_|YEN_)\s*", "", str(c)).strip()
    if dil == "en":
        return s + (" (earlier)" if str(c).startswith("ESK_") else " (latest)" if str(c).startswith("YEN_") else "")
    return s + (" (önc.)" if str(c).startswith("ESK_") else " (gün.)" if str(c).startswith("YEN_") else "")


MODEL_ADI = lambda n, dil: n if dil == "en" else MODEL_TR.get(n, n)
