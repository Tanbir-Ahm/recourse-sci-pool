# Downloads 20 Gauhati High Court judgments (also held by the open bucket) so that the two copies can be compared. Reads only; sends nothing from your computer.
$dest = Join-Path $env:USERPROFILE "Desktop\ghc_compare"
New-Item -ItemType Directory -Force $dest | Out-Null
$urls = @(
  "https://ghconline.gov.in/Judgment/WPC39242013.pdf",
  "https://ghconline.gov.in/Judgment/WPC6172014.pdf",
  "https://ghconline.gov.in/Judgment/WPC61842012.pdf",
  "https://ghconline.gov.in/Judgment/CRP892017.pdf",
  "https://ghconline.gov.in/Judgment/WPC30872010.pdf",
  "https://ghconline.gov.in/Judgment/RFA262012.pdf",
  "https://ghconline.gov.in/Judgment/WPC13992014.pdf",
  "https://ghconline.gov.in/Judgment/WPC59902013.pdf",
  "https://ghconline.gov.in/Judgment/WA2142008.pdf",
  "https://ghconline.gov.in/Judgment/WPC40102013.pdf",
  "https://ghconline.gov.in/Judgment/RSA702006.pdf",
  "https://ghconline.gov.in/Judgment/WPC24942011.pdf",
  "https://ghconline.gov.in/Judgment/CRLA1522014.pdf",
  "https://ghconline.gov.in/Judgment/WPC18322009.pdf",
  "https://ghconline.gov.in/Judgment/RSA172002.pdf",
  "https://ghconline.gov.in/Judgment/WPC8242016.pdf",
  "https://ghconline.gov.in/Judgment/WPC40822005.pdf",
  "https://ghconline.gov.in/Judgment/RFA892002.pdf",
  "https://ghconline.gov.in/Judgment/WPC45692010.pdf",
  "https://ghconline.gov.in/Judgment/WPC49722006.pdf"
)
foreach ($u in $urls) {
  $name = Split-Path $u -Leaf
  $out = Join-Path $dest $name
  if (-not (Test-Path $out)) {
    try { Invoke-WebRequest -Uri $u -OutFile $out -UserAgent "Recourse-research/1.0 (low-rate)" -TimeoutSec 90; Write-Host ("ok     " + $name) }
    catch { Write-Host ("FAILED " + $name + " : " + $_.Exception.Message) }
    Start-Sleep -Seconds 3
  }
}
$files = Get-ChildItem $dest -Filter *.pdf
Compress-Archive -Path $files.FullName -DestinationPath (Join-Path $dest "compare.zip") -Force
Write-Host ("Files: " + $files.Count + ", total MB: " + [math]::Round(($files | Measure-Object Length -Sum).Sum / 1MB, 1))
Write-Host ("Attach this file: " + (Join-Path $dest "compare.zip"))
