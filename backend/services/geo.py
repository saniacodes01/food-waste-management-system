"""Geospatial helpers built on PostGIS Geography columns.

Distances are in metres (Geography semantics). Callers pass km and we convert.
"""
from typing import Optional
from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_Distance, ST_DWithin


def make_point(lat: Optional[float], lng: Optional[float]):
    """Build a value assignable to a Geography('POINT') column, or None."""
    if lat is None or lng is None:
        return None
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def distance_m(column, lat: float, lng: float):
    """SQL expression: metres between `column` and the given point."""
    return ST_Distance(column, make_point(lat, lng))


def within(column, lat: float, lng: float, radius_km: float):
    """SQL predicate: `column` is within radius_km of the given point."""
    return ST_DWithin(column, make_point(lat, lng), radius_km * 1000.0)
