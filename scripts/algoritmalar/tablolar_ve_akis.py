# -*- coding: utf-8 -*-
"""
tablolar_ve_akis.py  -  Makaledeki hasta akisi (931 / 371 / 127 / 744 / 187),
Tablo 1 (demografi), Tablo 2 (secilen 20 degisken), Tablo 4 (k taramasi), Tablo 5 (denklem),
egitim/test karsilastirmasi, uc nokta bilesen ortusmesi ve tum adaylarin eksiklik tablosunu VERIDEN uretir.
KULLANIM:  py tablolar_ve_akis.py
Cikti: ekranda ozet + tablolar_cikti.xlsx (sayfalar: akis, dislanan_sutunlar, uc_nokta, uc_nokta_ortusme,
       tablo1, tablo1_egitim_test, tablo2, tablo4, tablo5, eksiklik_tum_adaylar)
Hasta adi / numarasi yazilmaz.
"""
from model_ortak import *
from scipy import stats
yy = y.values
OUT = os.path.join(KLASOR, "tablolar_cikti.xlsx")

# ---------------- 1) AKIS ----------------
d0 = pd.read_excel(VERI); r0 = pd.read_excel(RAW)
aday_ham = [c for c in d0.columns if str(c).startswith(("ESK_", "YEN_"))] + [c for c in STATIK if c in d0.columns]
bos = [c for c in aday_ham if pd.to_numeric(d0[c], errors="coerce").isna().all()]
dis = [c for c in r0.columns if c not in d0.columns]
akis = [
 ("Ham veri cekimi (aiveri2026_haz.xlsx): hasta", r0.shape[0]),
 ("Ham veri cekimi: sutun (degisken) sayisi", r0.shape[1]),
 ("Sizintisiz veri (sizintisiz_veri.xlsx): sutun", d0.shape[1]),
 ("Ham veriden dislanan sutun (sonucu tanimlayan EKO/EKG, kimlik vb.)", len(dis)),
 ("Aday havuzu: onceki (ESK_) tahlil sutunu", sum(str(c).startswith("ESK_") for c in aday_ham)),
 ("Aday havuzu: son (YEN_) tahlil sutunu", sum(str(c).startswith("YEN_") for c in aday_ham)),
 ("Aday havuzu: statik (yas, cinsiyet, KB, boy, kilo, BKI, sigara, DM suresi)", sum(c in STATIK for c in aday_ham)),
 ("Tamamen bos oldugu icin cikarilan aday", len(bos)),
 ("SONUC: aday degisken sayisi", X.shape[1]),
 ("Analize alinan hasta", len(X)),
 ("Uc nokta pozitif", int(y.sum())),
 ("Uc nokta negatif", int((1 - y).sum())),
 ("Egitim kumesi hasta / pozitif", "%d / %d" % (len(tr), int(ytr.sum()))),
 ("Test kumesi hasta / pozitif", "%d / %d" % (len(te), int(yte.sum()))),
 ("Secilen degisken (k)", len(SEL)),
]
P(""); P("1) AKIS")
for a, b in akis: P("   %-75s %s" % (a, b))
P("   Tamamen bos adaylar: " + ("; ".join(map(str, bos)) if bos else "yok"))
P("   Dislanan ham sutunlar (%d): %s" % (len(dis), "; ".join(map(str, dis))))

# ---------------- 2) UC NOKTA BILESENLERI ----------------
num = lambda c: pd.to_numeric(r0[c], errors="coerce")
bil = {"LA genislemesi": (num("la abn").fillna(0) > 0), "LVEDD genislemesi": (num("lvedd abn").fillna(0) > 0),
       "EF < %50": ((num("ef") < 50) | (num("ef (E)") < 50)).fillna(False),
       "Uzamis QTc": (num("qtc abn").fillna(0) > 0), "Uzamis QRS": (num("qrs abn").fillna(0) > 0)}
uc = pd.DataFrame([(k, int(v.sum()), round(100 * v.mean(), 1)) for k, v in bil.items()], columns=["bilesen", "n", "%"])
P(""); P("2) UC NOKTA BILESENLERI"); P(uc.to_string(index=False))

# ---------------- 3) TABLO 1 ----------------
def ort(c, ad):
    v = pd.to_numeric(X[c], errors="coerce"); a, b = v[yy == 0], v[yy == 1]
    p = stats.ttest_ind(a.dropna(), b.dropna(), equal_var=False).pvalue
    f = lambda s: "%.1f ± %.1f" % (s.mean(), s.std())
    return [ad, f(v), f(a), f(b), p, "Welch t", round(100 * v.isna().mean(), 1)]
def med(c, ad):
    v = pd.to_numeric(X[c], errors="coerce"); a, b = v[yy == 0], v[yy == 1]
    p = stats.mannwhitneyu(a.dropna(), b.dropna()).pvalue
    f = lambda s: "%.1f [%.1f–%.1f]" % (s.median(), s.quantile(.25), s.quantile(.75))
    return [ad, f(v), f(a), f(b), p, "Mann-Whitney U", round(100 * v.isna().mean(), 1)]
def kat(c, ad, pos):
    v = pd.to_numeric(X[c], errors="coerce"); m = (v == pos)
    p = stats.chi2_contingency(pd.crosstab(m, yy)).pvalue
    f = lambda s: "%d (%.1f%%)" % (m[s].sum(), 100 * m[s].sum() / s.sum())
    return [ad, f(np.ones(len(v), bool)), f(yy == 0), f(yy == 1), p, "Ki-kare", round(100 * v.isna().mean(), 1)]
t1 = [ort("YAŞ", "Age, years"), kat("CİNSİYET", "Female sex, n (%)", 1), ort("boy", "Height, cm"),
      med("kılo", "Weight, kg, median [IQR]"), med("bmı", "Body mass index, kg/m², median [IQR]"),
      ort("sistolık kan basıncı", "Systolic blood pressure, mmHg"), ort("diastolik kan basıncı", "Diastolic blood pressure, mmHg"),
      med("diyabet süresi", "Diabetes duration, years, median [IQR]"), kat("sigara", "Current smoking, n (%)", 1)]
T1 = pd.DataFrame(t1, columns=["Characteristic", "All (n=%d)" % len(yy), "Negative (n=%d)" % (yy == 0).sum(),
                               "Positive (n=%d)" % (yy == 1).sum(), "p", "test", "Missing %"])
P(""); P("3) TABLO 1"); P(T1.to_string(index=False))
kk = pd.to_numeric(X["kılo"], errors="coerce")
P("   Kontrol: en yuksek 3 kilo %s | en yuksek 3 BKI %s" % (sorted(kk.dropna())[-3:], sorted(pd.to_numeric(X["bmı"], errors="coerce").dropna())[-3:]))

# ---------------- 4) TABLO 2 ----------------
Fr = siralama_anova(Xtr, ytr)
beta = fin.named_steps["m"].coef_[0]
rng = np.random.RandomState(SEED); bs = np.full((NBOOT, len(SEL)), np.nan)
for b in range(NBOOT):
    i = rng.randint(0, len(tr), len(tr))
    if len(np.unique(ytr.values[i])) < 2: continue
    bs[b] = boru().fit(Xtr[SEL].iloc[i], pd.Series(ytr.values[i])).named_steps["m"].coef_[0]
lo, hi = np.nanpercentile(bs, 2.5, 0), np.nanpercentile(bs, 97.5, 0)
T2 = pd.DataFrame({"degisken": SEL, "F (egitim)": [round(Fr[s], 2) for s in SEL], "beta": np.round(beta, 4),
                   "exp(beta)": np.round(np.exp(beta), 3), "PI alt": np.round(np.exp(lo), 3), "PI ust": np.round(np.exp(hi), 3),
                   "eksik % (tum)": [round(100 * X[s].isna().mean(), 1) for s in SEL],
                   "zaman": ["onceki" if str(s).startswith("ESK_") else "son" if str(s).startswith("YEN_") else "-" for s in SEL]})
P(""); P("4) TABLO 2"); P(T2.to_string(index=False))

# ---------------- 5) UC NOKTA ORTUSMESI ----------------
B = pd.DataFrame({k: v.values.astype(int) for k, v in bil.items()})
say = B.sum(1)
ort_t = pd.DataFrame([("Kriter sayisi = %d" % j, int((say == j).sum()), round(100 * (say == j).mean(), 1)) for j in range(6)],
                     columns=["kriter sayisi", "n", "%"])
yalniz = pd.DataFrame([("Yalniz " + k, int(((B[k] == 1) & (say == 1)).sum())) for k in B.columns], columns=["bilesen", "n"])
P(""); P("5) UC NOKTA ORTUSMESI"); P(ort_t.to_string(index=False)); P(yalniz.to_string(index=False))
P("   Kontrol: kriter>=1 = %d (uc nokta pozitif %d)" % (int((say >= 1).sum()), int(y.sum())))

# ---------------- 6) EGITIM / TEST KARSILASTIRMASI ----------------
gr = np.zeros(len(X), int); gr[te] = 1
def et(c, ad, tur, pos=1):
    v = pd.to_numeric(X[c], errors="coerce"); a, b = v[gr == 0], v[gr == 1]
    if tur == "ort":
        f = lambda s: "%.1f ± %.1f" % (s.mean(), s.std()); p = stats.ttest_ind(a.dropna(), b.dropna(), equal_var=False).pvalue
    elif tur == "med":
        f = lambda s: "%.1f [%.1f–%.1f]" % (s.median(), s.quantile(.25), s.quantile(.75)); p = stats.mannwhitneyu(a.dropna(), b.dropna()).pvalue
    else:
        m = (v == pos); f = lambda s: "%d (%.1f%%)" % ((s == pos).sum(), 100 * (s == pos).mean())
        p = stats.chi2_contingency(pd.crosstab(m, gr)).pvalue
    return [ad, f(a), f(b), p]
te_rows = [["Endpoint positive, n (%)", "%d (%.1f%%)" % (ytr.sum(), 100 * ytr.mean()), "%d (%.1f%%)" % (yte.sum(), 100 * yte.mean()),
            stats.chi2_contingency(pd.crosstab(yy, gr)).pvalue],
           et("YAŞ", "Age, years", "ort"), et("CİNSİYET", "Female sex, n (%)", "kat"),
           et("bmı", "Body mass index, kg/m², median [IQR]", "med"), et("sistolık kan basıncı", "Systolic BP, mmHg", "ort"),
           et("diyabet süresi", "Diabetes duration, years, median [IQR]", "med"), et("sigara", "Current smoking, n (%)", "kat")]
TE = pd.DataFrame(te_rows, columns=["Characteristic", "Training (n=%d)" % len(tr), "Test (n=%d)" % len(te), "p"])
P(""); P("6) EGITIM / TEST"); P(TE.to_string(index=False))

# ---------------- 7) TABLO 4 (k taramasi, secim katlarin icinde) ----------------
NEV = int(ytr.sum()); kr = []
for k in [10, 15, 20, 30, 40]:
    a = []
    for ti, vi in skf.split(Xtr, ytr):
        Xi, yi = Xtr.iloc[ti], ytr.iloc[ti]
        s = tekillestir(siralama_anova(Xi, yi), k, list(Xi.columns))
        a.append(roc_auc_score(ytr.iloc[vi], boru().fit(Xi[s], yi).predict_proba(Xtr[s].iloc[vi])[:, 1]))
    kr.append([k, "%.3f ± %.3f" % (np.mean(a), np.std(a)), round(NEV / k, 1)])
T4 = pd.DataFrame(kr, columns=["k", "CV-AUC (selection inside folds)", "EPV (training)"])
P(""); P("7) TABLO 4"); P(T4.to_string(index=False))

# ---------------- 8) TABLO 5 (tam denklem) ----------------
imp = fin.named_steps["i"]; sc = fin.named_steps["s"]
T5 = pd.DataFrame({"degisken": SEL, "medyan (atama)": np.round(imp.statistics_, 2), "ortalama": np.round(sc.mean_, 3),
                   "SD": np.round(sc.scale_, 3), "beta (standart)": np.round(beta, 4),
                   "eksik % (tum)": [round(100 * X[s].isna().mean(), 1) for s in SEL]})
P(""); P("8) TABLO 5  kesisim = %.4f" % fin.named_steps["m"].intercept_[0]); P(T5.to_string(index=False))

# ---------------- 9) TUM ADAYLARIN EKSIKLIGI ----------------
EK = pd.DataFrame({"degisken": X.columns, "eksik % (tum)": np.round(100 * X.isna().mean().values, 1),
                   "eksik % (pozitif)": np.round(100 * X[yy == 1].isna().mean().values, 1),
                   "eksik % (negatif)": np.round(100 * X[yy == 0].isna().mean().values, 1),
                   "secildi": [c in SEL for c in X.columns]}).sort_values("eksik % (tum)")
P(""); P("9) EKSIKLIK: <=%%20: %d, %%20-50: %d, >%%50: %d aday" % ((EK.iloc[:, 1] <= 20).sum(),
      ((EK.iloc[:, 1] > 20) & (EK.iloc[:, 1] <= 50)).sum(), (EK.iloc[:, 1] > 50).sum()))

with pd.ExcelWriter(OUT, engine="openpyxl") as w:
    pd.DataFrame(akis, columns=["adim", "deger"]).to_excel(w, sheet_name="akis", index=False)
    pd.DataFrame({"dislanan_sutun": dis}).to_excel(w, sheet_name="dislanan_sutunlar", index=False)
    uc.to_excel(w, sheet_name="uc_nokta", index=False)
    T1.to_excel(w, sheet_name="tablo1", index=False)
    T2.to_excel(w, sheet_name="tablo2", index=False)
    ort_t.to_excel(w, sheet_name="uc_nokta_ortusme", index=False); yalniz.to_excel(w, sheet_name="uc_nokta_ortusme", index=False, startrow=9)
    TE.to_excel(w, sheet_name="tablo1_egitim_test", index=False)
    T4.to_excel(w, sheet_name="tablo4", index=False)
    T5.to_excel(w, sheet_name="tablo5", index=False)
    EK.to_excel(w, sheet_name="eksiklik_tum_adaylar", index=False)
P(""); P("-> " + os.path.basename(OUT)); P("BITTI.")
