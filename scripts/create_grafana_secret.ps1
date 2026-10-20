$ErrorActionPreference = "Stop"

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    throw "kubectl is not installed or is not on PATH."
}

$namespaceManifest = @"
apiVersion: v1
kind: Namespace
metadata:
  name: heart-disease-mlops
"@
$namespaceManifest | & kubectl apply -f -
if ($LASTEXITCODE -ne 0) {
    throw "kubectl could not create the heart-disease-mlops namespace."
}

$securePassword = Read-Host "Enter a local Grafana admin password" -AsSecureString
$pointer = [IntPtr]::Zero
$plainPassword = $null
$encodedPassword = $null

try {
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    $encodedPassword = [Convert]::ToBase64String(
        [Text.Encoding]::UTF8.GetBytes($plainPassword)
    )
    $manifest = @"
apiVersion: v1
kind: Secret
metadata:
  name: grafana-admin
  namespace: heart-disease-mlops
type: Opaque
data:
  admin-password: $encodedPassword
"@
    $manifest | & kubectl apply -f -
    if ($LASTEXITCODE -ne 0) {
        throw "kubectl could not create the grafana-admin Secret."
    }
}
finally {
    if ($pointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
    $plainPassword = $null
    $encodedPassword = $null
    $manifest = $null
    $securePassword.Dispose()
}
