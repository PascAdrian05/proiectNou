param(
  [ValidateSet('checkout.session.completed','customer.subscription.created','customer.subscription.updated','customer.subscription.deleted')]
  [string]$Event = 'checkout.session.completed'
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

Write-Host "Triggering event: $Event"
docker run --rm stripe/stripe-cli:latest trigger $Event --api-key $apiKey
