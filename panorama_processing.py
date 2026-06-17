import os
import time
import asyncio
import tempfile
import threading
from PIL import Image
from streetlevel import yandex
from geo_utils import haversine
from time import perf_counter


def _run_in_new_thread(fn, *args):
    """
    Run a blocking function that internally calls asyncio.run() in a
    brand-new thread with its own event loop.

    Why: yandex.find_panorama / yandex.download_panorama both call
    asyncio.run() internally (via streetlevel's tile downloader).
    If we hand them to run_in_executor they execute inside the *shared*
    thread-pool, where the parent ProactorEventLoop (Windows) has already
    set up socket I/O completion ports.  A nested asyncio.run() then tries
    to create a second ProactorEventLoop on the same thread, which corrupts
    the IOCP state and causes WinError 64 / ConnectionResetError on every
    connection after the first.

    Spawning a plain daemon thread gives each call its own clean OS thread
    with no pre-existing event loop state, so asyncio.run() inside
    streetlevel works correctly.
    """
    result = [None]
    exc = [None]

    def target():
        try:
            result[0] = fn(*args)
        except Exception as e:
            exc[0] = e

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join()

    if exc[0] is not None:
        raise exc[0]
    return result[0]


def crop_panorama_with_direction(input_path: str, output_path: str,
                                 direction_deg: float = 0, fov_deg: float = 25,
                                 height_pct: float = 0.1, tilt_pct: float = 0.3):
    """
    Crops a panorama to the given direction, FOV, and tilt.
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


# ── Synchronous version (unchanged interface) ────────────────────────────────

def get_panorama_with_view(lat: float, lon: float, direction_deg: float,
                           output_file: str = "road_view.jpg",
                           fov_deg: float = 25, tilt_pct: float = 0.35,
                           height_pct: float = 0.1,
                           max_distance_meters: float = 5.0,
                           retries: int = 3):
    """
    Synchronous wrapper — kept for backwards compatibility.
    For batch processing prefer get_panorama_with_view_async.
    """
    return asyncio.run(
        get_panorama_with_view_async(
            lat=lat, lon=lon, direction_deg=direction_deg,
            output_file=output_file, fov_deg=fov_deg,
            tilt_pct=tilt_pct, height_pct=height_pct,
            max_distance_meters=max_distance_meters, retries=retries,
        )
    )


# ── Async core ────────────────────────────────────────────────────────────────

async def get_panorama_with_view_async(lat: float, lon: float,
                                       direction_deg: float,
                                       output_file: str = "road_view.jpg",
                                       fov_deg: float = 25,
                                       tilt_pct: float = 0.35,
                                       height_pct: float = 0.1,
                                       max_distance_meters: float = 5.0,
                                       retries: int = 3,
                                       semaphore: asyncio.Semaphore | None = None):
    """
    Async version. Pass a shared semaphore from the caller to throttle
    concurrency across all panoramas in a batch (recommended: 8–16).
    """
    loop = asyncio.get_running_loop()

    async def _find():
        # Each call gets its own thread so streetlevel's internal asyncio.run()
        # doesn't conflict with our outer event loop (fixes WinError 64).
        return await loop.run_in_executor(
            None, _run_in_new_thread, yandex.find_panorama, lat, lon
        )

    async def _download(pano, path):
        await loop.run_in_executor(
            None, _run_in_new_thread, yandex.download_panorama, pano, path, 3
        )

    async def _crop(src, dst):
        # crop is pure CPU/PIL — safe to run in the shared thread pool
        await loop.run_in_executor(
            None, crop_panorama_with_direction, src, dst,
            direction_deg, fov_deg, height_pct, tilt_pct
        )

    async def _run():
        pano = None
        last_error = None

        for attempt in range(retries):
            try:
                pano = await _find()
                if pano:
                    break
            except Exception as e:
                last_error = str(e)
            await asyncio.sleep(1)

        if pano is None:
            return {"status": "download_error", "message": last_error} \
                   if last_error else {"status": "no_panorama"}

        distance = haversine([lat, lon], [pano.lat, pano.lon])
        if distance > max_distance_meters:
            return {"status": "panorama_too_far", "distance": distance}

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            temp_file = tmp.name

        try:
            await _download(pano, temp_file)

            await _crop(temp_file, output_file)

            return {"status": "success", "file_path": output_file, "distance": distance}

        except Exception as e:
            import traceback; traceback.print_exc()
            return {"status": "download_error", "message": str(e)}

        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    if semaphore is not None:
        async with semaphore:
            return await _run()
    else:
        return await _run()


# ── Batch helper (the main entry point for predict_road.py) ──────────────────

async def fetch_panoramas_batch(pano_params: list[dict],
                                output_dir: str,
                                road_id: str | int = 0,
                                max_distance_meters: float = 5.0,
                                concurrency: int = 10,
                                **kwargs) -> list[dict]:
    """
    Fetches all panoramas for one road concurrently.

    Args:
        pano_params:          list of {lat, lon, direction_deg} dicts from arrange_panoramas
        output_dir:           directory where cropped images are saved
        road_id:              used only for unique temp filenames
        max_distance_meters:  passed through to each panorama fetch
        concurrency:          max simultaneous downloads (tune to avoid 429s)
        **kwargs:             forwarded to get_panorama_with_view_async (fov_deg, etc.)

    Returns:
        list of result dicts in the same order as pano_params, each containing
        at minimum {"index", "lat", "lon", "status"} and optionally "file_path",
        "distance", "predicted_class".
    """
    sem = asyncio.Semaphore(concurrency)

    async def _one(i, pano):
        out = os.path.join(output_dir, f"road_{road_id}_{i}.jpg")
        result = await get_panorama_with_view_async(
            lat=pano["lat"],
            lon=pano["lon"],
            direction_deg=0,
            output_file=out,
            max_distance_meters=max_distance_meters,
            semaphore=sem,
            **kwargs,
        )
        return {"index": i, "lat": pano["lat"], "lon": pano["lon"], "direction_deg": pano["direction_deg"], **result}

    tasks = [_one(i, p) for i, p in enumerate(pano_params)]
    return await asyncio.gather(*tasks)