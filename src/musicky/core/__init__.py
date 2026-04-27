"""Core data model: signal-flow nodes, piece wrapper, timeline helpers, renderer."""

from musicky.core.automation import Automation, auto, evaluate
from musicky.core.node import Clip, Effect, Instrument, Mix, Node, clip
from musicky.core.piece import Piece, musicky
from musicky.core.render import Voice, flatten, render_audio, synthesize
from musicky.core.timeline import length, seq

__all__ = [
    "Automation",
    "Clip",
    "Effect",
    "Instrument",
    "Mix",
    "Node",
    "Piece",
    "Voice",
    "auto",
    "clip",
    "evaluate",
    "flatten",
    "length",
    "musicky",
    "render_audio",
    "seq",
    "synthesize",
]
