import pandas as pd
import csv
import time
import requests
import ast
from math import radians, sin, cos, sqrt, atan2

route_cache = {}
matrix_cache = {}
CACHE_ENABLED = False

def get_route_valhalla(start_coords, end_coords, max_retries=3):
    """
    Получение маршрута через Valhalla API (не используется в текущей реализации)
    """
    cache_key = f"{start_coords}_{end_coords}" if CACHE_ENABLED else None

    if CACHE_ENABLED and cache_key in route_cache:
        return route_cache[cache_key]

    url = "https://valhalla1.openstreetmap.de/route"

    body = {
        "locations": [
            {"lat": start_coords[0], "lon": start_coords[1]},
            {"lat": end_coords[0], "lon": end_coords[1]}
        ],
        "costing": "pedestrian",
        "directions_options": {"units": "kilometers"}
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=body, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if 'trip' in data:
                    route = data['trip']
                    leg = route['legs'][0]

                    result = {
                        'distance': leg['summary']['length'] * 1000,  # meters
                        'duration': leg['summary']['time'],  # seconds
                        'geometry': leg['shape']
                    }

                    if CACHE_ENABLED:
                        route_cache[cache_key] = result

                    return result

        except Exception:
            pass

        if attempt < max_retries - 1:
            time.sleep(1)

    return None


def get_valhalla_matrix(sources, targets, max_retries=3):
    """
    Matrix-запрос к Valhalla.
    sources: список кортежей (lat, lon)
    targets: список кортежей (lat, lon)
    Возвращает список списков расстояний в метрах: distances[i][j] – от source i до target j.
    Для нашего случая обычно один источник и много целей, поэтому вернём плоский список для первого источника.
    """
    if not sources or not targets:
        return []

    cache_key = None
    if CACHE_ENABLED:
        cache_key = (sources[0], tuple(targets))
        if cache_key in matrix_cache:
            return matrix_cache[cache_key]

    url = "https://valhalla1.openstreetmap.de/sources_to_targets"  # матричный эндпоинт

    # Формируем тела запроса: источники и цели
    payload = {
        "sources": [{"lat": lat, "lon": lon} for (lat, lon) in sources],
        "targets": [{"lat": lat, "lon": lon} for (lat, lon) in targets],
        "costing": "pedestrian"
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=30)  # матрица может дольше считаться
            if response.status_code == 200:
                data = response.json()
                # Ожидаемая структура: data['sources_to_targets'][i][j]['distance']
                distances = []
                for i, row in enumerate(data.get('sources_to_targets', [])):
                    dist_row = []
                    for j, cell in enumerate(row):
                        if cell and 'distance' in cell:
                            dist_row.append(cell['distance'] * 1000)  # км -> м
                        else:
                            dist_row.append(None)
                    distances.append(dist_row)

                result = distances[0] if distances else [None] * len(targets)
                if CACHE_ENABLED:
                    matrix_cache[cache_key] = result
                return result
        except Exception:
            pass
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # экспоненциальная задержка
    return [None] * len(targets)