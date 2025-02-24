import streamlit as st
import requests
import os
import sqlite3
from crewai import Agent, Crew, Task
import base64

# Manually set path to the latest SQLite
os.environ["LD_LIBRARY_PATH"] = "/home/adminuser/venv/lib/python3.12/lib-dynload"
sys.modules["sqlite3"] = __import__("pysqlite3")

# GitHub API Token (use environment variables for security)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

def get_repo_details(repo_url):
    repo_name = repo_url.split("github.com/")[-1]
    api_url = f"https://api.github.com/repos/{repo_name}"
    response = requests.get(api_url, headers=HEADERS)
    
    if response.status_code != 200:
        return {"error": "Failed to fetch repository details"}
    
    repo_data = response.json()
    
    # Extract repository structure and files
    contents_url = repo_data.get("contents_url", "").replace("{+path}", "")
    contents_response = requests.get(contents_url, headers=HEADERS)
    files = [item['path'] for item in contents_response.json()] if contents_response.status_code == 200 else []
    
    # Extract README content
    readme_url = f"https://api.github.com/repos/{repo_name}/readme"
    readme_response = requests.get(readme_url, headers=HEADERS)
    readme_content = "No README found."
    if readme_response.status_code == 200:
        readme_data = readme_response.json()
        readme_content = base64.b64decode(readme_data.get("content", "")).decode("utf-8", errors="ignore")
    
    # Extract languages
    languages_url = f"https://api.github.com/repos/{repo_name}/languages"
    languages_response = requests.get(languages_url, headers=HEADERS)
    languages = languages_response.json() if languages_response.status_code == 200 else {}
    
    return {"files": files, "readme": readme_content, "languages": languages}

# CrewAI Agents
data_analysis_agent = Agent(
    role="Data Analyst",
    goal="Analyze GitHub repo structure, technical stack, and metadata.",
    backstory="An experienced data analyst skilled in extracting insights from software repositories.",
    tasks=["Extract file structure", "Identify programming languages", "Summarize README"]
)

job_description_agent = Agent(
    role="HR Specialist",
    goal="Generate job descriptions based on project structure and technology stack.",
    backstory="A seasoned HR specialist who understands the hiring needs for technical roles.",
    tasks=["Analyze repository insights", "Match technologies to job roles", "Generate job descriptions"]
)

interview_agent = Agent(
    role="Interview Specialist",
    goal="Generate interview questions for candidates based on the repository insights.",
    backstory="An expert interviewer who crafts insightful questions to assess technical skills.",
    tasks=["Analyze technical stack", "Generate role-specific interview questions"]
)

# Define Crew
crew = Crew(agents=[data_analysis_agent, job_description_agent, interview_agent])

def generate_human_readable_insights(insights):
    files = insights.get("files", [])
    languages = insights.get("languages", {})
    readme_content = insights.get("readme", "No README available.")
    
    readable_text = f"""
    ## Repository Insights
    
    **Project Structure:**
    - The repository contains {len(files)} files and directories, including key files like:
      {', '.join(files[:10])} {'...' if len(files) > 10 else ''}
    
    **Programming Languages Used:**
    {', '.join([f'`{lang}`' for lang in languages.keys()]) if languages else 'No languages detected'}
    
    **README Summary:**
    {readme_content[:500]} {'...' if len(readme_content) > 500 else ''}
    """
    return readable_text

def generate_job_description(insights):
    return f"""
    We are looking for developers skilled in {', '.join([f'`{lang}`' for lang in insights.get('languages', {}).keys()])}.
    This role involves working on a project structured as {len(insights.get('files', []))} files.
    Ideal candidates should have experience in {', '.join(insights.get('languages', {}).keys())}.
    """

def generate_interview_questions(insights):
    return [
        f"Can you describe your experience with {lang}?" for lang in insights.get('languages', {}).keys()
    ] + [
        "How would you improve the structure of this project?",
        "What best practices would you apply to maintain this repository?"
    ]

# Streamlit UI
st.title("GitHub Repo Analysis Crew")
repo_url = st.text_input("Enter GitHub Repository URL:")
if st.button("Analyze Repo") and repo_url:
    insights = get_repo_details(repo_url)
    
    st.subheader("Repository Insights")
    st.markdown(generate_human_readable_insights(insights))
    
    job_desc = generate_job_description(insights)
    st.subheader("Generated Job Description")
    st.markdown(job_desc)
    
    interview_questions = generate_interview_questions(insights)
    st.subheader("Interview Questions")
    for q in interview_questions:
        st.write(f"- {q}")
