from flask import Flask, render_template, request, jsonify
import requests
from collections import Counter
import re
import os
from dotenv import load_dotenv
from transformers import pipeline

load_dotenv()

app = Flask(__name__)

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
headers = {'Authorization': f'token {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}

# Initialize Hugging Face text generation pipeline (using GPT-2 or GPT-3 model)
generator = pipeline('text-generation', model='gpt2')  # You can replace 'gpt2' with any other model

def extract_repo_info(url):
    # Extract owner and repo name from GitHub URL
    pattern = r'github\.com/([^/]+)/([^/]+)'
    match = re.search(pattern, url)
    if not match:
        return None, None
    return match.group(1), match.group(2)

def analyze_repository(owner, repo):
    # Get repository information
    repo_url = f'https://api.github.com/repos/{owner}/{repo}'
    repo_response = requests.get(repo_url, headers=headers)
    if repo_response.status_code != 200:
        return None

    # Get repository contents
    contents_url = f'https://api.github.com/repos/{owner}/{repo}/contents'
    contents_response = requests.get(contents_url, headers=headers)
    if contents_response.status_code != 200:
        return None

    # Get languages used
    languages_url = f'https://api.github.com/repos/{owner}/{repo}/languages'
    languages_response = requests.get(languages_url, headers=headers)
    languages = languages_response.json() if languages_response.status_code == 200 else {}

    # Analyze README if it exists
    readme_url = f'https://api.github.com/repos/{owner}/{repo}/readme'
    readme_response = requests.get(readme_url, headers=headers)
    readme_content = ""
    if readme_response.status_code == 200:
        import base64
        readme_content = base64.b64decode(readme_response.json()['content']).decode('utf-8')

    repo_data = repo_response.json()
    
    return {
        'name': repo_data['name'],
        'description': repo_data['description'],
        'languages': languages,
        'readme': readme_content,
        'stars': repo_data['stargazers_count'],
        'forks': repo_data['forks_count'],
        'open_issues': repo_data['open_issues_count']
    }

def generate_job_description(repo_data):
    if not repo_data:
        return "Unable to analyze repository"
    
    # Get a short description from the model if no description exists
    description = repo_data['description'] if repo_data['description'] else "An innovative software project"

    # Sort languages by usage
    languages = sorted(repo_data['languages'].items(), key=lambda x: x[1], reverse=True)
    main_languages = [lang[0] for lang in languages[:3]]

    # Prepare the prompt to feed the Hugging Face model
    prompt = f"""
Generate a job description for a developer role working on a GitHub project.

The project is called {repo_data['name']}. Here is some key information about the project:
- Project Description: {description} (if available, otherwise provide a brief and appealing overview)
- GitHub Statistics: The project has {repo_data['stars']} stars, {repo_data['forks']} forks, and {repo_data['open_issues']} open issues.
- Technical Skills: The project primarily uses {', '.join(main_languages)} (you can mention any related technologies if applicable).
- Responsibilities: List the primary responsibilities of a developer working on this project (e.g., coding, bug fixing, collaborating with the team, etc.).
- Preferred Qualifications: List the qualifications that would make someone a strong candidate for this position (e.g., experience, communication skills, etc.).

Make the job description attractive and easy to read, highlighting the project's importance and appeal to potential developers.
"""

    # Generate job description using the Hugging Face model
    generated_description = generator(prompt, max_length=300, num_return_sequences=1)[0]['generated_text']
    
    # Return the generated description
    return generated_description

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    github_url = request.json.get('github_url')
    owner, repo = extract_repo_info(github_url)
    
    if not owner or not repo:
        return jsonify({'error': 'Invalid GitHub URL'}), 400
    
    repo_data = analyze_repository(owner, repo)
    if not repo_data:
        return jsonify({'error': 'Unable to analyze repository'}), 400
    
    job_description = generate_job_description(repo_data)
    return jsonify({'job_description': job_description})

if __name__ == '__main__':
    app.run(debug=True)
