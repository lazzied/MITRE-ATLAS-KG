from scripts.mappers import (
    ATTACK_PHASE_DESCRIPTION,
    MODEL_COMPONENT_DESCRIPTION,
    SECURITY_OBJECTIVE_DESCRIPTION,
)
from scripts.schemas import (
    AttackPhase,
    AttackPhaseID,
    ModelComponent,
    ModelComponentID,
    SecurityObjective,
    SecurityObjectiveID,
)


def generate_attack_phase_dataclasses() -> list[AttackPhase]:
    return [
        AttackPhase(
            id=AttackPhaseID[phase_type.name],
            type=phase_type,
            description=description,
        )
        for phase_type, description
        in ATTACK_PHASE_DESCRIPTION.items()
    ]


def generate_security_objective_dataclasses() -> list[SecurityObjective]:
    return [
        SecurityObjective(
            id=SecurityObjectiveID[objective_type.name],
            type=objective_type,
            description=description,
        )
        for objective_type, description
        in SECURITY_OBJECTIVE_DESCRIPTION.items()
    ]


def generate_model_component_dataclasses() -> list[ModelComponent]:
    return [
        ModelComponent(
            id=ModelComponentID[component_type.name],
            type=component_type,
            description=description,
        )
        for component_type, description
        in MODEL_COMPONENT_DESCRIPTION.items()
    ]


def transform_attack_phase(phase: AttackPhase) -> dict:
    return {
        "id": phase.id.value,
        "type": phase.type.value,
        "description": phase.description,
    }


def transform_security_objective(objective: SecurityObjective) -> dict:
    return {
        "id": objective.id.value,
        "type": objective.type.value,
        "description": objective.description,
    }


def transform_model_component(component: ModelComponent) -> dict:
    return {
        "id": component.id.value,
        "type": component.type.value,
        "description": component.description,
    }
