# -*- coding: utf-8 -*-
"""
Figure_S1_eksik_veri.py
Figure S1. Proportion of missing values for candidate variables with any missing data.
Veri: sekil_verileri.xlsx, sayfa: eksik_veri  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_S1_eksik_veri.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

E = oku("eksik_veri")

def ciz(dil):
    tum = len(E)
    mi = E[E.eksik_yuzde > 0].sort_values("eksik_yuzde", ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(W2, 2.6))
    ax.bar(range(len(mi)), mi.eksik_yuzde, color=[C2 if s else C1 for s in mi.nihai_modelde], width=0.8)
    ax.axhline(30, color=INK2, lw=0.8, ls="--")
    ax.set_xticks([]); ax.grid(axis="x", visible=False)
    ax.set_ylabel(T("Missing (%)", "Eksik (%)", dil))
    ax.set_xlabel(T("%d of %d candidate variables have missing values, sorted (orange = in final model); the remaining %d are complete",
                    "%d aday değişkenin %d tanesinde eksik değer var, sıralı (turuncu = nihai modelde); kalan %d değişken eksiksiz", dil)
                  % ((len(mi), tum, tum - len(mi)) if dil == "en" else (tum, len(mi), tum - len(mi))))
    for i, r in mi.iterrows():
        if r.nihai_modelde and r.eksik_yuzde > 30:
            ax.text(i, r.eksik_yuzde + 1.5, ad(r.degisken, dil), rotation=90, ha="center", va="bottom", fontsize=5.5)
    ax.set_ylim(0, 125); ax.set_yticks(range(0, 101, 20))
    kaydet(fig, "Figure_S1", dil)

if __name__ == "__main__":
    her_dil(ciz)
