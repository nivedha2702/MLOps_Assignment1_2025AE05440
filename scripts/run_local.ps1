param(
    [ValidateSet("all", "data", "eda", "train", "test", "api")]
    [string]$Step = "all"
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed ($LASTEXITCODE): $Program $($Arguments -join ' ')"
    }
}

if ($Step -in @("all", "data")) {
    Invoke-Checked "python" @("-m", "src.data")
}
if ($Step -in @("all", "eda")) {
    Invoke-Checked "python" @("-m", "src.eda")
}
if ($Step -in @("all", "train")) {
    Invoke-Checked "python" @("-m", "src.train")
}
if ($Step -in @("all", "test")) {
    Invoke-Checked "python" @("-m", "pytest")
    Invoke-Checked "python" @("-m", "ruff", "check", ".")
}
if ($Step -eq "api") {
    Invoke-Checked "python" @("-m", "uvicorn", "src.api:app", "--reload", "--host", "127.0.0.1", "--port", "8000")
}
