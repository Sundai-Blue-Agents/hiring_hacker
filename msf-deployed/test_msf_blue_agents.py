import sys
import pytest
from unittest.mock import patch, MagicMock

# Add the parent directory to the sys.path to ensure the module can be found
sys.path.insert(0, '/Users/mmoussaif/projects/dev-demo/sundai-blue-agents/hiring_hacker/deployed')

# Import from crewai_tools for GithubSearchTool
from crewai_tools import GithubSearchTool
# Import our analyze function and CustomTool class
from msf_blue_agents import analyze_github_repo, CustomTool

def test_github_search_tool():
    with pytest.raises(ValueError):
        GithubSearchTool(gh_token=None, content_types=['repo, code'])

    tool = GithubSearchTool(gh_token='valid_token', content_types=['repo, code'])
    assert tool.gh_token == 'valid_token'
    assert tool.content_types == ['repo, code']

def test_custom_tool():
    # Test CustomTool initialization
    def dummy_func(x):
        return f"Result: {x}"
    
    tool = CustomTool(
        name="Test Tool",
        description="A test tool",
        func=dummy_func
    )
    
    assert tool.name == "Test Tool"
    assert tool.description == "A test tool"
    assert tool.func("test") == "Result: test"

@patch('msf_blue_agents.requests.get')
def test_analyze_github_repo_invalid_url(mock_get):
    # Test with invalid URL
    result = analyze_github_repo('https://invalid-url.com/repo')
    assert "Invalid GitHub repository URL" in result
    
    # Ensure requests.get was not called
    mock_get.assert_not_called()

@patch('msf_blue_agents.requests.get')
def test_analyze_github_repo_valid_url(mock_get):
    # Mock responses for different API endpoints
    mock_responses = {
        'https://api.github.com/repos/owner/repo': MagicMock(
            json=lambda: {
                'name': 'test-repo',
                'description': 'Test repository',
                'stargazers_count': 100,
                'forks_count': 50,
                'watchers_count': 75,
                'open_issues_count': 10,
                'created_at': '2023-01-01',
                'updated_at': '2023-02-01',
                'license': {'name': 'MIT'}
            }
        ),
        'https://api.github.com/repos/owner/repo/languages': MagicMock(
            json=lambda: {'Python': 10000, 'JavaScript': 5000}
        ),
        'https://api.github.com/repos/owner/repo/readme': MagicMock(
            json=lambda: {'content': 'VGVzdCBSZWFkbWU='}  # Base64 for "Test Readme"
        ),
        'https://api.github.com/repos/owner/repo/contributors': MagicMock(
            json=lambda: [{}, {}, {}]  # 3 contributors
        ),
        'https://api.github.com/repos/owner/repo/contents': MagicMock(
            json=lambda: [
                {'type': 'file', 'name': 'test.py', 'url': 'https://api.github.com/repos/owner/repo/contents/test.py'}
            ]
        ),
        'https://api.github.com/repos/owner/repo/contents/test.py': MagicMock(
            json=lambda: {'content': 'cHJpbnQoImhlbGxvIHdvcmxkIik='}  # Base64 for 'print("hello world")'
        )
    }
    
    def side_effect(url, headers=None):
        return mock_responses.get(url, MagicMock(json=lambda: {}))
    
    mock_get.side_effect = side_effect
    
    # Test with valid URL
    result = analyze_github_repo('https://github.com/owner/repo')
    
    # Check that the result contains expected information
    assert 'test-repo' in result
    assert 'Test repository' in result
    assert '100' in result  # stars
    assert 'Python' in result  # language
    assert 'Test Readme' in result
    assert '3' in result  # contributors
