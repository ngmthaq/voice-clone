<#
.SYNOPSIS
Installs the app if needed, downloads the models, measures the speed of this
computer the first time, and starts the app.

.DESCRIPTION
The script takes no options. Steps that are already done are skipped. First it
checks for Python 3.12, git, ffmpeg and VB-CABLE. If something is missing, it
asks one question and installs it with winget.
#>
$ErrorActionPreference = 'Stop'

function Show-Usage {
    Write-Host 'Usage: scripts\run.ps1'
    Write-Host ''
    Write-Host 'Installs the app if needed, downloads the models, measures the speed of this'
    Write-Host 'computer the first time, and starts the app. It takes no options. Steps that'
    Write-Host 'are already done are skipped. If Python 3.12, git, ffmpeg or VB-CABLE is missing,'
    Write-Host 'it asks one question and installs it with winget.'
}

if ($args.Count -gt 0) {
    if ($args[0] -in @('-h', '--help', '-help', '/?')) {
        Show-Usage
        exit 0
    }
    Write-Host "Unknown argument: $($args[0])" -ForegroundColor Red
    Show-Usage
    exit 2
}

function Stop-Run([string]$Message) {
    throw $Message
}

function Assert-Success([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        Stop-Run "$Step failed (exit code $LASTEXITCODE)."
    }
}

function Write-Warn([string]$Message) {
    Write-Host $Message -ForegroundColor Yellow
}

function Write-Ok([string]$Message, [switch]$NoIndent) {
    $indent = if ($NoIndent) { '' } else { '  ' }
    Write-Host "$indent[OK] $Message" -ForegroundColor Green
}

function Write-Missing([string]$Message) {
    Write-Host "  [X] $Message" -ForegroundColor Red
}

function Write-Fail([string]$Message) {
    Write-Missing $Message
}

function Find-Python312 {
    $candidates = @(
        @{ Command = 'py'; Arguments = @('-3.12') },
        @{ Command = 'python3.12'; Arguments = @() }
    )
    foreach ($candidate in $candidates) {
        try {
            $prefix = $candidate.Arguments
            $path = & $candidate.Command @prefix -c 'import sys; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and $path) {
                return ([string]$path).Trim()
            }
        } catch {
            continue
        }
    }
    return $null
}

function Get-VenvVersion([string]$PythonPath) {
    if (-not (Test-Path -LiteralPath $PythonPath)) {
        return $null
    }
    try {
        $version = & $PythonPath -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>$null
        if ($LASTEXITCODE -eq 0 -and $version) {
            return ([string]$version).Trim()
        }
    } catch {
        return $null
    }
    return $null
}

function Test-NvidiaCard {
    try {
        & nvidia-smi 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Test-Git {
    try {
        & git --version 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Test-Ffmpeg {
    return [bool](Get-Command ffmpeg -ErrorAction SilentlyContinue)
}

function Test-VbCable {
    try {
        $cable = Get-CimInstance Win32_SoundDevice | Where-Object { $_.Name -like '*CABLE*' }
        return [bool]$cable
    } catch {
        return $false
    }
}

$script:prerequisites = @('python', 'git', 'ffmpeg', 'vbcable')

function Test-Prerequisite([string]$Item) {
    switch ($Item) {
        'python' { return [bool](Find-Python312) }
        'git' { return (Test-Git) }
        'ffmpeg' { return (Test-Ffmpeg) }
        'vbcable' { return (Test-VbCable) }
    }
}

function Get-MissingPrerequisites {
    return @($script:prerequisites | Where-Object { -not (Test-Prerequisite $_) })
}

function Get-PrerequisiteName([string]$Item) {
    switch ($Item) {
        'python' { return 'Python 3.12' }
        'vbcable' { return 'VB-CABLE' }
        default { return $Item }
    }
}

function Read-YesNo {
    if ([Console]::IsInputRedirected) {
        Write-Host 'There is no terminal to answer, so the answer is Yes.'
        return $true
    }
    while ($true) {
        $answer = (Read-Host 'Some things are missing. Install them now? [Y/n]').Trim().ToLower()
        if ($answer -in @('', 'y', 'yes')) { return $true }
        if ($answer -in @('n', 'no')) { return $false }
    }
}

function Update-SessionPath {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = $machine + ';' + $user
}

function Install-WingetPackage([string]$Id) {
    try {
        & winget install --id $Id -e --silent --accept-source-agreements --accept-package-agreements | Out-Host
        $ok = ($LASTEXITCODE -eq 0)
    } catch {
        $ok = $false
    }
    Update-SessionPath
    return $ok
}

$script:vbCableInstalled = $false

function Install-VbCable {
    $folder = Join-Path $env:TEMP ('vbcable-' + [guid]::NewGuid())
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $ProgressPreference = 'SilentlyContinue'
        New-Item -ItemType Directory -Path $folder | Out-Null
        $zip = Join-Path $folder 'vbcable.zip'
        Invoke-WebRequest 'https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack46.zip' -OutFile $zip -UseBasicParsing
        Expand-Archive -LiteralPath $zip -DestinationPath $folder -Force
        $setups = @(Get-ChildItem -LiteralPath $folder -Recurse -Filter 'VBCABLE_Setup*.exe')
        if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') {
            $setup = $setups | Where-Object { $_.Name -like '*arm64*' } | Select-Object -First 1
        } elseif ([Environment]::Is64BitOperatingSystem) {
            $setup = $setups | Where-Object { $_.Name -ieq 'VBCABLE_Setup_x64.exe' } | Select-Object -First 1
        } else {
            $setup = $setups | Where-Object { $_.Name -ieq 'VBCABLE_Setup.exe' } | Select-Object -First 1
        }
        if (-not $setup) {
            throw 'The right setup file was not found in the download.'
        }
        Start-Process -FilePath $setup.FullName -Verb RunAs -Wait
        $script:vbCableInstalled = $true
    } catch {
        Write-Fail "VB-CABLE could not be installed ($($_.Exception.Message)). You can try later from: https://vb-audio.com/Cable/"
        try { Start-Process 'https://vb-audio.com/Cable/' } catch { $null = $_ }
    } finally {
        Remove-Item -LiteralPath $folder -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Install-Missing([string[]]$Missing) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Fail 'winget was not found. Get "App Installer" from the Microsoft Store, then run this script again.'
        return
    }
    $ids = @{ python = 'Python.Python.3.12'; git = 'Git.Git'; ffmpeg = 'Gyan.FFmpeg' }
    foreach ($item in $Missing) {
        $name = Get-PrerequisiteName $item
        if ($item -eq 'vbcable') {
            Write-Host "Installing $name (Windows will ask for permission)..."
            Install-VbCable
            if ($script:vbCableInstalled) {
                Write-Ok "$name installed"
                Write-Host "  Tip: if CABLE Input does not show up in your apps, restart Windows."
            }
            continue
        }
        Write-Host "Installing $name..."
        if (Install-WingetPackage $ids[$item]) {
            Write-Ok "$name installed"
        } elseif ($item -eq 'python') {
            Stop-Run "Python 3.12 could not be installed. You can try later with: winget install $($ids[$item])"
        } else {
            Write-Fail "$name could not be installed. You can try later with: winget install $($ids[$item])"
        }
    }
}

$script:reportedMissing = @()

function Install-Prerequisites {
    $missing = @(Get-MissingPrerequisites)
    if ($missing.Count -eq 0) {
        Write-Ok 'Everything voice-clone needs is ready.' -NoIndent
        return
    }
    Write-Host 'Checking what voice-clone needs...'
    foreach ($item in $script:prerequisites) {
        $name = Get-PrerequisiteName $item
        if ($missing -contains $item) {
            Write-Missing "$name is missing"
        } else {
            Write-Ok "$name is already installed"
        }
    }
    Write-Host ''
    if (Read-YesNo) {
        Write-Host ''
        Install-Missing $missing
    }
    $script:reportedMissing = @(Get-MissingPrerequisites)
    Write-Host ''
    if ($script:reportedMissing.Count -eq 0) {
        Write-Ok 'Everything voice-clone needs is ready.' -NoIndent
    } else {
        $names = ($script:reportedMissing | ForEach-Object { Get-PrerequisiteName $_ }) -join ', '
        Write-Host "Still missing: $names. The app may not work fully until they are installed."
    }
}

$exitCode = 0
Push-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
try {
    Install-Prerequisites

    $python = Find-Python312
    if (-not $python) {
        Stop-Run 'Python 3.12 was not found. Install it from https://www.python.org/downloads/ and run this script again.'
    }

    $venvPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
    $stamp = Join-Path (Get-Location) '.venv\.voice-clone-install'

    if (Test-Path -LiteralPath '.venv') {
        $venvVersion = Get-VenvVersion $venvPython
        if ($venvVersion -ne '3.12') {
            $shown = if ($venvVersion) { $venvVersion } else { 'unknown' }
            Write-Host "The .venv folder was not made with Python 3.12 (found: $shown). Making it again."
            Remove-Item -LiteralPath '.venv' -Recurse -Force
        }
    }
    if (-not (Test-Path -LiteralPath '.venv')) {
        Write-Host 'Making .venv with Python 3.12.'
        & $python -m venv .venv
        Assert-Success 'Making the .venv'
    }

    $installed = $false
    $currentHash = (Get-FileHash -LiteralPath 'pyproject.toml' -Algorithm SHA256).Hash
    $stampText = "dev:$currentHash"
    $savedHash = $null
    if (Test-Path -LiteralPath $stamp) {
        $savedHash = (Get-Content -LiteralPath $stamp -Raw).Trim()
    }
    if ($savedHash -ne $stampText) {
        $installed = $true
        Write-Host 'Installing the app. This can take a few minutes.'
        & $venvPython -m pip install pip-system-certs
        if ($LASTEXITCODE -ne 0) {
            Stop-Run 'Could not install pip-system-certs. If you are behind a company proxy, check that HTTPS_PROXY is set and the company certificate is installed in the system.'
        }
        & $venvPython -m pip install --upgrade pip
        Assert-Success 'Upgrading pip'

        $useCuda = Test-NvidiaCard
        if ($useCuda) {
            Write-Host 'Installing the CUDA build of PyTorch (about 2.5 GB).'
            & $venvPython -m pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
            Assert-Success 'Installing PyTorch (CUDA)'
        }

        & $venvPython -m pip install -e '.[dev]'
        Assert-Success 'Installing the app'

        if ($useCuda) {
            $cudaAvailable = & $venvPython -c 'import torch; print(torch.cuda.is_available())'
            Assert-Success 'Checking CUDA'
            Write-Host "torch.cuda.is_available(): $cudaAvailable"
            if ($cudaAvailable -ne 'True') {
                Write-Warn 'Warning: PyTorch cannot use the NVIDIA card. Update the NVIDIA driver and check again.'
            }
        }

        Set-Content -LiteralPath $stamp -Value $stampText -Encoding ASCII
    }

    $hasGit = Test-Git

    & $venvPython -m voice_clone download-models
    if ($LASTEXITCODE -ne 0) {
        Write-Warn 'Warning: the base models were not downloaded. They will be tried again next time.'
    }

    if (-not $hasGit) {
        Write-Warn 'Warning: Applio was skipped because git is not installed. Install it with: winget install Git.Git'
    } else {
        & $venvPython -m voice_clone install-applio
        if ($LASTEXITCODE -ne 0) {
            Write-Warn 'Warning: Applio was not installed. It will be tried again next time.'
        }
    }

    $startApp = $true
    & $venvPython -m voice_clone measure-speed --if-needed
    if ($LASTEXITCODE -eq 130) {
        $startApp = $false
        $exitCode = 130
    } elseif ($LASTEXITCODE -ne 0) {
        Write-Host 'Speed test skipped, it will try again next time.'
    }

    if ($startApp) {
        if ($installed) {
            if (($script:reportedMissing -notcontains 'vbcable') -and -not $script:vbCableInstalled -and -not (Test-VbCable)) {
                Write-Fail 'VB-CABLE was not found. Install it from https://vb-audio.com/Cable/'
            }
            if (($script:reportedMissing -notcontains 'ffmpeg') -and -not (Test-Ffmpeg)) {
                Write-Fail 'ffmpeg is not installed. You need it to train a voice. Install it with: winget install Gyan.FFmpeg'
            }
            if (($script:reportedMissing -notcontains 'git') -and -not $hasGit) {
                Write-Fail 'git is not installed. You need it to train a voice. Install it with: winget install Git.Git'
            }
        }

        & $venvPython -m voice_clone run
        $exitCode = $LASTEXITCODE
    }
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    $exitCode = 1
} finally {
    Pop-Location
}
exit $exitCode
