import os
from pathlib import Path
from dotenv import load_dotenv
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore 
from llama_index.llms.mistralai import MistralAI

def get_connections():
    """Loads environment variables and returns initialized connections."""
    #  Load enviroment,; death is better than debugging imports
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent if "scripts" in script_dir.parts else script_dir
    env_path = root_dir / ".env"
    load_dotenv(dotenv_path=env_path)
    
    #  initialize llm
    mistral_key = os.getenv("MISTRAL_API_KEY")
    llm = MistralAI(model="mistral-small-latest", api_key=mistral_key, temperature=0.0)
    
    # initialize llm for
    graph_store = Neo4jPropertyGraphStore(
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        url=os.getenv("NEO4J_URI"),
        database=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    
    return graph_store, llm