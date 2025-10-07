from __future__ import annotations
import json
import math
import os
import re
from typing import Any, Dict, List

from pydantic import ValidationError

from .config import CONFIG
from .models import (
    ProjectSpec,
    SceneSpec,
    VisualSpec,
    FlowchartSpec,
    FlowchartEdge,
    GraphSpec,
    GraphSeries,
)


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _chunk_text(text: str, max_chars: int = 4000) -> List[str]:
    text = text.replace("\r\n", "\n")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) <= max_chars:
                current = para
            else:
                # Hard split long paragraphs
                for i in range(0, len(para), max_chars):
                    chunks.append(para[i : i + max_chars])
                current = ""
    if current:
        chunks.append(current)
    return chunks


def summarize_with_gemini(topic: str, text: str) -> ProjectSpec:
    import google.generativeai as genai

    if not CONFIG.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    genai.configure(api_key=CONFIG.gemini_api_key)

    schema = {
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "summary": {"type": "string"},
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "bullets": {"type": "array", "items": {"type": "string"}},
                        "narration": {"type": "string"},
                        "visuals": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "kind": {"type": "string"},
                                    "flowchart": {
                                        "type": ["object", "null"],
                                        "properties": {
                                            "title": {"type": ["string", "null"]},
                                            "nodes": {"type": "array", "items": {"type": "string"}},
                                            "edges": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "source": {"type": "string"},
                                                        "target": {"type": "string"},
                                                        "label": {"type": ["string", "null"]},
                                                    },
                                                    "required": ["source", "target"],
                                                },
                                            },
                                        },
                                        "required": ["nodes", "edges"],
                                    },
                                    "graph": {
                                        "type": ["object", "null"],
                                        "properties": {
                                            "title": {"type": ["string", "null"]},
                                            "type": {"type": "string"},
                                            "x_label": {"type": ["string", "null"]},
                                            "y_label": {"type": ["string", "null"]},
                                            "series": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "name": {"type": "string"},
                                                        "x": {
                                                            "type": "array",
                                                            "items": {"type": ["string", "number"]},
                                                        },
                                                        "y": {
                                                            "type": "array",
                                                            "items": {"type": ["number"]},
                                                        },
                                                    },
                                                    "required": ["name", "x", "y"],
                                                },
                                            },
                                        },
                                        "required": ["type", "series"],
                                    },
                                },
                                "required": ["kind"],
                            },
                        },
                    },
                    "required": ["title", "narration"],
                },
            },
        },
        "required": ["topic", "summary", "scenes"],
    }

    sys_prompt = (
        "You are an expert instructional designer. Summarize and structure the content into a small number of scenes (3-7). "
        "Each scene includes: a short title, 3-6 bullets of key points, a concise narration (120-220 words), and zero or more visuals. "
        "Visuals can be a flowchart (nodes and edges) or a graph (bar/line/pie/scatter) with one or more series. "
        "Keep data small (<= 8 points/labels per series). Return ONLY JSON matching the provided schema."
    )

    user_prompt = (
        f"Topic: {topic}\n\n"
        f"Content to structure:\n{text[:10000]}\n\n"
        "Output schema (JSON):\n" + json.dumps(schema)
    )

    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(
        sys_prompt + "\n\n" + user_prompt,
        generation_config={
            "temperature": 0.2,
            "max_output_tokens": 4096,
            "response_mime_type": "application/json",
        },
    )

    raw = response.text
    data = json.loads(raw)

    # Validate via Pydantic
    try:
        scenes: List[SceneSpec] = []
        for s in data["scenes"]:
            visuals: List[VisualSpec] = []
            for v in s.get("visuals", []):
                if v.get("kind") == "flowchart" and v.get("flowchart"):
                    fc = v["flowchart"]
                    edges = [FlowchartEdge(**e) for e in fc.get("edges", [])]
                    visuals.append(VisualSpec(kind="flowchart", flowchart=FlowchartSpec(title=fc.get("title"), nodes=fc.get("nodes", []), edges=edges)))
                elif v.get("kind") == "graph" and v.get("graph"):
                    g = v["graph"]
                    series = [GraphSeries(**srs) for srs in g.get("series", [])]
                    visuals.append(VisualSpec(kind="graph", graph=GraphSpec(title=g.get("title"), type=g.get("type", "bar"), x_label=g.get("x_label"), y_label=g.get("y_label"), series=series)))
            scenes.append(
                SceneSpec(
                    title=s["title"],
                    bullets=s.get("bullets", []),
                    narration=s["narration"],
                    visuals=visuals,
                )
            )
        return ProjectSpec(topic=data["topic"], summary=data["summary"], scenes=scenes)
    except (KeyError, ValidationError, TypeError) as e:
        raise RuntimeError(f"Gemini returned invalid structure: {e}\nRaw: {raw[:800]}")


def summarize_offline(topic: str, text: str) -> ProjectSpec:
    text = _clean_text(text)
    if not text:
        return ProjectSpec(topic=topic, summary="", scenes=[])

    words = text.split()
    approx_scene_count = max(3, min(7, len(words) // 180))
    chunks = _chunk_text(text, max_chars=max(500, len(text) // approx_scene_count))
    chunks = chunks[:7]

    scenes: List[SceneSpec] = []
    for i, chunk in enumerate(chunks, start=1):
        sentences = re.split(r"(?<=[.!?])\s+", chunk)
        bullets = [s.strip() for s in sentences[:5] if len(s.strip()) > 0][:5]
        narration = chunk[:1800]

        visuals: List[VisualSpec] = []
        # Simple flowchart: sequence of first few phrases
        phrases = [re.sub(r"[^a-zA-Z0-9 ]", "", s).strip() for s in sentences[:5]]
        phrases = [p for p in phrases if len(p.split()) >= 2][:5]
        if len(phrases) >= 3:
            nodes = [f"Step {j+1}: {phrases[j][:40]}" for j in range(min(4, len(phrases)))]
            edges = [FlowchartEdge(source=nodes[j], target=nodes[j+1]) for j in range(len(nodes) - 1)]
            visuals.append(VisualSpec(kind="flowchart", flowchart=FlowchartSpec(title=f"Flow Overview {i}", nodes=nodes, edges=edges)))

        # Simple graph: keyword frequency of top 6 nouns-like tokens
        tokens = re.findall(r"[a-zA-Z]{4,}", chunk.lower())
        freq: Dict[str, int] = {}
        for t in tokens:
            if t in {"this", "that", "with", "from", "which", "into", "have", "will", "they", "them", "then", "there", "their"}:
                continue
            freq[t] = freq.get(t, 0) + 1
        top = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:6]
        if top:
            series = [GraphSeries(name="frequency", x=[k for k, _ in top], y=[v for _, v in top])]
            visuals.append(VisualSpec(kind="graph", graph=GraphSpec(title=f"Top Terms {i}", type="bar", x_label="term", y_label="count", series=series)))

        scenes.append(
            SceneSpec(
                title=f"Section {i}",
                bullets=bullets[:5],
                narration=narration,
                visuals=visuals,
            )
        )

    summary = " ".join(words[:120])
    return ProjectSpec(topic=topic, summary=summary, scenes=scenes)


def summarize(topic: str, text: str, provider: str | None = None) -> ProjectSpec:
    provider = (provider or ("gemini" if CONFIG.gemini_api_key else "offline")).lower()
    if provider == "gemini":
        return summarize_with_gemini(topic, text)
    return summarize_offline(topic, text)
