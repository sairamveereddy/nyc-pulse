import os
import requests
from elasticsearch import helpers
from elastic_client import get_es_client

es = get_es_client()

def setup_mistral_inference():
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("MISTRAL_API_KEY not found. Cannot set up inference.")
        return False
        
    print("Setting up mistral-embeddings inference endpoint...")
    # Setup inference endpoint for mistral-embed
    try:
        es.inference.put(
            task_type="text_embedding",
            inference_id="mistral-embeddings",
            inference_config={
                "service": "mistral",
                "service_settings": {
                    "api_key": api_key,
                    "model": "mistral-embed"
                }
            }
        )
        print("Successfully created mistral-embeddings inference endpoint.")
    except Exception as e:
        if "resource_already_exists_exception" in str(e):
            print("mistral-embeddings inference endpoint already exists.")
        else:
            print(f"Error creating inference endpoint: {e}")
            return False
    return True

def ingest_semantic_311():
    INDEX = 'nyc_311_semantic'
    print(f"Setting up index {INDEX}...")
    
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)
        
    es.indices.create(index=INDEX, body={
        'mappings': {
            'properties': {
                'created_date': {'type': 'date'},
                'complaint_type': {'type': 'keyword'},
                'descriptor': {'type': 'text'},
                'borough': {'type': 'keyword'},
                'location': {'type': 'geo_point'},
                'semantic_content': {
                    'type': 'semantic_text',
                    'inference_id': 'mistral-embeddings'
                }
            }
        }
    })
    
    print("Downloading 311 data...")
    # Fetching fewer records for semantic indexing to save time and API costs, ~2000 is enough for demo
    BIG_URL = 'https://data.cityofnewyork.us/resource/erm2-nwe9.json'
    big = requests.get(BIG_URL, params={
        '$limit': 2000,
        '$order': 'created_date DESC',
        '$select': 'created_date,complaint_type,descriptor,borough,latitude,longitude',
    }, timeout=120).json()
    
    def enrich(r):
        content = f"{r.get('complaint_type', '')} - {r.get('descriptor', '')} in {r.get('borough', '')}"
        doc = {
            'created_date': r.get('created_date'),
            'complaint_type': r.get('complaint_type'),
            'descriptor': r.get('descriptor'),
            'borough': r.get('borough'),
            'semantic_content': content
        }
        try:
            doc['location'] = {'lat': float(r['latitude']), 'lon': float(r['longitude'])}
        except (ValueError, KeyError, TypeError):
            pass
        return {k: v for k, v in doc.items() if v not in (None, '')}
        
    docs = [enrich(r) for r in big]
    
    print("Indexing documents to semantic index (this will call mistral-embed)...")
    success, errors = helpers.bulk(es, [{'_index': INDEX, '_source': d} for d in docs], raise_on_error=False, chunk_size=100)
    es.indices.refresh(index=INDEX)
    print(f"Indexed {success} documents with semantic embeddings. Errors: {len(errors)}")

if __name__ == '__main__':
    if not es:
        print("Cannot run ingest without Elasticsearch credentials.")
        exit(1)
    if setup_mistral_inference():
        ingest_semantic_311()
