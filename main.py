from coords_fill import process as fill_process
from process_routes import process_routes
from db import conn

def get_ids(start = None, end = None):
    if not(start) and not(end):
        with conn.cursor() as cur:
            cur.execute("SELECT MIN(id), MAX(id) FROM distances WHERE is_processed = FALSE")
            min_id, max_id = cur.fetchone()
            if min_id is None:
                print("Нет необработанных записей.")
            return min_id, max_id
    else:
        return start, end

def main():
    # fill = true – запускаем первичное заполнение
    fill = False  # Вызывается только 1 раз
    if fill:
        print("Первичное заполнение...")
        fill_process()
        print("Готово.")
    else:
        print("Запуск обработки...")
        process_routes(batch_size=100, fetch_limit=5000)
        print("Готово.")

if __name__ == "__main__":
    main()