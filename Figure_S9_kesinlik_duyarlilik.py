# -*- coding: utf-8 -*-
"""
Figure_S9_kesinlik_duyarlilik.py
Figure S9. Precision–recall curve on the held-out test set; dashed line, prevalence.
Veri: sekil_verileri.xlsx, sayfa: test_tahmin  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_S9_kesinlik_duyarlilik.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

from sklearn.metrics import precision_recall_curve, average_precision_score
TT = oku("test_tahmin"); yv = TT["y"].values; p = TT["p_model"].values

def ciz(dil):
    pr, rc, _ = precision_recall_curve(yv, p)
    fig, ax = plt.subplots(figsize=(W1, 2.6))
    ax.plot(rc, pr, color=C1, label="AUPRC %s" % dec(average_precision_score(yv, p), dil), drawstyle="steps-post")
    ax.axhline(yv.mean(), color=INK2, lw=0.8, ls="--", label=T("Prevalence %s", "Prevalans %s", dil) % dec(yv.mean(), dil))
    ax.set_xlabel(T("Recall (sensitivity)", "Duyarlılık", dil)); ax.set_ylabel(T("Precision (PPV)", "Kesinlik", dil))
    ax.set_ylim(0.3, 1.02); ax.legend(loc="upper right")
    kaydet(fig, "Figure_S9", dil)

if __name__ == "__main__":
    her_dil(ciz)
