$ErrorActionPreference = "Continue"

$ProjectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$ComposeFile = Join-Path $ProjectDirectory "docker-compose.yml"
$ComposeLog = Join-Path ([System.IO.Path]::GetTempPath()) "gradesense-compose.log"
$TimeoutSeconds = 300

function Stop-WithError {
    param([string]$Message)

    Write-Host ""
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Wait-ForContainer {
    param(
        [string]$Service,
        [string]$DisplayName
    )

    Write-Host "Waiting for $DisplayName..."
    $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $Deadline) {
        $ContainerId = (& docker compose -f $ComposeFile ps -q $Service 2>$null)
        if (-not $ContainerId) {
            Stop-WithError "$DisplayName container was not created."
        }

        $State = (& docker inspect --format "{{.State.Status}}" $ContainerId 2>$null)
        $Health = (& docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $ContainerId 2>$null)

        if ($State -eq "exited" -or $State -eq "dead") {
            Stop-WithError "$DisplayName container stopped unexpectedly. Run 'docker compose logs $Service' for details."
        }
        if ($Health -eq "healthy") {
            Write-Host "$DisplayName is healthy."
            return
        }
        if ($Health -eq "unhealthy") {
            Stop-WithError "$DisplayName failed its health check. Run 'docker compose logs $Service' for details."
        }

        Start-Sleep -Seconds 2
    }

    Stop-WithError "$DisplayName did not become healthy within $TimeoutSeconds seconds."
}

function Wait-ForUrl {
    param(
        [string]$Url,
        [string]$DisplayName
    )

    Write-Host "Checking $DisplayName..."
    $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $Deadline) {
        try {
            $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($Response.StatusCode -ge 200 -and $Response.StatusCode -lt 400) {
                Write-Host "$DisplayName is ready."
                return
            }
        }
        catch {
            # The service may still be starting.
        }
        Start-Sleep -Seconds 2
    }

    Stop-WithError "$DisplayName did not respond at $Url within $TimeoutSeconds seconds."
}

Set-Location $ProjectDirectory

Write-Host "Checking Docker..."
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Stop-WithError "Docker is not installed or is not available on PATH."
}

& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Stop-WithError "Docker Desktop is not running. Start Docker Desktop and run this script again."
}

& docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
    Stop-WithError "Docker Compose is not available. Install or enable the Docker Compose plugin."
}
Write-Host "Docker is running."

Write-Host "Starting GradeSense containers (existing containers and cached images will be reused)..."
& docker compose -f $ComposeFile up -d --build *> $ComposeLog
if ($LASTEXITCODE -ne 0) {
    Stop-WithError "Docker Compose could not start GradeSense. See $ComposeLog for the captured Docker output."
}

Wait-ForContainer -Service "database" -DisplayName "Database"
Wait-ForContainer -Service "backend" -DisplayName "Backend"
Wait-ForContainer -Service "frontend" -DisplayName "Frontend container"
Wait-ForUrl -Url "http://localhost:8000/health" -DisplayName "Backend API"
Wait-ForUrl -Url "http://localhost:5173/healthz" -DisplayName "Frontend"

Write-Host ""
Write-Host "=================================================="
Write-Host "GradeSense is ready!"
Write-Host ""
Write-Host "Frontend:"
Write-Host "http://localhost:5173"
Write-Host ""
Write-Host "Backend API:"
Write-Host "http://localhost:8000/docs"
Write-Host ""
Write-Host "Honeywell Demo:"
Write-Host "http://localhost:5173/honeywell-demo"
Write-Host "=================================================="
