param([string]$Mode = "scan")
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Devices.Enumeration.DeviceInformation,Windows.Devices.Enumeration,ContentType=WindowsRuntime] | Out-Null
[Windows.Devices.Bluetooth.BluetoothDevice,Windows.Devices.Bluetooth,ContentType=WindowsRuntime] | Out-Null

function Await-Rt($op, $resultType) {
    $methods = [WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.IsGenericMethodDefinition -and $_.GetParameters().Count -eq 1
    }
    foreach ($m in $methods) {
        try {
            $gm = $m.MakeGenericMethod($resultType)
            $task = $gm.Invoke($null, @($op))
            $task.Wait(-1)
            return $task.Result
        } catch {}
    }
    throw "Cannot await async operation"
}

if ($Mode -eq "paired") {
    try {
        # Get all paired Bluetooth devices using the standard selector
        $sel = [Windows.Devices.Bluetooth.BluetoothDevice]::GetDeviceSelectorFromPairingState($true)
        $op = [Windows.Devices.Enumeration.DeviceInformation]::FindAllAsync($sel)
        $result = Await-Rt $op ([Windows.Devices.Enumeration.DeviceInformationCollection])
        $a = @()
        foreach ($d in $result) {
            $props = @{}
            try { $props.name = if ($d.Name) { $d.Name } else { $null } } catch { $props.name = $null }
            try { $props.id = $d.Id } catch { $props.id = $null }
            try { $props.isPaired = $d.Pairing.IsPaired } catch { $props.isPaired = $null }
            if ($props.name -or $props.id) {
                $a += $props
            }
        }
        ConvertTo-Json @{ok=$true; count=$a.Count; devices=$a} -Depth 2 -Compress
    } catch {
        ConvertTo-Json @{ok=$false; error=$_.Exception.Message} -Compress
    }
} else {
    try {
        # Get all Bluetooth devices (paired + unpaired)
        $sel = [Windows.Devices.Bluetooth.BluetoothDevice]::GetDeviceSelector()
        $op = [Windows.Devices.Enumeration.DeviceInformation]::FindAllAsync($sel)
        $result = Await-Rt $op ([Windows.Devices.Enumeration.DeviceInformationCollection])
        $a = @()
        foreach ($d in $result) {
            $props = @{}
            try { $props.name = if ($d.Name) { $d.Name } else { $null } } catch { $props.name = $null }
            try { $props.id = $d.Id } catch { $props.id = $null }
            try { 
                $props.paired = if ($d.Pairing.IsPaired) { "paired" } else { "unpaired" }
                $props.canPair = $d.Pairing.CanPair
            } catch {
                $props.paired = "unknown"
                $props.canPair = $false
            }
            if ($props.name -or $props.id) {
                $a += $props
            }
        }
        $sorted = $a | Sort-Object name
        ConvertTo-Json @{ok=$true; count=$a.Count; devices=@($sorted)} -Depth 3 -Compress
    } catch {
        ConvertTo-Json @{ok=$false; error=$_.Exception.Message} -Compress
    }
}
