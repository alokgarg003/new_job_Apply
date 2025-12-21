# run_alok.py
"""
Full Alok‑personalized pipeline – discovery → enrichment → output CSV.
"""

from jobspy.pipeline import run_personalized_pipeline

if __name__ == "__main__":
    keywords = ["Application Support", "ServiceNow", "IT Support"]
    location = "India"
    results_wanted = 100
    output_file = "alok_personalized.csv"

    df = run_personalized_pipeline(
        keywords=keywords,
        location=location,
        results_wanted=results_wanted,
        output_file=output_file,
    )
    print(f"Personalized pipeline completed. {len(df)} jobs saved to {output_file}")