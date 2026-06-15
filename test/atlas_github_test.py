import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ATLAS_PATH = ROOT / "atlas-data"

print("ADDING PATH:", ATLAS_PATH)  # debug line

sys.path.insert(0, str(ATLAS_PATH))

import yaml
from pathlib import Path
from atlas.schemas import AtlasExport

path = Path("atlas-data/dist/v6/ATLAS-2026.05.yaml")

with path.open("r") as f:
    raw = yaml.safe_load(f)

atlas_data = AtlasExport.model_validate(raw)
"""

print("Release version:", atlas_data.collection.version)
import json
# Convert enum keys to their string values first
print(atlas_data.relationships)


#print("example of tactic:", atlas_data.tactics["AML.TA0001"].__dict__)
#print(list(vars(atlas_data.tactics["AML.TA0001"]).keys()))

#print("example of mitigation:", atlas_data.mitigations["AML.M0001"].__dict__)
#print(list(vars(atlas_data.mitigations["AML.M0001"]).keys()))

#print("example of technique:", atlas_data.techniques["AML.T0001"].__dict__)
#print(list(vars(atlas_data.techniques["AML.T0001"]).keys()))

print("example of use case:", atlas_data.case_studies["AML.CS0000"].__dict__)
print(list(vars(atlas_data.case_studies["AML.CS0000"]).keys()))
"""
print("Tactics:", len(atlas_data.tactics))
print("case studies:", len(atlas_data.case_studies))
print("Techniques:", len(atlas_data.techniques))
print("Mitigations:", len(atlas_data.mitigations))
print("Relationships:", len(atlas_data.relationships))
