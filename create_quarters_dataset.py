import pandas as pd
import numpy as np
from db import conn


def aggregate_data():
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                q.id AS quarter_id,
                q.area AS area,
                q.population AS population,
                -- Count for each category
                COUNT(CASE WHEN d.length_curve_line <= 400 THEN 1 END) AS great_count,
                COUNT(CASE WHEN d.length_curve_line > 400 AND d.length_curve_line <= 800 THEN 1 END) AS good_count,
                COUNT(CASE WHEN d.length_curve_line > 800 AND d.length_curve_line <= 1500 THEN 1 END) AS ok_count,

                -- Total area for each category
                SUM(CASE WHEN d.length_curve_line <= 400 THEN p.area ELSE 0 END) AS great_total_area,
                SUM(CASE WHEN d.length_curve_line > 400 AND d.length_curve_line <= 800 THEN p.area ELSE 0 END) AS good_total_area,
                SUM(CASE WHEN d.length_curve_line > 800 AND d.length_curve_line <= 1500 THEN p.area ELSE 0 END) AS ok_total_area,

                -- Mean NDVI for each category
                SUM(CASE WHEN d.length_curve_line <= 400 THEN p.ndvi * p.area ELSE 0 END) / NULLIF(SUM(CASE WHEN d.length_curve_line <= 400 THEN p.area ELSE 0 END), 0) AS great_mean_ndvi,
                SUM(CASE WHEN d.length_curve_line > 400 AND d.length_curve_line <= 800 THEN p.ndvi * p.area ELSE 0 END) / NULLIF(SUM(CASE WHEN d.length_curve_line > 400 AND d.length_curve_line <= 800 THEN p.area ELSE 0 END), 0) AS good_mean_ndvi,
                SUM(CASE WHEN d.length_curve_line > 800 AND d.length_curve_line <= 1500 THEN p.ndvi * p.area ELSE 0 END) / NULLIF(SUM(CASE WHEN d.length_curve_line > 800 AND d.length_curve_line <= 1500 THEN p.area ELSE 0 END), 0) AS ok_mean_ndvi

            FROM 
                quarters q
                JOIN distances d ON q.id = d.quarter_id
                JOIN green_zones p ON d.green_zone_id = p.id
            WHERE 
                q.city_id in (3)
            GROUP BY 
                q.id
            ORDER BY 
                q.id;
        """)
        aggregated_data = cur.fetchall()

        df = pd.DataFrame({
            'area': [],
            'population': [],
            'great_parks_count': [],
            'great_parks_area': [],
            'great_parks_ndvi': [],
            'good_parks_count': [],
            'good_parks_area': [],
            'good_parks_ndvi': [],
            'ok_parks_count': [],
            'ok_parks_area': [],
            'ok_parks_ndvi': [],
            'general_ndvi': [],
            'general_area': [],
            'population_density_per_green_zone': [],
            'general_population_density': []
        })
        for data in aggregated_data:
            area = data[1] or 0
            population = data[2] or 0

            great_count = data[3] or 0
            good_count = data[4] or 0
            ok_count = data[5] or 0

            great_area = data[6] or 0
            good_area = data[7] or 0
            ok_area = data[8] or 0

            great_ndvi = data[9]
            good_ndvi = data[10]
            ok_ndvi = data[11]

            gen_area = great_area + good_area + ok_area

            if gen_area > 0:
                weighted_sum = 0.0
                if great_area > 0 and great_ndvi is not None:
                    weighted_sum += great_ndvi * great_area
                if good_area > 0 and good_ndvi is not None:
                    weighted_sum += good_ndvi * good_area
                if ok_area > 0 and ok_ndvi is not None:
                    weighted_sum += ok_ndvi * ok_area
                gen_ndvi = weighted_sum / gen_area
            else:
                gen_ndvi = np.nan

            row = pd.DataFrame({
                'area': [area],
                'population': [population],
                'great_parks_count': [great_count],
                'great_parks_area': [great_area],
                'great_parks_ndvi': [great_ndvi],
                'good_parks_count': [good_count],
                'good_parks_area': [good_area],
                'good_parks_ndvi': [good_ndvi],
                'ok_parks_count': [ok_count],
                'ok_parks_area': [ok_area],
                'ok_parks_ndvi': [ok_ndvi],
                'general_ndvi': [gen_ndvi],
                'general_area': [gen_area],
                'population_density_per_green_zone': [population/gen_area if gen_area > 0 else 0],
                'general_population_density': [population/area if area > 0 else 0]
            })

            df = pd.concat([df, row], ignore_index=True)
    
    return df


def create_dataset() -> None:
    df = aggregate_data()

    df.to_csv("dataset/spb_dataset.csv", index=False)


def predict():
    # TODO
    pass


if __name__ == '__main__':
    create_dataset()