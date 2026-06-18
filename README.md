# A Queryable Knowledge Graph of MITRE ATLAS

a Neo4j knowledge graph from the MITRE ATLAS data model and enriches it with project-specific derived ontology nodes, structural classifier relationships, and similarity relationships.

note: in this current version, the query module doesn't work and same with similarities classifier.

The graph starts with ATLAS tactics, techniques, mitigations, case studies, and source relationships. It then adds defensive lifecycle metadata, model-security ontology nodes, and classifier-generated edges that describe how adversarial ML techniques interact with model components, attack phases, security objectives, mitigations, and related techniques or case studies.

## Architecture

The pipeline is organized around a small set of insertion and classifier modules:

- `neo4j_database.py`: Neo4j connection and generic entity/relationship insertion.
- `neo4j_inserters.py`: Reusable inserter classes for ATLAS data, derived data, structural classifier output, and similarity classifier output.
- `main_inserter.py`: Single end-to-end entrypoint for building the full graph.
- `schemas.py` : definition of KG entities
- `\entities` : creation of KG entities
- `classifiers/structural_classifiers/`: LLM-backed classifiers that infer operational security relationships.
- `classifiers/similarity_classifiers/`: Similarity calculators and LLM summaries for related techniques and case studies.

# Setup

## 1. Clone the MITRE ATLAS Data Repository

Choose a working directory and clone the MITRE ATLAS data repository:

```bash
git clone https://github.com/mitre-atlas/atlas-data.git
```

This will create a folder named `atlas-data`.

## 2. Clone the Knowledge Graph Project

Create a second directory alongside `atlas-data` and clone this repository into it:

```bash
git clone https://github.com/lazzied/MITRE-ATLAS-KG.git
```

Your directory structure should look like:

```text
root/
├── atlas-data/
└── MITRE-ATLAS-KG/
```

## 3. Create and Activate a Virtual Environment

Navigate to the project directory:

```bash
cd MITRE-ATLAS-KG
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it:

**Windows**

```bash
venv\Scripts\activate
```

**Linux/macOS**

```bash
source venv/bin/activate
```

## 4. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## 5. Run the Knowledge Graph Ingestion Pipeline

Return to the parent directory containing both repositories:

```bash
cd ..
```

From the root directory, run:

```bash
python -m scripts.main_inserter
```

The script expects both repositories to be sibling directories:

```text
root/
├── atlas-data/
└── MITRE-ATLAS-KG/
```


The entrypoint reports progress through each stage:

```text
[1/4] Inserting ATLAS entities and relationships...
[2/4] Inserting derived entities and relationships...
[3/4] Running structural classifiers...
```

The full run performs LLM calls and may take time. It should be run only when Neo4j is reachable, credentials are configured, and the ATLAS YAML file is present.
