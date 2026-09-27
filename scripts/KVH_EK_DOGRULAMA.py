# -*- coding: utf-8 -*-
"""
KVH_EK_DOGRULAMA.py  (27.09.2026)
Makalede/tezde yazan ama KVH_TAM_ANALIZ.py'nin URETMEDIGI sayilari hesaplar ve
her birini makaledeki degerle yan yana koyar.

KULLANIM (kendi bilgisayarinizda, gercek veriyle):
  1) Bu dosyayi KVH_TAM_ANALIZ.py ile ayni klasore koyun
     (Dropbox: /Umut Mete/07_Analiz). Ayni klasorde:
        sizintisiz_veri.xlsx  (678.451 bayt)
        aiveri2026_haz.xlsx
  2) python KVH_EK_DOGRULAMA.py
  3) Ciktilar:  cikti_ek/ek_dogrulama_rapor.txt
                cikti_ek/ek_dogrulama_karsilastirma.csv
                cikti_ek/dca_tam_tablo.csv
                cikti_ek/secici_duyarlilik.csv

KURAL: Makaleye yalnizca bu ciktilarda gorunen sayilar girer. "FARK" yazan
her satir icin makaledeki deger bu ciktinin degeriyle degistirilir.

Boru hatti KVH_TAM_ANALIZ.py ile birebir aynidir (ayni veri okuma, ayni bolme,
ayni SEED=42, ayni aile tekillestirmesi, ayni C=0.01).
"""
import os, re, sys, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows cmd Turkce karakter
except Exception:
    pass

from scipy import stats
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import f_classif, mutual_info_classif, RFE
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.calibration import CalibratedClassifierCV
from statsmodels.stats.outliers_influence import variance_inflation_factor

KLASOR = os.path.dirname(os.path.abspath(__file__))
CIKTI = os.path.join(KLASOR, "cikti_ek")
VERI = os.path.join(KLASOR, "sizintisiz_veri.xlsx")
RAW = os.path.join(KLASOR, "aiveri2026_haz.xlsx")
SEED, K, C, NBOOT = 42, 20, 0.01, 2000
STATIK = ["diyabet süresi", "YAŞ", "CİNSİYET", "sigara", "sistolık kan basıncı",
          "diastolik kan basıncı", "boy", "kılo", "bmı"]
os.makedirs(CIKTI, exist_ok=True)

_LOG, KARS = [], []
def P(s=""):
    print(s); _LOG.append(str(s))
def BASLIK(s):
    P(""); P("=" * 78); P(s); P("=" * 78)
def KONTROL(etiket, hesap, makale, tol=0.0015, nokta=3):
    """hesap: bu calistirmanin degeri; makale: makalede yazan deger (None = yeni)."""
    if makale is None:
        durum = "YENI"
    else:
        durum = "OK" if abs(hesap - makale) <= tol else "FARK"
    KARS.append(dict(etiket=etiket, hesaplanan=round(float(hesap), 4),
                     makalede=makale, durum=durum))
    mk = "-" if makale is None else ("%." + str(nokta) + "f") % makale
    P("   %-58s hesap %s | makale %s  [%s]" % (etiket, ("%." + str(nokta) + "f") % hesap, mk, durum))

# ---------------------------------------------------------------------------
# VERI (KVH_TAM_ANALIZ.py ile birebir)
# ---------------------------------------------------------------------------
BASLIK("0. VERI")
for f in (VERI, RAW):
    if not os.path.exists(f):
        sys.exit("HATA: dosya bulunamadi -> %s" % f)
P("sizintisiz_veri.xlsx boyut : %d bayt (beklenen 678451)" % os.path.getsize(VERI))
d = pd.read_excel(VERI); raw = pd.read_excel(RAW)
assert (pd.to_numeric(d["HASTA_NO"]) == pd.to_numeric(raw["HASTA_NO"])).all(), "HASTA_NO hizasi bozuk"
num = lambda c: pd.to_numeric(raw[c], errors="coerce")
la = num("la abn").fillna(0) > 0
lv = num("lvedd abn").fillna(0) > 0
ef_ = ((num("ef") < 50) | (num("ef (E)") < 50)).fillna(False)
qtc = num("qtc abn").fillna(0) > 0
qrs = num("qrs abn").fillna(0) > 0
y = pd.Series((la | lv | ef_ | qtc | qrs).astype(int)).reset_index(drop=True)
Xa = d.drop(columns=["kalp hastalığı"])
cols = [c for c in Xa.columns if str(c).startswith(("ESK_", "YEN_"))] + [c for c in STATIK if c in Xa.columns]
X = Xa[cols].apply(pd.to_numeric, errors="coerce")
X = X.drop(columns=X.columns[X.isna().all()].tolist()).reset_index(drop=True)
idx = np.arange(len(X))
tr, te = train_test_split(idx, test_size=0.2, stratify=y, random_state=SEED)
Xtr, Xte, ytr, yte = X.iloc[tr], X.iloc[te], y.iloc[tr], y.iloc[te]
yv = yte.values
P("uc nokta pozitif %d/%d | aday %d | egitim %d test %d" % (y.sum(), len(y), X.shape[1], len(tr), len(te)))

def aile(n):
    s = re.sub(r'^(ESK_|YEN_)\s*', '', str(n)).strip().lower()
    s = re.sub(r'\s+', ' ', s)
    if 'hba1c' in s: return 'hba1c'
    if s.startswith('üre') or s.startswith('bun'): return 'ure_bun'
    if 'tgfr' in s or 'kreatinin' in s: return 'renal'
    if 'rdw' in s: return 'rdw'
    if s in ('neu%', 'lym%', 'nlr'): return 'lokosit'
    if 'non hdl' in s or s == 'kolesterol' or 'ldl' in s: return 'aterojenik_lipid'
    return s

def siralama_anova(Xs, ys):
    F, _ = f_classif(Xs.fillna(Xs.median()), ys)
    return pd.Series(F, index=Xs.columns)

def tekillestir(rank, k, havuz):
    fam = {}
    for c in havuz: fam.setdefault(aile(c), []).append(c)
    en_iyi = {f: max(g, key=lambda c: rank.get(c, -np.inf)) for f, g in fam.items()}
    out, kullanilan = [], set()
    for c in sorted(rank.index, key=lambda z: -rank[z]):
        f = aile(c)
        if f in kullanilan: continue
        if en_iyi[f] not in out: out.append(en_iyi[f]); kullanilan.add(f)
        if len(out) >= k: break
    return out

def boru(est=None):
    return Pipeline([("i", SimpleImputer(strategy="median")), ("s", StandardScaler()),
                     ("m", est if est is not None else LogisticRegression(C=C, max_iter=2000))])

skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
Frank = siralama_anova(Xtr, ytr)
SEL = tekillestir(Frank, K, list(Xtr.columns))
fin = boru().fit(Xtr[SEL], ytr)
p = fin.predict_proba(Xte[SEL])[:, 1]
KONTROL("Nihai model test AUROC", roc_auc_score(yv, p), 0.755)

def boot_ci(yy, pp, seed):
    rng = np.random.RandomState(seed); b = []
    for _ in range(NBOOT):
        i = rng.randint(0, len(yy), len(yy))
        if len(np.unique(yy[i])) > 1: b.append(roc_auc_score(yy[i], pp[i]))
    return np.percentile(b, [2.5, 97.5])

# ---------------------------------------------------------------------------
# E1. KARAR EGRISI - TAM TABLO (Tablo 4.8 / Sekil 13)
# ---------------------------------------------------------------------------
BASLIK("E1. KARAR EGRISI ANALIZI - tam esik tablosu")
prev = yv.mean()
def nb(pp, t):
    yh = pp >= t
    return ((yh == 1) & (yv == 1)).sum()/len(yv) - ((yh == 1) & (yv == 0)).sum()/len(yv)*(t/(1-t))
satir = []
for t in np.round(np.arange(0.05, 0.701, 0.05), 2):
    m, a = nb(p, t), prev - (1-prev)*(t/(1-t))
    satir.append(dict(esik=t, model=m, herkesi_tedavi=a, fark=m - a, kimse=0.0))
dca = pd.DataFrame(satir); dca.to_csv(os.path.join(CIKTI, "dca_tam_tablo.csv"), index=False)
P("   esik | model  | herkesi tedavi | fark (model - herkesi tedavi)")
for _, r in dca.iterrows():
    P("   %.2f | %+.3f | %+.3f         | %+.3f" % (r.esik, r.model, r.herkesi_tedavi, r.fark))
ince = np.round(np.arange(0.01, 0.70, 0.01), 2)
fark_ince = np.array([nb(p, t) - (prev - (1-prev)*(t/(1-t))) for t in ince])
poz = ince[fark_ince > 0]
# fark'in bundan sonra hep pozitif kaldigi en kucuk esik
kalici = None
for i, t in enumerate(ince):
    if (fark_ince[i:] > 0).all(): kalici = t; break
P("   ince tarama: modelin herkesi-tedaviye ustun oldugu ilk esik = %s; bundan sonra hep ustun oldugu esik = %s"
  % (poz.min() if len(poz) else "yok", kalici))
for t, mk in [(0.20, None), (0.25, 0.032), (0.30, 0.058), (0.40, 0.155), (0.50, 0.310)]:
    KONTROL("DCA fark @%.2f" % t, dca.loc[np.isclose(dca.esik, t), "fark"].iloc[0], mk)
for t, mk in [(0.20, None), (0.25, 0.234), (0.30, 0.202), (0.40, 0.157), (0.50, 0.112)]:
    KONTROL("DCA model net fayda @%.2f" % t, dca.loc[np.isclose(dca.esik, t), "model"].iloc[0], mk)

# ---------------------------------------------------------------------------
# E2. SECICI DUYARLILIGI (Tablo VI / Tablo 3.2 / Ek E)
# Not: bu seciciler icin daha once saklanmis kod yok; burada tanimlandigi
# haliyle hesaplanir. Makaledeki tablo BU CIKTIYLA guncellenmelidir.
# Aile tekillestirmesi dahil diger her adim ANOVA ile aynidir; yalnizca
# siralama olcutu degisir.
# ---------------------------------------------------------------------------
BASLIK("E2. SECICI DUYARLILIGI")
def _Z(Xs):
    return StandardScaler().fit_transform(SimpleImputer(strategy="median").fit_transform(Xs))
def rank_rf(Xs, ys):
    m = RandomForestClassifier(n_estimators=400, random_state=SEED).fit(
        SimpleImputer(strategy="median").fit_transform(Xs), ys)
    return pd.Series(m.feature_importances_, index=Xs.columns)
def rank_lasso(Xs, ys):
    m = LogisticRegression(penalty="l1", solver="liblinear", C=0.1, max_iter=5000,
                           random_state=SEED).fit(_Z(Xs), ys)
    return pd.Series(np.abs(m.coef_[0]), index=Xs.columns)
def rank_rfe(Xs, ys):
    r = RFE(LogisticRegression(C=C, max_iter=2000), n_features_to_select=1, step=1).fit(_Z(Xs), ys)
    return pd.Series(-r.ranking_.astype(float), index=Xs.columns)
def rank_mi(Xs, ys):
    return pd.Series(mutual_info_classif(SimpleImputer(strategy="median").fit_transform(Xs), ys,
                                         random_state=SEED), index=Xs.columns)
SECICI = [("ANOVA F-istatistigi (kullanilan)", siralama_anova, (0.754, 0.755)),
          ("Rastgele orman onemi", rank_rf, (0.753, 0.732)),
          ("L1 cezali lojistik (LASSO)", rank_lasso, (0.747, 0.746)),
          ("Ozyinelemeli oznitelik eleme (RFE)", rank_rfe, (0.750, 0.722)),
          ("Karsilikli bilgi", rank_mi, (0.730, 0.701))]
def cv_icerde(secfn):
    a = []
    for ti, vi in skf.split(Xtr, ytr):
        Xi, yi = Xtr.iloc[ti], ytr.iloc[ti]
        s = secfn(Xi, yi)
        a.append(roc_auc_score(ytr.iloc[vi], boru().fit(Xi[s], yi).predict_proba(Xtr[s].iloc[vi])[:, 1]))
    return np.mean(a), np.std(a)
def test_auc(s):
    return roc_auc_score(yv, boru().fit(Xtr[s], ytr).predict_proba(Xte[s])[:, 1])
sec_satir = []
for ad, fn, (mcv, mte) in SECICI:
    f = lambda Xi, yi, fn=fn: tekillestir(fn(Xi, yi), K, list(Xi.columns))
    s = f(Xtr, ytr); cv, sd = cv_icerde(f); h = test_auc(s)
    ort = len(set(s) & set(SEL))
    sec_satir.append(dict(kume=ad, n=len(s), cv=cv, sd=sd, test=h, ortusme=ort))
    P("   %-38s n=%3d  CV %.3f +- %.3f | test %.3f | ANOVA ile ortusme %d/20" % (ad, len(s), cv, sd, h, ort))
    KONTROL(ad + " CV", cv, mcv); KONTROL(ad + " test", h, mte)
# elenenler, sonraki kusak, tum adaylar
ELENEN = [c for c in Xtr.columns if c not in SEL]
def f_elenen(Xi, yi):
    s = tekillestir(siralama_anova(Xi, yi), K, list(Xi.columns)); return [c for c in Xi.columns if c not in s]
def f_kusak(Xi, yi):
    return tekillestir(siralama_anova(Xi, yi), 40, list(Xi.columns))[20:40]
def f_tum(Xi, yi):
    return list(Xi.columns)
for ad, fn, (mcv, mte) in [("Yalnizca elenen degiskenler", f_elenen, (0.713, 0.727)),
                           ("Sonraki kusak (sira 21-40)", f_kusak, (0.685, 0.680)),
                           ("Tum aday degiskenler", f_tum, (0.735, 0.745))]:
    s = fn(Xtr, ytr); cv, sd = cv_icerde(fn); h = test_auc(s)
    sec_satir.append(dict(kume=ad, n=len(s), cv=cv, sd=sd, test=h, ortusme=len(set(s) & set(SEL))))
    P("   %-38s n=%3d  CV %.3f +- %.3f | test %.3f" % (ad, len(s), cv, sd, h))
    KONTROL(ad + " CV", cv, mcv); KONTROL(ad + " test", h, mte)
pd.DataFrame(sec_satir).to_csv(os.path.join(CIKTI, "secici_duyarlilik.csv"), index=False)

# ---------------------------------------------------------------------------
# E3. KAYIT HATASI DUZELTMESININ REFERANS MODELE ETKISI
# ---------------------------------------------------------------------------
BASLIK("E3. KILO/VKI DUZELTMESI ve KLINIK REFERANS MODEL")
KLINIK = [c for c in ["YAŞ", "CİNSİYET", "bmı", "sistolık kan basıncı", "diastolik kan basıncı",
                      "sigara", "diyabet süresi"] if c in X.columns]
Xc = X.copy()
kk = Xc["kılo"]; bb = Xc["bmı"]; hh = Xc["boy"]
i1 = kk.idxmax(); Xc.loc[i1, "kılo"] = 79.7
i2 = bb.idxmax(); Xc.loc[i2, "bmı"] = round(kk[i2]/(hh[i2]/100)**2, 1)
a_ham = roc_auc_score(yv, boru().fit(X.iloc[tr][KLINIK], ytr).predict_proba(X.iloc[te][KLINIK])[:, 1])
a_duz = roc_auc_score(yv, boru().fit(Xc.iloc[tr][KLINIK], ytr).predict_proba(Xc.iloc[te][KLINIK])[:, 1])
KONTROL("Referans model AUROC, ham veri", a_ham, 0.697)
KONTROL("Referans model AUROC, duzeltilmis veri", a_duz, 0.697)

# ---------------------------------------------------------------------------
# E4. TEKILLESTIRMESIZ MODEL: VIF ve URE OLASILIK ORANI
# ---------------------------------------------------------------------------
BASLIK("E4. TEKILLESTIRMESIZ MODEL (ure OR ve VIF)")
ham20 = list(Frank.sort_values(ascending=False).index[:K])
Z = _Z(Xtr[ham20])
vif = [variance_inflation_factor(Z, i) for i in range(len(ham20))]
KONTROL("Tekillestirmesiz maks VIF (makale ~850, yuvarlanmis)", max(vif), 850, tol=100, nokta=1)
m_ham = boru().fit(Xtr[ham20], ytr)
P("   tekillestirmesiz kume: %s" % ", ".join(ham20))
ure = [c for c in ham20 if aile(c) == "ure_bun"]
rng = np.random.RandomState(SEED); bs = []
for _ in range(NBOOT):
    i = rng.randint(0, len(tr), len(tr))
    if len(np.unique(ytr.values[i])) < 2: continue
    bs.append(boru().fit(Xtr[ham20].iloc[i], pd.Series(ytr.values[i])).named_steps["m"].coef_[0])
bs = np.array(bs)
for u in ure:
    j = ham20.index(u); b = m_ham.named_steps["m"].coef_[0][j]
    P("   %-28s cezali (C=0.01) exp b %.3f  [%.3f-%.3f]" % (u, np.exp(b), *np.exp(np.percentile(bs[:, j], [2.5, 97.5]))))
# cezasiz (klasik) lojistik: makaledeki 89,8 (0,28-28.774) buradan gelmis olabilir
import statsmodels.api as sm
Zc = sm.add_constant(Z)
try:
    lr_klasik = sm.Logit(ytr.values, Zc).fit(disp=0)
    for u in ure:
        j = ham20.index(u) + 1
        ci = lr_klasik.conf_int()[j]
        P("   %-28s cezasiz exp b %.1f  [%.2f-%.0f]" % (u, np.exp(lr_klasik.params[j]), np.exp(ci[0]), np.exp(ci[1])))
    P("   (Makalede: ure OR 89,8; %95 GA 0,28-28.774. Hangi satirin eslestigine bakin;")
    P("    hicbiri eslesmiyorsa bu sayi metinden cikarilip yukaridaki degerle degistirilmeli.)")
except Exception as e:
    P("   cezasiz model yakinsamadi: %s" % e)

# ---------------------------------------------------------------------------
# E5. CINSIYET ve SIGARANIN SIRASI
# ---------------------------------------------------------------------------
BASLIK("E5. CINSIYET ve SIGARA - ANOVA sirasi")
Fp = f_classif(Xtr.fillna(Xtr.median()), ytr)
tab = pd.DataFrame({"F": Fp[0], "p": Fp[1]}, index=Xtr.columns).sort_values("F", ascending=False)
tab["sira"] = np.arange(1, len(tab) + 1)
for c, ms, mf, mp in [("CİNSİYET", 61, 6.75, 0.0096), ("sigara", 110, 0.61, 0.434)]:
    KONTROL("%s sirasi" % c, tab.loc[c, "sira"], ms, tol=0, nokta=0)
    KONTROL("%s F" % c, tab.loc[c, "F"], mf, tol=0.006, nokta=2)
    KONTROL("%s p" % c, tab.loc[c, "p"], mp, tol=0.0006, nokta=4)

# ---------------------------------------------------------------------------
# E6. DIYABET SURESI = 0 GRUBU (ADA olcutleri)
# Tanim: diyabetik = herhangi bir HbA1c >= 6,5 VEYA herhangi bir glukoz >= 126
#        normoglisemik = tum HbA1c < 5,7 VE tum glukoz < 100 (en az biri olculmus)
# Makaledeki %15,6 / %25,6 baska bir tanimla hesaplandiysa tanim metne yazilmali.
# ---------------------------------------------------------------------------
BASLIK("E6. DIYABET SURESI 0 OLAN GRUP")
z = (X["diyabet süresi"] == 0).values
hb = X[[c for c in X.columns if aile(c) == "hba1c" and "%" in str(c)]]
gl = X[[c for c in X.columns if re.sub(r'^(ESK_|YEN_)\s*', '', str(c)).strip().lower() == "glukoz"]]
diy = ((hb >= 6.5).any(axis=1) | (gl >= 126).any(axis=1)).values
olcum = (hb.notna().any(axis=1) | gl.notna().any(axis=1)).values
normo = (((hb < 5.7) | hb.isna()).all(axis=1) & ((gl < 100) | gl.isna()).all(axis=1)).values & olcum
P("   HbA1c sutunlari: %s | glukoz sutunlari: %s" % (list(hb.columns), list(gl.columns)))
KONTROL("sure=0 n", z.sum(), 90, tol=0, nokta=0)
KONTROL("sure=0 icinde ADA'ya gore diyabetik %", 100*diy[z].mean(), 15.6, tol=0.06, nokta=1)
KONTROL("sure=0 icinde normoglisemik %", 100*normo[z].mean(), 25.6, tol=0.06, nokta=1)

# ---------------------------------------------------------------------------
# E7. BOOTSTRAP ARALIKLARININ TUTARLILIGI
# Makalede tam bilesik icin iki farkli aralik var: 0,681-0,824 (ana sonuc,
# tohum 1) ve 0,686-0,827 (daraltilmis uc nokta paragrafi, tohum 7).
# ---------------------------------------------------------------------------
BASLIK("E7. TAM BILESIK UC NOKTA ARALIKLARI")
lo1, hi1 = boot_ci(yv, p, 1); lo7, hi7 = boot_ci(yv, p, 7)
KONTROL("AUROC %95 GA alt (tohum 1)", lo1, 0.681); KONTROL("AUROC %95 GA ust (tohum 1)", hi1, 0.824)
KONTROL("AUROC %95 GA alt (tohum 7)", lo7, 0.686); KONTROL("AUROC %95 GA ust (tohum 7)", hi7, 0.827)
P("   Oneri: makalede tek aralik (tohum 1) kullanilsin; daraltilmis uc nokta paragrafindaki")
P("   'full composite' araligi 0,681-0,824 olarak duzeltilsin.")
def daralt_epv(lbl):
    yy = pd.Series(lbl.astype(int)).reset_index(drop=True)
    t2, _ = train_test_split(idx, test_size=0.2, stratify=yy, random_state=SEED)
    return yy.iloc[t2].sum() / K
KONTROL("Agir uc nokta EPV", daralt_epv(lv | ef_), 5.8, tol=0.05, nokta=1)
KONTROL("Elektriksel uc nokta EPV", daralt_epv(qtc | qrs), 6.5, tol=0.05, nokta=1)

# ---------------------------------------------------------------------------
# E8. PLATT YENIDEN KALIBRASYONU - iki yontem
# ---------------------------------------------------------------------------
BASLIK("E8. PLATT YENIDEN KALIBRASYONU")
def ece(pp):
    q = pd.qcut(pp, 10, duplicates="drop")
    return sum(abs(yv[q == g].mean() - pp[q == g].mean()) * (q == g).sum() for g in q.categories) / len(yv)
pc = CalibratedClassifierCV(boru(), method="sigmoid", cv=skf).fit(Xtr[SEL], ytr).predict_proba(Xte[SEL])[:, 1]
oof = cross_val_predict(boru(), Xtr[SEL], ytr, cv=skf, method="predict_proba")[:, 1]
lg = lambda v: np.log(v/(1-v))
pl = LogisticRegression(C=1e6, max_iter=2000).fit(lg(oof).reshape(-1, 1), ytr)
pp_oof = pl.predict_proba(lg(p).reshape(-1, 1))[:, 1]
KONTROL("ECE ham model", ece(p), 0.056)
KONTROL("ECE Platt, CalibratedClassifierCV (5 model ortalamasi)", ece(pc), 0.037)
KONTROL("ECE Platt, gercek kat-disi (tek model + sigmoid)", ece(pp_oof), None)
P("   Makale metni hangi yontemi anlatiyorsa o yontemin ECE'si yazilmali.")

# ---------------------------------------------------------------------------
# E9. KALIBRASYON EGIMI > 1: dusuk riskliler olduğundan yuksek mi?
# ---------------------------------------------------------------------------
BASLIK("E9. UC DILIMLERDE TAHMIN vs GOZLENEN")
q = pd.qcut(p, 10, labels=False, duplicates="drop")
for g, ad in [(q.min(), "en dusuk %10"), (q.max(), "en yuksek %10")]:
    P("   %-14s ortalama tahmin %.3f | gozlenen oran %.3f" % (ad, p[q == g].mean(), yv[q == g].mean()))
P("   Egim > 1 ise beklenen: dusuk dilimde tahmin > gozlenen, yuksek dilimde tahmin < gozlenen.")

# ---------------------------------------------------------------------------
BASLIK("OZET")
R = pd.DataFrame(KARS); R.to_csv(os.path.join(CIKTI, "ek_dogrulama_karsilastirma.csv"), index=False)
for dur in ["FARK", "YENI", "OK"]:
    P("   %-5s : %d satir" % (dur, (R.durum == dur).sum()))
P("")
P("FARK satirlari (makalede duzeltilecek):")
for _, r in R[R.durum == "FARK"].iterrows():
    P("   %-58s makale %s -> bu cikti %s" % (r.etiket, r.makalede, r.hesaplanan))
with open(os.path.join(CIKTI, "ek_dogrulama_rapor.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(_LOG))
P("\nCiktilar: %s" % CIKTI)
