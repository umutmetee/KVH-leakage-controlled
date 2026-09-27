# Retrospective classification of cardiac-abnormality status from routine endocrine and laboratory data

Analysis code for:

> U. Mete and C. B. Kalaycı, "Retrospective Classification of Cardiac Abnormality Status from Routine Endocrine and Laboratory Data: A Leakage-Controlled Machine Learning Study," *IEEE Access* (under review).

The repository contains **code only**. The study data come from routine patient care at a single endocrinology and metabolism clinic and cannot be posted publicly (see *Data availability* below). No patient-level data, identifiers or outputs derived from individual patients are included.

## What the scripts do

| Script | Reproduces |
|---|---|
| `scripts/KVH_TAM_ANALIZ.py` | Every number in the manuscript: endpoint derivation from the five echocardiographic/ECG criteria, leakage-control whitelist, ANOVA ranking with analyte-family deduplication (k = 20), the 13-model comparison, the final L2 logistic regression (C = 0.01), Youden threshold from out-of-fold training predictions, calibration, 20 random partitions, learning curves, selector sensitivity, bedside reference model, decision curve analysis, restricted endpoints, MICE and missingness-indicator analyses, selection-inclusive optimism bootstrap. |
| `scripts/KVH_EK_DOGRULAMA.py` | Independent re-computation of the supplementary checks (alternative selectors, DCA table, Platt variants, extreme deciles) with an automatic comparison against the published values. |
| `scripts/KVH_SEKILLER.py` | All figures (English and Turkish labels, 600 dpi PNG and vector PDF) and the numbers behind each figure as CSV. |
| `scripts/KVH_REVIZYON_EK.py` | Revision analyses: bootstrap CIs for the ensembles, post-Platt calibration slope, paired DeLong tests, VIF and family correlations. |

All random seeds are fixed (`SEED = 42`); the same data give the same numbers. Each script prints a control line at start-up (held-out AUROC 0.755, threshold τ = 0.428) so a user can confirm the pipeline is intact before reading further output.

## Requirements

Python ≥ 3.9 and the packages in `requirements.txt`:

```
pip install -r requirements.txt
```

## Running

Place the two input workbooks (`sizintisiz_veri.xlsx`, `aiveri2026_haz.xlsx`) in the same folder as the scripts, then:

```
python KVH_TAM_ANALIZ.py        # -> cikti/rapor.txt and CSV tables
python KVH_SEKILLER.py          # -> cikti_sekil/en, cikti_sekil/tr
```

Output labels and console messages are partly in Turkish (the working language of the study team); tags such as `[Tablo V]` or `[III-E]` map each printed line to the corresponding table or section of the manuscript.

## Using the published model on new data

The fitted equation (intercept, standardized coefficients, training means, SDs and imputation medians) is given in Table V of the paper. The linear predictor is LP = −0.4605 + Σ βᵢ·zᵢ with zᵢ = (xᵢ − meanᵢ)/SDᵢ, and p = 1/(1 + e^−LP). An optional two-parameter Platt recalibration is p_cal = 1/(1 + e^−(0.1455 + 1.3719·LP)).

## Data availability

The de-identified dataset can be shared with qualified researchers on reasonable request to the corresponding author (umete15@posta.pau.edu.tr), subject to the institutional data-sharing agreements that govern it.

## License

Code: MIT License (see `LICENSE`).
