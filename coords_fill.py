from db import conn
from datetime import date


def process(batch_size=200):
    with conn.cursor() as cur:
        cur.execute("SELECT city_id FROM cities")
        cities = [row[0] for row in cur.fetchall()]

        for city_id in cities:
            print(f"Обработка города {city_id}...")

            cur.execute("SELECT COUNT(*) FROM quarters WHERE city_id = %s", (city_id,))
            total_quarters = cur.fetchone()[0]
            print(f"  Всего кварталов: {total_quarters}")

            offset = 0
            processed = 0
            total_inserted = 0

            while offset < total_quarters:
                cur.execute("""
                    INSERT INTO distances (green_zone_id, quarter_id, is_processed, start_point, end_point)
                    SELECT 
                        gz.id,
                        q.id,
                        FALSE,
                        ST_Centroid(q.coords),
                        ST_ClosestPoint(gz.coords, ST_Centroid(q.coords))
                    FROM (
                        SELECT id, coords 
                        FROM quarters 
                        WHERE city_id = %s 
                        ORDER BY id 
                        LIMIT %s OFFSET %s
                    ) q
                    JOIN green_zones gz ON ST_DWithin(
                        ST_Centroid(q.coords)::geography, 
                        gz.coords::geography, 
                        1500
                    ) AND gz.city_id = %s
                    ON CONFLICT DO NOTHING;
                """, (city_id, batch_size, offset, city_id))

                inserted = cur.rowcount
                total_inserted += inserted
                processed += batch_size
                offset += batch_size

                print(f"    Пачка {offset//batch_size}: обработано кварталов до {offset} (из {total_quarters}), вставлено пар: {inserted}")

                conn.commit()

            cur.execute("""
                UPDATE quarters
                SET last_processed_at = %s
                WHERE city_id = %s
            """, (date.today(), city_id))
            conn.commit()

            print(f"  Город {city_id}: вставлено {total_inserted} пар, обновлено кварталов: {cur.rowcount}\n")

    print("Done")