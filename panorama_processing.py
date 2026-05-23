import os
from math import radians, sin, cos, atan2, sqrt
from PIL import Image
from streetlevel import yandex
from geo_utils import haversine


try:
    import nest_asyncio
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        nest_asyncio.apply()
    except RuntimeError:
        pass
except ImportError:
    pass

def crop_panorama_with_direction(input_path: str, output_path: str,
                                 direction_deg: float = 0, fov_deg: float = 70,
                                 height_pct: float = 0.40, tilt_pct: float = 0.50):
    """
    Обрезает панораму под заданное направление, угол обзора и наклон.
    """
    img = Image.open(input_path)
    width, height = img.size

    pixel_per_degree = width / 360.0
    center_x = (direction_deg % 360) * pixel_per_degree
    crop_width = int(fov_deg * pixel_per_degree)
    crop_height = int(height * height_pct)

    vertical_offset = int((height - crop_height) * tilt_pct)

    left = center_x - crop_width // 2
    right = center_x + crop_width // 2
    top = (height - crop_height) // 2 + vertical_offset
    bottom = top + crop_height

    top = max(0, min(top, height - crop_height))
    bottom = top + crop_height

    if left < 0:
        left_part = img.crop((0, top, right, bottom))
        right_part = img.crop((width + left, top, width, bottom))
        cropped = Image.new('RGB', (crop_width, crop_height))
        cropped.paste(right_part, (0, 0))
        cropped.paste(left_part, (right_part.width, 0))
    elif right > width:
        right_part = img.crop((left, top, width, bottom))
        left_part = img.crop((0, top, right - width, bottom))
        cropped = Image.new('RGB', (crop_width, crop_height))
        cropped.paste(right_part, (0, 0))
        cropped.paste(left_part, (right_part.width, 0))
    else:
        cropped = img.crop((left, top, right, bottom))

    cropped.save(output_path)

def get_panorama_with_view(lat: float, lon: float, direction_deg: float,
                           output_file: str = "road_view.jpg",
                           fov_deg: float = 50, tilt_pct: float = 0.5,
                           height_pct: float = 0.35,
                           max_distance_meters: float = 5.0) -> str:
    """
    Получает свежую панораму Яндекс, проверяет расстояние до запрошенных координат.
    Возвращает путь к файлу, если панорама найдена и расстояние <= max_distance_meters.
    В противном случае выбрасывает RuntimeError.
    """
    pano = yandex.find_panorama(lat, lon)
    if not pano:
        raise RuntimeError(f"No panorama found for ({lat}, {lon})")

    # Проверка расстояния между запрошенной и реальной точкой панорамы
    real_lat, real_lon = pano.lat, pano.lon
    distance = haversine(lat, lon, real_lat, real_lon)
    if distance > max_distance_meters:
        raise RuntimeError(
            f"Panorama is too far: {distance:.1f} m > {max_distance_meters} m. "
            f"Requested ({lat}, {lon}), actual ({real_lat}, {real_lon})"
        )

    temp_file = "temp_panorama.jpg"
    try:
        yandex.download_panorama(pano, temp_file, zoom=0)
        crop_panorama_with_direction(
            temp_file, output_file,
            direction_deg=direction_deg,
            fov_deg=fov_deg,
            height_pct=height_pct,
            tilt_pct=tilt_pct
        )
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    return output_file