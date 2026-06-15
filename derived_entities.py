# this code takes the classes of atlas and from them generate independent classes from the main class using its properties

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ATLAS_PATH = ROOT / "atlas-data"

print("ADDING PATH:", ATLAS_PATH)  # debug line

sys.path.insert(0, str(ATLAS_PATH))

from atlas.schemas import Mitigation, Technique
from mappers import AI_SYSTEM_DESCRIPTIONS, LIFECYCLE_PHASE_ID_MAP, MITIGATION_LIFECYCLE_PHASE_DESCRIPTIONS
from schemas import  LifeCyclePhase, LifecyclePhaseID, Platform, PlatformID, Relationship, RelationshipType



def generate_life_cycle_phase_dataclasses() -> list[LifeCyclePhase]:
    phases = []

    for phase_type, description in MITIGATION_LIFECYCLE_PHASE_DESCRIPTIONS.items():
        phases.append(
            LifeCyclePhase(
                id=LIFECYCLE_PHASE_ID_MAP[phase_type],
                type=phase_type,
                description=description,
            )
        )

    return phases


def generate_platform_dataclasses() -> list[Platform]:
    return [
        Platform(
            id=PlatformID[platform_type.name],
            type=platform_type,
            description=description,
        )
        for platform_type, description
        in AI_SYSTEM_DESCRIPTIONS.items()
    ]



def generate_platform_relationship(
    technique: Technique,
) -> list[Relationship]:
    relationships = []

    for platform_type in technique.platforms:
        platform_id = PlatformID[platform_type.name]

        relationships.append(
            Relationship(
                source=technique.id,
                target=platform_id,
                relationship_type=RelationshipType.APPLIES_TO_PLATFORM,
                description=(
                    f"This technique applies to {platform_type.value} systems."
                ),
            )
        )

    return relationships


def generate_life_cycle_phase_relationship(
    mitigation: Mitigation,
) -> list[Relationship]:
    relationships = []

    for phase_type in mitigation.lifecycle_phases:
        phase_id = LifecyclePhaseID[phase_type.name]

        relationships.append(
            Relationship(
                source=mitigation.id,
                target=phase_id,
                relationship_type=RelationshipType.APPLIES_IN_PHASE,
                description=(
                    f"This mitigation applies during the "
                    f"{phase_type.value} lifecycle phase."
                ),
            )
        )

    return relationships

def transform_lifecycle_phase(
    phase: LifeCyclePhase,
) -> dict:
    return {
        "id": phase.id.value,
        "type": phase.type.value,
        "description": phase.description,
    }


def transform_platform(
    platform: Platform,
) -> dict:
    return {
        "id": platform.id.value,
        "type": platform.type.value,
        "description": platform.description,
    }

if __name__ == "__main__":
    life_cycle_phases = generate_life_cycle_phase_dataclasses()
    platforms = generate_platform_dataclasses()
    print("Generated life cycle phases:")
    for phase in life_cycle_phases:
        print(phase)