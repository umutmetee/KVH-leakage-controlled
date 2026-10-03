# -*- coding: utf-8 -*-
"""
Figure_4_k_secimi.py
Figure 4. Choice of the feature budget k. (a) Cross-validated AUROC with feature selection repeated inside each fold (mean ± 1 SD). (b) Events per variable in the training partition.
Veri: sekil_verileri.xlsx, sayfa: k_taramasi  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_4_k_secimi.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

KR = oku("k_taramasi")

def ciz(dil):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W2, 2.3))
    a1.axvline(20, color=C2, lw=0.8, ls="--", zorder=0)
    a1.errorbar(KR["k"], KR["cv"], yerr=KR["sd"], fmt="o-", color=C1, capsize=2, ms=4, zorder=3)
    a1.set_xlabel(T("Number of retained features (k)", "Korunan öznitelik sayısı (k)", dil))
    a1.set_ylabel(T("CV-AUROC, selection inside folds (±1 SD)", "Kat içi seçimli ÇD-AUROC (±1 SS)", dil))
    a1.set_title(T("(a) Discrimination", "(a) Ayırt edicilik", dil), loc="left")
    a2.axhline(10, color=INK2, lw=0.8, ls=":", zorder=0); a2.axvline(20, color=C2, lw=0.8, ls="--", zorder=0)
    a2.plot(KR["k"], KR["epv"], "s-", color=C1, ms=4, zorder=3)
    a2.text(KR["k"].max(), 10.4, "EPV = 10", ha="right", va="bottom", color=INK2, fontsize=7)
    a2.set_xlabel(T("Number of retained features (k)", "Korunan öznitelik sayısı (k)", dil))
    a2.set_ylabel(T("Events per variable (training)", "Değişken başına olay (eğitim)", dil))
    a2.set_title(T("(b) Sample-size safety", "(b) Örneklem güvenliği", dil), loc="left")
    fig.tight_layout()
    kaydet(fig, "Figure_4", dil)

if __name__ == "__main__":
    her_dil(ciz)
