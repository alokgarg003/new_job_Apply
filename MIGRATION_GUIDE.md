# Migration Guide: JobSpy 1.0 → 2.0

This guide helps you migrate from the original JobSpy (CSV-based) to JobSpy 2.0 (database-powered with API).

## Overview of Changes

### What Changed

1. **Architecture**: Moved from script-based to clean service architecture
2. **Storage**: CSV files → Supabase PostgreSQL database
3. **API**: Added comprehensive REST API with FastAPI
4. **Matching**: Enhanced algorithm with more sophisticated scoring
5. **Configuration**: Environment-based configuration management
6. **CLI**: New command-line interface for operations

### What Stayed the Same

1. **Core Scrapers**: LinkedIn and Naukri scrapers still work
2. **Matching Logic**: Same core principles, just enhanced
3. **Output Format**: Can still export to CSV if needed

## Migration Steps

### Step 1: Set Up New Environment

```bash
# Install new dependencies
pip install -r requirements.txt

# Configure Supabase
cp .env.example .env
# Edit .env with your Supabase credentials
```

### Step 2: Migrate Existing Data (Optional)

If you have existing CSV data you want to migrate:

```python
# migrate_data.py
import pandas as pd
from uuid import uuid4
from jobspy.repositories import JobRepository

# Read your old CSV
df = pd.read_csv("alok_personalized.csv")

job_repo = JobRepository()

for _, row in df.iterrows():
    job_data = {
        "external_id": row.get("id", str(uuid4())),
        "site": row["site"],
        "title": row["title"],
        "company_name": row["company_name"],
        "job_url": row["job_url"],
        "location": {"city": row.get("location", "")},
        "description": row.get("description"),
        "skills": row.get("key_skills", "").split(",") if pd.notna(row.get("key_skills")) else [],
        "is_remote": row.get("is_remote", False),
        "date_posted": row.get("date_posted")
    }

    try:
        job_repo.upsert_job(job_data)
        print(f"Migrated: {job_data['title']}")
    except Exception as e:
        print(f"Error: {e}")
```

### Step 3: Update Your Workflows

#### Old Way (v1.0)
```bash
python run_alok.py
# Output: alok_personalized.csv
```

#### New Way (v2.0)

**Option A: Using CLI**
```bash
# Create profile
python cli.py profile create \
  --email alok@example.com \
  --name "Alok Garg" \
  --experience 10

# Run search
python cli.py search run \
  --profile-id YOUR_PROFILE_ID \
  --keywords "Application Support,ServiceNow,IT Support" \
  --location "India" \
  --results 200
```

**Option B: Using API**
```bash
# Create profile
curl -X POST http://localhost:8000/api/v1/profiles \
  -H "X-User-ID: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alok@example.com",
    "full_name": "Alok Garg",
    "skills": ["linux", "aws", "python", "servicenow"],
    "experience_years": 10
  }'

# Run search
curl -X POST http://localhost:8000/api/v1/searches \
  -H "X-User-ID: your-profile-id" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["Application Support", "ServiceNow", "IT Support"],
    "location": "India",
    "results_wanted": 200,
    "auto_match": true
  }'
```

### Step 4: Update Configuration

#### Old Configuration (settings.py)
```python
PROFILE_PRIMARY_SKILLS = ["linux", "shell", "bash"]
EVAL_PRIMARY_WEIGHT = 12
```

#### New Configuration (jobspy/config.py)
```python
class MatchingConfig(BaseModel):
    primary_skills: List[str] = ["linux", "shell", "bash"]
    primary_weight: int = 12
```

Or via environment variables:
```env
MATCHING__PRIMARY_SKILLS=linux,shell,bash
MATCHING__PRIMARY_WEIGHT=12
```

## API Equivalent for Common Tasks

### Task: Run a Job Search

**Old (v1.0)**
```python
from jobspy.pipeline import run_personalized_pipeline

df = run_personalized_pipeline(
    keywords=["DevOps", "AWS"],
    location="India",
    results_wanted=100,
    output_file="jobs.csv"
)
```

**New (v2.0 - Programmatic)**
```python
from uuid import uuid4
from jobspy.services import JobSearchService

service = JobSearchService()
profile_id = uuid4()  # Or get existing profile ID

result = service.execute_search(
    profile_id=profile_id,
    keywords=["DevOps", "AWS"],
    location="India",
    results_wanted=100,
    auto_match=True
)

print(f"Found {result['jobs_found']} jobs")
print(f"Strong matches: {result['match_stats']['strong_matches']}")
```

**New (v2.0 - API)**
```bash
curl -X POST http://localhost:8000/api/v1/searches \
  -H "X-User-ID: profile-id" \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["DevOps", "AWS"], "location": "India", "results_wanted": 100}'
```

### Task: Get Matched Jobs

**Old (v1.0)**
```python
# Read from CSV
df = pd.read_csv("alok_personalized.csv")
strong_matches = df[df['resume_alignment_level'] == 'Strong Match']
```

**New (v2.0 - Programmatic)**
```python
from jobspy.services import MatchingService

service = MatchingService()
matches = service.get_top_matches(
    profile_id=profile_id,
    min_score=70,  # Strong matches only
    limit=20
)
```

**New (v2.0 - API)**
```bash
curl "http://localhost:8000/api/v1/jobs/matches?min_score=70&limit=20" \
  -H "X-User-ID: profile-id"
```

### Task: Export to CSV

**New (v2.0)**
```python
# Export matches to CSV
from jobspy.repositories import JobMatchRepository
import pandas as pd

match_repo = JobMatchRepository()
matches = match_repo.get_top_matches(profile_id, min_score=45, limit=100)

df = pd.DataFrame(matches)
df.to_csv("matched_jobs.csv", index=False)
```

## Breaking Changes

### 1. Output Format

**Old**: Single CSV file with all columns
**New**: Database storage with API access

**Solution**: Use repositories to query data and export to CSV if needed

### 2. Configuration

**Old**: `settings.py` file
**New**: `jobspy/config.py` + `.env` file

**Solution**: Move settings to environment variables or update config.py

### 3. Matching Algorithm

**Old**: Simple keyword matching
**New**: Enhanced algorithm with weighted scoring

**Solution**: Scores may differ slightly. Review alignment levels and adjust thresholds if needed.

### 4. Job Sites

**Old**: Attempted to support many sites (most didn't work for India)
**New**: Focused on working sites (LinkedIn, Naukri)

**Solution**: Stick with supported sites or implement new scrapers properly

## Feature Comparison

| Feature | v1.0 | v2.0 |
|---------|------|------|
| Job Scraping | ✅ | ✅ Enhanced |
| CSV Output | ✅ | ✅ Optional |
| Database Storage | ❌ | ✅ Supabase |
| REST API | ❌ | ✅ FastAPI |
| CLI Tools | ❌ | ✅ Full CLI |
| Profile Management | ❌ | ✅ Full CRUD |
| Search History | ❌ | ✅ Tracked |
| Match Scoring | ✅ Basic | ✅ Enhanced |
| Background Jobs | ❌ | ✅ Ready |
| Testing | ⚠️ Limited | ✅ Comprehensive |
| Documentation | ⚠️ Basic | ✅ Complete |

## Backward Compatibility

### Using Old Scripts

You can still use the old pipeline approach:

```python
# Old style still works (backward compatible)
from jobspy import scrape_jobs

df = scrape_jobs(
    site_name=["linkedin", "naukri"],
    search_term="Application Support",
    location="India",
    results_wanted=100
)
```

However, this won't:
- Save to database
- Track search history
- Provide match scoring
- Support API access

### Migrating Gradually

You can migrate gradually:

1. **Phase 1**: Keep using old scripts, add database logging
2. **Phase 2**: Start using API for new searches
3. **Phase 3**: Migrate historical data
4. **Phase 4**: Fully adopt new architecture

## Getting Help

### Common Issues

**Issue**: "Module not found" errors
**Solution**: `pip install -r requirements.txt`

**Issue**: "Database connection failed"
**Solution**: Check `.env` file has correct Supabase credentials

**Issue**: "Different match scores than v1.0"
**Solution**: Algorithm enhanced. Review `jobspy/config.py` to adjust weights

### Support Channels

- GitHub Issues: For bugs and feature requests
- Documentation: README_V2.md for detailed guides
- Email: For private inquiries

## Next Steps

1. Read the new README_V2.md
2. Set up your Supabase database
3. Create your first profile
4. Run a test search
5. Explore the API docs at `/api/docs`

Welcome to JobSpy 2.0!
