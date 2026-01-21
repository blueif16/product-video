"""
Main entry point. Single text input, human-in-the-loop when needed.
"""
import sys
from src.orchestrator import run_pipeline


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║           PRODUCT VIDEO PIPELINE                             ║
║                                                              ║
║   Describe your app and desired video.                       ║
║   I'll capture assets and (soon) generate the video.         ║
╚══════════════════════════════════════════════════════════════╝
"""


def main():
    """Interactive entry point."""
    print(BANNER)
    
    print("Describe your project and what kind of video you want:")
    print("(Include: project path, what the app does, video goals)")
    print()
    
    # Handle multi-line input
    lines = []
    print("> ", end="", flush=True)
    
    try:
        while True:
            line = input()
            if line.strip() == "":
                if lines:
                    break
                continue
            lines.append(line)
            print("  ", end="", flush=True)
    except EOFError:
        pass
    
    user_input = "\n".join(lines).strip()
    
    if not user_input:
        print("No input provided. Exiting.")
        return
    
    print()
    print("-" * 60)
    print()
    
    run_pipeline(user_input)


def run_from_string(user_input: str) -> dict:
    """Programmatic entry point."""
    return run_pipeline(user_input)


if __name__ == "__main__":
    main()
