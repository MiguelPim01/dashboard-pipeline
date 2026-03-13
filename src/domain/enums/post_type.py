from __future__ import annotations

from enum import Enum


class PostTypeEnum(str, Enum):
    GOV = "GOV"
    PRESS = "PRESS"
    DEFAULT = "DEFAULT"
