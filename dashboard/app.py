"""Simple Streamlit dashboard for API monitoring."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List

import requests
import streamlit as st
from prometheus_client.parser import text_string_to_metric_families

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
REFRESH_INTERVAL = int(os.getenv("DASHBOARD_REFRESH_SECONDS", "15"))

st.set_page_config(page_title="Books API Monitoring", layout="wide")
st.title("📈 Books API – Monitoramento")
st.caption("Visualização em tempo real das métricas expostas pelo endpoint `/metrics`.")

@st.cache_data(ttl=REFRESH_INTERVAL)
def fetch_metrics() -> str:
    response = requests.get(f"{API_BASE_URL}/metrics", timeout=10)
    response.raise_for_status()
    return response.text


def parse_metrics(raw_metrics: str) -> Dict[str, List[Dict[str, float]]]:
    parsed: Dict[str, List[Dict[str, float]]] = {}
    for family in text_string_to_metric_families(raw_metrics):
        samples = []
        for sample in family.samples:
            row: Dict[str, float] = {"value": sample.value}
            for key, value in sample.labels.items():
                row[key] = value
            samples.append(row)
        parsed[family.name] = samples
    return parsed


with st.spinner("Atualizando métricas..."):
    raw_metrics = fetch_metrics()
    metrics = parse_metrics(raw_metrics)

st.success(f"Métricas atualizadas às {datetime.now().strftime('%H:%M:%S')} (UTC)")

summary_col, latency_col = st.columns(2)

with summary_col:
    st.subheader("Requisições por rota")
    request_metrics = metrics.get("http_requests_total", [])
    if request_metrics:
        st.table(request_metrics)
    else:
        st.info("Nenhuma métrica de requisição disponível ainda.")

with latency_col:
    st.subheader("Latência (p95 / p99)")
    latency_metrics = metrics.get("http_request_duration_seconds", [])
    if latency_metrics:
        st.table(latency_metrics)
    else:
        st.info("Latências ainda não calculadas – aguarde novas requisições.")

st.markdown("---")
st.subheader("Detalhes brutos do endpoint /metrics")
st.code(raw_metrics[:10_000], language="text")