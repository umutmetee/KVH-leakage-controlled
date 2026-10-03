# -*- coding: utf-8 -*-
"""
Figure_S2_korelasyon.py
Figure S2. Pearson correlation matrix of the 20 retained variables in the training partition (median-imputed).
Veri: sekil_verileri.xlsx, sayfa: korelasyon  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_S2_korelasyon.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

R = oku("korelasyon").set_index("Unnamed: 0")

def ciz(dil):
    k = len(R)
    fig, ax = plt.subplots(figsize=(W2 * 0.8, W2 * 0.7))
    im = ax.imshow(R.values, cmap="RdBu_r", vmin=-1, vmax=1)
    lab = [ad(v, dil) for v in R.index]
    ax.set_xticks(range(k)); ax.set_xticklabels(lab, rotation=90, fontsize=6)
    ax.set_yticks(range(k)); ax.set_yticklabels(lab, fontsize=6); ax.grid(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.04); cb.set_label(T("Pearson correlation", "Pearson korelasyon katsayısı", dil))
    kaydet(fig, "Figure_S2", dil)

if __name__ == "__main__":
    her_dil(ciz)
