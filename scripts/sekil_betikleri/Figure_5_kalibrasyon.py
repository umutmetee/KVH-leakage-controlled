# -*- coding: utf-8 -*-
"""
Figure_5_kalibrasyon.py
Figure 5. Calibration of the final model on the held-out test set (logistic calibration curve with 95% bootstrap band, decile observed rates; bottom: predicted probabilities by endpoint status).
Veri: sekil_verileri.xlsx, sayfa: test_tahmin  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_5_kalibrasyon.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

import statsmodels.api as sm
from matplotlib import gridspec
TT = oku("test_tahmin"); yv = TT["y"].values; p = TT["p_model"].values

def ciz(dil):
    q = pd.qcut(p, 10, labels=False, duplicates="drop")
    xs = np.array([p[q == g].mean() for g in np.unique(q)]); ys = np.array([yv[q == g].mean() for g in np.unique(q)])
    grid = np.linspace(0.05, 0.9, 60); rng = np.random.RandomState(SEED); curves = []
    lg = np.log(p / (1 - p))
    for _ in range(500):
        i = rng.randint(0, len(yv), len(yv))
        try:
            m = sm.Logit(yv[i], sm.add_constant(lg[i])).fit(disp=0)
            curves.append(1 / (1 + np.exp(-(m.params[0] + m.params[1] * np.log(grid / (1 - grid))))))
        except Exception:
            pass
    curves = np.array(curves); m0 = sm.Logit(yv, sm.add_constant(lg)).fit(disp=0)
    fit = 1 / (1 + np.exp(-(m0.params[0] + m0.params[1] * np.log(grid / (1 - grid)))))
    fig = plt.figure(figsize=(W1, 3.9)); gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.08)
    ax = fig.add_subplot(gs[0]); hx = fig.add_subplot(gs[1], sharex=ax)
    ax.fill_between(grid, np.percentile(curves, 2.5, 0), np.percentile(curves, 97.5, 0), color=C1, alpha=0.18, lw=0,
                    label=T("Logistic calibration, 95% CI", "Lojistik kalibrasyon, %95 GA", dil))
    ax.plot(grid, fit, color=C1)
    ax.plot(xs, ys, "o", color=C2, ms=4, label=T("Deciles (observed)", "Onda birlik dilimler (gözlenen)", dil))
    ax.plot([0, 1], [0, 1], color=INK2, lw=0.8, ls="--", label=T("Ideal", "İdeal", dil))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_ylabel(T("Observed proportion", "Gözlenen oran", dil))
    citl = sm.GLM(yv, np.ones((len(yv), 1)), family=sm.families.Binomial(), offset=lg).fit().params[0]
    ax.text(0.03, 0.97, "CITL %s\n%s %s\nBrier %s" % (dec(citl, dil), T("Slope", "Eğim", dil), dec(m0.params[1], dil),
            dec(np.mean((p - yv) ** 2), dil)), va="top", fontsize=7, color=INK)
    ax.legend(loc="lower right", fontsize=6); plt.setp(ax.get_xticklabels(), visible=False)
    bins = np.linspace(0, 1, 41)
    hx.hist(p[yv == 0], bins=bins, color=C1, alpha=0.75, label=T("Endpoint negative", "Uç nokta negatif", dil))
    hx.hist(p[yv == 1], bins=bins, color=C2, alpha=0.75, label=T("Endpoint positive", "Uç nokta pozitif", dil))
    hx.set_xlabel(T("Predicted probability", "Tahmin edilen olasılık", dil)); hx.set_ylabel("n"); hx.legend(fontsize=6)
    kaydet(fig, "Figure_5", dil)

if __name__ == "__main__":
    her_dil(ciz)
