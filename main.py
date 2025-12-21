# main.py
"""
Main entry point for the JobSpy application.
Handles CLI arguments and initiates the scraping/enrichment pipeline.
"""

import argparse
import logging
from jobspy.pipeline import run_personalized_pipeline
from jobspy.util import create_logger

log = create_logger("Main")

def parse_cli_args():
    parser = argparse.ArgumentParser(description="JobSpy - Enhanced Job Search Engine")
    parser.add_argument("search_term", type=str, default=None, help="Job search query")
    parser.add_argument("-l", "--location", type=str, default="India", help="Location filter")
    parser.add_argument("-s", "--site", type=str, nargs="+", default=None,
                       choices=["linkedin", "indeed", "glassdoor", "naukri", "google", "ziprecruiter"],
                       help="Job boards to search")
    parser.add_argument("-r", "--remote", action="store_true", help="Show remote jobs only")
    parser.add_argument("--results", type=int, default=15, help="Number of results to show")
    parser.add_argument("--resume_file", type=str, help="Path to resume file for matching")
    parser.add_argument("--output", type=str, default="personalized_jobs.csv",
                       help="Output CSV file name")
    parser.add_argument("--format", type=str, default="csv", choices=["csv", "markdown"],
                       help="Output format")
    return parser.parse_args()

def main():
    args = parse_cli_args()
    try:
        input_params = {
            "search_term": args.search_term,
            "location": args.location,
            "remote": args.remote,
            "results_wanted": args.results,
            "description_format": "markdown",
            "hours_old": None,
            "offset": 0,
            "linkedin_company_ids": None,
        }
        df = run_personalized_pipeline(
            keywords=[args.search_term],
            location=args.location,
            results_wanted=args.results,
            output_file=args.output,
        )
        print(f"Found {len(df)} jobs. Results saved to {args.output}")
    except Exception as e:
        log.error(f"Application error: {str(e)}")
        raise

if __name__ == "__main__":
    main()