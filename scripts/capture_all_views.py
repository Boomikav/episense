import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIRS = [
    Path("docs/screenshots"),
    Path(r"C:\Users\ajaya\.gemini\antigravity\brain\e0bda1e0-5867-4584-9d51-012ef6025664\screenshots"),
]

for d in OUTPUT_DIRS:
    d.mkdir(parents=True, exist_ok=True)

def save_shots(page, basename: str):
    for d in OUTPUT_DIRS:
        dest = d / f"{basename}.png"
        page.screenshot(path=str(dest), full_page=True)
        print(f"   [Captured] {dest}")

def main():
    print("=" * 80)
    print("CAPTURING FRESH SCREENSHOTS OF RUNNING EPISENSE APPLICATION")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        # 1. Overview
        print("\n1. Navigating to Overview...")
        page.goto("http://localhost:5173", timeout=15000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        save_shots(page, "01_overview")

        # 1b. Eight Priority Pathogens Intelligence View
        print("\n1b. Navigating to Eight Priority Pathogens Intelligence View...")
        try:
            page.click("text=Eight Priority Pathogens")
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            save_shots(page, "01b_eight_diseases_intelligence")

            # 1c. Open Malaria Detail Dossier Modal
            print("\n1c. Opening Malaria Detail Dossier Modal...")
            detail_btns = page.locator("button:has-text('Inspect Historical Dossier')")
            if detail_btns.count() > 0:
                detail_btns.first.click()
                time.sleep(2)
                save_shots(page, "01c_eight_diseases_detail_modal")
                close_btn = page.locator("button:has-text('Close Dossier')")
                if close_btn.count() > 0:
                    close_btn.first.click()
                else:
                    page.keyboard.press("Escape")
                time.sleep(1)
        except Exception as e:
            print(f"   [Notice] Could not capture Eight Diseases View: {e}")

        # 2. Event Intelligence -> Validated Events & Fusion (Current)
        print("\n2a. Navigating to Event Intelligence -> Validated Events & Fusion (Current)...")
        page.click("text=Event Intelligence")
        page.wait_for_load_state("networkidle")
        time.sleep(1.5)
        page.click("text=Validated Events & Fusion")
        time.sleep(1)
        save_shots(page, "02_event_fusion_current")

        # 2b. Event Intelligence -> Validated Events & Fusion (Recent Publications)
        print("\n2b. Switching to 'Recent Publications (Historical Dates)' tab...")
        page.click("text=Recent Publications (Historical Dates)")
        time.sleep(2)
        save_shots(page, "02b_event_fusion_recent")

        # 2f. Firozpur Cluster Inspection
        print("\n2f. Selecting Firozpur Leptospirosis cluster...")
        try:
            page.click("text=Firozepur, Punjab")
            time.sleep(2)
            page.wait_for_selector("text=Supporting Candidate Observations", timeout=5000)
            save_shots(page, "02f_firozpur_cluster_inspection")
        except Exception as e:
            print(f"   [Notice] Could not click Firozpur cluster card directly: {e}")

        # 2d. Filter to Priority Diseases
        print("\n2d. Clicking 'Priority Filter'...")
        page.click("text=Priority Filter")
        time.sleep(1)
        save_shots(page, "02d_event_fusion_priority")

        # 2e. Filter to Non-Priority Diseases
        print("\n2e. Clicking 'Non-Priority Filter'...")
        page.click("text=Non-Priority Filter")
        time.sleep(1)
        save_shots(page, "02e_event_fusion_non_priority")

        # Switch back to All Event Groups
        page.click("text=All Event Groups")
        time.sleep(1)

        # 2c. Event Intelligence -> Validated Events & Fusion (Historical Archival)
        print("\n2c. Switching to 'Historical Archival Corpus' tab...")
        page.click("text=Historical Archival Corpus")
        time.sleep(1.5)
        save_shots(page, "02c_event_fusion_historical")

        # 3. Event Intelligence -> Early Signals
        print("\n3. Navigating to Event Intelligence -> Early Signals...")
        page.click("text=Early Signals")
        time.sleep(1.5)
        page.wait_for_load_state("networkidle")
        save_shots(page, "03_early_signals")

        # 4. Event Intelligence -> Explainable Alerts
        print("\n4. Navigating to Event Intelligence -> Explainable Alerts...")
        page.click("text=Explainable Alerts")
        time.sleep(2)
        page.wait_for_load_state("networkidle")
        save_shots(page, "04_explainable_alerts")

        # 4b. Open First Alert Detail Modal to Capture Analyst Inference Dossier
        print("\n4b. Opening Analyst Inference Dossier Modal...")
        try:
            inspect_btns = page.locator("button:has-text('Inspect')")
            if inspect_btns.count() > 0:
                inspect_btns.first.click()
                time.sleep(2)
                save_shots(page, "04b_analyst_inference_dossier")
                # Close modal
                page.keyboard.press("Escape")
                time.sleep(1)
        except Exception as e:
            print(f"   [Notice] Could not open Alert Modal: {e}")

        # 5. Geographic View
        print("\n5. Navigating to Geographic View...")
        page.click("text=Geographic View")
        time.sleep(2)
        page.wait_for_load_state("networkidle")
        save_shots(page, "05_geographic_view")

        # 6. Forecasting & Model Status
        print("\n6. Navigating to Forecasting & Model Status...")
        page.click("text=Forecasting & Model Status")
        time.sleep(2)
        page.wait_for_load_state("networkidle")
        save_shots(page, "06_forecasting_model_status")

        # 7. Sources & System Health
        print("\n7. Navigating to Sources & System Health...")
        page.click("text=Sources & System Health")
        time.sleep(2)
        page.wait_for_load_state("networkidle")
        save_shots(page, "07_sources_system_health")

        # 8. NLP Forensic Workbench
        print("\n8. Navigating to NLP Forensic Workbench...")
        page.click("text=NLP Forensic Workbench")
        time.sleep(2)
        page.wait_for_load_state("networkidle")
        save_shots(page, "08_nlp_workbench")

        # 8b. Select Kinnaur NIL Report
        print("\n8b. Selecting Kinnaur NIL Report in NLP Workbench...")
        try:
            kinnaur_item = page.locator("text=Kinnaur").first
            if kinnaur_item:
                kinnaur_item.click()
                time.sleep(2)
                save_shots(page, "08b_kinnaur_negative_rule_out")
        except Exception as e:
            print(f"   [Notice] Could not select Kinnaur item in NLP workbench: {e}")

        browser.close()
        print("\nAll fresh screenshots captured and archived successfully!")

if __name__ == "__main__":
    main()
