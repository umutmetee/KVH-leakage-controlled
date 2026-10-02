# -*- coding: utf-8 -*-
"""
ek_hakem_analizleri_2.py  (EK ANALIZLER 2 - hakem M5, M6, M7, M8)
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

# ===========================================================================
# EK ANALIZLER 2  (ciktiyi oldugu gibi Claude'a yapistirin)
# ===========================================================================
import statsmodels.api as sm
def fark_ci(a, b, seed=7):
    rng = np.random.RandomState(seed); dd = []
    for _ in range(NBOOT):
        i = rng.randint(0, len(yv), len(yv))
        if len(np.unique(yv[i])) > 1: dd.append(roc_auc_score(yv[i], a[i]) - roc_auc_score(yv[i], b[i]))
    return roc_auc_score(yv, a) - roc_auc_score(yv, b), np.percentile(dd, 2.5), np.percentile(dd, 97.5)
def kal(yy, pp):
    pp = np.clip(pp, 1e-6, 1 - 1e-6); lg = np.log(pp / (1 - pp))
    citl = sm.GLM(yy, np.ones((len(yy), 1)), family=sm.families.Binomial(), offset=lg).fit().params[0]
    slope = sm.GLM(yy, sm.add_constant(lg), family=sm.families.Binomial()).fit().params[1]
    return citl, slope
def esik_metrik(yy, pp, tau):
    t = pp >= tau; tp = (t & (yy == 1)).sum(); tn = (~t & (yy == 0)).sum()
    return tp / (yy == 1).sum(), tn / (yy == 0).sum()
def degerlendir(ad, havuz, Xtr_=None, Xte_=None, ytr_=None, yte_=None, fark=True):
    Xtr_ = Xtr if Xtr_ is None else Xtr_; Xte_ = Xte if Xte_ is None else Xte_
    ytr_ = ytr if ytr_ is None else ytr_; yy = yv if yte_ is None else yte_.values
    sel = tekillestir(siralama_anova(Xtr_[havuz], ytr_), K, havuz)
    pp = boru().fit(Xtr_[sel], ytr_).predict_proba(Xte_[sel])[:, 1]
    o = cross_val_predict(boru(), Xtr_[sel], ytr_, cv=skf, method="predict_proba")[:, 1]
    f1, t1, h1 = roc_curve(ytr_, o); tau = h1[np.argmax(t1 - f1)]
    lo, hi = boot_ci(yy, pp, 1); ci, sl = kal(yy, pp); se, sp = esik_metrik(yy, pp, tau)
    P("")
    P("[%s] havuz=%d degisken, secilen=%d" % (ad, len(havuz), len(sel)))
    P("   AUROC %.3f (%.3f-%.3f) | CITL %+.3f | egim %.3f | tau %.3f | duyarlilik %.3f | ozgulluk %.3f"
      % (roc_auc_score(yy, pp), lo, hi, ci, sl, tau, se, sp))
    if fark: P("   birincilden fark: %+.3f (%.3f, %.3f)" % fark_ci(pp, p))
    P("   secilenler: " + "; ".join(sel))
    return sel, pp

HAVUZ = list(Xtr.columns)
P("")
P("BIRINCIL kontrol: AUROC %.3f (beklenen 0.755)" % AUC)
P("Birincil secilenler: " + "; ".join(SEL))

# --- M6: her analit icin tek zaman noktasi ---------------------------------
STAT = [c for c in HAVUZ if not str(c).startswith(("ESK_", "YEN_"))]
degerlendir("M6a YALNIZ ONCEKI (ESK_) + statik", [c for c in HAVUZ if str(c).startswith("ESK_")] + STAT)
degerlendir("M6b YALNIZ SON (YEN_) + statik", [c for c in HAVUZ if str(c).startswith("YEN_")] + STAT)

# --- M7: eksiklik esigi (egitim verisinde hesaplanir) -----------------------
eks = Xtr.isna().mean()
for e in (0.50, 0.30, 0.20):
    degerlendir("M7 eksiklik <= %%%d" % int(e * 100), [c for c in HAVUZ if eks[c] <= e])
P("   Birincil secilenlerin egitim eksiklik oranlari: " +
  "; ".join("%s=%.1f%%" % (c, 100 * eks[c]) for c in SEL))

# --- M8: sonuc x cinsiyet tabakali bolme -------------------------------------
cins = X["CİNSİYET"].where(X["CİNSİYET"].isin([1, 2]), 0).astype(int).astype(str)
tab = y.astype(str) + "_" + cins
az = tab.value_counts(); tab = tab.where(~tab.isin(az[az < 5].index), y.astype(str))
tr2, te2 = train_test_split(idx, test_size=0.2, stratify=tab, random_state=SEED)
yte2 = y.iloc[te2]
P("")
P("M8 tabakali bolme: test n=%d, olay=%d, kadin=%d" % (len(te2), yte2.sum(), (X["CİNSİYET"].iloc[te2] == 1).sum()))
sel2, p2 = degerlendir("M8 sonuc+cinsiyet tabakali bolme", HAVUZ, X.iloc[tr2], X.iloc[te2], y.iloc[tr2], yte2, fark=False)
SX2 = sel2 + (["CİNSİYET"] if "CİNSİYET" not in sel2 else [])
p2s = boru().fit(X.iloc[tr2][SX2], y.iloc[tr2]).predict_proba(X.iloc[te2][SX2])[:, 1]
y2 = yte2.values; c2 = X["CİNSİYET"].iloc[te2].values
P("   +cinsiyet zorlanmis: AUROC %.3f (%.3f-%.3f)" % ((roc_auc_score(y2, p2s),) + tuple(boot_ci(y2, p2s, 1))))
for g in (1, 2):
    m = c2 == g
    if m.sum() < 10: continue
    P("   CINSIYET=%d (n=%d): CITL %+.3f / cinsiyetli %+.3f" % (g, m.sum(), kal(y2[m], p2[m])[0], kal(y2[m], p2s[m])[0]))

# --- M5: tum veriyle (n=931) gelistirilen denklem ---------------------------
selA = tekillestir(siralama_anova(X, y), K, HAVUZ)
fA = boru().fit(X[selA], y)
im, sc, lr_ = fA.named_steps["i"], fA.named_steps["s"], fA.named_steps["m"]
P("")
P("M5 TUM VERI DENKLEMI (n=%d, olay=%d)  sabit=%.4f" % (len(y), y.sum(), lr_.intercept_[0]))
P("   ortak degisken (birincil ile): %d / %d" % (len(set(selA) & set(SEL)), K))
for c, b, mu, sd, md in zip(selA, lr_.coef_[0], sc.mean_, sc.scale_, im.statistics_):
    P("   %-40s beta=%+.4f  ort=%.4g  ss=%.4g  medyan=%.4g%s" % (c, b, mu, sd, md, "" if c in SEL else "  [YENI]"))
P("")
P("BITTI.")
