import math
from db import conn
from geo_utils import wkt_linestring_to_coords, haversine, next_geo_coords, azimuth, back_azimuth
from typing import Dict


# Размещение панорам на участке дороге
def arrange_panoramas(road_id) -> Dict:
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT geom_curve
            FROM roads WHERE id = %s
        """, (road_id,))
        
        rows = cur.fetchall()
    
    geom_curve = rows[0][0]
    
    # test: geom_curve = 'LINESTRING(56.8047788 60.5412938,56.8050156 60.5412006,56.8052554 60.541155,56.8053215 60.5411524,56.8053578 60.5411615,56.8053895 60.5411652,56.8054874 60.5412046,56.8055933 60.5412569,56.8056955 60.5413348,56.8060505 60.5416102)'
    coords = wkt_linestring_to_coords(geom_curve)

    distance = 0

    for i in range(len(coords)-1):
        distance += haversine(coords[i], coords[i+1])
    
    # Количество панорам на участок дороги
    n = min(math.ceil(distance / 60), max(2, math.ceil(5 * math.sqrt(distance / 100))))

    # Расстояние между панорамами
    pDistance = round(distance / n, 3)

    way_params = []

    buffer = 0
    for i in range(len(coords)-1):

        segment_length = haversine(coords[i], coords[i+1])
        if buffer >= segment_length:
            buffer -= segment_length
            continue

        theta = math.radians(azimuth(coords[i][0], coords[i][1], 
                            coords[i+1][0], coords[i+1][1]))
        
        current_coords = next_geo_coords(coords[i], buffer, theta) if buffer != 0 else coords[i]
        iDistance = haversine(current_coords, coords[i+1])
        print(iDistance, haversine(coords[i], coords[i+1]))

        while iDistance > pDistance:

            if len(way_params) == 0:
                way_params.append({
                    'lat': current_coords[0],
                    'lon': current_coords[1],
                    'direction_deg': [math.degrees(theta)]
                })
            else:
                way_params.append({
                    'lat': current_coords[0],
                    'lon': current_coords[1],
                    'direction_deg': [math.degrees(theta)]
                })
                way_params.append({
                    'lat': current_coords[0],
                    'lon': current_coords[1],
                    'direction_deg': [back_azimuth(math.degrees(theta))]
                })
        
            current_coords = next_geo_coords(current_coords, pDistance, theta)
            iDistance = haversine(current_coords, coords[i+1])
        
        buffer = pDistance - iDistance
    
    return {
        'id': road_id,
        'way_params': way_params
    }

if __name__ == '__main__':
    # test = arrange_panoramas(1)
    # print(test)
    pass