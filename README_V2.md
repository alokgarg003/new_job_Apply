# JobSpy 2.0 - Intelligent Job Scraping and Matching Platform

A production-ready job aggregation and intelligent matching platform built with modern Python, FastAPI, and Supabase.

## Features

### Core Capabilities

- **Multi-Source Job Scraping**: Scrape jobs from LinkedIn, Naukri, and other major job boards
- **Intelligent Matching**: AI-powered job matching algorithm that scores jobs based on your profile
- **Database Persistence**: All data stored in Supabase with proper schema and relationships
- **RESTful API**: Modern FastAPI-based API with OpenAPI documentation
- **CLI Tools**: Command-line interface for quick operations
- **Background Processing**: Ready for asynchronous job processing for large-scale scraping

### Technical Highlights

- **Clean Architecture**: Repository pattern, service layer, dependency injection
- **Type Safety**: Full Pydantic models and type hints throughout
- **Database**: Supabase PostgreSQL with Row Level Security (RLS)
- **Testing**: Comprehensive test suite with pytest
- **Observability**: Structured logging and error handling
- **Scalability**: Designed for horizontal scaling

## Architecture

```
jobspy/
├── api/              # FastAPI application
│   ├── routes/       # API endpoints
│   │   ├── profiles.py
│   │   ├── searches.py
│   │   ├── jobs.py
│   │   └── admin.py
│   ├── models.py     # Pydantic request/response models
│   ├── dependencies.py
│   └── app.py
├── services/         # Business logic layer
│   ├── job_scraper_service.py
│   ├── matching_service.py
│   ├── profile_service.py
│   └── job_search_service.py
├── repositories/     # Data access layer
│   ├── base_repository.py
│   ├── profile_repository.py
│   ├── job_repository.py
│   ├── job_search_repository.py
│   └── job_match_repository.py
├── linkedin/         # LinkedIn scraper
├── naukri/          # Naukri scraper
├── config.py         # Configuration management
├── database.py       # Database connection
└── util.py           # Shared utilities
```

## Quick Start

### Prerequisites

- Python 3.10+
- Supabase account (free tier available)
- Virtual environment (recommended)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd jobspy
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

Required environment variables:
```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

5. Verify database connection:
```bash
python cli.py db status
```

### Running the API Server

```bash
python run_server.py
```

The API will be available at `http://localhost:8000`

Interactive API documentation: `http://localhost:8000/api/docs`

Alternative documentation: `http://localhost:8000/api/redoc`

## Using the CLI

### Profile Management

Create a profile:
```bash
python cli.py profile create \
  --email user@example.com \
  --name "John Doe" \
  --experience 5
```

View profile:
```bash
python cli.py profile show --email user@example.com
```

### Job Searching

Run a job search:
```bash
python cli.py search run \
  --profile-id YOUR_PROFILE_ID \
  --keywords "DevOps,AWS,Python" \
  --location "India" \
  --results 100
```

View search history:
```bash
python cli.py search history --profile-id YOUR_PROFILE_ID
```

### Database Management

Check database status:
```bash
python cli.py db status
```

## API Usage

### Authentication

For development, use the `X-User-ID` header with your profile UUID:
```bash
curl -H "X-User-ID: your-profile-id" http://localhost:8000/api/v1/profiles/me
```

### API Examples

#### Create a Profile

```bash
curl -X POST http://localhost:8000/api/v1/profiles \
  -H "X-User-ID: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "full_name": "John Doe",
    "skills": ["python", "aws", "linux"],
    "experience_years": 5
  }'
```

Response:
```json
{
  "id": "uuid-here",
  "email": "user@example.com",
  "full_name": "John Doe",
  "skills": ["python", "aws", "linux"],
  "experience_years": 5,
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### Execute a Job Search

```bash
curl -X POST http://localhost:8000/api/v1/searches \
  -H "X-User-ID: your-profile-id" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["DevOps", "AWS", "Python"],
    "location": "India",
    "sites": ["linkedin", "naukri"],
    "results_wanted": 100,
    "auto_match": true
  }'
```

Response:
```json
{
  "search_id": "search-uuid",
  "jobs_found": 85,
  "jobs_saved": 82,
  "match_stats": {
    "total_matches": 65,
    "strong_matches": 12,
    "good_matches": 28,
    "stretch_matches": 25
  }
}
```

#### Get Top Job Matches

```bash
curl "http://localhost:8000/api/v1/jobs/matches?min_score=50&limit=20" \
  -H "X-User-ID": your-profile-id"
```

#### Search Existing Jobs

```bash
curl "http://localhost:8000/api/v1/jobs/search?keywords=python,aws&location=Bengaluru&limit=50"
```

## Database Schema

The application uses Supabase PostgreSQL with the following main tables:

### Profiles
User profiles with skills, experience, and preferences
- `id` (UUID, primary key)
- `email` (unique)
- `full_name`
- `skills` (JSONB array)
- `experience_years`
- `preferences` (JSONB)

### Jobs
Job listings from various sources
- `id` (UUID, primary key)
- `external_id` + `site` (unique constraint)
- `title`, `company_name`, `location`
- `description`, `job_url`
- `skills` (JSONB array)
- `salary_min`, `salary_max`
- `is_remote`, `work_from_home_type`

### Job Searches
Search history and parameters
- `id` (UUID, primary key)
- `profile_id` (foreign key)
- `keywords`, `location`, `sites`
- `status` (pending/running/completed/failed)
- `jobs_found`

### Job Matches
Match scores between profiles and jobs
- `id` (UUID, primary key)
- `profile_id`, `job_id`, `search_id` (foreign keys)
- `match_score` (0-100)
- `alignment_level` (Strong/Good/Stretch/Ignore)
- `matching_skills`, `missing_skills`
- `why_fits`

All tables have Row Level Security (RLS) enabled for data protection.

## Matching Algorithm

The intelligent matching algorithm evaluates jobs based on:

### Scoring Criteria

1. **Primary Skills** (Weight: 12 points each, max 60)
   - Core technical skills from your profile
   - Keywords: python, aws, linux, jenkins, terraform, etc.

2. **Secondary Skills** (Weight: 5 points each, max 15)
   - Nice-to-have skills
   - Keywords: docker, kubernetes, java, grafana, etc.

3. **Bonuses**
   - MFT/File Transfer Tools: +10 points
   - On-call/Shift Work: +7 points
   - Cloud Platforms (AWS/Azure/GCP): +5 points per platform
   - ServiceNow/ITIL/Incident Management: +8 points
   - CI/CD Experience: +4 points
   - Support/Production Oriented: +6 points

4. **Penalties**
   - Development-heavy roles: -30 points

5. **Exclusion Signals**
   - Frontend keywords (React, Angular, Vue)
   - UI/UX roles
   - DSA/Competitive Programming

### Alignment Levels

- **Strong Match** (70-100): Excellent fit, apply immediately
- **Good Match** (45-69): Good fit, worth applying
- **Stretch Role** (20-44): Reach opportunity, consider carefully
- **Ignore** (0-19): Not a good fit

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Supabase
SUPABASE_URL=your_project_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_key

# Scraper Settings
LINKEDIN_DELAY=3.0
NAUKRI_DELAY=2.5
DEFAULT_RESULTS=150

# Redis (optional, for caching)
REDIS_URL=redis://localhost:6379/0
```

### Customizing Matching Algorithm

Edit `jobspy/config.py` to customize:

```python
class MatchingConfig(BaseModel):
    primary_skills: List[str] = [
        "python", "linux", "aws", "azure"
        # Add your primary skills
    ]

    secondary_skills: List[str] = [
        "docker", "kubernetes", "java"
        # Add your secondary skills
    ]

    exclude_signals: List[str] = [
        "frontend", "react", "vue"
        # Add exclusion keywords
    ]

    primary_weight: int = 12  # Points per primary skill
    secondary_weight: int = 5  # Points per secondary skill
    min_score: int = 45  # Minimum score for matches
```

## Testing

### Run Tests

```bash
# All tests
pytest tests/

# With coverage
pytest --cov=jobspy tests/

# Specific test file
pytest tests/test_services.py -v

# Integration tests (requires database)
pytest -m integration tests/
```

### Test Structure

```
tests/
├── conftest.py          # Pytest fixtures
├── test_api.py          # API endpoint tests
├── test_services.py     # Service layer tests
├── test_repositories.py # Repository tests
└── test_util.py         # Utility function tests
```

## Development

### Code Style

Format code with Black:
```bash
black jobspy/ tests/
```

### Pre-commit Hooks

Install pre-commit hooks:
```bash
pre-commit install
```

This will automatically:
- Format code with Black
- Check for syntax errors
- Run linters

### Adding New Job Boards

1. Create scraper module:
```python
# jobspy/mysite/mysite.py
from jobspy.model import Scraper, ScraperInput, JobResponse

class MySiteScraper(Scraper):
    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        # Implement scraping logic
        pass
```

2. Register in `jobspy/scrape_jobs.py`:
```python
SCRAPER_MAPPING = {
    Site.LINKEDIN: LinkedIn,
    Site.NAUKRI: Naukri,
    Site.MYSITE: MySiteScraper,  # Add here
}
```

3. Add tests:
```python
# tests/test_mysite.py
def test_mysite_scraper():
    scraper = MySiteScraper()
    # Test scraping logic
```

## Production Deployment

### Environment Setup

1. Set production environment variables
2. Use strong secrets for authentication
3. Configure proper CORS origins
4. Enable rate limiting
5. Set up monitoring and logging

### Scaling Considerations

- **API**: Deploy multiple instances behind a load balancer
- **Database**: Use Supabase read replicas for high read loads
- **Caching**: Implement Redis for caching and session management
- **Background Jobs**: Use Celery with Redis/RabbitMQ for async processing
- **Monitoring**: Integrate Prometheus/Grafana for metrics

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "run_server.py"]
```

```bash
# Build and run
docker build -t jobspy:latest .
docker run -p 8000:8000 --env-file .env jobspy:latest
```

## Monitoring and Observability

### Health Checks

- `GET /health`: Basic health check with database status
- `GET /api/v1/admin/stats`: System statistics

### Logging

Structured logging is enabled by default:
```python
from jobspy.util import create_logger

log = create_logger("MyService")
log.info("Operation successful")
log.error("Operation failed", exc_info=True)
```

Configure log level: `LOG_LEVEL=DEBUG|INFO|WARNING|ERROR`

## Security

- **Row Level Security (RLS)**: All database tables have RLS enabled
- **Input Validation**: Pydantic models validate all inputs
- **SQL Injection Prevention**: Parameterized queries via Supabase client
- **CORS Configuration**: Configurable allowed origins
- **Authentication**: Header-based auth (dev), JWT-ready for production
- **Rate Limiting**: Ready for implementation

## Troubleshooting

### Database Connection Issues

```bash
# Check database status
python cli.py db status

# Verify environment variables
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY
```

### Import Errors

```bash
# Ensure all dependencies are installed
pip install -r requirements.txt

# Check Python version (requires 3.10+)
python --version
```

### Scraping Issues

- **Rate Limiting**: Adjust delay in `config.py`
- **Blocked IPs**: Consider using proxies
- **No Results**: Some sites may not work in certain regions

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests
5. Run tests (`pytest tests/`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Changelog

### Version 2.0.0 (Current)

- Complete rewrite with clean architecture
- Supabase database integration
- Modern FastAPI-based API
- Enhanced matching algorithm with intelligent scoring
- CLI tools for profile and search management
- Comprehensive test suite
- Production-ready features
- Improved documentation

### Version 1.0.0 (Legacy)

- Basic scraping functionality
- CSV output only
- Limited matching capabilities

## Roadmap

- [ ] Real-time job alerts via webhooks
- [ ] Email notifications
- [ ] Advanced resume parser with NLP
- [ ] Interview preparation suggestions
- [ ] Salary insights and analytics
- [ ] Mobile app (React Native)
- [ ] Browser extension
- [ ] Integration with ATS systems
- [ ] Company reviews aggregation
- [ ] Career path recommendations
- [ ] LinkedIn Easy Apply automation

## Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/jobspy/issues)
- Documentation: [Read the docs](https://jobspy.readthedocs.io)
- Email: support@example.com

## Acknowledgments

- Built with FastAPI, Supabase, Pandas, and Pydantic
- Inspired by the need for intelligent job search automation
- Thanks to all contributors and the open-source community

## Related Projects

- **JobScraper**: Simpler job scraping library
- **ResumeParser**: NLP-based resume parsing
- **CareerPath**: Career guidance platform
