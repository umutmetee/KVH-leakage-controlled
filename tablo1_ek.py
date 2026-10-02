# -*- coding: utf-8 -*-
"""
tablo1_ek.py  -  hakem m8 (BMI'yi boy-kilodan turet) ve m9 (carpik degiskenler icin medyan [IQR])
KULLANIM:  py tablo1_ek.py      (ciktiyi oldugu gibi Claude'a yapistirin)
"""
from model_ortak import *
from scipy.stats import mannwhitneyu, ttest_ind
yy = y.values
def ozet_medyan(s):
    s = pd.to_numeric(s, errors="coerce")
    f = lambda v: "%.1f [%.1f-%.1f]" % (np.nanmedian(v), np.nanpercentile(v, 25), np.nanpercentile(v, 75))
    p = mannwhitneyu(s[yy == 0].dropna(), s[yy == 1].dropna()).pvalue
    return "%s | %s | %s | p=%.3g | eksik %.1f%%" % (f(s), f(s[yy == 0]), f(s[yy == 1]), p, 100 * s.isna().mean())
def ozet_ort(s):
    s = pd.to_numeric(s, errors="coerce")
    f = lambda v: "%.1f +- %.1f" % (np.nanmean(v), np.nanstd(v, ddof=1))
    p = ttest_ind(s[yy == 0].dropna(), s[yy == 1].dropna()).pvalue
    return "%s | %s | %s | p=%.3g | eksik %.1f%%" % (f(s), f(s[yy == 0]), f(s[yy == 1]), p, 100 * s.isna().mean())
P("")
P("m9  (tum | olay- | olay+ | Mann-Whitney p | eksik)")
P("   Diyabet suresi, yil, medyan [IQR]: " + ozet_medyan(X["diyabet süresi"]))
for c in ["YAŞ", "sistolık kan basıncı", "diastolik kan basıncı", "boy", "kılo", "bmı"]:
    if c in X.columns: P("   %-22s medyan [IQR]: %s" % (c, ozet_medyan(X[c])))
# m8
boy = pd.to_numeric(X["boy"], errors="coerce"); kilo = pd.to_numeric(X["kılo"], errors="coerce")
bmi0 = pd.to_numeric(X["bmı"], errors="coerce")
bmi_h = kilo / (boy / 100) ** 2
bmi_h = bmi_h.where((boy > 120) & (boy < 220) & (kilo > 30) & (kilo < 250))
P("")
P("m8  BMI")
P("   kayitli BMI eksik: %d (%.1f%%)" % (bmi0.isna().sum(), 100 * bmi0.isna().mean()))
ikisi = bmi0.notna() & bmi_h.notna()
P("   kayitli ile hesaplanan uyumu (ikisi de var, n=%d): ort. fark %.2f, |fark|>1 olan %d" % (ikisi.sum(), (bmi0 - bmi_h)[ikisi].mean(), ((bmi0 - bmi_h).abs() > 1)[ikisi].sum()))
bmi1 = bmi0.fillna(bmi_h)
P("   tamamlanmis BMI eksik: %d (%.1f%%)" % (bmi1.isna().sum(), 100 * bmi1.isna().mean()))
P("   Tablo 1 satiri (ort +- SS): " + ozet_ort(bmi1))
P("   (eski, yalniz kayitli): " + ozet_ort(bmi0))
X2 = X.copy(); X2["bmı"] = bmi1
pk0 = boru().fit(Xtr[KLINIK], ytr).predict_proba(Xte[KLINIK])[:, 1]
pk1 = boru().fit(X2.iloc[tr][KLINIK], ytr).predict_proba(X2.iloc[te][KLINIK])[:, 1]
P("   yatak basi model: kayitli BMI %.3f | tamamlanmis BMI %.3f (%.3f-%.3f)" % ((roc_auc_score(yv, pk0), roc_auc_score(yv, pk1)) + tuple(boot_ci(yv, pk1, 1))))
P("   20 degiskenli modelden fark (tamamlanmis BMI ile): %+.3f" % (AUC - roc_auc_score(yv, pk1)))
P("")
P("BITTI.")
