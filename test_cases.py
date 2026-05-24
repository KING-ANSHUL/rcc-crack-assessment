import sys
sys.path.insert(0, r'C:\college_project')
from risk_engine import full_assessment

cases = [
    ('V-01 Midspan beam 0.3mm vertical',
     dict(width_mm=0.30, depth_pct=25, orientation='Vertical (flexural)',
          distance='Far from support/joint', activity='Unknown (single observation)',
          importance='Secondary member', member_type='Beam')),
    ('V-02 0.7mm diagonal near column',
     dict(width_mm=0.70, depth_pct=30, orientation='Diagonal (shear/joint)',
          distance='Near support/joint (<0.5d)', activity='Unknown (single observation)',
          importance='Primary (lateral load frame)', member_type='Beam')),
    ('V-03 0.15mm diagonal in B-C JOINT',
     dict(width_mm=0.15, depth_pct=20, orientation='Diagonal (shear/joint)',
          distance='Near support/joint (<0.5d)', activity='Unknown (single observation)',
          importance='Primary (lateral load frame)', member_type='Beam-Column Joint')),
    ('V-04 Hairline midspan secondary beam',
     dict(width_mm=0.05, depth_pct=10, orientation='Vertical (flexural)',
          distance='Far from support/joint', activity='Stable (no change)',
          importance='Secondary member', member_type='Beam')),
    ('V-05 0.5mm horizontal column face',
     dict(width_mm=0.50, depth_pct=25, orientation='Horizontal',
          distance='Near support/joint (<0.5d)', activity='Unknown (single observation)',
          importance='Primary (lateral load frame)', member_type='Column')),
]

print(f"{'Case':<42} {'CRI':>6} {'MRI':>6}  {'Risk':<10}  Width check")
print('-' * 95)
for name, kwargs in cases:
    r = full_assessment(**kwargs, exposure='Moderate', concrete_grade='M25', seismic_zone='Zone IV')
    w = 'EXCEEDS' if 'EXCEEDS' in r['width_status'] else 'Within limit'
    print(f"{name:<42} {r['cri']:>6.3f} {r['mri']:>6.3f}  {r['risk_level']:<10}  {w}")

print()
print("Annexure A case (report says CRI~0.744, Critical):")
r = full_assessment(0.40, 22, 'Diagonal (shear/joint)', 'Near support/joint (<0.5d)',
                    'Unknown (single observation)', 'Primary (lateral load frame)',
                    'Beam', 'Moderate', 'M25', 'Zone IV')
print(f"  CRI={r['cri']}  MRI={r['mri']}  Risk={r['risk_level']}")
print(f"  {r['width_status']}")
if r['shear_note']:
    print(f"  {r['shear_note']}")
