from __future__ import annotations

import json
import os
import tempfile
import uuid
from typing import Protocol, runtime_checkable
from urllib.request import Request, urlopen


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


class BilibiliAntiCrawlerHandler:
    """Built-in B站 anti-crawler handler for HTTP 412 bypass."""
    
    name = "bilibili-412"
    
    def supports(self, url: str) -> bool:
        return "bilibili.com" in url
    
    def apply(self, ydl_opts: dict) -> dict:
        """Apply B站-specific anti-crawler headers and cookies."""
        new_opts = ydl_opts.copy()
        headers = new_opts.get("http_headers", {}).copy()
        
        headers["Origin"] = "https://www.bilibili.com"
        headers["Referer"] = "https://www.bilibili.com/"
        
        new_opts["http_headers"] = headers
        new_opts["cookiefile"] = self._get_bilibili_cookie_file()
        
        return new_opts
    
    def _get_bilibili_cookie_file(self) -> str:
        """Generate a temporary cookie file with buvid3/buvid4 fingerprint."""
        try:
            req = Request(
                "https://api.bilibili.com/x/frontend/finger/spi",
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    ),
                    "Referer": "https://www.bilibili.com/",
                },
            )
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            buvid3 = data.get("data", {}).get("b_3", "")
            buvid4 = data.get("data", {}).get("b_4", "")
        except Exception:
            buvid3 = ""
            buvid4 = ""
        
        if not buvid3:
            buvid3 = f"{uuid.uuid4().hex.upper()}infoc"
        
        cookie_lines = [
            "# Netscape HTTP Cookie File",
            "# https://curl.haxx.se/rfc/cookie_spec.html",
            "# This is a generated file!  Do not edit.",
            "",
            f".bilibili.com\tTRUE\t/\tFALSE\t0\tbuvid3\t{buvid3}",
        ]
        if buvid4:
            cookie_lines.append(f".bilibili.com\tTRUE\t/\tFALSE\t0\tbuvid4\t{buvid4}")
        
        cookie_content = "\n".join(cookie_lines) + "\n"
        
        fd, path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w") as f:
            f.write(cookie_content)
        return path