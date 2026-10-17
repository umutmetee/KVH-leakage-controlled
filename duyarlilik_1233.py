# -*- coding: utf-8 -*-
"""
duyarlilik_1233.py  -  "Ayrilan hastalari da egitime katsaydiniz?" sorusu icin duyarlilik analizi.
model_ortak.py ile ayni klasorde calisir (ayni boru hatti: ANOVA-F + aile tekillestirme, K=20,
L2 lojistik regresyon C=0.01, medyan atama, z-skoru; secim her zaman yalnizca egitim verisinde).

A) Referans: tezdeki model (744 egitim) -> ayni 187 test hastasi
B) Ayrilan hastalar EGITIME eklenir (744 + ayrilan) -> AYNI 187 test hastasi
   (adil karsilastirma: test hastalari degismez; fark icin eslestirilmis onyukleme)
C) 20 rastgele bolme (tohum 0-19): yalniz 931 vs 931 + ayrilan birlesik kohort
Cikti: ekranda + duyarlilik_1233.xlsx (yalnizca ozet sayilar; hasta kimligi YAZILMAZ)
KULLANIM:  py duyarlilik_1233.py
"""
from model_ortak import *
import statsmodels.api as sm

# --- ayrilan hastalar (dogrulama_302.py ile ayni tanim) ---
VK = os.path.dirname(VERI)
d2 = pd.read_excel(os.path.join(VK, "sizintisiz_veri_1233.xlsx"))
r2 = pd.read_excel(os.path.join(VK, "aiveri2026_haz_1233.xlsx"))
eski = set(pd.to_numeric(d["HASTA_NO"]).astype("int64"))
m = ~pd.to_numeric(d2["HASTA_NO"], errors="coerce").astype("Int64").isin(eski).values
D = d2[m].reset_index(drop=True)
R = r2[~pd.to_numeric(r2["HASTA_NO"], errors="coerce").astype("Int64").isin(eski).values].reset_index(drop=True)
assert (pd.to_numeric(D.HASTA_NO).values == pd.to_numeric(R.HASTA_NO).values).all()
nm = lambda c: pd.to_numeric(R[c], errors="coerce")
yd = pd.Series(((nm("la abn").fillna(0) > 0) | (nm("lvedd abn").fillna(0) > 0)
                | ((nm("ef") < 50) | (nm("ef (E)") < 50)).fillna(False)
                | (nm("qtc abn").fillna(0) > 0) | (nm("qrs abn").fillna(0) > 0)).astype(int).values)
Xd = D.reindex(columns=X.columns).apply(pd.to_numeric, errors="coerce").reset_index(drop=True)

P(""); P("AYRILAN HASTALAR: n = %d | olay %d (%%%.1f) | analizdeki 931: olay %%%.1f"
         % (len(yd), yd.sum(), 100 * yd.mean(), 100 * y.mean()))
P("Birincil modelin 20 degiskeninin ayrilan hastalardaki eksiklik orani:")
EKS = []
for c in SEL:
    EKS.append(dict(degisken=c, eksik_931=round(100 * X[c].isna().mean(), 1), eksik_ayrilan=round(100 * Xd[c].isna().mean(), 1)))
    P("   %-38s 931: %%%5.1f | ayrilan: %%%5.1f" % (c, EKS[-1]["eksik_931"], EKS[-1]["eksik_ayrilan"]))

def kur(Xt, yt):
    sel = tekillestir(siralama_anova(Xt, yt), K, list(Xt.columns))
    return boru().fit(Xt[sel], yt), sel

def kalibrasyon(yy, pp):
    lg = np.log(np.clip(pp, 1e-6, 1 - 1e-6) / (1 - np.clip(pp, 1e-6, 1 - 1e-6)))
    citl = sm.GLM(yy, np.ones((len(yy), 1)), family=sm.families.Binomial(), offset=lg).fit().params[0]
    egim = sm.GLM(yy, sm.add_constant(lg), family=sm.families.Binomial()).fit().params[1]
    return citl, egim

# --- A ve B: ayni 187 test hastasi ---
pA = p
cA, eA = kalibrasyon(yv, pA)
XtrB = pd.concat([Xtr.reset_index(drop=True), Xd], ignore_index=True)
ytrB = pd.concat([ytr.reset_index(drop=True), yd], ignore_index=True)
mB, selB = kur(XtrB, ytrB)
pB = mB.predict_proba(Xte[selB])[:, 1]
aA, aB = roc_auc_score(yv, pA), roc_auc_score(yv, pB)
loA, hiA = boot_ci(yv, pA, 1); loB, hiB = boot_ci(yv, pB, 1)
cB, eB = kalibrasyon(yv, pB)
rng = np.random.RandomState(7); fark = []
for _ in range(NBOOT):
    i = rng.randint(0, len(yv), len(yv))
    if len(np.unique(yv[i])) > 1: fark.append(roc_auc_score(yv[i], pB[i]) - roc_auc_score(yv[i], pA[i]))
fark = np.array(fark)
P(""); P("AYNI 187 TEST HASTASINDA KARSILASTIRMA")
P("   A) Tezdeki model (egitim %d)            : AUROC %.3f (%.3f-%.3f) | CITL %+.3f | egim %.3f | Brier %.3f"
  % (len(ytr), aA, loA, hiA, cA, eA, brier_score_loss(yv, pA)))
P("   B) Ayrilanlar egitime eklendi (egitim %d): AUROC %.3f (%.3f-%.3f) | CITL %+.3f | egim %.3f | Brier %.3f"
  % (len(ytrB), aB, loB, hiB, cB, eB, brier_score_loss(yv, pB)))
P("   Fark B - A: %+.3f (%%95 GA %+.3f, %+.3f) | farkin sifirdan buyuk oldugu onyukleme orani %%%.0f"
  % (aB - aA, *np.percentile(fark, [2.5, 97.5]), 100 * (fark > 0).mean()))
P("   B'de secime giren yeni degiskenler : " + (", ".join(sorted(set(selB) - set(SEL))) or "yok"))
P("   B'de secimden cikan degiskenler    : " + (", ".join(sorted(set(SEL) - set(selB))) or "yok"))

# --- C: 20 rastgele bolme ---
XP = pd.concat([X, Xd], ignore_index=True); yP = pd.concat([y, yd], ignore_index=True)
Y = []
P(""); P("20 RASTGELE BOLME (tohum 0-19; her bolmede secim yalniz egitimde)")
P("   tohum | yalniz 931 | 931 + ayrilan (n=%d)" % len(yP))
for s in range(20):
    t0, s0 = train_test_split(np.arange(len(X)), test_size=0.2, stratify=y, random_state=s)
    m0, sl0 = kur(X.iloc[t0], y.iloc[t0]); a0 = roc_auc_score(y.iloc[s0], m0.predict_proba(X.iloc[s0][sl0])[:, 1])
    t1, s1 = train_test_split(np.arange(len(XP)), test_size=0.2, stratify=yP, random_state=s)
    m1, sl1 = kur(XP.iloc[t1], yP.iloc[t1]); a1 = roc_auc_score(yP.iloc[s1], m1.predict_proba(XP.iloc[s1][sl1])[:, 1])
    Y.append(dict(tohum=s, yalniz_931=round(a0, 3), birlesik=round(a1, 3)))
    P("   %5d | %.3f      | %.3f" % (s, a0, a1))
Yd = pd.DataFrame(Y)
P("   ORTALAMA (SS): yalniz 931 %.3f (%.3f) | birlesik %.3f (%.3f)"
  % (Yd.yalniz_931.mean(), Yd.yalniz_931.std(), Yd.birlesik.mean(), Yd.birlesik.std()))
P("   (kontrol: tezdeki 20 bolme ortalamasi 0,744, SS 0,029)")

OZ = pd.DataFrame([
    dict(analiz="A tezdeki model, 187 test", egitim_n=len(ytr), AUROC=round(aA, 3), GA_alt=round(loA, 3), GA_ust=round(hiA, 3), CITL=round(cA, 3), egim=round(eA, 3)),
    dict(analiz="B ayrilanlar egitime eklendi, ayni 187 test", egitim_n=len(ytrB), AUROC=round(aB, 3), GA_alt=round(loB, 3), GA_ust=round(hiB, 3), CITL=round(cB, 3), egim=round(eB, 3)),
    dict(analiz="Fark B-A (eslestirilmis onyukleme)", egitim_n=np.nan, AUROC=round(aB - aA, 3), GA_alt=round(np.percentile(fark, 2.5), 3), GA_ust=round(np.percentile(fark, 97.5), 3), CITL=np.nan, egim=np.nan),
    dict(analiz="C 20 bolme ortalama, yalniz 931", egitim_n=np.nan, AUROC=round(Yd.yalniz_931.mean(), 3), GA_alt=np.nan, GA_ust=np.nan, CITL=np.nan, egim=np.nan),
    dict(analiz="C 20 bolme ortalama, birlesik", egitim_n=np.nan, AUROC=round(Yd.birlesik.mean(), 3), GA_alt=np.nan, GA_ust=np.nan, CITL=np.nan, egim=np.nan),
])
out = os.path.join(KLASOR, "duyarlilik_1233.xlsx")
with pd.ExcelWriter(out) as w:
    OZ.to_excel(w, sheet_name="ozet", index=False)
    Yd.to_excel(w, sheet_name="yirmi_bolme", index=False)
    pd.DataFrame(EKS).to_excel(w, sheet_name="eksiklik", index=False)
    n_ = max(len(selB), len(SEL))
    pd.DataFrame({"A_secilen": SEL + [""] * (n_ - len(SEL)), "B_secilen": selB + [""] * (n_ - len(selB))}).to_excel(w, sheet_name="degiskenler", index=False)
P(""); P("Yazildi: " + out); P("BITTI. Ekrandaki ciktinin tamamini kopyalayip gonderin.")
