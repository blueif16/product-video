"""
Gemini 3 Pro Image Generation

Wraps the Gemini image generation API for creating enhanced visuals.

Usage:
    from tools.image_gen import generate_image, generate_image_with_reference
    
    # Simple generation
    path = generate_image("A glowing dashboard UI", aspect_ratio="16:9")
    
    # With reference image
    path = generate_image_with_reference(
        prompt="Enhanced version with glow effects",
        reference_path="/path/to/screenshot.png",
        aspect_ratio="16:9"
    )
"""
import os
import uuid
import tempfile
from pathlib import Path
from typing import Optional
from PIL import Image

from google import genai
from google.genai import types

from config import Config


# ─────────────────────────────────────────────────────────────
# Client Setup
# ─────────────────────────────────────────────────────────────

def get_genai_client() -> genai.Client:
    """Get configured Gemini client."""
    return genai.Client(api_key=Config.GEMINI_API_KEY)


# ─────────────────────────────────────────────────────────────
# Image Generation
# ─────────────────────────────────────────────────────────────

def generate_image(
    prompt: str,
    aspect_ratio: str = "16:9",
    image_size: str = "2K",
    output_dir: Optional[str] = None,
) -> str:
    """
    Generate an image from a text prompt.
    
    Args:
        prompt: Detailed description of the image to generate
        aspect_ratio: Output aspect ratio (16:9, 9:16, 1:1, etc.)
        image_size: Resolution (1K, 2K, 4K - must be uppercase)
        output_dir: Where to save the image (defaults to temp dir)
    
    Returns:
        Path to the generated image file
    
    Raises:
        ValueError: If generation fails or no image in response
    """
    client = get_genai_client()
    
    # Ensure valid aspect ratio format
    aspect_ratio = _normalize_aspect_ratio(aspect_ratio)
    
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE'],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=image_size.upper(),
            ),
        )
    )
    
    return _save_response_image(response, output_dir)


def generate_image_with_reference(
    prompt: str,
    reference_path: str,
    aspect_ratio: str = "16:9",
    image_size: str = "2K",
    output_dir: Optional[str] = None,
) -> str:
    """
    Generate an image using a reference image.
    
    Use this for:
    - Enhancing screenshots with effects (glow, atmosphere)
    - Creating artistic variations
    - Adding visual enhancements while preserving layout
    
    Args:
        prompt: What to generate/enhance
        reference_path: Path to reference image (screenshot to enhance)
        aspect_ratio: Output aspect ratio
        image_size: Resolution (1K, 2K, 4K)
        output_dir: Where to save the image
    
    Returns:
        Path to the generated image file
    """
    client = get_genai_client()
    
    # Load reference image
    if not os.path.exists(reference_path):
        raise FileNotFoundError(f"Reference image not found: {reference_path}")
    
    ref_image = Image.open(reference_path)
    aspect_ratio = _normalize_aspect_ratio(aspect_ratio)
    
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=[prompt, ref_image],
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE'],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=image_size.upper(),
            ),
        )
    )
    
    return _save_response_image(response, output_dir)


def generate_image_with_multiple_refs(
    prompt: str,
    reference_paths: list[str],
    aspect_ratio: str = "16:9",
    image_size: str = "2K",
    output_dir: Optional[str] = None,
) -> str:
    """
    Generate image with multiple reference images (up to 14 total).
    
    Args:
        prompt: Generation prompt
        reference_paths: List of paths to reference images
        aspect_ratio: Output aspect ratio
        image_size: Resolution
        output_dir: Where to save
    
    Returns:
        Path to generated image
    """
    if len(reference_paths) > 14:
        raise ValueError("Maximum 14 reference images allowed")
    
    client = get_genai_client()
    
    # Build contents list: prompt + all reference images
    contents = [prompt]
    for path in reference_paths:
        if os.path.exists(path):
            contents.append(Image.open(path))
    
    aspect_ratio = _normalize_aspect_ratio(aspect_ratio)
    
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE'],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=image_size.upper(),
            ),
        )
    )
    
    return _save_response_image(response, output_dir)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _normalize_aspect_ratio(ratio: str) -> str:
    """
    Normalize aspect ratio to API format.
    
    Accepts: "16:9", "16x9", "16/9" → Returns: "16:9"
    """
    # Replace common separators
    normalized = ratio.replace("x", ":").replace("/", ":")
    
    # Validate against known ratios
    valid_ratios = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
    if normalized not in valid_ratios:
        print(f"   ⚠️  Unknown aspect ratio '{ratio}', defaulting to 16:9")
        return "16:9"
    
    return normalized


def _save_response_image(response, output_dir: Optional[str] = None) -> str:
    """
    Extract and save image from Gemini response.
    
    Returns:
        Path to saved image file
    
    Raises:
        ValueError: If no image in response
    """
    # Use temp dir if not specified
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Look for image in response parts
    for part in response.parts:
        if hasattr(part, 'as_image'):
            image = part.as_image()
            if image:
                # Generate unique filename
                filename = f"gen_{uuid.uuid4().hex[:8]}.png"
                output_path = os.path.join(output_dir, filename)
                
                image.save(output_path)
                return output_path
    
    # No image found - check for text explanation
    text_parts = [p.text for p in response.parts if hasattr(p, 'text') and p.text]
    if text_parts:
        raise ValueError(f"Image generation failed. Model response: {' '.join(text_parts)}")
    
    raise ValueError("No image in response and no error message")


# ─────────────────────────────────────────────────────────────
# High-Level API for Editor Integration
# ─────────────────────────────────────────────────────────────

def generate_enhanced_screenshot(
    prompt: str,
    source_path: Optional[str] = None,
    aspect_ratio: str = "16:9",
    project_id: Optional[str] = None,
) -> dict:
    """
    Generate an enhanced image and upload to cloud storage.
    
    This is the main entry point for the editor phase.
    
    Args:
        prompt: What to generate/enhance
        source_path: Optional reference screenshot to enhance
        aspect_ratio: Output aspect ratio
        project_id: Video project ID (for organizing uploads)
    
    Returns:
        {
            "local_path": "/tmp/gen_xxx.png",
            "cloud_url": "https://xxx.supabase.co/storage/..."
        }
    """
    from tools.storage import upload_asset
    
    # Generate the image
    if source_path and os.path.exists(source_path):
        local_path = generate_image_with_reference(
            prompt=prompt,
            reference_path=source_path,
            aspect_ratio=aspect_ratio,
        )
    else:
        local_path = generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
        )
    
    # Upload to cloud storage
    cloud_url = None
    if project_id:
        try:
            cloud_url = upload_asset(
                local_path=local_path,
                project_id=project_id,
                subfolder="generated",
            )
        except Exception as e:
            print(f"   ⚠️  Cloud upload failed: {e}")
    
    return {
        "local_path": local_path,
        "cloud_url": cloud_url,
    }
