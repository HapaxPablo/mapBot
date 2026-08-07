import math

from django.db.models import Q


def parse_bounds(value):
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(',')]
        if len(parts) != 4:
            return None
        value = dict(zip(('west', 'south', 'east', 'north'), parts))

    if not isinstance(value, dict):
        return None
    try:
        west = float(value['west'])
        south = float(value['south'])
        east = float(value['east'])
        north = float(value['north'])
    except (KeyError, TypeError, ValueError):
        return None
    if not all(math.isfinite(item) for item in (west, south, east, north)):
        return None
    if not (-180 <= west <= 180 and -180 <= east <= 180):
        return None
    if not (-90 <= south <= 90 and -90 <= north <= 90) or south > north:
        return None
    return {'west': west, 'south': south, 'east': east, 'north': north}


def filter_by_bounds(queryset, bounds):
    queryset = queryset.filter(
        lat__gte=bounds['south'],
        lat__lte=bounds['north'],
    )
    if bounds['west'] <= bounds['east']:
        return queryset.filter(
            lng__gte=bounds['west'],
            lng__lte=bounds['east'],
        )
    return queryset.filter(
        Q(lng__gte=bounds['west']) | Q(lng__lte=bounds['east']),
    )
