import ast
import re
from math import sin, cos, atan2, radians, sqrt, asin, degrees

def coords_to_wkt_linestring(coord_str):
    """Преобразует список координат в WKT LINESTRING"""
    try:
        points = ast.literal_eval(coord_str)
        if not points or len(points) < 3:
            return None
        
        # Меняем порядок (lat, lon) -> (lon lat)
        wkt_points = ','.join(f"{lon} {lat}" for lat, lon in points)
        return f"LINESTRING({wkt_points})"
    except:
        return None

def wkt_linestring_to_coords(wkt_str):
    """Преобразует WKT LINESTRING в список координат (lat, lon)"""

    try:
        if not wkt_str or not isinstance(wkt_str, str):
            return None
        
        # Проверяем, что это LINESTRING
        if not wkt_str.strip().upper().startswith('LINESTRING'):
            return None
        
        # Извлекаем содержимое между скобками
        match = re.search(r'LINESTRING\s*\((.*?)\)', wkt_str, re.IGNORECASE)
        if not match:
            return None
        
        coords_text = match.group(1)
        if not coords_text.strip():
            return None
        
        points = []
        # Разбиваем на пары координат
        for pair in coords_text.split(','):
            pair = pair.strip()
            if not pair:
                continue
            
            parts = pair.split()
            if len(parts) != 2:
                return None
            
            lon, lat = float(parts[0]), float(parts[1])
            points.append([lat, lon])  # Меняем обратно (lon, lat) -> (lat, lon)
        
        # Возвращаем None если меньше 3 точек
        if len(points) < 3:
            return None
        
        return points
        
    except:
        return None
    
def haversine(coord1, coord2):
    """
    Вычисление расстояния между двумя географическими точками в метрах (не используется в текущей реализации)
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    R = 6371000  # Радиус Земли в метрах

    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c


# Вычисление азимута - направление из одной координаты в другую (угол между направлением на север и вектором)
def azimuth(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1

    x = sin(dlon) * cos(lat2)
    y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
    azimuth_rad = atan2(x, y)
    
    return (degrees(azimuth_rad) + 360) % 360


# Вычисление обратного азимута
def back_azimuth(azimuth):
    return (azimuth + 180) % 360


def next_geo_coords(coords, d, theta):
    R = 6371000

    lat1 = radians(coords[0])
    lon1 = radians(coords[1])

    delta = d / R

    lat2 = asin(
        sin(lat1) * cos(delta) +
        cos(lat1) * sin(delta) * cos(theta)
    )

    lon2 = lon1 + atan2(
        sin(theta) * sin(delta) * cos(lat1),
        cos(delta) - sin(lat1) * sin(lat2)
    )

    return [degrees(lat2), degrees(lon2)]