#!/usr/bin/env python3
"""
JobSpy Setup Verification Script

This script verifies that the JobSpy 2.0 installation is correctly set up
and all components are accessible.
"""

import sys
import os
from pathlib import Path

def check_python_version():
    """Check Python version."""
    print("\n🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} (OK)")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} (Need 3.10+)")
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n📦 Checking dependencies...")
    required = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'supabase',
        'click',
        'pandas',
        'requests',
        'beautifulsoup4'
    ]

    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} (missing)")
            missing.append(package)

    if missing:
        print(f"\n   Install missing packages: pip install {' '.join(missing)}")
        return False
    return True

def check_file_structure():
    """Check if key files and directories exist."""
    print("\n📁 Checking file structure...")

    required_files = [
        'jobspy/api/app.py',
        'jobspy/api/models.py',
        'jobspy/api/dependencies.py',
        'jobspy/api/routes/profiles.py',
        'jobspy/api/routes/searches.py',
        'jobspy/api/routes/jobs.py',
        'jobspy/services/job_scraper_service.py',
        'jobspy/services/matching_service.py',
        'jobspy/services/profile_service.py',
        'jobspy/services/job_search_service.py',
        'jobspy/repositories/base_repository.py',
        'jobspy/repositories/profile_repository.py',
        'jobspy/repositories/job_repository.py',
        'jobspy/config.py',
        'jobspy/database.py',
        'cli.py',
        'run_server.py',
        'README_V2.md',
        'MIGRATION_GUIDE.md',
        '.env.example'
    ]

    missing = []
    for file in required_files:
        path = Path(file)
        if path.exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} (missing)")
            missing.append(file)

    return len(missing) == 0

def check_environment():
    """Check if .env file exists and has required variables."""
    print("\n🔧 Checking environment configuration...")

    env_path = Path('.env')
    if not env_path.exists():
        print("   ⚠️  .env file not found")
        print("   Create one from .env.example: cp .env.example .env")
        return False

    print("   ✅ .env file exists")

    # Check for required variables
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'SUPABASE_SERVICE_ROLE_KEY'
    ]

    with open('.env', 'r') as f:
        content = f.read()

    missing_vars = []
    for var in required_vars:
        if var in content and not content.count(f"{var}=your_") > 0:
            print(f"   ✅ {var} configured")
        else:
            print(f"   ⚠️  {var} needs configuration")
            missing_vars.append(var)

    if missing_vars:
        print(f"\n   Configure these variables in .env file")
        return False

    return True

def check_database_connection():
    """Check if database connection works."""
    print("\n🗄️  Checking database connection...")

    try:
        from jobspy.database import Database
        db = Database()

        # Try a simple query
        response = db.client.table('profiles').select('id').limit(1).execute()
        print("   ✅ Database connection successful")
        return True
    except Exception as e:
        print(f"   ❌ Database connection failed: {str(e)}")
        print("   Make sure your Supabase credentials are correct in .env")
        return False

def check_imports():
    """Check if key modules can be imported."""
    print("\n🔍 Checking module imports...")

    modules = [
        ('jobspy.config', 'AppConfig'),
        ('jobspy.database', 'Database'),
        ('jobspy.api.app', 'create_app'),
        ('jobspy.services.matching_service', 'MatchingService'),
        ('jobspy.repositories.job_repository', 'JobRepository')
    ]

    all_ok = True
    for module_path, class_name in modules:
        try:
            module = __import__(module_path, fromlist=[class_name])
            getattr(module, class_name)
            print(f"   ✅ {module_path}.{class_name}")
        except Exception as e:
            print(f"   ❌ {module_path}.{class_name}: {str(e)}")
            all_ok = False

    return all_ok

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("JobSpy 2.0 Setup Verification")
    print("=" * 60)

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("File Structure", check_file_structure),
        ("Environment", check_environment),
        ("Module Imports", check_imports),
        ("Database Connection", check_database_connection)
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n❌ Error during {name} check: {str(e)}")
            results[name] = False

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} {name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 All checks passed! JobSpy 2.0 is ready to use.")
        print("\nNext steps:")
        print("1. Create a profile: python3 cli.py profile create --email user@example.com --name 'Your Name' --experience 5")
        print("2. Run a search: python3 cli.py search run --profile-id YOUR_ID --keywords 'Python,AWS' --location India")
        print("3. Start API server: python3 run_server.py")
        print("4. View API docs: http://localhost:8000/api/docs")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("- Install dependencies: pip install -r requirements.txt")
        print("- Configure environment: cp .env.example .env (then edit .env)")
        print("- Check Supabase credentials in .env file")
        return 1

if __name__ == "__main__":
    sys.exit(main())
