# -*- coding: utf-8 -*-
"""
Figure_3_roc_modeller.py
Figure 3. ROC curves of logistic regression, the support vector machine, random forest and gradient boosting on the held-out test set (n = 187); AUROC in parentheses.
Veri: sekil_verileri.xlsx, sayfa: test_tahmin  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_3_roc_modeller.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

from sklearn.metrics import roc_curve, roc_auc_score
TT = oku("test_tahmin"); yv = TT["y"].values

def ciz(dil):
    fig, ax = plt.subplots(figsize=(W1, W1))
    for n, c, ls in [("Logistic Regression", C2, "-"), ("Support Vector Machine", C1, "--"), ("Random Forest", C3, "-."), ("Gradient Boosting", INK2, ":")]:
        pp = TT["p_" + n].values; fpr, tpr, _ = roc_curve(yv, pp)
        ax.plot(fpr, tpr, color=c, ls=ls, label="%s (%s)" % (MODEL_ADI(n, dil), dec(roc_auc_score(yv, pp), dil)))
    ax.plot([0, 1], [0, 1], color=GRID, lw=0.8)
    ax.set_xlabel(T("1 − specificity", "1 − özgüllük", dil)); ax.set_ylabel(T("Sensitivity", "Duyarlılık", dil))
    ax.legend(loc="lower right"); ax.set_aspect("equal")
    kaydet(fig, "Figure_3", dil)

if __name__ == "__main__":
    her_dil(ciz)
