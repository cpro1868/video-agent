param(
    [Parameter(Mandatory = $true)]
    [string]$Url,

    [string]$Lang = "zh",
    [string]$Proxy = "",
    [string]$Config = "config.yaml",
    [string]$ExpectedStrategy = "",
    [string]$PythonExe = "",
    [switch]$KeepTemp
)

$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$stdoutFile = [System.IO.Path]::GetTempFileName()
$stderrFile = [System.IO.Path]::GetTempFileName()

$argsList = @(
    "-u", $Url,
    "--lang", $Lang,
    "--transcript-only",
    "--config", $Config
)

if ($Proxy) {
    $argsList += @("--proxy", $Proxy)
}

if ($KeepTemp) {
    $argsList += "--keep-temp"
}

try {
    $nativeError = $null
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        if ($PythonExe) {
            & $PythonExe -m video_agent_skill @argsList 1> $stdoutFile 2> $stderrFile
        }
        else {
            & uv run video-agent @argsList 1> $stdoutFile 2> $stderrFile
        }
        $exitCode = $LASTEXITCODE
    }
    catch {
        $nativeError = $_
        if ($null -ne $LASTEXITCODE) {
            $exitCode = $LASTEXITCODE
        }
        else {
            $exitCode = 1
        }
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $stdout = [string](Get-Content -LiteralPath $stdoutFile -Raw -Encoding UTF8)
    $stderr = [string](Get-Content -LiteralPath $stderrFile -Raw -Encoding UTF8)

    if ([string]::IsNullOrWhiteSpace($stdout)) {
        Write-Host $stderr
        if ($nativeError) {
            Write-Host $nativeError
        }
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

    if (-not $payload.content.transcript_excerpt) {
        Write-Host ($payload | ConvertTo-Json -Depth 10)
        throw "transcript_excerpt is empty."
    }

    Write-Host "smoke-ok"
    Write-Host "strategy=$($payload.meta.strategy_used)"
    Write-Host "language=$($payload.meta.language)"
    Write-Host "excerpt_chars=$($payload.content.transcript_excerpt.Length)"
    exit $exitCode
}
finally {
    Remove-Item -LiteralPath $stdoutFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $stderrFile -Force -ErrorAction SilentlyContinue
}
