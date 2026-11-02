import sys
sys.path.insert(0, "src")
import json
from episense.surveillance.data_sufficiency import DataSufficiencyProfiler

def main():
    profiler = DataSufficiencyProfiler(db_path="data/surveillance_store.sqlite")
    results = profiler.audit_database()
    print("=== PRIORITY DISEASES CAPABILITY MATRIX ===")
    dump_list = []
    for disease_name, profile in results.items():
        row = profile.model_dump()
        dump_list.append(row)
        print(f"Disease: {row['disease']}")
        print(f"  Target: {row['target_variable']} ({row['target_unit']}) | Level: {row['geographic_level']} | Freq: {row['observation_frequency']}")
        print(f"  Span: {row['first_observation_period']} -> {row['last_observation_period']}")
        print(f"  Valid Obs: {row['total_valid_observations']} | Distinct: {row['distinct_periods_count']} | Consec: {row['consecutive_observed_periods']} | Missing: {row['missing_periods_count']}")
        print(f"  Completeness: {row['completeness_status']} | Comparability: {row['comparability_status']}")
        print(f"  Event Surveillance: {row['event_surveillance_status']}")
        print(f"  Anomaly Eligibility: {row['statistical_anomaly_eligibility']}")
        print(f"  Forecast Eligibility: {row['forecast_eligibility']}")
        print(f"  Suppression Reason: {row['suppression_reason']}")
        print(f"  Min Requirement: {row['minimum_requirement']}")
        print(f"  Evaluation Status: {row['evaluation_status']}")
        print(f"  Recent Events: {row['recent_event_records']} | Hist Events: {row['historical_event_records']} | Numerical Obs: {row['available_numerical_observations']}")
        print("-" * 60)

    with open("docs/priority_matrix_dump.json", "w", encoding="utf-8") as f:
        json.dump(dump_list, f, indent=2)
    print("Dumped to docs/priority_matrix_dump.json")

if __name__ == "__main__":
    main()
