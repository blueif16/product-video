"""
Centralized configuration. Load once, use everywhere.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

    # Supabase URL
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    
    # ─────────────────────────────────────────────────────────────
    # Supabase API Keys - New format (sb_publishable_... / sb_secret_...)
    # ─────────────────────────────────────────────────────────────
    SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")
    SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
    
    # ─────────────────────────────────────────────────────────────
    # Legacy Supabase Keys (deprecated, for backwards compatibility)
    # ─────────────────────────────────────────────────────────────
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    # Capture settings
    CAPTURES_OUTPUT_DIR = Path(os.getenv("CAPTURES_OUTPUT_DIR", "/tmp/productvideo_captures"))

    # Permanent assets (where screenshots get copied after capture for Remotion access)
    PROJECT_ROOT = Path(__file__).parent.parent
    PERMANENT_ASSETS_DIR = PROJECT_ROOT / "assets" / "captures"

    # Supabase Storage
    SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "captures")
    
    MAX_CAPTURE_ATTEMPTS = 5
    DEFAULT_RECORDING_DURATION = 8
    MODEL_NAME = "gemini-3-flash-preview"

    # ─────────────────────────────────────────────────────────────
    # Video Trimming Configuration
    # ─────────────────────────────────────────────────────────────
    # 是否自动裁剪视频中的静态帧
    AUTO_TRIM_STATIC_FRAMES = os.getenv("AUTO_TRIM_STATIC_FRAMES", "true").lower() == "true"

    # 运动检测阈值（None = 自动检测）
    _threshold_env = os.getenv("MOTION_DETECTION_THRESHOLD")
    MOTION_DETECTION_THRESHOLD = float(_threshold_env) if _threshold_env else None

    # 最小运动时长（秒）
    MIN_MOTION_DURATION = float(os.getenv("MIN_MOTION_DURATION", "0.3"))

    # 合并间隔（秒）
    MERGE_GAP = float(os.getenv("MERGE_GAP", "0.3"))

    # 缓冲时间（秒）
    BUFFER_TIME = float(os.getenv("BUFFER_TIME", "0.2"))

    # Debug mode - set DEBUG=1 in env to enable verbose logging
    DEBUG = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")
    
    # ─────────────────────────────────────────────────────────────
    # Exploration Limits (for stuck loop detection)
    # ─────────────────────────────────────────────────────────────
    # Max describe_screen calls before forcing HITL
    MAX_DESCRIBE_CALLS = int(os.getenv("MAX_DESCRIBE_CALLS", "12"))
    
    # Max navigation attempts (taps/swipes/open_urls) without reaching target
    MAX_NAVIGATION_ATTEMPTS = int(os.getenv("MAX_NAVIGATION_ATTEMPTS", "20"))
    
    # Whether to enable HITL for stuck agents (set to false for fully automated runs)
    ENABLE_HITL = os.getenv("ENABLE_HITL", "true").lower() == "true"
    
    @classmethod
    def get_supabase_key(cls, elevated: bool = True) -> str:
        """
        Get the appropriate Supabase API key.
        
        Args:
            elevated: If True, use secret/service_role key (bypasses RLS).
                     If False, use publishable/anon key (respects RLS).
        
        Returns:
            API key string (prefers new format, falls back to legacy)
        
        Priority:
            1. New format (sb_publishable_... or sb_secret_...)
            2. Legacy format (anon or service_role JWT)
            3. Old single SUPABASE_KEY (deprecated)
        """
        if elevated:
            # Server-side operations - use secret key
            if cls.SUPABASE_SECRET_KEY:
                return cls.SUPABASE_SECRET_KEY
            if cls.SUPABASE_SERVICE_ROLE_KEY:
                return cls.SUPABASE_SERVICE_ROLE_KEY
        else:
            # Client-safe operations - use publishable key
            if cls.SUPABASE_PUBLISHABLE_KEY:
                return cls.SUPABASE_PUBLISHABLE_KEY
            if cls.SUPABASE_ANON_KEY:
                return cls.SUPABASE_ANON_KEY
        
        # Fallback to legacy single key (deprecated)
        legacy_key = os.getenv("SUPABASE_KEY")
        if legacy_key:
            import warnings
            warnings.warn(
                "SUPABASE_KEY is deprecated. Use SUPABASE_PUBLISHABLE_KEY and "
                "SUPABASE_SECRET_KEY instead. See .env.example for details.",
                DeprecationWarning
            )
            return legacy_key
        
        raise ValueError(
            "No Supabase API key found. Set SUPABASE_SECRET_KEY (or SUPABASE_PUBLISHABLE_KEY) "
            "in your .env file. See .env.example for the new key format."
        )


def get_model() -> ChatGoogleGenerativeAI:
    """Get the Gemini model for all LangGraph agents."""
    return ChatGoogleGenerativeAI(
        model=Config.MODEL_NAME,
        google_api_key=Config.GEMINI_API_KEY,
        temperature=0,
        # Required for Gemini 3 models - preserves thought signatures during tool calls
        include_thoughts=True,
    )
