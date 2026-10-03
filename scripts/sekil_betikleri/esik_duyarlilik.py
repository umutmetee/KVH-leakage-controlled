# -*- coding: utf-8 -*-
"""
esik_duyarlilik.py  (EK ANALIZ: uc nokta esikleri kilavuza tam esitlenirse / akla yatkin olmayan EKG degerleri)
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

# ---------------------------------------------------------------------------
# UC NOKTA TANIMI DUYARLILIK ANALIZI
# ---------------------------------------------------------------------------
SEL = tekillestir(siralama_anova(Xtr, ytr), K, list(Xtr.columns))
cins = num("CİNSİYET").values            # 1 = kadin, 2 = erkek (test setinde kadin n=92)
kadin = cins == 1
msa = num("max sol atr").values; mqrs = num("max qrs dur").values; mqtc = num("max qtc").values
P("")
P("SINIR DEGERLER (kac hastanin etiketi degisebilir):")
P("   LA tam 39 mm (kadin): %d | LA tam 41 mm (erkek): %d" % (((msa == 39) & kadin).sum(), ((msa == 41) & ~kadin).sum()))
P("   QRS tam 120 ms: %d" % (mqrs == 120).sum())
P("   QRS > 200 ms (akla yatkin degil): %d, bunlardan qrs abn isaretli: %d" % ((mqrs > 200).sum(), ((mqrs > 200) & qrs).sum()))
P("   QTc > 600 ms: %d | QTc 0 < x < 300 ms: %d" % ((mqtc > 600).sum(), ((mqtc > 0) & (mqtc < 300)).sum()))
la_k = np.where(kadin, msa >= 39, msa >= 41)                      # ASE/EACVI ust sinir 38/40 mm
qrs_k = (mqrs >= 120) & (mqrs <= 200)                             # >=120 ms; >200 ms hatali kabul
qrs_h = qrs & ~(mqrs > 200)                                       # yalnizca hatali QRS'ler cikarilir
TAN = {
 "Birincil tanim": y.values,
 "LA kilavuz esigi (>=39 / >=41 mm)": (la_k | lv | ef_ | qtc | qrs).astype(int),
 "QRS >200 ms hatali sayilirsa": (la | lv | ef_ | qtc | qrs_h).astype(int),
 "Ikisi + QRS >=120 ms": (la_k | lv | ef_ | qtc | qrs_k).astype(int),
}
def calis(yy):
    yy = pd.Series(yy)
    t2, e2 = train_test_split(idx, test_size=0.2, stratify=yy, random_state=SEED)
    X2, y2 = X.iloc[t2], yy.iloc[t2]
    s2 = tekillestir(siralama_anova(X2, y2), K, list(X2.columns))
    pp = boru().fit(X2[s2], y2).predict_proba(X.iloc[e2][s2])[:, 1]; ye = yy.iloc[e2].values
    lo, hi = boot_ci(ye, pp, 1)
    return roc_auc_score(ye, pp), lo, hi, len(set(s2) & set(SEL))
P("")
P("SONUC (ayni boru hatti, yeni etiketle bastan):")
for ad, yy in TAN.items():
    a, lo, hi, ort = calis(yy)
    P("   %-36s pozitif %d (%.1f%%) | degisen %d | AUROC %.3f (%.3f-%.3f) | birincil 20 ile ortak %d"
      % (ad, yy.sum(), 100 * yy.mean(), (yy != y.values).sum(), a, lo, hi, ort))
