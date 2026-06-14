import os
import asyncio
from panorama_planner import arrange_panoramas
from panorama_processing import fetch_panoramas_batch
from road_classifier import ModelUser
from road_classifier import get_ready_model
import torch

#path_to_model = 'Pypline/model/model_RQCD_state_dict_6_epoch.pt'
#classifier = ModelUser(path_to_model)

# Определяем устройство
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model_path = 'Pypline/model/model_RQCD_state_dict_9_epoch.pt'

# Создаём архитектуру модели (должна совпадать с той, что обучалась)
new_model = get_ready_model(num_classes=3).to(device)
param_model = torch.load(model_path)

new_model.load_state_dict(param_model)

classifier = ModelUser(model=new_model, device=device, 
                       class_names=['bad', 'regular', 'good'])


TEMP_DIR = "Pypline/temp_panos"
os.makedirs(TEMP_DIR, exist_ok=True)


async def predict_road_quality_async(geom_curve,
                                     road_id: str | int = 0,
                                     concurrency: int = 10):
    """
    Async version: fetches all panoramas for one road concurrently,
    then runs batched classifier inference on the successful ones.

    Args:
        geom_curve:   WKT linestring geometry from DB
        road_id:      unique identifier used for temp filenames
        concurrency:  max simultaneous Yandex requests (8–16 is safe;
                      raise carefully — Yandex may rate-limit you)
    """
    road_data = arrange_panoramas(geom_curve)
    params = road_data["way_params"]
    step = road_data["step_len"]

    # 1. Fetch all panoramas concurrently
    raw_results = await fetch_panoramas_batch(
        pano_params=params,
        output_dir=TEMP_DIR,
        road_id=road_id,
        max_distance_meters=step,
        concurrency=concurrency,
    )

    # 2. Separate successes from failures, print every result on the go
    
    successful = []
    failed = []

    for r in raw_results:
        if r["status"] == "success":
            """print(
                f"[road {road_id}] [{r['index']}] OK "
                f"lat={r['lat']:.6f} lon={r['lon']:.6f} "
                f"dir={r.get('direction_deg', '?')}° "
                f"dist={r['distance']:.1f}m"
            )"""
            successful.append(r)
        else:
            """print(
                f"[road {road_id}] [{r['index']}] {r['status']} "
                f"lat={r['lat']:.6f} lon={r['lon']:.6f} "
                f"dir={r.get('direction_deg', '?')}°"
            )"""
            failed.append(r)
    

    # 3. Batch classify all downloaded images in one shot
    #
    # ModelUser.predict_batch() is preferred when available because it pushes
    # all images through the model in a single forward pass (much faster on GPU).
    # We fall back to looping predict_image() if the method doesn't exist.
    #
    image_paths = [r["file_path"] for r in successful]
    try:
        predictions = classifier.predict_batch(image_paths)
    except AttributeError:
        # Fallback: single-image inference in a threadpool so we don't block
        # the event loop during heavy CPU/GPU work.
        loop = asyncio.get_running_loop()
        predictions = await asyncio.gather(*[
            loop.run_in_executor(None, classifier.predict_image, p)
            for p in image_paths
        ])

    # 4. Attach predictions and clean up temp files
    results = list(failed)  # start with failures

    for r, pred in zip(successful, predictions):
        #print(
        #    f"[{r['index']}] OK -> "
        #    f"class={pred}, "
        #    f"distance={r['distance']:.2f}m"
        #)
        results.append({**r, "predicted_class": pred})

        img_path = r.get("file_path")
        if img_path and os.path.exists(img_path):
            os.remove(img_path)

    results.sort(key=lambda x: x["index"])  # restore original order

    return {
        "total_points": len(params),
        "success_count": len(successful),
        "results": results,
    }


def predict_road_quality(geom_curve, road_id: str | int = 0, concurrency: int = 10):
    """
    Synchronous entry point — wraps the async version.
    Identical interface to the original function.
    """
    return asyncio.run(
        predict_road_quality_async(geom_curve, road_id=road_id, concurrency=concurrency)
    )


# ── Multi-road batch (for processing all 60 000 roads) ───────────────────────

async def process_roads_batch(road_geometries: list,
                              concurrency_per_road: int = 10,
                              road_concurrency: int = 4) -> list[dict]:
    """
    Process multiple roads concurrently.

    road_concurrency controls how many roads are in-flight at once.
    Total simultaneous Yandex requests = road_concurrency × concurrency_per_road.
    Start with road_concurrency=4, concurrency_per_road=8 (32 total) and
    increase gradually while watching for 429 / connection errors.

    Args:
        road_geometries:    list of (road_id, geom_curve) tuples
        concurrency_per_road: panorama fetch concurrency inside one road
        road_concurrency:   how many roads to process simultaneously

    Returns:
        list of result dicts, one per road
    """
    road_sem = asyncio.Semaphore(road_concurrency)

    async def _one_road(road_id, geom):
        async with road_sem:
            result = await predict_road_quality_async(
                geom,
                road_id=road_id,
                concurrency=concurrency_per_road,
            )
            return {"road_id": road_id, **result}

    tasks = [_one_road(rid, geom) for rid, geom in road_geometries]
    return await asyncio.gather(*tasks, return_exceptions=True)


def process_all_roads(road_geometries: list,
                      concurrency_per_road: int = 10,
                      road_concurrency: int = 4) -> list[dict]:
    """
    Synchronous entry point for the full 60 000-road pipeline.

    Usage:
        roads = [(road_id, wkt_geom), ...]
        results = process_all_roads(roads)
    """
    return asyncio.run(
        process_roads_batch(
            road_geometries,
            concurrency_per_road=concurrency_per_road,
            road_concurrency=road_concurrency,
        )
    )