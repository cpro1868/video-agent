param(
    [Parameter(Mandatory = $true)]
    [string]$Url,

    [string]$Lang = "zh",
    [string]$Proxy = "",
    [string]$Config = "config.yaml",
    [string]$PythonExe = "",
    [string]$LlmApiBase = "https://api.minimaxi.com/v1",
    [string]$LlmModel = "MiniMax-M2.7",
    [string]$SystemPromptFile = "prompts/default-system.txt",
    [string]$UserPromptFile = "prompts/default-video-summary.txt",
    [string]$ExpectedStrategy = "",
    [switch]$KeepTemp
)

$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

if (-not $env:VIDEO_AGENT_LLM_API_KEY) {
    throw "VIDEO_AGENT_LLM_API_KEY is required."
}

$stdoutFile = [System.IO.Path]::GetTempFileName()
$stderrFile = [System.IO.Path]::GetTempFileName()

$argsList = @(
    "-u", $Url,
    "--lang", $Lang,
    "--config", $Config,
    "--llm-api-base", $LlmApiBase,
    "--llm-model", $LlmModel,
    "--llm-system-prompt-file", $SystemPromptFile,
    "--llm-user-prompt-file", $UserPromptFile
)

if ($Proxy) {
    $argsList += @("--proxy", $Proxy)
}

if ($KeepTemp) {
    $argsList += "--keep-temp"
}

try {
    $previousErrorActionPreference = $ErrorActionPreference
    $previousPythonPath = $env:PYTHONPATH
    try {
        $ErrorActionPreference = "Continue"
        if ($PythonExe) {
            $repoRoot = Split-Path -Parent $PSScriptRoot
            $srcPath = Join-Path $repoRoot "src"
            if (Test-Path (Join-Path $srcPath "video_agent_skill")) {
                if ($env:PYTHONPATH) {
                    $env:PYTHONPATH = "$srcPath;$env:PYTHONPATH"
                }
                else {
                    $env:PYTHONPATH = $srcPath
                }
            }
            & $PythonExe -m video_agent_skill @argsList 1> $stdoutFile 2> $stderrFile
        }
        else {
            & uv run video-agent @argsList 1> $stdoutFile 2> $stderrFile
        }
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
        $env:PYTHONPATH = $previousPythonPath
    }

    $stdout = [string](Get-Content -LiteralPath $stdoutFile -Raw -Encoding UTF8)
    $stderr = [string](Get-Content -LiteralPath $stderrFile -Raw -Encoding UTF8)

    if ([string]::IsNullOrWhiteSpace($stdout)) {
        Write-Host $stderr
        throw "video-agent produced empty stdout."
    }

    try {
        $payload = $stdout | ConvertFrom-Json
    }
    catch {
        Write-Host $stdout
        Write-Host $stderr
        throw "stdout was not valid JSON."
    }

    if ($payload.status -ne "success") {
        Write-Host ($payload | ConvertTo-Json -Depth 10)
        if (-not [string]::IsNullOrWhiteSpace($stderr)) {
            Write-Host "stderr:"
            Write-Host $stderr
        }
        throw "smoke test failed with status '$($payload.status)'."
    }

    if ($ExpectedStrategy -and $payload.meta.strategy_used -ne $ExpectedStrategy) {
        Write-Host ($payload | ConvertTo-Json -Depth 10)
        throw "expected strategy '$ExpectedStrategy' but got '$($payload.meta.strategy_used)'."
    }

    if (-not $payload.content.summary -or -not $payload.content.key_points) {
        Write-Host ($payload | ConvertTo-Json -Depth 10)
        throw "summary or key_points is empty."
    }

    if ($Lang.StartsWith("zh") -and $payload.content.summary.Length -gt 200) {
        Write-Host ($payload | ConvertTo-Json -Depth 10)
        throw "summary is longer than 200 characters."
    }

    Write-Host "smoke-ok"
    Write-Host "strategy=$($payload.meta.strategy_used)"
    Write-Host "language=$($payload.meta.language)"
    Write-Host "summary_chars=$($payload.content.summary.Length)"
    Write-Host "key_points=$($payload.content.key_points.Count)"
    exit $exitCode
}
finally {
    Remove-Item -LiteralPath $stdoutFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $stderrFile -Force -ErrorAction SilentlyContinue
}
