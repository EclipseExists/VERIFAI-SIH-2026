# Forensics Module

The forensics module analyzes document images for possible visual inconsistencies.

## Current Forensic Signals

### 1. Error Level Analysis (ELA)

ELA recompresses the input image at a known JPEG quality and compares it with the original image.

Differences in compression levels may indicate areas that require further investigation.

ELA is an indicative forensic signal and does not by itself prove forgery.

Output:
- `ela_output.jpg`

### 2. Noise Consistency Analysis

Noise analysis compares the original image with a blurred version to visualize local texture and noise differences.

Inconsistent local patterns may indicate areas requiring further investigation.

Output:
- `noise_output.jpg`

## Combined Analysis

`forensic_analysis.py` runs both forensic signals and returns a structured result.

Each signal contains:

- Signal type
- Score
- Severity
- Anomaly status
- Evidence path
- Explanation

## Limitations

ELA and noise analysis provide forensic indicators and evidence, not definitive proof that a document is forged.

The final risk assessment should combine multiple signals and remain subject to human officer review.
At the current stage, score and anomaly status are placeholders for integration with the risk engine. The module currently generates forensic evidence rather than making a definitive forgery decision.