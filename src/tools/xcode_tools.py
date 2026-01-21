"""
Xcode project parsing tools.
Programmatic extraction of bundle ID, URL schemes, and project structure.
"""
import re
import plistlib
from pathlib import Path
from typing import Optional


def find_xcodeproj(project_path: str) -> Optional[Path]:
    """
    Find .xcodeproj in the given path.
    Handles both direct .xcodeproj path and parent directory.
    """
    path = Path(project_path).expanduser()
    
    # Direct .xcodeproj path
    if path.suffix == ".xcodeproj" and path.exists():
        return path
    
    # Parent directory - search for .xcodeproj
    if path.is_dir():
        xcodeprojs = list(path.glob("*.xcodeproj"))
        if xcodeprojs:
            return xcodeprojs[0]
        # Also check one level deeper
        xcodeprojs = list(path.glob("*/*.xcodeproj"))
        if xcodeprojs:
            return xcodeprojs[0]
    
    return None


def extract_bundle_id_from_pbxproj(pbxproj_path: Path) -> Optional[str]:
    """
    Extract PRODUCT_BUNDLE_IDENTIFIER from project.pbxproj.
    """
    try:
        content = pbxproj_path.read_text()
        
        # Look for PRODUCT_BUNDLE_IDENTIFIER = "..." or = ...;
        patterns = [
            r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*"([^"]+)"',
            r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*([^;]+);',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                bundle_id = match.group(1).strip()
                # Skip variable references like $(PRODUCT_BUNDLE_IDENTIFIER)
                if not bundle_id.startswith("$("):
                    return bundle_id
        
        return None
    except Exception:
        return None


def extract_url_schemes_from_plist(info_plist_path: Path) -> list[str]:
    """
    Extract URL schemes (deep links) from Info.plist.
    """
    try:
        with open(info_plist_path, "rb") as f:
            plist = plistlib.load(f)
        
        schemes = []
        url_types = plist.get("CFBundleURLTypes", [])
        for url_type in url_types:
            url_schemes = url_type.get("CFBundleURLSchemes", [])
            schemes.extend(url_schemes)
        
        return schemes
    except Exception:
        return []


def extract_project_info(project_path: str) -> dict:
    """
    Extract bundle ID, URL schemes, and project name from an Xcode project.
    
    Args:
        project_path: Path to .xcodeproj or directory containing it
    
    Returns:
        dict with:
        - bundle_id: str or None
        - url_schemes: list[str]
        - project_name: str or None
        - xcodeproj_path: str or None
        - error: str or None (if extraction failed)
    """
    result = {
        "bundle_id": None,
        "url_schemes": [],
        "project_name": None,
        "xcodeproj_path": None,
        "error": None,
    }
    
    # Find .xcodeproj
    xcodeproj = find_xcodeproj(project_path)
    if not xcodeproj:
        result["error"] = f"No .xcodeproj found in {project_path}"
        return result
    
    result["xcodeproj_path"] = str(xcodeproj)
    result["project_name"] = xcodeproj.stem
    
    # Extract bundle ID from project.pbxproj
    pbxproj_path = xcodeproj / "project.pbxproj"
    if pbxproj_path.exists():
        bundle_id = extract_bundle_id_from_pbxproj(pbxproj_path)
        if bundle_id:
            result["bundle_id"] = bundle_id
    
    # Find Info.plist - usually in a folder with same name as project
    project_dir = xcodeproj.parent
    possible_plist_locations = [
        project_dir / xcodeproj.stem / "Info.plist",
        project_dir / "Info.plist",
        project_dir / xcodeproj.stem / f"{xcodeproj.stem}-Info.plist",
    ]
    
    for plist_path in possible_plist_locations:
        if plist_path.exists():
            schemes = extract_url_schemes_from_plist(plist_path)
            if schemes:
                result["url_schemes"] = schemes
            break
    
    if not result["bundle_id"]:
        result["error"] = "Could not extract bundle ID from project"
    
    return result
