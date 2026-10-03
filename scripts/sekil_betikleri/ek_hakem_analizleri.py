# -*- coding: utf-8 -*-
"""
ek_hakem_analizleri.py  (EK ANALIZLER - olasi hakem sorulari: hiperparametre aramasi, ic ice model, cinsiyet)
ADIM 1 / 2: Analizi BIR KEZ calistirir ve her figurun cizildigi sayilari
sekil_verileri.xlsx dosyasina (figur basina bir sayfa) yazar.
ADIM 2: Figure_*.py betiklerinin her biri yalnizca kendi sayfasini okuyup
tek bir figur cizer (veya tum_sekilleri_ciz.py hepsini sirayla cizer).

KULLANIM (07_Analiz klasorunde; bu klasordeki dosyalar oraya kopyalanir):
    py 00_sekil_verisi_uret.py
Gerekli dosyalar ayni klasorde: sizintisiz_veri.xlsx, aiveri2026_haz.xlsx
Cikti: sekil_verileri.xlsx  (hasta kimligi, ad veya hasta numarasi ICERMEZ;
        yalnizca ozet sayilar ve test kumesi tahmin olasiliklari)
Boru hatti KVH_TAM_ANALIZ.py ile birebir aynidir (SEED=42, C=0.01, K=20).
"""
import os, re, sys, warnings

def _py_kontrol():
    """VS Code calistir dugmesi sklearn'suz bir Python acarsa betigi 'py' ile yeniden baslatir."""
    import os, sys, shutil, subprocess
    try:
        import sklearn, statsmodels  # noqa: F401
        return
    except ImportError:
        pass
    if os.environ.get("KVH_YENIDEN") != "1" and shutil.which("py"):
        print("Bu Python'da sklearn/statsmodels yok (%s); 'py' ile yeniden calistiriliyor..." % sys.executable)
        env = dict(os.environ, KVH_YENIDEN="1")
        sys.exit(subprocess.call(["py", os.path.abspath(sys.argv[0])] + sys.argv[1:], env=env))
    sys.exit("HATA: sklearn/statsmodels bulunamadi. Terminalde 'py <dosya>.py' ile calistirin.")
_py_kontrol()
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import (RandomForestClassifier, ExtraTreesClassifier, AdaBoostClassifier,
                              GradientBoostingClassifier, HistGradientBoostingClassifier,
                              VotingClassifier, StackingClassifier)
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_predict, learning_curve
from sklearn.metrics import roc_auc_score, roc_curve

KLASOR = os.path.dirname(os.path.abspath(__file__))
def bul(ad):
    """Veri dosyasini once bu klasorde, sonra ust klasorlerde ve onlarin 07_Analiz alt klasorunde arar."""
    k = KLASOR
    while True:
        for aday in (os.path.join(k, ad), os.path.join(k, "07_Analiz", ad)):
            if os.path.exists(aday): return aday
        ust = os.path.dirname(k)
        if ust == k: return os.path.join(KLASOR, ad)
        k = ust
VERI = bul("sizintisiz_veri.xlsx")
RAW = bul("aiveri2026_haz.xlsx")
print("Veri:", VERI)
CIKTI = os.path.join(KLASOR, "sekil_verileri.xlsx")
SEED, K, C = 42, 20, 0.01
NBOOT = int(os.environ.get("KVH_NBOOT", 2000))
STATIK = ["diyabet süresi", "YAŞ", "CİNSİYET", "sigara", "sistolık kan basıncı",
          "diastolik kan basıncı", "boy", "kılo", "bmı"]
def P(s=""):
    print(s)
# ---------------------------------------------------------------------------
# VERI ve BORU HATTI (KVH_TAM_ANALIZ.py ile ayni)
# ---------------------------------------------------------------------------
P("VERI yukleniyor...")
for f in (VERI, RAW):
    if not os.path.exists(f):
        sys.exit("HATA: dosya bulunamadi -> %s" % f)
d = pd.read_excel(VERI); raw = pd.read_excel(RAW)
assert (pd.to_numeric(d["HASTA_NO"]) == pd.to_numeric(raw["HASTA_NO"])).all()
num = lambda c: pd.to_numeric(raw[c], errors="coerce")
la = (num("la abn").fillna(0) > 0).values
lv = (num("lvedd abn").fillna(0) > 0).values
ef_ = ((num("ef") < 50) | (num("ef (E)") < 50)).fillna(False).values
qtc = (num("qtc abn").fillna(0) > 0).values
qrs = (num("qrs abn").fillna(0) > 0).values
y = pd.Series((la | lv | ef_ | qtc | qrs).astype(int))
Xa = d.drop(columns=["kalp hastalığı"])
cols = [c for c in Xa.columns if str(c).startswith(("ESK_", "YEN_"))] + [c for c in STATIK if c in Xa.columns]
X = Xa[cols].apply(pd.to_numeric, errors="coerce")
X = X.drop(columns=X.columns[X.isna().all()].tolist()).reset_index(drop=True)
idx = np.arange(len(X))
tr, te = train_test_split(idx, test_size=0.2, stratify=y, random_state=SEED)
Xtr, Xte, ytr, yte = X.iloc[tr], X.iloc[te], y.iloc[tr], y.iloc[te]
yv = yte.values

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
    en_iyi = {f: max(g, key=lambda c: rank.get(c, -1)) for f, g in fam.items()}
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
def boot_ci(yy, pp, seed):
    rng = np.random.RandomState(seed); b = []
    for _ in range(NBOOT):
        i = rng.randint(0, len(yy), len(yy))
        if len(np.unique(yy[i])) > 1: b.append(roc_auc_score(yy[i], pp[i]))
    return np.percentile(b, [2.5, 97.5])

skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
Frank = siralama_anova(Xtr, ytr)
SEL = tekillestir(Frank, K, list(Xtr.columns))
fin = boru().fit(Xtr[SEL], ytr)
p = fin.predict_proba(Xte[SEL])[:, 1]
AUC = roc_auc_score(yv, p)
oof = cross_val_predict(boru(), Xtr[SEL], ytr, cv=skf, method="predict_proba")[:, 1]
f_, t_, th_ = roc_curve(ytr, oof); TAU = th_[np.argmax(t_ - f_)]
P("Nihai model AUROC %.3f | tau %.3f (beklenen 0.755 / 0.428)" % (AUC, TAU))

# ---------------------------------------------------------------------------
# EK ANALIZ: hiperparametre aramasi YALNIZCA egitim verisinde (ic ice 5 kat CV)
# Test seti yalnizca son degerlendirmede bir kez kullanilir; ayni 20 degisken.
# ---------------------------------------------------------------------------
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
IZG = {
 "Logistic Regression": (LogisticRegression(max_iter=5000), {"m__C": [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1, 3]}),
 "Random Forest": (RandomForestClassifier(n_estimators=400, random_state=SEED),
                   {"m__max_depth": [3, 5, 8, None], "m__min_samples_leaf": [1, 5, 10, 20], "m__max_features": ["sqrt", 0.5]}),
 "Gradient Boosting": (GradientBoostingClassifier(random_state=SEED),
                       {"m__n_estimators": [100, 300], "m__learning_rate": [0.01, 0.05, 0.1], "m__max_depth": [2, 3], "m__subsample": [0.7, 1.0]}),
 "Support Vector Machine": (SVC(probability=True, random_state=SEED),
                            {"m__C": [0.1, 0.3, 1, 3, 10], "m__gamma": ["scale", 0.003, 0.01, 0.03]}),
}
satir = []
for ad, (est, izgara) in IZG.items():
    P("Arama: %s ..." % ad)
    gs = GridSearchCV(boru(est), izgara, scoring="roc_auc", cv=skf, n_jobs=-1).fit(Xtr[SEL], ytr)
    pp = gs.best_estimator_.predict_proba(Xte[SEL])[:, 1]
    lo, hi = boot_ci(yv, pp, 1)
    en_iyi = "; ".join("%s=%s" % (k.replace("m__", ""), v) for k, v in gs.best_params_.items())
    satir.append(dict(model=ad, en_iyi_ayar=en_iyi, cv_auroc=gs.best_score_, test_auroc=roc_auc_score(yv, pp), lo=lo, hi=hi))
    P("   en iyi: %s | CV %.3f | test %.3f (%.3f-%.3f)" % (en_iyi, gs.best_score_, satir[-1]["test_auroc"], lo, hi))
SON = pd.DataFrame(satir)
P("")
P("SONUC (birincil analiz: LR C=0.01 test AUROC %.3f)" % AUC)
for _, r in SON.iterrows():
    P("   %-24s test %.3f (%.3f-%.3f)  CV %.3f  [%s]" % (r.model, r.test_auroc, r.lo, r.hi, r.cv_auroc, r.en_iyi_ayar))

# ---------------------------------------------------------------------------
# EK ANALIZ 2: ic ice model (yatak basi 7 degisken + 20 laboratuvar degiskeni)
# ---------------------------------------------------------------------------
import statsmodels.api as sm
KLINIK = [c for c in ["YAŞ", "CİNSİYET", "bmı", "sistolık kan basıncı", "diastolik kan basıncı", "sigara", "diyabet süresi"] if c in X.columns]
pk = boru().fit(Xtr[KLINIK], ytr).predict_proba(Xte[KLINIK])[:, 1]
IC = SEL + [c for c in KLINIK if c not in SEL]
pn = boru().fit(Xtr[IC], ytr).predict_proba(Xte[IC])[:, 1]
def fark_ci(a, b, seed=7):
    rng = np.random.RandomState(seed); dd = []
    for _ in range(NBOOT):
        i = rng.randint(0, len(yv), len(yv))
        if len(np.unique(yv[i])) > 1: dd.append(roc_auc_score(yv[i], a[i]) - roc_auc_score(yv[i], b[i]))
    dd = np.array(dd); return roc_auc_score(yv, a) - roc_auc_score(yv, b), np.percentile(dd, 2.5), np.percentile(dd, 97.5), (dd > 0).mean()
P("")
P("IC ICE MODEL (%d degisken = 20 lab/secili + yatak basi):" % len(IC))
P("   AUROC %.3f (%.3f-%.3f)" % (roc_auc_score(yv, pn), *boot_ci(yv, pn, 1)))
P("   ic ice - yatak basi : %+.3f (%.3f, %.3f)  P(>0)=%.2f" % fark_ci(pn, pk))
P("   ic ice - birincil   : %+.3f (%.3f, %.3f)  P(>0)=%.2f" % fark_ci(pn, p))
# olabilirlik orani testi (egitim verisinde, cezasiz lojistik; yalnizca destekleyici)
def ll(cols):
    Z = SimpleImputer(strategy="median").fit(Xtr[cols]).transform(Xtr[cols]); Z = StandardScaler().fit_transform(Z)
    return sm.Logit(ytr.values, sm.add_constant(Z)).fit(disp=0).llf
lr = 2 * (ll(IC) - ll(KLINIK)); dfree = len(IC) - len(KLINIK)
from scipy.stats import chi2
P("   LR testi (egitim, cezasiz): chi2 = %.1f, sd = %d, p = %.2g" % (lr, dfree, chi2.sf(lr, dfree)))

# ---------------------------------------------------------------------------
# EK ANALIZ 3: cinsiyet modele zorla eklenince
# ---------------------------------------------------------------------------
SX = SEL + (["CİNSİYET"] if "CİNSİYET" not in SEL else [])
ps_ = boru().fit(Xtr[SX], ytr).predict_proba(Xte[SX])[:, 1]
P("")
P("CINSIYET EKLI MODEL: AUROC %.3f (%.3f-%.3f) | birincile fark %+.3f (%.3f, %.3f)" % ((roc_auc_score(yv, ps_), *boot_ci(yv, ps_, 1)) + fark_ci(ps_, p)[:3]))
cs = Xte["CİNSİYET"].values
def citl(yy, pp):
    lg = np.log(pp / (1 - pp))
    return sm.GLM(yy, np.ones((len(yy), 1)), family=sm.families.Binomial(), offset=lg).fit().params[0]
gruplar = sorted(pd.unique(cs[~pd.isna(cs)]))
for g in (gruplar if len(gruplar) <= 3 else []):
    m = cs == g
    if m.sum() < 20 or len(np.unique(yv[m])) < 2: continue
    P("   CINSIYET=%s (n=%d): AUROC birincil %.3f / cinsiyetli %.3f | CITL birincil %+.3f / cinsiyetli %+.3f"
      % (g, m.sum(), roc_auc_score(yv[m], p[m]), roc_auc_score(yv[m], ps_[m]), citl(yv[m], p[m]), citl(yv[m], ps_[m])))
