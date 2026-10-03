# -*- coding: utf-8 -*-
"""
Figure_S10_klinik_etki.py
Figure S10. Clinical impact curve on the held-out test set.
Veri: sekil_verileri.xlsx, sayfa: test_tahmin  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_S10_klinik_etki.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

TT = oku("test_tahmin"); yv = TT["y"].values; p = TT["p_model"].values

def ciz(dil):
    ths = np.round(np.arange(0.05, 0.701, 0.01), 2)
    hr = np.array([1000 * (p >= t).mean() for t in ths]); tp = np.array([1000 * ((p >= t) & (yv == 1)).mean() for t in ths])
    fig, ax = plt.subplots(figsize=(W1, 2.6))
    ax.plot(ths, hr, color=C1, label=T("Classified high risk", "Yüksek riskli sınıflanan", dil))
    ax.plot(ths, tp, color=C2, ls="--", label=T("… of whom endpoint positive", "… bunlardan uç nokta pozitif", dil))
    ax.set_xlabel(T("Threshold probability", "Eşik olasılığı", dil)); ax.set_ylabel(T("Number per 1,000 patients", "1.000 hasta başına sayı", dil))
    ax.legend(loc="upper right")
    kaydet(fig, "Figure_S10", dil)

if __name__ == "__main__":
    her_dil(ciz)
