<#
.SYNOPSIS
Runs one JobG hybrid retrieval query with an isolated Ollama server session.

.DESCRIPTION
The script verifies port 11434 before startup, stops pre-existing Ollama-related
processes when safe, starts Ollama for one query, and cleans up Ollama-related
processes plus the Ollama listener even when their PIDs differ. It never kills
a non-Ollama process that happens to own port 11434.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string] $Query,

    [ValidateSet('All', 'Director', 'Architect', 'TPM')]
    [string] $Persona = 'All',

    [switch] $KeywordsOnly
)

$ErrorActionPreference = 'Stop'
$ownedServer = $null
$exitCode = 1

function Get-OllamaProcesses {
    @(Get-Process -Name 'ollama*' -ErrorAction SilentlyContinue)
}

function Get-OllamaPortListeners {
    # Parse netstat instead of querying the CIM-backed networking cmdlet. This
    # works in standard PowerShell and in restricted shells where CIM access is denied.
    $netstatPath = Join-Path $env:SystemRoot 'System32\netstat.exe'
    $lines = & $netstatPath -ano -p tcp
    if ($LASTEXITCODE -ne 0) {
        throw "netstat failed while checking port 11434 (exit code $LASTEXITCODE)."
    }

    $listeners = foreach ($line in $lines) {
        if ($line -match '^\s*TCP\s+(.+):11434\s+\S+\s+LISTENING\s+(\d+)\s*$') {
            [pscustomobject]@{
                LocalAddress = $Matches[1]
                LocalPort = 11434
                OwningProcess = [int] $Matches[2]
            }
        }
    }
    @($listeners)
}

function Test-OllamaPort {
    $listeners = @(Get-OllamaPortListeners)
    return ($listeners.Count -eq 0)
}

function Get-OllamaProcessIds {
    $ids = [System.Collections.Generic.HashSet[int]]::new()

    foreach ($process in (Get-OllamaProcesses)) {
        $null = $ids.Add([int] $process.Id)
    }

    foreach ($listener in (Get-OllamaPortListeners)) {
        $owner = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
        if ($owner -and $owner.ProcessName -like 'ollama*') {
            $null = $ids.Add([int] $owner.Id)
        }
        elseif ($owner) {
            throw "Port 11434 belongs to PID $($owner.Id) ($($owner.ProcessName)); refusing to terminate a non-Ollama process."
        }
        else {
            throw "Port 11434 is listening under PID $($listener.OwningProcess), but its owner could not be identified safely."
        }
    }

    return $ids
}

function Stop-OllamaProcesses {
    $ids = Get-OllamaProcessIds
    foreach ($processId in $ids) {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            try {
                Stop-Process -Id $processId -Force -ErrorAction Stop
            }
            catch {
                Write-Host "Stop attempt for Ollama PID $processId will be retried: $($_.Exception.Message)" -ForegroundColor DarkYellow
            }
        }
    }
}

function Wait-ForOllamaPortRelease {
    param(
        [int] $TimeoutSeconds = 10,
        [int] $QuietChecksRequired = 8
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $clearChecks = 0
    do {
        Stop-OllamaProcesses
        Start-Sleep -Milliseconds 250

        $remainingProcesses = @(Get-OllamaProcesses)
        $remainingListeners = @(Get-OllamaPortListeners)
        if ($remainingProcesses.Count -eq 0 -and $remainingListeners.Count -eq 0) {
            $clearChecks++
        }
        else {
            $clearChecks = 0
        }
    } while ($clearChecks -lt $QuietChecksRequired -and (Get-Date) -lt $deadline)

    return ($clearChecks -ge $QuietChecksRequired -and (Get-OllamaProcesses).Count -eq 0 -and (Test-OllamaPort))
}

try {
    if ($KeywordsOnly) {
        Write-Host 'Keyword-only mode selected; Ollama will not be started or stopped.' -ForegroundColor Yellow
    }
    else {
        # Establish exclusive ownership and verify the port is clear before startup.
        $preexistingProcesses = @(Get-OllamaProcesses)
        $preexistingListeners = @(Get-OllamaPortListeners)
        if ($preexistingProcesses.Count -gt 0 -or $preexistingListeners.Count -gt 0) {
            $pids = (Get-OllamaProcessIds | Sort-Object) -join ', '
            Write-Host "Stopping pre-existing Ollama process(es) to claim this session. PID(s): $pids" -ForegroundColor Yellow
            if (-not (Wait-ForOllamaPortRelease -TimeoutSeconds 10 -QuietChecksRequired 8)) {
                throw 'Could not get Ollama processes and port 11434 to remain stopped. Quit the Ollama tray app and retry.'
            }
        }

        if (-not (Test-OllamaPort)) {
            throw 'Port 11434 is not free; refusing to start a second server.'
        }

        $ollamaCommand = Get-Command ollama -ErrorAction Stop
        $ownedServer = Start-Process -FilePath $ollamaCommand.Source -ArgumentList 'serve' -PassThru -WindowStyle Hidden
        Write-Host "Started Ollama for this JobG session (PID $($ownedServer.Id)); waiting 4 seconds..." -ForegroundColor Green
        Start-Sleep -Seconds 4

        $ollamaTags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5
        $hasEmbeddingModel = @($ollamaTags.models | Where-Object {
            $_.name -eq 'nomic-embed-text' -or $_.name -eq 'nomic-embed-text:latest'
        }).Count -gt 0
        if (-not $hasEmbeddingModel) {
            throw "Ollama is responding, but nomic-embed-text is not installed. Run 'ollama pull nomic-embed-text' once, then retry."
        }
    }

    Write-Host "Running JobG retrieval for persona '$Persona'..." -ForegroundColor Cyan
    $python = (Get-Command python -ErrorAction Stop).Source
    $pythonArgs = @((Join-Path $PSScriptRoot 'rag_matcher.py'), $Query, '--persona', $Persona)
    if ($KeywordsOnly) {
        $pythonArgs += '--keywords-only'
    }
    & $python @pythonArgs
    $exitCode = $LASTEXITCODE
}
catch {
    Write-Host "SESSION ERROR: $($_.Exception.Message)" -ForegroundColor Red
    $exitCode = 1
}
finally {
    if ($ownedServer) {
        Write-Host 'Stopping all JobG-session Ollama processes and the port 11434 owner...' -ForegroundColor Yellow
        try {
            $clean = Wait-ForOllamaPortRelease -TimeoutSeconds 10 -QuietChecksRequired 8
            if ($clean -and (Test-OllamaPort)) {
                Write-Host '[✓] TEARDOWN SUCCESS: Port 11434 released & processes terminated cleanly.' -ForegroundColor Green
            }
            else {
                $remaining = @(Get-OllamaProcesses)
                $listeners = @(Get-OllamaPortListeners)
                $remainingIds = ($remaining | ForEach-Object { $_.Id }) -join ', '
                $listenerIds = ($listeners | ForEach-Object { $_.OwningProcess }) -join ', '
                Write-Host "[✗] TEARDOWN FAILED: Ollama PID(s) remain [$remainingIds]; port listener PID(s) [$listenerIds]." -ForegroundColor Red
                $exitCode = 1
            }
        }
        catch {
            Write-Host "[✗] TEARDOWN FAILED: $($_.Exception.Message)" -ForegroundColor Red
            $exitCode = 1
        }
    }
    elseif ($KeywordsOnly) {
        Write-Host 'No Ollama process was started or stopped by this keyword-only session.' -ForegroundColor DarkGray
    }
}

exit $exitCode
