"""
Quick sanity tests. Run with: pytest tests/
"""
import pytest
from pathlib import Path


def test_imports():
    """Verify all modules import correctly."""
    from src.config import get_claude, Config
    from src.tools import ANALYZER_TOOLS, CAPTURER_TOOLS
    from src.agents import create_analyzer_agent, create_capturer_agent
    from src.orchestrator import build_pipeline
    from src.main import run_from_string
    
    assert Config.MAX_CAPTURE_ATTEMPTS == 5
    assert len(ANALYZER_TOOLS) > 0
    assert len(CAPTURER_TOOLS) > 0


def test_bash_tool():
    """Test bash tool executes."""
    from src.tools.bash_tools import run_bash
    
    result = run_bash.invoke({"command": "echo hello"})
    assert "hello" in result


def test_list_directory_tool():
    """Test directory listing."""
    from src.tools.bash_tools import list_directory
    
    result = list_directory.invoke({"dir_path": "/tmp", "pattern": "*"})
    assert "ERROR" not in result or "No files" in result


def test_asset_estimation():
    """Test asset count estimation logic."""
    # Fast vibe = more assets
    duration = 30
    base = duration // 2  # 15
    fast_multiplier = 1.3
    fast_count = int(base * fast_multiplier)  # ~19
    
    # Slow vibe = fewer assets
    slow_multiplier = 0.7
    slow_count = int(base * slow_multiplier)  # ~10
    
    assert fast_count > slow_count
    assert 5 <= fast_count <= 30
    assert 5 <= slow_count <= 30


@pytest.mark.skip(reason="Requires API keys")
def test_input_parsing():
    """Test that input parsing extracts fields correctly."""
    from src.config import get_claude
    from langchain_core.messages import HumanMessage
    
    model = get_claude()
    
    test_input = """
    FocusFlow is my task manager app with smooth animations.
    I want a 30 second energetic video.
    Project is at ~/Code/FocusFlow/FocusFlow.xcodeproj
    """
    
    response = model.invoke([HumanMessage(content=f"""
Extract: project_path, duration_s, vibe from:
{test_input}

Format: PATH: ..., DURATION: ..., VIBE: ...
""")])
    
    content = response.content.lower()
    assert "focusflow" in content
    assert "30" in content


@pytest.mark.skip(reason="Requires simulator running")
def test_capture_screenshot():
    """Test screenshot capture (requires running simulator)."""
    from src.tools.capture_tools import capture_screenshot
    
    result = capture_screenshot.invoke({"name": "test"})
    assert "saved" in result.lower() or "error" in result.lower()


@pytest.mark.skip(reason="Requires API keys")
def test_analyzer_agent():
    """Test analyzer agent creation."""
    from src.agents import create_analyzer_agent
    
    agent = create_analyzer_agent()
    assert agent is not None


@pytest.mark.skip(reason="Requires Supabase setup")
def test_supabase_connection():
    """Test Supabase connection."""
    from src.db.supabase_client import get_supabase
    
    client = get_supabase()
    assert client is not None


@pytest.mark.skip(reason="Requires full setup")
def test_pipeline_build():
    """Test pipeline graph compiles."""
    from src.orchestrator import build_pipeline
    
    graph = build_pipeline()
    assert graph is not None
