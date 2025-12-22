# tests/test_pipeline_dry.py
from jobspy.pipeline import run_personalized_pipeline
import settings


def test_pipeline_dry_mode(tmp_path):
    settings.DRY_RUN = True
    out = tmp_path / "out.csv"
    df = run_personalized_pipeline(["test"], None, 1, output_file=str(out))
    assert df is not None
    assert len(df) >= 0
    settings.DRY_RUN = False