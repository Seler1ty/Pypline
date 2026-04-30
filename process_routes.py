from db import conn
import time
from route_osm import get_route_valhalla


def get_unprocessed_distances(start_id, end_id, limit=100):

    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                id,
                ST_X(start_point),
                ST_Y(start_point),
                ST_X(end_point),
                ST_Y(end_point)
            FROM distances
            WHERE
                is_processed = FALSE
                AND id BETWEEN %s AND %s
            ORDER BY id
            LIMIT %s
        """, (start_id, end_id, limit))

        return cur.fetchall()


def update_route(distance_id, curve_distance):

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE distances
            SET
                length_curve_line = %s,
                is_processed = TRUE
            WHERE id = %s
        """, (
            curve_distance,
            distance_id
        ))


def process_routes(start_id, end_id):

    rows = get_unprocessed_distances(start_id, end_id)

    for row in rows:

        distance_id = row[0]

        start = (row[1], row[2])
        end = (row[3], row[4])

        route = get_route_valhalla(start, end)

        if route:
            update_route(
                distance_id,
                route["distance"]
            )

        time.sleep(0.1)

    conn.commit()