# -*- coding: utf-8 -*-
"""
Figure_S5_karisiklik_matrisi.py
Figure S5. Confusion matrix on the held-out test set at the training-derived Youden threshold.
Veri: sekil_verileri.xlsx, sayfa: test_tahmin + ozet  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_S5_karisiklik_matrisi.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

from sklearn.metrics import confusion_matrix
TT = oku("test_tahmin"); yv = TT["y"].values; p = TT["p_model"].values; TAU = ozet()["tau"]

def ciz(dil):
    tn, fp, fn, tp = confusion_matrix(yv, (p >= TAU).astype(int)).ravel()
    M = np.array([[tn, fp], [fn, tp]])
    fig, ax = plt.subplots(figsize=(W1 * 0.85, W1 * 0.75))
    ax.imshow(M, cmap="Blues", vmin=0, vmax=M.max() * 1.3); ax.grid(False)
    lab = [[T("TN", "GN", dil), T("FP", "YP", dil)], [T("FN", "YN", dil), T("TP", "GP", dil)]]
    for i in range(2):
        for j in range(2):
            ax.text(j, i, "%s = %d" % (lab[i][j], M[i, j]), ha="center", va="center", fontsize=9, color=INK)
    ax.set_xticks([0, 1]); ax.set_xticklabels([T("Predicted negative", "Tahmin: negatif", dil), T("Predicted positive", "Tahmin: pozitif", dil)])
    ax.set_yticks([0, 1]); ax.set_yticklabels([T("Observed negative", "Gerçek: negatif", dil), T("Observed positive", "Gerçek: pozitif", dil)])
    ax.set_title("τ = %s" % dec(TAU, dil))
    kaydet(fig, "Figure_S5", dil)

if __name__ == "__main__":
    her_dil(ciz)
