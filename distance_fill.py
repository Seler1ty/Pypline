import psycopg2
import time
from datetime import datetime, timezone
from route_osm import haversine, get_route_valhalla
from credentials import Credentials

# Подключение к БД

conn = psycopg2.connect(
    host = "aws-0-eu-west-1.pooler.supabase.com",
    dbname = "postgres",
    user = Credentials.USER,
    password = Credentials.PASSWORD,
    port = 6543,
    sslmode = "require"
)
# conn.close()

# conn.autocommit = True

def get_cities():
    with conn.cursor() as cur:
        cur.execute("SELECT city_id FROM cities")
        return [row[0] for row in cur.fetchall()]


def get_unprocessed_quarters(city_id):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, coords
            FROM quarters
            WHERE city_id = %s
                AND last_processed_at IS NULL
            ORDER BY id;                    
        """, (city_id))

        return cur.fetchall()

def get_green_zones(city_id):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, coords
            FROM green_zones
            WHERE city_id = %s
        """, (city_id))
        return cur.fetchall()

def save_distance(q_id, gz_id, curve_dist, proccessed):
    with conn.cursor() as cur:
        cur.execute("""
        INSERT INTO distances (curve_line_dist, green_zone_id, quarter_id, is_processed)
        VALUES (%s, %s, %s, %s);    
    """, (curve_dist, gz_id, q_id, proccessed))


def mark_quarter_done(q_id):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE quarters
            SET last_processed at = %s
            WHERE id = %s            
        """, (datetime.now(timezone.utc), q_id))


def process():
    cities = get_cities()

    for city_id in cities:
        print(f"City {city_id}")

        green_zones = get_green_zones(city_id)
        quarters = get_unprocessed_quarters(city_id)

        for q in quarters:
            q_id, q_poly = q

            with conn.cursor() as cur:
                cur.execute("""
                SELECT ST_AsText(ST_Centroid(coords))
                FROM quarters
                WHERE id = %s;
                """, (q_id,))
                center = cur.fetchone()[0]

            print(f"Quarter {q_id}")

            all_ok = True

            for gz in green_zones:
                gz_id, gz_poly = gz

                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT ST_AsText(ST_Centroid(coords))
                        FROM green_zones
                        WHERE id = %s;
                    """, (gz_id,))
                    target = cur.fetchone()[0]

                # 1. прямое расстояние
                direct = haversine(center, target)

                if direct > 1500:
                    continue

                # 2. маршрут
                route = get_route_valhalla(center, target)

                time.sleep(0.1)

                if route:
                    save_distance(
                        route["distance"],
                        q_id, gz_id,
                        True
                    )
                else:
                    save_distance(
                        direct,
                        q_id, gz_id,
                        False
                    )
                    all_ok = False

            # если всё успешно
            if all_ok:
                mark_quarter_done(q_id)


def main():
    print("Hello, World!")
    pass


if __name__ == "__main__":
    main()