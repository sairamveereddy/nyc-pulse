import os
import json
from mistralai.client import Mistral
from tools import TOOLS_MAP
from elastic_client import get_es_client

def get_mistral_client():
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("Warning: MISTRAL_API_KEY not found in env.")
        return None
    return Mistral(api_key=api_key)

def run_evidence_loop(event_description: str):
    client = get_mistral_client()
    if not client:
        return {"error": "Mistral API key not configured."}
        
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_transit_context",
                "description": "Find MTA stops near a given location name or station name to understand transit displacement.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location_name": {"type": "string"}
                    },
                    "required": ["location_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_historical_impacts",
                "description": "Search historical 311 data (BM25 lexical) for complaints related to an issue near a location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "issue": {"type": "string"},
                        "time_context": {"type": "string"}
                    },
                    "required": ["location", "issue"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "semantic_search_signals",
                "description": "Perform genuine semantic retrieval over 311 records using Mistral embeddings. Finds concepts where keywords don't match.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The semantic concept to search for, e.g. 'problems caused when commuters suddenly move onto streets'"},
                        "location": {"type": "string", "description": "Optional location filter"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "verify_hypothesis",
                "description": "Search Elasticsearch for evidence supporting or contradicting a specific ripple effect hypothesis.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "hypothesis": {"type": "string"},
                        "location": {"type": "string"}
                    },
                    "required": ["hypothesis", "location"]
                }
            }
        }
    ]

    messages = [
        {
            "role": "system",
            "content": (
                "You are NYC Pulse, an evidence-driven urban intelligence agent. "
                "Investigate likely SECOND-ORDER and THIRD-ORDER ripple effects of city disruptions.\n\n"
                "CRITICAL RULES:\n"
                "1. NEVER present a statistic, historical event, evidence count, dataset, percentage, or factual supporting claim unless that information was EXACTLY returned from an Elasticsearch tool call.\n"
                "2. If Elasticsearch does not contain specific data (e.g. Uber, Citi Bike, DOT cameras, sales data), DO NOT mention statistics for them. If you hypothesize about them, explicitly label it 'AI HYPOTHESIS - insufficient Elastic evidence'.\n"
                "3. You must separate your HYPOTHESIS from the ELASTIC EVIDENCE.\n"
                "4. Return ONLY the top 3 strongest ripple effects that have the best Elasticsearch evidence.\n"
                "5. CAUSALITY SAFETY: 311 contextual records do NOT prove causality from a subway disruption. Never use phrases like 'evidence confirms this will happen' or 'strong evidence proves' unless records explicitly connect the event to the outcome. Instead use: 'historical/contextual signals support this hypothesis', 'Elastic found signals consistent with this possibility', 'evidence is indirect', or 'insufficient direct evidence'.\n"
                "6. CONFIDENCE SCORING: HIGH confidence is allowed ONLY when retrieved evidence directly supports the relationship being claimed. If evidence is indirect/contextual, maximum confidence must be MEDIUM. If retrieved results contain substantial irrelevant matches, confidence must be LOW or MEDIUM. Elasticsearch result count alone must NEVER increase confidence; relevance and directness matter more than quantity."
            )
        },
        {
            "role": "user",
            "content": f"Investigate this disruption and determine the ripple effects: {event_description}"
        }
    ]

    trace = []
    metrics = {
        "tool_calls": 0,
        "hypotheses_verified": 0,
        "records_searched": 0
    }
    
    trace.append({"step": "Mistral analyzed disruption", "details": event_description})

    # First turn: Agent investigates and calls tools
    response = client.chat.complete(
        model="mistral-large-latest",
        messages=messages,
        tools=tools
    )
    
    messages.append(response.choices[0].message)
    trace.append({"step": "Mistral formed initial hypotheses", "details": "Planning evidence gathering"})

    # Execute tools (Evidence Loop)
    while response.choices[0].message.tool_calls:
        tool_calls = response.choices[0].message.tool_calls
        for tool_call in tool_calls:
            metrics["tool_calls"] += 1
            fn_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            step_name = "Elastic search"
            if fn_name == "get_transit_context": step_name = "Elastic geo search"
            elif fn_name == "search_historical_impacts": step_name = "Elastic BM25 historical search"
            elif fn_name == "semantic_search_signals": step_name = "Elastic + Mistral semantic search"
            elif fn_name == "verify_hypothesis": 
                step_name = "Elastic Evidence Loop verification"
                metrics["hypotheses_verified"] += 1
            
            trace.append({"step": step_name, "tool": fn_name, "args": args})
            
            if fn_name in TOOLS_MAP:
                result = TOOLS_MAP[fn_name](**args)
                # extract counts
                if "Found " in result and " historical" in result:
                    try: metrics["records_searched"] += int(result.split("Found ")[1].split(" ")[0])
                    except: pass
                if "Found " in result and " semantic" in result:
                    try: metrics["records_searched"] += int(result.split("Found ")[1].split(" ")[0])
                    except: pass
            else:
                result = "Error: Tool not found."
                
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": fn_name,
                "content": result
            })
            
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=messages,
            tools=tools
        )
        messages.append(response.choices[0].message)

    trace.append({"step": "Final evidence-backed assessment", "details": "Generating structured output"})

    # Request structured output
    schema_prompt = (
        "Based on the evidence gathered, provide the final structured output in JSON format. "
        "It must exactly match this structure:\n"
        "{\n"
        "  \"event\": {\"summary\": \"...\", \"location\": \"...\", \"routes\": []},\n"
        "  \"affected_areas\": [\"...\"],\n"
        "  \"ripple_effects\": [\n"
        "    {\n"
        "      \"hypothesis\": \"...\",\n"
        "      \"elastic_verification_query\": \"The exact terms you used to verify this\",\n"
        "      \"elastic_evidence_count\": 0,\n"
        "      \"supporting_signals\": [\"Exact quote or data point from Elastic\", ...],\n"
        "      \"contradicting_insufficient_signals\": \"...\",\n"
        "      \"confidence\": \"LOW/MEDIUM/HIGH\",\n"
        "      \"final_assessment\": \"...\"\n"
        "    }\n"
        "  ],\n"
        "  \"recommended_monitoring\": [{\"metric\": \"...\", \"why\": \"...\"}],\n"
        "  \"recommended_actions\": [{\"action\": \"...\", \"why\": \"...\"}]\n"
        "}\n\n"
        "Remember:\n"
        "- MAX 3 ripple effects.\n"
        "- NO hallucinated numbers. Everything in supporting_signals MUST come exactly from the tool outputs.\n"
        "- If no evidence exists for a claim, explicitly say 'AI HYPOTHESIS - insufficient Elastic evidence'.\n"
        "- CAUSALITY: Use safe language ('historical signals support this', 'evidence is indirect'). DO NOT claim 311 data proves causality.\n"
        "- CONFIDENCE: HIGH only if directly supported. Indirect evidence maxes out at MEDIUM.\n"
    )
    
    messages.append({
        "role": "user",
        "content": schema_prompt
    })
    
    final_response = client.chat.complete(
        model="mistral-large-latest",
        messages=messages,
        response_format={"type": "json_object"}
    )
    
    json_data = json.loads(final_response.choices[0].message.content)
    
    es = get_es_client()
    stats = {}
    if es:
        try:
            stats['mta'] = es.count(index='mta_subway_stops')['count']
            stats['311'] = es.count(index='nyc_311_requests')['count']
            stats['311_semantic'] = es.count(index='nyc_311_semantic')['count']
        except:
            pass
            
    metrics["total_indexed"] = stats
    
    return {
        "report": json_data,
        "trace": trace,
        "metrics": metrics
    }

if __name__ == "__main__":
    res = run_evidence_loop("A major L train disruption happens at Bedford Avenue during evening rush hour. What happens next?")
    print(json.dumps(res, indent=2))
