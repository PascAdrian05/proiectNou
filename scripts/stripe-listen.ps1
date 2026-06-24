param(
  [string]$ForwardTo = "http://host.docker.internal:8000/api/v1/billing/stripe/webhook"
)

$envFile = Join-Path $PSScriptRoot "..\backend\.env"
if (-not (Test-Path $envFile)) {
  Write-Error "Missing backend/.env"
  exit 1
}

$apiKeyLine = (Get-Content $envFile | Where-Object { $_ -like 'STRIPE_API_KEY=*' } | Select-Object -First 1)
if (-not $apiKeyLine) {
  Write-Error "STRIPE_API_KEY is missing in backend/.env"
  exit 1
}

$apiKey = ($apiKeyLine -split '=', 2)[1].Trim()
if (-not $apiKey) {
  Write-Error "STRIPE_API_KEY is empty in backend/.env"
  exit 1
}

Write-Host "Starting Stripe listener via Docker..."
Write-Host "Forwarding to: $ForwardTo"
Write-Host "Copy the shown webhook secret and set STRIPE_WEBHOOK_SECRET in backend/.env"

docker run --rm -it stripe/stripe-cli:latest listen --api-key $apiKey --forward-to $ForwardTo
