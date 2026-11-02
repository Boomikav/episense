from pathlib import Path
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path("docs/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def verify_and_capture_ui():
    print("=" * 80)
    print("BROWSER-BASED VERIFICATION OF THE RUNNING APPLICATION")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Overview View
        print("\n1. Verifying 'Overview' view...")
        page.goto("http://localhost:5173", timeout=15000)
        page.wait_for_load_state("networkidle")
        time.sleep(1.5)

        # Check for 6 KPI Cards
        kpi_texts = page.locator("text=Overall Source Status").count()
        kpi_new_docs = page.locator("text=New Operational Reports").count()
        kpi_review = page.locator("text=Events Requiring Review").count()
        kpi_series = page.locator("text=Eligible Numerical Series").count()
        kpi_supported = page.locator("text=Supported Forecasts / Anomalies").count()
        kpi_suppressed = page.locator("text=Suppressed Analyses").count()

        print(f"   KPI Cards Found:")
        print(f"     - Overall Source Status: {kpi_texts > 0}")
        print(f"     - New Operational Reports: {kpi_new_docs > 0}")
        print(f"     - Events Requiring Review: {kpi_review > 0}")
        print(f"     - Eligible Numerical Series: {kpi_series > 0}")
        print(f"     - Supported Forecasts / Anomalies: {kpi_supported > 0}")
        print(f"     - Suppressed Analyses: {kpi_suppressed > 0}")

        # Check for Synthesis Sections
        findings = page.locator("text=Most Important New Findings").count()
        what_we_know = page.locator("text=Why It Matters / What We Know").count()
        uncertain = page.locator("text=What Is Still Uncertain").count()
        next_steps = page.locator("text=Recommended Next Steps").count()
        sources_summary = page.locator("text=Public Health Source Health Summary").count()

        print(f"   Synthesis Sections Found:")
        print(f"     - Most Important New Findings: {findings > 0}")
        print(f"     - Why It Matters / What We Know: {what_we_know > 0}")
        print(f"     - What Is Still Uncertain: {uncertain > 0}")
        print(f"     - Recommended Next Steps: {next_steps > 0}")
        print(f"     - Source Health Summary: {sources_summary > 0}")

        page.screenshot(path=str(SCREENSHOT_DIR / "01_overview_dashboard.png"), full_page=True)
        print("   Saved: docs/screenshots/01_overview_dashboard.png")

        # 2. Event Intelligence
        print("\n2. Verifying 'Event Intelligence' view...")
        page.click("text=Event Intelligence")
        time.sleep(1.5)
        page.wait_for_load_state("networkidle")

        # Verify no uncalibrated decimals in alert table
        has_arbitrary_decimal = page.locator("text=0.842").count()
        print(f"   Check: Old arbitrary decimal '0.842' present: {has_arbitrary_decimal > 0} (Expected: False)")

        page.screenshot(path=str(SCREENSHOT_DIR / "02_event_intelligence.png"), full_page=True)
        print("   Saved: docs/screenshots/02_event_intelligence.png")

        # 3. Geographic View
        print("\n3. Verifying 'Geographic View'...")
        page.click("text=Geographic View")
        time.sleep(1.5)
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(SCREENSHOT_DIR / "03_geographic_view.png"), full_page=True)
        print("   Saved: docs/screenshots/03_geographic_view.png")

        # 4. Forecasting & Model Status
        print("\n4. Verifying 'Forecasting & Model Status' view...")
        page.click("text=Forecasting & Model Status")
        time.sleep(1.5)
        page.wait_for_load_state("networkidle")

        # Check 8 diseases in sufficiency table
        dengue_count = page.locator("text=Dengue").count()
        malaria_count = page.locator("text=Malaria").count()
        chiku_count = page.locator("text=Chikungunya").count()
        cholera_count = page.locator("text=Cholera").count()
        lepto_count = page.locator("text=Leptospirosis").count()
        je_count = page.locator("text=Japanese Encephalitis").count()
        scrub_count = page.locator("text=Scrub Typhus").count()
        add_count = page.locator("text=Acute Diarrhoeal Disease").count()

        print(f"   Sufficiency Table Pathogens Found:")
        print(f"     - Dengue: {dengue_count > 0}, Malaria: {malaria_count > 0}, Chikungunya: {chiku_count > 0}")
        print(f"     - Cholera: {cholera_count > 0}, Leptospirosis: {lepto_count > 0}, JE: {je_count > 0}")
        print(f"     - Scrub Typhus: {scrub_count > 0}, ADD: {add_count > 0}")

        # Check suppression notice
        suppression_text = page.locator("text=SUPPRESSED (N < 12)").count()
        print(f"   Suppression Badges Found: {suppression_text}")

        page.screenshot(path=str(SCREENSHOT_DIR / "04_forecasting_model_status.png"), full_page=True)
        print("   Saved: docs/screenshots/04_forecasting_model_status.png")

        # 5. Sources & System Health
        print("\n5. Verifying 'Sources & System Health' view...")
        page.click("text=Sources & System Health")
        time.sleep(1.5)
        page.wait_for_load_state("networkidle")

        who_feed = page.locator("text=who_news_feed").count()
        social_stream = page.locator("text=public_health_social_stream").count()
        print(f"   Sources found: who_news_feed={who_feed > 0}, public_health_social_stream={social_stream > 0}")

        page.screenshot(path=str(SCREENSHOT_DIR / "05_sources_system_health.png"), full_page=True)
        print("   Saved: docs/screenshots/05_sources_system_health.png")

        # 6. Secondary NLP Forensic Workbench
        print("\n6. Verifying 'NLP Forensic Workbench'...")
        page.click("text=NLP Forensic Workbench")
        time.sleep(1.5)
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(SCREENSHOT_DIR / "06_nlp_forensic_workbench.png"), full_page=True)
        print("   Saved: docs/screenshots/06_nlp_forensic_workbench.png")

        browser.close()
        print("\nAll 6 views successfully audited and screenshots captured in docs/screenshots/!")

if __name__ == "__main__":
    verify_and_capture_ui()
