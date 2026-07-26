<#
.SYNOPSIS
    Rebuild the stack and seed it end to end.

.DESCRIPTION
    Runs setup in dependency order, which matters:

      1. curriculum       -> Neo4j subjects, concepts, prerequisite edges
      2. risk model       -> Neo4j risk factors and causal edges
      3. school roster    -> Postgres schools, classes, teachers, students, accounts,
                             wellbeing evidence, attendance
      4. assessments      -> concept scores, depressed by each learner's own evidence
      5. derived evidence -> Current_Academic_Performance from those scores
      6. graph projection -> the read-optimised Neo4j view of all of the above

    The academic generator needs the roster, the derived evidence needs the scores,
    and the projection needs everything.

    Seeding is administrator-only, except while the database has no accounts at all.
    Reseeding a live database therefore needs an administrator sign-in; use -AdminUser
    and -AdminPassword, or -Recreate to start from an empty schema.

.PARAMETER Recreate
    Drop and rebuild the Postgres schema first. Needed after a model change, because
    the API creates tables but never alters them.
#>
[CmdletBinding()]
param(
    [string]$ApiUrl = "http://localhost:8000",
    [switch]$Recreate,
    [switch]$KeepVolumes,
    [switch]$SkipBuild,
    [int]$StudentsPerClass = 20,
    [string]$AdminUser,
    [string]$AdminPassword = "wellbeing2026"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$session = $null

function Invoke-Step {
    param([string]$Name, [string]$Path, [object]$Body)
    Write-Host "  $Name" -NoNewline
    $params = @{ Method = "Post"; Uri = "$ApiUrl$Path"; ContentType = "application/json" }
    if ($null -ne $script:session) { $params.WebSession = $script:session }
    if ($null -ne $Body) { $params.Body = ($Body | ConvertTo-Json -Compress) }
    $result = Invoke-RestMethod @params
    Write-Host " done" -ForegroundColor Green
    return $result
}

Push-Location $root
try {
    if (-not $SkipBuild) {
        Write-Host "Rebuilding containers" -ForegroundColor Cyan
        if ($KeepVolumes) { docker compose down } else { docker compose down -v }
        docker compose build
    }

    if ($Recreate) {
        Write-Host "Recreating the Postgres schema" -ForegroundColor Cyan
        docker compose up -d postgres
        Start-Sleep -Seconds 6
        docker compose exec -T postgres psql -U kgis -d kgis -c `
            "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO kgis;" | Out-Null
        docker compose restart api 2>$null | Out-Null
    }

    docker compose up -d

    Write-Host "Waiting for the API" -ForegroundColor Cyan
    $ready = $false
    foreach ($attempt in 1..60) {
        try {
            $health = Invoke-RestMethod -Uri "$ApiUrl/health" -TimeoutSec 3
            if ($health.status -eq "ok") {
                Write-Host "  risk model: $($health.risk_model.variant) / $($health.risk_model.fingerprint)"
                $ready = $true
                break
            }
        } catch { Start-Sleep -Seconds 2 }
    }
    if (-not $ready) { throw "API did not become healthy at $ApiUrl" }

    if ($AdminUser) {
        Write-Host "Signing in as $AdminUser" -ForegroundColor Cyan
        $body = @{ username = $AdminUser; password = $AdminPassword } | ConvertTo-Json -Compress
        Invoke-RestMethod -Method Post -Uri "$ApiUrl/api/auth/login" -Body $body `
            -ContentType "application/json" -SessionVariable session | Out-Null
        $script:session = $session
    }

    Write-Host "Seeding" -ForegroundColor Cyan
    Invoke-Step "curriculum       " "/internal/import/curriculum" $null | Out-Null
    Invoke-Step "risk model       " "/internal/import/risk-model" $null | Out-Null
    $seed = Invoke-Step "school roster    " "/internal/seed/school-data" @{ students_per_class = $StudentsPerClass }

    # The roster just created the first accounts, which closes the bootstrap window.
    # Everything after this point needs an administrator, so sign in as the principal
    # it produced.
    if ($null -eq $script:session) {
        $admin = $seed.demo_credentials | Where-Object { $_.role -eq "admin" } | Select-Object -First 1
        if ($null -eq $admin) { throw "The seed produced no administrator account." }
        Write-Host "  signing in as $($admin.username) ($($admin.role_title))" -ForegroundColor DarkGray
        $body = @{ username = $admin.username; password = $admin.password } | ConvertTo-Json -Compress
        Invoke-RestMethod -Method Post -Uri "$ApiUrl/api/auth/login" -Body $body `
            -ContentType "application/json" -SessionVariable bootstrapSession | Out-Null
        $script:session = $bootstrapSession
    }

    Invoke-Step "assessments      " "/internal/generate/synthetic-data" @{} | Out-Null
    Invoke-Step "derived evidence " "/internal/generate/evidence" $null | Out-Null
    $graph = Invoke-Step "graph projection " "/internal/project/graph" $null

    Write-Host ""
    Write-Host "Seeded" -ForegroundColor Green
    Write-Host "  $($seed.school_count) schools, $($seed.class_count) classes, $($seed.teacher_count) teachers"
    Write-Host "  $($seed.student_count) students, $($seed.evidence_count) wellbeing evidence rows"
    Write-Host "  graph: $($graph.mastery_edge_count) mastery, $($graph.evidence_edge_count) evidence, $($graph.peer_edge_count) peer edges"
    Write-Host ""
    Write-Host "Demonstration accounts (password: wellbeing2026)" -ForegroundColor Cyan
    $seed.demo_credentials | Select-Object -First 8 | ForEach-Object {
        "  {0,-11} {1,-22} {2}" -f $_.role, $_.username, $_.role_title
    }
    Write-Host ""
    Write-Host "Open http://localhost:3000" -ForegroundColor Cyan
}
finally {
    Pop-Location
}
