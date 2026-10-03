# -*- coding: utf-8 -*-
"""
Figure_8_karar_egrisi.py
Figure 8. Decision curve analysis on the held-out test set.
Veri: sekil_verileri.xlsx, sayfa: test_tahmin  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_8_karar_egrisi.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

TT = oku("test_tahmin"); yv = TT["y"].values; p = TT["p_model"].values; pk = TT["p_referans"].values

def nb(pp, t, yy):
    yh = pp >= t
    return ((yh == 1) & (yy == 1)).mean() - ((yh == 1) & (yy == 0)).mean() * (t / (1 - t))

def ciz(dil):
    ths = np.round(np.arange(0.05, 0.701, 0.01), 2); prev = yv.mean()
    m = np.array([nb(p, t, yv) for t in ths]); r = np.array([nb(pk, t, yv) for t in ths])
    a = prev - (1 - prev) * ths / (1 - ths)
    rng = np.random.RandomState(SEED); B = []
    for _ in range(500):
        i = rng.randint(0, len(yv), len(yv)); B.append([nb(p[i], t, yv[i]) for t in ths])
    B = np.array(B)
    fig, ax = plt.subplots(figsize=(W1, 2.7))
    ax.fill_between(ths, np.percentile(B, 2.5, 0), np.percentile(B, 97.5, 0), color=C1, alpha=0.15, lw=0)
    ax.plot(ths, m, color=C1, label=T("20-variable model (95% CI)", "20 değişkenli model (%95 GA)", dil))
    ax.plot(ths, r, color=C3, ls="-.", label=T("Bedside reference model", "Yatak başı referans model", dil))
    ax.plot(ths, a, color=C2, ls="--", label=T("Treat all", "Herkesi tedavi et", dil))
    ax.axhline(0, color=INK2, lw=0.8, ls=":", label=T("Treat none", "Kimseyi tedavi etme", dil))
    ax.set_ylim(-0.1, 0.5); ax.set_xlabel(T("Threshold probability", "Eşik olasılığı", dil)); ax.set_ylabel(T("Net benefit", "Net fayda", dil))
    ax.legend(loc="upper right", fontsize=6, ncol=2)
    kaydet(fig, "Figure_8", dil)

if __name__ == "__main__":
    her_dil(ciz)
