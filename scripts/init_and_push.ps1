param(
    [Parameter(Mandatory=$true)]
    [string]$RemoteUrl,
    [string]$UserName = "",
    [string]$UserEmail = "",
    [string]$Branch = "main"
)

$ErrorActionPreference = 'Stop'
$repoDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Write-Host "Working in: $repoDir"

# Check git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git not found in PATH. Please install Git (winget/choco or from https://git-scm.com/) and re-run this script."
    exit 2
}

if ($UserName -ne "") {
    git config --global user.name "$UserName"
}
if ($UserEmail -ne "") {
    git config --global user.email "$UserEmail"
}

Set-Location -Path $repoDir

# Initialize repo if needed
if (-not (Test-Path (Join-Path $repoDir ".git"))) {
    git init
    git checkout -b $Branch
} else {
    Write-Host "Repository already initialized."
}

# Add and commit
git add .
$diff = git status --porcelain
if ([string]::IsNullOrWhiteSpace($diff)) {
    Write-Host "No changes to commit."
} else {
    git commit -m "chore: import recovered workspace"
}

# Add remote if not present
$remotes = git remote
if (-not ($remotes -match "origin")) {
    git remote add origin $RemoteUrl
    Write-Host "Added remote origin: $RemoteUrl"
} else {
    Write-Host "Remote 'origin' already exists. To change it run: git remote set-url origin <url>"
}

# Push
try {
    git branch -M $Branch
    git push -u origin $Branch
    Write-Host "Pushed to origin/$Branch"
} catch {
    Write-Warning "Push failed: $_. Exception.Message"
    Write-Host "If this is a new remote, ensure you have permission and the remote exists. For GitHub with HTTPS you may be prompted for credentials or use a PAT."
}
