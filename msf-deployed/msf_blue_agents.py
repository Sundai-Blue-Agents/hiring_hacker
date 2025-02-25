# Fix for sqlite3 version issues
import sys
import importlib.util

# Check if pysqlite3 is available
if importlib.util.find_spec("pysqlite3") is not None:
    import pysqlite3
    # Replace sqlite3 with pysqlite3 in sys.modules
    sys.modules["sqlite3"] = pysqlite3
    print("Successfully replaced sqlite3 with pysqlite3")
else:
    print("Warning: pysqlite3 not found. Using system sqlite3 which may cause issues.")

import os
import requests
import streamlit as st
from crewai import Agent, Task, Crew, LLM
from crewai_tools import GithubSearchTool, WebsiteSearchTool, SerperDevTool
from typing import Optional, Dict, Any, List, Callable
from dotenv import load_dotenv
import base64
from github import Github

# Define a custom tool class
class CustomTool:
    def __init__(self, name: str, description: str, func: Callable):
        self.name = name
        self.description = description
        self.func = func

# Load environment variables
load_dotenv()

# Load tokens
github_token = os.getenv("GITHUB_TOKEN")
openai_api_key = os.getenv("OPENAI_API_KEY")
serper_api_key = os.getenv("SERPER_API_KEY")
HEADERS = {"Authorization": f"token {github_token}"} if github_token else {}

# Define a function to analyze GitHub repositories
def analyze_github_repo(repo_url: str) -> str:
    """
    Analyzes a GitHub repository to extract detailed information including languages, stars, contributors, and content.
    
    Args:
        repo_url: The GitHub repository URL to analyze
        
    Returns:
        A string containing the analysis results
    """
    # Extract owner and repo name from URL
    parts = repo_url.strip("/").split("/")
    if "github.com" not in repo_url or len(parts) < 5:
        return "Invalid GitHub repository URL"
    
    owner = parts[-2]
    repo_name = parts[-1]
    
    try:
        # Direct API call with proper error handling
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
        headers = {"Authorization": f"token {github_token}"} if github_token else {}
        
        # Get repository information
        repo_response = requests.get(api_url, headers=headers)
        if repo_response.status_code == 404:
            return f"Repository not found: {owner}/{repo_name}"
        if repo_response.status_code == 403:
            return "API rate limit exceeded. Please try again later or provide a GitHub token."
        if repo_response.status_code != 200:
            return f"Error accessing repository: {repo_response.status_code} - {repo_response.text}"
        
        repo_data = repo_response.json()
        
        # Get basic repository information
        repo_info = {
            "name": repo_data.get("name", "Unknown"),
            "description": repo_data.get("description", "No description"),
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "watchers": repo_data.get("watchers_count", 0),
            "open_issues": repo_data.get("open_issues_count", 0),
            "created_at": repo_data.get("created_at", "Unknown"),
            "updated_at": repo_data.get("updated_at", "Unknown"),
            "license": repo_data.get("license", {}).get("name", "No license information")
        }
        
        # Get languages
        languages_response = requests.get(f"{api_url}/languages", headers=headers)
        languages = languages_response.json() if languages_response.status_code == 200 else {}
        
        # Calculate language percentages
        total_bytes = sum(languages.values()) if languages else 1  # Avoid division by zero
        language_percentages = {lang: f"{(bytes_count/total_bytes)*100:.1f}%" 
                               for lang, bytes_count in languages.items()}
        
        # Get README content
        readme_content = "README not found"
        readme_response = requests.get(f"{api_url}/readme", headers=headers)
        if readme_response.status_code == 200:
            readme_data = readme_response.json()
            if "content" in readme_data:
                try:
                    readme_content = base64.b64decode(readme_data["content"]).decode("utf-8")
                except Exception as e:
                    readme_content = f"Error decoding README: {str(e)}"
        
        # Get contributors
        contributors_response = requests.get(f"{api_url}/contributors", headers=headers)
        contributors = contributors_response.json() if contributors_response.status_code == 200 else []
        contributor_count = len(contributors) if isinstance(contributors, list) else 0
        
        # Get top contributors
        top_contributors = []
        if isinstance(contributors, list) and contributors:
            for contributor in contributors[:5]:  # Get top 5 contributors
                top_contributors.append({
                    "login": contributor.get("login", "Unknown"),
                    "contributions": contributor.get("contributions", 0)
                })
        
        # Get repository contents
        contents_response = requests.get(f"{api_url}/contents", headers=headers)
        contents = contents_response.json() if contents_response.status_code == 200 else []
        
        # Analyze directory structure
        directories = []
        files_by_type = {}
        
        if isinstance(contents, list):
            for item in contents:
                if item.get("type") == "dir":
                    directories.append(item.get("name"))
                elif item.get("type") == "file":
                    file_ext = os.path.splitext(item.get("name", ""))[1].lower()
                    if file_ext:
                        files_by_type[file_ext] = files_by_type.get(file_ext, 0) + 1
        
        # Sample some code files for analysis
        code_samples = []
        if isinstance(contents, list):
            for item in contents:
                if item.get("type") == "file" and item.get("name", "").endswith((".py", ".js", ".java", ".cpp", ".go", ".ts", ".rb")):
                    try:
                        file_response = requests.get(item.get("url", ""), headers=headers)
                        if file_response.status_code == 200:
                            file_content = file_response.json()
                            if "content" in file_content:
                                try:
                                    decoded_content = base64.b64decode(file_content["content"]).decode("utf-8")
                                    code_samples.append({
                                        "filename": item.get("name", "Unknown"),
                                        "content": decoded_content[:1000] + "..." if len(decoded_content) > 1000 else decoded_content
                                    })
                                except Exception as e:
                                    code_samples.append({
                                        "filename": item.get("name", "Unknown"),
                                        "content": f"Error decoding content: {str(e)}"
                                    })
                        if len(code_samples) >= 3:  # Limit to 3 samples
                            break
                    except Exception as e:
                        continue
        
        # Get dependencies from package files
        dependencies = {}
        package_files = ["package.json", "requirements.txt", "Gemfile", "pom.xml", "build.gradle"]
        
        for package_file in package_files:
            try:
                file_response = requests.get(f"{api_url}/contents/{package_file}", headers=headers)
                if file_response.status_code == 200:
                    file_content = file_response.json()
                    if "content" in file_content:
                        try:
                            decoded_content = base64.b64decode(file_content["content"]).decode("utf-8")
                            dependencies[package_file] = decoded_content
                        except:
                            pass
            except:
                continue
        
        # Compile the results
        result = {
            "name": repo_info["name"],
            "description": repo_info["description"],
            "stars": repo_info["stars"],
            "forks": repo_info["forks"],
            "watchers": repo_info["watchers"],
            "open_issues": repo_info["open_issues"],
            "languages": language_percentages,
            "contributors": contributor_count,
            "top_contributors": top_contributors,
            "directories": directories,
            "files_by_type": files_by_type,
            "dependencies": dependencies,
            "readme": readme_content,
            "code_samples": code_samples,
            "created_at": repo_info["created_at"],
            "updated_at": repo_info["updated_at"],
            "license": repo_info["license"]
        }
        
        # Format the result as a readable string
        formatted_result = "# Repository Analysis: " + repo_info["name"] + "\n\n"
        
        formatted_result += "## Overview\n"
        formatted_result += f"- **Description**: {repo_info['description']}\n"
        formatted_result += f"- **Stars**: {repo_info['stars']}\n"
        formatted_result += f"- **Forks**: {repo_info['forks']}\n"
        formatted_result += f"- **Watchers**: {repo_info['watchers']}\n"
        formatted_result += f"- **Open Issues**: {repo_info['open_issues']}\n"
        formatted_result += f"- **Created**: {repo_info['created_at']}\n"
        formatted_result += f"- **Last Updated**: {repo_info['updated_at']}\n"
        formatted_result += f"- **License**: {repo_info['license']}\n\n"
        
        formatted_result += "## Programming Languages\n"
        for lang, percentage in language_percentages.items():
            formatted_result += f"- **{lang}**: {percentage}\n"
        formatted_result += "\n"
        
        formatted_result += "## Contributors\n"
        formatted_result += f"- **Total Contributors**: {contributor_count}\n"
        formatted_result += "- **Top Contributors**:\n"
        for contributor in top_contributors:
            formatted_result += f"  - {contributor['login']}: {contributor['contributions']} contributions\n"
        formatted_result += "\n"
        
        formatted_result += "## Repository Structure\n"
        formatted_result += "- **Directories**:\n"
        for directory in directories:
            formatted_result += f"  - {directory}\n"
        formatted_result += "- **Files by Type**:\n"
        for file_type, count in files_by_type.items():
            formatted_result += f"  - {file_type}: {count} files\n"
        formatted_result += "\n"
        
        formatted_result += "## Dependencies\n"
        for package_file, content in dependencies.items():
            formatted_result += f"### {package_file}:\n```\n{content[:500]}{'...' if len(content) > 500 else ''}\n```\n"
        formatted_result += "\n"
        
        formatted_result += "## README\n```\n"
        formatted_result += f"{readme_content[:1000]}{'...' if len(readme_content) > 1000 else ''}\n```\n\n"
        
        formatted_result += "## Code Samples\n"
        for sample in code_samples:
            formatted_result += f"### {sample['filename']}:\n```\n{sample['content'][:500]}{'...' if len(sample['content']) > 500 else ''}\n```\n"
                
        return formatted_result
    
    except Exception as e:
        return f"Error analyzing repository: {str(e)}"

# Streamlit interface
st.title("Unlock the Code: Leveraging GitHub Repo Insights to Craft Winning Job Descriptions & Ace Interview Questions")

# Get the GitHub repo URL from the user
repo_url = st.text_input("Enter the GitHub Repository URL:")

# Add a debug option
debug_mode = st.checkbox("Debug Mode", value=False, help="Show raw analyzer output for debugging")

# Run the task when the button is pressed
if st.button("Analyze Repository"):
    if repo_url:
        st.info(f"Analyzing repository: {repo_url}")
        
        # If debug mode is enabled, show the raw analyzer output
        if debug_mode:
            with st.expander("Raw Analyzer Output"):
                st.info("Testing direct analyzer function...")
                raw_analysis = analyze_github_repo(repo_url)
                st.markdown(raw_analysis)
        
        # Initialize tools
        github_search = GithubSearchTool(
            github_repo=repo_url,
            gh_token=github_token, 
            content_types=['repo', 'code']
        )
        
        # Create a custom tool from our function
        github_analysis = CustomTool(
            name="GitHub Repository Analysis",
            description="Analyzes a GitHub repository to extract detailed information including languages, stars, contributors, and content",
            func=lambda query=None: analyze_github_repo(repo_url)  # Always use the repo_url from the input field
        )
        
        serper_tool = None
        if serper_api_key:
            serper_tool = SerperDevTool(api_key=serper_api_key)
        
        # Configure LLM
        llm = LLM(
            model="gpt-4o",  # Using a more capable model
            temperature=0.3,
            max_tokens=4096,
            frequency_penalty=0.1,
            presence_penalty=0.1,
        )

        # Define the Agents
        repo_extraction_agent = Agent(
            role="Repo Analysis Expert",
            goal="Extract comprehensive details from a GitHub repository, including stars, languages, contributors, code structure, and README content.",
            backstory=(
                "You are a senior software engineer specialized in repository analysis. "
                "You have extensive experience in analyzing codebases to understand their structure, "
                "technologies, and patterns. Your insights help teams understand projects at a deep level."
            ),
            tools=[github_search, github_analysis],
            llm=llm,
            verbose=True
        )

        job_description_agent = Agent(
            role="Technical Recruiter",
            goal="Create a detailed job description based on the repository analysis that accurately reflects the technical requirements and skills needed.",
            backstory=(
                "You are an experienced technical recruiter with a background in software engineering. "
                "You understand both the technical and human aspects of software development roles. "
                "You excel at translating technical requirements into clear job descriptions that "
                "attract the right candidates."
            ),
            tools=[serper_tool] if serper_tool else [],
            llm=llm,
            verbose=True
        )
        
        interview_questions_agent = Agent(
            role="Technical Interviewer",
            goal="Generate relevant technical interview questions based on the repository's technologies and code patterns.",
            backstory=(
                "You are a senior technical interviewer with years of experience hiring for technical roles. "
                "You know how to craft questions that assess both technical knowledge and problem-solving abilities. "
                "Your questions reveal whether candidates truly understand the technologies they claim to know."
            ),
            tools=[serper_tool] if serper_tool else [],
            llm=llm,
            verbose=True
        )

        # Define the Tasks
        task1 = Task(
            description=(
                f"Analyze the GitHub repository at {repo_url} in detail. Extract and summarize the following information:\n"
                "1. Repository overview (stars, forks, contributors)\n"
                "2. Programming languages used and their proportions\n"
                "3. Key libraries and frameworks identified in the code\n"
                "4. Code organization and architecture patterns\n"
                "5. Main functionality and purpose based on README and code samples\n"
                "Focus on extracting factual information that will be useful for creating job descriptions and interview questions.\n"
                "Do not make up any information not found in the repository."
            ),
            expected_output="A comprehensive analysis of the repository with technical details and insights.",
            agent=repo_extraction_agent
        )

        task2 = Task(
            description=(
                "Based on the repository analysis, create a detailed job description that includes:\n"
                "1. Job title appropriate for the project\n"
                "2. Required technical skills and experience levels\n"
                "3. Preferred qualifications\n"
                "4. Key responsibilities\n"
                "5. Project context and team information (if available)\n"
                "The job description should accurately reflect the technical stack and complexity of the project.\n"
                "Use the repository analysis to create an accurate and compelling job description."
            ),
            expected_output="A professional job description tailored to the repository's technical requirements.",
            agent=job_description_agent
        )
        
        task3 = Task(
            description=(
                "Create a set of technical interview questions based on the repository analysis. Include:\n"
                "1. 5-7 technical knowledge questions specific to the main languages and frameworks used\n"
                "2. 2-3 system design questions relevant to the project's architecture\n"
                "3. 2-3 problem-solving questions that test skills needed for this codebase\n"
                "4. 1-2 questions about relevant best practices\n"
                "For each question, provide a brief explanation of what you're assessing and what a good answer might include.\n"
                "Use the repository analysis to create relevant and insightful interview questions."
            ),
            expected_output="A set of tailored technical interview questions with assessment criteria.",
            agent=interview_questions_agent
        )

        # Instantiate Crew
        crew = Crew(
            agents=[repo_extraction_agent, job_description_agent, interview_questions_agent],
            tasks=[task1, task2, task3],
            verbose=True,
            memory=True,  # Enable memory to share context between agents
            planning=True  # Enables planning to manage tasks in sequence
        )

        # Run the Crew and display results
        with st.spinner("Analyzing repository and generating insights... This may take a few minutes."):
            result = crew.kickoff()

        # Display results in sections
        st.subheader("Analysis Results:")
        
        # Create tabs for different sections
        tab1, tab2, tab3 = st.tabs(["Repository Analysis", "Job Description", "Interview Questions"])
        
        # Extract results directly from the task objects
        try:
            # Access the task outputs directly from the task objects
            repo_analysis = task1.output.raw if hasattr(task1, 'output') and hasattr(task1.output, 'raw') else ""
            job_description = task2.output.raw if hasattr(task2, 'output') and hasattr(task2.output, 'raw') else ""
            interview_questions = task3.output.raw if hasattr(task3, 'output') and hasattr(task3.output, 'raw') else ""
            
            # Display the extracted content in tabs
            with tab1:
                st.markdown("### Repository Analysis")
                st.markdown(repo_analysis if repo_analysis else "Analysis not available")
            
            with tab2:
                st.markdown("### Job Description")
                st.markdown(job_description if job_description else "Job description not available")
            
            with tab3:
                st.markdown("### Interview Questions")
                st.markdown(interview_questions if interview_questions else "Interview questions not available")
        except Exception as e:
            st.error(f"Error displaying results: {str(e)}")
            st.write("Result:", str(result))
    else:
        st.error("Please enter a valid GitHub repository URL.")
