from panorama_planner import arrange_panoramas
from panorama_processing import get_panorama_with_view
from road_classifier import ModelUser
import os

path_to_model = './model/model_RQCD_state_dict_43_epoch.pt'

classifier = ModelUser(path_to_model)

road_data = arrange_panoramas(road_id=1)
params = road_data['way_params']
step = road_data['step_len']

results = []

for i, pano in enumerate(params):

    try:
        img_path = get_panorama_with_view(
            lat=pano['lat'],
            lon=pano['lon'],
            direction_deg=pano['direction_deg'],
            output_file=f'Pypeline/temp_panos/road_{i}.jpg',
            max_distance_meters=step
        )

        predicted_class = classifier.predict_image(img_path)

        results.append({
            'lat': pano['lat'],
            'lon': pano['lon'],
            'prediction': predicted_class
        })

        print(f'[{i}] OK -> {predicted_class}')

    except RuntimeError as e:
        print(f'[{i}] ERROR -> {e}')
    
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)