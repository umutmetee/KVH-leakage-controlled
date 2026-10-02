# -*- coding: utf-8 -*-
"""
Figure_S4_model_auroc.py
Figure S4. Held-out test AUROC by model (error bars = 95% bootstrap CI).
Veri: sekil_verileri.xlsx, sayfa: modeller_auroc  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_S4_model_auroc.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

MR = oku("modeller_auroc").sort_values("auc", ascending=True).reset_index(drop=True)

def ciz(dil):
    fig, ax = plt.subplots(figsize=(W1, 3.0))
    yy = np.arange(len(MR))
    ax.barh(yy, MR["auc"] - 0.5, left=0.5, color=[C2 if n == "Logistic Regression" else C1 for n in MR["model"]], height=0.6)
    ok = MR["lo"].notna().values
    ax.errorbar(MR["auc"][ok], yy[ok], xerr=[(MR["auc"] - MR["lo"])[ok], (MR["hi"] - MR["auc"])[ok]],
                fmt="none", ecolor=INK2, elinewidth=0.8, capsize=2)
    ax.set_yticks(yy); ax.set_yticklabels([MODEL_ADI(n, dil) for n in MR["model"]])
    ax.set_xlim(0.5, 0.9); ax.grid(axis="y", visible=False)
    ax.set_xlabel(T("Held-out test AUROC (95% bootstrap CI)", "Ayrık test AUROC (%95 önyükleme GA)", dil))
    kaydet(fig, "Figure_S4", dil)

if __name__ == "__main__":
    her_dil(ciz)
