from db import conn
from route_osm import get_valhalla_matrix
from collections import defaultdict

def get_unprocessed_grouped(limit=5000):
    """
    Возвращает словарь {quarter_id: [(distance_id, start_lon, start_lat, end_lon, end_lat), ...]}
    Выбирает до `limit` необработанных записей из distances, группирует по quarter_id.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, quarter_id,
                   ST_X(start_point) AS start_lon, ST_Y(start_point) AS start_lat,
                   ST_X(end_point) AS end_lon, ST_Y(end_point) AS end_lat
            FROM distances
            WHERE is_processed = FALSE
            ORDER BY quarter_id, id
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()

    grouped = defaultdict(list)
    for row in rows:
        distance_id, q_id, start_lon, start_lat, end_lon, end_lat = row
        grouped[q_id].append((distance_id, start_lon, start_lat, end_lon, end_lat))
    return grouped

def update_routes_batch(updates):
    """
    Массовое обновление: updates = [(distance_id, curve_distance), ...]
    """
    if not updates:
        return
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE distances AS d
            SET length_curve_line = u.dist,
                is_processed = TRUE
            FROM UNNEST(%s::int[], %s::float[]) AS u(id, dist)
            WHERE d.id = u.id
        """, ( [uid for uid, _ in updates], [dist for _, dist in updates] ))
    conn.commit()

def process_routes(batch_size=100, fetch_limit=10000):
    """
    batch_size   – сколько конечных точек отправлять в одном матричном запросе по API
    fetch_limit  – сколько записей за раз читать из БД
    """
    total_processed = 0

    while True:
        grouped = get_unprocessed_grouped(limit=fetch_limit)
        if not grouped:
            break

        all_updates = []

        for quarter_id, pairs in grouped.items():
            first = pairs[0]
            start_lon, start_lat = first[1], first[2]  # (start_lon, start_lat)

            end_points = []  # список (end_lon, end_lat)
            distance_ids = []
            for (dist_id, _, _, end_lon, end_lat) in pairs:
                distance_ids.append(dist_id)
                end_points.append((end_lon, end_lat))

            start_latlon = (start_lat, start_lon)
            targets_latlon = [(lat, lon) for (lon, lat) in end_points]  # меняем местами

            # Разбитие на батчи
            for i in range(0, len(targets_latlon), batch_size):
                batch_targets = targets_latlon[i:i+batch_size]
                batch_ids = distance_ids[i:i+batch_size]

                distances_m = get_valhalla_matrix([start_latlon], batch_targets)

                for dist_id, dist in zip(batch_ids, distances_m):
                    if dist is not None:
                        all_updates.append((dist_id, dist))
                    else:
                        pass

            if len(all_updates) >= 500:
                update_routes_batch(all_updates)
                total_processed += len(all_updates)
                print(f"Обновлено {len(all_updates)} записей (всего {total_processed})")
                all_updates = []

        if all_updates:
            update_routes_batch(all_updates)
            total_processed += len(all_updates)
            print(f"Обновлено {len(all_updates)} записей (всего {total_processed})")

    print(f"Done. Всего обработано маршрутов: {total_processed}")