import json
from elastic_client import get_es_client

es = get_es_client()

def get_transit_context(location_name: str) -> str:
    """Find MTA stops near a given location name or station name."""
    if not es: return "Error: Elasticsearch not configured."
    res = es.search(index='mta_subway_stops', size=5, body={
        'query': {'match': {'stop_name': location_name}}
    })
    hits = res['hits']['hits']
    if not hits:
        return f"No MTA stops found matching '{location_name}'."
    
    results = []
    for hit in hits:
        src = hit['_source']
        results.append(f"Station: {src.get('stop_name')} (ID: {src.get('stop_id')})")
    
    if hits and 'location' in hits[0]['_source']:
        loc = hits[0]['_source']['location']
        geo_res = es.search(index='mta_subway_stops', size=10, body={
            'query': {
                'geo_distance': {
                    'distance': '1km',
                    'location': loc
                }
            }
        })
        nearby = [h['_source']['stop_name'] for h in geo_res['hits']['hits'] if h['_id'] != hits[0]['_id']]
        results.append(f"Nearby stations (1km radius): {', '.join(set(nearby))}")
        
    return "\n".join(results)

def search_historical_impacts(location: str, issue: str, time_context: str = "") -> str:
    """Search 311 data for historical complaints related to an issue near a location."""
    if not es: return "Error: Elasticsearch not configured."
    query = f"{issue} {location} {time_context}"
    res = es.search(index='nyc_311_requests', size=10, body={
        'query': {
            'multi_match': {
                'query': query,
                'fields': ['complaint_type^2', 'descriptor', 'borough']
            }
        }
    })
    hits = res['hits']['hits']
    total = res['hits']['total']['value']
    if not hits:
        return f"No historical 311 evidence found for {issue} near {location}. Total records matched: 0."
    
    results = [f"Found {total} historical 311 complaints (BM25 Lexical). Showing top hits:"]
    for h in hits:
        src = h['_source']
        results.append(f"- {src.get('created_date', '')[:10]}: {src.get('complaint_type')} ({src.get('descriptor')}) in {src.get('borough')}")
        
    return "\n".join(results)

def get_neighborhood_signals(location: str) -> str:
    """Get recent overall 311 signals/complaints for a borough or neighborhood to establish a baseline."""
    if not es: return "Error: Elasticsearch not configured."
    res = es.search(index='nyc_311_requests', size=0, body={
        'query': {
            'match': {'borough': location}
        },
        'aggs': {
            'top_complaints': {
                'terms': {'field': 'complaint_type', 'size': 5}
            }
        }
    })
    
    buckets = res.get('aggregations', {}).get('top_complaints', {}).get('buckets', [])
    if not buckets:
        return f"No neighborhood signals found for {location}."
        
    results = [f"Top 311 complaint categories in {location}:"]
    for b in buckets:
        results.append(f"- {b['key']}: {b['doc_count']} incidents")
    return "\n".join(results)

def semantic_search_signals(query: str, location: str = None) -> str:
    """Perform genuine semantic retrieval over 311 records using Mistral embeddings. Finds concepts where keywords don't match."""
    if not es: return "Error: Elasticsearch not configured."
    
    es_query = {
        "semantic": {
            "field": "semantic_content",
            "query": query
        }
    }
    
    # We won't use a strict borough filter because location from Mistral might be "Williamsburg, Brooklyn" instead of just "BROOKLYN"
    try:
        res = es.search(index='nyc_311_semantic', size=5, body={'query': es_query})
        hits = res['hits']['hits']
        total = res['hits']['total']['value']
        
        if not hits:
            return f"No semantic matches found for '{query}'."
            
        results = [f"Found {total} semantic matches using Mistral embeddings. Showing top hits:"]
        for h in hits:
            src = h['_source']
            results.append(f"- [{src.get('complaint_type')}] {src.get('descriptor')} in {src.get('borough')} (Score: {h['_score']:.2f})")
        return "\n".join(results)
    except Exception as e:
        return f"Semantic search failed: {str(e)}"

def verify_hypothesis(hypothesis: str, location: str) -> str:
    """Search Elasticsearch for evidence supporting or contradicting a specific ripple effect hypothesis (Hybrid BM25 + Semantic)."""
    if not es: return "Error: Elasticsearch not configured."
    query = f"{hypothesis} {location}"
    
    results = []
    
    # 1. Lexical BM25 Search
    res_lex = es.search(index='nyc_311_requests', size=3, body={
        'query': {
            'multi_match': {
                'query': query,
                'fields': ['complaint_type', 'descriptor']
            }
        }
    })
    lex_total = res_lex['hits']['total']['value']
    results.append(f"Lexical (BM25) search found {lex_total} records matching hypothesis.")
    for h in res_lex['hits']['hits']:
        src = h['_source']
        results.append(f"- [LEXICAL] [{src.get('complaint_type')}] {src.get('descriptor')} in {src.get('borough')}")
        
    # 2. Semantic Search (Mistral embeddings)
    try:
        es_query = {
            "semantic": {
                "field": "semantic_content",
                "query": f"{hypothesis} near {location}"
            }
        }
        res_sem = es.search(index='nyc_311_semantic', size=3, body={'query': es_query})
        sem_total = res_sem['hits']['total']['value']
        results.append(f"\nSemantic search found {sem_total} records matching concepts.")
        for h in res_sem['hits']['hits']:
            src = h['_source']
            results.append(f"- [SEMANTIC] [{src.get('complaint_type')}] {src.get('descriptor')} in {src.get('borough')}")
    except Exception as e:
        pass # Silently skip semantic if index is not ready yet
        
    if lex_total == 0 and ('sem_total' not in locals() or sem_total == 0):
        return f"Could not verify hypothesis '{hypothesis}'. Total records matched: 0."
        
    return "\n".join(results)

TOOLS_MAP = {
    "get_transit_context": get_transit_context,
    "search_historical_impacts": search_historical_impacts,
    "get_neighborhood_signals": get_neighborhood_signals,
    "semantic_search_signals": semantic_search_signals,
    "verify_hypothesis": verify_hypothesis
}
