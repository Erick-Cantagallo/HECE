# ==========================================================
# HECE Project Report Generator
# Version: 1.1 (Fixed with Recursive Tree)
# ==========================================================

$ProjectRoot = Split-Path $PSScriptRoot -Parent
$ReportFolder = Join-Path $ProjectRoot "reports"

if (!(Test-Path $ReportFolder)) {
    New-Item -ItemType Directory -Path $ReportFolder | Out-Null
}

$Date = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$OutputFile = Join-Path $ReportFolder "project_report_$Date.txt"

$PythonVersion = python --version
$GitBranch = git branch --show-current
$LastCommit = git log -1 --pretty=%B

$PythonFiles = (Get-ChildItem $ProjectRoot -Recurse -Filter *.py |
Where-Object {$_.FullName -notmatch '[\\/]\.venv([\\/]|$)'}).Count

$MarkdownFiles = (Get-ChildItem $ProjectRoot -Recurse -Filter *.md |
Where-Object {$_.FullName -notmatch '[\\/]\.venv([\\/]|$)'}).Count

$TestFiles = (Get-ChildItem "$ProjectRoot/tests" -Recurse -Filter *.py -ErrorAction SilentlyContinue).Count

$TotalFiles = (Get-ChildItem $ProjectRoot -Recurse -File |
Where-Object {$_.FullName -notmatch '[\\/]\.venv([\\/]|$)'}).Count

@"
==========================================================
HECE PROJECT REPORT
==========================================================

Generated:
$(Get-Date)

Project:
HECE

Git Branch:
$GitBranch

Last Commit:
$LastCommit

Python:
$PythonVersion

----------------------------------------------------------

DIRECTORY STRUCTURE

"@ | Out-File $OutputFile

# ==========================================================
# FIX: Recursive Function for Real Tree (Ignoring .venv)
# ==========================================================
function Get-CustomTree {
    param (
        [string]$TargetFolder,
        [string]$Prefix = ""
    )

    # Get items from the current folder, ignoring .venv and __pycache__
    $items = Get-ChildItem -Path $TargetFolder -Force -ErrorAction SilentlyContinue | 
             Where-Object { $_.Name -notmatch '^\.venv$' -and $_.Name -notmatch '^__pycache__$' } |
             Sort-Object -Property @{Expression={$_.PSIsContainer}; Descending=$true}, Name

    $count = $items.Count
    for ($i = 0; $i -lt $count; $i++) {
        $item = $items[$i]
        $isLast = ($i -eq $count - 1)

        # Adjust the formatting depending on whether it is the last item in the directory
        if ($isLast) {
            $branch = "\-- "
            $newPrefix = $Prefix + "    "
        } else {
            $branch = "|-- "
            $newPrefix = $Prefix + "|   "
        }

        # Print the current item
        "$Prefix$branch$($item.Name)"

        # If it is a directory, call the function recursively
        if ($item.PSIsContainer) {
            Get-CustomTree -TargetFolder $item.FullName -Prefix $newPrefix
        }
    }
}

Write-Output "." | Out-File $OutputFile -Append
Get-CustomTree -TargetFolder $ProjectRoot | Out-File $OutputFile -Append
# ==========================================================

@"

----------------------------------------------------------

STATISTICS

Python Files : $PythonFiles

Markdown Files : $MarkdownFiles

Test Files : $TestFiles

Total Files : $TotalFiles

==========================================================

"@ | Out-File $OutputFile -Append

Write-Host ""
Write-Host "Report generated successfully!" -ForegroundColor Green
Write-Host $OutputFile -ForegroundColor Cyan