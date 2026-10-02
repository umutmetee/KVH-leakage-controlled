# -*- coding: utf-8 -*-
"""
Figure_S11_uc_nokta_kesisim.py
Figure S11. Overlap of the five endpoint criteria among positive patients (12 most frequent combinations).
Veri: sekil_verileri.xlsx, sayfa: uc_nokta_kesisim + ozet  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_S11_uc_nokta_kesisim.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

from matplotlib import gridspec
KES = oku("uc_nokta_kesisim"); o = ozet()
ADLAR = ["LA", "LVEDD", "EF<50%", "QTc", "QRS"]
NKR = {"LA": o["n_uc_nokta_LA"], "LVEDD": o["n_uc_nokta_LVEDD"], "EF<50%": o["n_uc_nokta_EF"],
       "QTc": o["n_uc_nokta_QTc"], "QRS": o["n_uc_nokta_QRS"]}

def ciz(dil):
    top = KES.sort_values("n", ascending=False).head(12).reset_index(drop=True)
    fig = plt.figure(figsize=(W2 * 0.8, 3.2)); gs = gridspec.GridSpec(2, 1, height_ratios=[2, 1.1], hspace=0.05)
    a = fig.add_subplot(gs[0]); b = fig.add_subplot(gs[1], sharex=a); xs = np.arange(len(top))
    a.bar(xs, top.n, color=C1, width=0.6)
    for x_, v in zip(xs, top.n): a.text(x_, v + 1, str(v), ha="center", fontsize=6.5)
    a.set_ylabel(T("Patients", "Hasta", dil)); a.grid(axis="x", visible=False); plt.setp(a.get_xticklabels(), visible=False)
    for x_, (_, r) in zip(xs, top.iterrows()):
        on = [i for i, k in enumerate(ADLAR) if r[k] == 1]
        b.scatter([x_] * len(ADLAR), range(len(ADLAR)), color=GRID, s=18, zorder=2)
        b.scatter([x_] * len(on), on, color=INK, s=18, zorder=3)
        if len(on) > 1: b.plot([x_, x_], [min(on), max(on)], color=INK, lw=1)
    b.set_yticks(range(len(ADLAR))); b.set_yticklabels(["%s (n=%d)" % (k, NKR[k]) for k in ADLAR])
    b.set_xticks([]); b.grid(False); b.invert_yaxis()
    npoz = int(KES.n.sum())
    b.set_xlabel(T("Twelve most frequent intersections shown (%d of %d endpoint-positive patients);\nthe remaining %d fall in smaller intersections",
                   "En sık görülen on iki kesişim gösterilmiştir (%d / %d uç nokta pozitif hasta);\nkalan %d hasta daha küçük kesişimlerde",
                   dil) % (top.n.sum(), npoz, npoz - top.n.sum()), fontsize=7)
    kaydet(fig, "Figure_S11", dil)

if __name__ == "__main__":
    her_dil(ciz)
