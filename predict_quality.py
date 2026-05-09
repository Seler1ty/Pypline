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
                COUNT(CASE WHEN d.length_curve_line > 800 AND d.length_curve_line <= 1500 THEN 1 END) AS mid_count,

                -- Total area for each category
                SUM(CASE WHEN d.length_curve_line <= 400 THEN p.area ELSE 0 END) AS great_total_area,
                SUM(CASE WHEN d.length_curve_line > 400 AND d.length_curve_line <= 800 THEN p.area ELSE 0 END) AS good_total_area,
                SUM(CASE WHEN d.length_curve_line > 800 AND d.length_curve_line <= 1500 THEN p.area ELSE 0 END) AS mid_total_area,

                -- Mean NDVI for each category
                SUM(CASE WHEN d.length_curve_line <= 400 THEN p.ndvi * p.area ELSE 0 END) / NULLIF(SUM(CASE WHEN d.length_curve_line <= 400 THEN p.area ELSE 0 END), 0) AS great_mean_ndvi,
                SUM(CASE WHEN d.length_curve_line > 400 AND d.length_curve_line <= 800 THEN p.ndvi * p.area ELSE 0 END) / NULLIF(SUM(CASE WHEN d.length_curve_line > 400 AND d.length_curve_line <= 800 THEN p.area ELSE 0 END), 0) AS good_mean_ndvi,
                SUM(CASE WHEN d.length_curve_line > 800 AND d.length_curve_line <= 1500 THEN p.ndvi * p.area ELSE 0 END) / NULLIF(SUM(CASE WHEN d.length_curve_line > 800 AND d.length_curve_line <= 1500 THEN p.area ELSE 0 END), 0) AS mid_mean_ndvi

            FROM 
                quarters q
                JOIN distances d ON q.id = d.quarter_id
                JOIN green_zones p ON d.green_zone_id = p.id
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
            
            gen_area = data[6] + data[7] + data[8]

            if gen_area > 0:
                gen_ndvi = (data[9] * data[6] + data[10] * data[7] + data[11] * data[8]) / gen_area
            else:
                gen_ndvi = np.nan  # или None

            row = pd.DataFrame({
                'area': [data[1]],
                'population': [data[2]],
                'great_parks_count': [data[3]],
                'great_parks_area': [data[6]],
                'great_parks_ndvi': [data[9]],
                'good_parks_count': [data[4]],
                'good_parks_area': [data[7]],
                'good_parks_ndvi': [data[10]],
                'ok_parks_count': [data[5]],
                'ok_parks_area': [data[8]],
                'ok_parks_ndvi': [data[11]],
                'general_ndvi': [gen_ndvi],
                'general_area': [gen_area],
                'population_density_per_green_zone': [data[2]/gen_area if gen_area > 0 else 0],
                'general_population_density': [data[2]/data[1] if data[1] > 0 else 0]
            })

            df = pd.concat([df, row], ignore_index=True)
        
        df.to_csv("new_dataset.csv", index=False)
    
if __name__ == '__main__':
    aggregate_data()