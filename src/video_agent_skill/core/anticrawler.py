from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AntiCrawlerHandler(Protocol):
    """Anti-crawler handler interface.
    
    Third-party plugins implement this interface to handle
    anti-crawler mechanisms (login, tokens, special headers).
    """
    
    @property
    def name(self) -> str:
        """Handler unique identifier."""
        ...
    
    def supports(self, url: str) -> bool:
        """Check if this handler applies to the URL."""
        ...
    
    def apply(self, ydl_opts: dict) -> dict:
        """Modify yt-dlp options to apply anti-crawler handling.
        
        Args:
            ydl_opts: Current yt-dlp options dict
            
        Returns:
            Modified yt-dlp options (must return new dict, don't modify in place)
        """
        ...