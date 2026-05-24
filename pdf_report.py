"""Generate a professional PDF assessment report using reportlab."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable, KeepTogether)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io
from datetime import datetime

RISK_COLOURS = {
    "Low":      colors.HexColor("#2e7d32"),
    "Moderate": colors.HexColor("#f9a825"),
    "High":     colors.HexColor("#e65100"),
    "Critical": colors.HexColor("#b71c1c"),
}
RISK_BG = {
    "Low":      colors.HexColor("#e8f5e9"),
    "Moderate": colors.HexColor("#fff8e1"),
    "High":     colors.HexColor("#fff3e0"),
    "Critical": colors.HexColor("#ffebee"),
}
BLUE    = colors.HexColor("#1a237e")
LTBLUE  = colors.HexColor("#e8eaf6")
GREY    = colors.HexColor("#f5f5f5")
DKGREY  = colors.HexColor("#424242")


def build_pdf(result: dict, inputs: dict, site_meta: dict = None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=18*mm, rightMargin=18*mm,
                             topMargin=18*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    story = []

    def style(name, **kw):
        s = ParagraphStyle(name, parent=styles["Normal"], **kw)
        return s

    H1   = style("H1", fontSize=16, textColor=BLUE, spaceAfter=2, spaceBefore=6, leading=20, fontName="Helvetica-Bold")
    H2   = style("H2", fontSize=11, textColor=BLUE, spaceAfter=3, spaceBefore=8, leading=14, fontName="Helvetica-Bold")
    H3   = style("H3", fontSize=9.5, textColor=DKGREY, spaceAfter=2, spaceBefore=4, leading=13, fontName="Helvetica-Bold")
    BODY = style("BODY", fontSize=9, spaceAfter=2, leading=13, textColor=DKGREY)
    SMAL = style("SMAL", fontSize=8, spaceAfter=1, leading=11, textColor=colors.HexColor("#757575"))
    CENT = style("CENT", fontSize=9, alignment=TA_CENTER, leading=13)

    level = result["risk_level"]
    rc    = RISK_COLOURS[level]

    # ── Header ──────────────────────────────────────────────────────────────
    sm = site_meta or {}
    site_line = sm.get("site", "—")
    insp_line = sm.get("inspector", "—") or "—"
    date_line = sm.get("date", datetime.now().strftime("%d %b %Y"))

    header_data = [[
        Paragraph("<b>RCC CRACK RISK ASSESSMENT REPORT</b>", style("hd", fontSize=14, textColor=colors.white, fontName="Helvetica-Bold", leading=18)),
        Paragraph(
            f"Site: {site_line}<br/>Inspector: {insp_line}<br/>Date: {date_line}<br/>"
            f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}<br/>"
            f"Delhi Technological University · Dept. of Civil Engineering",
            style("hds", fontSize=7.5, textColor=colors.white, alignment=TA_RIGHT, leading=11)
        ),
    ]]
    ht = Table(header_data, colWidths=[110*mm, 64*mm])
    ht.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), BLUE),
        ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1), 10),
        ("RIGHTPADDING",(0,0),(-1,-1), 10),
        ("TOPPADDING",  (0,0),(-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
    ]))
    story.append(ht)
    story.append(Spacer(1, 5*mm))

    # ── IS Code subtitle ─────────────────────────────────────────────────────
    story.append(Paragraph(
        "IS 456:2000 · IS 13920:2016 · IS 1893:2016 · ACI 318-19",
        style("sub", fontSize=8, textColor=colors.HexColor("#5c6bc0"),
              alignment=TA_CENTER, spaceAfter=4)
    ))

    # ── Risk level banner ────────────────────────────────────────────────────
    banner = [[Paragraph(
        f"<b>RISK LEVEL: {level.upper()}</b>   &nbsp;&nbsp;  {result['urgency']}",
        style("bn", fontSize=12, textColor=colors.white, fontName="Helvetica-Bold",
              alignment=TA_CENTER, leading=16)
    )]]
    bt = Table(banner, colWidths=[174*mm])
    bt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), rc),
        ("TOPPADDING",(0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    story.append(bt)
    story.append(Spacer(1, 4*mm))

    # ── Risk indices ─────────────────────────────────────────────────────────
    story.append(Paragraph("Risk Indices", H2))

    def index_row(label, value, note, colour):
        pct = min(int(value * 100), 100)
        bar_w = int(pct * 1.40)  # max 140 pts wide in the bar column
        return [
            Paragraph(f"<b>{label}</b>", BODY),
            Paragraph(f"<b>{value:.3f}</b>", style("rv", fontSize=10, textColor=colour, fontName="Helvetica-Bold")),
            Paragraph(note, SMAL),
        ]

    idx_data = [
        ["Index", "Score", "Basis"],
        index_row("CRI — Crack Risk Index", result["cri"],
                  "Weighted sum of 6 variables (IS 456 + IS 13920 calibrated)", RISK_COLOURS.get(result["risk_level"], BLUE)),
        index_row("MRI — Member Risk Index", result["mri"],
                  f"CRI × {result['member_multiplier']} ({inputs.get('member_type')} multiplier, IS 13920:2016 · {inputs.get('seismic_zone','Zone IV')})",
                  RISK_COLOURS.get(result["risk_level"], BLUE)),
    ]
    it = Table(idx_data, colWidths=[55*mm, 25*mm, 94*mm])
    it.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), BLUE),
        ("TEXTCOLOR",     (0,0),(-1,0), colors.white),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[GREY, colors.white]),
        ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#e0e0e0")),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
    ]))
    story.append(it)
    story.append(Spacer(1, 4*mm))

    # ── CRI Variable Breakdown ────────────────────────────────────────────────
    story.append(Paragraph("CRI Variable Breakdown", H2))
    LABELS = {
        "width":       "Crack Width",
        "depth":       "Depth Ratio",
        "orientation": "Orientation",
        "distance":    "Distance from Support/Joint",
        "activity":    "Activity Over Time",
        "importance":  "Member Importance",
    }
    CODE_REFS = {
        "width":       "IS 456:2000 Cl. 35.3.2",
        "depth":       "ACI 318-19 §6.6.3.1 / Branson eq.",
        "orientation": "IS 456:2000 Cl. 40 · IS 13920:2016 Cl. 8.3.1",
        "distance":    "IS 456:2000 Cl. 40.5 · IS 13920:2016 Cl. 8",
        "activity":    "IS 456:2000 Cl. 19.2",
        "importance":  "IS 456:2000 Cl. 22",
    }
    WEIGHTS = result.get("weights", {})
    contrib = result.get("contributions", {})
    scores  = result.get("scores", {})

    var_data = [["Variable", "Wt.", "Score", "Contribution", "IS Code Reference"]]
    for k, label in LABELS.items():
        var_data.append([
            Paragraph(label, BODY),
            Paragraph(str(WEIGHTS.get(k,"")), CENT),
            Paragraph(f"{scores.get(k,0):.2f}", CENT),
            Paragraph(f"{contrib.get(k,0):.4f}", CENT),
            Paragraph(CODE_REFS[k], SMAL),
        ])
    var_data.append([
        Paragraph("<b>Total CRI</b>", style("tot", fontSize=9, fontName="Helvetica-Bold")),
        "", "", Paragraph(f"<b>{result['cri']:.4f}</b>",
                          style("totv", fontSize=9, fontName="Helvetica-Bold",
                                textColor=rc, alignment=TA_CENTER)), ""
    ])
    vt = Table(var_data, colWidths=[50*mm, 12*mm, 14*mm, 22*mm, 76*mm])
    vt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), BLUE),
        ("TEXTCOLOR",     (0,0),(-1,0), colors.white),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 8.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-2),[GREY, colors.white]),
        ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#e0e0e0")),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
        ("BACKGROUND",    (0,-1),(-1,-1), LTBLUE),
        ("SPAN",          (0,-1),(2,-1)),
        ("SPAN",          (4,-1),(4,-1)),
    ]))
    story.append(vt)
    story.append(Spacer(1, 4*mm))

    # ── IS Code Checks ────────────────────────────────────────────────────────
    story.append(Paragraph("IS Code Compliance Checks", H2))

    checks = []
    # Width check
    w_ok = inputs.get("width_mm", 0) <= result["permissible_width_mm"]
    checks.append([
        Paragraph("Crack Width — IS 456:2000 Cl. 35.3.2", H3),
        Paragraph("PASS" if w_ok else "FAIL",
                  style("chk", fontSize=9, fontName="Helvetica-Bold",
                        textColor=RISK_COLOURS["Low"] if w_ok else RISK_COLOURS["Critical"],
                        alignment=TA_CENTER)),
        Paragraph(result.get("width_status",""), SMAL),
    ])

    if result.get("shear_note"):
        checks.append([
            Paragraph("Shear Check — IS 456:2000 Table 20", H3),
            Paragraph("NOTE", style("chk2", fontSize=9, fontName="Helvetica-Bold",
                                    textColor=RISK_COLOURS["High"], alignment=TA_CENTER)),
            Paragraph(result["shear_note"], SMAL),
        ])

    if result.get("joint_shear_limit"):
        checks.append([
            Paragraph("Joint Shear — IS 13920:2016 Cl. 8.1.3", H3),
            Paragraph("CHECK", style("chk3", fontSize=9, fontName="Helvetica-Bold",
                                     textColor=RISK_COLOURS["Critical"], alignment=TA_CENTER)),
            Paragraph(f"Joint shear limit = {result['joint_shear_limit']:.2f} MPa "
                      f"for {inputs.get('concrete_grade','M25')}. "
                      f"Diagonal joint crack → brittle failure mode (IS 13920 Cl. 8.3.1).", SMAL),
        ])

    checks.append([
        Paragraph("ETABS Stiffness Modifier — ACI 318-19 §6.6.3.1", H3),
        Paragraph("REF", style("chk4", fontSize=9, fontName="Helvetica-Bold",
                               textColor=BLUE, alignment=TA_CENTER)),
        Paragraph(f"Use Ieff = {result.get('ie_modifier',0.35):.2f}·Ig for "
                  f"{inputs.get('member_type','Beam')} in ETABS damage-state model.", SMAL),
    ])

    ct = Table(checks, colWidths=[65*mm, 16*mm, 93*mm])
    ct.setStyle(TableStyle([
        ("GRID",        (0,0),(-1,-1), 0.3, colors.HexColor("#e0e0e0")),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[GREY, colors.white, GREY, colors.white]),
        ("VALIGN",      (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",  (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0),(-1,-1), 6),
    ]))
    story.append(ct)
    story.append(Spacer(1, 4*mm))

    # ── Probable Mechanism ────────────────────────────────────────────────────
    mech = result.get("mechanism")
    if mech:
        story.append(Paragraph("Probable Failure Mechanism", H2))
        mech_data = [[
            Paragraph(f"<b>{mech['mechanism']}</b>", BODY),
            Paragraph(mech['code'], style("mc", fontSize=8.5, textColor=BLUE, fontName="Helvetica-Bold")),
        ],[
            Paragraph(mech['detail'], SMAL),
            Paragraph("", SMAL),
        ]]
        mt = Table(mech_data, colWidths=[120*mm, 54*mm])
        mt.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,-1), LTBLUE),
            ("GRID",       (0,0),(-1,-1), 0.3, colors.HexColor("#c5cae9")),
            ("TOPPADDING", (0,0),(-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ("LEFTPADDING",(0,0),(-1,-1), 8),
            ("SPAN", (0,1),(1,1)),
        ]))
        story.append(mt)
        story.append(Spacer(1, 4*mm))

    # ── Recommended Action ────────────────────────────────────────────────────
    story.append(Paragraph("Recommended Action", H2))
    action_data = [[Paragraph(result["action"], BODY)]]
    at = Table(action_data, colWidths=[174*mm])
    at.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), RISK_BG[level]),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("BOX",           (0,0),(-1,-1), 1.5, rc),
    ]))
    story.append(at)
    story.append(Spacer(1, 4*mm))

    # ── Inspection Inputs Summary ─────────────────────────────────────────────
    story.append(Paragraph("Inspection Input Summary", H2))
    input_rows = [
        ["Parameter", "Value", "Parameter", "Value"],
        ["Member Type",     inputs.get("member_type","—"),     "Concrete Grade", inputs.get("concrete_grade","—")],
        ["Crack Width",     f"{inputs.get('width_mm',0):.2f} mm",  "Exposure Class",  inputs.get("exposure","—")],
        ["Depth Ratio",     f"{inputs.get('depth_pct',0):.0f}%",   "Seismic Zone",    inputs.get("seismic_zone","—")],
        ["Orientation",     inputs.get("orientation","—"),     "Joint Type",      inputs.get("joint_type","—")],
        ["Distance",        inputs.get("distance","—"),        "Perm. Width",     f"{result['permissible_width_mm']} mm"],
        ["Activity",        inputs.get("activity","—"),        "Width Ratio",     f"{result['width_ratio']}×"],
        ["Importance",      inputs.get("importance","—"),      "Member Mult. α",  str(result.get("member_multiplier","—"))],
    ]
    inpt = Table(input_rows, colWidths=[45*mm, 42*mm, 45*mm, 42*mm])
    inpt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), BLUE),
        ("TEXTCOLOR",     (0,0),(-1,0), colors.white),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[GREY, colors.white]),
        ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#e0e0e0")),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("FONTNAME",      (0,1),(0,-1), "Helvetica-Bold"),
        ("FONTNAME",      (2,1),(2,-1), "Helvetica-Bold"),
        ("BACKGROUND",    (0,1),(0,-1), LTBLUE),
        ("BACKGROUND",    (2,1),(2,-1), LTBLUE),
    ]))
    story.append(inpt)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9e9e9e")))
    story.append(Paragraph(
        "Anshul Dhoundiyal · Uday Kiran Mudavath · Anurag Kumar &nbsp;|&nbsp; "
        "Guide: Prof. G.P. Awadhiya, Dept. of Civil Engineering, DTU · May 2026",
        style("ft", fontSize=7.5, textColor=colors.HexColor("#9e9e9e"),
              alignment=TA_CENTER, spaceBefore=3)
    ))
    story.append(Paragraph(
        "IS 456:2000 · IS 13920:2016 · IS 1893:2016 · ACI 318-19 §6.6.3.1",
        style("ft2", fontSize=7.5, textColor=colors.HexColor("#9e9e9e"),
              alignment=TA_CENTER)
    ))

    doc.build(story)
    return buf.getvalue()
