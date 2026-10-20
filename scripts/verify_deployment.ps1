param(
    [string]$ApiUrl = "http://127.0.0.1:8000",
    [string]$PrometheusUrl = "http://127.0.0.1:9090",
    [string]$GrafanaUrl = "http://127.0.0.1:3000",
    [int]$ScrapeTimeoutSeconds = 90
)

$ErrorActionPreference = "Stop"
$ApiUrl = $ApiUrl.TrimEnd("/")
$PrometheusUrl = $PrometheusUrl.TrimEnd("/")
$GrafanaUrl = $GrafanaUrl.TrimEnd("/")

function Wait-ForEndpoint {
    param(
        [string]$Uri,
        [int]$Attempts = 30
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            return Invoke-RestMethod -Uri $Uri -TimeoutSec 5
        }
        catch {
            if ($attempt -eq $Attempts) {
                throw "Endpoint did not become ready: $Uri. $($_.Exception.Message)"
            }
            Start-Sleep -Seconds 2
        }
    }
}

Write-Host "Checking API health at $ApiUrl/health"
$health = Wait-ForEndpoint -Uri "$ApiUrl/health"
if ($health.status -ne "ok") {
    throw "API health check failed: $($health | ConvertTo-Json -Compress)"
}
Write-Host "API health: $($health.status)"

$payload = @{
    age = 63
    sex = 1
    cp = 1
    trestbps = 145
    chol = 233
    fbs = 1
    restecg = 2
    thalach = 150
    exang = 0
    oldpeak = 2.3
    slope = 3
    ca = 0
    thal = 6
} | ConvertTo-Json

Write-Host "Sending a synthetic sample to $ApiUrl/predict"
$prediction = Invoke-RestMethod `
    -Method Post `
    -Uri "$ApiUrl/predict" `
    -ContentType "application/json" `
    -Body $payload `
    -TimeoutSec 20
if ($prediction.prediction -notin @(0, 1)) {
    throw "Prediction response does not contain a binary prediction."
}
if ($prediction.confidence -lt 0 -or $prediction.confidence -gt 1) {
    throw "Prediction confidence is outside [0, 1]."
}
$prediction | ConvertTo-Json

Write-Host "Checking API Prometheus exposition at $ApiUrl/metrics"
$apiMetrics = Invoke-RestMethod -Uri "$ApiUrl/metrics" -TimeoutSec 10
if ($apiMetrics -notmatch "heart_api_requests_total") {
    throw "API /metrics response is missing heart_api_requests_total."
}
Write-Host "API metrics endpoint is returning heart_api_requests_total."

$queryUrl = "$PrometheusUrl/api/v1/query?query=min%28up%7Bjob%3D%22heart-disease-api%22%7D%29"
$deadline = (Get-Date).AddSeconds($ScrapeTimeoutSeconds)
$targetUp = $false
do {
    try {
        $result = Invoke-RestMethod -Uri $queryUrl -TimeoutSec 10
        if (
            $result.status -eq "success" -and
            $result.data.result.Count -gt 0 -and
            [double]$result.data.result[0].value[1] -eq 1
        ) {
            $targetUp = $true
            break
        }
    }
    catch {
        Write-Host "Waiting for Prometheus: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 5
} while ((Get-Date) -lt $deadline)

if (-not $targetUp) {
    throw "Prometheus did not report the heart-disease-api target as UP within $ScrapeTimeoutSeconds seconds."
}
Write-Host "Prometheus target: UP"

Write-Host "Checking Grafana health at $GrafanaUrl/api/health"
$grafanaHealth = Wait-ForEndpoint -Uri "$GrafanaUrl/api/health"
if ($grafanaHealth.database -ne "ok") {
    throw "Grafana health check failed: $($grafanaHealth | ConvertTo-Json -Compress)"
}
Write-Host "Grafana health: $($grafanaHealth.database)"
Write-Host "All API, Prometheus, and Grafana deployment checks passed."
