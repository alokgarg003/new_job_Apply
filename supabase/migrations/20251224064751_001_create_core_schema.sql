/*
  # JobSpy Core Database Schema
  
  ## Overview
  This migration establishes the foundational schema for JobSpy - a job aggregation and matching platform.
  
  ## Tables Created
  
  ### 1. profiles
  - Stores user profiles with resume data and preferences
  - `id` (uuid, primary key)
  - `email` (text, unique)
  - `full_name` (text)
  - `resume_text` (text) - parsed resume content
  - `skills` (jsonb) - array of skills
  - `experience_years` (integer)
  - `preferred_locations` (jsonb) - array of locations
  - `preferred_job_types` (jsonb) - array of job types
  - `created_at`, `updated_at` (timestamptz)
  
  ### 2. job_searches
  - Tracks search queries and parameters
  - `id` (uuid, primary key)
  - `profile_id` (uuid, foreign key)
  - `keywords` (jsonb) - search keywords array
  - `location` (text)
  - `sites` (jsonb) - job boards searched
  - `results_wanted` (integer)
  - `status` (text) - pending/running/completed/failed
  - `created_at`, `completed_at` (timestamptz)
  
  ### 3. jobs
  - Central job listings table
  - `id` (uuid, primary key)
  - `external_id` (text) - site-specific job ID
  - `site` (text) - linkedin/naukri/etc
  - `title` (text)
  - `company_name` (text)
  - `location` (jsonb) - structured location data
  - `description` (text)
  - `job_url` (text)
  - `job_type` (text)
  - `experience_range` (text)
  - `skills` (jsonb) - extracted skills
  - `salary_min`, `salary_max` (numeric)
  - `salary_currency` (text)
  - `is_remote` (boolean)
  - `work_from_home_type` (text)
  - `date_posted` (date)
  - `raw_data` (jsonb) - full scrape result
  - `created_at`, `updated_at` (timestamptz)
  
  ### 4. job_matches
  - Stores match scores between profiles and jobs
  - `id` (uuid, primary key)
  - `profile_id` (uuid, foreign key)
  - `job_id` (uuid, foreign key)
  - `search_id` (uuid, foreign key)
  - `match_score` (integer)
  - `alignment_level` (text) - Strong/Good/Stretch/Ignore
  - `matching_skills` (jsonb)
  - `missing_skills` (jsonb)
  - `match_reasons` (jsonb)
  - `why_fits` (text)
  - `created_at` (timestamptz)
  
  ### 5. saved_searches
  - User's saved search configurations for alerts
  - `id` (uuid, primary key)
  - `profile_id` (uuid, foreign key)
  - `name` (text)
  - `search_params` (jsonb)
  - `alert_frequency` (text) - daily/weekly/realtime
  - `is_active` (boolean)
  - `last_run_at` (timestamptz)
  - `created_at`, `updated_at` (timestamptz)
  
  ### 6. job_applications
  - Track application status
  - `id` (uuid, primary key)
  - `profile_id` (uuid, foreign key)
  - `job_id` (uuid, foreign key)
  - `status` (text) - interested/applied/interviewing/offered/rejected
  - `notes` (text)
  - `applied_at` (timestamptz)
  - `created_at`, `updated_at` (timestamptz)
  
  ## Security
  - RLS enabled on all tables
  - Policies restrict access to own data only
  - Service role can bypass for background jobs
  
  ## Indexes
  - Performance indexes on foreign keys and search fields
  - Full-text search indexes on job descriptions
*/

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =====================================================
-- PROFILES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE NOT NULL,
  full_name text,
  resume_text text,
  skills jsonb DEFAULT '[]'::jsonb,
  experience_years integer DEFAULT 0,
  preferred_locations jsonb DEFAULT '[]'::jsonb,
  preferred_job_types jsonb DEFAULT '[]'::jsonb,
  preferences jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Indexes for profiles
CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_skills ON profiles USING gin(skills);

-- RLS for profiles
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own profile"
  ON profiles FOR SELECT
  TO authenticated
  USING (auth.uid()::text = id::text);

CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  TO authenticated
  USING (auth.uid()::text = id::text)
  WITH CHECK (auth.uid()::text = id::text);

CREATE POLICY "Users can insert own profile"
  ON profiles FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid()::text = id::text);

-- =====================================================
-- JOB SEARCHES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS job_searches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  keywords jsonb DEFAULT '[]'::jsonb,
  location text,
  sites jsonb DEFAULT '[]'::jsonb,
  results_wanted integer DEFAULT 100,
  status text DEFAULT 'pending',
  error_message text,
  jobs_found integer DEFAULT 0,
  created_at timestamptz DEFAULT now(),
  completed_at timestamptz
);

-- Indexes for job_searches
CREATE INDEX IF NOT EXISTS idx_job_searches_profile ON job_searches(profile_id);
CREATE INDEX IF NOT EXISTS idx_job_searches_status ON job_searches(status);
CREATE INDEX IF NOT EXISTS idx_job_searches_created ON job_searches(created_at DESC);

-- RLS for job_searches
ALTER TABLE job_searches ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own searches"
  ON job_searches FOR SELECT
  TO authenticated
  USING (profile_id::text = auth.uid()::text);

CREATE POLICY "Users can create own searches"
  ON job_searches FOR INSERT
  TO authenticated
  WITH CHECK (profile_id::text = auth.uid()::text);

CREATE POLICY "Users can update own searches"
  ON job_searches FOR UPDATE
  TO authenticated
  USING (profile_id::text = auth.uid()::text)
  WITH CHECK (profile_id::text = auth.uid()::text);

-- =====================================================
-- JOBS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id text NOT NULL,
  site text NOT NULL,
  title text NOT NULL,
  company_name text,
  location jsonb DEFAULT '{}'::jsonb,
  description text,
  job_url text NOT NULL,
  job_type text,
  experience_range text,
  skills jsonb DEFAULT '[]'::jsonb,
  salary_min numeric,
  salary_max numeric,
  salary_currency text DEFAULT 'INR',
  is_remote boolean DEFAULT false,
  work_from_home_type text,
  date_posted date,
  raw_data jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(external_id, site)
);

-- Indexes for jobs
CREATE INDEX IF NOT EXISTS idx_jobs_site ON jobs(site);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_name);
CREATE INDEX IF NOT EXISTS idx_jobs_posted ON jobs(date_posted DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_remote ON jobs(is_remote);
CREATE INDEX IF NOT EXISTS idx_jobs_skills ON jobs USING gin(skills);
CREATE INDEX IF NOT EXISTS idx_jobs_description_fts ON jobs USING gin(to_tsvector('english', description));
CREATE INDEX IF NOT EXISTS idx_jobs_title_search ON jobs USING gin(title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);

-- RLS for jobs (public read, service role write)
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read jobs"
  ON jobs FOR SELECT
  TO authenticated, anon
  USING (true);

-- =====================================================
-- JOB MATCHES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS job_matches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  job_id uuid REFERENCES jobs(id) ON DELETE CASCADE,
  search_id uuid REFERENCES job_searches(id) ON DELETE CASCADE,
  match_score integer DEFAULT 0,
  alignment_level text,
  matching_skills jsonb DEFAULT '[]'::jsonb,
  missing_skills jsonb DEFAULT '[]'::jsonb,
  match_reasons jsonb DEFAULT '[]'::jsonb,
  why_fits text,
  created_at timestamptz DEFAULT now(),
  UNIQUE(profile_id, job_id)
);

-- Indexes for job_matches
CREATE INDEX IF NOT EXISTS idx_job_matches_profile ON job_matches(profile_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_job ON job_matches(job_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_search ON job_matches(search_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_score ON job_matches(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_job_matches_level ON job_matches(alignment_level);

-- RLS for job_matches
ALTER TABLE job_matches ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own matches"
  ON job_matches FOR SELECT
  TO authenticated
  USING (profile_id::text = auth.uid()::text);

CREATE POLICY "Users can create own matches"
  ON job_matches FOR INSERT
  TO authenticated
  WITH CHECK (profile_id::text = auth.uid()::text);

CREATE POLICY "Users can update own matches"
  ON job_matches FOR UPDATE
  TO authenticated
  USING (profile_id::text = auth.uid()::text)
  WITH CHECK (profile_id::text = auth.uid()::text);

-- =====================================================
-- SAVED SEARCHES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS saved_searches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  name text NOT NULL,
  search_params jsonb NOT NULL,
  alert_frequency text DEFAULT 'daily',
  is_active boolean DEFAULT true,
  last_run_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Indexes for saved_searches
CREATE INDEX IF NOT EXISTS idx_saved_searches_profile ON saved_searches(profile_id);
CREATE INDEX IF NOT EXISTS idx_saved_searches_active ON saved_searches(is_active);

-- RLS for saved_searches
ALTER TABLE saved_searches ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own saved searches"
  ON saved_searches FOR ALL
  TO authenticated
  USING (profile_id::text = auth.uid()::text)
  WITH CHECK (profile_id::text = auth.uid()::text);

-- =====================================================
-- JOB APPLICATIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS job_applications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  job_id uuid REFERENCES jobs(id) ON DELETE CASCADE,
  status text DEFAULT 'interested',
  notes text,
  applied_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(profile_id, job_id)
);

-- Indexes for job_applications
CREATE INDEX IF NOT EXISTS idx_job_applications_profile ON job_applications(profile_id);
CREATE INDEX IF NOT EXISTS idx_job_applications_job ON job_applications(job_id);
CREATE INDEX IF NOT EXISTS idx_job_applications_status ON job_applications(status);

-- RLS for job_applications
ALTER TABLE job_applications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own applications"
  ON job_applications FOR ALL
  TO authenticated
  USING (profile_id::text = auth.uid()::text)
  WITH CHECK (profile_id::text = auth.uid()::text);

-- =====================================================
-- FUNCTIONS AND TRIGGERS
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update_updated_at trigger to relevant tables
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_profiles_updated_at') THEN
    CREATE TRIGGER update_profiles_updated_at
      BEFORE UPDATE ON profiles
      FOR EACH ROW
      EXECUTE FUNCTION update_updated_at_column();
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_jobs_updated_at') THEN
    CREATE TRIGGER update_jobs_updated_at
      BEFORE UPDATE ON jobs
      FOR EACH ROW
      EXECUTE FUNCTION update_updated_at_column();
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_saved_searches_updated_at') THEN
    CREATE TRIGGER update_saved_searches_updated_at
      BEFORE UPDATE ON saved_searches
      FOR EACH ROW
      EXECUTE FUNCTION update_updated_at_column();
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_job_applications_updated_at') THEN
    CREATE TRIGGER update_job_applications_updated_at
      BEFORE UPDATE ON job_applications
      FOR EACH ROW
      EXECUTE FUNCTION update_updated_at_column();
  END IF;
END $$;