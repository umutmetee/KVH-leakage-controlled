# -*- coding: utf-8 -*-
"""
Figure_7_ek_deger.py
Figure 7. Incremental value of the laboratory panel over the seven-variable bedside reference model on the held-out test set. (a) ROC curves. (b) Paired bootstrap distribution of the AUROC difference.
Veri: sekil_verileri.xlsx, sayfa: test_tahmin + fark_onyukleme  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_7_ek_deger.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

from sklearn.metrics import roc_curve, roc_auc_score
TT = oku("test_tahmin"); yv = TT["y"].values; p = TT["p_model"].values; pk = TT["p_referans"].values
dd = oku("fark_onyukleme")["fark"].values

def ciz(dil):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W2, 2.7))
    for pp, c, ls, lb in [(p, C1, "-", T("20-variable model", "20 değişkenli model", dil)),
                          (pk, C2, "--", T("Bedside reference (7 variables)", "Yatak başı referans (7 değişken)", dil))]:
        fpr, tpr, _ = roc_curve(yv, pp); a1.plot(fpr, tpr, color=c, ls=ls, label="%s, %s" % (lb, dec(roc_auc_score(yv, pp), dil)))
    a1.plot([0, 1], [0, 1], color=GRID, lw=0.8); a1.set_aspect("equal"); a1.legend(loc="lower right", fontsize=6)
    a1.set_xlabel(T("1 − specificity", "1 − özgüllük", dil)); a1.set_ylabel(T("Sensitivity", "Duyarlılık", dil))
    a1.set_title(T("(a) ROC curves", "(a) ROC eğrileri", dil), loc="left")
    a2.hist(dd, bins=40, color=C1, edgecolor="white")
    lo, hi = np.percentile(dd, [2.5, 97.5])
    a2.axvline(0, color=INK, lw=0.9); a2.axvline(lo, color=C2, ls="--", lw=0.9); a2.axvline(hi, color=C2, ls="--", lw=0.9)
    a2.set_xlabel(T("ΔAUROC (model − reference), paired bootstrap", "ΔAUROC (model − referans), eşleştirilmiş önyükleme", dil))
    a2.set_ylabel(T("Bootstrap replicates", "Önyükleme tekrarı", dil))
    a2.set_title(T("(b) Paired bootstrap of ΔAUROC", "(b) ΔAUROC eşleştirilmiş önyükleme", dil), loc="left")
    fark = roc_auc_score(yv, p) - roc_auc_score(yv, pk)
    a2.text(0.02, 0.97, T("Δ = %s\n95%% CI %s to %s\nP(Δ > 0) = %s", "Δ = %s\n%%95 GA %s ile %s\nP(Δ > 0) = %s", dil)
            % (dec(fark, dil).replace("-", "−"), dec(lo, dil).replace("-", "−"), dec(hi, dil).replace("-", "−"), dec((dd > 0).mean(), dil, 2)),
            transform=a2.transAxes, va="top", fontsize=7, color=INK, zorder=10,
            bbox=dict(boxstyle="square,pad=0.35", fc="white", ec=GRID, lw=0.6))
    a2.set_ylim(0, a2.get_ylim()[1] * 1.28)
    fig.tight_layout(); kaydet(fig, "Figure_7", dil)

if __name__ == "__main__":
    her_dil(ciz)
