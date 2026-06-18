import sys
import yaml
from pathlib import Path
from typing import List, Any

from atlas.schemas import AtlasExport
from scripts.classifiers.initialization import get_connections
from scripts.neo4j_database import Neo4jClient, Neo4jInserter
from scripts.derived_entities import (
    generate_life_cycle_phase_dataclasses, 
    generate_applies_in_phase_relationship, 
    generate_platform_dataclasses, 
    generate_applies_to_platform_relationship, 
)
from scripts.new_entities import (
    generate_attack_phase_dataclasses,
    generate_model_component_dataclasses,
    generate_security_objective_dataclasses,
)
from scripts.classifiers.structural_classifiers.classify_alters import AltersClassifier
from scripts.classifiers.structural_classifiers.classify_mitigates import MitigationClassifier
from scripts.classifiers.structural_classifiers.classify_has_access_to import HasAccessToClassifier
from scripts.classifiers.structural_classifiers.classify_occurs_at import OccursAtClassifier
from scripts.classifiers.structural_classifiers.classify_violates import ViolatesClassifier


class Neo4jDerivedInserter(Neo4jInserter):
    """
    Handles generation and insertion of inferred/derived nodes and edges.
    """
    def insert_derived_entities(self, life_cycle_phase_objects: List[Any], platform_objects: List[Any]) -> None:
        for phase in life_cycle_phase_objects:
            self.insert_entity(phase)

        for platform in platform_objects:
            self.insert_entity(platform)

    def insert_derived_relationships(self, atlas_data: AtlasExport) -> None:
        for technique in atlas_data.techniques.values():
            for rel in generate_applies_to_platform_relationship(technique):
                self.insert_relationship(rel)

        for mitigation in atlas_data.mitigations.values():
            for rel in generate_applies_in_phase_relationship(mitigation):
                self.insert_relationship(rel)


class Neo4jNewEntityInserter(Neo4jInserter):
    """
    Handles project-specific static ontology nodes.
    """
    def insert_new_entities(
        self,
        attack_phase_objects: List[Any],
        security_objective_objects: List[Any],
        model_component_objects: List[Any],
    ) -> None:
        for phase in attack_phase_objects:
            self.insert_entity(phase)

        for objective in security_objective_objects:
            self.insert_entity(objective)

        for component in model_component_objects:
            self.insert_entity(component)


class Neo4jAtlasInserter(Neo4jInserter):
    """
    Handles standard matrix ingestion sequences directly from the parsed source.
    """
    def insert_atlas_entities(self, atlas_data: AtlasExport) -> None:
        for tactic in atlas_data.tactics.values():
            self.insert_entity(tactic)

        for mitigation in atlas_data.mitigations.values():
            self.insert_entity(mitigation)

        for technique in atlas_data.techniques.values():
            self.insert_entity(technique)

        for case_study in atlas_data.case_studies.values():
            self.insert_entity(case_study)

    def insert_atlas_relationships(self, atlas_data: AtlasExport) -> None:
        for source_id, rel_by_type in atlas_data.relationships.items():
            for rel_type, rel_list in rel_by_type.items():
                for relationship in rel_list:
                    self.insert_relationship(relationship)


class Neo4jClassifiersInserter(Neo4jInserter):
    def __init__(self, graph_store, llm):
        super().__init__(graph_store.client)
        self.graph_store = graph_store
        self.llm = llm

    def insert_structural_classifiers_relationships(self, classifier_cls, label: str) -> List[Any]:
        classifier = classifier_cls(self.graph_store, self.llm)
        relationships = classifier.process_all_relationships()

        for relationship in relationships:
            self.insert_relationship(relationship)

        print(f"Inserted/updated {len(relationships)} {label} relationships.")
        return relationships

    def insert_alters_relationships(self):
        return self.insert_structural_classifiers_relationships(AltersClassifier, "ALTERS")

    def insert_has_access_to_relationships(self):
        return self.insert_structural_classifiers_relationships(HasAccessToClassifier, "HAS_ACCESS_TO")

    def update_mitigates_relationships(self):
        return self.insert_structural_classifiers_relationships(MitigationClassifier, "MITIGATES")

    def insert_occurs_at_relationships(self):
        return self.insert_structural_classifiers_relationships(OccursAtClassifier, "OCCURS_AT")

    def insert_violates_relationships(self):
        return self.insert_structural_classifiers_relationships(ViolatesClassifier, "VIOLATES")

    def insert_all_structural_classifiers_relationships(self) -> None:
        self.insert_has_access_to_relationships()
        self.insert_alters_relationships()
        self.insert_occurs_at_relationships()
        self.insert_violates_relationships()
        self.update_mitigates_relationships()


if __name__ == "__main__":
    client = Neo4jClient()
    client.connect()
    
    path = Path("atlas-data/dist/v6/ATLAS-2026.05.yaml")
    if not path.exists():
        print(f"Error: Targeted blueprint file not discovered at location: {path}")
        client.close()
        sys.exit(1)
        
    with path.open("r") as f:
        raw = yaml.safe_load(f)

    atlas_data = AtlasExport.model_validate(raw)
    
    # Generate derived metadata objects
    derived_phases = generate_life_cycle_phase_dataclasses()
    derived_platforms = generate_platform_dataclasses()
    attack_phases = generate_attack_phase_dataclasses()
    security_objectives = generate_security_objective_dataclasses()
    model_components = generate_model_component_dataclasses()
    
    # Initialize the orchestration targets
    atlas_inserter = Neo4jAtlasInserter(client.driver)
    derived_inserter = Neo4jDerivedInserter(client.driver)
    new_entity_inserter = Neo4jNewEntityInserter(client.driver)
    
    print("Beginning structural ingestion cycle...")
    
    # Execution pipeline execution chain
    #atlas_inserter.insert_atlas_entities(atlas_data)
    #atlas_inserter.insert_atlas_relationships(atlas_data)
    
    #derived_inserter.insert_derived_entities(derived_phases, derived_platforms)
    #derived_inserter.insert_derived_relationships(atlas_data)
    
    new_entity_inserter.insert_new_entities(attack_phases,security_objectives,model_components,
    )
    
    print("Ingestion sequence successfully committed.")
    client.close()

