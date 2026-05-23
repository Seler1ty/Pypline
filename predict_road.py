from panorama_planner import arrange_panoramas
from panorama_processing import get_panorama_with_view
from road_classifier import ModelUser

path_to_model = './model/model_RQCD_state_dict_43_epoch.pt'

classifier = ModelUser(path_to_model)

road_data = arrange_panoramas(road_id=1)

results = []

for i, pano in enumerate(road_data['way_params']):

    try:
        img_path = get_panorama_with_view(
            lat=pano['lat'],
            lon=pano['lon'],
            direction_deg=pano['direction_deg'],
            output_file=f'road_{i}.jpg',
            max_distance_meters=7.0
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