$ErrorActionPreference = "Stop"
$namespace = "heart-disease-mlops"

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    throw "kubectl is not installed or is not on PATH."
}

$currentContext = & kubectl config current-context
if ($LASTEXITCODE -ne 0) {
    throw "Could not determine the current Kubernetes context."
}
Write-Host "Cleaning only namespace '$namespace' from context '$currentContext'."

$namespaceExists = & kubectl get namespace $namespace --ignore-not-found -o name
if ($LASTEXITCODE -ne 0) {
    throw "Could not inspect namespace '$namespace'."
}
if (-not $namespaceExists) {
    Write-Host "Namespace '$namespace' does not exist; nothing to clean."
    exit 0
}

& kubectl delete namespace $namespace --wait=false
if ($LASTEXITCODE -ne 0) {
    throw "Could not request deletion of namespace '$namespace'."
}

$deadline = (Get-Date).AddSeconds(90)
do {
    $serviceJson = & kubectl get service heart-disease-api `
        -n $namespace `
        --ignore-not-found `
        -o json
    if ($LASTEXITCODE -eq 0 -and $serviceJson) {
        $service = $serviceJson | ConvertFrom-Json
        $hasExternalAddress = (
            $null -ne $service.status.loadBalancer.ingress -and
            @($service.status.loadBalancer.ingress).Count -gt 0
        )
        $hasCleanupFinalizer = @($service.metadata.finalizers) `
            -contains "service.kubernetes.io/load-balancer-cleanup"
        if (
            $service.metadata.deletionTimestamp -and
            $service.spec.type -eq "LoadBalancer" -and
            -not $hasExternalAddress -and
            $hasCleanupFinalizer
        ) {
            $patchPath = [IO.Path]::GetTempFileName()
            try {
                [IO.File]::WriteAllText($patchPath, '{"metadata":{"finalizers":[]}}')
                & kubectl patch service heart-disease-api `
                    -n $namespace `
                    --type=merge `
                    --patch-file $patchPath
                if ($LASTEXITCODE -ne 0) {
                    throw "Could not release the pending local LoadBalancer cleanup finalizer."
                }
                Write-Host "Released cleanup finalizer for the local Service with no external IP."
            }
            finally {
                Remove-Item -LiteralPath $patchPath -Force -ErrorAction SilentlyContinue
            }
        }
    }
    elseif ($LASTEXITCODE -ne 0) {
        throw "Could not inspect the API Service while cleaning the namespace."
    }

    $namespaceExists = & kubectl get namespace $namespace --ignore-not-found -o name
    if ($LASTEXITCODE -ne 0) {
        throw "Could not check whether namespace '$namespace' was deleted."
    }
    if (-not $namespaceExists) {
        Write-Host "Namespace '$namespace' and its assignment resources were removed."
        exit 0
    }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)

throw "Namespace '$namespace' is still terminating. Inspect it with kubectl get namespace $namespace -o yaml."
