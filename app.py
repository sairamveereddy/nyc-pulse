import streamlit as st
import json
from agent import run_evidence_loop

st.set_page_config(page_title="NYC Pulse | Urban Intelligence", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
/* Base Variables & Theme */
:root {
    --ivory: #F7F6F2;
    --charcoal: #171923;
    --cobalt: #485CFF;
    --acid: #C7F36B;
    --lavender: #EAE7FF;
    --white: #FFFFFF;
}

/* App Backgrounds */
[data-testid="stAppViewContainer"] {
    background-color: #F7F6F2;
    color: #171923;
    font-family: 'Inter', -apple-system, sans-serif;
}
[data-testid="stSidebar"] {
    background-color: #FFFFFF;
    border-right: 1px solid #E5E5E5;
}
[data-testid="stHeader"] {
    background: transparent;
}
.block-container {
    padding-top: 1rem;
    max-width: 1200px;
}

/* Typography Overrides */
h1, h2, h3, h4, h5, p, span, div {
    color: #171923;
}

/* Buttons */
.stButton > button {
    background-color: #485CFF !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 4px !important;
    padding: 8px 24px !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    background-color: #C7F36B !important;
    color: #171923 !important;
}

/* Input Fields */
.stTextInput input {
    background-color: #FFFFFF !important;
    border: 1px solid #E5E5E5 !important;
    color: #171923 !important;
    border-radius: 4px !important;
    padding: 12px 16px !important;
    font-size: 1rem !important;
    box-shadow: none !important;
}
.stTextInput input:focus {
    border-color: #485CFF !important;
}

/* Chips (Secondary Buttons) */
.chip-btn .stButton > button {
    background-color: #FFFFFF !important;
    color: #171923 !important;
    border: 1px solid #E5E5E5 !important;
    font-size: 0.85rem !important;
    padding: 4px 16px !important;
}
.chip-btn .stButton > button:hover {
    background-color: #EAE7FF !important;
    border-color: #485CFF !important;
}

/* Custom Components */
.eyebrow {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #485CFF;
    margin-bottom: 8px;
}
.hero-title {
    font-size: 3rem;
    font-weight: 800;
    line-height: 1.1;
    margin-bottom: 12px;
    color: #171923;
    letter-spacing: -0.02em;
}
.hero-sub {
    font-size: 1.1rem;
    color: #555555;
    margin-bottom: 32px;
    max-width: 600px;
}

/* Cards */
.info-card {
    background: #FFFFFF;
    border: 1px solid #E5E5E5;
    border-radius: 6px;
    padding: 24px;
    margin-bottom: 16px;
    transition: box-shadow 0.15s ease;
}
.info-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}

.pill {
    background: #EAE7FF;
    color: #485CFF;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
}
.pill.high { background: #C7F36B; color: #171923; }
.pill.low { background: #FDE8E8; color: #9B1C1C; }

/* Timeline */
.timeline {
    border-left: 2px solid #EAE7FF;
    margin-left: 10px;
    padding-left: 24px;
}
.timeline-item {
    position: relative;
    margin-bottom: 24px;
    font-size: 0.9rem;
    color: #171923;
}
.timeline-dot {
    position: absolute;
    left: -29px;
    top: 4px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
}
.dot-mistral { background: #485CFF; }
.dot-elastic { background: #FFFFFF; border: 2px solid #485CFF; }
.dot-semantic { background: #C7F36B; border: 2px solid #171923; }
.dot-evidence { background: #171923; }
.dot-done { background: #485CFF; }

.timeline-title {
    font-weight: 600;
    margin-bottom: 4px;
}
.timeline-meta {
    font-size: 0.8rem;
    color: #666;
    font-family: monospace;
}

hr {
    border-color: #E5E5E5;
    margin: 32px 0;
}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:8px; margin-bottom: 40px;">
        <div style="width:16px; height:16px; background:#485CFF; border-radius:2px;"></div>
        <div style="font-weight:800; font-size:1.1rem; letter-spacing: -0.5px;">NYC PULSE</div>
    </div>
    <div style="font-size: 0.85rem; font-weight:600; margin-bottom: 12px; color:#555;">NAVIGATION</div>
    <div style="font-size: 0.95rem; margin-bottom: 12px; font-weight: 500; color:#485CFF;">Investigate</div>
    <div style="font-size: 0.95rem; margin-bottom: 12px; color:#171923;">Data Sources</div>
    <div style="font-size: 0.95rem; margin-bottom: 40px; color:#171923;">System</div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background:#F7F6F2; padding: 16px; border-radius: 6px; border: 1px solid #E5E5E5;">
        <div style="font-size:0.75rem; font-weight:700; color:#555; margin-bottom:4px;">INDEXED DOCUMENTS</div>
        <div style="font-size:1.5rem; font-weight:800; color:#171923;">21,488</div>
        <div style="font-size:0.75rem; color:#666; margin-top:4px;">Live Elastic Cluster</div>
    </div>
    """, unsafe_allow_html=True)

# --- TOP BAR ---
st.markdown("""
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 48px; border-bottom: 1px solid #E5E5E5; padding-bottom: 16px;">
    <div style="font-size:0.85rem; color:#555;">Intelligence / <span style="color:#171923; font-weight:500;">Investigation</span></div>
    <div style="font-size:0.75rem; background:#EAE7FF; color:#485CFF; padding:4px 12px; border-radius:12px; font-weight:600;">ELASTIC + MISTRAL · READY</div>
</div>
""", unsafe_allow_html=True)

# --- MAIN HERO ---
st.markdown('<div class="eyebrow">URBAN INTELLIGENCE</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">Understand the city\'s next move.</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Investigate how one disruption creates ripple effects across New York.</div>', unsafe_allow_html=True)

# Scenario State Management
if "scenario_query" not in st.session_state:
    st.session_state.scenario_query = "A major L train disruption happens at Bedford Avenue during evening rush hour."

def set_query(q):
    st.session_state.scenario_query = q

col_q, col_btn = st.columns([4, 1])
with col_q:
    query = st.text_input("Scenario", key="scenario_query", label_visibility="collapsed")
with col_btn:
    analyze = st.button("Analyze", use_container_width=True)

# Chips
c1, c2, c3 = st.columns([1,1,2])
with c1:
    st.markdown('<div class="chip-btn">', unsafe_allow_html=True)
    st.button("L Train Disruption", on_click=set_query, args=("A major L train disruption happens at Bedford Avenue during evening rush hour.",))
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="chip-btn">', unsafe_allow_html=True)
    st.button("Times Square Power Out", on_click=set_query, args=("A sudden power outage hits Times Square during Friday night Broadway hours.",))
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<hr style='margin: 40px 0;'>", unsafe_allow_html=True)

if analyze:
    with st.spinner("Investigating with Mistral & Elasticsearch..."):
        try:
            result = run_evidence_loop(query)
            
            if "error" in result:
                st.error(result["error"])
                st.stop()
                
            report = result["report"]
            trace = result["trace"]
            metrics = result["metrics"]
            
            # Compact Summary
            st.markdown(f"""
            <div style="display:flex; gap: 32px; margin-bottom: 40px; font-size: 0.9rem;">
                <div><span style="color:#666;">Event:</span> <strong>{report['event']['summary']}</strong></div>
                <div><span style="color:#666;">Verification:</span> <strong>{metrics.get('hypotheses_verified', 0)} hypotheses checked</strong></div>
                <div><span style="color:#666;">Tool Calls:</span> <strong>{metrics.get('tool_calls', 0)}</strong></div>
            </div>
            """, unsafe_allow_html=True)
            
            col_main, col_side = st.columns([68, 32], gap="large")
            
            with col_main:
                st.markdown("<div class='eyebrow' style='margin-bottom:24px;'>POTENTIAL RIPPLE EFFECTS</div>", unsafe_allow_html=True)
                
                for idx, effect in enumerate(report.get("ripple_effects", [])[:3]):
                    conf = effect.get("confidence", "UNKNOWN").upper()
                    conf_class = conf.lower()
                    
                    st.markdown(f"""
                    <div class="info-card">
                        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px;">
                            <span style="font-weight: 700; color: #485CFF; font-size: 0.9rem;">0{idx+1}</span>
                            <span class="pill {conf_class}">{conf} CONFIDENCE</span>
                        </div>
                        <h3 style="margin:0 0 12px 0; font-size: 1.1rem; line-height: 1.4;">{effect.get('hypothesis')}</h3>
                        <p style="margin:0 0 16px 0; font-size: 0.95rem; color: #555; line-height: 1.5;">{effect.get('final_assessment')}</p>
                    """, unsafe_allow_html=True)
                    
                    with st.expander("Evidence Details"):
                        st.markdown(f"**Verification Query:** `{effect.get('elastic_verification_query')}`")
                        st.markdown(f"**Elastic Evidence Count:** {effect.get('elastic_evidence_count')}")
                        st.markdown("**Contextual Signals:**")
                        for sig in effect.get("supporting_signals", []):
                            st.markdown(f"- {sig}")
                        st.markdown("**Contradicting / Insufficient Signals:**")
                        st.write(effect.get("contradicting_insufficient_signals", "None"))
                    
                    st.markdown("</div>", unsafe_allow_html=True)
            
            with col_side:
                st.markdown("<div class='eyebrow' style='margin-bottom:24px;'>INVESTIGATION ACTIVITY</div>", unsafe_allow_html=True)
                
                trace_html = '<div class="timeline">'
                for t in trace:
                    step = t['step']
                    step_lower = step.lower()
                    if 'mistral' in step_lower: dot = 'dot-mistral'
                    elif 'semantic' in step_lower: dot = 'dot-semantic'
                    elif 'elastic search' in step_lower or 'bm25' in step_lower or 'geo' in step_lower: dot = 'dot-elastic'
                    elif 'verif' in step_lower or 'evidence' in step_lower: dot = 'dot-evidence'
                    else: dot = 'dot-done'
                    
                    meta = ""
                    if 'args' in t:
                        if 'query' in t['args']: meta = f"<div class='timeline-meta'>Q: {t['args']['query'][:40]}...</div>"
                        elif 'location_name' in t['args']: meta = f"<div class='timeline-meta'>Loc: {t['args']['location_name']}</div>"
                        
                    trace_html += f"""
                    <div class="timeline-item">
                        <div class="timeline-dot {dot}"></div>
                        <div class="timeline-title">{step}</div>
                        {meta}
                    </div>
                    """
                trace_html += '</div>'
                st.markdown(trace_html, unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)
            
            # --- BOTTOM SECTION ---
            c_mon, c_act = st.columns(2, gap="large")
            
            with c_mon:
                st.markdown("<div class='eyebrow' style='margin-bottom:16px;'>WHAT TO MONITOR</div>", unsafe_allow_html=True)
                for rec in report.get("recommended_monitoring", []):
                    st.markdown(f"""
                    <div style="margin-bottom:16px;">
                        <div style="font-weight:600; font-size:0.95rem; margin-bottom:4px;">{rec.get('metric')}</div>
                        <div style="color:#555; font-size:0.9rem;">{rec.get('why')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
            with c_act:
                st.markdown("<div class='eyebrow' style='margin-bottom:16px;'>RECOMMENDED ACTIONS</div>", unsafe_allow_html=True)
                for act in report.get("recommended_actions", []):
                    st.markdown(f"""
                    <div style="margin-bottom:16px; border-left: 3px solid #485CFF; padding-left:16px;">
                        <div style="font-weight:600; font-size:0.95rem; margin-bottom:4px;">{act.get('action')}</div>
                        <div style="color:#555; font-size:0.9rem;">{act.get('why')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
            st.markdown("<br><br>", unsafe_allow_html=True)
            with st.expander("Technical Evidence & Architecture"):
                st.markdown("**Retrieval Method:** Hybrid — BM25 + Mistral Semantic Search")
                st.json(trace)
                st.json(metrics.get("total_indexed", {}))

        except Exception as e:
            st.error(f"An error occurred: {e}")
