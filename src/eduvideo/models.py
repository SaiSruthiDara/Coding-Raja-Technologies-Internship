from __future__ import annotations
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class FlowchartEdge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None


class FlowchartSpec(BaseModel):
    title: Optional[str] = None
    nodes: List[str] = Field(default_factory=list)
    edges: List[FlowchartEdge] = Field(default_factory=list)


class GraphSeries(BaseModel):
    name: str
    x: List[float | int | str]
    y: List[float | int]


class GraphSpec(BaseModel):
    title: Optional[str] = None
    type: Literal["bar", "line", "pie", "scatter"] = "bar"
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    series: List[GraphSeries] = Field(default_factory=list)


class VisualSpec(BaseModel):
    kind: Literal["flowchart", "graph"]
    flowchart: Optional[FlowchartSpec] = None
    graph: Optional[GraphSpec] = None


class SceneSpec(BaseModel):
    title: str
    bullets: List[str] = Field(default_factory=list)
    narration: str
    visuals: List[VisualSpec] = Field(default_factory=list)


class ProjectSpec(BaseModel):
    topic: str
    summary: str
    scenes: List[SceneSpec]

    @classmethod
    def minimal(cls, topic: str, text: str) -> "ProjectSpec":
        return cls(topic=topic, summary=text[:280], scenes=[])
