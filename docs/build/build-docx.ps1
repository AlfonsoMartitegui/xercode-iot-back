param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DocsRoot = Resolve-Path (Join-Path $ScriptDir "..")
$SourcePath = Join-Path $DocsRoot "MEMORIA_TECNICA_BACKEND.md"
$BuildDir = Join-Path $DocsRoot "build"
$ExportsDir = Join-Path $DocsRoot "exports"
$GeneratedDir = Join-Path $DocsRoot "generated"
$DiagramsDir = Join-Path $GeneratedDir "diagrams"
$BuildMarkdown = Join-Path $BuildDir "build-unificado.md"
$ReportPath = Join-Path $BuildDir "reporte-build.md"
$OutputDocx = Join-Path $ExportsDir "MEMORIA_TECNICA_IOT-HUB-BACKEND.docx"
$ReferenceDocx = Join-Path $DocsRoot "reference.docx"

function Add-ReportLine {
    param([System.Collections.Generic.List[string]]$Lines, [string]$Line)
    $Lines.Add($Line) | Out-Null
}

function Convert-ToPandocPath {
    param([string]$Path)
    return $Path.Replace("\", "/")
}

$report = [System.Collections.Generic.List[string]]::new()
$startedAt = Get-Date

New-Item -ItemType Directory -Force $BuildDir, $ExportsDir, $GeneratedDir, $DiagramsDir | Out-Null

Add-ReportLine $report "# Reporte de build"
Add-ReportLine $report ""
Add-ReportLine $report "- Fecha: $($startedAt.ToString("yyyy-MM-dd HH:mm:ss"))"
Add-ReportLine $report "- Docs root: `"$DocsRoot`""
Add-ReportLine $report "- Fuente Markdown: `"$SourcePath`""
Add-ReportLine $report "- Markdown temporal: `"$BuildMarkdown`""
Add-ReportLine $report "- Directorio diagramas: `"$DiagramsDir`""
Add-ReportLine $report "- DOCX destino: `"$OutputDocx`""
Add-ReportLine $report ""

if (-not (Test-Path $SourcePath)) {
    Add-ReportLine $report "## Error"
    Add-ReportLine $report ""
    Add-ReportLine $report "No existe el Markdown fuente."
    Set-Content -LiteralPath $ReportPath -Value $report -Encoding UTF8
    throw "No existe el Markdown fuente: $SourcePath"
}

if ($Clean) {
    Get-ChildItem -LiteralPath $DiagramsDir -Include "*.svg","*.png" -File -ErrorAction SilentlyContinue | Remove-Item -Force
    Get-ChildItem -LiteralPath $BuildDir -Filter "diagram-*.mmd" -File -ErrorAction SilentlyContinue | Remove-Item -Force
    if (Test-Path $BuildMarkdown) {
        Remove-Item -LiteralPath $BuildMarkdown -Force
    }
}

$pandocCommand = Get-Command "pandoc" -ErrorAction SilentlyContinue
$mmdcCommand = Get-Command "mmdc" -ErrorAction SilentlyContinue
$rsvgCommand = Get-Command "rsvg-convert" -ErrorAction SilentlyContinue

Add-ReportLine $report "## Herramientas"
Add-ReportLine $report ""
if ($pandocCommand) {
    Add-ReportLine $report "- Pandoc: OK (`"$($pandocCommand.Source)`")"
} else {
    Add-ReportLine $report "- Pandoc: NO ENCONTRADO"
}

if ($mmdcCommand) {
    Add-ReportLine $report "- Mermaid CLI: OK (`"$($mmdcCommand.Source)`")"
} else {
    Add-ReportLine $report "- Mermaid CLI: NO ENCONTRADO"
    Add-ReportLine $report "- Instalar manualmente si se desea generar DOCX con diagramas renderizados:"
    Add-ReportLine $report ""
    Add-ReportLine $report '```powershell'
    Add-ReportLine $report "npm install -g @mermaid-js/mermaid-cli"
    Add-ReportLine $report '```'
}

if ($rsvgCommand) {
    Add-ReportLine $report "- rsvg-convert: OK (`"$($rsvgCommand.Source)`")"
    Add-ReportLine $report "- Imagenes para Pandoc: SVG"
} else {
    Add-ReportLine $report "- rsvg-convert: NO ENCONTRADO"
    Add-ReportLine $report "- Imagenes para Pandoc: PNG generado por Mermaid CLI como fallback; los SVG se siguen generando."
}
Add-ReportLine $report ""

$source = Get-Content -LiteralPath $SourcePath -Raw -Encoding UTF8
$pattern = '(?ms)^```mermaid\s*\r?\n(.*?)\r?\n```'
$regex = [System.Text.RegularExpressions.Regex]::new($pattern)
$matches = $regex.Matches($source)

Add-ReportLine $report "## Mermaid"
Add-ReportLine $report ""
Add-ReportLine $report "- Bloques Mermaid detectados: $($matches.Count)"
Add-ReportLine $report "- SVG generados antes de render: $((Get-ChildItem -LiteralPath $DiagramsDir -Filter "*.svg" -File -ErrorAction SilentlyContinue | Measure-Object).Count)"
Add-ReportLine $report "- PNG generados antes de render: $((Get-ChildItem -LiteralPath $DiagramsDir -Filter "*.png" -File -ErrorAction SilentlyContinue | Measure-Object).Count)"
Add-ReportLine $report ""

if (-not $pandocCommand) {
    Add-ReportLine $report "## Resultado"
    Add-ReportLine $report ""
    Add-ReportLine $report "- DOCX generado: False"
    Set-Content -LiteralPath $ReportPath -Value $report -Encoding UTF8
    throw "Pandoc no esta disponible en PATH."
}

if (-not $mmdcCommand -and $matches.Count -gt 0) {
    Add-ReportLine $report "## Resultado"
    Add-ReportLine $report ""
    Add-ReportLine $report "- DOCX generado: False"
    Add-ReportLine $report "- Motivo: Mermaid CLI no esta disponible."
    Set-Content -LiteralPath $ReportPath -Value $report -Encoding UTF8
    throw "Mermaid CLI (mmdc) no esta disponible en PATH. Instalar con: npm install -g @mermaid-js/mermaid-cli"
}

$renderErrors = [System.Collections.Generic.List[string]]::new()
$diagramIndex = 0

$buildContent = $regex.Replace($source, {
    param($match)

    $script:diagramIndex++
    $id = "{0:D3}" -f $script:diagramIndex
    $diagramSource = $match.Groups[1].Value.Trim()
    $mmdPath = Join-Path $BuildDir "diagram-$id.mmd"
    $svgPath = Join-Path $DiagramsDir "diagram-$id.svg"
    $pngPath = Join-Path $DiagramsDir "diagram-$id.png"

    Set-Content -LiteralPath $mmdPath -Value $diagramSource -Encoding UTF8

    try {
        & $mmdcCommand.Source -i $mmdPath -o $svgPath --backgroundColor transparent | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "mmdc SVG devolvio codigo $LASTEXITCODE"
        }
        Add-ReportLine $report "- Diagrama ${id}: SVG OK -> `"$svgPath`""

        if (-not $rsvgCommand) {
            & $mmdcCommand.Source -i $mmdPath -o $pngPath --backgroundColor white | Out-Null
            if ($LASTEXITCODE -ne 0) {
                throw "mmdc PNG fallback devolvio codigo $LASTEXITCODE"
            }
            Add-ReportLine $report "- Diagrama ${id}: PNG fallback OK -> `"$pngPath`""
        }
    } catch {
        $message = "Diagrama ${id}: ERROR -> $($_.Exception.Message)"
        $renderErrors.Add($message) | Out-Null
        Add-ReportLine $report "- $message"
    }

    if ($rsvgCommand) {
        $relativeImage = "../generated/diagrams/diagram-$id.svg"
    } else {
        $relativeImage = "../generated/diagrams/diagram-$id.png"
    }
    return "![Diagrama Mermaid $id]($relativeImage)"
})

Add-ReportLine $report ""
Add-ReportLine $report "- SVG generados: $((Get-ChildItem -LiteralPath $DiagramsDir -Filter "*.svg" -File -ErrorAction SilentlyContinue | Measure-Object).Count)"
Add-ReportLine $report "- PNG generados: $((Get-ChildItem -LiteralPath $DiagramsDir -Filter "*.png" -File -ErrorAction SilentlyContinue | Measure-Object).Count)"
Add-ReportLine $report "- Errores de render: $($renderErrors.Count)"
Add-ReportLine $report ""

Set-Content -LiteralPath $BuildMarkdown -Value $buildContent -Encoding UTF8

if ($renderErrors.Count -gt 0) {
    Add-ReportLine $report "## Resultado"
    Add-ReportLine $report ""
    Add-ReportLine $report "Build detenido por errores renderizando Mermaid."
    Set-Content -LiteralPath $ReportPath -Value $report -Encoding UTF8
    throw "Build detenido por errores renderizando Mermaid. Ver $ReportPath"
}

Add-ReportLine $report "## Pandoc"
Add-ReportLine $report ""

$pandocArgs = @(
    "build/build-unificado.md",
    "-o",
    "exports/MEMORIA_TECNICA_IOT-HUB-BACKEND.docx",
    "--toc",
    "--toc-depth=2",
    "--number-sections",
    "--resource-path=.;build;generated/diagrams;assets;assets/img;assets/diagramas"
)

if (Test-Path $ReferenceDocx) {
    $referenceArg = "--reference-doc=$((Convert-ToPandocPath $ReferenceDocx))"
    $pandocArgs += $referenceArg
    Add-ReportLine $report "- reference.docx: OK (`"$ReferenceDocx`")"
} else {
    Add-ReportLine $report "- reference.docx: no existe; se continua con estilo por defecto."
}

Add-ReportLine $report "- Comando: pandoc $($pandocArgs -join ' ')"

Push-Location $DocsRoot
try {
    $pandocOutput = & $pandocCommand.Source @pandocArgs 2>&1
    $pandocExit = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($pandocOutput) {
    Add-ReportLine $report ""
    Add-ReportLine $report "### Salida Pandoc"
    Add-ReportLine $report ""
    foreach ($line in $pandocOutput) {
        Add-ReportLine $report "- $line"
    }
}

if ($pandocExit -ne 0) {
    Add-ReportLine $report "- Pandoc: ERROR codigo $pandocExit"
    Add-ReportLine $report ""
    Add-ReportLine $report "## Resultado"
    Add-ReportLine $report ""
    Add-ReportLine $report "DOCX no generado."
    Set-Content -LiteralPath $ReportPath -Value $report -Encoding UTF8
    throw "Pandoc fallo con codigo $pandocExit"
}

$docxExists = Test-Path $OutputDocx
Add-ReportLine $report "- Pandoc: OK"
Add-ReportLine $report "- DOCX generado: $docxExists"

if ($docxExists) {
    $docxItem = Get-Item $OutputDocx
    Add-ReportLine $report "- DOCX ruta: `"$OutputDocx`""
    Add-ReportLine $report "- DOCX tamano bytes: $($docxItem.Length)"
}

Add-ReportLine $report ""
Add-ReportLine $report "## Artefactos"
Add-ReportLine $report ""
Add-ReportLine $report "- Markdown temporal: `"$BuildMarkdown`""
Add-ReportLine $report "- Diagramas SVG/PNG: `"$DiagramsDir`""
Add-ReportLine $report "- Export DOCX: `"$OutputDocx`""

Set-Content -LiteralPath $ReportPath -Value $report -Encoding UTF8

Write-Host "Build DOCX completado."
Write-Host "DOCX: $OutputDocx"
Write-Host "Reporte: $ReportPath"
