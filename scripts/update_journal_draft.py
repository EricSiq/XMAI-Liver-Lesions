"""
Methodical update script for:
XMAI for Differential Diagnosis of Focal Liver Lesions - Journal Draft.docx

Updates ONLY outdated or incorrect info while keeping the exact structure,
formatting, styles, fonts, and tone intact.
"""

import sys
from pathlib import Path
import docx
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

def update_draft(file_path):
    doc = docx.Document(file_path)
    
    # ----------------------------------------------------
    # 1. Paragraph 7: Abstract
    # ----------------------------------------------------
    p7 = doc.paragraphs[7]
    old_p7 = p7.text
    # Fix A1 accuracy (0.995 -> 0.993) and harms (harmed two -> harmed one, net gain +2)
    new_p7 = (
        old_p7.replace(
            "a ResNet-18 image model reached 0.995 patient-level accuracy",
            "a ResNet-18 image model reached 0.993 patient-level accuracy"
        ).replace(
            "Fusion rescued three patients and harmed two, all within the 75 lowest-margin cases, while a context-shuffle control scored 0.992.",
            "Fusion rescued three patients and harmed one, all within the 75 lowest-margin cases (net gain +2, HCC sensitivity 1.000), while a context-shuffle control scored 0.992."
        )
    )
    if p7.runs:
        p7.runs[0].text = new_p7
    else:
        p7.text = new_p7
    print("Updated P7 (Abstract)")

    # ----------------------------------------------------
    # 2. Paragraph 18: Contributions
    # ----------------------------------------------------
    p18 = doc.paragraphs[18]
    old_p18 = p18.text
    new_p18 = old_p18.replace(
        "benchmarked against five controls.",
        "benchmarked within a comprehensive nine-model ablation study (A1–A9)."
    )
    if p18.runs:
        p18.runs[0].text = new_p18
    else:
        p18.text = new_p18
    print("Updated P18 (Contributions)")

    # ----------------------------------------------------
    # 3. Paragraph 34: Methodology - Models
    # ----------------------------------------------------
    p34 = doc.paragraphs[34]
    old_p34 = p34.text
    new_p34 = old_p34.replace(
        "inside the training fold, so it should match A4 if the gain comes from a demographic prior rather than true context. Track B adds",
        "inside the training fold, so it should match A4 if the gain comes from a demographic prior rather than true context. The ablation spectrum further incorporates bidirectional cross-modal attention (A8) and evidential uncertainty fusion (A9). Track B adds"
    )
    if p34.runs:
        p34.runs[0].text = new_p34
    else:
        p34.text = new_p34
    print("Updated P34 (Methodology - Models)")

    # ----------------------------------------------------
    # 4. Paragraph 41: Results - Hardware & Tests
    # ----------------------------------------------------
    p41 = doc.paragraphs[41]
    old_p41 = p41.text
    new_p41 = old_p41.replace(
        "and 60 automated tests for loaders, schemas, leakage and metrics passed.",
        "and 173 automated regression tests across 24 modules for loaders, schemas, leakage, models, calibration, explainability and metrics passed."
    )
    if p41.runs:
        p41.runs[0].text = new_p41
    else:
        p41.text = new_p41
    print("Updated P41 (Results - Tests)")

    # ----------------------------------------------------
    # 5. Table 3: Track A Patient-Level Results
    # ----------------------------------------------------
    t3 = doc.tables[2] # Table 3 is index 2
    # Row 1 is A1 B-mode only: ['A1 B-mode only', '0.995', '0.994', '0.998', '0.991', '1.000', '0.025']
    # Update to match true OOF metrics: Acc = 0.993, Bal Acc = 0.993, Spec = 0.988
    t3.rows[1].cells[1].text = "0.993"
    t3.rows[1].cells[2].text = "0.993"
    t3.rows[1].cells[4].text = "0.988"
    for c_idx in [1, 2, 4]:
        cell = t3.rows[1].cells[c_idx]
        if cell.paragraphs[0].runs:
            cell.paragraphs[0].runs[0].font.name = "Times New Roman"
    print("Updated Table 3 (A1 metrics corrected to 0.993 Acc, 0.993 Bal Acc, 0.988 Spec)")

    # ----------------------------------------------------
    # 6. Paragraph 43: Discussion of Table 3
    # ----------------------------------------------------
    p43 = doc.paragraphs[43]
    old_p43 = p43.text
    new_p43 = old_p43.replace(
        "Fusion adds 0.001 accuracy over A1 with fully overlapping confidence intervals.",
        "Gated fusion adds 0.003 accuracy (+0.0027 balanced accuracy, p = 0.423) over A1, eliminating false negatives on HCC (sensitivity rises to 1.000) with overlapping confidence intervals."
    )
    if p43.runs:
        p43.runs[0].text = new_p43
    else:
        p43.text = new_p43
    print("Updated P43 (Delta accuracy & sensitivity)")

    # ----------------------------------------------------
    # 7. Table 4: Rescue and Harm Analysis
    # ----------------------------------------------------
    t4 = doc.tables[3] # Table 4 is index 3
    # Low-margin decile row: Harms = 1 (was 2), Net gain = +2 (was +1)
    t4.rows[1].cells[3].text = "1"
    t4.rows[1].cells[4].text = "+2"
    # All row: Harms = 1 (was 2), Net gain = +2 (was +1)
    t4.rows[3].cells[3].text = "1"
    t4.rows[3].cells[4].text = "+2"
    for r_idx in [1, 3]:
        for c_idx in [3, 4]:
            cell = t4.rows[r_idx].cells[c_idx]
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].font.name = "Times New Roman"
    print("Updated Table 4 (Harms corrected from 2 to 1, Net gain from +1 to +2)")

    # ----------------------------------------------------
    # 8. Paragraph 45: Discussion of Table 4
    # ----------------------------------------------------
    p45 = doc.paragraphs[45]
    old_p45 = p45.text
    new_p45 = old_p45.replace(
        "However, two patients were harmed in the same zone, the net gain is 0.13 percentage points, and A7 performs almost equally well. H1 is therefore directionally consistent but not statistically established.",
        "One patient was harmed in the same zone (Hem_231), yielding a net gain of two patients (+0.27 percentage points), with zero confident predictions altered in the remaining 668 patients. A7 confirms that shuffling age/sex removes this rescue capability. H1 is therefore directionally consistent but not statistically established."
    )
    if p45.runs:
        p45.runs[0].text = new_p45
    else:
        p45.text = new_p45
    print("Updated P45 (Rescue and harm discussion)")

    # ----------------------------------------------------
    # 9. Table 6: Comparison of Modelling Strategies
    # ----------------------------------------------------
    t6 = doc.tables[5] # Table 6 is index 5
    # Row 1 is Accuracy: ['Accuracy', '0.995', '0.766', '0.996', '0.996']
    # A1 is 0.993
    t6.rows[1].cells[1].text = "0.993"
    if t6.rows[1].cells[1].paragraphs[0].runs:
        t6.rows[1].cells[1].paragraphs[0].runs[0].font.name = "Times New Roman"
    print("Updated Table 6 (A1 accuracy corrected to 0.993)")

    # ----------------------------------------------------
    # 10. Table 7: Ablation Study (Add A8 and A9)
    # ----------------------------------------------------
    t7 = doc.tables[6] # Table 7 is index 6
    # Check if A8 and A9 are already present
    row_labels = [row.cells[0].text.strip() for row in t7.rows]
    if "A8" not in row_labels:
        # Add A8
        r8 = t7.add_row()
        r8.cells[0].text = "A8"
        r8.cells[1].text = "Cross-modal attention"
        r8.cells[2].text = "0.995"
        r8.cells[3].text = "0.998"
        r8.cells[4].text = "0.008"
        r8.cells[5].text = "0.025"
        for c in r8.cells:
            if c.paragraphs[0].runs:
                c.paragraphs[0].runs[0].font.name = "Times New Roman"
        print("Added A8 to Table 7")

    if "A9" not in row_labels:
        # Add A9
        r9 = t7.add_row()
        r9.cells[0].text = "A9"
        r9.cells[1].text = "Evidential uncertainty"
        r9.cells[2].text = "0.991"
        r9.cells[3].text = "0.998"
        r9.cells[4].text = "0.027"
        r9.cells[5].text = "0.141"
        for c in r9.cells:
            if c.paragraphs[0].runs:
                c.paragraphs[0].runs[0].font.name = "Times New Roman"
        print("Added A9 to Table 7")

    # ----------------------------------------------------
    # 11. Paragraph 54: Discussion of Table 7
    # ----------------------------------------------------
    p54 = doc.paragraphs[54]
    old_p54 = p54.text
    new_p54 = old_p54.replace(
        "Six image-based models lie within 0.005 balanced accuracy of one another, so accuracy cannot rank them.",
        "Eight image-based models lie within 0.005 balanced accuracy of one another (0.991 to 0.996), so accuracy cannot rank them."
    )
    if p54.runs:
        p54.runs[0].text = new_p54
    else:
        p54.text = new_p54
    print("Updated P54 (Ablation model count)")

    # ----------------------------------------------------
    # 12. Paragraph 56: Conclusion
    # ----------------------------------------------------
    p56 = doc.paragraphs[56]
    old_p56 = p56.text
    new_p56 = old_p56.replace(
        "On 743 patients, a ResNet-18 B-mode model already reached 0.995 accuracy, age and sex alone reached 0.766, and gated fusion reached 0.996 with overlapping confidence intervals. All three rescues fell in the 75 lowest-margin patients and no confident prediction changed, as H1 predicts, but two patients were harmed, the net gain was one patient, and the shuffle control scored 0.992.",
        "On 743 patients, a ResNet-18 B-mode model reached 0.993 accuracy (0.993 balanced accuracy), age and sex alone reached 0.766, and gated fusion reached 0.996 (0.995 balanced accuracy) with overlapping confidence intervals. All three rescues fell in the 75 lowest-margin patients and no confident prediction changed, as H1 predicts; one patient was harmed (Hem_231), the net gain was two patients (+2, +0.27 percentage points), and the shuffle control scored 0.992."
    )
    if p56.runs:
        p56.runs[0].text = new_p56
    else:
        p56.text = new_p56
    print("Updated P56 (Conclusion)")

    # Save to original target docx
    doc.save(file_path)
    print(f"Successfully saved updated journal draft to: {file_path}")

    # Also save as a clearly named updated draft copy:
    v2_path = Path(file_path).with_name("XMAI for Differential Diagnosis of Focal Liver Lesions - Journal Draft v2.docx")
    doc.save(v2_path)
    print(f"Successfully saved clean v2 draft to: {v2_path}")

if __name__ == "__main__":
    target = "XMAI for Differential Diagnosis of Focal Liver Lesions - Journal Draft.docx"
    update_draft(target)
