# Convenience only: direct Docker Compose commands are documented in README.
param(
    [Parameter(Position=0)][ValidateSet('up','update','logs','status','down')][string]$Action='up',
    [Parameter(Position=1)][ValidateSet('front','back','postgres','llm_worker','export_worker','mailpit')][string]$Component,
    [string]$Project,
    [string]$EnvFile,
    [switch]$Production,
    [switch]$Pull
)
$arguments = @((Join-Path $PSScriptRoot 'stack.py'), $Action)
if ($Component) { $arguments += $Component }
if ($Project) { $arguments += @('--project', $Project) }
if ($EnvFile) { $arguments += @('--env-file', $EnvFile) }
if ($Production) { $arguments += '--production' }
if ($Pull) { $arguments += '--pull' }
& python @arguments
exit $LASTEXITCODE
