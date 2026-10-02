# -*- coding: utf-8 -*-
"""
Figure_S7_ogrenme_egrisi.py
Figure S7. Learning curves for the final logistic regression model (5-fold CV on the training partition; bands, ±1 SD).
Veri: sekil_verileri.xlsx, sayfa: ogrenme_egrisi  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_S7_ogrenme_egrisi.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

L = oku("ogrenme_egrisi")

def ciz(dil):
    fig, ax = plt.subplots(figsize=(W1, 2.5))
    for k, c, mk, lb in [("egitim", C1, "o", T("Training", "Eğitim", dil)), ("cd", C2, "s", T("Cross-validation", "Çapraz doğrulama", dil))]:
        m, s = L[k + "_ort"], L[k + "_ss"]
        ax.plot(L["egitim_n"], m, marker=mk, color=c, ms=3.5, label=lb)
        ax.fill_between(L["egitim_n"], m - s, m + s, color=c, alpha=0.15, lw=0)
    ax.set_xlabel(T("Training-set size", "Eğitim kümesi büyüklüğü", dil)); ax.set_ylabel("AUROC"); ax.legend()
    kaydet(fig, "Figure_S7", dil)

if __name__ == "__main__":
    her_dil(ciz)
