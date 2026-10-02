# -*- coding: utf-8 -*-
"""
Figure_1_akis_semasi.py
Figure 1. Cohort selection, train/test partitioning, and modeling pipeline overview.
Veri: sekil_verileri.xlsx, sayfa: ozet  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_1_akis_semasi.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

o = ozet()
from matplotlib.patches import FancyBboxPatch

def ciz(dil):
    kutular = [
        T("Routine endocrinology records\n(laboratory draws 2019–2024)", "Rutin endokrinoloji kayıtları\n(laboratuvar ölçümleri 2019–2024)", dil),
        T("Eligible cohort: n = %d\n(adults, laboratory panel + cardiac work-up)", "Uygun kohort: n = %d\n(erişkin, laboratuvar paneli + kardiyak değerlendirme)", dil) % o["n_hasta"],
        T("Endpoint from ECG / echo\nLA · LVEDD · EF<50%% · QTc · QRS\n%d positive (%s%%)", "EKG / EKO'dan uç nokta\nLA · LVEDD · EF<%%50 · QTc · QRS\n%d pozitif (%%%s)", dil)
            % (o["n_olay"], dec(100 * o["n_olay"] / o["n_hasta"], dil, 1)),
        T("Whitelist: %d candidates\n(all outcome-defining fields removed)", "Beyaz liste: %d aday\n(sonucu tanımlayan tüm alanlar çıkarıldı)", dil) % o["n_aday_degisken"],
        T("Stratified 80/20 split\ntrain %d (%d ev.) · test %d (%d ev.)", "Tabakalı 80/20 bölme\neğitim %d (%d olay) · test %d (%d olay)", dil)
            % (o["n_egitim"], o["olay_egitim"], o["n_test"], o["olay_test"]),
        T("Training fold only:\nANOVA F + analyte-family dedup → k = 20", "Yalnızca eğitim bölümü:\nANOVA F + analit ailesi tekilleştirme → k = 20", dil),
        T("Logistic regression (C = 0.01)\nmedian impute → standardize → fit", "Lojistik regresyon (C = 0,01)\nmedyan atama → standartlaştırma → uydurma", dil),
    ]
    n = len(kutular); h, ara = 0.92, 0.38
    fig, ax = plt.subplots(figsize=(W1, n * (h + ara) * 0.62)); ax.axis("off"); ax.grid(False)
    ust = n * (h + ara)
    for i, t in enumerate(kutular):
        yb = ust - (i + 1) * (h + ara) + ara
        ax.add_patch(FancyBboxPatch((0.03, yb), 0.94, h, boxstyle="round,pad=0.01,rounding_size=0.06",
                                    fc="#f1f1f1", ec=INK2, lw=1.1))
        ax.text(0.5, yb + h / 2, t, ha="center", va="center", fontsize=7.5, color=INK, linespacing=1.25)
        if i < n - 1:
            ax.annotate("", xy=(0.5, yb - ara + 0.04), xytext=(0.5, yb - 0.02),
                        arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.1, mutation_scale=9))
    ax.set_xlim(0, 1); ax.set_ylim(0, ust)
    kaydet(fig, "Figure_1", dil)

if __name__ == "__main__":
    her_dil(ciz)
