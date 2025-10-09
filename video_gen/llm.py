from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError


class ChartSeries(BaseModel):
    name: str
    values: list[float]


class ChartSpec(BaseModel):
    chart_type: str = Field(description="bar or line")
    title: str
    x_labels: list[str]
    series: list[ChartSeries]


class FlowchartSpec(BaseModel):
    title: str
    steps: list[str]


class Section(BaseModel):
    title: str
    bullets: list[str]
    flowchart: Optional[FlowchartSpec] = None
    charts: Optional[list[ChartSpec]] = None


class Plan(BaseModel):
    topic: str
    sections: list[Section]


def _clean_json(s: str) -> str:
    # Extract JSON block if surrounded by backticks or text
    code_block = re.search(r"```(?:json)?\n([\s\S]*?)\n```", s)
    if code_block:
        return code_block.group(1)
    # Fallback: try to find first { ... } balanced-ish
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return s[start : end + 1]
    return s


def structure_content(
    topic: Optional[str] = None,
    raw_text: Optional[str] = None,
    use_mock: bool = False,
) -> Plan:
    """
    Produce a structured plan (sections, bullets, optional flowcharts and charts).
    If `use_mock` or GEMINI is unavailable, returns a deterministic mock plan.
    """
    if use_mock:
        return _mock_plan(topic=topic or "Untitled Topic", raw_text=raw_text)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _mock_plan(topic=topic or "Untitled Topic", raw_text=raw_text)

    try:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Trim raw_text to avoid very long prompts
        trimmed_text = (raw_text or "").strip()
        if len(trimmed_text) > 12000:
            trimmed_text = trimmed_text[:12000] + "\n...[truncated]"

        system_instruction = (
            "You are a teaching assistant. Given a topic and optional source text, "
            "produce a JSON object with a clear outline for an educational video. "
            "Use compact bullets. Include at most one flowchart per section when helpful, "
            "and 0-2 simple charts per section when data is present or can be exemplified. "
            "Return ONLY valid minified JSON matching the schema."
        )

        schema_hint = {
            "topic": "string",
            "sections": [
                {
                    "title": "string",
                    "bullets": ["string", "string"],
                    "flowchart": {"title": "string", "steps": ["string", "string"]},
                    "charts": [
                        {
                            "chart_type": "bar|line",
                            "title": "string",
                            "x_labels": ["x1", "x2"],
                            "series": [{"name": "Series A", "values": [1, 2]}],
                        }
                    ],
                }
            ],
        }

        user_prompt = (
            f"TOPIC: {topic or 'N/A'}\n\n"
            f"SOURCE_TEXT:\n{trimmed_text}\n\n"
            f"SCHEMA_EXAMPLE (shape only):\n{json.dumps(schema_hint)}\n"
            "Respond with JSON only."
        )

        response = model.generate_content([
            {"role": "system", "parts": [system_instruction]},
            {"role": "user", "parts": [user_prompt]},
        ])

        raw = getattr(response, "text", None) or "".join(p.text for p in getattr(response, "parts", []) if hasattr(p, "text"))
        raw_json = _clean_json(raw)
        data = json.loads(raw_json)
        plan = Plan.model_validate(data)
        return plan
    except Exception:
        return _mock_plan(topic=topic or "Untitled Topic", raw_text=raw_text)


def _mock_plan(topic: str, raw_text: Optional[str]) -> Plan:
    text = (raw_text or "").strip()
    # naive sentence split
    sentences = re.split(r"(?<=[.!?])\s+", text) if text else []

    def bullets_from_sentences(start: int, count: int) -> list[str]:
        return [s.strip() for s in sentences[start : start + count] if s.strip()][:4]

    sections: list[Section] = []
    sections.append(
        Section(
            title=f"Introduction to {topic}",
            bullets=(
                bullets_from_sentences(0, 4)
                or [
                    f"Overview of {topic} and its importance",
                    "Key definitions and core idea",
                    "Real-world context",
                ]
            ),
            flowchart=FlowchartSpec(
                title="High-level flow",
                steps=["Start", topic, "Key Step", "Result", "End"],
            ),
        )
    )

    sections.append(
        Section(
            title="Process and Components",
            bullets=(
                bullets_from_sentences(4, 4)
                or [
                    "Break down the process into stages",
                    "Introduce main components",
                    "Explain interactions",
                ]
            ),
            charts=[
                ChartSpec(
                    chart_type="bar",
                    title="Example Comparison",
                    x_labels=["A", "B", "C", "D"],
                    series=[
                        ChartSeries(name="Metric", values=[3, 5, 2, 4])
                    ],
                )
            ],
        )
    )

    sections.append(
        Section(
            title="Applications and Summary",
            bullets=(
                bullets_from_sentences(8, 4)
                or [
                    "Common applications",
                    "Benefits and trade-offs",
                    "Summary and next steps",
                ]
            ),
        )
    )

    return Plan(topic=topic, sections=sections)
