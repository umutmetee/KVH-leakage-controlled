# -*- coding: utf-8 -*-
"""
00_sekil_verisi_uret.py
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
# HESAPLAR
# ---------------------------------------------------------------------------
P("Modeller egitiliyor...")
MOD = {
 "Logistic Regression": LogisticRegression(C=C, max_iter=2000),
 "Naive Bayes": GaussianNB(),
 "Support Vector Machine": SVC(C=1, gamma="scale", probability=True, random_state=SEED),
 "AdaBoost": AdaBoostClassifier(random_state=SEED),
 "Extra Trees": ExtraTreesClassifier(n_estimators=400, random_state=SEED),
 "Random Forest": RandomForestClassifier(n_estimators=400, random_state=SEED),
 "Hist. Gradient Boosting": HistGradientBoostingClassifier(random_state=SEED),
 "K-Nearest Neighbours": KNeighborsClassifier(n_neighbors=7),
 "Gradient Boosting": GradientBoostingClassifier(random_state=SEED),
 "Multilayer Perceptron": MLPClassifier(hidden_layer_sizes=(64,), max_iter=1000, random_state=SEED),
 "Decision Tree": DecisionTreeClassifier(max_depth=5, random_state=SEED),
}
Pp = {n: boru(e).fit(Xtr[SEL], ytr).predict_proba(Xte[SEL])[:, 1] for n, e in MOD.items()}
baz = [("lr", boru()), ("nb", boru(GaussianNB())),
       ("rf", boru(RandomForestClassifier(n_estimators=400, random_state=SEED)))]
for n, e in [("Soft Voting", VotingClassifier(baz, voting="soft")),
             ("Stacking", StackingClassifier(baz, final_estimator=LogisticRegression(max_iter=2000), cv=5))]:
    e.fit(Xtr[SEL], ytr); Pp[n] = e.predict_proba(Xte[SEL])[:, 1]
mrow = []
for n, pp in Pp.items():
    lo, hi = boot_ci(yv, pp, 1) if n in MOD else (np.nan, np.nan)
    mrow.append(dict(model=n, auc=roc_auc_score(yv, pp), lo=lo, hi=hi))
MR = pd.DataFrame(mrow).sort_values("auc", ascending=True); 

P("Katsayi onyuklemesi...")
rng = np.random.RandomState(SEED); bs = np.full((NBOOT, K), np.nan)
for b in range(NBOOT):
    i = rng.randint(0, len(tr), len(tr))
    if len(np.unique(ytr.values[i])) < 2: continue
    bs[b] = boru().fit(Xtr[SEL].iloc[i], pd.Series(ytr.values[i])).named_steps["m"].coef_[0]
beta = fin.named_steps["m"].coef_[0]; b0 = fin.named_steps["m"].intercept_[0]
EQ = pd.DataFrame({"var": SEL, "F": [Frank[s] for s in SEL], "beta": beta,
                   "lo": np.nanpercentile(bs, 2.5, 0), "hi": np.nanpercentile(bs, 97.5, 0)})


P("k taramasi...")
krow = []
NEV = int(ytr.sum())
for k in [10, 15, 20, 30, 40]:
    a = []
    for ti, vi in skf.split(Xtr, ytr):
        Xi, yi = Xtr.iloc[ti], ytr.iloc[ti]
        s = tekillestir(siralama_anova(Xi, yi), k, list(Xi.columns))
        a.append(roc_auc_score(ytr.iloc[vi], boru().fit(Xi[s], yi).predict_proba(Xtr[s].iloc[vi])[:, 1]))
    krow.append(dict(k=k, cv=np.mean(a), sd=np.std(a), epv=NEV / k))
KR = pd.DataFrame(krow); 

P("20 bolme...")
au, frq = [], {}
for s_ in range(20):
    t2, e2 = train_test_split(idx, test_size=0.2, stratify=y, random_state=s_)
    X2, y2 = X.iloc[t2], y.iloc[t2]
    s2 = tekillestir(siralama_anova(X2, y2), K, list(X2.columns))
    for c in s2: frq[c] = frq.get(c, 0) + 1
    au.append(roc_auc_score(y.iloc[e2], boru().fit(X2[s2], y2).predict_proba(X.iloc[e2][s2])[:, 1]))

FR = pd.Series(frq)

P("Ogrenme egrisi...")
ts, trs, vas = learning_curve(boru(), Xtr[SEL], ytr, cv=skf, scoring="roc_auc", train_sizes=np.linspace(.2, 1, 6))

P("Klinik referans ve duyarlilik analizleri...")
KLINIK = [c for c in ["YAŞ", "CİNSİYET", "bmı", "sistolık kan basıncı", "diastolik kan basıncı", "sigara", "diyabet süresi"] if c in X.columns]
pk = boru().fit(Xtr[KLINIK], ytr).predict_proba(Xte[KLINIK])[:, 1]
AK = roc_auc_score(yv, pk)
rng = np.random.RandomState(7); dd = []
for _ in range(NBOOT):
    i = rng.randint(0, len(yv), len(yv))
    if len(np.unique(yv[i])) > 1: dd.append(roc_auc_score(yv[i], p[i]) - roc_auc_score(yv[i], pk[i]))
dd = np.array(dd)

def altgrup(maske, etiket=None):
    yy = y if etiket is None else pd.Series(etiket.astype(int))
    Xs, ys = X[maske].reset_index(drop=True), yy[maske].reset_index(drop=True)
    t2, e2 = train_test_split(np.arange(len(Xs)), test_size=0.2, stratify=ys, random_state=SEED)
    X2, y2 = Xs.iloc[t2], ys.iloc[t2]
    s2 = tekillestir(siralama_anova(X2, y2), K, list(X2.columns))
    pp = boru().fit(X2[s2], y2).predict_proba(Xs.iloc[e2][s2])[:, 1]; yy2 = ys.iloc[e2].values
    lo, hi = boot_ci(yy2, pp, 7)
    return roc_auc_score(yy2, pp), lo, hi
tum = np.ones(len(X), bool)
# ESK_ = onceki (eski) tahlil, YEN_ = en son tahlil
ESKp = [c for c in Xtr.columns if str(c).startswith("ESK_")] + [c for c in STATIK if c in Xtr.columns]
sE = tekillestir(siralama_anova(Xtr[ESKp], ytr), K, ESKp)
pb = boru().fit(Xtr[sE], ytr).predict_proba(Xte[sE])[:, 1]
YENp = [c for c in Xtr.columns if str(c).startswith("YEN_")] + [c for c in STATIK if c in Xtr.columns]
sY = tekillestir(siralama_anova(Xtr[YENp], ytr), K, YENp)
py = boru().fit(Xtr[sY], ytr).predict_proba(Xte[sY])[:, 1]
HI = [s for s in SEL if X[s].isna().mean() > 0.30]
Xi2 = X.copy()
for s in HI: Xi2["EKSIK_" + s] = X[s].isna().astype(int)
IND = ["EKSIK_" + s for s in HI]
pm = boru().fit(Xi2.iloc[tr][SEL + IND], ytr).predict_proba(Xi2.iloc[te][SEL + IND])[:, 1]
# secim dahil iyimserlik
gor = roc_auc_score(ytr, fin.predict_proba(Xtr[SEL])[:, 1])
rng = np.random.RandomState(SEED); opt = []
for b in range(200):
    i = rng.randint(0, len(tr), len(tr)); Xb, yb = Xtr.iloc[i], ytr.iloc[i]
    if yb.nunique() < 2: continue
    sb = tekillestir(siralama_anova(Xb, yb), K, list(Xb.columns)); mb = boru().fit(Xb[sb], yb)
    opt.append(roc_auc_score(yb, mb.predict_proba(Xb[sb])[:, 1]) - roc_auc_score(ytr, mb.predict_proba(Xtr[sb])[:, 1]))
opt = np.array(opt)
ds = X["diyabet süresi"].values
SENS = [  # (en, tr, auc, lo, hi, grup)
 ("Primary analysis (20 variables)", "Birincil analiz (20 değişken)", AUC, *boot_ci(yv, p, 1), 0),
 ("Selection-inclusive optimism correction", "Seçim dâhil iyimserlik düzeltmesi", gor - opt.mean(), gor - np.percentile(opt, 97.5), gor - np.percentile(opt, 2.5), 0),
 ("Missingness indicators added", "Eksiklik göstergeleri eklenmiş", roc_auc_score(yv, pm), *boot_ci(yv, pm, 1), 0),
 ("Earlier measurements only", "Yalnızca önceki ölçümler", roc_auc_score(yv, pb), *boot_ci(yv, pb, 1), 1),
 ("Latest measurements only", "Yalnızca en son ölçümler", roc_auc_score(yv, py), *boot_ci(yv, py, 1), 1),
 ("Ejection fraction ≥ 50% subgroup", "Ejeksiyon fraksiyonu ≥ %50 altgrubu", *altgrup(~ef_), 1),
 ("Diabetes duration > 0 subgroup", "Diyabet süresi > 0 altgrubu", *altgrup(ds != 0), 1),
 ("Structural endpoint (LA/LVEDD/EF)", "Yapısal uç nokta (LA/LVEDD/EF)", *altgrup(tum, la | lv | ef_), 2),
 ("Electrical endpoint (QTc/QRS)", "Elektriksel uç nokta (QTc/QRS)", *altgrup(tum, qtc | qrs), 2),
 ("Severe endpoint (LVEDD/EF)", "Ağır uç nokta (LVEDD/EF)", *altgrup(tum, lv | ef_), 2),
 ("Bedside reference model (7 variables)", "Yatak başı referans model (7 değişken)", AK, *boot_ci(yv, pk, 1), 3),
]
SR = pd.DataFrame(SENS, columns=["en", "tr", "auc", "lo", "hi", "grup"])
for r in SENS: P("   %-45s %.3f [%.3f-%.3f]" % (r[0], r[2], r[3], r[4]))
# ---------------------------------------------------------------------------
# EK HESAPLAR (yalnizca sekiller icin)
# ---------------------------------------------------------------------------
FR_tum = FR.reindex(list(set(FR.index) | set(SEL))).fillna(0).astype(int)
Z = SimpleImputer(strategy="median").fit_transform(Xtr[SEL])
R = pd.DataFrame(np.corrcoef(Z, rowvar=False), index=SEL, columns=SEL)
sc = fin.named_steps["s"]
NOM = pd.DataFrame({"degisken": SEL, "beta": beta, "ortalama": sc.mean_, "ss": np.sqrt(sc.var_),
                    "p01": [np.percentile(X[v].dropna(), 1) for v in SEL],
                    "p99": [np.percentile(X[v].dropna(), 99) for v in SEL]})
mi = X.isna().mean() * 100
EKS = pd.DataFrame({"degisken": mi.index, "eksik_yuzde": mi.values, "nihai_modelde": [v in SEL for v in mi.index]})
ucn = pd.DataFrame({"LA": la, "LVEDD": lv, "EF<50%": ef_, "QTc": qtc, "QRS": qrs}).astype(int)
poz = ucn[ucn.sum(1) > 0]
KES = poz.value_counts().rename("n").reset_index()          # her kriter kombinasyonu ve hasta sayisi
OGR = pd.DataFrame({"egitim_n": ts, "egitim_ort": trs.mean(1), "egitim_ss": trs.std(1),
                    "cd_ort": vas.mean(1), "cd_ss": vas.std(1)})
TT = pd.DataFrame({"y": yv, "p_model": p, "p_referans": pk})
for n_, pp in Pp.items():
    TT["p_" + n_] = pp

OZ = pd.DataFrame([
    ("n_hasta", len(X)), ("n_olay", int(y.sum())), ("n_aday_degisken", X.shape[1]),
    ("n_egitim", len(tr)), ("olay_egitim", int(ytr.sum())), ("n_test", len(te)), ("olay_test", int(yv.sum())),
    ("auroc", AUC), ("tau", TAU), ("auroc_referans", AK), ("kesisim_b0", b0),
    ("n_uc_nokta_LA", int(la.sum())), ("n_uc_nokta_LVEDD", int(lv.sum())), ("n_uc_nokta_EF", int(ef_.sum())),
    ("n_uc_nokta_QTc", int(qtc.sum())), ("n_uc_nokta_QRS", int(qrs.sum())),
], columns=["ad", "deger"])

with pd.ExcelWriter(CIKTI) as w:
    OZ.to_excel(w, sheet_name="ozet", index=False)
    TT.to_excel(w, sheet_name="test_tahmin", index=False)
    EQ.to_excel(w, sheet_name="katsayilar", index=False)
    MR.to_excel(w, sheet_name="modeller_auroc", index=False)
    KR.to_excel(w, sheet_name="k_taramasi", index=False)
    pd.DataFrame({"bolme": range(20), "auroc": au}).to_excel(w, sheet_name="yirmi_bolme", index=False)
    pd.DataFrame({"degisken": FR_tum.index, "sayi": FR_tum.values,
                  "nihai_modelde": [v in SEL for v in FR_tum.index]}).to_excel(w, sheet_name="secilme_sikligi", index=False)
    OGR.to_excel(w, sheet_name="ogrenme_egrisi", index=False)
    pd.DataFrame({"fark": dd}).to_excel(w, sheet_name="fark_onyukleme", index=False)
    SR.to_excel(w, sheet_name="duyarlilik", index=False)
    EKS.to_excel(w, sheet_name="eksik_veri", index=False)
    R.to_excel(w, sheet_name="korelasyon", index=True)
    NOM.to_excel(w, sheet_name="nomogram", index=False)
    KES.to_excel(w, sheet_name="uc_nokta_kesisim", index=False)

P("")
P("KONTROL (makaledeki degerler parantez icinde):")
P("   AUROC %.3f (0.755) | tau %.3f (0.428) | referans %.3f | fark %+.3f (+0.058)" % (AUC, TAU, AK, AUC - AK))
P("   n %d / olay %d (931 / 371) | egitim %d (%d) | test %d (%d)" % (len(X), y.sum(), len(tr), ytr.sum(), len(te), yv.sum()))
P("   aday degisken %d (Sekil 1: 127) | eksik degeri olan %d (Sekil S1: 117)" % (X.shape[1], int((X.isna().mean() > 0).sum())))
P("Yazildi: %s" % CIKTI)
