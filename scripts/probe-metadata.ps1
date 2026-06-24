param(
    [Parameter(Mandatory = $true)]
    [string]$Url,

    [string]$Proxy = ""
)

$ErrorActionPreference = "Stop"

$pythonCode = @'
import sys

from video_agent_skill.core.extractor import _probe_video_info

url = sys.argv[1]
proxy = sys.argv[2] if len(sys.argv) > 2 else ""
info = _probe_video_info(url, proxy=proxy)
print("duration", info.get("duration"))
print("subtitles", sorted((info.get("subtitles") or {}).keys()))
print("automatic", sorted((info.get("automatic_captions") or {}).keys()))
'@

$scriptPath = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "video-agent-probe-$([guid]::NewGuid()).py")
try {
    Set-Content -LiteralPath $scriptPath -Value $pythonCode -Encoding UTF8
    uv run python $scriptPath $Url $Proxy
}
finally {
    Remove-Item -LiteralPath $scriptPath -Force -ErrorAction SilentlyContinue
}
