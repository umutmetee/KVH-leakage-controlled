# -*- coding: utf-8 -*-
"""
KVH_TAM_ANALIZ.py
Makalede ve tezde raporlanan HER sayiyi tek calistirmada yeniden uretir.

KULLANIM
--------
1) Bu dosyayi, asagidaki iki Excel dosyasiyla AYNI klasore koyun:
       sizintisiz_veri.xlsx      (931 x 130  -  oznitelikler)
       aiveri2026_haz.xlsx       (931 x 199  -  ham kayit, uc nokta kaynagi)
   DIKKAT: sizintisiz_veri.xlsx'in DOGRU kopyasi 678.451 bayt olanidir.
2) Gerekli paketler:
       pip install pandas numpy scipy scikit-learn statsmodels openpyxl matplotlib
3) Calistirin:
       python KVH_TAM_ANALIZ.py
4) Ciktilar ayni klasorde "cikti/" altina yazilir:
       rapor.txt        - ekrana basilanin aynisi
       *.csv            - tablolarin makine okunabilir hali
       sekil_*.png      - grafikler

DOGRULAMA
---------
rapor.txt icindeki her satirin basinda [Mx.y] veya [Tablo N] etiketi vardir.
Bu etiketleri makaledeki/tezdeki ilgili yerle karsilastirin. Uyusmayan bir
satir varsa, sorun kodda ya da veridedir; kaynak burada gorunur.

Rastgelelik: tum tohumlar sabittir (SEED=42). Ayni veriyle ayni sayilar cikar.
"""

import os, re, sys, warnings, json
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from scipy import stats
from scipy.special import expit
from scipy.optimize import brentq
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import f_classif, mutual_info_classif, RFE
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
from sklearn.metrics import (roc_auc_score, roc_curve, precision_recall_curve,
                             average_precision_score, brier_score_loss, confusion_matrix)
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

# ----------------------------------------------------------------------------
# AYARLAR
# ----------------------------------------------------------------------------
KLASOR   = os.path.dirname(os.path.abspath(__file__))
CIKTI    = os.path.join(KLASOR, "cikti")
VERI     = os.path.join(KLASOR, "sizintisiz_veri.xlsx")
RAW      = os.path.join(KLASOR, "aiveri2026_haz.xlsx")
SEED     = 42      # tum bolmelerde ve modellerde kullanilan tohum
K        = 20      # secilen oznitelik sayisi
C        = 0.01    # L2 duzenlilestirme gucu (kucuk C = guclu ceza)
NBOOT    = 2000    # onyukleme yeniden ornekleme sayisi
NOPT     = 200     # secim dahil iyimserlik onyuklemesi
SEKIL    = True    # False yaparsaniz grafikler uretilmez (daha hizli)

STATIK = ["diyabet süresi", "YAŞ", "CİNSİYET", "sigara", "sistolık kan basıncı",
          "diastolik kan basıncı", "boy", "kılo", "bmı"]

os.makedirs(CIKTI, exist_ok=True)
_LOG = []
def P(s=""):
    print(s)
    _LOG.append(str(s))
def BASLIK(s):
    P(""); P("=" * 78); P(s); P("=" * 78)

# ----------------------------------------------------------------------------
# 1. VERI YUKLEME ve UC NOKTA TURETIMI
# ----------------------------------------------------------------------------
BASLIK("1. VERI ve UC NOKTA")
for f in (VERI, RAW):
    if not os.path.exists(f):
        sys.exit("HATA: dosya bulunamadi -> %s" % f)
P("sizintisiz_veri.xlsx boyut : %d bayt  (beklenen 678451)" % os.path.getsize(VERI))

d   = pd.read_excel(VERI)
raw = pd.read_excel(RAW)
P("sizintisiz_veri  : %d satir x %d sutun" % d.shape)
P("aiveri2026_haz   : %d satir x %d sutun" % raw.shape)

# Satir hizalamasi: iki dosya konumsal birlestiriliyor, HASTA_NO ile dogrulanir
assert (pd.to_numeric(d["HASTA_NO"]) == pd.to_numeric(raw["HASTA_NO"])).all(), \
    "SATIR HIZALAMASI BOZUK: iki dosyanin HASTA_NO sirasi ayni degil"
P("[kontrol] HASTA_NO hizalamasi: 931/931 birebir  -> konumsal birlestirme guvenli")

num = lambda c: pd.to_numeric(raw[c], errors="coerce")
la   = num("la abn").fillna(0) > 0
lv   = num("lvedd abn").fillna(0) > 0
ef_  = ((num("ef") < 50) | (num("ef (E)") < 50)).fillna(False)
qtc  = num("qtc abn").fillna(0) > 0
qrs  = num("qrs abn").fillna(0) > 0
y = pd.Series((la | lv | ef_ | qtc | qrs).astype(int)).reset_index(drop=True)

P("")
P("[M3] UC NOKTA BILESENLERI (hasta birden fazla kriteri karsilayabilir)")
for ad, v in [("Sol atriyum genislemesi", la), ("Uzamis QTc", qtc), ("EF < %50", ef_),
              ("LVEDD genislemesi", lv), ("Uzamis QRS", qrs)]:
    P("   %-26s %3d hasta (%%%.1f)" % (ad, v.sum(), 100 * v.mean()))
P("[M3] UC NOKTA POZITIF : %d / %d  (%%%.1f)" % (y.sum(), len(y), 100 * y.mean()))

# Eşik degerlerinin veriden geri cikarilmasi (M3 dogrulamasi)
P("")
P("[M3] ESIK DEGERLERI (bayraklardan geri cikarildi, cinsiyete gore)")
cin = num("CİNSİYET")   # 1 = kadin, 2 = erkek
for olcum, bayrak, ad in [("max sol atr","la abn","Sol atriyum capi (mm)"),
                          ("max lvedd","lvedd abn","LVEDD (mm)"),
                          ("max qtc","qtc abn","QTc (ms)"),
                          ("max qrs dur","qrs abn","QRS (ms)")]:
    v, g = num(olcum), num(bayrak)
    sat = []
    for lab, sel in [("K", cin == 1), ("E", cin == 2)]:
        a, b = v[(g == 1) & sel], v[(g == 0) & sel]
        if a.notna().sum() >= 5:
            sat.append("%s: > %.0f" % (lab, b.max()))
    P("   %-24s %s" % (ad, "   ".join(sat)))
P("   %-24s K: < 50   E: < 50" % "Ejeksiyon fraksiyonu (%)")

# Eski kayitli tani alani ile karsilastirma (M3 / Y8)
eski = d["kalp hastalığı"].astype(int).reset_index(drop=True)
ct = pd.crosstab(eski, y)
P("")
P("[Y8] KAYITLI TANI ALANI ile OLCUME DAYALI KURAL")
P("   eski pozitif : %d   yeni pozitif : %d" % (eski.sum(), y.sum()))
P("   uyusmazlik   : %d hasta  (%d pozitif->negatif, %d negatif->pozitif)"
  % ((eski != y).sum(), ct.loc[1, 0], ct.loc[0, 1]))

# ----------------------------------------------------------------------------
# 2. BEYAZ LISTE ve ADAY HAVUZU
# ----------------------------------------------------------------------------
BASLIK("2. ADAY DEGISKENLER")
Xa = d.drop(columns=["kalp hastalığı"])
cols = [c for c in Xa.columns if str(c).startswith(("ESK_", "YEN_"))] + \
       [c for c in STATIK if c in Xa.columns]
X = Xa[cols].apply(pd.to_numeric, errors="coerce")
bos = X.columns[X.isna().all()].tolist()
X = X.drop(columns=bos).reset_index(drop=True)
P("[Tablo IV-asama] ham sutun %d -> beyaz liste sonrasi %d -> tamamen bos %d cikarildi -> ADAY %d"
  % (raw.shape[1], d.shape[1], len(bos), X.shape[1]))
mi = X.isna().mean() * 100
P("[M5.1] eksiklik: ortalama %%%.1f  medyan %%%.1f  maks %%%.1f  |  >%%30 olan: %d/%d"
  % (mi.mean(), mi.median(), mi.max(), (mi > 30).sum(), len(mi)))

# ----------------------------------------------------------------------------
# 3. BOLME, SIRALAMA, AILE TEKILLESTIRMESI
# ----------------------------------------------------------------------------
BASLIK("3. BOLME ve OZNITELIK SECIMI")
idx = np.arange(len(X))
tr, te = train_test_split(idx, test_size=0.2, stratify=y, random_state=SEED)
Xtr, Xte, ytr, yte = X.iloc[tr], X.iloc[te], y.iloc[tr], y.iloc[te]
P("[III-A] egitim %d hasta (%d pozitif)  |  test %d hasta (%d pozitif)"
  % (len(tr), ytr.sum(), len(te), yte.sum()))
P("[III-A] prevalans egitim %%%.1f  test %%%.1f" % (100*ytr.mean(), 100*yte.mean()))

def aile(n):
    """Analit ailesi: ayni analitin tekrar/yeniden ifade edilmis olculeri."""
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
    return Pipeline([("i", SimpleImputer(strategy="median")),
                     ("s", StandardScaler()),
                     ("m", est if est is not None else LogisticRegression(C=C, max_iter=2000))])

Frank = siralama_anova(Xtr, ytr)
SEL = tekillestir(Frank, K, list(Xtr.columns))
P("")
P("[Tablo II] SECILEN %d DEGISKEN (ANOVA F, egitim bolumu)" % K)
for i, s in enumerate(SEL, 1):
    P("   %2d. %-30s F = %7.2f   eksik %%%.1f" % (i, s, Frank[s], 100*X[s].isna().mean()))

# Tekillestirme olmadan VIF (M / Y2 dogrulamasi)
ham20 = list(Frank.sort_values(ascending=False).index[:K])
def vif_hesap(kume):
    Z = StandardScaler().fit_transform(SimpleImputer(strategy="median").fit_transform(Xtr[kume]))
    return [variance_inflation_factor(Z, i) for i in range(len(kume))]
v_ham, v_ded = vif_hesap(ham20), vif_hesap(SEL)
P("")
P("[II-C] VIF  tekillestirme YOK : maks %.1f" % max(v_ham))
P("[II-C] VIF  tekillestirme VAR : maks %.2f" % max(v_ded))
a_ham = roc_auc_score(yte, boru().fit(Xtr[ham20], ytr).predict_proba(Xte[ham20])[:, 1])
P("[II-C] ayirt edicilik bedeli  : %.3f AUROC (tekillestirmesiz %.3f)"
  % (a_ham - roc_auc_score(yte, boru().fit(Xtr[SEL], ytr).predict_proba(Xte[SEL])[:, 1]), a_ham))
P("")
P("[Y2] AYNI GRUPTAKI DEGISKENLERIN VIF'i (aile kurali disinda birakilanlar)")
K2 = Xtr[SEL].corr()
for g, uyeler in [("trombosit", ["YEN_PLT", "ESK_PCT", "YEN_P-LCR"]),
                  ("glisemik", ["YEN_Glukoz", "ESK_Tokluk Kan Şekeri (TKŞ)", "ESK_HBA1C (%)"])]:
    for u in uyeler:
        if u in SEL: P("   %-10s %-30s VIF = %.2f" % (g, u, v_ded[SEL.index(u)]))
if "YEN_PLT" in SEL and "ESK_PCT" in SEL:
    P("   r(trombosit, plateletkrit) = %+.3f" % K2.loc["YEN_PLT", "ESK_PCT"])

# ----------------------------------------------------------------------------
# 4. k TARAMASI
# ----------------------------------------------------------------------------
BASLIK("4. OZNITELIK SAYISI (k) TARAMASI")
skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
NEV = int(ytr.sum())
P("[Tablo IV]  k | kat ici secimli CD-AUC | ayrik test | EPV")
for k in [10, 15, 20, 30, 40]:
    a = []
    for ti, vi in skf.split(Xtr, ytr):
        Xi, yi = Xtr.iloc[ti], ytr.iloc[ti]
        s = tekillestir(siralama_anova(Xi, yi), k, list(Xi.columns))
        m = boru().fit(Xi[s], yi)
        a.append(roc_auc_score(ytr.iloc[vi], m.predict_proba(Xtr[s].iloc[vi])[:, 1]))
    s = tekillestir(Frank, k, list(Xtr.columns))
    h = roc_auc_score(yte, boru().fit(Xtr[s], ytr).predict_proba(Xte[s])[:, 1])
    P("   %2d | %.3f +- %.3f        | %.3f      | %.1f" % (k, np.mean(a), np.std(a), h, NEV/k))

# ----------------------------------------------------------------------------
# 5. ON UC MODEL
# ----------------------------------------------------------------------------
BASLIK("5. ON UC ALGORITMANIN KARSILASTIRMASI")
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
Pp, yv = {}, yte.values
for n, e in MOD.items():
    Pp[n] = boru(e).fit(Xtr[SEL], ytr).predict_proba(Xte[SEL])[:, 1]
baz = [("lr", boru()), ("nb", boru(GaussianNB())),
       ("rf", boru(RandomForestClassifier(n_estimators=400, random_state=SEED)))]
for n, e in [("Soft Voting", VotingClassifier(baz, voting="soft")),
             ("Stacking", StackingClassifier(baz, final_estimator=LogisticRegression(max_iter=2000), cv=5))]:
    e.fit(Xtr[SEL], ytr); Pp[n] = e.predict_proba(Xte[SEL])[:, 1]

def esik_youden(p_oof, y_oof):
    f, t, th = roc_curve(y_oof, p_oof)
    return th[np.argmax(t - f)]

oof = cross_val_predict(boru(), Xtr[SEL], ytr, cv=skf, method="predict_proba")[:, 1]
TAU = esik_youden(oof, ytr)
P("[III-E] karar esigi (egitim kat disi tahminlerden, Youden) tau = %.3f" % TAU)
P("")
satir = []
for n, p in Pp.items():
    tau = esik_youden(cross_val_predict(boru(MOD[n]), Xtr[SEL], ytr, cv=skf, method="predict_proba")[:, 1], ytr) \
          if n in MOD else TAU
    yh = (p >= tau).astype(int)
    tn, fp, fn, tp = confusion_matrix(yv, yh).ravel()
    auc = roc_auc_score(yv, p)
    if n in MOD:
        rng = np.random.RandomState(1); bs = []
        for _ in range(NBOOT):
            i = rng.randint(0, len(yv), len(yv))
            if len(np.unique(yv[i])) > 1: bs.append(roc_auc_score(yv[i], p[i]))
        lo, hi = np.percentile(bs, [2.5, 97.5])
    else:
        lo = hi = np.nan
    satir.append(dict(Model=n, AUC=auc, lo=lo, hi=hi,
                      AUPRC=average_precision_score(yv, p),
                      Sens=tp/(tp+fn), Spec=tn/(tn+fp), PPV=tp/(tp+fp), NPV=tn/(tn+fn),
                      Acc=(tp+tn)/len(yv), F1=2*tp/(2*tp+fp+fn),
                      MCC=(tp*tn-fp*fn)/np.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)),
                      Brier=brier_score_loss(yv, p), TN=tn, FP=fp, FN=fn, TP=tp))
R = pd.DataFrame(satir).sort_values("AUC", ascending=False)
R.to_csv(os.path.join(CIKTI, "tablo_modeller.csv"), index=False)
P("[Tablo III] %-24s %-22s %-6s %-6s %-6s %-6s" % ("Model", "AUROC (%95 GA)", "AUPRC", "Duy.", "Ozg.", "Brier"))
for _, r in R.iterrows():
    ci = "%.3f (%.3f-%.3f)" % (r.AUC, r.lo, r.hi) if pd.notna(r.lo) else "%.3f (-)" % r.AUC
    P("            %-24s %-22s %.3f  %.3f  %.3f  %.3f" % (r.Model, ci, r.AUPRC, r.Sens, r.Spec, r.Brier))

# ----------------------------------------------------------------------------
# 6. NIHAI MODEL: DENKLEM, KATSAYILAR, KALIBRASYON
# ----------------------------------------------------------------------------
BASLIK("6. NIHAI MODEL")
imp = SimpleImputer(strategy="median").fit(Xtr[SEL])
sc  = StandardScaler().fit(imp.transform(Xtr[SEL]))
fin = boru().fit(Xtr[SEL], ytr)
beta = fin.named_steps["m"].coef_[0]
b0   = fin.named_steps["m"].intercept_[0]
p    = fin.predict_proba(Xte[SEL])[:, 1]
P("[Tablo V] kesisim = %.4f" % b0)

rng = np.random.RandomState(SEED); bs = np.full((NBOOT, K), np.nan)
yv_tr = ytr.values
for b in range(NBOOT):
    i = rng.randint(0, len(tr), len(tr))
    if len(np.unique(yv_tr[i])) < 2: continue
    bs[b] = boru().fit(Xtr[SEL].iloc[i], pd.Series(yv_tr[i])).named_steps["m"].coef_[0]
lo_b, hi_b = np.nanpercentile(bs, 2.5, 0), np.nanpercentile(bs, 97.5, 0)
eq = pd.DataFrame({"degisken": SEL, "F": [Frank[s] for s in SEL],
                   "medyan": imp.statistics_, "ortalama": sc.mean_, "SS": np.sqrt(sc.var_),
                   "beta": beta, "exp_beta": np.exp(beta),
                   "OA_alt": np.exp(lo_b), "OA_ust": np.exp(hi_b), "VIF": v_ded})
eq.to_csv(os.path.join(CIKTI, "tablo_denklem.csv"), index=False)
P("[Tablo II/V] %-30s %8s %8s %-16s %5s" % ("degisken", "beta", "exp b", "%95 OA", "VIF"))
for _, r in eq.iterrows():
    P("             %-30s %+8.3f %8.3f %.3f-%.3f     %5.2f"
      % (r.degisken, r.beta, r.exp_beta, r.OA_alt, r.OA_ust, r.VIF))

citl = sm.GLM(yv, np.ones((len(yv), 1)), family=sm.families.Binomial(),
              offset=np.log(p/(1-p))).fit().params[0]
egim = sm.Logit(yv, sm.add_constant(np.log(p/(1-p)))).fit(disp=0).params[1]
q = pd.qcut(p, 10, duplicates="drop")
ece = sum(abs(yv[q == g].mean() - p[q == g].mean()) * (q == g).sum() for g in q.categories) / len(yv)
tn, fp, fn, tp = confusion_matrix(yv, (p >= TAU).astype(int)).ravel()
P("")
P("[III-E] AUROC %.3f | AUPRC %.3f | prevalans %.3f | lift %.2f"
  % (roc_auc_score(yv, p), average_precision_score(yv, p), yv.mean(),
     average_precision_score(yv, p)/yv.mean()))
P("[III-E] CITL %.3f | egim %.3f | ECE %.3f | Brier %.3f" % (citl, egim, ece, brier_score_loss(yv, p)))
P("[III-E] karisiklik matrisi  GN=%d YP=%d YN=%d GP=%d" % (tn, fp, fn, tp))
P("[III-E] duyarlilik %.3f | ozgulluk %.3f | dogruluk %.3f" % (tp/(tp+fn), tn/(tn+fp), (tp+tn)/len(yv)))

# Platt duyarlilik analizi
from sklearn.calibration import CalibratedClassifierCV
cal = CalibratedClassifierCV(boru(), method="sigmoid", cv=skf).fit(Xtr[SEL], ytr)
pc = cal.predict_proba(Xte[SEL])[:, 1]
qc = pd.qcut(pc, 10, duplicates="drop")
ece_c = sum(abs(yv[qc == g].mean() - pc[qc == g].mean()) * (qc == g).sum() for g in qc.categories)/len(yv)
P("[M4.3] Platt yeniden kalibrasyonu: ECE %.3f -> %.3f  (uygulanmadi)" % (ece, ece_c))

# class_weight duyarlilik analizi
cw = Pipeline([("i", SimpleImputer(strategy="median")), ("s", StandardScaler()),
               ("m", LogisticRegression(C=C, max_iter=2000, class_weight="balanced"))]).fit(Xtr[SEL], ytr)
pw = cw.predict_proba(Xte[SEL])[:, 1]
citl_w = sm.GLM(yv, np.ones((len(yv), 1)), family=sm.families.Binomial(),
                offset=np.log(pw/(1-pw))).fit().params[0]
P("[M4.2] class_weight='balanced': AUROC %.3f, CITL %.3f  (reddedildi; CITL %.3f -> %.3f)"
  % (roc_auc_score(yv, pw), citl_w, citl, citl_w))

# ----------------------------------------------------------------------------
# 7. KLINIK REFERANS MODELI ve KARAR EGRISI
# ----------------------------------------------------------------------------
BASLIK("7. EK DEGER ve KLINIK FAYDA")
KLINIK = [c for c in ["YAŞ", "CİNSİYET", "bmı", "sistolık kan basıncı",
                      "diastolik kan basıncı", "sigara", "diyabet süresi"] if c in X.columns]
pk = boru().fit(Xtr[KLINIK], ytr).predict_proba(Xte[KLINIK])[:, 1]
af, ak = roc_auc_score(yv, p), roc_auc_score(yv, pk)
rng = np.random.RandomState(7); dd = []
for _ in range(NBOOT):
    i = rng.randint(0, len(yv), len(yv))
    if len(np.unique(yv[i])) > 1: dd.append(roc_auc_score(yv[i], p[i]) - roc_auc_score(yv[i], pk[i]))
dd = np.array(dd)
P("[III-H] klinik referans (%d degisken) AUROC %.3f | tam model %.3f" % (len(KLINIK), ak, af))
P("[III-H] fark %+.3f  %%95 GA [%+.3f, %+.3f]  P(tam>klinik) = %.2f"
  % (af-ak, np.percentile(dd, 2.5), np.percentile(dd, 97.5), (dd > 0).mean()))
prev = yv.mean()
def net_fayda(pp, t):
    yh = pp >= t
    return ((yh == 1) & (yv == 1)).sum()/len(yv) - (((yh == 1) & (yv == 0)).sum()/len(yv))*(t/(1-t))
P("")
P("[Tablo DCA] esik | model | herkesi tedavi | fark")
for t in [0.20, 0.25, 0.30, 0.40, 0.50]:
    na = prev - (1-prev)*(t/(1-t))
    P("            %.2f  | %+.3f | %+.3f         | %+.3f" % (t, net_fayda(p, t), na, net_fayda(p, t)-na))

# ----------------------------------------------------------------------------
# 8. KARARLILIK, SIZINTI, DARALTILMIS UC NOKTALAR
# ----------------------------------------------------------------------------
BASLIK("8. KARARLILIK ve DUYARLILIK ANALIZLERI")
a_cv = []
for ti, vi in skf.split(Xtr, ytr):
    Xi, yi = Xtr.iloc[ti], ytr.iloc[ti]
    s = tekillestir(siralama_anova(Xi, yi), K, list(Xi.columns))
    a_cv.append(roc_auc_score(ytr.iloc[vi], boru().fit(Xi[s], yi).predict_proba(Xtr[s].iloc[vi])[:, 1]))
P("[III-E] kat ici secimli capraz dogrulama : %.3f +- %.3f" % (np.mean(a_cv), np.std(a_cv)))

au, frq = [], {}
for s_ in range(20):
    t2, e2 = train_test_split(idx, test_size=0.2, stratify=y, random_state=s_)
    X2, y2 = X.iloc[t2], y.iloc[t2]
    s2 = tekillestir(siralama_anova(X2, y2), K, list(X2.columns))
    for c in s2: frq[c] = frq.get(c, 0) + 1
    au.append(roc_auc_score(y.iloc[e2], boru().fit(X2[s2], y2).predict_proba(X.iloc[e2][s2])[:, 1]))
P("[III-E] 20 bagimsiz bolme : %.3f +- %.3f  (aralik %.3f-%.3f)"
  % (np.mean(au), np.std(au), min(au), max(au)))
P("[III-E] 20/20 secilen : %s" % ", ".join(c for c, v in frq.items() if v == 20))
P("[III-E] 19/20 secilen : %s" % ", ".join(c for c, v in frq.items() if v == 19))

ts, trs, vas = learning_curve(boru(), Xtr[SEL], ytr, cv=skf, scoring="roc_auc",
                              train_sizes=np.linspace(.2, 1, 6))
P("[III-E] ogrenme egrisi : egitim %.3f  dogrulama %.3f  fark %.3f"
  % (trs[-1].mean(), vas[-1].mean(), trs[-1].mean()-vas[-1].mean()))

gor = roc_auc_score(ytr, fin.predict_proba(Xtr[SEL])[:, 1])
rng = np.random.RandomState(SEED); opt = []
for b in range(NOPT):
    i = rng.randint(0, len(tr), len(tr))
    Xb, yb = Xtr.iloc[i], ytr.iloc[i]
    if yb.nunique() < 2: continue
    sb = tekillestir(siralama_anova(Xb, yb), K, list(Xb.columns))
    mb = boru().fit(Xb[sb], yb)
    opt.append(roc_auc_score(yb, mb.predict_proba(Xb[sb])[:, 1]) -
               roc_auc_score(ytr, mb.predict_proba(Xtr[sb])[:, 1]))
o = np.mean(opt)
P("[III-I] secim dahil onyukleme : gorunur %.3f | iyimserlik %.3f | duzeltilmis %.3f [%.3f-%.3f]"
  % (gor, o, gor-o, gor-np.percentile(opt, 97.5), gor-np.percentile(opt, 2.5)))

# Sizinti testi + GA (M1)
ESKp = [c for c in Xtr.columns if str(c).startswith("ESK_")] + [c for c in STATIK if c in Xtr.columns]
sE = tekillestir(siralama_anova(Xtr[ESKp], ytr), K, ESKp)
pb = boru().fit(Xtr[sE], ytr).predict_proba(Xte[sE])[:, 1]
rng = np.random.RandomState(11); db = []
for _ in range(NBOOT):
    i = rng.randint(0, len(yv), len(yv))
    if len(np.unique(yv[i])) > 1: db.append(roc_auc_score(yv[i], p[i]) - roc_auc_score(yv[i], pb[i]))
db = np.array(db)
P("[M1/A1.2] yalnizca-baseline (%d aday) AUROC %.3f | fark %+.3f GA [%+.3f, %+.3f] P=%.2f"
  % (len(ESKp), roc_auc_score(yv, pb), af-roc_auc_score(yv, pb),
     np.percentile(db, 2.5), np.percentile(db, 97.5), (db > 0).mean()))

# EF>=50 altgrup (M1/A1.3)
def altgrup(maske, ad, etiket=None):
    yy = (y if etiket is None else pd.Series(etiket.astype(int)).reset_index(drop=True))
    Xs, ys = X[maske].reset_index(drop=True), yy[maske].reset_index(drop=True)
    i2 = np.arange(len(Xs)); t2, e2 = train_test_split(i2, test_size=0.2, stratify=ys, random_state=SEED)
    X2, y2 = Xs.iloc[t2], ys.iloc[t2]
    s2 = tekillestir(siralama_anova(X2, y2), K, list(X2.columns))
    pp = boru().fit(X2[s2], y2).predict_proba(Xs.iloc[e2][s2])[:, 1]; yy2 = ys.iloc[e2].values
    a = roc_auc_score(yy2, pp)
    rng = np.random.RandomState(7); b_ = []
    for _ in range(NBOOT):
        i = rng.randint(0, len(yy2), len(yy2))
        if len(np.unique(yy2[i])) > 1: b_.append(roc_auc_score(yy2[i], pp[i]))
    P("   %-34s n=%3d n+=%3d AUROC %.3f [%.3f-%.3f] EPV %.1f"
      % (ad, len(Xs), int(ys.sum()), a, np.percentile(b_, 2.5), np.percentile(b_, 97.5), int(y2.sum())/K))
P("")
P("[M1/A1.3 + M3] ALTGRUP ve DARALTILMIS UC NOKTA ANALIZLERI")
ef_dusuk = ((num("ef") < 50) | (num("ef (E)") < 50)).fillna(False)
altgrup((~ef_dusuk).values, "EF >= %50 altgrubu")
def daralt(lbl, ad):
    yy = pd.Series(lbl.astype(int)).reset_index(drop=True)
    i2 = np.arange(len(X)); t2, e2 = train_test_split(i2, test_size=0.2, stratify=yy, random_state=SEED)
    X2, y2 = X.iloc[t2], yy.iloc[t2]
    s2 = tekillestir(siralama_anova(X2, y2), K, list(X2.columns))
    pp = boru().fit(X2[s2], y2).predict_proba(X.iloc[e2][s2])[:, 1]; yy2 = yy.iloc[e2].values
    a = roc_auc_score(yy2, pp)
    rng = np.random.RandomState(7); b_ = []
    for _ in range(NBOOT):
        i = rng.randint(0, len(yy2), len(yy2))
        if len(np.unique(yy2[i])) > 1: b_.append(roc_auc_score(yy2[i], pp[i]))
    P("   %-34s n+=%3d AUROC %.3f [%.3f-%.3f] EPV %.1f"
      % (ad, int(yy.sum()), a, np.percentile(b_, 2.5), np.percentile(b_, 97.5), int(y2.sum())/K))
daralt(la | lv | ef_, "Yapisal (LA/LVEDD/EF)")
daralt(qtc | qrs, "Elektriksel (QTc/QRS)")
daralt(lv | ef_, "Agir (LVEDD/EF)")

# Kohort turdesligi
ds = pd.to_numeric(X["diyabet süresi"], errors="coerce")
altgrup((ds != 0).values, "Diyabet suresi > 0 (n=841)")
h_ = pd.to_numeric(X["ESK_HBA1C (%)"], errors="coerce"); g_ = pd.to_numeric(X["YEN_Glukoz"], errors="coerce")
z = ds == 0
P("   [M2] sure=0 grubu: n=%d (%%%.1f) | HbA1c medyan %.1f vs %.1f | glukoz %.1f vs %.1f | prevalans %%%.1f vs %%%.1f"
  % (z.sum(), 100*z.mean(), h_[z].median(), h_[~z].median(), g_[z].median(), g_[~z].median(),
     100*y[z.values].mean(), 100*y[(~z).values].mean()))

# ----------------------------------------------------------------------------
# 9. EKSIK VERI DUYARLILIK (M5)
# ----------------------------------------------------------------------------
BASLIK("9. EKSIK VERI DUYARLILIK ANALIZLERI")
au_m, CO = [], []
for m in range(5):
    pl2 = Pipeline([("i", IterativeImputer(max_iter=15, sample_posterior=True,
                                           random_state=m, initial_strategy="median")),
                    ("s", StandardScaler()), ("m", LogisticRegression(C=C, max_iter=2000))]).fit(Xtr[SEL], ytr)
    au_m.append(roc_auc_score(yv, pl2.predict_proba(Xte[SEL])[:, 1]))
    CO.append(pl2.named_steps["m"].coef_[0])
CO = np.array(CO)
P("[M5.2] MICE (m=5) AUROC ortalama %.3f (aralik %.3f-%.3f) | medyan imputasyon %.3f"
  % (np.mean(au_m), min(au_m), max(au_m), af))
kay = pd.DataFrame({"degisken": SEL, "medyan_beta": beta, "mice_beta": CO.mean(0),
                    "fark": CO.mean(0)-beta, "eksik_%": [100*X[s].isna().mean() for s in SEL]})
kay.to_csv(os.path.join(CIKTI, "mice_katsayi_kaymasi.csv"), index=False)
P("[M5.2] ortalama mutlak kayma %.3f | en buyuk %.3f" % (kay.fark.abs().mean(), kay.fark.abs().max()))
for _, r in kay.reindex(kay["eksik_%"].sort_values(ascending=False).index).head(4).iterrows():
    P("        %-30s eksik %%%.1f  beta %+.3f -> %+.3f  (%+.3f)"
      % (r.degisken, r["eksik_%"], r.medyan_beta, r.mice_beta, r.fark))

HI = [s for s in SEL if X[s].isna().mean() > 0.30]
Xi2 = X.copy()
for s in HI: Xi2["EKSIK_" + s] = X[s].isna().astype(int)
IND = ["EKSIK_" + s for s in HI]
m2 = boru().fit(Xi2.iloc[tr][SEL+IND], ytr)
a2 = roc_auc_score(yv, m2.predict_proba(Xi2.iloc[te][SEL+IND])[:, 1])
co = m2.named_steps["m"].coef_[0][-len(IND):]
rng = np.random.RandomState(SEED); bsi = np.full((1000, len(IND)), np.nan)
for b in range(1000):
    i = rng.randint(0, len(tr), len(tr))
    if len(np.unique(yv_tr[i])) < 2: continue
    bsi[b] = boru().fit(Xi2.iloc[tr][SEL+IND].iloc[i], pd.Series(yv_tr[i])).named_steps["m"].coef_[0][-len(IND):]
P("[M5.3] eksiklik gostergesi eklenmis model AUROC %.3f (gostergesiz %.3f)" % (a2, af))
for s, c_, l, h in zip(HI, co, np.nanpercentile(bsi, 2.5, 0), np.nanpercentile(bsi, 97.5, 0)):
    P("        %-30s exp b %.3f [%.3f-%.3f] %s"
      % (s, np.exp(c_), np.exp(l), np.exp(h), "ANLAMLI" if (l > 0 or h < 0) else "-"))

# ----------------------------------------------------------------------------
# 10. ORNEKLEM BUYUKLUGU (Riley)
# ----------------------------------------------------------------------------
BASLIK("10. ORNEKLEM BUYUKLUGU (Riley)")
N = 200000; phi = float(ytr.mean())
def _sim(sig):
    # her cagrida ayni tohum: fonksiyon deterministik olmali, yoksa kok bulma sasar
    rr = np.random.RandomState(1)
    lp = rr.normal(0, sig, N)
    a0 = brentq(lambda a: expit(lp+a).mean()-phi, -20, 20)
    lp = lp+a0; pr = expit(lp)
    return lp, (rr.rand(N) < pr).astype(int), pr
def _c(z):
    lp, yy, _ = _sim(z); return roc_auc_score(yy, lp)-af
sig = brentq(_c, 0.1, 6.0, xtol=1e-3)
lp_, yy_, pr_ = _sim(sig)
ll = np.mean(yy_*np.log(pr_)+(1-yy_)*np.log(1-pr_))
ll0 = phi*np.log(phi)+(1-phi)*np.log(1-phi)
R2cs = 1-np.exp(2*(ll0-ll))
gerekli = K/((0.9-1)*np.log(1-R2cs/0.9))
P("[IV-E] beklenen R2cs (C=%.3f'ten benzetimle) = %.3f | gerekli n = %.0f | mevcut %d | acik %%%.0f"
  % (af, R2cs, gerekli, len(tr), 100*(1-len(tr)/gerekli)))

# ----------------------------------------------------------------------------
# 11. DEMOGRAFI TABLOSU
# ----------------------------------------------------------------------------
BASLIK("11. DEMOGRAFI TABLOSU (TRIPOD 13b)")
Xc = X.copy()
kk = pd.to_numeric(Xc["kılo"], errors="coerce").copy(); bb = pd.to_numeric(Xc["bmı"], errors="coerce").copy()  # .copy(): duzeltme oncesi degeri yazdirmak icin
hh = pd.to_numeric(Xc["boy"], errors="coerce")
i1 = kk.idxmax(); Xc.loc[i1, "kılo"] = 79.7
i2_ = bb.idxmax(); Xc.loc[i2_, "bmı"] = round(kk[i2_]/(hh[i2_]/100)**2, 1)
P("[Tablo I] duzeltme 1: kilo %.0f -> 79.7 (boy %.0f)" % (kk[i1], hh[i1]))
P("[Tablo I] duzeltme 2: BMI %.1f -> %.1f (kilo %.0f, boy %.0f'dan)" % (bb[i2_], Xc.loc[i2_, "bmı"], kk[i2_], hh[i2_]))
lab = y.values; dsat = []
def _n(c, ad):
    v = pd.to_numeric(Xc[c], errors="coerce"); a, b_ = v[lab == 0], v[lab == 1]
    pv = stats.ttest_ind(a.dropna(), b_.dropna(), equal_var=False).pvalue
    return [ad, "%.1f ± %.1f" % (v.mean(), v.std()), "%.1f ± %.1f" % (a.mean(), a.std()),
            "%.1f ± %.1f" % (b_.mean(), b_.std()), "%.4f" % pv, "%.1f" % (100*v.isna().mean())]
def _c(c, ad, pos):
    v = pd.to_numeric(Xc[c], errors="coerce")
    pv = stats.chi2_contingency(pd.crosstab(v == pos, lab)).pvalue
    f = lambda m: "%d (%%%.1f)" % (((v == pos) & m).sum(), 100*((v == pos) & m).sum()/m.sum())
    return [ad, f(np.ones(len(v), bool)), f(lab == 0), f(lab == 1), "%.4f" % pv, "%.1f" % (100*v.isna().mean())]
dsat.append(_n("YAŞ", "Yas (yil)")); dsat.append(_c("CİNSİYET", "Kadin", 1))
for c, ad in [("boy", "Boy (cm)"), ("kılo", "Kilo (kg)"), ("bmı", "VKI (kg/m2)"),
              ("sistolık kan basıncı", "Sistolik KB"), ("diastolik kan basıncı", "Diyastolik KB"),
              ("diyabet süresi", "Diyabet suresi (yil)")]:
    if c in Xc.columns: dsat.append(_n(c, ad))
dsat.append(_c("sigara", "Sigara", 1))
DT = pd.DataFrame(dsat, columns=["Ozellik", "Tum (931)", "Negatif (560)", "Pozitif (371)", "p", "Eksik %"])
DT.to_csv(os.path.join(CIKTI, "tablo_demografi.csv"), index=False)
for _, r in DT.iterrows():
    P("   %-22s %-16s %-16s %-16s p=%-8s %s" % tuple(r.values))

# ----------------------------------------------------------------------------
# 12. SEKILLER
# ----------------------------------------------------------------------------
if SEKIL:
    BASLIK("12. SEKILLER")
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 8, "savefig.dpi": 200, "savefig.bbox": "tight"})
    def kay(fig, ad):
        fig.savefig(os.path.join(CIKTI, "sekil_%s.png" % ad)); plt.close(fig); P("   yazildi: sekil_%s.png" % ad)
    f_, t_, _ = roc_curve(yv, p)
    fig, ax = plt.subplots(figsize=(4, 3)); ax.plot(f_, t_, lw=1.2)
    ax.plot([0, 1], [0, 1], ":", lw=.8); ax.set_xlabel("1 - Ozgulluk"); ax.set_ylabel("Duyarlilik")
    ax.set_title("ROC  AUROC = %.3f" % af); kay(fig, "roc")
    xs = [p[q == g].mean() for g in q.categories]; ys = [yv[q == g].mean() for g in q.categories]
    fig, ax = plt.subplots(figsize=(4, 3)); ax.plot([0, 1], [0, 1], ":", lw=.8)
    ax.plot(xs, ys, "o-", ms=3); ax.set_xlabel("Tahmin"); ax.set_ylabel("Gozlenen")
    ax.set_title("Kalibrasyon  CITL %.3f egim %.3f" % (citl, egim)); kay(fig, "kalibrasyon")
    pr_, rc_, _ = precision_recall_curve(yv, p)
    fig, ax = plt.subplots(figsize=(4, 3)); ax.plot(rc_, pr_, lw=1.2)
    ax.axhline(yv.mean(), ls=":", lw=.8); ax.set_xlabel("Duyarlilik"); ax.set_ylabel("Kesinlik")
    ax.set_title("AUPRC = %.3f" % average_precision_score(yv, p)); kay(fig, "pr")
    ths = np.linspace(.05, .7, 60)
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot(ths, [net_fayda(p, t) for t in ths], lw=1.2, label="Model")
    ax.plot(ths, [prev-(1-prev)*(t/(1-t)) for t in ths], "--", lw=1, label="Herkesi tedavi")
    ax.axhline(0, ls=":", lw=.8, label="Kimseyi tedavi")
    ax.set_ylim(-.25, .35); ax.set_xlabel("Esik"); ax.set_ylabel("Net fayda")
    ax.legend(fontsize=6, frameon=False); kay(fig, "dca")

# ----------------------------------------------------------------------------
with open(os.path.join(CIKTI, "rapor.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(_LOG))
BASLIK("BITTI")
P("Tum ciktilar: %s" % CIKTI)
P("rapor.txt icindeki [etiket]'leri makaledeki ilgili bolumle karsilastirin.")
