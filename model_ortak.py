# -*- coding: utf-8 -*-
"""
model_ortak.py  -  Model_*.py betiklerinin ortak parcasi (dogrudan calistirilmaz).
Veriyi okur, makaledeki boru hattini kurar (SEED=42, K=20, C=0.01, ANOVA-F +
analit ailesi tekillestirme, yalnizca egitim verisinde) ve her algoritma icin
Tablo 3 / Tablo S1 satirini hesaplayip model_sonuclari.xlsx dosyasina yazar.
Boru hatti KVH_TAM_ANALIZ.py ile birebir aynidir.
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
CIKTI = os.path.join(KLASOR, "model_sonuclari.xlsx")
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
P("Birincil model kontrol: AUROC %.3f | tau %.3f (beklenen 0.755 / 0.428)" % (AUC, TAU))

from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix
def esik_youden(p_oof, y_oof):
    f, t, th = roc_curve(y_oof, p_oof)
    return th[np.argmax(t - f)]
KLINIK = [c for c in ["YAŞ", "CİNSİYET", "bmı", "sistolık kan basıncı", "diastolik kan basıncı",
                      "sigara", "diyabet süresi"] if c in X.columns]

def calistir(no, ad, tahminci, degiskenler=None, topluluk=False, yer="Makale, Tablo 3"):
    """Tek algoritmayi egitir, test kumesinde degerlendirir, sonucu yazar.
    topluluk=True: Soft Voting / Stacking; esik birincil LR esigi (tau) olur (KVH_TAM_ANALIZ ile ayni)."""
    cols = SEL if degiskenler is None else degiskenler
    model = tahminci if topluluk else boru(tahminci)
    pp = model.fit(Xtr[cols], ytr).predict_proba(Xte[cols])[:, 1]
    if topluluk:
        tau = TAU
    else:
        oof_ = cross_val_predict(boru(tahminci), Xtr[cols], ytr, cv=skf, method="predict_proba")[:, 1]
        tau = esik_youden(oof_, ytr)
    tn, fp, fn, tp = confusion_matrix(yv, (pp >= tau).astype(int)).ravel()
    lo, hi = boot_ci(yv, pp, 1)
    r = dict(No=no, Model=ad, Yer=yer, Degisken_sayisi=len(cols), AUROC=roc_auc_score(yv, pp), CI_alt=lo, CI_ust=hi,
             AUPRC=average_precision_score(yv, pp), F1=2*tp/(2*tp+fp+fn), Accuracy=(tp+tn)/len(yv),
             Sensitivity=tp/(tp+fn), Specificity=tn/(tn+fp), PPV=tp/(tp+fp) if tp+fp else np.nan,
             NPV=tn/(tn+fn) if tn+fn else np.nan,
             MCC=(tp*tn-fp*fn)/np.sqrt(max((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn), 1)),
             Brier=brier_score_loss(yv, pp), Esik_tau=tau, TN=tn, FP=fp, FN=fn, TP=tp)
    P("")
    P("[%s] %s  (%s)" % (no, ad, yer))
    P("   AUROC %.3f (%.3f-%.3f) | AUPRC %.3f | F1 %.3f | Acc %.3f | Duy %.3f | Ozg %.3f | PPV %.3f | NPV %.3f | MCC %.3f | Brier %.3f | tau %.3f"
      % (r["AUROC"], lo, hi, r["AUPRC"], r["F1"], r["Accuracy"], r["Sensitivity"], r["Specificity"],
         r["PPV"], r["NPV"], r["MCC"], r["Brier"], tau))
    P("   Karisiklik: TN=%d FP=%d FN=%d TP=%d" % (tn, fp, fn, tp))
    yaz(no, r, pp)
    return r

def yaz(no, r, pp):
    """Sonucu model_sonuclari.xlsx'e yazar: 'ozet' sayfasi + modele ait sayfa (hasta kimligi yok)."""
    ozet = pd.DataFrame()
    if os.path.exists(CIKTI):
        try: ozet = pd.read_excel(CIKTI, sheet_name="ozet")
        except Exception: ozet = pd.DataFrame()
    if len(ozet): ozet = ozet[ozet["No"].astype(str) != str(no)]
    ozet = pd.concat([ozet, pd.DataFrame([r])], ignore_index=True)
    sira = lambda s: (1 if str(s).startswith("S") else 0, int(re.sub(r"\D", "", str(s)) or 0))
    ozet = ozet.iloc[sorted(range(len(ozet)), key=lambda i: sira(ozet["No"].iloc[i]))]
    mod = "a" if os.path.exists(CIKTI) else "w"
    kw = dict(if_sheet_exists="replace") if mod == "a" else {}
    with pd.ExcelWriter(CIKTI, engine="openpyxl", mode=mod, **kw) as w:
        ozet.to_excel(w, sheet_name="ozet", index=False)
        pd.DataFrame({"gercek": yv, "olasilik": pp}).to_excel(w, sheet_name=("Model_%s" % no)[:31], index=False)
    P("   -> %s (sayfa: ozet, Model_%s)" % (os.path.basename(CIKTI), no))
