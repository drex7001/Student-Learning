[CmdletBinding()]
param(
    [string]$ApiUrl = "http://localhost:8000",
    [string]$StudentId = "STU-001",
    [string]$SubjectId = "OL-MATH",
    [switch]$KeepVolumes,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Action
}

function Wait-ForApi {
    param(
        [string]$HealthUrl,
        [int]$Attempts = 60,
        [int]$DelaySeconds = 2
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            $response = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 5
            if ($response.status -eq "ok") {
                Write-Host "API is ready." -ForegroundColor Green
                return
            }
        }
        catch {
            Write-Host "Waiting for API ($attempt/$Attempts)..." -ForegroundColor DarkGray
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    throw "API did not become ready at $HealthUrl"
}

function Invoke-JsonPost {
    param(
        [string]$Uri,
        [object]$Body = @{}
    )

    Invoke-RestMethod `
        -Method Post `
        -Uri $Uri `
        -ContentType "application/json" `
        -Body ($Body | ConvertTo-Json -Depth 10)
}

Invoke-Step "Reset Docker stack" {
    if ($KeepVolumes) {
        docker compose down
    }
    else {
        docker compose down -v
    }
}

if (-not $SkipBuild) {
    Invoke-Step "Build Docker images without cache" {
        docker compose build --no-cache
    }
}

Invoke-Step "Start Docker stack" {
    docker compose up -d
}

Invoke-Step "Wait for API" {
    Wait-ForApi -HealthUrl "$ApiUrl/health"
}

Invoke-Step "Import curriculum into Neo4j" {
    $result = Invoke-JsonPost -Uri "$ApiUrl/internal/import/curriculum"
    $result | ConvertTo-Json -Depth 10
}

Invoke-Step "Generate synthetic student data" {
    $result = Invoke-JsonPost -Uri "$ApiUrl/internal/generate/synthetic-data"
    $result | ConvertTo-Json -Depth 10
}

Invoke-Step "Seed quiz questions from data/quiz" {
    $profile = Invoke-RestMethod -Uri "$ApiUrl/api/learn/student/$StudentId/subject/$SubjectId"
    $profile.recommended_quiz | ConvertTo-Json -Depth 10

    if (($profile.recommended_quiz.question_count -as [int]) -le 0) {
        throw "Quiz seeding completed, but recommended question count is 0 for $StudentId / $SubjectId."
    }
}

Invoke-Step "Verify quiz start and Sinhala fields" {
    $quiz = Invoke-JsonPost `
        -Uri "$ApiUrl/api/learn/quiz/start" `
        -Body @{
            student_id = $StudentId
            subject_id = $SubjectId
            concept_ids = @("MATH-001")
            quiz_length = 5
        }

    if (-not $quiz.questions -or $quiz.questions.Count -eq 0) {
        throw "Quiz start returned no questions."
    }

    $quiz.questions | Select-Object id, prompt, prompt_si | Format-Table -AutoSize
}

Invoke-Step "Verify quiz rows in Postgres" {
    docker compose exec -T postgres psql -U kgis -d kgis -c "select subject_id, count(*) from quiz_questions group by subject_id order by subject_id;"
}

Write-Host ""
Write-Host "Reset and seed completed." -ForegroundColor Green
Write-Host "Teacher dashboard: http://localhost:3000"
Write-Host "Student learning:  http://localhost:3000/learn?subject=$SubjectId&student=$StudentId"
