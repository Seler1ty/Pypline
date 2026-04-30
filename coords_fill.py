from db import conn
import time
from datetime import datetime, timezone
from route_osm import haversine



def get_cities():
    with conn.cursor() as cur:
        cur.execute("SELECT city_id FROM cities")
        return [row[0] for row in cur.fetchall()]


def get_quarters(city_id):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                id,
                ST_Centroid(coords),
                ST_Y(ST_Centroid(coords)),
                ST_X(ST_Centroid(coords))
            FROM quarters
            WHERE city_id = %s
            ORDER BY id;
        """, (city_id,))

        return cur.fetchall()


def get_green_zones(city_id):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                id,
                ST_Centroid(coords),
                ST_Y(ST_Centroid(coords)),
                ST_X(ST_Centroid(coords))
            FROM green_zones
            WHERE city_id = %s
        """, (city_id,))

        return cur.fetchall()


def save_route_ends(q_id, gz_id, q_center, gz_center):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO distances (
                green_zone_id,
                quarter_id,
                is_processed,
                start_point,
                end_point
            )
            VALUES (%s, %s, FALSE, %s, %s)
            ON CONFLICT DO NOTHING;
        """, (
            gz_id,
            q_id,
            q_center,
            gz_center,
        ))

# Я пока делал код, забыл, зачем нам нужна эта функция. Чекните, нужна ли, пж
def mark_quarter_done(q_id):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE quarters
            SET last_processed_at = %s
            WHERE id = %s            
        """, (datetime.now(timezone.utc), q_id,))


def process():

    cities = get_cities()

    for city_id in cities:

        green_zones = get_green_zones(city_id)
        quarters = get_quarters(city_id)

        for q_id, q_center_geom, q_lat, q_lon in quarters:

            center = (q_lat, q_lon)

            for gz_id, gz_center_geom, gz_lat, gz_lon in green_zones:

                target = (gz_lat, gz_lon)

                direct = haversine(center, target)

                if direct <= 1500:
                    save_route_ends(
                        gz_id,
                        q_id,
                        q_center_geom,
                        gz_center_geom
                    )

        conn.commit()