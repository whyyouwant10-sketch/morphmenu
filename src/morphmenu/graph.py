"""The small directed conversion graph used by v0.1 planning."""

from __future__ import annotations

from collections import deque

from .model import ConversionEdge


STRUCTURED = ("json", "yaml", "csv")


def conversion_edges() -> tuple[ConversionEdge, ...]:
    edges: list[ConversionEdge] = []
    for source in STRUCTURED:
        for target in STRUCTURED:
            if source != target:
                edges.append(ConversionEdge(source, target, "builtin", cost=1))
        edges.append(ConversionEdge(source, "text", "builtin"))
        edges.append(ConversionEdge(source, "markdown", "builtin"))
    edges.extend(
        [
            ConversionEdge("text", "json", "builtin"),
            ConversionEdge("text", "yaml", "builtin"),
            ConversionEdge("text", "csv", "builtin"),
            ConversionEdge("text", "markdown", "builtin"),
            ConversionEdge("markdown", "text", "builtin", lossy=True),
            ConversionEdge("markdown", "json", "builtin", lossy=True),
            ConversionEdge("markdown", "yaml", "builtin", lossy=True),
            ConversionEdge("markdown", "csv", "builtin", lossy=True),
        ]
    )
    image_formats = ("png", "jpeg", "webp")
    for source in image_formats:
        for target in image_formats:
            if source != target:
                edges.append(ConversionEdge(source, target, "ImageMagick", required_capability="imagemagick"))
    audio_formats = ("wav", "mp3", "flac")
    for source in audio_formats:
        for target in audio_formats:
            if source != target:
                edges.append(ConversionEdge(source, target, "FFmpeg", required_capability="ffmpeg"))
    for source, target in (("mp4", "webm"), ("webm", "mp4")):
        edges.append(ConversionEdge(source, target, "FFmpeg", required_capability="ffmpeg", lossy=True))
    return tuple(edges)


EDGES = conversion_edges()


def find_route(source: str, target: str) -> tuple[ConversionEdge, ...] | None:
    if source == target:
        return ()
    queue = deque([(source, ())])
    visited = {source}
    adjacency: dict[str, list[ConversionEdge]] = {}
    for edge in EDGES:
        adjacency.setdefault(edge.source, []).append(edge)
    for values in adjacency.values():
        values.sort(key=lambda edge: (edge.cost, edge.lossy, edge.adapter, edge.target))
    while queue:
        current, route = queue.popleft()
        for edge in adjacency.get(current, []):
            if edge.target in visited:
                continue
            new_route = route + (edge,)
            if edge.target == target:
                return new_route
            visited.add(edge.target)
            queue.append((edge.target, new_route))
    return None
