# Voyverse ATLAS Graph Pipeline

Voyverse builds a Neo4j knowledge graph from the MITRE ATLAS data model and enriches it with project-specific derived ontology nodes, structural classifier relationships, and similarity relationships.

The graph starts with ATLAS tactics, techniques, mitigations, case studies, and source relationships. It then adds defensive lifecycle metadata, model-security ontology nodes, and classifier-generated edges that describe how adversarial ML techniques interact with model components, attack phases, security objectives, mitigations, and related techniques or case studies.

## Architecture

The pipeline is organized around a small set of insertion and classifier modules:

- `neo4j_database.py`: Neo4j connection and generic entity/relationship insertion.
- `neo4j_inserters.py`: Reusable inserter classes for ATLAS data, derived data, structural classifier output, and similarity classifier output.
- `main_inserter.py`: Single end-to-end entrypoint for building the full graph.
- `derived_entities.py`: Derived lifecycle/platform nodes and relationships.
- `new_entities.py`: Static ontology nodes for attack phases, security objectives, and model components.
- `classifiers/structural_classifiers/`: LLM-backed classifiers that infer operational security relationships.
- `classifiers/similarity_classifiers/`: Similarity calculators and LLM summaries for related techniques and case studies.

## Pipeline Stages

Run order matters because later stages depend on nodes and relationships created earlier.

1. **ATLAS ingestion**
   Inserts ATLAS tactics, mitigations, techniques, case studies, and source relationships. ATLAS case-study technique usage is stored as `EMPLOYS` in Neo4j.

2. **Derived ontology ingestion**
   Inserts lifecycle phases and platforms, then creates derived `APPLIES_IN_PHASE` and `APPLIES_TO_PLATFORM` relationships. It also inserts static project ontology nodes: attack phases, security objectives, and model components.

3. **Structural classifiers**
   Runs classifiers that enrich techniques and mitigations with operational relationships:
   - `HAS_ACCESS_TO`: model components required or useful for a technique.
   - `ALTERS`: model components modified by a technique.
   - `OCCURS_AT`: whether a technique occurs during training or inference.
   - `VIOLATES`: security objectives impacted by a technique.
   - `MITIGATES`: mitigation-to-technique coverage categories.

4. **Similarity classifiers**
   Creates bidirectional `IS_SIMILAR_TO` relationships:
   - Technique similarity compares technique topology and shared operational properties.
   - Case study similarity compares employed techniques and soft technique matches.

By default, classifier relationship reasoning is not stored to reduce token usage. Inserter and classifier constructors support `include_reasoning=True` for debugging or tests.

## Setup

Install Python dependencies in your preferred virtual environment:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements
```

Create `scripts/.env` with Neo4j and Mistral settings:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<password>
NEO4J_DATABASE=neo4j
MISTRAL_API_KEY=<api-key>
```

Ensure ATLAS data exists at:

```text
atlas-data/dist/v6/ATLAS-2026.05.yaml
```

## Running The Full Pipeline

From the project root:

```bash
python -m scripts.main_inserter
```

The entrypoint reports progress through each stage:

```text
[1/4] Inserting ATLAS entities and relationships...
[2/4] Inserting derived entities and relationships...
[3/4] Running structural classifiers...
[4/4] Running similarity classifiers...
```

The full run performs LLM calls and may take time. It should be run only when Neo4j is reachable, credentials are configured, and the ATLAS YAML file is present.

## Development Workflow

- Keep insertion behavior centralized in `neo4j_database.py` and `neo4j_inserters.py`.
- Add new static ontology nodes through `new_entities.py`.
- Add derived relationships through `derived_entities.py`.
- Keep classifier logic inside the relevant classifier module and return `Relationship` objects for insertion.
- Run a syntax check before long graph builds:

```bash
python -m compileall -q scripts
```

For local debugging, run individual classifier modules directly with a small target entity before executing the full pipeline.
