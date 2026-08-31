# Robot STL assets

The 47 STL files in `src/mjlab_microduck/robot/microduck/assets/` serve two
current robot assemblies:

- `robot_allcollisions.xml`: normal walking feet.
- `robot_allcollisions_rollers.xml`: four passive wheels.

They are deliberately kept together beside the MJCF files because MuJoCo loads
them by relative path. `asset_manifest.csv` classifies every file by physical
role and records the quantity used by each assembly.

## Create an organized copy

From the repository root:

```bash
uv run scripts/organize_robot_assets.py --check
uv run scripts/organize_robot_assets.py
```

The second command creates the ignored build artifact
`build/microduck_robot_assets/` with this layout:

```text
01_print_candidates/
├── rigid/
└── flexible/
02_purchased_reference/
├── electronics/
└── mechanical/
90_legacy_unreferenced/
MANIFEST.csv
README.md
```

Use a different new output directory when a bundle already exists:

```bash
uv run scripts/organize_robot_assets.py --output build/microduck_robot_assets-v2
```

## What the categories mean

`print_candidate_rigid` contains structural mounts, shells, leg parts, and
roller frames. `print_candidate_flexible` contains the mouth skins, walking
soles, and roller tires. The material assignments are inferred from the current
part names and assembly roles; they are not slicer profiles.

`purchased_reference` is intentionally included in the bundle. It contains the
visual/collision envelopes for 15 Dynamixel XL330 servos, eleven 22 x 16 x 4 mm
bearings, three approximately 10 x 15 x 3 mm bearings (ID x OD x thickness), the
Robot HAT PCB, Raspberry Pi Zero 2 W, NP-F970 battery, camera lens, and speaker.
These files help with fit and clearance checks; they are not printable
replacements for the purchased parts. The complete reconstruction BOM and its
evidence labels are in [hardware/microduck_bom.csv](hardware/microduck_bom.csv).

`legacy_unreferenced` contains four older shell/upper-leg exports that neither
current assembly declares. Keeping them separate prevents accidental printing
while preserving potentially useful historical geometry.

## Manufacturing warning

The MJCF export configs set `simplify_stls: true` and cap mesh size. Therefore
the checked-in meshes are simulation assets, not a certified manufacturing
release. Before printing, verify the current Onshape revision, units,
tolerances, material, fasteners, supports, and orientation. The source README
licenses 3D model files under Creative Commons BY-SA-NC.

The current Onshape links are stored in:

- `config_mjcf_allcollisions.json` for the walking assembly.
- `config_mjcf_allcollisions_rollers.json` for the roller assembly.
