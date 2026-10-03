# -*- coding: utf-8 -*-
"""
Figure_2_katsayi_forest.py
Figure 2. Forest plot of standardized coefficients per SD increase (exp β with 95% bootstrap percentile interval).
Veri: sekil_verileri.xlsx, sayfa: katsayilar  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_2_katsayi_forest.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

EQ = oku("katsayilar")

def ciz(dil):
    fig, ax = plt.subplots(figsize=(W1, 3.6))
    e = EQ.iloc[::-1]; yy = np.arange(len(e))
    ax.errorbar(np.exp(e["beta"]), yy, xerr=[np.exp(e["beta"]) - np.exp(e["lo"]), np.exp(e["hi"]) - np.exp(e["beta"])],
                fmt="o", ms=3.5, color=C1, ecolor=C1, elinewidth=1, capsize=2)
    ax.axvline(1, color=INK2, lw=0.8, ls="--")
    ax.set_yticks(yy); ax.set_yticklabels([ad(v, dil) for v in e["var"]]); ax.grid(axis="y", visible=False)
    ax.set_xlabel(T("exp β per 1 SD (95% bootstrap interval)", "exp β (bir SS başına, %95 önyükleme aralığı)", dil))
    kaydet(fig, "Figure_2", dil)

if __name__ == "__main__":
    her_dil(ciz)
