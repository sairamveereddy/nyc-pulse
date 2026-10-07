import io
import csv
import zipfile
import requests
from elasticsearch import helpers
from elastic_client import get_es_client

es = get_es_client()

def ingest_mta():
    print("Downloading MTA GTFS...")
    resp = requests.get('https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip', timeout=120)
    resp.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    
    def read_csv(name):
        with zf.open(name) as f:
            return list(csv.DictReader(io.TextIOWrapper(f, 'utf-8-sig')))
            
    stops = read_csv('stops.txt')
    STOPS_INDEX = 'mta_subway_stops'
    if es.indices.exists(index=STOPS_INDEX):
        es.indices.delete(index=STOPS_INDEX)
    es.indices.create(index=STOPS_INDEX, body={'mappings': {'properties': {
        'stop_id':   {'type': 'keyword'},
        'stop_name': {'type': 'text', 'fields': {'keyword': {'type': 'keyword'}}},
        'location':  {'type': 'geo_point'},
        'parent_station': {'type': 'keyword'},
    }}})
    
    def stop_doc(s):
        doc = {'stop_id': s['stop_id'], 'stop_name': s['stop_name'], 'parent_station': s.get('parent_station') or None}
        try:
            doc['location'] = {'lat': float(s['stop_lat']), 'lon': float(s['stop_lon'])}
        except (ValueError, KeyError):
            pass
        return {k: v for k, v in doc.items() if v not in (None, '')}
        
    helpers.bulk(es, [{'_index': STOPS_INDEX, '_source': stop_doc(s)} for s in stops], raise_on_error=False)
    es.indices.refresh(index=STOPS_INDEX)
    print(f"Indexed {len(stops)} MTA stops.")

def ingest_311():
    print("Downloading 311 data...")
    BIG_URL = 'https://data.cityofnewyork.us/resource/erm2-nwe9.json'
    big = requests.get(BIG_URL, params={
        '$limit': 20000,
        '$order': 'created_date DESC',
        '$select': 'created_date,complaint_type,descriptor,borough,latitude,longitude,agency_name,status',
    }, timeout=120).json()
    
    INDEX = 'nyc_311_requests'
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)
        
    es.indices.create(index=INDEX, body={'mappings': {'properties': {
        'created_date': {'type': 'date'},
        'complaint_type': {'type': 'keyword'},
        'descriptor': {'type': 'text'},
        'borough': {'type': 'keyword'},
        'location': {'type': 'geo_point'},
        'agency_name': {'type': 'keyword'},
        'status': {'type': 'keyword'}
    }}})
    
    def enrich(r):
        doc = {
            'created_date': r.get('created_date'),
            'complaint_type': r.get('complaint_type'),
            'descriptor': r.get('descriptor'),
            'borough': r.get('borough'),
            'agency_name': r.get('agency_name'),
            'status': r.get('status'),
        }
        try:
            doc['location'] = {'lat': float(r['latitude']), 'lon': float(r['longitude'])}
        except (ValueError, KeyError, TypeError):
            pass
        return {k: v for k, v in doc.items() if v not in (None, '')}
        
    docs = [enrich(r) for r in big]
    helpers.bulk(es, [{'_index': INDEX, '_source': d} for d in docs], raise_on_error=False)
    es.indices.refresh(index=INDEX)
    print(f"Indexed {len(docs)} 311 requests.")

if __name__ == '__main__':
    if not es:
        print("Cannot run ingest without Elasticsearch credentials.")
        exit(1)
    ingest_mta()
    ingest_311()
