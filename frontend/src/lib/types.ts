/** TypeScript type definitions for the Resume Matcher API. */

// --- Resume ---

export interface BasicInfo {
  name: string;
  email: string;
  phone: string;
  city: string;
  years_of_experience: number | null;
}

export interface Education {
  school: string;
  degree: string;
  major: string;
  start_date: string | null;
  end_date: string | null;
  expected_graduation: string | null;
  gpa: number | null;
}

export interface WorkExperience {
  company: string;
  title: string;
  start_date: string | null;
  end_date: string | null;
  description: string;
  achievements: string[];
  employment_type: string;
}

export interface Competition {
  name: string;
  level: string;
  award: string;
  date: string | null;
}

export interface Skill {
  name: string;
  level: string | null;
  category: string | null;
}

export interface ParsedResumeData {
  resume_type: "campus" | "experienced" | "unknown";
  basic_info: BasicInfo;
  education: Education[];
  work_experience: WorkExperience[];
  skills: Skill[];
  projects: { name: string; description: string; tech_stack: string[]; url: string | null }[];
  certifications: { name: string; issuer: string; date: string | null }[];
  languages: { name: string; proficiency: string }[];
  competitions: Competition[];
}

export interface ResumeItem {
  id: string;
  original_filename: string;
  file_type: string;
  parse_status: string;
  resume_type: string;
  created_at: string;
}

export interface ResumeDetail extends ResumeItem {
  parsed_data: ParsedResumeData;
  raw_text: string;
  parse_error: string | null;
  parse_duration_ms: number | null;
}

// --- Job Description ---

export interface ParsedJDData {
  basic_info: Record<string, string>;
  requirements: { type: string; category: string; description: string; weight: number }[];
  responsibilities: string[];
  skills_required: { name: string; level: string | null; importance: string }[];
  education_required: { min_degree: string | null; preferred_majors: string[] };
  experience_required: { min_years: number | null; preferred_fields: string[] };
}

export interface JDItem {
  id: string;
  title: string;
  department: string | null;
  location: string | null;
  parsed_data: ParsedJDData;
  raw_text: string;
  parse_status: string;
  is_active: boolean;
  created_at: string;
}

// --- Matching ---

export interface DimensionScores {
  education: number;
  skills: number;
  experience: number;
  certifications: number;
  languages: number;
  location: number;
  overall: number;
}

export interface MatchResult {
  id: string;
  resume_id: string;
  job_id: string;
  rule_score: number | null;
  tfidf_score: number | null;
  semantic_score: number | null;
  llm_score: number | null;
  overall_score: number;
  dimension_scores: DimensionScores;
  matched_skills: string[];
  missing_skills: string[];
  llm_reasoning: string | null;
  suggestions: string[];
  is_hard_pass: boolean;
  hard_pass_reasons: string[];
  match_duration_ms: number | null;
  created_at: string;
}

// --- Dashboard ---

export interface DashboardData {
  total_resumes: number;
  total_jobs: number;
  total_matches: number;
  parse_status: Record<string, number>;
  score_distribution: Record<string, number>;
  top_matches: {
    match_id: string;
    resume_name: string;
    job_title: string;
    score: number;
    date: string;
  }[];
  avg_score: number;
}
