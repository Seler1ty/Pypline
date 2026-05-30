import csv
from db import conn

# 2. Путь к файлу и нужные столбцы (укажите свои индексы или названия)
csv_files = {
    1: 'Pypline/prepared_roads_data/RoadsEKB.csv',
    2: 'Pypline/prepared_roads_data/RoadsMSC.csv',
    3: 'Pypline/prepared_roads_data/RoadsSPB.csv'
}

selected_columns = ['feature_id', 'geometry_format']

try:
    cur = conn.cursor()

    for city_id, file_path in csv_files.items():

        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # Формируем SQL-запрос для вставки

            # Читаем CSV построчно и отбираем нужные данные
            for row in reader:
                # Извлекаем только те значения, которые есть в selected_columns
                values = [row[col] for col in selected_columns]

                # Выполняем запрос
                cur.execute("""
                    INSERT INTO roads (id, city_id, geom_curve) VALUES (%s, %s, %s) 
                """, (values[0][4:], city_id, values[1]))

    # Применяем изменения
    conn.commit()
    print("Данные успешно добавлены!")

except Exception as error:
    print(f"Ошибка подключения или вставки: {error}")
    if conn:
        conn.rollback()

finally:
    # Закрываем соединение
    print("Закрываем соединение...")
    if cur: cur.close()
    if conn: conn.close()
    print("Соединение закрыто")
