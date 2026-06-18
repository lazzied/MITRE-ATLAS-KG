import sys
import yaml
from pathlib import Path

from atlas.schemas import AtlasExport
from scripts.classifiers.initialization import get_connections
from scripts.entities.derived_entities import (
    generate_life_cycle_phase_dataclasses,
    generate_platform_dataclasses,
)
from scripts.neo4j_database import Neo4jClient
from scripts.neo4j_inserters import (
    Neo4jAtlasInserter,
    Neo4jDerivedInserter,
    Neo4jNewEntityInserter,
    Neo4jSimilarityClassifiersInserter,
    Neo4jStructuralClassifiersInserter,
)
from scripts.entities.new_entities import (
    generate_attack_phase_dataclasses,
    generate_model_component_dataclasses,
    generate_security_objective_dataclasses,
)


ATLAS_DATA_PATH = Path("atlas-data/dist/v6/ATLAS-2026.05.yaml")


def load_atlas_data(path: Path) -> AtlasExport:
    if not path.exists():
        print(f"Error: Targeted blueprint file not discovered at location: {path}")
        sys.exit(1)

    with path.open("r") as f:
        raw = yaml.safe_load(f)

    return AtlasExport.model_validate(raw)


def main() -> None:
    print("Beginning complete Neo4j insertion pipeline...")

    atlas_data = load_atlas_data(ATLAS_DATA_PATH)

    derived_phases = generate_life_cycle_phase_dataclasses()
    derived_platforms = generate_platform_dataclasses()
    attack_phases = generate_attack_phase_dataclasses()
    security_objectives = generate_security_objective_dataclasses()
    model_components = generate_model_component_dataclasses()

    client = Neo4jClient()
    client.connect()

    try:
        atlas_inserter = Neo4jAtlasInserter(client.driver)
        derived_inserter = Neo4jDerivedInserter(client.driver)
        new_entity_inserter = Neo4jNewEntityInserter(client.driver)

        print("\nPreparing Neo4j constraints and indexes...")
        atlas_inserter.ensure_schema()
        print("Neo4j schema preparation complete.")

        print("\n[1/4] Inserting ATLAS entities and relationships...")
        #atlas_inserter.insert_atlas_entities(atlas_data)
        #atlas_inserter.insert_atlas_relationships(atlas_data)
        print("ATLAS entities and relationships inserted.")

        print("\n[2/4] Inserting derived entities and relationships...")
        #derived_inserter.insert_derived_entities(derived_phases, derived_platforms)
        """
        new_entity_inserter.insert_new_entities(
            attack_phases,
            security_objectives,
            model_components,
        )
        """
        #derived_inserter.insert_derived_relationships(atlas_data)
        print("Derived entities and relationships inserted.")

        print("\n[3/4] Running structural classifiers...")
        graph_store, llm = get_connections()
        structural_inserter = Neo4jStructuralClassifiersInserter(graph_store, llm)
        structural_inserter.insert_all_structural_classifiers_relationships()
        print("Structural classifier relationships inserted.")

        print("\n[4/4] Running similarity classifiers...")
        #similarity_inserter = Neo4jSimilarityClassifiersInserter(graph_store, llm)
        #similarity_inserter.insert_all_similarity_classifiers_relationships()
        print("Similarity classifier relationships inserted.")

        print("\nComplete Neo4j insertion pipeline successfully committed.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
