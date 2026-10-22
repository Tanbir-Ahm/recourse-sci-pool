# Downloads the Gauhati High Court judgments of 2010 named in the court's monthly lists (except the criminal ones you download with download_missing_criminal.ps1), from https://ghconline.gov.in/,
# into Desktop\ghc_judgments_2010 , one file every 3 seconds, then packs them into zip files of about 20 MB. It only downloads the files named below and saves them; it sends nothing from your computer.
# Test with 30 files:  powershell -ExecutionPolicy Bypass -File download_2010.ps1 -Limit 30      Everything:  ... -Limit 0      If it stops, run it again: files already downloaded are skipped.
param([int]$Limit = 30)
$dest = Join-Path $env:USERPROFILE "Desktop\ghc_judgments_2010"
New-Item -ItemType Directory -Force $dest | Out-Null
$urls = @(
  "https://ghconline.gov.in/Judgment/WPC662407.pdf",
  "https://ghconline.gov.in/Judgment/WPC83509.pdf",
  "https://ghconline.gov.in/Judgment/WA10508.pdf",
  "https://ghconline.gov.in/Judgment/WPC287609c.pdf",
  "https://ghconline.gov.in/Judgment/WPC29892010.pdf",
  "https://ghconline.gov.in/Judgment/WPC513309.pdf",
  "https://ghconline.gov.in/Judgment/MACAPP26005.pdf",
  "https://ghconline.gov.in/Judgment/WPC651602.pdf",
  "https://ghconline.gov.in/Judgment/WPC320110.pdf",
  "https://ghconline.gov.in/Judgment/WPC614706.pdf",
  "https://ghconline.gov.in/Judgment/RSA14000.pdf",
  "https://ghconline.gov.in/Judgment/RSA15300.pdf",
  "https://ghconline.gov.in/Judgment/MFA3601.pdf",
  "https://ghconline.gov.in/Judgment/ITA308.pdf",
  "https://ghconline.gov.in/Judgment/MFA6501.pdf",
  "https://ghconline.gov.in/Judgment/MACAPP4100.pdf",
  "https://ghconline.gov.in/Judgment/WPC163209.pdf",
  "https://ghconline.gov.in/Judgment/WA1282008.pdf",
  "https://ghconline.gov.in/Judgment/WPC467.pdf",
  "https://ghconline.gov.in/Judgment/RSA17200.pdf",
  "https://ghconline.gov.in/Judgment/RFA7501.pdf",
  "https://ghconline.gov.in/Judgment/CrlA809.pdf",
  "https://ghconline.gov.in/Judgment/WPC578809.pdf",
  "https://ghconline.gov.in/Judgment/CoApp82004.pdf",
  "https://ghconline.gov.in/Judgment/WPC605802.pdf",
  "https://ghconline.gov.in/Judgment/RSA10300.pdf",
  "https://ghconline.gov.in/Judgment/RSA14900.pdf",
  "https://ghconline.gov.in/Judgment/WA23907.pdf",
  "https://ghconline.gov.in/Judgment/SA15498.pdf",
  "https://ghconline.gov.in/Judgment/WA3292007.pdf",
  "https://ghconline.gov.in/Judgment/MACAPP12507.pdf",
  "https://ghconline.gov.in/Judgment/WPC225310.pdf",
  "https://ghconline.gov.in/Judgment/WPCAP1172010.pdf",
  "https://ghconline.gov.in/Judgment/WA2782010.pdf",
  "https://ghconline.gov.in/Judgment/RSA13400.pdf",
  "https://ghconline.gov.in/Judgment/RSA14610.pdf",
  "https://ghconline.gov.in/Judgment/WPCAP332010.pdf",
  "https://ghconline.gov.in/Judgment/WPCAP1542010.pdf",
  "https://ghconline.gov.in/Judgment/RSA19900.pdf"
)
$n = 0
foreach ($u in $urls) {
  if ($Limit -gt 0 -and $n -ge $Limit) { break }
  $name = Split-Path $u -Leaf
  $out = Join-Path $dest $name
  if (-not (Test-Path $out)) {
    try { Invoke-WebRequest -Uri $u -OutFile $out -UserAgent "Recourse-research/1.0 (low-rate)" -TimeoutSec 90; Write-Host ("ok     " + $name) }
    catch { Write-Host ("FAILED " + $name + " : " + $_.Exception.Message) }
    Start-Sleep -Seconds 3
  }
  $n++
}
$files = Get-ChildItem $dest -Filter *.pdf | Sort-Object Name
Write-Host ("Downloaded files: " + $files.Count + " of " + $urls.Count + ", total MB: " + [math]::Round(($files | Measure-Object Length -Sum).Sum / 1MB, 1))
$batch = @(); $size = 0; $part = 1
foreach ($f in $files) {
  $batch += $f.FullName; $size += $f.Length
  if ($size -gt 20MB) { Compress-Archive -Path $batch -DestinationPath (Join-Path $dest ("2010_part{0:D2}.zip" -f $part)) -Force; $part++; $batch = @(); $size = 0 }
}
if ($batch.Count -gt 0) { Compress-Archive -Path $batch -DestinationPath (Join-Path $dest ("2010_part{0:D2}.zip" -f $part)) -Force }
Write-Host ("Zip files are in " + $dest)
