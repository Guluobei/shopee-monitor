# Shopee Competitor Suite Check Script
# Run: powershell -ExecutionPolicy Bypass -File check-suite.ps1

param([string]$SuitePath = ".")

Write-Host "============================================================"
Write-Host "Shopee Competitor Suite Integrity Check"
Write-Host "============================================================"

$pass = 0
$warn = 0
$fail = 0

# Check main SKILL.md
$mainSkill = Join-Path $SuitePath "SKILL.md"
if (Test-Path $mainSkill) {
    Write-Host "[PASS] Main SKILL.md exists" -ForegroundColor Green
    $pass++
} else {
    Write-Host "[FAIL] Main SKILL.md missing" -ForegroundColor Red
    $fail++
}

# Check sub-skills
$subSkills = @("shopee-scraper", "competitor-analysis", "report-generator")
foreach ($skill in $subSkills) {
    $skillFile = Join-Path $SuitePath "skills\$skill\SKILL.md"
    if (Test-Path $skillFile) {
        Write-Host "[PASS] Sub-skill $skill exists" -ForegroundColor Green
        $pass++
    } else {
        Write-Host "[FAIL] Sub-skill $skill missing" -ForegroundColor Red
        $fail++
    }
}

# Check config
$configFile = Join-Path $SuitePath "config\competitors.yaml"
if (Test-Path $configFile) {
    Write-Host "[PASS] Config file exists" -ForegroundColor Green
    $pass++
} else {
    Write-Host "[FAIL] Config file missing" -ForegroundColor Red
    $fail++
}

# Check references
$refs = @("market-insights.md", "product-lines.md", "competitor-metrics.md")
foreach ($ref in $refs) {
    $refFile = Join-Path $SuitePath "references\$ref"
    if (Test-Path $refFile) {
        Write-Host "[PASS] Reference $ref exists" -ForegroundColor Green
        $pass++
    } else {
        Write-Host "[WARN] Reference $ref missing" -ForegroundColor Yellow
        $warn++
    }
}

# Check scripts
$scripts = @(
    "skills\shopee-scraper\scripts\zhixia_monitor.py",
    "skills\shopee-scraper\scripts\zhixia_scraper.py",
    "skills\competitor-analysis\scripts\data_processor.py"
)
foreach ($script in $scripts) {
    $scriptFile = Join-Path $SuitePath $script
    if (Test-Path $scriptFile) {
        Write-Host "[PASS] Script $script exists" -ForegroundColor Green
        $pass++
    } else {
        Write-Host "[FAIL] Script $script missing" -ForegroundColor Red
        $fail++
    }
}

# Check README
$readme = Join-Path $SuitePath "README.md"
if (Test-Path $readme) {
    Write-Host "[PASS] README.md exists" -ForegroundColor Green
    $pass++
} else {
    Write-Host "[FAIL] README.md missing" -ForegroundColor Red
    $fail++
}

# Check test prompts
$testPrompts = Join-Path $SuitePath "examples\test-prompts.json"
if (Test-Path $testPrompts) {
    Write-Host "[PASS] test-prompts.json exists" -ForegroundColor Green
    $pass++
} else {
    Write-Host "[WARN] test-prompts.json missing" -ForegroundColor Yellow
    $warn++
}

# Summary
Write-Host ""
Write-Host "============================================================"
Write-Host "Summary"
Write-Host "============================================================"
Write-Host "PASS: $pass" -ForegroundColor Green
Write-Host "WARN: $warn" -ForegroundColor Yellow
Write-Host "FAIL: $fail" -ForegroundColor Red

if ($fail -gt 0) {
    Write-Host ""
    Write-Host "[RESULT] Suite incomplete - fix FAIL items" -ForegroundColor Red
    exit 1
} elseif ($warn -gt 0) {
    Write-Host ""
    Write-Host "[RESULT] Suite mostly complete - consider fixing WARN items" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host ""
    Write-Host "[RESULT] Suite complete - ready for release" -ForegroundColor Green
    exit 0
}