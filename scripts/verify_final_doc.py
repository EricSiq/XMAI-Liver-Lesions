import docx
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

for name in [
    'XMAI for Differential Diagnosis of Focal Liver Lesions - Journal Draft v2.docx',
    'XMAI for Differential Diagnosis of Focal Liver Lesions - Journal Draft.docx'
]:
    print(f"=== VERIFICATION: {name} ===")
    doc = docx.Document(name)
    
    # Check haemangioma count
    haem_count = sum(p.text.lower().count('haemangioma') for p in doc.paragraphs)
    for t in doc.tables:
        for r in t.rows:
            for c in r.cells:
                haem_count += c.text.lower().count('haemangioma')
    print('Remaining "haemangioma" occurrences:', haem_count)
    
    # Check Shapley formula
    print('Shapley formula in P36 contains "S ⊆ M \\ {m}"?', 'S ⊆ M \\ {m}' in doc.paragraphs[36].text)
    
    # Check Abstract
    print('\n[Abstract P7 Snippet]:')
    print(' ', doc.paragraphs[7].text[:260])
    
    # Check Table 3 A4
    t3 = doc.tables[2]
    print('\n[Table 3 A4 row]:')
    print(' ', [c.text for c in t3.rows[3].cells])
    
    # Check Results P43
    print('\n[Results P43 Snippet]:')
    print(' ', doc.paragraphs[43].text[:240])
    
    # Check Comparative P50
    print('\n[Comparative P50 Snippet]:')
    print(' ', doc.paragraphs[50].text[-260:])
    
    # Check Table 7 A4
    t7 = doc.tables[6]
    print('\n[Table 7 A4 row]:')
    print(' ', [c.text for c in t7.rows[4].cells])
    
    # Check Conclusion P56
    print('\n[Conclusion P56 Snippet]:')
    print(' ', doc.paragraphs[56].text[:240])
    print('\n' + '='*60 + '\n')
