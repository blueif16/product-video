"""
Image Analysis with Gemini Vision using Structured Outputs

Analyzes uploaded images to extract detailed descriptions for video production.
Uses natural language embedding format: "[Type] ([Orientation]): description"
User notes guide analysis without polluting the output.
"""
from pydantic import BaseModel, Field
from PIL import Image
from google import genai
from google.genai import types

from config import Config


class ImageDescription(BaseModel):
    """
    Single image analysis result with natural language embedding.
    
    Format enforces: "[Type] ([Orientation]): [Detailed description]"
    
    Types: phone screenshot, website screenshot, tablet screenshot, 
           decorative image, product photo, icon/logo, diagram/chart
    Orientations: portrait, landscape, square
    """
    description: str = Field(
        description="""Comprehensive description that MUST start with type and orientation in brackets.

Format: "[Type] ([Orientation]): [Detailed description]"

Types: phone screenshot, website screenshot, tablet screenshot, decorative image, product photo, icon/logo, diagram/chart
Orientations: portrait, landscape, square

Example: "Phone screenshot (portrait): Dashboard displaying daily task completion metrics with purple accent color (#7C3AED), rounded cards layout, prominent Add Task button at bottom"

Include:
- Main content and UI elements
- Dominant colors (hex codes if identifiable)
- Visual style and layout
- Key interactive elements

Format as a single flowing sentence after the type/orientation prefix.
"""
    )


class BatchImageDescriptions(BaseModel):
    """Batch image analysis results."""
    descriptions: list[str] = Field(
        description="""List of descriptions, one per image in order.

Each description MUST follow format: "[Type] ([Orientation]): [Detailed description]"

If images show relationships (sequential screens, different states, related functionality), mention it naturally in the descriptions.

Example:
[
  "Phone screenshot (portrait): Login screen with email and password fields...",
  "Phone screenshot (portrait): Dashboard (accessed from previous login screen) showing..."
]
"""
    )


def get_genai_client() -> genai.Client:
    """Get configured Gemini client."""
    return genai.Client(api_key=Config.GEMINI_API_KEY)


def get_image_dimensions(image_path: str) -> tuple[int, int]:
    """
    Get image dimensions using PIL.

    Args:
        image_path: Path to image file

    Returns:
        (width, height) tuple, or (0, 0) if unable to read
    """
    try:
        with Image.open(image_path) as img:
            return img.size  # Returns (width, height)
    except Exception as e:
        print(f"Error reading image dimensions: {e}")
        return (0, 0)


def append_dimensions_to_description(description: str, width: int, height: int) -> str:
    """
    Append dimensions to description in standard format.

    Args:
        description: Base description text
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        Description with dimensions appended: "description [width×height]"
    """
    if width > 0 and height > 0:
        return f"{description} [{width}×{height}]"
    return description


SINGLE_IMAGE_PROMPT = """Analyze this image and provide a description.

Your description MUST follow this exact format:
"[Type] ([Orientation]): [Detailed content description]"

Types: phone screenshot, website screenshot, tablet screenshot, decorative image, product photo, icon/logo, diagram/chart
Orientations: portrait, landscape, square

Include in your description:
- Main content and UI elements
- Dominant colors (hex codes if identifiable)
- Visual style and layout
- Key interactive elements

Format as a single flowing sentence after the type/orientation prefix.

Example: "Phone screenshot (portrait): Dashboard displaying daily task completion metrics with purple accent color (#7C3AED), rounded cards layout, prominent Add Task button at bottom"
"""


BATCH_IMAGE_PROMPT = """Analyze these {count} images and provide descriptions.

Each description MUST follow this exact format:
"[Type] ([Orientation]): [Detailed content description]"

Types: phone screenshot, website screenshot, tablet screenshot, decorative image, product photo, icon/logo, diagram/chart
Orientations: portrait, landscape, square

For each image include:
- Main content and UI elements
- Dominant colors (hex codes if identifiable)
- Visual style and layout
- Key interactive elements

If images show relationships (sequential screens, different states, related functionality), mention it naturally within the descriptions.

Return one description per image in the exact order provided.
"""


def analyze_image(image_path: str, user_note: str = "") -> dict:
    """
    Analyze a single image using Gemini Vision with structured output.

    Args:
        image_path: Path to the image file
        user_note: Optional context from user about this image's purpose/content

    Returns:
        dict with:
            - description: String description with dimensions appended
            - width: Image width in pixels
            - height: Image height in pixels
    """
    # Get dimensions first
    width, height = get_image_dimensions(image_path)

    try:
        with open(image_path, "rb") as f:
            image_data = f.read()

        client = get_genai_client()

        # Build prompt with optional user context
        prompt = SINGLE_IMAGE_PROMPT
        if user_note:
            prompt += f'\n\nUser\'s context: "{user_note}"\nUse this to understand the image\'s purpose and describe it accordingly.'

        response = client.models.generate_content(
            model=Config.MODEL_NAME,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(
                            data=image_data,
                            mime_type="image/png"
                        ),
                        types.Part.from_text(text=prompt)
                    ]
                )
            ],
            config={
                "response_mime_type": "application/json",
                "response_json_schema": ImageDescription.model_json_schema(),
            }
        )

        result = ImageDescription.model_validate_json(response.text)
        base_description = result.description

        # Append dimensions to description
        full_description = append_dimensions_to_description(base_description, width, height)

        return {
            "description": full_description,
            "width": width,
            "height": height,
        }

    except Exception as e:
        print(f"Error analyzing image: {e}")
        fallback_desc = append_dimensions_to_description(
            "Image file (portrait): Image analysis failed, manual review required",
            width,
            height
        )
        return {
            "description": fallback_desc,
            "width": width,
            "height": height,
            "error": str(e)
        }


def analyze_image_batch(image_paths: list[str], user_notes: list[str] = None) -> list[dict]:
    """
    Analyze multiple images in a single batch request.
    
    This is the recommended approach for upload mode - all images analyzed together
    in one call, allowing the model to understand relationships and context.

    Args:
        image_paths: List of image file paths
        user_notes: Optional list of user context notes (one per image)

    Returns:
        List of dicts, each with:
            - description: String description with dimensions appended
            - width: Image width in pixels
            - height: Image height in pixels
            - path: Original image path
    """
    if not image_paths:
        return []

    # Default to empty notes if not provided
    if user_notes is None:
        user_notes = [""] * len(image_paths)
    
    # Ensure notes list matches images list
    if len(user_notes) != len(image_paths):
        user_notes = user_notes + [""] * (len(image_paths) - len(user_notes))

    # Get dimensions for all images first
    dimensions_list = [get_image_dimensions(path) for path in image_paths]

    try:
        # Read all image data
        image_parts = []
        for path in image_paths:
            with open(path, "rb") as f:
                image_data = f.read()
                image_parts.append(
                    types.Part.from_bytes(
                        data=image_data,
                        mime_type="image/png"
                    )
                )

        # Build prompt with user context
        prompt = BATCH_IMAGE_PROMPT.format(count=len(image_paths))
        
        # Add user notes context if any are provided
        if any(user_notes):
            prompt += "\n\nUser's context for each image:\n"
            for i, note in enumerate(user_notes, 1):
                if note:
                    prompt += f"Image {i}: \"{note}\"\n"
                else:
                    prompt += f"Image {i}: (no user note)\n"
            prompt += "\nUse these notes to understand each image's purpose and describe accordingly."

        # Add prompt at the end
        image_parts.append(types.Part.from_text(text=prompt))

        client = get_genai_client()

        response = client.models.generate_content(
            model=Config.MODEL_NAME,
            contents=[
                types.Content(
                    role="user",
                    parts=image_parts
                )
            ],
            config={
                "response_mime_type": "application/json",
                "response_json_schema": BatchImageDescriptions.model_json_schema(),
            }
        )

        result = BatchImageDescriptions.model_validate_json(response.text)
        base_descriptions = result.descriptions

        # Combine descriptions with dimensions
        results = []
        for i, (path, base_desc) in enumerate(zip(image_paths, base_descriptions)):
            width, height = dimensions_list[i]
            full_description = append_dimensions_to_description(base_desc, width, height)
            results.append({
                "description": full_description,
                "width": width,
                "height": height,
                "path": path,
            })

        return results

    except Exception as e:
        print(f"Error analyzing image batch: {e}")
        # Return fallback for each image
        results = []
        for i, path in enumerate(image_paths):
            width, height = dimensions_list[i]
            fallback_desc = append_dimensions_to_description(
                "Image file (portrait): Batch analysis failed, manual review required",
                width,
                height
            )
            results.append({
                "description": fallback_desc,
                "width": width,
                "height": height,
                "path": path,
                "error": str(e)
            })
        return results


# Commented out: Parallel analysis approach (kept for reference)
# This would be used if you wanted true parallelism instead of batch analysis
"""
async def analyze_images_parallel(image_paths: list[str], user_notes: list[str] = None) -> list[dict]:
    '''
    Analyze multiple images in parallel using asyncio.
    
    Faster wall-clock time but no cross-image context awareness.
    Use this if you don't need the model to understand relationships between images.
    
    Args:
        image_paths: List of image file paths
        user_notes: Optional list of user context notes (one per image)
    
    Returns:
        List of dicts (same format as analyze_image_batch)
    '''
    import asyncio
    
    if user_notes is None:
        user_notes = [""] * len(image_paths)
    
    # Ensure notes list matches images list
    if len(user_notes) != len(image_paths):
        user_notes = user_notes + [""] * (len(image_paths) - len(user_notes))
    
    # Create tasks for parallel execution
    tasks = [
        asyncio.to_thread(analyze_image, path, note)
        for path, note in zip(image_paths, user_notes)
    ]
    
    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks)
    
    # Add path to each result
    for result, path in zip(results, image_paths):
        result["path"] = path
    
    return results
"""
