import inspect
import sys
from pathlib import Path

files_to_check = [
    "tests/integration/test_live_surveillance_qualification.py",
    "tests/integration/test_provenance_and_active_risk_isolation.py",
    "tests/integration/test_restart_recovery_and_cardinality.py",
    "tests/unit/test_operational_audit.py",
    "tests/unit/test_api.py",
    "tests/unit/test_forecasting_scientific_reconciliation.py",
    "tests/test_evidence_first_refactor.py",
    "tests/unit/test_data_integrity_refactor.py",
]

print("=" * 80)
print("TEST INTEGRITY VERIFICATION AUDIT")
print("=" * 80)

for fpath in files_to_check:
    p = Path(fpath)
    if not p.exists():
        print(f"File not found: {fpath}")
        continue
    content = p.read_text(encoding="utf-8")
    asserts = [line.strip() for line in content.splitlines() if line.strip().startswith("assert ")]
    print(f"\nFile: {fpath} ({len(asserts)} assertions)")
    for a in asserts[:5]:
        print(f"  {a[:75]}")
    if len(asserts) > 5:
        print(f"  ... and {len(asserts)-5} more assertions")
