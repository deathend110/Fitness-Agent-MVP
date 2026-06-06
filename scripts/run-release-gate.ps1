$ErrorActionPreference = 'Stop'

Set-Location (Join-Path $PSScriptRoot '..')
uv run python scripts/release_gate.py run-all
exit $LASTEXITCODE
