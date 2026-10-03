# -*- coding: utf-8 -*-
"""
Figure_6_nomogram.py
Figure 6. Nomogram of the final 20-variable model (predictor axes span the 1st–99th percentile of observed values).
Veri: sekil_verileri.xlsx, sayfa: nomogram  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_6_nomogram.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

NOM = oku("nomogram"); o = ozet(); b0 = o["kesisim_b0"]

def ciz(dil):
    rows = []
    for _, r in NOM.iterrows():
        c_lo = r.beta * (r.p01 - r.ortalama) / r.ss; c_hi = r.beta * (r.p99 - r.ortalama) / r.ss
        rows.append((r.degisken, r.p01, r.p99, c_lo, c_hi, r.beta, r.ortalama, r.ss))
    rng_max = max(abs(r[4] - r[3]) for r in rows); pts = lambda c, cmin: 100 * (c - cmin) / rng_max
    fig, ax = plt.subplots(figsize=(W2, 7.2)); ax.axis("off")
    n = len(rows) + 3; yy = n
    ax.plot([0, 100], [yy, yy], color=INK, lw=0.8)
    for t_ in range(0, 101, 10):
        ax.plot([t_, t_], [yy, yy + 0.15], color=INK, lw=0.6); ax.text(t_, yy + 0.3, str(t_), ha="center", fontsize=6)
    ax.text(-2, yy, T("Points", "Puan", dil), ha="right", va="center", fontsize=7, weight="bold")
    cmins = []
    for k_, (v, lo, hi, c_lo, c_hi, be, mu, sd) in enumerate(rows):
        yy = n - 1 - k_; cmin = min(c_lo, c_hi); cmins.append(cmin)
        x0, x1 = pts(c_lo, cmin), pts(c_hi, cmin)
        ax.plot([min(x0, x1), max(x0, x1)], [yy, yy], color=C1, lw=1.2)
        uz = abs(x1 - x0); nt = 4 if uz >= 30 else (3 if uz >= 14 else 2)
        for val in np.linspace(lo, hi, nt):
            xp = pts(be * (val - mu) / sd, cmin)
            ax.plot([xp, xp], [yy, yy + 0.12], color=C1, lw=0.6)
            ax.text(xp, yy + 0.22, ("%.3g" % val).replace(".", ",") if dil == "tr" else "%.3g" % val, ha="center", fontsize=5.2, color=INK2)
        ax.text(-2, yy, ad(v, dil), ha="right", va="center", fontsize=6.5)
    tot_max = sum(abs(r[4] - r[3]) for r in rows) * 100 / rng_max
    lp_min = b0 + sum(cmins)
    yy = 1.2
    ax.plot([0, 100], [yy, yy], color=INK, lw=0.8)
    for t_ in np.linspace(0, tot_max, 11):
        xp = 100 * t_ / tot_max; ax.plot([xp, xp], [yy, yy + 0.15], color=INK, lw=0.6); ax.text(xp, yy + 0.3, "%d" % t_, ha="center", fontsize=6)
    ax.text(-2, yy, T("Total points", "Toplam puan", dil), ha="right", va="center", fontsize=7, weight="bold")
    yy = 0.2; ax.plot([0, 100], [yy, yy], color=INK, lw=0.8)
    for kk, pr_ in enumerate([0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]):
        tpts = (np.log(pr_ / (1 - pr_)) - lp_min) * 100 / rng_max
        if 0 <= tpts <= tot_max:
            xp = 100 * tpts / tot_max; ax.plot([xp, xp], [yy, yy + 0.15], color=C2, lw=0.8)
            ax.text(xp, yy - (0.35 if kk % 2 == 0 else 0.7), dec(pr_, dil, 2), ha="center", fontsize=6, color=C2)
    ax.text(-2, yy, T("Probability", "Olasılık", dil), ha="right", va="center", fontsize=7, weight="bold")
    ax.set_xlim(-45, 104); ax.set_ylim(-1.0, n + 0.8)
    kaydet(fig, "Figure_6", dil)

if __name__ == "__main__":
    her_dil(ciz)
