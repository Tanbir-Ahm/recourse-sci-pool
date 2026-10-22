# Retries the 20 Gauhati High Court files that failed in the first run (the court's server closed the connection). One file every 5 seconds, then one zip: retry.zip.
# Run:  powershell -ExecutionPolicy Bypass -File .\retry_failed.ps1
$dest = Join-Path $env:USERPROFILE "Desktop\ghc_judgments_retry"
New-Item -ItemType Directory -Force $dest | Out-Null
$urls = @(
  "https://ghconline.gov.in/Judgment/CrlA58J2008.pdf",
  "https://ghconline.gov.in/Judgment/CrlRevP22014.pdf",
  "https://ghconline.gov.in/Judgment/CrlRP3942004.pdf",
  "https://ghconline.gov.in/Judgment/CrlRP6862004.pdf",
  "https://ghconline.gov.in/Judgment/CrlRP7512004.pdf",
  "https://ghconline.gov.in/Judgment/CrlA3J2006.pdf",
  "https://ghconline.gov.in/Judgment/CrlA79J2006.pdf",
  "https://ghconline.gov.in/Judgment/CrlRevPet1912013",
  "https://ghconline.gov.in/Judgment/CrlRevp48004.pdf",
  "https://ghconline.gov.in/Judgment/CrlA17J2005.pdf",
  "https://ghconline.gov.in/Judgment/CrlA43J2005.pdf",
  "https://ghconline.gov.in/Judgment/CrlPet1132013.pdf",
  "https://ghconline.gov.in/Judgment/CrlAppeal29203.pdf",
  "https://ghconline.gov.in/Judgment/CRLAJ282009.pdf",
  "https://ghconline.gov.in/Judgment/CrlPet642014.pdf",
  "https://ghconline.gov.in/Judgment/CrlAJ222009.pdf",
  "https://ghconline.gov.in/Judgment/CrlA38J2009.pdf",
  "https://ghconline.gov.in/Judgment/CrlA63J2009.pdf",
  "https://ghconline.gov.in/Judgment/CrlAppeal123J04.pdf",
  "https://ghconline.gov.in/Judgment/CRLAJ1102009.pdf"
)
foreach ($u in $urls) {
  $name = Split-Path $u -Leaf
  if ($name -notlike "*.pdf") { $name = $name + ".pdf" }
  $out = Join-Path $dest $name
  if (-not (Test-Path $out)) {
    try {
      Invoke-WebRequest -Uri $u -OutFile $out -UserAgent "Recourse-research/1.0 (low-rate)" -TimeoutSec 120
      Write-Host ("ok     " + $name)
    } catch { Write-Host ("FAILED " + $name + " : " + $_.Exception.Message) }
    Start-Sleep -Seconds 5
  }
}
$files = Get-ChildItem $dest -Filter *.pdf
Write-Host ("Downloaded files: " + $files.Count)
if ($files.Count -gt 0) { Compress-Archive -Path $files.FullName -DestinationPath (Join-Path $dest "retry.zip") -Force }
Write-Host ("Zip is in " + $dest)
