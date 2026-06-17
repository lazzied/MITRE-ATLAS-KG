# this code takes the classes of atlas and from them generate independent classes from them using their properties without the use of llm; properties to entities

from atlas.schemas import Mitigation, Technique
from scripts.mappers import MITIGATION_LIFECYCLE_PHASE_DESCRIPTIONS, PLATFORM_DESCRIPTIONS
from scripts.schemas import  LifeCyclePhase, LifecyclePhaseID, Platform, PlatformID, Relationship, RelationshipType



def generate_life_cycle_phase_dataclasses() -> list[LifeCyclePhase]:
    phases = []

    for phase_type, description in MITIGATION_LIFECYCLE_PHASE_DESCRIPTIONS.items():
        phases.append(
            LifeCyclePhase(
                id=LifecyclePhaseID[phase_type.name],
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
        in PLATFORM_DESCRIPTIONS.items()
    ]

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

def generate_applies_to_platform_relationship(
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


def generate_applies_in_phase_relationship(
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



if __name__ == "__main__":
    life_cycle_phases = generate_life_cycle_phase_dataclasses()
    platforms = generate_platform_dataclasses()
    print("Generated life cycle phases:")
    for phase in life_cycle_phases:
        print(phase)
