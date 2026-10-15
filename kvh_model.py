# -*- coding: utf-8 -*-
"""
kvh_model.py - fits the final model of the article (minimal reproduction code).

Steps: composite endpoint from five echocardiographic/ECG criteria; candidate set
(earlier/latest laboratory values + static variables; outcome-defining variables are
not in the input file); stratified 80/20 split (seed 42); ANOVA-F ranking with
analyte-family deduplication in the training data only (k = 20); L2 logistic
regression (C = 0.01) with median imputation and standardisation; Youden threshold
from out-of-fold training predictions.

Input files (not public; available on request): sizintisiz_veri.xlsx, aiveri2026_haz.xlsx
Usage: python kvh_model.py
Expected control line: test AUROC 0.731 | tau 0.387
"""
import os, re, sys, warnings
import numpy as np, pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score, roc_curve
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
def find(name):
    k = HERE
    while True:
        for c in (os.path.join(k, name), os.path.join(k, "07_Analiz", name)):
            if os.path.exists(c): return c
        if os.path.dirname(k) == k: sys.exit("Input file not found: " + name)
        k = os.path.dirname(k)

SEED, K, C = 42, 20, 0.01
STATIC = ["diyabet süresi", "YAŞ", "CİNSİYET", "sigara", "sistolık kan basıncı",
          "diastolik kan basıncı", "boy", "kılo", "bmı"]

d = pd.read_excel(find("sizintisiz_veri.xlsx")); raw = pd.read_excel(find("aiveri2026_haz.xlsx"))
assert (pd.to_numeric(d["HASTA_NO"]) == pd.to_numeric(raw["HASTA_NO"])).all()

# endpoint: any of five pre-specified criteria (flags applied during data preparation)
num = lambda c: pd.to_numeric(raw[c], errors="coerce")
y = pd.Series(((num("la abn").fillna(0) > 0) | (num("lvedd abn").fillna(0) > 0)
               | ((num("ef") < 50) | (num("ef (E)") < 50)).fillna(False)
               | (num("qtc abn").fillna(0) > 0) | (num("qrs abn").fillna(0) > 0)).astype(int).values)

# candidates: ESK_ = latest draw, YEN_ = earlier draw, plus static variables
Xa = d.drop(columns=["kalp hastalığı"])
cols = [c for c in Xa.columns if str(c).startswith(("ESK_", "YEN_"))] + [c for c in STATIC if c in Xa.columns]
X = Xa[cols].apply(pd.to_numeric, errors="coerce")
X = X.drop(columns=X.columns[X.isna().all()].tolist()).reset_index(drop=True)

tr, te = train_test_split(np.arange(len(X)), test_size=0.2, stratify=y, random_state=SEED)
Xtr, Xte, ytr, yte = X.iloc[tr], X.iloc[te], y.iloc[tr], y.iloc[te]

def family(n):
    s = re.sub(r"\s+", " ", re.sub(r"^(ESK_|YEN_)\s*", "", str(n)).strip().lower())
    if "hba1c" in s: return "hba1c"
    if s.startswith("üre") or s.startswith("bun"): return "urea_bun"
    if "tgfr" in s or "kreatinin" in s: return "renal"
    if "rdw" in s: return "rdw"
    if s in ("neu%", "lym%", "nlr"): return "leukocyte"
    if "non hdl" in s or s == "kolesterol" or "ldl" in s: return "atherogenic_lipid"
    return s

def select(Xs, ys, k):
    F = pd.Series(f_classif(Xs.fillna(Xs.median()), ys)[0], index=Xs.columns)
    fam = {}
    for c in Xs.columns: fam.setdefault(family(c), []).append(c)
    best = {f: max(g, key=lambda c: F.get(c, -1)) for f, g in fam.items()}
    out, used = [], set()
    for c in sorted(F.index, key=lambda z: -F[z]):
        f = family(c)
        if f in used: continue
        if best[f] not in out: out.append(best[f]); used.add(f)
        if len(out) >= k: break
    return out, F

pipe = lambda: Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler()),
                         ("lr", LogisticRegression(C=C, max_iter=2000))])
SEL, F = select(Xtr, ytr, K)
model = pipe().fit(Xtr[SEL], ytr)
auc = roc_auc_score(yte, model.predict_proba(Xte[SEL])[:, 1])
oof = cross_val_predict(pipe(), Xtr[SEL], ytr, method="predict_proba",
                        cv=StratifiedKFold(5, shuffle=True, random_state=SEED))[:, 1]
f_, t_, th = roc_curve(ytr, oof); tau = th[np.argmax(t_ - f_)]
print("Control: test AUROC %.3f | tau %.3f (expected 0.731 / 0.387)" % (auc, tau))

imp, sc, lr = model.named_steps["impute"], model.named_steps["scale"], model.named_steps["lr"]
eq = pd.DataFrame({"variable": SEL, "F": [F[c] for c in SEL], "median": imp.statistics_,
                   "mean": sc.mean_, "SD": sc.scale_, "beta": lr.coef_[0]})
print("Intercept %.4f" % lr.intercept_[0]); print(eq.round(4).to_string(index=False))
eq.to_csv(os.path.join(HERE, "model_equation.csv"), index=False)
