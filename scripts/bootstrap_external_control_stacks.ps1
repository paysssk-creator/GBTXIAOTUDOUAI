param(
    [string]$Root = ""
)

$ErrorActionPreference = "Stop"

if (-not $Root) {
    $Root = Join-Path $PSScriptRoot "..\\third_party\\control_stacks"
}

$items = @(
    @{ Id = "openinterpreter"; Repo = "https://github.com/openinterpreter/openinterpreter"; Branch = "main"; Sha = "ac1b565c729e7a6192865e03301d81fa7c924025" },
    @{ Id = "omniparser"; Repo = "https://github.com/microsoft/OmniParser"; Branch = "master"; Sha = "b0d5c9f5701f7e2be4771872e6e928da77759df3" },
    @{ Id = "self_operating_computer"; Repo = "https://github.com/OthersideAI/self-operating-computer"; Branch = "main"; Sha = "fac568eea7da5e24f8bc91bfc1211b65679177eb" },
    @{ Id = "agent_s"; Repo = "https://github.com/simular-ai/Agent-S"; Branch = "main"; Sha = "73ea17225bae73ab45d077cc442978d3ff8e286a" },
    @{ Id = "ufo"; Repo = "https://github.com/microsoft/UFO"; Branch = "main"; Sha = "b28183fd426452c6cb511627c9bd32a929f29406" },
    @{ Id = "cradle"; Repo = "https://github.com/BAAI-Agents/Cradle"; Branch = "main"; Sha = "d7752fccf890d8d3818cd1d435f3705f604a1339" },
    @{ Id = "os_copilot"; Repo = "https://github.com/OS-Copilot/OS-Copilot"; Branch = "main"; Sha = "f720af8807e49a92dda64572d2c6bc6c0ac7ee7e" },
    @{ Id = "showui"; Repo = "https://github.com/showlab/ShowUI"; Branch = "main"; Sha = "21ed7cb24be0cc877bb8352ee34d58a9aea2c876" },
    @{ Id = "ui_tars_desktop"; Repo = "https://github.com/bytedance/UI-TARS-desktop"; Branch = "main"; Sha = "c2ad42e3eb9b27830db41a3e6f51ca7179d9b168" }
)

New-Item -ItemType Directory -Force -Path $Root | Out-Null

foreach ($item in $items) {
    $target = Join-Path $Root $item.Id
    Write-Host "==> " $item.Id -ForegroundColor Cyan

    if (-not (Test-Path $target)) {
        git clone --filter=blob:none --no-checkout $item.Repo $target
    }

    Push-Location $target
    try {
        git fetch origin $item.Sha --depth 1
        git checkout --force $item.Sha
        git clean -fd
    }
    finally {
        Pop-Location
    }
}

Write-Host "OK: external control stack snapshots prepared at $Root" -ForegroundColor Green
