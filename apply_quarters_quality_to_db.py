# apply_quality_to_db.py
import pandas as pd
import numpy as np
from datetime import date
from db import conn
from predictor import Predictor

MODEL_PATH = "ai_models/green_zones_model.pkl"
FEATURE_COLUMNS = [
    'area', 'population',
    'great_parks_count', 'great_parks_area', 'great_parks_ndvi',
    'good_parks_count', 'good_parks_area', 'good_parks_ndvi',
    'ok_parks_count', 'ok_parks_area', 'ok_parks_ndvi',
    'general_ndvi', 'general_area',
    'population_density_per_green_zone', 'general_population_density'
]

def get_quarters_to_predict():
    """
    Возвращает список id кварталов, для которых нужно выполнить предсказание:
    - quality IS NULL
    - ИЛИ last_processed_at IS NULL
    - ИЛИ last_processed_at <= CURRENT_DATE - INTERVAL '1 year'
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id
            FROM quarters
            WHERE quality IS NULL
               OR last_processed_at IS NULL
               OR last_processed_at <= (CURRENT_DATE - INTERVAL '1 year')
        """)
        return [row[0] for row in cur.fetchall()]

def get_aggregated_data_for_quarters(quarter_ids):
    """
    Для заданных quarter_ids возвращает DataFrame с признаками (аналогично dataset.py).
    Если quarter_ids пуст – возвращает пустой DataFrame.
    """
    if not quarter_ids:
        return pd.DataFrame()

    # Формируем запрос с IN (...)
    placeholders = ','.join(['%s'] * len(quarter_ids))
    query = f"""
        SELECT 
            q.id AS quarter_id,
            q.area AS area,
            q.population AS population,
            COUNT(CASE WHEN d.length_curve_line <= 400 THEN 1 END) AS great_count,
            COUNT(CASE WHEN d.length_curve_line > 400 AND d.length_curve_line <= 800 THEN 1 END) AS good_count,
            COUNT(CASE WHEN d.length_curve_line > 800 AND d.length_curve_line <= 1500 THEN 1 END) AS ok_count,
            SUM(CASE WHEN d.length_curve_line <= 400 THEN p.area ELSE 0 END) AS great_total_area,
            SUM(CASE WHEN d.length_curve_line > 400 AND d.length_curve_line <= 800 THEN p.area ELSE 0 END) AS good_total_area,
            SUM(CASE WHEN d.length_curve_line > 800 AND d.length_curve_line <= 1500 THEN p.area ELSE 0 END) AS ok_total_area,
            SUM(CASE WHEN d.length_curve_line <= 400 THEN p.ndvi * p.area ELSE 0 END) / NULLIF(SUM(CASE WHEN d.length_curve_line <= 400 THEN p.area ELSE 0 END), 0) AS great_mean_ndvi,
            SUM(CASE WHEN d.length_curve_line > 400 AND d.length_curve_line <= 800 THEN p.ndvi * p.area ELSE 0 END) / NULLIF(SUM(CASE WHEN d.length_curve_line > 400 AND d.length_curve_line <= 800 THEN p.area ELSE 0 END), 0) AS good_mean_ndvi,
            SUM(CASE WHEN d.length_curve_line > 800 AND d.length_curve_line <= 1500 THEN p.ndvi * p.area ELSE 0 END) / NULLIF(SUM(CASE WHEN d.length_curve_line > 800 AND d.length_curve_line <= 1500 THEN p.area ELSE 0 END), 0) AS ok_mean_ndvi
        FROM quarters q
        JOIN distances d ON q.id = d.quarter_id
        JOIN green_zones p ON d.green_zone_id = p.id
        WHERE q.id IN ({placeholders})
        GROUP BY q.id
        ORDER BY q.id
    """
    with conn.cursor() as cur:
        cur.execute(query, quarter_ids)
        rows = cur.fetchall()

    data = []
    for row in rows:
        q_id = row[0]
        area = row[1] or 0
        population = row[2] or 0
        great_count = row[3] or 0
        good_count = row[4] or 0
        ok_count = row[5] or 0
        great_area = row[6] or 0
        good_area = row[7] or 0
        ok_area = row[8] or 0
        great_ndvi = row[9] if row[9] is not None else 0.0
        good_ndvi = row[10] if row[10] is not None else 0.0
        ok_ndvi = row[11] if row[11] is not None else 0.0

        gen_area = great_area + good_area + ok_area
        if gen_area > 0:
            weighted = 0.0
            if great_area > 0:
                weighted += great_ndvi * great_area
            if good_area > 0:
                weighted += good_ndvi * good_area
            if ok_area > 0:
                weighted += ok_ndvi * ok_area
            gen_ndvi = weighted / gen_area
        else:
            gen_ndvi = np.nan

        pop_density_per_green = population / gen_area if gen_area > 0 else 0
        pop_density_general = population / area if area > 0 else 0

        data.append({
            'quarter_id': q_id,
            'area': area,
            'population': population,
            'great_parks_count': great_count,
            'great_parks_area': great_area,
            'great_parks_ndvi': great_ndvi,
            'good_parks_count': good_count,
            'good_parks_area': good_area,
            'good_parks_ndvi': good_ndvi,
            'ok_parks_count': ok_count,
            'ok_parks_area': ok_area,
            'ok_parks_ndvi': ok_ndvi,
            'general_ndvi': gen_ndvi,
            'general_area': gen_area,
            'population_density_per_green_zone': pop_density_per_green,
            'general_population_density': pop_density_general
        })

    return pd.DataFrame(data)

def update_quarter_results(quarter_id, quality, processed_date):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE quarters
            SET quality = %s, last_processed_at = %s
            WHERE id = %s
        """, (quality, processed_date, quarter_id))
    conn.commit()

def main():
    print("1. Загрузка модели...")
    predictor = Predictor(MODEL_PATH)

    print("2. Поиск кварталов, нуждающихся в обновлении...")
    quarter_ids = get_quarters_to_predict()
    if not quarter_ids:
        print("Нет кварталов для обновления.")
        return
    print(f"Найдено кварталов: {len(quarter_ids)}")

    print("3. Агрегация данных для этих кварталов...")
    df = get_aggregated_data_for_quarters(quarter_ids)
    if df.empty:
        print("Нет данных с парками (все кварталы без зон) – проставляем качество 1 и дату.")
        # Для кварталов, у которых нет ни одной связи, устанавливаем качество = 1
        today = date.today()
        for qid in quarter_ids:
            update_quarter_results(qid, 1, today)
        print("Готово (кварталы без зон).")
        return

    # Отделяем quarter_id от признаков
    ids = df['quarter_id'].values
    X = df[FEATURE_COLUMNS]

    print("4. Применение модели...")
    predictions = predictor.predict(X)

    # Обновление кварталов
    print("5. Обновление БД...")
    today = date.today()
    for qid, qual in zip(ids, predictions):
        quality_int = int(round(qual))
        update_quarter_results(qid, quality_int, today)

    ids_with_data = set(ids)
    ids_without_data = set(quarter_ids) - ids_with_data
    if ids_without_data:
        print(f"  Кварталов без связей: {len(ids_without_data)} – устанавливаем качество 1")
        for qid in ids_without_data:
            update_quarter_results(qid, 1, today)

    print("Готово.")

if __name__ == "__main__":
    main()