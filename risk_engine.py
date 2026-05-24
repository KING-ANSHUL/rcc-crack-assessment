"""
CRI → MRI → FRI Risk Engine
All thresholds and weights derived from:
  IS 456:2000  — Plain and Reinforced Concrete (Cl. 35.3.2, 40, Table 19/20)
  IS 13920:2016 — Ductile Detailing (Cl. 8.1, 8.3)
  IS 1893:2016  — Seismic zoning
  ACI 318-19 §6.6.3.1 — Cracked-section stiffness modifiers (used in ETABS)
"""

import math

# ─────────────────────────────────────────────────────────────────────────────
# IS 456:2000 DATA
# ─────────────────────────────────────────────────────────────────────────────

# Permissible surface crack width (mm) — IS 456:2000 Cl. 35.3.2
# Normal exposure → 0.30 mm, Moderate → 0.20 mm, Severe/aggressive → 0.10 mm
IS456_CRACK_WIDTH_LIMIT = {
    "Mild":      0.30,
    "Moderate":  0.20,
    "Severe":    0.10,
    "Very Severe": 0.10,
    "Extreme":   0.10,
}

# Max shear stress τc,max (MPa) — IS 456:2000 Table 20
IS456_TAU_MAX = {15: 2.5, 20: 2.8, 25: 3.1, 30: 3.5, 35: 3.7, 40: 4.0}

# Concrete characteristic compressive strength (MPa)
CONCRETE_GRADES = {"M15": 15, "M20": 20, "M25": 25, "M30": 30, "M35": 35, "M40": 40}

# Modulus of Elasticity — IS 456:2000 Cl. 6.2.3.1: Ec = 5000√fck (MPa)
def ec(fck): return 5000 * math.sqrt(fck)

# ACI 318-19 §6.6.3.1 cracked-section stiffness modifiers
# Used for ETABS damage-state models as noted in report Chapter 6
ACI_STIFFNESS_MODIFIER = {"Beam": 0.35, "Column": 0.70, "Beam-Column Joint": 0.40}

# ─────────────────────────────────────────────────────────────────────────────
# IS 1893:2016 — SEISMIC ZONE FACTORS
# ─────────────────────────────────────────────────────────────────────────────

IS1893_ZONE_FACTOR = {"Zone II": 0.10, "Zone III": 0.16, "Zone IV": 0.24, "Zone V": 0.36}

# ─────────────────────────────────────────────────────────────────────────────
# IS 13920:2016 — JOINT SHEAR LIMITS (Cl. 8.1.3)
# τj,max = 1.0√fck (exterior joint), 1.5√fck (interior joint) in MPa
# ─────────────────────────────────────────────────────────────────────────────

def joint_shear_limit(fck: float, joint_type: str = "Interior") -> float:
    if joint_type == "Exterior":
        return 1.0 * math.sqrt(fck)
    return 1.5 * math.sqrt(fck)


# ─────────────────────────────────────────────────────────────────────────────
# CRI VARIABLE SCORING — each returns 0.0 (least severe) to 1.0 (most severe)
# ─────────────────────────────────────────────────────────────────────────────

def score_crack_width(width_mm: float, exposure: str) -> float:
    """
    IS 456:2000 Cl. 35.3.2
    Score = width_mm / permissible_width, capped and normalised.
    At 3× the permissible limit → score = 1.0 (worst).
    """
    limit = IS456_CRACK_WIDTH_LIMIT.get(exposure, 0.30)
    ratio = width_mm / limit
    # Score 0 at ≤0.5× limit; score 1 at ≥3× limit (linear in between)
    s = (ratio - 0.5) / 2.5
    return round(max(0.0, min(s, 1.0)), 4)


def score_depth_ratio(depth_pct: float) -> float:
    """
    Based on ACI 318-19 Branson equation used for ETABS (Ch.6 of report).
    Effective Ie drops sharply when crack depth > 25% of section depth.
    0–10%: negligible stiffness loss  → score 0
    10–30%: Ie ≈ 0.5–0.75 Ig         → score up to 0.40
    >30%: Ie approaches Icr           → score 1.0
    """
    if depth_pct <= 10:
        return round(depth_pct / 10 * 0.0, 4)
    elif depth_pct <= 30:
        return round(0.40 * (depth_pct - 10) / 20, 4)
    else:
        return round(min(0.40 + 0.60 * (depth_pct - 30) / 40, 1.0), 4)


def score_orientation(orientation: str) -> float:
    """
    IS 456:2000 Cl. 40 (shear), IS 13920:2016 Cl. 8.3.1 (joint diagonal).
    Vertical flexural crack → serviceability concern only (Cl. 35.3.2).
    Diagonal → shear distress (Cl. 40) or joint shear (IS 13920 Cl. 8.3.1).
    """
    scores = {
        "Vertical (flexural)":    0.20,   # IS 456 Cl. 35.3: serviceability
        "Horizontal":             0.50,   # IS 456 Cl. 40: bond split risk
        "Diagonal (shear/joint)": 0.85,   # IS 456 Cl. 40 + IS 13920 Cl. 8.3.1
        "Mixed":                  0.70,
    }
    return scores.get(orientation, 0.50)


def score_distance(distance: str, member: str) -> float:
    """
    IS 456:2000 Cl. 40.5: critical shear zone = d to 2d from support face.
    IS 13920:2016 Cl. 8: joint panel = within d of beam-column interface.
    'Near' = within 0.5d → fully in critical zone → score 1.0.
    """
    base = {"Far from support/joint": 0.20,
            "Intermediate (0.5d – 2d)": 0.55,
            "Near support/joint (<0.5d)": 1.00}
    s = base.get(distance, 0.55)
    # Joint members get an additional 10% bump (IS 13920 — joint panels are inherently critical)
    if member == "Beam-Column Joint" and distance != "Far from support/joint":
        s = min(s + 0.10, 1.00)
    return round(s, 4)


def score_activity(activity: str) -> float:
    """
    IS 456:2000 Cl. 19.2 (monitoring) — an active crack means live loading or
    ongoing settlement; progressive widening escalates all risk indices.
    """
    scores = {
        "Stable (no change)":            0.10,
        "Unknown (single observation)":  0.50,
        "Progressing (widening)":        1.00,
    }
    return scores.get(activity, 0.50)


def score_importance(importance: str) -> float:
    """
    IS 456:2000 Cl. 22 (structural continuity) — primary lateral-load members
    carry seismic/wind forces; failure is progressive.
    """
    scores = {
        "Non-critical member":            0.30,
        "Secondary member":               0.65,
        "Primary (lateral load frame)":   1.00,
    }
    return scores.get(importance, 0.65)


# CRI variable weights — sum = 1.00
# Rationale: FE cases FE-03 and FE-05 show location dominates structural consequence
WEIGHTS = {
    "width":       0.18,  # IS 456 Cl. 35.3.2
    "depth":       0.17,  # ACI 318-19 Branson / ETABS modifier
    "orientation": 0.14,  # IS 456 Cl. 40 + IS 13920 Cl. 8.3.1
    "distance":    0.19,  # IS 456 Cl. 40.5 + IS 13920 Cl. 8 (highest weight)
    "activity":    0.14,  # IS 456 Cl. 19.2
    "importance":  0.18,  # IS 456 Cl. 22
}

# ─────────────────────────────────────────────────────────────────────────────
# MEMBER MULTIPLIERS α_m — IS 13920:2016
# ─────────────────────────────────────────────────────────────────────────────

def member_multiplier(member: str, seismic_zone: str = "Zone IV") -> float:
    """
    Base multipliers from IS 13920:2016 failure mode hierarchy.
    Beam = 1.00 (ductile flexural failure — IS 13920 Cl. 6)
    Column = 1.15 (strong-column-weak-beam — IS 13920 Cl. 7)
    Joint = 1.35 base + seismic zone increment (IS 13920 Cl. 8.3.1 brittle)

    Seismic zone increment for joint (IS 1893:2016 Z factor proportional):
      Zone II (Z=0.10) → +0.00
      Zone III(Z=0.16) → +0.05
      Zone IV (Z=0.24) → +0.10  ← Delhi
      Zone V  (Z=0.36) → +0.15
    """
    base = {"Beam": 1.00, "Column": 1.15, "Beam-Column Joint": 1.35}
    alpha = base.get(member, 1.00)
    if member == "Beam-Column Joint":
        zone_increment = {
            "Zone II": 0.00, "Zone III": 0.05, "Zone IV": 0.10, "Zone V": 0.15
        }
        alpha += zone_increment.get(seismic_zone, 0.10)
    return round(alpha, 4)


# ─────────────────────────────────────────────────────────────────────────────
# RISK BANDS
# ─────────────────────────────────────────────────────────────────────────────

def risk_band(score: float) -> tuple:
    """Returns (level, urgency, is_code_action, colour)"""
    if score <= 0.25:
        return (
            "Low",
            "Routine observation",
            "IS 456:2000 Cl. 35.3.2 — Within serviceability limits. "
            "Document and include in next scheduled inspection.",
            "#2e7d32",
        )
    elif score <= 0.45:
        return (
            "Moderate",
            "Periodic monitoring",
            "IS 456:2000 Cl. 35.3.2 — Approaching or at crack width limit. "
            "Reassess in 3–6 months. Surface repair if exposure class warrants.",
            "#f9a825",
        )
    elif score <= 0.70:
        return (
            "High",
            "Detailed inspection required",
            "IS 456:2000 Cl. 40 — Possible shear distress. "
            "Engage structural specialist. Expose reinforcement at crack location. "
            "Check bar corrosion and delamination. Do not surface-fill without assessment.",
            "#e65100",
        )
    else:
        return (
            "Critical",
            "URGENT STRUCTURAL REVIEW",
            "IS 13920:2016 Cl. 8.3.1 — Possible brittle failure mode. "
            "Immediate expert assessment. Consider temporary load restriction. "
            "Sounding test for delamination. 30-day follow-up mandatory.",
            "#b71c1c",
        )


# ─────────────────────────────────────────────────────────────────────────────
# IS 456:2000 TABLE 20 — Shear capacity check (informational output)
# ─────────────────────────────────────────────────────────────────────────────

def probable_mechanism(orientation: str, member: str,
                        distance: str, width_mm: float,
                        exposure: str) -> dict:
    """
    Returns the most probable failure mechanism and IS code reference.
    Based on crack pattern + location per IS 456:2000 and IS 13920:2016.
    """
    perm = IS456_CRACK_WIDTH_LIMIT.get(exposure, 0.30)
    near = distance == "Near support/joint (<0.5d)"

    if member == "Beam-Column Joint" and orientation == "Diagonal (shear/joint)":
        return {
            "mechanism": "Joint Shear Distress",
            "code": "IS 13920:2016 Cl. 8.3.1",
            "detail": ("Diagonal cracking in the joint panel indicates joint shear "
                       "distress — a brittle failure mode with limited warning. "
                       "Load transfer continuity between beam and column at risk."),
            "severity": "critical",
        }
    if orientation == "Diagonal (shear/joint)" and near and member == "Beam":
        return {
            "mechanism": "Shear Failure at Support Zone",
            "code": "IS 456:2000 Cl. 40",
            "detail": ("Diagonal crack near beam support indicates shear distress. "
                       "Crack angle ~45° suggests principal tensile stress exceeds "
                       "concrete tensile capacity. Verify Vu/(b·d) ≤ τc,max (Table 20)."),
            "severity": "high",
        }
    if orientation == "Horizontal" and member == "Column":
        return {
            "mechanism": "Bond / Bar Splitting",
            "code": "IS 456:2000 Cl. 26.2",
            "detail": ("Horizontal crack parallel to column axis suggests bond "
                       "failure or bar splitting along longitudinal reinforcement. "
                       "Indicates loss of concrete cover integrity."),
            "severity": "high",
        }
    if orientation == "Diagonal (shear/joint)" and member == "Column":
        return {
            "mechanism": "Column Shear / Diagonal Tension",
            "code": "IS 13920:2016 Cl. 7.3",
            "detail": ("Diagonal crack in column may indicate shear-dominant behaviour "
                       "under lateral loading. Check column shear capacity per IS 13920."),
            "severity": "high",
        }
    if orientation == "Vertical (flexural)" and not near:
        if width_mm > perm:
            return {
                "mechanism": "Flexural Cracking (Serviceability Exceeded)",
                "code": "IS 456:2000 Cl. 35.3.2",
                "detail": (f"Vertical flexural crack at midspan soffit. Width {width_mm} mm "
                            f"exceeds permissible {perm} mm for this exposure class. "
                            "Monitor for progression; check long-term deflection."),
                "severity": "moderate",
            }
        return {
            "mechanism": "Flexural Cracking (Within Serviceability Limits)",
            "code": "IS 456:2000 Cl. 35.3.2",
            "detail": (f"Typical flexural crack at midspan under service load. "
                       f"Width {width_mm} mm within permissible {perm} mm. Routine monitoring."),
            "severity": "low",
        }
    if orientation == "Horizontal" and member == "Beam":
        return {
            "mechanism": "Horizontal Splitting / Delamination",
            "code": "IS 456:2000 Cl. 40",
            "detail": ("Horizontal crack in beam may indicate delamination along "
                       "reinforcement layer or torsional/bond effects."),
            "severity": "moderate",
        }
    # Default
    return {
        "mechanism": "Indeterminate — Multi-mechanism Possible",
        "code": "IS 456:2000 Cl. 35",
        "detail": ("Crack pattern does not match a single dominant mechanism. "
                   "Requires on-site structural engineer assessment."),
        "severity": "moderate",
    }


def shear_capacity_note(orientation: str, distance: str,
                         fck_grade: str, member: str) -> str | None:
    """
    IS 456:2000 Cl. 40 — if diagonal crack near support, flag shear concern
    with τc,max from Table 20.
    """
    if orientation != "Diagonal (shear/joint)":
        return None
    if distance not in ("Near support/joint (<0.5d)", "Intermediate (0.5d – 2d)"):
        return None
    fck = CONCRETE_GRADES.get(fck_grade, 25)
    tau_max = IS456_TAU_MAX.get(fck, 3.1)
    if member == "Beam":
        return (f"IS 456:2000 Table 20 — For {fck_grade}, τc,max = {tau_max} MPa. "
                f"Diagonal crack near support: verify Vu/(b·d) ≤ {tau_max} MPa.")
    elif member == "Beam-Column Joint":
        j_limit = joint_shear_limit(fck, "Interior")
        return (f"IS 13920:2016 Cl. 8.1.3 — For {fck_grade}, joint shear limit "
                f"τj,max = 1.5√fck = {j_limit:.2f} MPa. "
                f"Diagonal joint crack: urgent verification required.")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# FRI — FRAME RISK INDEX
# ─────────────────────────────────────────────────────────────────────────────

def compute_fri(mri_list: list) -> dict:
    """
    FRI = [Σ(MRIᵢ) / N] × C_cluster
    C_cluster = 1 + 0.25 × (n_High / N)
    where n_High = number of MRIs ≥ 0.46 (High or Critical band)
    Cluster penalty captures progressive frame distress (FE-06 result).
    """
    if not mri_list:
        return {"fri": 0.0, "c_cluster": 1.0, "n_high": 0}
    n = len(mri_list)
    n_high = sum(1 for m in mri_list if m >= 0.46)
    c_cluster = round(1 + 0.25 * (n_high / n), 4)
    fri = round(min((sum(mri_list) / n) * c_cluster, 1.00), 4)
    level, urgency, action, colour = risk_band(fri)
    return {
        "fri": fri, "c_cluster": c_cluster, "n_high": n_high,
        "risk_level": level, "urgency": urgency, "action": action,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ASSESSMENT FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def full_assessment(
    width_mm: float,
    depth_pct: float,
    orientation: str,
    distance: str,
    activity: str,
    importance: str,
    member_type: str,
    exposure: str = "Moderate",
    concrete_grade: str = "M25",
    seismic_zone: str = "Zone IV",
    joint_type: str = "Interior",
) -> dict:
    """
    Returns complete risk assessment dict with IS code references.

    Parameters
    ----------
    width_mm      : actual measured crack width in mm
    depth_pct     : estimated crack depth as % of section depth (0–100)
    orientation   : crack orientation label
    distance      : distance from support/joint label
    activity      : crack activity label
    importance    : member importance label
    member_type   : 'Beam' | 'Column' | 'Beam-Column Joint'
    exposure      : IS 456 Table 3 exposure class
    concrete_grade: 'M20' | 'M25' | 'M30' | 'M35' | 'M40'
    seismic_zone  : IS 1893:2016 zone
    joint_type    : 'Interior' | 'Exterior' (for IS 13920 joint shear limit)
    """
    fck = CONCRETE_GRADES.get(concrete_grade, 25)
    perm_width = IS456_CRACK_WIDTH_LIMIT.get(exposure, 0.30)

    # Individual variable scores
    s = {
        "width":       score_crack_width(width_mm, exposure),
        "depth":       score_depth_ratio(depth_pct),
        "orientation": score_orientation(orientation),
        "distance":    score_distance(distance, member_type),
        "activity":    score_activity(activity),
        "importance":  score_importance(importance),
    }

    # CRI
    cri = round(sum(WEIGHTS[k] * s[k] for k in s), 4)
    contributions = {k: round(WEIGHTS[k] * s[k], 4) for k in s}

    # MRI
    alpha = member_multiplier(member_type, seismic_zone)
    mri = round(min(cri * alpha, 1.00), 4)

    # Risk band from MRI
    level, urgency, action, colour = risk_band(mri)

    # IS code informational notes
    shear_note = shear_capacity_note(orientation, distance, concrete_grade, member_type)
    width_ratio = round(width_mm / perm_width, 2)
    width_status = (
        f"{'EXCEEDS' if width_mm > perm_width else 'Within'} IS 456:2000 Cl. 35.3.2 limit "
        f"({width_mm} mm {'>' if width_mm > perm_width else '≤'} {perm_width} mm "
        f"for {exposure} exposure). Ratio = {width_ratio}×."
    )

    # Stiffness modifier for ETABS reference
    ie_modifier = ACI_STIFFNESS_MODIFIER.get(member_type, 0.35)

    # Probable mechanism
    mechanism = probable_mechanism(orientation, member_type, distance, width_mm, exposure)

    return {
        # Core risk indices
        "cri": cri,
        "mri": mri,
        "risk_level": level,
        "urgency": urgency,
        "action": action,
        "colour": colour,

        # Variable scores and contributions
        "scores": s,
        "contributions": contributions,

        # Member context
        "member_multiplier": alpha,
        "seismic_zone": seismic_zone,

        # IS code specifics
        "permissible_width_mm": perm_width,
        "width_ratio": width_ratio,
        "width_status": width_status,
        "shear_note": shear_note,
        "ie_modifier": ie_modifier,
        "fck": fck,
        "joint_shear_limit": joint_shear_limit(fck, joint_type) if member_type == "Beam-Column Joint" else None,

        # Weights (for breakdown display)
        "weights": WEIGHTS,

        # Probable failure mechanism
        "mechanism": mechanism,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ETABS FE REFERENCE DATA — Six cases from the project (Ch. 6)
# ─────────────────────────────────────────────────────────────────────────────

FE_CASES = [
    {
        "id": "FE-01",
        "member": "Full frame",
        "scenario": "Uncracked reference — baseline",
        "stiffness_modifier": 1.00,
        "ie_ig_ratio": 1.00,
        "description": "Baseline: all members uncracked (1.0 Ig). Provides reference deflection, storey drift, and beam-end moments.",
        "risk_logic_use": "Absolute reference for all damage-state comparisons",
    },
    {
        "id": "FE-02",
        "member": "Ground beam",
        "scenario": "Flexural crack — depth ratio 10% / 25% / 40%",
        "stiffness_modifier": "Branson eq.",
        "ie_ig_ratio": "0.74 – 0.50",
        "description": "Branson equation applied for three depth ratios. Ie/Ig drops from ~0.74 (d/h=0.25) to ~0.50 (d/h=0.40). Deflection increases by 18–35%.",
        "risk_logic_use": "Calibrates CRI depth-ratio score thresholds",
    },
    {
        "id": "FE-03",
        "member": "Ground beam",
        "scenario": "Shear crack near support — 0.25 Ig locally",
        "stiffness_modifier": 0.25,
        "ie_ig_ratio": 0.25,
        "description": "Local stiffness at support zone reduced to 0.25 Ig. Force redistribution to adjacent members. Demand ratio at support = 0.82.",
        "risk_logic_use": "Justifies high weight for distance-from-support in CRI",
    },
    {
        "id": "FE-04",
        "member": "Ground column",
        "scenario": "Base-zone crack — rotational spring degraded 50% → 25%",
        "stiffness_modifier": "0.50k → 0.25k",
        "ie_ig_ratio": "0.50 → 0.25",
        "description": "Column base rotational spring reduced from 0.50k to 0.25k. Column-end rotation increases, moment redistributes to upper storey.",
        "risk_logic_use": "Basis for column MRI multiplier (1.15×)",
    },
    {
        "id": "FE-05",
        "member": "B-C Joint",
        "scenario": "Diagonal joint crack — panel stiffness 0.40 Ig",
        "stiffness_modifier": 0.40,
        "ie_ig_ratio": 0.40,
        "description": "Joint panel stiffness reduced to 0.40 Ig (IS 13920 damage state). Joint rotation +38%, storey drift amplified +22%, beam-end moment mismatch.",
        "risk_logic_use": "Justifies joint MRI multiplier (1.35–1.45×) and Critical band",
    },
    {
        "id": "FE-06",
        "member": "Bay subassembly",
        "scenario": "FE-03 + FE-05 combined in same load chain",
        "stiffness_modifier": "Multiple",
        "ie_ig_ratio": "0.25 + 0.40",
        "description": "Combined shear crack + joint crack in same load chain. Drift amplification disproportionately greater than sum of individual cases. D/C ratios exceed 1.0.",
        "risk_logic_use": "Validates FRI cluster correction factor C_cluster",
    },
]

# Expected storey drift limits (IS 1893:2016 Cl. 7.11.1)
# Permissible storey drift = 0.004 × storey height
# For h = 3.2 m → limit = 0.004 × 3200 = 12.8 mm
IS1893_DRIFT_LIMIT_FRACTION = 0.004  # of storey height


def fe_adjusted_mri(base_mri: float, dc_ratio: float | None,
                    drift_amplification_pct: float | None,
                    ie_ig_actual: float | None) -> dict:
    """
    Adjusts MRI using actual ETABS FE outputs.

    Parameters
    ----------
    base_mri              : MRI from crack observation alone
    dc_ratio              : demand/capacity ratio from ETABS (e.g. 0.82 = 82%)
    drift_amplification_pct: % increase in storey drift vs uncracked baseline (FE-01)
    ie_ig_actual          : actual Ie/Ig ratio from ETABS output

    Returns adjusted MRI and explanation.
    """
    adjusted = base_mri
    notes = []

    if dc_ratio is not None:
        # D/C > 0.8 escalates risk; D/C > 1.0 = failure
        if dc_ratio >= 1.0:
            adjusted = min(adjusted * 1.30, 1.0)
            notes.append(f"D/C = {dc_ratio:.2f} ≥ 1.0 — member overstressed; MRI escalated +30%")
        elif dc_ratio >= 0.80:
            adjusted = min(adjusted * 1.15, 1.0)
            notes.append(f"D/C = {dc_ratio:.2f} ≥ 0.80 — approaching capacity; MRI escalated +15%")
        else:
            notes.append(f"D/C = {dc_ratio:.2f} — within capacity limits")

    if drift_amplification_pct is not None:
        # IS 1893:2016 Cl. 7.11.1: drift amplification > 20% is significant
        if drift_amplification_pct >= 30:
            adjusted = min(adjusted * 1.20, 1.0)
            notes.append(f"Drift amplification +{drift_amplification_pct:.0f}% ≥ 30% — significant; MRI escalated +20%")
        elif drift_amplification_pct >= 20:
            adjusted = min(adjusted * 1.10, 1.0)
            notes.append(f"Drift amplification +{drift_amplification_pct:.0f}% ≥ 20% — moderate (IS 1893 Cl. 7.11.1); MRI escalated +10%")
        else:
            notes.append(f"Drift amplification +{drift_amplification_pct:.0f}% — within normal range")

    if ie_ig_actual is not None:
        expected_ie = ACI_STIFFNESS_MODIFIER.get("Beam", 0.35)
        if ie_ig_actual < expected_ie * 0.7:
            adjusted = min(adjusted * 1.10, 1.0)
            notes.append(f"Ie/Ig = {ie_ig_actual:.2f} — below ACI 318-19 §6.6.3.1 expected ({expected_ie}); MRI escalated +10%")
        else:
            notes.append(f"Ie/Ig = {ie_ig_actual:.2f} — consistent with ACI 318-19 §6.6.3.1 ({expected_ie})")

    adjusted = round(adjusted, 4)
    level, urgency, action, colour = risk_band(adjusted)
    return {
        "fe_mri": adjusted,
        "base_mri": base_mri,
        "escalation": round(adjusted - base_mri, 4),
        "notes": notes,
        "risk_level": level,
        "urgency": urgency,
        "colour": colour,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE: option lists for Streamlit dropdowns
# ─────────────────────────────────────────────────────────────────────────────

MEMBER_TYPES     = ["Beam", "Column", "Beam-Column Joint"]
ORIENTATIONS     = ["Vertical (flexural)", "Horizontal", "Diagonal (shear/joint)", "Mixed"]
DISTANCES        = ["Far from support/joint", "Intermediate (0.5d – 2d)", "Near support/joint (<0.5d)"]
ACTIVITIES       = ["Stable (no change)", "Unknown (single observation)", "Progressing (widening)"]
IMPORTANCES      = ["Non-critical member", "Secondary member", "Primary (lateral load frame)"]
EXPOSURE_CLASSES = list(IS456_CRACK_WIDTH_LIMIT.keys())
CONCRETE_GRADES_LIST = list(CONCRETE_GRADES.keys())
SEISMIC_ZONES    = list(IS1893_ZONE_FACTOR.keys())
JOINT_TYPES      = ["Interior", "Exterior"]

__all__ = [
    "full_assessment", "compute_fri", "fe_adjusted_mri", "probable_mechanism",
    "FE_CASES", "WEIGHTS", "MEMBER_TYPES", "ORIENTATIONS", "DISTANCES",
    "ACTIVITIES", "IMPORTANCES", "EXPOSURE_CLASSES", "CONCRETE_GRADES_LIST",
    "SEISMIC_ZONES", "JOINT_TYPES", "IS456_CRACK_WIDTH_LIMIT", "IS456_TAU_MAX",
    "IS1893_DRIFT_LIMIT_FRACTION", "member_multiplier",
]
