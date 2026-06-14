import math
from geo_utils import wkt_linestring_to_coords, haversine, next_geo_coords, azimuth, back_azimuth
from typing import Dict


# Размещение панорам на участке дороге
def arrange_panoramas(db_coords) -> Dict:
    
    # test input
    # geom_curve = 'LINESTRING(56.8047788 60.5412938,56.8050156 60.5412006,56.8052554 60.541155,56.8053215 60.5411524,56.8053578 60.5411615,56.8053895 60.5411652,56.8054874 60.5412046,56.8055933 60.5412569,56.8056955 60.5413348,56.8060505 60.5416102)'
    coords = wkt_linestring_to_coords(db_coords)

    distance = 0

    for i in range(len(coords)-1):
        distance += haversine(coords[i], coords[i+1])
    
    # Количество панорам на участок дороги
    n = min(math.ceil(distance / 60), max(2, math.ceil(5 * math.sqrt(distance / 100))))

    # Расстояние между панорамами
    pDistance = round(distance / n, 3)

    way_params = []

    distance_to_next = 0

    for i in range(len(coords) - 1):

        start = coords[i]
        end = coords[i + 1]

        segment_length = haversine(start, end)

        theta_deg = azimuth(
            start[0], start[1],
            end[0], end[1]
        )

        theta = math.radians(theta_deg)

        travelled = 0

        while travelled + distance_to_next <= segment_length:

            # Точка панорамы
            pano_coords = next_geo_coords(
                start,
                travelled + distance_to_next,
                theta
            ) if travelled + distance_to_next > 0 else start

            if len(way_params) == 0:
                way_params.append({
                    'lat': pano_coords[1],
                    'lon': pano_coords[0],
                    'direction_deg': theta_deg
                })
            else:
                way_params.append({
                    'lat': pano_coords[1],
                    'lon': pano_coords[0],
                    'direction_deg': theta_deg
                })

                # Unused (performance matters)
                '''
                way_params.append({
                    'lat': pano_coords[1],
                    'lon': pano_coords[0],
                    'direction_deg': back_azimuth(theta_deg)
                })
                '''

            travelled += distance_to_next

            # После первой панорамы всегда шаг pDistance
            distance_to_next = pDistance

        # Сколько осталось пройти до следующей панорамы
        distance_to_next -= (segment_length - travelled)
    
    return {
        'step_len': math.floor(pDistance) // 2,
        'way_params': way_params
    }

if __name__ == '__main__':
    # test = arrange_panoramas(1)
    # print(test)
    pass