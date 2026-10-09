$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $root ".train-venv\Scripts\python.exe"
$runs = Join-Path $root "runs\detect"
Set-Location $root

# 清理残留占用GPU的python进程
Write-Host ">>> Check and clean leftover GPU python processes"
try{
    $gpuProcs = nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader
    if($gpuProcs){
        $gpuProcs | ForEach-Object {
            $parts = $_ -split ','
            $pid = $parts[0].Trim()
            if($pid -match '^\d+$'){
                Write-Host "Kill leftover PID: $pid"
                taskkill /F /PID $pid 2>&1 | Out-Null
            }
        }
    }
}
catch{
    Write-Warning "nvidia‑smi call failed, skip process cleanup"
}

$actionRun = Join-Path $runs "action_final_300"
New-Item -ItemType Directory -Force -Path $actionRun | Out-Null
Write-Host "===== Start training action_final_300 ====="
& $python detection\train_action.py `
    --data datasets\actions\action_data.yaml `
    --model ..\runs\detect\action300\weights\best.pt `
    --epochs 300 --batch 12 --imgsz 640 --device 0 --workers 0 --amp `
    --patience 80 --cache disk --compile False --name action_final_300 `
    > (Join-Path $actionRun "train.stdout.log") `
    2> (Join-Path $actionRun "train.stderr.log")
if ($LASTEXITCODE -ne 0) {
    Write-Error "Stage1 training failed, exitcode $LASTEXITCODE"
    exit $LASTEXITCODE
}

$personRun = Join-Path $runs "person_full_100"
New-Item -ItemType Directory -Force -Path $personRun | Out-Null
Write-Host "===== Start training person_full_100 ====="
& $python detection\train_action.py `
    --data datasets\person_full\person_data.yaml `
    --model ..\runs\detect\action_person_full_bg_100\weights\best.pt `
    --epochs 100 --batch 8 --imgsz 640 --device 0 --workers 0 --amp `
    --patience 30 --cache disk --compile False --name person_full_100 `
    > (Join-Path $personRun "train.stdout.log") `
    2> (Join-Path $personRun "train.stderr.log")

exit $LASTEXITCODE
