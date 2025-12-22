# main.py
from jobspy.pipeline import run_personalized_pipeline
from jobspy.util import create_logger
import settings
import argparse

log = create_logger("Main")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run JobSpy pipeline")
    parser.add_argument("--dry", action="store_true", help="Run in dry mode (no network calls, uses mock data)")
    parser.add_argument("--results", type=int, default=30, help="Number of results to fetch")
    parser.add_argument("--output", type=str, default="alok_personalized.csv", help="Output CSV path")
    args = parser.parse_args()

    if args.dry:
        settings.DRY_RUN = True
        settings.SAMPLE_RESULTS = args.results or settings.SAMPLE_RESULTS

    keywords = ["Application Support", "ServiceNow", "IT Support"]
    location = "India"
    results_wanted = args.results
    output_file = args.output

    df = run_personalized_pipeline(
        keywords=keywords,
        location=location,
        results_wanted=results_wanted,
        output_file=output_file,
    )
    print(f"Personalized pipeline completed. {len(df)} jobs saved to {output_file}")