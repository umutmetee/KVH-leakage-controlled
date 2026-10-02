# -*- coding: utf-8 -*-
"""
Figure_9_duyarlilik_forest.py
Figure 9. AUROC (95% bootstrap CI) across sensitivity analyses.
Veri: sekil_verileri.xlsx, sayfa: duyarlilik  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_9_duyarlilik_forest.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

SR = oku("duyarlilik"); o = ozet()

def ciz(dil):
    s = SR.iloc[::-1].reset_index(drop=True); yy = np.arange(len(s))
    fig, ax = plt.subplots(figsize=(W2 * 0.75, 3.25))
    for i, r in s.iterrows():
        ic = r.en.startswith("Selection-inclusive")   # egitim onyuklemesi, ayrik test degil
        c = C2 if r.grup == 0 and i == len(s) - 1 else (INK2 if r.grup == 3 else (C3 if ic else C1))
        ax.errorbar(r.auc, i, xerr=[[r.auc - r.lo], [r.hi - r.auc]], fmt="o", color=c, ecolor=c, ms=4, capsize=2, elinewidth=1,
                    mfc="white" if ic else c)
        ax.text(0.905, i, "%s (%s–%s)" % (dec(r.auc, dil), dec(r.lo, dil), dec(r.hi, dil)), va="center", fontsize=6.5, color=INK)
    ax.axvline(o["auroc"], color=C2, lw=0.8, ls="--")
    ax.set_yticks(yy); ax.set_yticklabels(s[dil]); ax.set_xlim(0.55, 0.9); ax.grid(axis="y", visible=False)
    ax.set_xlabel(T("AUROC (95% bootstrap CI)", "AUROC (%95 önyükleme GA)", dil))
    kaydet(fig, "Figure_9", dil)

if __name__ == "__main__":
    her_dil(ciz)
