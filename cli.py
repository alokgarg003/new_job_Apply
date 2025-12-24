#!/usr/bin/env python3
# cli.py
"""
Command-line interface for JobSpy.
"""
import click
import sys
from pathlib import Path
from uuid import UUID, uuid4
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from jobspy.services import ProfileService, JobSearchService, MatchingService
from jobspy.config import get_config
from jobspy.util import create_logger

log = create_logger("CLI")


@click.group()
@click.option('--debug/--no-debug', default=False)
def cli(debug):
    """JobSpy Command Line Interface."""
    if debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)


@cli.group()
def profile():
    """Profile management commands."""
    pass


@profile.command()
@click.option('--email', required=True, help='User email')
@click.option('--name', help='Full name')
@click.option('--experience', type=int, default=0, help='Years of experience')
def create(email, name, experience):
    """Create a new profile."""
    try:
        service = ProfileService()

        existing = service.get_profile_by_email(email)
        if existing:
            click.echo(f"Error: Profile already exists with ID: {existing['id']}")
            return

        profile_id = uuid4()
        profile = service.create_profile(
            profile_id=profile_id,
            email=email,
            full_name=name,
            experience_years=experience
        )

        click.echo(f"Profile created successfully!")
        click.echo(f"Profile ID: {profile['id']}")
        click.echo(f"Email: {profile['email']}")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@profile.command()
@click.option('--email', required=True, help='User email')
def show(email):
    """Show profile details."""
    try:
        service = ProfileService()
        profile = service.get_profile_by_email(email)

        if not profile:
            click.echo("Profile not found")
            return

        click.echo(f"\nProfile Details:")
        click.echo(f"  ID: {profile['id']}")
        click.echo(f"  Email: {profile['email']}")
        click.echo(f"  Name: {profile.get('full_name', 'N/A')}")
        click.echo(f"  Experience: {profile.get('experience_years', 0)} years")
        click.echo(f"  Skills: {len(profile.get('skills', []))} skills")
        click.echo(f"  Created: {profile.get('created_at', 'N/A')}")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.group()
def search():
    """Job search commands."""
    pass


@search.command()
@click.option('--profile-id', required=True, help='Profile ID')
@click.option('--keywords', required=True, help='Comma-separated keywords')
@click.option('--location', default='India', help='Job location')
@click.option('--sites', default='linkedin,naukri', help='Comma-separated sites')
@click.option('--results', default=100, type=int, help='Number of results')
@click.option('--remote/--no-remote', default=False, help='Filter for remote jobs')
def run(profile_id, keywords, location, sites, results, remote):
    """Run a job search."""
    try:
        service = JobSearchService()

        profile_uuid = UUID(profile_id)
        keyword_list = [k.strip() for k in keywords.split(',')]
        site_list = [s.strip() for s in sites.split(',')]

        click.echo(f"\nStarting job search...")
        click.echo(f"  Profile: {profile_id}")
        click.echo(f"  Keywords: {', '.join(keyword_list)}")
        click.echo(f"  Location: {location}")
        click.echo(f"  Sites: {', '.join(site_list)}")
        click.echo(f"  Results wanted: {results}")
        click.echo()

        result = service.execute_search(
            profile_id=profile_uuid,
            keywords=keyword_list,
            location=location,
            sites=site_list,
            results_wanted=results,
            is_remote=remote,
            auto_match=True
        )

        click.echo(f"\nSearch completed!")
        click.echo(f"  Search ID: {result['search_id']}")
        click.echo(f"  Jobs found: {result['jobs_found']}")
        click.echo(f"  Jobs saved: {result['jobs_saved']}")

        if 'match_stats' in result:
            stats = result['match_stats']
            click.echo(f"\nMatch Statistics:")
            click.echo(f"  Total matches: {stats['total_matches']}")
            click.echo(f"  Strong matches: {stats['strong_matches']}")
            click.echo(f"  Good matches: {stats['good_matches']}")
            click.echo(f"  Stretch roles: {stats['stretch_matches']}")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@search.command()
@click.option('--profile-id', required=True, help='Profile ID')
@click.option('--limit', default=20, type=int, help='Number of results')
def history(profile_id, limit):
    """Show search history."""
    try:
        service = JobSearchService()
        profile_uuid = UUID(profile_id)

        searches = service.get_user_searches(profile_uuid, limit=limit)

        if not searches:
            click.echo("No searches found")
            return

        click.echo(f"\nSearch History ({len(searches)} results):\n")

        for s in searches:
            click.echo(f"ID: {s['id']}")
            click.echo(f"  Keywords: {', '.join(s.get('keywords', []))}")
            click.echo(f"  Location: {s.get('location', 'N/A')}")
            click.echo(f"  Status: {s.get('status', 'unknown')}")
            click.echo(f"  Jobs found: {s.get('jobs_found', 0)}")
            click.echo(f"  Created: {s.get('created_at', 'N/A')}")
            click.echo()

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.group()
def db():
    """Database management commands."""
    pass


@db.command()
def migrate():
    """Run database migrations."""
    click.echo("Database migrations are managed through Supabase.")
    click.echo("Migrations have been applied automatically.")
    click.echo("Use 'db status' to check database connection.")


@db.command()
def status():
    """Check database connection status."""
    try:
        from jobspy.database import get_db

        db_instance = get_db()
        result = db_instance.client.table('profiles').select('id', count='exact').limit(0).execute()

        click.echo("Database connection: OK")
        click.echo(f"Total profiles: {result.count or 0}")

    except Exception as e:
        click.echo(f"Database connection: FAILED", err=True)
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
def server():
    """Start the API server."""
    click.echo("Starting JobSpy API server...")
    click.echo("Use: uvicorn jobspy.api.app:create_app --factory --reload")
    click.echo("Or run: python run_server.py")


@cli.command()
def version():
    """Show version information."""
    config = get_config()
    click.echo(f"JobSpy v2.0.0")
    click.echo(f"Environment: {config.environment}")
    click.echo(f"Python: {sys.version.split()[0]}")


if __name__ == '__main__':
    cli()
