# -*- coding: utf-8 -*-
"""
KVH_SEKILLER.py  (27.09.2026)
Makale (Ingilizce) ve tez (Turkce) icin TUM sekilleri gercek veriden, yayin
kalitesinde (600 dpi PNG + vektor PDF) yeniden uretir. Mevcut sekillerin
guncellenmis hallerine ek olarak Q1/Q2 dergilerde beklenen yeni sekiller de
uretilir.

KULLANIM (kendi bilgisayarinizda, 07_Analiz klasorunde):
    python KVH_SEKILLER.py
Gerekli dosyalar ayni klasorde: sizintisiz_veri.xlsx, aiveri2026_haz.xlsx
Ciktilar:
    cikti_sekil/en/*.png, *.pdf   -> makale (Ingilizce etiketler)
    cikti_sekil/tr/*.png, *.pdf   -> tez (Turkce etiketler)
    cikti_sekil/sekil_verileri/*.csv -> her seklin cizildigi sayilar
    cikti_sekil/sekil_rapor.txt   -> kontrol degerleri
Sure: birkac dakika (onyukleme ve 20 bolme nedeniyle).

Boru hatti KVH_TAM_ANALIZ.py ile birebir aynidir (SEED=42, C=0.01, K=20).
"""
import os, re, sys, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import gridspec
from matplotlib.patches import FancyBboxPatch

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
OUT = os.path.join(KLASOR, "cikti_sekil")
SEED, K, C = 42, 20, 0.01
NBOOT = int(os.environ.get("KVH_NBOOT", 2000))
STATIK = ["diyabet süresi", "YAŞ", "CİNSİYET", "sigara", "sistolık kan basıncı",
          "diastolik kan basıncı", "boy", "kılo", "bmı"]
for s in ("en", "tr", "sekil_verileri"):
    os.makedirs(os.path.join(OUT, s), exist_ok=True)
_LOG = []
def P(s=""):
    print(s); _LOG.append(str(s))

# ---------------------------------------------------------------------------
# GORSEL STIL  (renkler dataviz dogrulayicisindan gecti: 3 slot, tum ciftler)
# ---------------------------------------------------------------------------
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"     # mavi, turuncu, su yesili
INK, INK2, GRID = "#0b0b0b", "#52514e", "#d9d8d4"
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 1.4, "savefig.dpi": 600, "savefig.bbox": "tight",
    "legend.frameon": False, "pdf.fonttype": 42,
})
W1, W2 = 3.5, 7.16    # IEEE tek / cift sutun genisligi (inc)

def kaydet(fig, ad, dil):
    fig.savefig(os.path.join(OUT, dil, ad + ".png"))
    fig.savefig(os.path.join(OUT, dil, ad + ".pdf"))
    plt.close(fig)
    P("   yazildi: %s/%s.png" % (dil, ad))

def csv(df, ad):
    df.to_csv(os.path.join(OUT, "sekil_verileri", ad + ".csv"), index=False)

def dec(x, dil, n=3):
    s = ("%." + str(n) + "f") % x
    return s.replace(".", ",") if dil == "tr" else s

# Degisken adlari (EN / TR)
AD = {
 "ESK_tGFR CKD-EPİ": ("eGFR (CKD-EPI, baseline)", "eGFR (CKD-EPI, başl.)"),
 "YEN_tGFR CKD-EPİ": ("eGFR (CKD-EPI, latest)", "eGFR (CKD-EPI, gün.)"),
 "YAŞ": ("Age", "Yaş"),
 "ESK_Üre": ("Urea (baseline)", "Üre (başl.)"), "YEN_Üre": ("Urea (latest)", "Üre (gün.)"),
 "ESK_LYM%": ("Lymphocyte % (baseline)", "Lenfosit % (başl.)"), "YEN_LYM%": ("Lymphocyte % (latest)", "Lenfosit % (gün.)"),
 "ESK_HDL Kolesterol": ("HDL cholesterol (baseline)", "HDL kolesterol (başl.)"),
 "YEN_HDL Kolesterol": ("HDL cholesterol (latest)", "HDL kolesterol (gün.)"),
 "YEN_Kolesterol": ("Total cholesterol (latest)", "Total kolesterol (gün.)"),
 "ESK_RDW": ("RDW (baseline)", "RDW (başl.)"),
 "YEN_Ürik Asit": ("Uric acid (latest)", "Ürik asit (gün.)"), "ESK_Ürik Asit": ("Uric acid (baseline)", "Ürik asit (başl.)"),
 "YEN_PLT": ("Platelet count (latest)", "Trombosit (gün.)"), "ESK_PLT": ("Platelet count (baseline)", "Trombosit (başl.)"),
 "ESK_Kalsiyum (Ca)": ("Calcium (baseline)", "Kalsiyum (başl.)"),
 "diyabet süresi": ("Diabetes duration", "Diyabet süresi"),
 "ESK_PCT": ("Plateletcrit (baseline)", "Plateletkrit (başl.)"),
 "ESK_Tokluk Kan Şekeri (TKŞ)": ("Postprandial glucose (baseline)", "Tokluk glukoz (başl.)"),
 "YEN_Glukoz": ("Glucose (latest)", "Glukoz (gün.)"), "ESK_Glukoz": ("Glucose (baseline)", "Glukoz (başl.)"),
 "ESK_HBA1C (%)": ("HbA1c % (baseline)", "HbA1c % (başl.)"),
 "ESK_CRP": ("CRP (baseline)", "CRP (başl.)"),
 "YEN_P-LCR": ("P-LCR (latest)", "P-LCR (gün.)"),
 "ESK_Albumin": ("Albumin (baseline)", "Albumin (başl.)"),
 "ESK_NEU#": ("Neutrophil count (baseline)", "Nötrofil sayısı (başl.)"),
 "ESK_HGB": ("Haemoglobin (baseline)", "Hemoglobin (başl.)"),
 "YEN_MCHC": ("MCHC (latest)", "MCHC (gün.)"), "ESK_LYM#": ("Lymphocyte count (baseline)", "Lenfosit sayısı (başl.)"),
 "ESK_NEU%": ("Neutrophil % (baseline)", "Nötrofil % (başl.)"), "ESK_NLR": ("NLR (baseline)", "NLR (başl.)"),
}
def ad(c, dil):
    if c in AD: return AD[c][0 if dil == "en" else 1]
    s = re.sub(r"^(ESK_|YEN_)\s*", "", str(c)).strip()
    if dil == "en":
        return s + (" (baseline)" if str(c).startswith("ESK_") else " (latest)" if str(c).startswith("YEN_") else "")
    return s + (" (başl.)" if str(c).startswith("ESK_") else " (gün.)" if str(c).startswith("YEN_") else "")

MODEL_TR = {"Stacking": "Yığılmış topluluk", "Support Vector Machine": "Destek vektör makinesi",
            "Logistic Regression": "Lojistik regresyon", "Extra Trees": "Ekstra ağaçlar",
            "Soft Voting": "Yumuşak oylama", "Random Forest": "Rastgele orman", "Naive Bayes": "Naive Bayes",
            "Hist. Gradient Boosting": "Histogram grad. artırma", "AdaBoost": "AdaBoost",
            "Gradient Boosting": "Gradyan artırma", "K-Nearest Neighbours": "K-en yakın komşu",
            "Multilayer Perceptron": "Çok katmanlı algılayıcı", "Decision Tree": "Karar ağacı"}
T = lambda en, tr, dil: en if dil == "en" else tr

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
MR = pd.DataFrame(mrow).sort_values("auc", ascending=True); csv(MR, "modeller_auroc")

P("Katsayi onyuklemesi...")
rng = np.random.RandomState(SEED); bs = np.full((NBOOT, K), np.nan)
for b in range(NBOOT):
    i = rng.randint(0, len(tr), len(tr))
    if len(np.unique(ytr.values[i])) < 2: continue
    bs[b] = boru().fit(Xtr[SEL].iloc[i], pd.Series(ytr.values[i])).named_steps["m"].coef_[0]
beta = fin.named_steps["m"].coef_[0]; b0 = fin.named_steps["m"].intercept_[0]
EQ = pd.DataFrame({"var": SEL, "F": [Frank[s] for s in SEL], "beta": beta,
                   "lo": np.nanpercentile(bs, 2.5, 0), "hi": np.nanpercentile(bs, 97.5, 0)})
csv(EQ, "katsayilar")

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
KR = pd.DataFrame(krow); csv(KR, "k_taramasi")

P("20 bolme...")
au, frq = [], {}
for s_ in range(20):
    t2, e2 = train_test_split(idx, test_size=0.2, stratify=y, random_state=s_)
    X2, y2 = X.iloc[t2], y.iloc[t2]
    s2 = tekillestir(siralama_anova(X2, y2), K, list(X2.columns))
    for c in s2: frq[c] = frq.get(c, 0) + 1
    au.append(roc_auc_score(y.iloc[e2], boru().fit(X2[s2], y2).predict_proba(X.iloc[e2][s2])[:, 1]))
csv(pd.DataFrame({"bolme": range(20), "auroc": au}), "yirmi_bolme")
FR = pd.Series(frq).sort_values(ascending=True); csv(FR.rename("sayi").reset_index(), "secilme_sikligi")

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
dd = np.array(dd); csv(pd.DataFrame({"fark": dd}), "fark_onyukleme")

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
ESKp = [c for c in Xtr.columns if str(c).startswith("ESK_")] + [c for c in STATIK if c in Xtr.columns]
sE = tekillestir(siralama_anova(Xtr[ESKp], ytr), K, ESKp)
pb = boru().fit(Xtr[sE], ytr).predict_proba(Xte[sE])[:, 1]
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
 ("Baseline measurements only", "Yalnızca başlangıç ölçümleri", roc_auc_score(yv, pb), *boot_ci(yv, pb, 1), 1),
 ("Ejection fraction ≥ 50% subgroup", "Ejeksiyon fraksiyonu ≥ %50 altgrubu", *altgrup(~ef_), 1),
 ("Diabetes duration > 0 subgroup", "Diyabet süresi > 0 altgrubu", *altgrup(ds != 0), 1),
 ("Structural endpoint (LA/LVEDD/EF)", "Yapısal uç nokta (LA/LVEDD/EF)", *altgrup(tum, la | lv | ef_), 2),
 ("Electrical endpoint (QTc/QRS)", "Elektriksel uç nokta (QTc/QRS)", *altgrup(tum, qtc | qrs), 2),
 ("Severe endpoint (LVEDD/EF)", "Ağır uç nokta (LVEDD/EF)", *altgrup(tum, lv | ef_), 2),
 ("Bedside reference model (7 variables)", "Yatak başı referans model (7 değişken)", AK, *boot_ci(yv, pk, 1), 3),
]
SR = pd.DataFrame(SENS, columns=["en", "tr", "auc", "lo", "hi", "grup"]); csv(SR, "duyarlilik_forest")
for r in SENS: P("   %-45s %.3f [%.3f-%.3f]" % (r[0], r[2], r[3], r[4]))

# ---------------------------------------------------------------------------
# SEKILLER
# ---------------------------------------------------------------------------
def fig_F(dil):   # ANOVA F
    fig, ax = plt.subplots(figsize=(W1, 3.4))
    e = EQ.iloc[::-1]
    ax.barh([ad(v, dil) for v in e["var"]], e["F"], color=C1, height=0.62)
    ax.set_xlabel(T("Univariate ANOVA F-statistic (training partition)", "Tek değişkenli ANOVA F-istatistiği (eğitim bölümü)", dil))
    ax.grid(axis="y", visible=False)
    kaydet(fig, "01_anova_F", dil)

def fig_corr(dil):
    Z = SimpleImputer(strategy="median").fit_transform(Xtr[SEL])
    R = np.corrcoef(Z, rowvar=False)
    fig, ax = plt.subplots(figsize=(W2 * 0.8, W2 * 0.7))
    im = ax.imshow(R, cmap="RdBu_r", vmin=-1, vmax=1)
    lab = [ad(v, dil) for v in SEL]
    ax.set_xticks(range(K)); ax.set_xticklabels(lab, rotation=90, fontsize=6)
    ax.set_yticks(range(K)); ax.set_yticklabels(lab, fontsize=6); ax.grid(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.04); cb.set_label(T("Pearson correlation", "Pearson korelasyon katsayısı", dil))
    kaydet(fig, "02_korelasyon", dil)

def fig_forest_beta(dil):
    fig, ax = plt.subplots(figsize=(W1, 3.6))
    e = EQ.iloc[::-1]; yy = np.arange(len(e))
    ax.errorbar(np.exp(e["beta"]), yy, xerr=[np.exp(e["beta"]) - np.exp(e["lo"]), np.exp(e["hi"]) - np.exp(e["beta"])],
                fmt="o", ms=3.5, color=C1, ecolor=C1, elinewidth=1, capsize=2)
    ax.axvline(1, color=INK2, lw=0.8, ls="--")
    ax.set_yticks(yy); ax.set_yticklabels([ad(v, dil) for v in e["var"]]); ax.grid(axis="y", visible=False)
    ax.set_xlabel(T("exp β per 1 SD (95% bootstrap interval)", "exp β (bir SS başına, %95 önyükleme aralığı)", dil))
    kaydet(fig, "03_katsayi_forest", dil)

def fig_models(dil):
    fig, ax = plt.subplots(figsize=(W1, 3.0))
    m = MR; yy = np.arange(len(m))
    col = [C2 if n == "Logistic Regression" else C1 for n in m["model"]]
    ax.barh(yy, m["auc"] - 0.5, left=0.5, color=col, height=0.6)
    ok = m["lo"].notna()
    ax.errorbar(m["auc"][ok], yy[ok.values], xerr=[(m["auc"] - m["lo"])[ok], (m["hi"] - m["auc"])[ok]],
                fmt="none", ecolor=INK2, elinewidth=0.8, capsize=2)
    ax.set_yticks(yy); ax.set_yticklabels([n if dil == "en" else MODEL_TR[n] for n in m["model"]])
    ax.set_xlim(0.5, 0.9); ax.grid(axis="y", visible=False)
    ax.set_xlabel(T("Held-out test AUROC (95% bootstrap CI)", "Ayrık test AUROC (%95 önyükleme GA)", dil))
    kaydet(fig, "04_model_auroc", dil)

def fig_roc(dil):
    fig, ax = plt.subplots(figsize=(W1, W1))
    for n, c, ls in [("Logistic Regression", C2, "-"), ("Stacking", C1, "--"), ("Random Forest", C3, "-."), ("Decision Tree", INK2, ":")]:
        fpr, tpr, _ = roc_curve(yv, Pp[n])
        ax.plot(fpr, tpr, color=c, ls=ls, label="%s (%s)" % (n if dil == "en" else MODEL_TR[n], dec(roc_auc_score(yv, Pp[n]), dil)))
    ax.plot([0, 1], [0, 1], color=GRID, lw=0.8)
    ax.set_xlabel(T("1 − specificity", "1 − özgüllük", dil)); ax.set_ylabel(T("Sensitivity", "Duyarlılık", dil))
    ax.legend(loc="lower right"); ax.set_aspect("equal")
    kaydet(fig, "05_roc_modeller", dil)

def fig_k(dil):   # iki panel, tek eksen (cift eksen yok)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W2, 2.3))
    a1.errorbar(KR["k"], KR["cv"], yerr=KR["sd"], fmt="o-", color=C1, capsize=2, ms=4)
    a1.axvline(20, color=C2, lw=0.8, ls="--")
    a1.set_xlabel(T("Number of retained features (k)", "Korunan öznitelik sayısı (k)", dil))
    a1.set_ylabel(T("CV-AUROC, selection inside folds (±1 SD)", "Kat içi seçimli ÇD-AUROC (±1 SS)", dil))
    a1.set_title(T("(a) Discrimination", "(a) Ayırt edicilik", dil), loc="left")
    a2.plot(KR["k"], KR["epv"], "s-", color=C1, ms=4)
    a2.axhline(10, color=INK2, lw=0.8, ls=":"); a2.axvline(20, color=C2, lw=0.8, ls="--")
    a2.text(40, 10.4, T("EPV = 10", "EPV = 10", dil), ha="right", va="bottom", color=INK2, fontsize=7)
    a2.set_xlabel(T("Number of retained features (k)", "Korunan öznitelik sayısı (k)", dil))
    a2.set_ylabel(T("Events per variable (training)", "Değişken başına olay (eğitim)", dil))
    a2.set_title(T("(b) Sample-size safety", "(b) Örneklem güvenliği", dil), loc="left")
    fig.tight_layout(); kaydet(fig, "06_k_taramasi", dil)

def fig_cal(dil):  # kalibrasyon + onyukleme bandi + risk histogrami
    q = pd.qcut(p, 10, labels=False, duplicates="drop")
    xs = np.array([p[q == g].mean() for g in np.unique(q)]); ys = np.array([yv[q == g].mean() for g in np.unique(q)])
    grid = np.linspace(0.05, 0.9, 60); rng = np.random.RandomState(SEED); curves = []
    lg = np.log(p / (1 - p))
    for _ in range(500):
        i = rng.randint(0, len(yv), len(yv))
        try:
            m = sm.Logit(yv[i], sm.add_constant(lg[i])).fit(disp=0)
            curves.append(1 / (1 + np.exp(-(m.params[0] + m.params[1] * np.log(grid / (1 - grid))))))
        except Exception:
            pass
    curves = np.array(curves); m0 = sm.Logit(yv, sm.add_constant(lg)).fit(disp=0)
    fit = 1 / (1 + np.exp(-(m0.params[0] + m0.params[1] * np.log(grid / (1 - grid)))))
    fig = plt.figure(figsize=(W1, 3.9)); gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.08)
    ax = fig.add_subplot(gs[0]); hx = fig.add_subplot(gs[1], sharex=ax)
    ax.fill_between(grid, np.percentile(curves, 2.5, 0), np.percentile(curves, 97.5, 0), color=C1, alpha=0.18, lw=0,
                    label=T("Logistic calibration, 95% CI", "Lojistik kalibrasyon, %95 GA", dil))
    ax.plot(grid, fit, color=C1)
    ax.plot(xs, ys, "o", color=C2, ms=4, label=T("Deciles (observed)", "Onda birlik dilimler (gözlenen)", dil))
    ax.plot([0, 1], [0, 1], color=INK2, lw=0.8, ls="--", label=T("Ideal", "İdeal", dil))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_ylabel(T("Observed proportion", "Gözlenen oran", dil))
    citl = sm.GLM(yv, np.ones((len(yv), 1)), family=sm.families.Binomial(), offset=lg).fit().params[0]
    ax.text(0.03, 0.97, "CITL %s\n%s %s\nBrier %s" % (dec(citl, dil), T("Slope", "Eğim", dil), dec(m0.params[1], dil),
            dec(np.mean((p - yv) ** 2), dil)), va="top", fontsize=7, color=INK)
    ax.legend(loc="lower right", fontsize=6); plt.setp(ax.get_xticklabels(), visible=False)
    bins = np.linspace(0, 1, 41)
    hx.hist(p[yv == 0], bins=bins, color=C1, alpha=0.75, label=T("Endpoint negative", "Uç nokta negatif", dil))
    hx.hist(p[yv == 1], bins=bins, color=C2, alpha=0.75, label=T("Endpoint positive", "Uç nokta pozitif", dil))
    hx.set_xlabel(T("Predicted probability", "Tahmin edilen olasılık", dil)); hx.set_ylabel("n"); hx.legend(fontsize=6)
    csv(pd.DataFrame({"tahmin": xs, "gozlenen": ys}), "kalibrasyon_dilimleri")
    kaydet(fig, "07_kalibrasyon", dil)

def fig_cm(dil):
    tn, fp, fn, tp = confusion_matrix(yv, (p >= TAU).astype(int)).ravel()
    M = np.array([[tn, fp], [fn, tp]])
    fig, ax = plt.subplots(figsize=(W1 * 0.85, W1 * 0.75))
    ax.imshow(M, cmap="Blues", vmin=0, vmax=M.max() * 1.3); ax.grid(False)
    lab = [[T("TN", "GN", dil), T("FP", "YP", dil)], [T("FN", "YN", dil), T("TP", "GP", dil)]]
    for i in range(2):
        for j in range(2):
            ax.text(j, i, "%s = %d" % (lab[i][j], M[i, j]), ha="center", va="center", fontsize=9, color=INK)
    ax.set_xticks([0, 1]); ax.set_xticklabels([T("Predicted negative", "Tahmin: negatif", dil), T("Predicted positive", "Tahmin: pozitif", dil)])
    ax.set_yticks([0, 1]); ax.set_yticklabels([T("Observed negative", "Gerçek: negatif", dil), T("Observed positive", "Gerçek: pozitif", dil)])
    ax.set_title("τ = %s" % dec(TAU, dil))
    kaydet(fig, "08_karisiklik", dil)

def fig_splits(dil):
    fig, ax = plt.subplots(figsize=(W1, 2.4))
    ax.hist(au, bins=np.arange(0.69, 0.815, 0.0125), color=C1, edgecolor="white")
    ax.axvline(np.mean(au), color=C2, lw=1.2, label=T("Mean %s ± %s", "Ortalama %s ± %s", dil) % (dec(np.mean(au), dil), dec(np.std(au), dil)))
    ax.axvline(AUC, color=INK2, lw=1, ls="--", label=T("Primary split %s", "Birincil bölme %s", dil) % dec(AUC, dil))
    ax.set_xlabel(T("Held-out AUROC across 20 random splits", "20 rastgele bölmede ayrık test AUROC", dil))
    ax.set_ylabel(T("Count", "Sayı", dil)); ax.legend(loc="upper left")
    kaydet(fig, "09_yirmi_bolme", dil)

def fig_lc(dil):
    fig, ax = plt.subplots(figsize=(W1, 2.5))
    for sc, c, mk, lb in [(trs, C1, "o", T("Training", "Eğitim", dil)), (vas, C2, "s", T("Cross-validation", "Çapraz doğrulama", dil))]:
        ax.plot(ts, sc.mean(1), marker=mk, color=c, ms=3.5, label=lb)
        ax.fill_between(ts, sc.mean(1) - sc.std(1), sc.mean(1) + sc.std(1), color=c, alpha=0.15, lw=0)
    ax.set_xlabel(T("Training-set size", "Eğitim kümesi büyüklüğü", dil)); ax.set_ylabel("AUROC"); ax.legend()
    kaydet(fig, "10_ogrenme_egrisi", dil)

def fig_freq(dil):
    f = FR[FR >= 10]
    fig, ax = plt.subplots(figsize=(W1, 3.4))
    col = [C1 if v in SEL else GRID for v in f.index]
    ax.barh([ad(v, dil) for v in f.index], f.values, color=col, height=0.62)
    ax.set_xlim(0, 20); ax.grid(axis="y", visible=False)
    ax.set_xlabel(T("Times selected in 20 random splits", "20 bölmede seçilme sayısı", dil))
    ax.text(19.8, 0, T("grey = not in final model", "gri = nihai modelde yok", dil), ha="right", va="center", fontsize=6, color=INK2)
    kaydet(fig, "11_secilme_sikligi", dil)

def fig_pr(dil):
    pr, rc, _ = precision_recall_curve(yv, p)
    fig, ax = plt.subplots(figsize=(W1, 2.6))
    ax.plot(rc, pr, color=C1, label="AUPRC %s" % dec(average_precision_score(yv, p), dil), drawstyle="steps-post")
    ax.axhline(yv.mean(), color=INK2, lw=0.8, ls="--", label=T("Prevalence %s", "Prevalans %s", dil) % dec(yv.mean(), dil))
    ax.set_xlabel(T("Recall (sensitivity)", "Duyarlılık", dil)); ax.set_ylabel(T("Precision (PPV)", "Kesinlik", dil))
    ax.set_ylim(0.3, 1.02); ax.legend(loc="upper right")
    kaydet(fig, "12_kesinlik_duyarlilik", dil)

def nb(pp, t, yy):
    yh = pp >= t
    return ((yh == 1) & (yy == 1)).mean() - ((yh == 1) & (yy == 0)).mean() * (t / (1 - t))
def fig_dca(dil):
    ths = np.round(np.arange(0.05, 0.701, 0.01), 2); prev = yv.mean()
    m = np.array([nb(p, t, yv) for t in ths]); r = np.array([nb(pk, t, yv) for t in ths])
    a = prev - (1 - prev) * ths / (1 - ths)
    rng = np.random.RandomState(SEED); B = []
    for _ in range(500):
        i = rng.randint(0, len(yv), len(yv)); B.append([nb(p[i], t, yv[i]) for t in ths])
    B = np.array(B)
    fig, ax = plt.subplots(figsize=(W1, 2.7))
    ax.fill_between(ths, np.percentile(B, 2.5, 0), np.percentile(B, 97.5, 0), color=C1, alpha=0.15, lw=0)
    ax.plot(ths, m, color=C1, label=T("20-variable model (95% CI)", "20 değişkenli model (%95 GA)", dil))
    ax.plot(ths, r, color=C3, ls="-.", label=T("Bedside reference model", "Yatak başı referans model", dil))
    ax.plot(ths, a, color=C2, ls="--", label=T("Treat all", "Herkesi tedavi et", dil))
    ax.axhline(0, color=INK2, lw=0.8, ls=":", label=T("Treat none", "Kimseyi tedavi etme", dil))
    ax.set_ylim(-0.1, 0.5); ax.set_xlabel(T("Threshold probability", "Eşik olasılığı", dil)); ax.set_ylabel(T("Net benefit", "Net fayda", dil))
    ax.legend(loc="upper right", fontsize=6, ncol=2)
    csv(pd.DataFrame({"esik": ths, "model": m, "referans": r, "herkesi_tedavi": a}), "dca")
    kaydet(fig, "13_karar_egrisi", dil)

# ---- YENI SEKILLER ----
def fig_sens_forest(dil):   # N1
    s = SR.iloc[::-1].reset_index(drop=True); yy = np.arange(len(s))
    fig, ax = plt.subplots(figsize=(W2 * 0.75, 3.0))
    for i, r in s.iterrows():
        c = C2 if r.grup == 0 and i == len(s) - 1 else (INK2 if r.grup == 3 else C1)
        ax.errorbar(r.auc, i, xerr=[[r.auc - r.lo], [r.hi - r.auc]], fmt="o", color=c, ecolor=c, ms=4, capsize=2, elinewidth=1)
        ax.text(0.905, i, "%s (%s–%s)" % (dec(r.auc, dil), dec(r.lo, dil), dec(r.hi, dil)), va="center", fontsize=6.5, color=INK)
    ax.axvline(AUC, color=C2, lw=0.8, ls="--")
    ax.set_yticks(yy); ax.set_yticklabels(s[dil]); ax.set_xlim(0.55, 0.9); ax.grid(axis="y", visible=False)
    ax.set_xlabel(T("Held-out AUROC (95% bootstrap CI)", "Ayrık test AUROC (%95 önyükleme GA)", dil))
    kaydet(fig, "N1_duyarlilik_forest", dil)

def fig_risk_dist(dil):     # N2
    fig, ax = plt.subplots(figsize=(W1, 2.4))
    bins = np.linspace(0, 1, 26)
    ax.hist(p[yv == 0], bins=bins, color=C1, alpha=0.55, label=T("Endpoint negative (n=%d)", "Uç nokta negatif (n=%d)", dil) % (yv == 0).sum())
    ax.hist(p[yv == 1], bins=bins, color=C2, alpha=0.55, label=T("Endpoint positive (n=%d)", "Uç nokta pozitif (n=%d)", dil) % (yv == 1).sum())
    ax.axvline(TAU, color=INK, lw=0.9, ls="--"); ax.text(TAU - 0.01, ax.get_ylim()[1] * 0.55, "τ = %s" % dec(TAU, dil), fontsize=7, ha="right")
    ax.set_xlabel(T("Predicted probability (test set)", "Tahmin edilen olasılık (test kümesi)", dil)); ax.set_ylabel("n"); ax.legend(loc="upper right")
    kaydet(fig, "N2_risk_dagilimi", dil)

def fig_cic(dil):            # N3 klinik etki egrisi
    ths = np.round(np.arange(0.05, 0.701, 0.01), 2)
    hr = np.array([1000 * (p >= t).mean() for t in ths]); tp = np.array([1000 * ((p >= t) & (yv == 1)).mean() for t in ths])
    fig, ax = plt.subplots(figsize=(W1, 2.6))
    ax.plot(ths, hr, color=C1, label=T("Classified high risk", "Yüksek riskli sınıflanan", dil))
    ax.plot(ths, tp, color=C2, ls="--", label=T("… of whom endpoint positive", "… bunlardan uç nokta pozitif", dil))
    ax.set_xlabel(T("Threshold probability", "Eşik olasılığı", dil)); ax.set_ylabel(T("Number per 1,000 patients", "1.000 hasta başına sayı", dil))
    ax.legend(loc="upper right")
    csv(pd.DataFrame({"esik": ths, "yuksek_risk": hr, "gercek_pozitif": tp}), "klinik_etki")
    kaydet(fig, "N3_klinik_etki", dil)

def fig_nomogram(dil):       # N4
    imp = fin.named_steps["i"]; sc = fin.named_steps["s"]
    rows = []
    for j, v in enumerate(SEL):
        x = X[v].dropna(); lo, hi = np.percentile(x, [1, 99])
        c_lo = beta[j] * (lo - sc.mean_[j]) / np.sqrt(sc.var_[j]); c_hi = beta[j] * (hi - sc.mean_[j]) / np.sqrt(sc.var_[j])
        rows.append((v, lo, hi, c_lo, c_hi))
    rng_max = max(abs(r[4] - r[3]) for r in rows); pts = lambda c, cmin: 100 * (c - cmin) / rng_max
    fig, ax = plt.subplots(figsize=(W2, 7.2)); ax.axis("off")
    n = len(rows) + 3; yy = n
    ax.plot([0, 100], [yy, yy], color=INK, lw=0.8)
    for t_ in range(0, 101, 10):
        ax.plot([t_, t_], [yy, yy + 0.15], color=INK, lw=0.6); ax.text(t_, yy + 0.3, str(t_), ha="center", fontsize=6)
    ax.text(-2, yy, T("Points", "Puan", dil), ha="right", va="center", fontsize=7, weight="bold")
    cmins = []
    for k_, (v, lo, hi, c_lo, c_hi) in enumerate(rows):
        yy = n - 1 - k_; cmin = min(c_lo, c_hi); cmins.append(cmin)
        x0, x1 = pts(c_lo, cmin), pts(c_hi, cmin)
        ax.plot([min(x0, x1), max(x0, x1)], [yy, yy], color=C1, lw=1.2)
        uz = abs(x1 - x0); nt = 4 if uz >= 30 else (3 if uz >= 14 else 2)
        for val in np.linspace(lo, hi, nt):
            c = beta[k_] * (val - sc.mean_[k_]) / np.sqrt(sc.var_[k_]); xp = pts(c, cmin)
            ax.plot([xp, xp], [yy, yy + 0.12], color=C1, lw=0.6)
            ax.text(xp, yy + 0.22, ("%.3g" % val).replace(".", ",") if dil == "tr" else "%.3g" % val, ha="center", fontsize=5.2, color=INK2)
        ax.text(-2, yy, ad(v, dil), ha="right", va="center", fontsize=6.5)
    tot_min = 0; tot_max = sum(abs(r[4] - r[3]) for r in rows) * 100 / rng_max
    lp_min = b0 + sum(cmins)
    yy = 1.2
    ax.plot([0, 100], [yy, yy], color=INK, lw=0.8)
    for t_ in np.linspace(tot_min, tot_max, 11):
        xp = 100 * t_ / tot_max; ax.plot([xp, xp], [yy, yy + 0.15], color=INK, lw=0.6); ax.text(xp, yy + 0.3, "%d" % t_, ha="center", fontsize=6)
    ax.text(-2, yy, T("Total points", "Toplam puan", dil), ha="right", va="center", fontsize=7, weight="bold")
    yy = 0.2; ax.plot([0, 100], [yy, yy], color=INK, lw=0.8)
    for kk, pr_ in enumerate([0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]):
        lp = np.log(pr_ / (1 - pr_)); tpts = (lp - lp_min) * 100 / rng_max
        if 0 <= tpts <= tot_max:
            xp = 100 * tpts / tot_max; ax.plot([xp, xp], [yy, yy + 0.15], color=C2, lw=0.8)
            ax.text(xp, yy - (0.35 if kk % 2 == 0 else 0.7), dec(pr_, dil, 2), ha="center", fontsize=6, color=C2)
    ax.text(-2, yy, T("Probability", "Olasılık", dil), ha="right", va="center", fontsize=7, weight="bold")
    ax.set_xlim(-45, 104); ax.set_ylim(-1.0, n + 0.8)
    kaydet(fig, "N4_nomogram", dil)

def fig_upset(dil):          # N5
    comp = {T("LA", "LA", dil): la, "LVEDD": lv, "EF<50%": ef_, "QTc": qtc, "QRS": qrs}
    names = list(comp); M = np.column_stack([comp[k] for k in names]).astype(int)
    pos = M[M.sum(1) > 0]; combos = pd.Series([tuple(r) for r in pos]).value_counts().head(12)
    fig = plt.figure(figsize=(W2 * 0.8, 3.2)); gs = gridspec.GridSpec(2, 1, height_ratios=[2, 1.1], hspace=0.05)
    a = fig.add_subplot(gs[0]); b = fig.add_subplot(gs[1], sharex=a); xs = np.arange(len(combos))
    a.bar(xs, combos.values, color=C1, width=0.6)
    for x_, v in zip(xs, combos.values): a.text(x_, v + 1, str(v), ha="center", fontsize=6.5)
    a.set_ylabel(T("Patients", "Hasta", dil)); a.grid(axis="x", visible=False); plt.setp(a.get_xticklabels(), visible=False)
    for x_, cmb in zip(xs, combos.index):
        on = [i for i, v in enumerate(cmb) if v]
        b.scatter([x_] * len(names), range(len(names)), color=GRID, s=18, zorder=2)
        b.scatter([x_] * len(on), on, color=INK, s=18, zorder=3)
        if len(on) > 1: b.plot([x_, x_], [min(on), max(on)], color=INK, lw=1)
    b.set_yticks(range(len(names))); b.set_yticklabels(["%s (n=%d)" % (k, comp[k].sum()) for k in names])
    b.set_xticks([]); b.grid(False); b.invert_yaxis()
    csv(pd.DataFrame({"kombinasyon": [str(c) for c in combos.index], "n": combos.values}), "uc_nokta_kesisim")
    kaydet(fig, "N5_uc_nokta_kesisim", dil)

def fig_incr(dil):           # N6
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W2, 2.7))
    for pp, c, ls, lb in [(p, C1, "-", T("20-variable model", "20 değişkenli model", dil)), (pk, C2, "--", T("Bedside reference (7 variables)", "Yatak başı referans (7 değişken)", dil))]:
        fpr, tpr, _ = roc_curve(yv, pp); a1.plot(fpr, tpr, color=c, ls=ls, label="%s, %s" % (lb, dec(roc_auc_score(yv, pp), dil)))
    a1.plot([0, 1], [0, 1], color=GRID, lw=0.8); a1.set_aspect("equal"); a1.legend(loc="lower right", fontsize=6)
    a1.set_xlabel(T("1 − specificity", "1 − özgüllük", dil)); a1.set_ylabel(T("Sensitivity", "Duyarlılık", dil))
    a1.set_title(T("(a) ROC curves", "(a) ROC eğrileri", dil), loc="left")
    a2.hist(dd, bins=40, color=C1, edgecolor="white")
    lo, hi = np.percentile(dd, [2.5, 97.5])
    a2.axvline(0, color=INK, lw=0.9); a2.axvline(lo, color=C2, ls="--", lw=0.9); a2.axvline(hi, color=C2, ls="--", lw=0.9)
    a2.set_xlabel(T("ΔAUROC (model − reference), paired bootstrap", "ΔAUROC (model − referans), eşleştirilmiş önyükleme", dil))
    a2.set_ylabel(T("Bootstrap replicates", "Önyükleme tekrarı", dil))
    a2.set_title(T("(b) Paired bootstrap of ΔAUROC", "(b) ΔAUROC eşleştirilmiş önyükleme", dil), loc="left")
    a2.text(0.02, 0.97, T("Δ = %s\n95%% CI %s to %s\nP(Δ > 0) = %s", "Δ = %s\n%%95 GA %s ile %s\nP(Δ > 0) = %s", dil)
            % (dec(AUC - AK, dil).replace("-", "−"), dec(lo, dil).replace("-", "−"), dec(hi, dil).replace("-", "−"), dec((dd > 0).mean(), dil, 2)),
            transform=a2.transAxes, va="top", fontsize=7, color=INK, zorder=10,
            bbox=dict(boxstyle="square,pad=0.35", fc="white", ec=GRID, lw=0.6))
    a2.set_ylim(0, a2.get_ylim()[1] * 1.28)   # kutu cubuklarin ustunde kalsin
    fig.tight_layout(); kaydet(fig, "N6_ek_deger", dil)

def fig_missing(dil):        # N7
    mi = (X.isna().mean() * 100).sort_values(ascending=False)
    mi = mi[mi > 0]
    fig, ax = plt.subplots(figsize=(W2, 2.6))
    col = [C2 if v in SEL else C1 for v in mi.index]
    ax.bar(range(len(mi)), mi.values, color=col, width=0.8)
    ax.axhline(30, color=INK2, lw=0.8, ls="--")
    ax.set_xticks([]); ax.grid(axis="x", visible=False)
    ax.set_ylabel(T("Missing (%)", "Eksik (%)", dil))
    ax.set_xlabel(T("%d candidate variables with any missingness, sorted (orange = in final model)",
                    "Eksik değeri olan %d aday değişken, sıralı (turuncu = nihai modelde)", dil) % len(mi))
    for i, v in enumerate(mi.index):
        if v in SEL and mi[v] > 30: ax.text(i, mi[v] + 1.5, ad(v, dil), rotation=90, ha="center", va="bottom", fontsize=5.5)
    ax.set_ylim(0, 100)
    kaydet(fig, "N7_eksik_veri", dil)

TUM = [fig_F, fig_corr, fig_forest_beta, fig_models, fig_roc, fig_k, fig_cal, fig_cm, fig_splits, fig_lc,
       fig_freq, fig_pr, fig_dca, fig_sens_forest, fig_risk_dist, fig_cic, fig_nomogram, fig_upset, fig_incr, fig_missing]
SADECE = [x.strip() for x in os.environ.get("KVH_SADECE", "").split(",") if x.strip()]
ADLAR = {"N4": fig_nomogram, "N6": fig_incr}
if SADECE:
    TUM = [ADLAR[x] for x in SADECE if x in ADLAR]
for dil in ("en", "tr"):
    P("Sekiller (%s)..." % dil)
    for fn in TUM:
        try:
            fn(dil)
        except Exception as e:
            P("   HATA %s: %s" % (fn.__name__, e))
P("")
P("KONTROL: AUROC %.3f | referans %.3f | fark %+.3f [%.3f, %.3f]" % (AUC, AK, AUC - AK, *np.percentile(dd, [2.5, 97.5])))
with open(os.path.join(OUT, "sekil_rapor.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(_LOG))
P("Bitti: %s" % OUT)
