import os
import re
import base64
import requests
from flask import Flask, render_template, request, jsonify
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

# GitHub Token (optional)
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
headers = {'Authorization': f'token {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}

def extract_repo_info(url):
    """Extract owner and repo name from GitHub URL"""
    pattern = r'github\.com/([^/]+)/([^/]+)'
    match = re.search(pattern, url)
    if not match:
        return None, None
    return match.group(1), match.group(2)

def fetch_github_data(owner, repo):
    """Fetches repository metadata and README content from GitHub"""
    repo_url = f'https://api.github.com/repos/{owner}/{repo}'
    readme_url = f'https://api.github.com/repos/{owner}/{repo}/readme'

    repo_response = requests.get(repo_url, headers=headers)
    if repo_response.status_code != 200:
        return None

    repo_data = repo_response.json()

    repo_info = {
        'name': repo_data.get('name', 'Unknown Repository'),
        'description': repo_data.get('description', 'No description available'),
        'stars': repo_data.get('stargazers_count', 0),
        'forks': repo_data.get('forks_count', 0),
        'open_issues': repo_data.get('open_issues_count', 0),
    }

    # Fetch README content (if available)
    readme_content = ""
    readme_response = requests.get(readme_url, headers=headers)
    if readme_response.status_code == 200:
        readme_content = base64.b64decode(readme_response.json().get('content', '')).decode('utf-8')

    repo_info['readme'] = readme_content[:1000]  # Limit README size

    return repo_info

def generate_job_description(repo_info):
    """Generate a job description based on the repository info"""
    job_description = f"""
    Job Description for Repository: {repo_info['name']}

    Description: {repo_info['description']}
    
    Required Skills:
    - Familiarity with Java (or related language) programming languages.
    - Experience with modern development frameworks and libraries.
    - Knowledge of concurrency, I/O, and multithreading (based on repo functionality).
    
    Responsibilities:
    - Develop and maintain software solutions.
    - Collaborate with team members to design and improve architecture.
    - Ensure high performance and scalability of solutions.
    """

    return job_description

def generate_interview_questions(repo_info):
    """Generate interview questions based on the repository info"""
    interview_questions = [
        f"1. What key features would you expect in a project like {repo_info['name']}?",
        "2. How would you handle concurrency in a multi-threaded Java application?",
        "3. Explain the importance of using immutable collections in a project like this.",
        "4. Can you describe a time you integrated third-party libraries into a project?"
    ]
    return interview_questions

@app.route('/analyze', methods=['POST'])
def analyze():
    """Handle the analysis of a GitHub repository"""
    try:
        repo_url = request.json.get('repo_url')
        if not repo_url:
            return jsonify({
                'success': False,
                'error': 'Repository URL is required'
            }), 400

        # Extract owner and repository name from the URL
        owner, repo_name = extract_repo_info(repo_url)
        if not owner or not repo_name:
            raise ValueError("Invalid GitHub repository URL")

        # Fetch the repository data
        repo_info = fetch_github_data(owner, repo_name)
        if not repo_info:
            raise ValueError("Could not retrieve repository data. Check if the repository exists and is public.")

        # Generate Job Description and Interview Questions
        job_description = generate_job_description(repo_info)
        interview_questions = generate_interview_questions(repo_info)

        return jsonify({
            'success': True,
            'results': {
                'repository_info': repo_info,
                'analysis_results': {
                    'job_description': job_description,
                    'interview_questions': interview_questions
                }
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
