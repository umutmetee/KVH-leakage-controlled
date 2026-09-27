# -*- coding: utf-8 -*-
"""
KVH_REVIZYON_EK.py  (27.09.2026)
Kalayci revizyon plani v2'de acik kalan analizler. Boru hatti KVH_SEKILLER.py /
KVH_TAM_ANALIZ.py ile birebir aynidir (SEED=42, C=0.01, K=20).

KULLANIM (07_Analiz klasorunde):   python KVH_REVIZYON_EK.py
Ciktilar: cikti_revizyon/revizyon_rapor.txt  (+ CSV dosyalari)
Sure: birkac dakika.

R1  Stacking ve Soft Voting icin %95 onyukleme GA (plan A4.5)
R2  Platt sonrasi kalibrasyon egimi, CITL, ECE (plan A4.3b)
R3  Eslestirilmis DeLong testi: LR'ye karsi diger modeller ve referans (plan 4.4)
R4  Nihai 20 degiskende VIF ve trombosit / glisemik korelasyonlar (plan Y2)
R5  eGFR hangi CKD-EPI denklemiyle hesaplanmis? 2009 ve 2021 ile karsilastirma
R6  Kohort bilesimi: diyabet suresi > 0 olan hasta sayisi (plan M2)
"""
import os, re, sys, warnings
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
from sklearn.metrics import roc_auc_score, roc_curve, precision_recall_curve, average_precision_score, confusion_matrix
import statsmodels.api as sm
KLASOR = os.path.dirname(os.path.abspath(__file__))
VERI = os.path.join(KLASOR, "sizintisiz_veri.xlsx")
RAW = os.path.join(KLASOR, "aiveri2026_haz.xlsx")
OUT = os.path.join(KLASOR, "cikti_revizyon")
SEED, K, C = 42, 20, 0.01
NBOOT = int(os.environ.get("KVH_NBOOT", 2000))
STATIK = ["diyabet süresi", "YAŞ", "CİNSİYET", "sigara", "sistolık kan basıncı",
          "diastolik kan basıncı", "boy", "kılo", "bmı"]
os.makedirs(OUT, exist_ok=True)
_LOG = []
def P(s=""):
    print(s); _LOG.append(str(s))
def csv(df, ad): df.to_csv(os.path.join(OUT, ad + ".csv"), index=False)
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

from sklearn.calibration import CalibratedClassifierCV
from scipy import stats

def BASLIK(s):
    P(""); P("=" * 78); P(s); P("=" * 78)

def ece(pp):
    q = pd.qcut(pp, 10, duplicates="drop")
    return sum(abs(yv[q == g].mean() - pp[q == g].mean()) * (q == g).sum() for g in q.categories) / len(yv)
def kal(pp):
    lg = np.log(pp / (1 - pp))
    citl = sm.GLM(yv, np.ones((len(yv), 1)), family=sm.families.Binomial(), offset=lg).fit().params[0]
    egim = sm.Logit(yv, sm.add_constant(lg)).fit(disp=0).params[1]
    return citl, egim, ece(pp), np.mean((pp - yv) ** 2)

# ---- modeller (KVH_SEKILLER.py ile ayni tanimlar) ----
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
P("Modeller egitiliyor...")
Pp = {n: boru(e).fit(Xtr[SEL], ytr).predict_proba(Xte[SEL])[:, 1] for n, e in MOD.items()}
baz = [("lr", boru()), ("nb", boru(GaussianNB())),
       ("rf", boru(RandomForestClassifier(n_estimators=400, random_state=SEED)))]
for n, e in [("Soft Voting", VotingClassifier(baz, voting="soft")),
             ("Stacking", StackingClassifier(baz, final_estimator=LogisticRegression(max_iter=2000), cv=5))]:
    e.fit(Xtr[SEL], ytr); Pp[n] = e.predict_proba(Xte[SEL])[:, 1]

# ---------------------------------------------------------------------------
BASLIK("R1. TOPLULUK MODELLERI ICIN %95 ONYUKLEME GA (Tablo III'te eksik olan)")
P("Kontrol: LR GA makalede 0.681-0.824 (ayni tohumla ayni cikmali)")
r1 = []
for n in ["Logistic Regression", "Stacking", "Soft Voting"]:
    lo, hi = boot_ci(yv, Pp[n], 1)
    r1.append(dict(model=n, auroc=roc_auc_score(yv, Pp[n]), lo=lo, hi=hi,
                   auprc=average_precision_score(yv, Pp[n])))
    P("   %-22s AUROC %.3f  (%%95 GA %.3f-%.3f)  AUPRC %.3f" % (n, r1[-1]["auroc"], lo, hi, r1[-1]["auprc"]))
csv(pd.DataFrame(r1), "R1_topluluk_ga")

# ---------------------------------------------------------------------------
BASLIK("R2. PLATT SONRASI KALIBRASYON (egim 1'e yaklasiyor mu?)")
pc = CalibratedClassifierCV(boru(), method="sigmoid", cv=skf).fit(Xtr[SEL], ytr).predict_proba(Xte[SEL])[:, 1]
lgt = lambda v: np.log(v / (1 - v))
pl = LogisticRegression(C=1e6, max_iter=2000).fit(lgt(oof).reshape(-1, 1), ytr)
pp_oof = pl.predict_proba(lgt(p).reshape(-1, 1))[:, 1]
P("Kontrol: ham model makalede CITL 0.000, egim 1.276, ECE 0.056, Brier 0.194")
r2 = []
for ad_, pp in [("Ham model (yayimlanan denklem)", p),
                ("Platt, CalibratedClassifierCV (5 model ort.)", pc),
                ("Platt, tek model + kat-disi sigmoid", pp_oof)]:
    c_, e_, ec_, b_ = kal(pp)
    r2.append(dict(yontem=ad_, citl=c_, egim=e_, ece=ec_, brier=b_, auroc=roc_auc_score(yv, pp)))
    P("   %-46s CITL %+.3f  egim %.3f  ECE %.3f  Brier %.3f  AUROC %.3f" % (ad_, c_, e_, ec_, b_, r2[-1]["auroc"]))
P("   Platt katsayilari (tek model): a = %.4f, b = %.4f  [p_kal = 1/(1+exp(-(a + b*logit(p))))]"
  % (pl.intercept_[0], pl.coef_[0][0]))
csv(pd.DataFrame(r2), "R2_platt_kalibrasyon")

# ---------------------------------------------------------------------------
BASLIK("R3. ESLESTIRILMIS DeLONG TESTI (ayni 187 test hastasi)")
def _mid(x):
    J = np.argsort(x); Z = x[J]; N = len(x); T = np.zeros(N); i = 0
    while i < N:
        j = i
        while j < N and Z[j] == Z[i]: j += 1
        T[i:j] = 0.5 * (i + j - 1); i = j
    T2 = np.empty(N); T2[J] = T + 1; return T2
def delong(yy, a, b):
    o = np.argsort(-yy); yy = yy[o]; S = np.vstack([a[o], b[o]]); m = int(yy.sum()); n = len(yy) - m
    tx = np.array([_mid(s[:m]) for s in S]); ty = np.array([_mid(s[m:]) for s in S]); tz = np.array([_mid(s) for s in S])
    auc = tz[:, :m].sum(1) / m / n - (m + 1.0) / 2.0 / n
    v01 = (tz[:, :m] - tx) / n; v10 = 1.0 - (tz[:, m:] - ty) / m
    cov = np.cov(v01) / m + np.cov(v10) / n
    d = auc[0] - auc[1]; se = np.sqrt(cov[0, 0] + cov[1, 1] - 2 * cov[0, 1])
    return auc[0], auc[1], d, d - 1.96 * se, d + 1.96 * se, 2 * stats.norm.sf(abs(d) / se)
KLINIK = [c for c in ["YAŞ", "CİNSİYET", "bmı", "sistolık kan basıncı", "diastolik kan basıncı", "sigara", "diyabet süresi"] if c in X.columns]
pk = boru().fit(Xtr[KLINIK], ytr).predict_proba(Xte[KLINIK])[:, 1]
r3 = []
P("   %-26s %7s %7s %8s %18s %7s" % ("Karsilastirma (LR - X)", "LR", "X", "fark", "%95 GA", "p"))
for n, pp in list(Pp.items()) + [("Bedside reference (7 var.)", pk)]:
    if n == "Logistic Regression": continue
    a1, a2, dd_, lo, hi, pv = delong(yv, p, pp)
    r3.append(dict(karsi=n, auc_lr=a1, auc_x=a2, fark=dd_, lo=lo, hi=hi, p=pv))
    P("   %-26s %7.3f %7.3f %+8.3f   %+.3f / %+.3f %7.3f" % (n, a1, a2, dd_, lo, hi, pv))
csv(pd.DataFrame(r3), "R3_delong")
P("   Not: referans karsilastirmasinda makale eslestirilmis onyukleme veriyor (+0.058, -0.013/+0.132);")
P("   DeLong ayni soruya parametrik yanit verir, ikisi birlikte raporlanabilir.")

# ---------------------------------------------------------------------------
BASLIK("R4. VIF (nihai 20 degisken) VE AILE KORELASYONLARI")
Z = pd.DataFrame(StandardScaler().fit_transform(SimpleImputer(strategy="median").fit_transform(Xtr[SEL])), columns=SEL)
Rm = np.corrcoef(Z.values, rowvar=False); VIF = np.diag(np.linalg.inv(Rm))
vt = pd.DataFrame({"degisken": SEL, "VIF": VIF}).sort_values("VIF", ascending=False)
for _, r in vt.iterrows(): P("   %-32s VIF %.2f" % (r.degisken, r.VIF))
P("   Maksimum VIF: %.2f (makalede 3.1)" % VIF.max())
csv(vt, "R4_vif")
def kor(ad1, ad2, veri):
    a = [c for c in veri.columns if c == ad1]; b = [c for c in veri.columns if c == ad2]
    if not a or not b: return None
    m = veri[[a[0], b[0]]].dropna()
    return np.corrcoef(m.iloc[:, 0], m.iloc[:, 1])[0, 1], len(m)
P("   Ham veride (eksiksiz ciftler) Pearson r:")
for c1, c2 in [("YEN_PLT", "ESK_PCT"), ("YEN_PLT", "YEN_P-LCR"), ("ESK_PCT", "YEN_P-LCR"),
               ("ESK_PLT", "ESK_PCT"), ("YEN_Glukoz", "ESK_Tokluk Kan Şekeri (TKŞ)"),
               ("YEN_Glukoz", "ESK_HBA1C (%)"), ("ESK_Tokluk Kan Şekeri (TKŞ)", "ESK_HBA1C (%)")]:
    k_ = kor(c1, c2, Xtr)
    if k_: P("      %-30s ~ %-30s r = %.3f (n = %d)" % (c1, c2, k_[0], k_[1]))

# ---------------------------------------------------------------------------
BASLIK("R5. eGFR: CKD-EPI 2009 MU 2021 MI?")
cin = pd.to_numeric(X["CİNSİYET"], errors="coerce") if "CİNSİYET" in X.columns else None   # 1 kadin, 2 erkek
yas = pd.to_numeric(X["YAŞ"], errors="coerce")
def ckd(scr, age, kadin, yil):
    if yil == 2009:
        k = np.where(kadin, 0.7, 0.9); a = np.where(kadin, -0.329, -0.411)
        return 141 * np.minimum(scr / k, 1) ** a * np.maximum(scr / k, 1) ** -1.209 * 0.993 ** age * np.where(kadin, 1.018, 1)
    k = np.where(kadin, 0.7, 0.9); a = np.where(kadin, -0.241, -0.302)
    return 142 * np.minimum(scr / k, 1) ** a * np.maximum(scr / k, 1) ** -1.200 * 0.9938 ** age * np.where(kadin, 1.012, 1)
kreat = [c for c in X.columns if "kreatinin" in str(c).lower()]
P("   Kreatinin sutunlari: %s" % kreat)
r5 = []
for on in ["YEN_", "ESK_"]:
    ks = [c for c in kreat if str(c).startswith(on)]; gs = [c for c in X.columns if str(c).startswith(on) and "tgfr" in str(c).lower()]
    if not ks or not gs or cin is None: continue
    scr = pd.to_numeric(X[ks[0]], errors="coerce"); kay = pd.to_numeric(X[gs[0]], errors="coerce")
    m = scr.notna() & kay.notna() & yas.notna() & cin.notna() & (scr > 0)
    for yil in (2009, 2021):
        h = ckd(scr[m].values, yas[m].values, (cin[m] == 1).values, yil)
        fark = np.abs(h - kay[m].values)
        r5.append(dict(olcum=on, denklem=yil, n=int(m.sum()), MAE=fark.mean(), medyan_fark=np.median(fark),
                       yuzde_2_birim_icinde=100 * (fark <= 2).mean()))
        P("   %s  CKD-EPI %d: n=%d  ortalama mutlak fark %.2f  medyan %.2f  |fark|<=2 olanlar %%%.1f"
          % (on, yil, m.sum(), fark.mean(), np.median(fark), 100 * (fark <= 2).mean()))
csv(pd.DataFrame(r5), "R5_ckd_epi")
P("   Yorum: kayitli eGFR'ye hangi denklem daha yakinsa laboratuvar o denklemi kullaniyordur.")
P("   Not: YAS guncel yas oldugundan ESK_ satirinda yas farki nedeniyle kucuk sapma beklenir; YEN_ satiri esas alinir.")

# ---------------------------------------------------------------------------
BASLIK("R6. KOHORT BILESIMI")
ds = pd.to_numeric(X["diyabet süresi"], errors="coerce")
P("   Diyabet suresi > 0 : %d / %d (%%%.1f)" % ((ds > 0).sum(), len(ds), 100 * (ds > 0).mean()))
P("   Diyabet suresi = 0 : %d" % (ds == 0).sum())
P("   Diyabet suresi eksik: %d" % ds.isna().sum())

with open(os.path.join(OUT, "revizyon_rapor.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(_LOG))
P(""); P("Bitti: %s" % OUT)
