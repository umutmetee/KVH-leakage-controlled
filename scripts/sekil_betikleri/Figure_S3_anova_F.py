# -*- coding: utf-8 -*-
"""
Figure_S3_anova_F.py
Figure S3. Univariate ANOVA F-statistic of the 20 retained features (training partition only).
Veri: sekil_verileri.xlsx, sayfa: katsayilar  (once 00_sekil_verisi_uret.py)
KULLANIM:  py Figure_S3_anova_F.py
Cikti: cikti_sekil/en/ (makale) ve cikti_sekil/tr/ (tez), PNG 600 dpi + PDF
"""
from ortak import *

EQ = oku("katsayilar")

def ciz(dil):
    fig, ax = plt.subplots(figsize=(W1, 3.4))
    e = EQ.iloc[::-1]
    ax.barh([ad(v, dil) for v in e["var"]], e["F"], color=C1, height=0.62)
    ax.set_xlabel(T("Univariate ANOVA F-statistic (training partition)", "Tek değişkenli ANOVA F-istatistiği (eğitim bölümü)", dil))
    ax.grid(axis="y", visible=False)
    kaydet(fig, "Figure_S3", dil)

if __name__ == "__main__":
    her_dil(ciz)
