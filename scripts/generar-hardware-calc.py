#!/usr/bin/env python3
"""Genera c1/hardware-calc.xlsx — plantilla de dimensionament de maquinari.

Todas las salidas son FÓRMULAS de Excel reales (no valores precalculados):
el alumno hace clic en la celda y ve el cálculo. Se abre sin avisos en
Excel y en LibreOffice.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.protection import SheetProtection

# ---------------------------------------------------------------- disseny
ACCENT = "0F6E6A"          # verd-turquesa del curs
ACCENT_SOFT = "E3F0EF"
INPUT_BG = "FFF9E9"        # groc molt clar: "aquí escrius tu"
PAPER = "FFFFFF"
INK = "1A1A1A"
MUTED = "5C6B6A"
GREEN, AMBER, RED = "1E7A3C", "9A6700", "B01C1C"
GREEN_BG, AMBER_BG, RED_BG = "DFF3E4", "FFF1CC", "FBDDDD"

FONT = "Calibri"
PEU = "CIDET · IA en local · Classe 1"

thin = Side(style="thin", color="C9D6D5")
med = Side(style="medium", color=ACCENT)
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
INPUT_BOX = Border(
    left=Side(style="thin", color=ACCENT),
    right=Side(style="thin", color=ACCENT),
    top=Side(style="thin", color=ACCENT),
    bottom=Side(style="thin", color=ACCENT),
)


def h1(ws, cell: str, text: str) -> None:
    ws[cell] = text
    ws[cell].font = Font(name=FONT, size=16, bold=True, color=ACCENT)


def h2(ws, cell: str, text: str) -> None:
    ws[cell] = text
    ws[cell].font = Font(name=FONT, size=11, bold=True, color=PAPER)
    ws[cell].fill = PatternFill("solid", fgColor=ACCENT)
    ws[cell].alignment = Alignment(vertical="center")
    ws[cell].border = BOX


def note(ws, cell: str, text: str) -> None:
    ws[cell] = text
    ws[cell].font = Font(name=FONT, size=9, italic=True, color=MUTED)


def label(ws, cell: str, text: str) -> None:
    ws[cell] = text
    ws[cell].font = Font(name=FONT, size=11, color=INK)
    ws[cell].alignment = Alignment(vertical="center")


def input_cell(ws, cell: str, value=None, numfmt: str | None = None) -> None:
    c = ws[cell]
    if value is not None:
        c.value = value
    c.fill = PatternFill("solid", fgColor=INPUT_BG)
    c.border = INPUT_BOX
    c.font = Font(name=FONT, size=11, bold=True, color=INK)
    c.alignment = Alignment(horizontal="center", vertical="center")
    c.protection = __import__("openpyxl").styles.Protection(locked=False)
    if numfmt:
        c.number_format = numfmt


def out_cell(ws, cell: str, formula: str, numfmt: str = "0.00") -> None:
    c = ws[cell]
    c.value = formula
    c.number_format = numfmt
    c.font = Font(name=FONT, size=11, color=INK)
    c.border = BOX
    c.alignment = Alignment(horizontal="center", vertical="center")
    c.fill = PatternFill("solid", fgColor=ACCENT_SOFT)


def footer(ws, row: int, col: str = "A") -> None:
    ws[f"{col}{row}"] = PEU
    ws[f"{col}{row}"].font = Font(name=FONT, size=9, color=MUTED)


def widths(ws, mapping: dict[str, int]) -> None:
    for col, w in mapping.items():
        ws.column_dimensions[col].width = w


wb = Workbook()

# =============================================================================
# HOJA 1 — Dimensionament
# =============================================================================
ws = wb.active
ws.title = "Dimensionament"
ws.sheet_view.showGridLines = False
ws.sheet_properties.tabColor = ACCENT
widths(ws, {"A": 3, "B": 30, "C": 20, "D": 4, "E": 30, "F": 18, "G": 3, "H": 46})

h1(ws, "B2", "Dimensionament de maquinari per a LLM en local")
note(ws, "B3", "Omple només les caselles grogues. La resta són fórmules: fes-hi clic per veure-les.")

# ---- entrades
h2(ws, "B5", "ENTRADES")
ws.merge_cells("B5:C5")

entrades = [
    (6, "Nom del client", "Ferreteria Puig SL", None),
    (7, "Model candidat", "Qwen3 14B", None),
    (8, "Paràmetres (B)", 14, "0.0"),
    (9, "Quantització", "Q4", None),
    (10, "Context (tokens)", 8192, "#,##0"),
    (11, "KV cache quantitzada", "No", None),
    (12, "Usuaris simultanis", 1, "0"),
    (13, "GPU triada", "RTX 5070", None),
]
for row, name, value, fmt in entrades:
    label(ws, f"B{row}", name)
    input_cell(ws, f"C{row}", value, fmt)

# validaciones
dv_quant = DataValidation(
    type="list", formula1="Referencia!$B$5:$B$9", allow_blank=False,
    showErrorMessage=True, errorTitle="Quantització no vàlida",
    error="Tria un valor de la llista: FP16, Q8, Q6, Q4 o Q3.",
)
dv_ctx = DataValidation(
    type="list", formula1='"2048,4096,8192,16384,32768,65536,131072"',
    allow_blank=False, showErrorMessage=True, errorTitle="Context no vàlid",
    error="Tria una de les mides de context de la llista.",
)
dv_kv = DataValidation(
    type="list", formula1='"No,Q8"', allow_blank=False, showErrorMessage=True,
    errorTitle="Valor no vàlid", error="Només 'No' o 'Q8'.",
)
dv_gpu = DataValidation(
    type="list", formula1="GPUs!$B$5:$B$14", allow_blank=False,
    showErrorMessage=True, errorTitle="GPU no vàlida",
    error="Tria una GPU de la pestanya GPUs.",
)
dv_par = DataValidation(
    type="decimal", operator="greaterThan", formula1="0", showErrorMessage=True,
    errorTitle="Paràmetres", error="Els paràmetres han de ser un número més gran que 0.",
)
dv_usr = DataValidation(
    type="whole", operator="greaterThanOrEqual", formula1="1", showErrorMessage=True,
    errorTitle="Usuaris", error="Com a mínim 1 usuari simultani.",
)
for dv, ref in (
    (dv_par, "C8"), (dv_quant, "C9"), (dv_ctx, "C10"),
    (dv_kv, "C11"), (dv_usr, "C12"), (dv_gpu, "C13"),
):
    ws.add_data_validation(dv)
    dv.add(ref)

note(ws, "B15", "Q4_K_M és el punt dolç: ~4x menys memòria que FP16 amb pèrdua de qualitat mínima.")

# ---- salidas
h2(ws, "E5", "RESULTATS")
ws.merge_cells("E5:F5")

BPP = "VLOOKUP($C$9,Referencia!$B$5:$D$9,3,FALSE)"
GPU_VRAM = "VLOOKUP($C$13,GPUs!$B$5:$H$14,2,FALSE)"
GPU_BW = "VLOOKUP($C$13,GPUs!$B$5:$H$14,3,FALSE)"

label(ws, "E6", "Bytes per paràmetre")
out_cell(ws, "F6", f"={BPP}", "0.00")

label(ws, "E7", "VRAM pesos (GB)")
out_cell(ws, "F7", f"=$C$8*{BPP}*1.1")

label(ws, "E8", "VRAM context (GB)")
out_cell(ws, "F8", '=$C$10/1000*0.15*$C$12*IF($C$11="Q8",0.5,1)')

label(ws, "E9", "VRAM total (GB)")
ws["E9"].font = Font(name=FONT, size=11, bold=True, color=INK)
out_cell(ws, "F9", "=$F$7+$F$8")
ws["F9"].font = Font(name=FONT, size=12, bold=True, color=ACCENT)

label(ws, "E10", "VRAM de la GPU (GB)")
out_cell(ws, "F10", f"={GPU_VRAM}", "0")

label(ws, "E11", "Marge (GB)")
out_cell(ws, "F11", "=$F$10-$F$9")

label(ws, "E12", "Hi cap?")
ws["E12"].font = Font(name=FONT, size=11, bold=True, color=INK)
out_cell(
    ws, "F12",
    '=IF($F$11<0,"✘ No",IF($F$11>1.5,"✔ Sí","⚠ Just"))',
    "General",
)
ws["F12"].font = Font(name=FONT, size=12, bold=True)

label(ws, "E14", "Amplada de banda (GB/s)")
out_cell(ws, "F14", f"={GPU_BW}", "#,##0")

label(ws, "E15", "t/s teòrics")
out_cell(ws, "F15", f"=IF($F$7=0,0,{GPU_BW}/$F$7)", "0.0")

label(ws, "E16", "t/s esperats a la pràctica")
ws["E16"].font = Font(name=FONT, size=11, bold=True, color=INK)
out_cell(ws, "F16", "=$F$15*0.7", "0.0")
ws["F16"].font = Font(name=FONT, size=12, bold=True, color=ACCENT)
note(ws, "E17", "El rendiment real sol quedar entre el 60 % i el 80 % del teòric.")

# formato condicional sobre "Hi cap?"
ws.conditional_formatting.add(
    "F12",
    CellIsRule(operator="equal", formula=['"✔ Sí"'],
               fill=PatternFill("solid", start_color=GREEN_BG, end_color=GREEN_BG),
               font=Font(name=FONT, size=12, bold=True, color=GREEN)),
)
ws.conditional_formatting.add(
    "F12",
    CellIsRule(operator="equal", formula=['"⚠ Just"'],
               fill=PatternFill("solid", start_color=AMBER_BG, end_color=AMBER_BG),
               font=Font(name=FONT, size=12, bold=True, color=AMBER)),
)
ws.conditional_formatting.add(
    "F12",
    CellIsRule(operator="equal", formula=['"✘ No"'],
               fill=PatternFill("solid", start_color=RED_BG, end_color=RED_BG),
               font=Font(name=FONT, size=12, bold=True, color=RED)),
)
# marge: verd si > 1,5 / ambre si 0..1,5 / vermell si < 0
ws.conditional_formatting.add(
    "F11", CellIsRule(operator="lessThan", formula=["0"],
                      fill=PatternFill("solid", start_color=RED_BG, end_color=RED_BG),
                      font=Font(name=FONT, color=RED, bold=True)))
ws.conditional_formatting.add(
    "F11", CellIsRule(operator="between", formula=["0", "1.5"],
                      fill=PatternFill("solid", start_color=AMBER_BG, end_color=AMBER_BG),
                      font=Font(name=FONT, color=AMBER, bold=True)))
ws.conditional_formatting.add(
    "F11", CellIsRule(operator="greaterThan", formula=["1.5"],
                      fill=PatternFill("solid", start_color=GREEN_BG, end_color=GREEN_BG),
                      font=Font(name=FONT, color=GREEN, bold=True)))

# ---- veredicte
h2(ws, "H5", "VEREDICTE")
veredicte = (
    '=IF($F$11<0,'
    '"✘ NO hi cap. Falten "&TEXT(-$F$11,"0.0")&" GB. Opcions: (1) baixa a una quantització '
    'més agressiva, (2) tria un model més petit, (3) fes offload a CPU —perdràs molta '
    'velocitat—, o (4) canvia de GPU.",'
    'IF($F$11<=1.5,'
    '"⚠ Hi cap JUST ("&TEXT($F$11,"0.0")&" GB de marge). Funcionarà, però sense recorregut: '
    'baixa el context o quantitza la KV cache a Q8 abans de posar-ho en producció. '
    'Amb "&$C$12&" usuari(s) el marge es menja de pressa.",'
    '"✔ Hi cap bé ("&TEXT($F$11,"0.0")&" GB de marge). Espera uns "&TEXT($F$16,"0")&" tokens/s. '
    'Encara tens marge per pujar el context o servir més usuaris en paral·lel."))'
)
ws["H6"] = veredicte
ws["H6"].font = Font(name=FONT, size=11, color=INK)
ws["H6"].alignment = Alignment(wrap_text=True, vertical="top")
ws["H6"].border = BOX
ws["H6"].fill = PatternFill("solid", fgColor=ACCENT_SOFT)
ws.merge_cells("H6:H16")
ws.row_dimensions[6].height = 15

h2(ws, "H18", "LES DUES FÓRMULES DEL CURS")
ws["H19"] = "VRAM_pesos ≈ paràmetres (B) × bytes/paràmetre × 1,1"
ws["H20"] = "tokens/s ≈ amplada de banda (GB/s) ÷ mida del model (GB)"
for r in (19, 20):
    ws[f"H{r}"].font = Font(name="Consolas", size=10, color=ACCENT, bold=True)

footer(ws, 22, "B")

ws.freeze_panes = "B5"
ws.protection = SheetProtection(sheet=False)   # hoja 1 editable

# =============================================================================
# HOJA 2 — GPUs
# =============================================================================
g = wb.create_sheet("GPUs")
g.sheet_view.showGridLines = False
widths(g, {"A": 3, "B": 18, "C": 12, "D": 20, "E": 16, "F": 8, "G": 18, "H": 20})

h1(g, "B2", "GPUs de referència")
note(g, "B3", "Comprova sempre l'amplada de banda de la variant concreta a techpowerup.com/gpu-specs")

heads = ["GPU", "VRAM (GB)", "Amplada banda (GB/s)", "Arquitectura", "Any",
         "Accelera FP8/FP4", "Preu orientatiu (€)"]
for i, hd in enumerate(heads):
    c = g.cell(row=4, column=2 + i, value=hd)
    c.font = Font(name=FONT, size=10, bold=True, color=PAPER)
    c.fill = PatternFill("solid", fgColor=ACCENT)
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    c.border = BOX
g.row_dimensions[4].height = 30

gpus = [
    ("RTX 3060", 12, 360, "Ampere", 2021, "No", 300),
    ("RTX 5070", 12, 672, "Blackwell", 2025, "Sí", 650),
    ("RTX 5060 Ti", 16, 448, "Blackwell", 2025, "Sí", 480),
    ("RTX 4090", 24, 1008, "Ada Lovelace", 2022, "No", 1900),
    ("RTX 5090", 32, 1792, "Blackwell", 2025, "Sí", 2400),
    ("L4", 24, 300, "Ada Lovelace", 2023, "No", 2600),
    ("A100 40GB", 40, 1555, "Ampere", 2020, "No", 9000),
    ("RTX 4060 Ti 16GB", 16, 288, "Ada Lovelace", 2023, "No", 480),
    ("RTX 3090", 24, 936, "Ampere", 2020, "No", 800),
    ("RTX 5080", 16, 960, "Blackwell", 2025, "Sí", 1200),
]
aula = {"RTX 3060", "RTX 5070", "RTX 5060 Ti"}
for r, row in enumerate(gpus, start=5):
    for i, v in enumerate(row):
        c = g.cell(row=r, column=2 + i, value=v)
        c.border = BOX
        c.font = Font(name=FONT, size=10, bold=row[0] in aula, color=INK)
        c.alignment = Alignment(horizontal="center" if i else "left", vertical="center")
        if i in (1, 2, 4, 6):
            c.number_format = "#,##0"
        if row[0] in aula:
            c.fill = PatternFill("solid", fgColor=ACCENT_SOFT)

note(g, "B16", "Files ombrejades = les tres GPU de l'aula.")
note(g, "B17", "Els preus són orientatius de mercat de segona mà / PVP 2026 i canvien cada mes: fes-los servir només per comparar ordres de magnitud.")
note(g, "B18", "Les Blackwell (50xx) accelen FP8/FP4 per maquinari; Ampere no. Això importa per a vLLM i models quantitzats en FP8.")
footer(g, 20, "B")
g.protection = SheetProtection(sheet=True, objects=True, scenarios=True,
                               formatCells=False, selectLockedCells=True,
                               selectUnlockedCells=True)

# =============================================================================
# HOJA 3 — Referencia   (sin acento en el nombre: evita líos en fórmulas)
# =============================================================================
r_ = wb.create_sheet("Referencia")
r_.sheet_view.showGridLines = False
widths(r_, {"A": 3, "B": 16, "C": 10, "D": 20, "E": 22, "F": 40})

h1(r_, "B2", "Referència: quantitzacions i fórmules")

heads = ["Quantització", "Bits", "Bytes/paràmetre", "Mida relativa", "Pèrdua de qualitat orientativa"]
for i, hd in enumerate(heads):
    c = r_.cell(row=4, column=2 + i, value=hd)
    c.font = Font(name=FONT, size=10, bold=True, color=PAPER)
    c.fill = PatternFill("solid", fgColor=ACCENT)
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    c.border = BOX
r_.row_dimensions[4].height = 30

quants = [
    ("FP16", 16, 2.0, "100 %", "Cap (referència)"),
    ("Q8", 8, 1.0, "50 %", "Pràcticament imperceptible"),
    ("Q6", 6, 0.75, "38 %", "Molt petita"),
    ("Q4", 4, 0.5, "25 %", "Petita — el punt dolç (Q4_K_M)"),
    ("Q3", 3, 0.4, "20 %", "Notable: comença a fallar en raonament"),
]
for r, row in enumerate(quants, start=5):
    for i, v in enumerate(row):
        c = r_.cell(row=r, column=2 + i, value=v)
        c.border = BOX
        c.font = Font(name=FONT, size=10, bold=(row[0] == "Q4"), color=INK)
        c.alignment = Alignment(horizontal="center" if i in (1, 2, 3) else "left",
                                vertical="center")
        if i == 2:
            c.number_format = "0.00"
        if row[0] == "Q4":
            c.fill = PatternFill("solid", fgColor=ACCENT_SOFT)

r_["B11"] = "Q4_K_M és el punt dolç"
r_["B11"].font = Font(name=FONT, size=14, bold=True, color=ACCENT)
r_["B12"] = "Per al 95 % dels casos d'empresa, la resposta és RAG, no fine-tuning."
r_["B12"].font = Font(name=FONT, size=10, italic=True, color=MUTED)

h2(r_, "B14", "LES FÓRMULES DEL CURS")
r_.merge_cells("B14:F14")
r_["B16"] = "VRAM_pesos (GB) ≈ paràmetres (B) × bytes/paràmetre × 1,1"
r_["B18"] = "tokens/s ≈ amplada de banda (GB/s) ÷ mida del model (GB)"
r_["B20"] = "VRAM_context (GB) ≈ 0,1–0,2 GB per cada 1.000 tokens  (la meitat amb KV cache Q8)"
for row in (16, 18, 20):
    r_[f"B{row}"].font = Font(name="Consolas", size=13, bold=True, color=ACCENT)
    r_.merge_cells(f"B{row}:F{row}")

r_["B22"] = "Regles pràctiques"
r_["B22"].font = Font(name=FONT, size=11, bold=True, color=INK)
regles = [
    "· El 1,1 de la fórmula és el sobrecost real: activacions, buffers i fragmentació.",
    "· Per a assistents d'empresa, temperatura 0–0,3.",
    "· El català tokenitza pitjor que l'anglès: més context consumit i, per tant, més lent.",
    "· El rendiment real queda entre el 60 % i el 80 % del teòric.",
    "· Les Blackwell accelen FP8/FP4 per maquinari; Ampere no.",
]
for i, t in enumerate(regles, start=23):
    r_[f"B{i}"] = t
    r_[f"B{i}"].font = Font(name=FONT, size=10, color=INK)
    r_.merge_cells(f"B{i}:F{i}")

footer(r_, 30, "B")
r_.protection = SheetProtection(sheet=True, objects=True, scenarios=True,
                                selectLockedCells=True, selectUnlockedCells=True)

# =============================================================================
# HOJA 4 — Exemples
# =============================================================================
e = wb.create_sheet("Exemples")
e.sheet_view.showGridLines = False
widths(e, {"A": 3, "B": 26, "C": 9, "D": 9, "E": 11, "F": 12, "G": 11,
           "H": 13, "I": 15, "J": 14, "K": 14, "L": 15})

h1(e, "B2", "Exemples resolts — la matriu «hi cap?»")
note(e, "B3", "Reprodueix la diapositiva 24. Els números són fórmules: canvia'ls i mira què passa.")

heads = ["Model", "Par. (B)", "Quant.", "Context", "VRAM pesos",
         "VRAM ctx", "VRAM teòrica", "VRAM real (Ollama)",
         "RTX 3060 12GB", "RTX 5070 12GB", "RTX 5060 Ti 16GB"]
for i, hd in enumerate(heads):
    c = e.cell(row=5, column=2 + i, value=hd)
    c.font = Font(name=FONT, size=10, bold=True, color=PAPER)
    c.fill = PatternFill("solid", fgColor=ACCENT)
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    c.border = BOX
e.row_dimensions[5].height = 34

# La columna «VRAM real» és una MESURA, no una estimació: és el que marca
# `nvidia-smi` amb el model carregat a Ollama. La teòrica infraestima perquè
# Q4_K_M no són 0,5 bytes/paràmetre exactes (~0,6 de mitjana) i el runtime
# reserva búfers propis. Els veredictes es calculen sobre la mesura real.
exemples = [
    ("Qwen3 14B", 14, "Q4", 8192, 11.0),
    ("Gemma 4 26B-A4B", 26, "Q4", 8192, 15.5),
    ("Qwen3.6 27B", 27, "Q4", 8192, 18.2),
]
for idx, (nom, par, quant, ctx, real) in enumerate(exemples):
    r = 6 + idx
    e.cell(row=r, column=2, value=nom)
    e.cell(row=r, column=3, value=par).number_format = "0"
    e.cell(row=r, column=4, value=quant)
    e.cell(row=r, column=5, value=ctx).number_format = "#,##0"
    # fórmules reals, idèntiques a les del full 1
    e.cell(row=r, column=6,
           value=f"=C{r}*VLOOKUP(D{r},Referencia!$B$5:$D$9,3,FALSE)*1.1").number_format = "0.0"
    e.cell(row=r, column=7, value=f"=E{r}/1000*0.15*1").number_format = "0.0"
    e.cell(row=r, column=8, value=f"=F{r}+G{r}").number_format = "0.0"
    e.cell(row=r, column=9, value=real).number_format = "0.0"
    for col, vram in ((10, 12), (11, 12), (12, 16)):
        e.cell(row=r, column=col,
               value=f'=IF({vram}-$I{r}<0,"✘ No",IF({vram}-$I{r}>1.5,"✔ Sí","⚠ Just"))')
    for col in range(2, 13):
        c = e.cell(row=r, column=col)
        c.border = BOX
        c.alignment = Alignment(horizontal="center" if col > 2 else "left",
                                vertical="center")
        c.font = Font(name=FONT, size=10, color=INK)
    e.cell(row=r, column=9).font = Font(name=FONT, size=10, bold=True, color=ACCENT)

for col in ("J", "K", "L"):
    rng = f"{col}6:{col}8"
    e.conditional_formatting.add(rng, CellIsRule(
        operator="equal", formula=['"✔ Sí"'],
        fill=PatternFill("solid", start_color=GREEN_BG, end_color=GREEN_BG),
        font=Font(name=FONT, bold=True, color=GREEN)))
    e.conditional_formatting.add(rng, CellIsRule(
        operator="equal", formula=['"⚠ Just"'],
        fill=PatternFill("solid", start_color=AMBER_BG, end_color=AMBER_BG),
        font=Font(name=FONT, bold=True, color=AMBER)))
    e.conditional_formatting.add(rng, CellIsRule(
        operator="equal", formula=['"✘ No"'],
        fill=PatternFill("solid", start_color=RED_BG, end_color=RED_BG),
        font=Font(name=FONT, bold=True, color=RED)))

lectura = [
    "Com es llegeix això",
    "· Qwen3 14B Q4 amb 8k de context: la fórmula dóna ~8,9 GB, però mesurat a Ollama en surten ~11 GB.",
    "   Just a la 5070 (12 GB): arrenca, però sense marge. Còmode a la 5060 Ti (16 GB).",
    "· Gemma 4 26B-A4B Q4 → ~15,5 GB. Només a la 5060 Ti, i molt just.",
    "· Qwen3.6 27B Q4 → ~18 GB. A cap de les tres GPU de l'aula.",
    "",
    "Per què la teòrica i la real no coincideixen?",
    "· Q4_K_M no són 0,5 bytes/paràmetre exactes: barreja blocs de 4, 5 i 6 bits i surt a ~0,6 de mitjana.",
    "· El runtime (Ollama/llama.cpp) reserva els seus propis búfers de càlcul, a banda de pesos i KV cache.",
    "· La fórmula del curs és per DIMENSIONAR de pressa, no per predir al decigram.",
    "   Regla de butxaca: si el marge teòric és < 2 GB, considera-ho «just» i mesura-ho abans de prometre res.",
    "",
    "Conclusió del curs: amb 12–16 GB, la franja útil és 7B–14B en Q4.",
    "Per a més, o compres més VRAM, o acceptes offload a CPU i la lentitud que comporta.",
]
for i, t in enumerate(lectura, start=10):
    e[f"B{i}"] = t
    bold = t.startswith(("Conclusió", "Com es llegeix", "Per què"))
    e[f"B{i}"].font = Font(name=FONT, size=10, bold=bold,
                           color=ACCENT if bold else INK)
    e.merge_cells(f"B{i}:L{i}")

footer(e, 26, "B")
e.protection = SheetProtection(sheet=True, objects=True, scenarios=True,
                               selectLockedCells=True, selectUnlockedCells=True)

out = Path("/home/miquelonis/projects/mindora/cidet-ia-local/c1/hardware-calc.xlsx")
out.parent.mkdir(parents=True, exist_ok=True)
wb.save(out)
print(f"escrit: {out}  ({out.stat().st_size} bytes)")
