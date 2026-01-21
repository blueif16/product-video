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
    MAX_CAPTURE_ATTEMPTS = 5
    DEFAULT_RECORDING_DURATION = 8
    MODEL_NAME = "gemini-3-flash-preview"
    
    # Debug mode - set DEBUG=1 in env to enable verbose logging
    DEBUG = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")
    
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
