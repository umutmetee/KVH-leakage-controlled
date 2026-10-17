# Leakage-controlled classification of cardiac abnormalities from routine laboratory data

Code for the final model of:

> Mete U, Kalaycı CB, Fenkci SM, Tekin I, Taban Mete S. *Retrospective Classification of Echocardiographic and Electrocardiographic Abnormalities from Routine Endocrine and Laboratory Data: A Leakage-Controlled Machine Learning Study* (submitted).

`kvh_model.py` derives the composite endpoint, builds the candidate set, selects 20 variables in the training data only (ANOVA F-statistic with analyte-family deduplication), fits the L2-penalised logistic regression (C = 0.01) and derives the decision threshold. It prints a control line (test AUROC 0.731, τ = 0.387) and writes the fitted equation to `model_equation.csv`.

The repository contains **code only**. The patient data cannot be made public; they can be shared with qualified researchers on request to the corresponding author, subject to institutional agreements. Scripts for the sensitivity analyses are also available on request.

Additional scripts (same pipeline, shared module `model_ortak.py`; data files not included):

- `Model_1_...py` to `Model_5_...py`, `Model_S1_...py` to `Model_S9_...py`: the 13 algorithms and the bedside reference model on the same 187 test patients; `tum_modelleri_calistir.py` runs them all and writes `model_sonuclari.xlsx`.
- `duyarlilik_1233.py`: adds the 301 patients set aside before development to the training partition and re-evaluates on the same test patients (AUROC 0.725 vs 0.731), and repeats over 20 random splits of the pooled cohort (mean 0.734 vs 0.744).

To apply the published model to new patients, use the equation in Table 6 of the article or the spreadsheet calculator (Supplementary File S2).

```
pip install -r requirements.txt
python kvh_model.py
```

License: MIT.
