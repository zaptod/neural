from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "pipeline_video" / "catalogacao_memes_template.xlsx"
MAX_ROWS = 10000


COLUMNS = [
    ("id_arquivo", 16),
    ("tipo_arquivo", 14),
    ("status_triagem", 16),
    ("nome_original", 28),
    ("caminho_relativo", 38),
    ("duracao_seg", 12),
    ("largura_px", 12),
    ("altura_px", 12),
    ("orientacao", 14),
    ("tem_audio", 12),
    ("fala_importante", 16),
    ("texto_na_tela", 16),
    ("watermark", 14),
    ("loop_limpo", 12),
    ("funcao_narrativa_1", 22),
    ("funcao_narrativa_2", 22),
    ("funcao_narrativa_3", 22),
    ("emocao_1", 18),
    ("emocao_2", 18),
    ("intensidade_1_5", 14),
    ("tom_1", 16),
    ("tom_2", 16),
    ("midia_base", 16),
    ("uso_principal", 20),
    ("uso_secundario", 20),
    ("categoria_roleta_1", 20),
    ("categoria_roleta_2", 20),
    ("observacoes", 42),
]


OPTIONS = {
    "tipo_arquivo": ["video", "foto"],
    "status_triagem": ["nao_revisado", "aprovado", "teste", "descartar"],
    "orientacao": ["vertical", "horizontal", "quadrado", "misto"],
    "tem_audio": ["sim", "nao"],
    "fala_importante": ["sim", "nao"],
    "texto_na_tela": ["sim", "nao"],
    "watermark": ["nenhuma", "leve", "forte"],
    "loop_limpo": ["sim", "nao"],
    "funcao_narrativa": [
        "god_roll",
        "high_roll",
        "mid_roll",
        "bad_roll",
        "troll_roll",
        "reveal",
        "power_up",
        "build_summary",
        "final_boss",
        "versus",
        "victory",
        "defeat",
        "transition",
    ],
    "emocao": [
        "hype",
        "choque",
        "caos",
        "deboche",
        "terror",
        "tristeza",
        "humilhacao",
        "confianca",
        "absurdo",
        "respeito",
        "raiva",
        "silencio",
    ],
    "intensidade": ["1", "2", "3", "4", "5"],
    "tom": ["epico", "engracado", "ironico", "sombrio", "absurdo", "dramatico", "seco"],
    "midia_base": ["anime", "meme", "facecam", "filme", "serie", "edit", "gameplay", "outro"],
    "uso": [
        "raca",
        "titulo",
        "reencarnacao",
        "qi",
        "forca",
        "velocidade",
        "combate",
        "poderes",
        "armas",
        "build",
        "versus",
        "vitoria",
        "derrota",
    ],
    "categoria_roleta": [
        "raca",
        "titulo",
        "reencarnacao",
        "qi",
        "forca",
        "velocidade",
        "combate",
        "poderes",
        "armas",
        "build",
        "versus",
    ],
}


def col_letter(index: int) -> str:
    result = []
    n = index
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result.append(chr(65 + rem))
    return "".join(reversed(result))


def inline_str_cell(ref: str, value: str, style: int | None = None) -> str:
    style_attr = f' s="{style}"' if style is not None else ""
    return (
        f'<c r="{ref}" t="inlineStr"{style_attr}>'
        f"<is><t>{escape(value)}</t></is>"
        f"</c>"
    )


def row_cells_xml(row_idx: int, values: list[str], *, style: int | None = None) -> str:
    cells = []
    for col_idx, value in enumerate(values, start=1):
        if value is None or value == "":
            continue
        cells.append(inline_str_cell(f"{col_letter(col_idx)}{row_idx}", str(value), style=style))
    return "".join(cells)


def build_content_types() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""


def build_root_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""


def build_workbook() -> str:
    defined_names = [
        ('tipo_arquivo', "Opcoes!$A$2:$A$3"),
        ('status_triagem', "Opcoes!$B$2:$B$5"),
        ('orientacao', "Opcoes!$C$2:$C$5"),
        ('sim_nao', "Opcoes!$D$2:$D$3"),
        ('watermark', "Opcoes!$E$2:$E$4"),
        ('funcao_narrativa', "Opcoes!$F$2:$F$14"),
        ('emocao', "Opcoes!$G$2:$G$13"),
        ('intensidade', "Opcoes!$H$2:$H$6"),
        ('tom', "Opcoes!$I$2:$I$8"),
        ('midia_base', "Opcoes!$J$2:$J$9"),
        ('uso', "Opcoes!$K$2:$K$14"),
        ('categoria_roleta', "Opcoes!$L$2:$L$12"),
    ]
    defined_xml = "".join(
        f'<definedName name="{name}">{ref}</definedName>' for name, ref in defined_names
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <bookViews>
    <workbookView xWindow="0" yWindow="0" windowWidth="24000" windowHeight="14000"/>
  </bookViews>
  <sheets>
    <sheet name="Catalogacao" sheetId="1" r:id="rId1"/>
    <sheet name="Opcoes" state="hidden" sheetId="2" r:id="rId2"/>
    <sheet name="Instrucoes" sheetId="3" r:id="rId3"/>
  </sheets>
  <definedNames>{defined_xml}</definedNames>
</workbook>"""


def build_workbook_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>
  <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def build_styles() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font>
      <sz val="11"/>
      <color theme="1"/>
      <name val="Calibri"/>
      <family val="2"/>
    </font>
    <font>
      <b/>
      <sz val="11"/>
      <color rgb="FFFFFFFF"/>
      <name val="Calibri"/>
      <family val="2"/>
    </font>
  </fonts>
  <fills count="3">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border>
      <left style="thin"><color rgb="FFD9E2F3"/></left>
      <right style="thin"><color rgb="FFD9E2F3"/></right>
      <top style="thin"><color rgb="FFD9E2F3"/></top>
      <bottom style="thin"><color rgb="FFD9E2F3"/></bottom>
      <diagonal/>
    </border>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="2">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
  </cellXfs>
  <cellStyles count="1">
    <cellStyle name="Normal" xfId="0" builtinId="0"/>
  </cellStyles>
</styleSheet>"""


def build_core() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dc:title>Catalogacao de Memes</dc:title>
  <dc:description>Planilha para classificar videos e fotos por contexto narrativo.</dc:description>
</cp:coreProperties>"""


def build_app() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Microsoft Excel</Application>
  <HeadingPairs>
    <vt:vector size="2" baseType="variant">
      <vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant>
      <vt:variant><vt:i4>3</vt:i4></vt:variant>
    </vt:vector>
  </HeadingPairs>
  <TitlesOfParts>
    <vt:vector size="3" baseType="lpstr">
      <vt:lpstr>Catalogacao</vt:lpstr>
      <vt:lpstr>Opcoes</vt:lpstr>
      <vt:lpstr>Instrucoes</vt:lpstr>
    </vt:vector>
  </TitlesOfParts>
</Properties>"""


def build_catalog_sheet(prefilled_rows: list[list[str]] | None = None) -> str:
    cols_xml = "".join(
        f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>'
        for idx, (_, width) in enumerate(COLUMNS, start=1)
    )
    rows_xml = [f'<row r="1" spans="1:{len(COLUMNS)}">{row_cells_xml(1, [name for name, _ in COLUMNS], style=1)}</row>']
    for row_idx, row_values in enumerate(prefilled_rows or [], start=2):
        rows_xml.append(f'<row r="{row_idx}" spans="1:{len(COLUMNS)}">{row_cells_xml(row_idx, row_values)}</row>')
    data_validations = [
        ('B2:B10000', "tipo_arquivo"),
        ('C2:C10000', "status_triagem"),
        ('I2:I10000', "orientacao"),
        ('J2:L10000', "sim_nao"),
        ('M2:M10000', "watermark"),
        ('N2:N10000', "sim_nao"),
        ('O2:Q10000', "funcao_narrativa"),
        ('R2:S10000', "emocao"),
        ('T2:T10000', "intensidade"),
        ('U2:V10000', "tom"),
        ('W2:W10000', "midia_base"),
        ('X2:Y10000', "uso"),
        ('Z2:AA10000', "categoria_roleta"),
    ]
    validations_xml = "".join(
        (
            f'<dataValidation type="list" allowBlank="1" showInputMessage="1" '
            f'showErrorMessage="1" errorStyle="stop" sqref="{sqref}">'
            f"<formula1>{name}</formula1>"
            f"</dataValidation>"
        )
        for sqref, name in data_validations
    )
    last_col = col_letter(len(COLUMNS))
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheetViews>
    <sheetView workbookViewId="0">
      <pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>
    </sheetView>
  </sheetViews>
  <sheetFormatPr defaultRowHeight="18"/>
  <cols>{cols_xml}</cols>
  <sheetData>{''.join(rows_xml)}</sheetData>
  <autoFilter ref="A1:{last_col}1"/>
  <dataValidations count="{len(data_validations)}">{validations_xml}</dataValidations>
  <pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>
</worksheet>"""


def build_options_sheet() -> str:
    groups = [
        ("tipo_arquivo", OPTIONS["tipo_arquivo"]),
        ("status_triagem", OPTIONS["status_triagem"]),
        ("orientacao", OPTIONS["orientacao"]),
        ("sim_nao", OPTIONS["tem_audio"]),
        ("watermark", OPTIONS["watermark"]),
        ("funcao_narrativa", OPTIONS["funcao_narrativa"]),
        ("emocao", OPTIONS["emocao"]),
        ("intensidade", OPTIONS["intensidade"]),
        ("tom", OPTIONS["tom"]),
        ("midia_base", OPTIONS["midia_base"]),
        ("uso", OPTIONS["uso"]),
        ("categoria_roleta", OPTIONS["categoria_roleta"]),
    ]
    rows = {}
    for col_idx, (header, values) in enumerate(groups, start=1):
        rows.setdefault(1, []).append(inline_str_cell(f"{col_letter(col_idx)}1", header, style=1))
        for row_idx, value in enumerate(values, start=2):
            rows.setdefault(row_idx, []).append(inline_str_cell(f"{col_letter(col_idx)}{row_idx}", value))
    row_xml = "".join(
        f'<row r="{row_idx}">{"".join(cells)}</row>'
        for row_idx, cells in sorted(rows.items())
    )
    cols_xml = "".join(
        f'<col min="{idx}" max="{idx}" width="22" customWidth="1"/>'
        for idx in range(1, len(groups) + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView workbookViewId="0"/></sheetViews>
  <sheetFormatPr defaultRowHeight="18"/>
  <cols>{cols_xml}</cols>
  <sheetData>{row_xml}</sheetData>
  <pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>
</worksheet>"""


def build_instructions_sheet() -> str:
    lines = [
        "Como usar",
        "1. Cada linha representa um arquivo do pack: video ou foto.",
        "2. Preencha nome_original e caminho_relativo primeiro.",
        "3. Nas colunas com dropdown, escolha apenas uma das opcoes da lista.",
        "4. Use funcao_narrativa_1/2/3 para dizer o papel do clipe na edicao.",
        "5. Use emocao_1/2 e intensidade_1_5 para descrever a energia do clipe.",
        "6. Uso_principal e categoria_roleta ajudam a pipeline a encaixar o clipe certo na hora certa.",
        "7. Observacoes serve para contexto livre, piadas internas ou restricoes.",
        "Sugestao de fluxo",
        "Triar primeiro: status_triagem, orientacao, audio, texto, watermark.",
        "Depois categorizar: funcao_narrativa, emocao, tom, uso e categoria_roleta.",
    ]
    rows = []
    for idx, line in enumerate(lines, start=1):
        style = 1 if idx in {1, 9} else None
        rows.append(f'<row r="{idx}">{inline_str_cell(f"A{idx}", line, style=style)}</row>')
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetFormatPr defaultRowHeight="20"/>
  <cols><col min="1" max="1" width="110" customWidth="1"/></cols>
  <sheetData>{''.join(rows)}</sheetData>
  <pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>
</worksheet>"""


def write_xlsx(output_path: Path, *, prefilled_rows: list[list[str]] | None = None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", build_content_types())
        zf.writestr("_rels/.rels", build_root_rels())
        zf.writestr("docProps/core.xml", build_core())
        zf.writestr("docProps/app.xml", build_app())
        zf.writestr("xl/workbook.xml", build_workbook())
        zf.writestr("xl/_rels/workbook.xml.rels", build_workbook_rels())
        zf.writestr("xl/styles.xml", build_styles())
        zf.writestr("xl/worksheets/sheet1.xml", build_catalog_sheet(prefilled_rows=prefilled_rows))
        zf.writestr("xl/worksheets/sheet2.xml", build_options_sheet())
        zf.writestr("xl/worksheets/sheet3.xml", build_instructions_sheet())


def main() -> None:
    write_xlsx(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
