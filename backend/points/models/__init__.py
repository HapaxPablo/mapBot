"""Компонент серверной части GeoMap."""

from .point import Point, photo_path
from .point_type import PointType
from .point_vote import PointVote

__all__ = ('Point', 'PointType', 'PointVote', 'photo_path')
