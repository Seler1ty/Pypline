from db import get_conn
from predict_road import process_all_roads
from time import perf_counter


def aggregate_quality_data(data: dict):
    quality_array = []

    relation = {
        'good': 1,
        'regular': 2,
        'bad': 3,
    }
    reversed_relation = {v: k for k, v in relation.items()}

    for element in data['results']:
        if element['status'] == 'success':
            quality_array.append(relation[element['predicted_class']])
        else:
            quality_array.append(None)

    if quality_array.count(None) == len(quality_array):
        return []

    else:
        valid_quality_ind = []

        for i in range(len(quality_array)):
            if quality_array[i] != None:
                valid_quality_ind.append(i)

        # Заполняем начало
        first_valid = valid_quality_ind[0]
        for i in range(first_valid):
            quality_array[i] = quality_array[first_valid]

        # Заполняем конец
        last_valid = valid_quality_ind[-1]
        for i in range(last_valid + 1, len(quality_array)):
            quality_array[i] = quality_array[last_valid]

        # Заполняем середину
        for i in range(len(valid_quality_ind) - 1):
            start = valid_quality_ind[i]
            end = valid_quality_ind[i + 1]

            if start - end == 1:
                continue

            for j in range(start + 1, end):
                t = (j - start) / (end - start)
                interpolated_value = round(
                    quality_array[start] + (quality_array[end] - quality_array[start]) * t
                )
                quality_array[j] = interpolated_value
                # print(f"Примерное качество -> {reversed_relation[interpolated_value]}")

    result = [reversed_relation[quality] for quality in quality_array]

    stats = {}
    for key in relation.keys():
        stats[key] = result.count(key)

    return stats


def load_data_to_db(data, id, conn):
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE roads
                SET is_processed=TRUE, good_num=%s, regular_num=%s, bad_num=%s
                WHERE id=%s
            """, (
                data['good'],
                data['regular'],
                data['bad'],
                id,
            ))
        conn.commit()
        # print(f"[{id}] Успешно загружен!")
    except Exception as error:
        # print(f"[{id}] Ошибка подключения или вставки: {error}")
        if conn:
            conn.rollback()


def main():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, ST_AsText(geom_curve)
                FROM roads WHERE city_id=1 AND is_processed=TRUE
            """)
            rows = cur.fetchall()

    for batch in range(1):
        pending = [
            (row[0], row[1])
            for row in rows[:3]
        ]

        road_results = process_all_roads(
            pending,
            concurrency_per_road=3,
            road_concurrency=2,
        )

        # Новое соединение для записи результатов батча
        with get_conn() as conn:
            for road_result in road_results:
                if isinstance(road_result, Exception):
                    continue

                road_id = road_result["road_id"]
                data = aggregate_quality_data(road_result)

                if not data:
                    continue

                load_data_to_db(data, road_id, conn)


if __name__ == '__main__':
    main()