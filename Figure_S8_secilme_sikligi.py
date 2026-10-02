# -*- coding: utf-8 -*-
"""
Figure_S8_secilme_sikligi.py
Figure S8. Selection frequency across 20 random partitions (variables selected in at least 10, plus all final-model variables).
Veri: sekil_verileri.xlsx, sayfa: secilme_sikligi  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_S8_secilme_sikligi.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

FS = oku("secilme_sikligi")

def ciz(dil):
    f = FS[(FS.sayi >= 10) | FS.nihai_modelde].sort_values("sayi", ascending=True, kind="mergesort").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(W1, 0.155 * len(f) + 0.9))
    yy = np.arange(len(f))
    ax.barh(yy, f.sayi, color=[C1 if s else GRID for s in f.nihai_modelde], height=0.62)
    for i, v in enumerate(f.sayi):
        ax.text(v + 0.25, i, "%d" % v, va="center", fontsize=5.5, color=INK2)
    ax.set_yticks(yy); ax.set_yticklabels([ad(v, dil) for v in f.degisken])
    ax.set_xlim(0, 21.5); ax.set_xticks(range(0, 21, 5)); ax.grid(axis="y", visible=False)
    ax.set_xlabel(T("Times selected in 20 random splits", "20 bölmede seçilme sayısı", dil))
    ax.text(21.3, 0, T("blue = in final model\ngrey = not in final model", "mavi = nihai modelde\ngri = nihai modelde yok", dil),
            ha="right", va="bottom", fontsize=6, color=INK2)
    kaydet(fig, "Figure_S8", dil)

if __name__ == "__main__":
    her_dil(ciz)
