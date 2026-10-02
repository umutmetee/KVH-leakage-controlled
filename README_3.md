# Retrospective classification of cardiac-abnormality status from routine endocrine and laboratory data

Analysis code for:

> U. Mete, C. B. Kalaycı, S. M. Fenkci, I. Tekin and S. Taban Mete, "Retrospective Classification of Cardiac Abnormality Status from Routine Endocrine and Laboratory Data: A Leakage-Controlled Machine Learning Study" (manuscript submitted for publication).

Archived on Zenodo: https://doi.org/10.5281/zenodo.23000553

The repository contains **code only**. The study data come from routine patient care at a single endocrinology and metabolism clinic and cannot be posted publicly (see *Data availability* below). No patient-level data, identifiers or outputs derived from individual patients are included.

## What the scripts do

| Script | Reproduces |
|---|---|
| `scripts/KVH_TAM_ANALIZ.py` | Every number in the manuscript: endpoint derivation from the five echocardiographic/ECG criteria, leakage-control whitelist, ANOVA ranking with analyte-family deduplication (k = 20), the algorithm comparison, the final L2 logistic regression (C = 0.01), Youden threshold from out-of-fold training predictions, calibration, 20 random partitions, learning curves, selector sensitivity, bedside reference model, decision curve analysis, restricted endpoints, multiple imputation and missingness-indicator analyses, selection-inclusive optimism bootstrap. |
| `scripts/KVH_EK_DOGRULAMA.py` | Independent re-computation of the supplementary checks (alternative selectors, decision curve table, Platt variants, extreme deciles) with an automatic comparison against the published values. |
| `scripts/KVH_REVIZYON_EK.py` | Bootstrap CIs for the ensembles, post-Platt calibration slope, paired DeLong tests, VIF and family correlations. |
| `scripts/algoritmalar/Model_1..5_*.py` | One script per model in the main article: logistic regression (primary), SVM, random forest, gradient boosting (Table 3) and the seven-variable bedside reference model (Section 3.8). |
| `scripts/algoritmalar/Model_S1..S9_*.py` | One script per additional algorithm in Supplementary Table S1. All model scripts share `model_ortak.py` and write `model_sonuclari.xlsx`; `tum_modelleri_calistir.py` runs them all. |
| `scripts/algoritmalar/tablo1_ek.py` | Table 1 medians [IQR] and body mass index derived from height and weight (bedside-model sensitivity check). |
| `scripts/sekil_betikleri/ek_hakem_analizleri_2.py` | Single-time-point models, missingness thresholds, sex-stratified split and the full-cohort equation (Section 3.9, Table S6). |
| `scripts/sekil_betikleri/00_sekil_verisi_uret.py` | Runs the analysis once and writes all numbers needed for the figures to `sekil_verileri.xlsx` (no patient identifiers). |
| `scripts/sekil_betikleri/Figure_*.py` | One script per figure (Figures 1–9 and S1–S11); each reads only its own sheet of `sekil_verileri.xlsx` and writes a 600 dpi PNG and a PDF. `tum_sekilleri_ciz.py` runs them all. |
| `scripts/sekil_betikleri/ek_hakem_analizleri.py` | Hyperparameter tuning within the training data, nested bedside-plus-laboratory model and sex-adjusted model (Supplementary Table S3; Sections 3.3, 3.8 and 3.9). |
| `scripts/sekil_betikleri/esik_duyarlilik.py` | Endpoint-definition sensitivity analysis (Supplementary Table S4). |
| `scripts/KVH_SEKILLER.py` | Earlier all-in-one figure script, kept for reference; superseded by `scripts/sekil_betikleri`. |

All random seeds are fixed (`SEED = 42`); the same data give the same numbers. Each script prints a control line at start-up (held-out AUROC 0.755, threshold τ = 0.428) so a user can confirm the pipeline is intact before reading further output.

## Requirements

Python ≥ 3.9 and the packages in `requirements.txt`:

```
pip install -r requirements.txt
```

## Running

Place the two input workbooks (`sizintisiz_veri.xlsx`, `aiveri2026_haz.xlsx`) in the same folder as the scripts (the scripts in `sekil_betikleri` also look in the parent folders), then:

```
python KVH_TAM_ANALIZ.py                      # -> cikti/rapor.txt and CSV tables
python sekil_betikleri/00_sekil_verisi_uret.py
python sekil_betikleri/tum_sekilleri_ciz.py   # -> sekil_betikleri/cikti_sekil/en, cikti_sekil/tr
```

Output labels and console messages are partly in Turkish (the working language of the study team). Console tags such as `[Tablo V]` refer to an earlier numbering of the tables; the current manuscript numbers tables 1–6 and S1–S4.

## Using the published model on new data

The fitted equation (intercept, standardized coefficients, training means, SDs and imputation medians) is given in Table 5 of the paper. The linear predictor is LP = −0.4605 + Σ βᵢ·zᵢ with zᵢ = (xᵢ − meanᵢ)/SDᵢ, and p = 1/(1 + e^−LP). An optional two-parameter Platt recalibration is p_cal = 1/(1 + e^−(0.1455 + 1.3719·LP)).

## Data availability

The de-identified dataset can be shared with qualified researchers on reasonable request to the corresponding author (umete15@posta.pau.edu.tr), subject to the institutional data-sharing agreements that govern it.

## License

Code: MIT License (see `LICENSE`).
