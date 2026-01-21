"""
Shared tools available to agents.
"""
from langchain_core.tools import tool
import subprocess
from pathlib import Path
from config import Config


@tool
def run_bash(command: str) -> str:
    """
    Execute a bash command and return output.
    Use for: file operations, xcodebuild commands, xcrun simctl, ffmpeg, etc.
    
    Returns stdout on success, stderr on failure.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120  # 2 min timeout
        )
        if result.returncode == 0:
            return result.stdout or "Command succeeded (no output)"
        else:
            return f"ERROR (exit {result.returncode}): {result.stderr}"
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out after 120 seconds"
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def read_file(file_path: str) -> str:
    """
    Read contents of a file. Use for examining Swift source files, 
    project configs, etc.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"ERROR: File not found: {file_path}"
        if path.stat().st_size > 100_000:  # 100KB limit
            return f"ERROR: File too large (>100KB). Use bash with head/tail instead."
        return path.read_text()
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def write_file(file_path: str, content: str) -> str:
    """
    Write content to a file. Use for injecting logging statements,
    creating scripts, etc.
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool  
def list_directory(dir_path: str, pattern: str = "*") -> str:
    """
    List files in a directory matching pattern.
    Examples: list_directory("/path", "*.swift"), list_directory("/path", "*View*")
    """
    try:
        path = Path(dir_path)
        if not path.exists():
            return f"ERROR: Directory not found: {dir_path}"
        files = list(path.glob(pattern))
        if not files:
            return f"No files matching '{pattern}' in {dir_path}"
        return "\n".join(str(f) for f in sorted(files)[:100])  # Limit to 100
    except Exception as e:
        return f"ERROR: {str(e)}"
