# -*- coding: utf-8 -*-
"""
Figure_S6_yirmi_bolme.py
Figure S6. Distribution of held-out AUROC across 20 random train/test partitions.
Veri: sekil_verileri.xlsx, sayfa: yirmi_bolme + ozet  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_S6_yirmi_bolme.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

au = oku("yirmi_bolme")["auroc"].values; AUC = ozet()["auroc"]

def ciz(dil):
    fig, ax = plt.subplots(figsize=(W1, 2.4))
    ax.hist(au, bins=np.arange(0.69, 0.815, 0.0125), color=C1, edgecolor="white")
    ax.axvline(np.mean(au), color=C2, lw=1.2, label=T("Mean %s ± %s", "Ortalama %s ± %s", dil) % (dec(np.mean(au), dil), dec(np.std(au), dil)))
    ax.axvline(AUC, color=INK2, lw=1, ls="--", label=T("Primary split %s", "Birincil bölme %s", dil) % dec(AUC, dil))
    ax.set_xlabel(T("Held-out AUROC across 20 random splits", "20 rastgele bölmede ayrık test AUROC", dil))
    ax.set_ylabel(T("Count", "Sayı", dil)); ax.legend(loc="upper left")
    kaydet(fig, "Figure_S6", dil)

if __name__ == "__main__":
    her_dil(ciz)
