$hostAddress = "127.0.0.1"
$port = 8765
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$url = "http://$hostAddress`:$port"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Project Python environment is missing. Install the development environment first."
}

$process = Start-Process -FilePath $python -ArgumentList @("-m", "telegram_knowledge_base", "web") -WorkingDirectory $projectRoot -PassThru
for ($attempt = 0; $attempt -lt 50; $attempt++) {
    Start-Sleep -Milliseconds 200
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "$url/health" -TimeoutSec 2 | Out-Null
        break
    } catch {
        if ($process.HasExited) {
            throw "Local GUI server stopped before becoming ready."
        }
    }
}

Start-Process $url
