from predict_road import predict_road_quality
from db import get_conn

with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, ST_AsText(geom_curve)
                FROM roads WHERE city_id=1 AND is_processed=FALSE
            """)
            rows = cur.fetchall()

geom = rows[1][1]

print(geom)
result = predict_road_quality(geom, road_id="test_road")

print(f"Total points: {result['total_points']}")
print(f"Successful:   {result['success_count']}")
for r in result["results"]:
    print(r)