import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

def get_es_client():
    endpoint = os.environ.get('ELASTIC_ENDPOINT')
    api_key = os.environ.get('ELASTIC_API_KEY')
    if not endpoint or not api_key:
        print("Warning: ELASTIC_ENDPOINT and/or ELASTIC_API_KEY not found in env.")
        return None
    es = Elasticsearch(endpoint, api_key=api_key)
    return es
