"""Thin wrapper utilities to invoke existing extractors in removed_scripts.
These are thin convenience functions for the prototype. They run the existing scripts
via subprocess and return the process object for monitoring.
"""
from subprocess import Popen
import shlex
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def run_selenium_extractor(input_csv: str, url_column: str = 'URL', output_dir: str = 'outputs', batch_size: int = 100, workers: int = 1, headless: bool = True, single_driver: bool = True):
    cmd = ["python", os.path.join(ROOT, 'removed_scripts', 'linkedin_contact_extractor_selenium.py'), "--input", input_csv, "--url-column", url_column, "--output-dir", output_dir, "--batch-size", str(batch_size), "--workers", str(workers)]
    if headless:
        cmd.append("--headless")
    if single_driver:
        cmd.append("--single-driver")
    proc = Popen([str(c) for c in cmd])
    return proc


def run_requests_extractor(input_csv: str, url_column: str = 'URL', output_dir: str = 'outputs', max_profiles: int = None):
    cmd = ["python", os.path.join(ROOT, 'removed_scripts', 'linkedin_contact_extractor.py'), "--input", input_csv, "--url-column", url_column, "--output-dir", output_dir]
    if max_profiles:
        cmd.extend(["--max-profiles", str(max_profiles)])
    proc = Popen([str(c) for c in cmd])
    return proc
