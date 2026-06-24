param(
    [string]$Text = "The video explains how to prepare a cup of coffee: grind the beans, control the water temperature, and pour slowly until extraction is complete.",
    [string]$Lang = "zh",
    [string]$ApiBase = "https://api.minimaxi.com/v1",
    [string]$Model = "MiniMax-M2.7",
    [string]$SystemPromptFile = "prompts/default-system.txt",
    [string]$UserPromptFile = "prompts/default-video-summary.txt",
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"

if (-not $env:VIDEO_AGENT_LLM_API_KEY) {
    throw "VIDEO_AGENT_LLM_API_KEY is required."
}

$pythonCode = @'
import json
import os
import sys
from dataclasses import asdict

from video_agent_skill.core.summarizer import summarize_text
from video_agent_skill.utils.config import LlmConfig

text = sys.argv[1]
language = sys.argv[2]
api_base = sys.argv[3]
model = sys.argv[4]
system_prompt_file = sys.argv[5]
user_prompt_file = sys.argv[6]
timeout_seconds = int(sys.argv[7])

system_prompt = ""
user_prompt_template = ""
if system_prompt_file:
    system_prompt = open(system_prompt_file, encoding="utf-8").read().strip()
if user_prompt_file:
    user_prompt_template = open(user_prompt_file, encoding="utf-8").read().strip()

content = summarize_text(
    text,
    _language=language,
    _llm=LlmConfig(
        api_base=api_base,
        model_name=model,
        api_key=os.environ["VIDEO_AGENT_LLM_API_KEY"],
        timeout_seconds=timeout_seconds,
        system_prompt=system_prompt,
        user_prompt_template=user_prompt_template,
    ),
)

print(json.dumps(asdict(content), ensure_ascii=False))
'@

$scriptPath = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "video-agent-llm-$([guid]::NewGuid()).py")
try {
    Set-Content -LiteralPath $scriptPath -Value $pythonCode -Encoding UTF8
    uv run python $scriptPath $Text $Lang $ApiBase $Model $SystemPromptFile $UserPromptFile $TimeoutSeconds
}
finally {
    Remove-Item -LiteralPath $scriptPath -Force -ErrorAction SilentlyContinue
}
