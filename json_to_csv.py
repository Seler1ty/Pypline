import json
import csv
from pathlib import Path
from geo_utils import coords_to_wkt_linestring

def flatten_coordinates(coords):
    """
    Convert nested coordinate arrays into a compact string.
    Useful for LineString / Polygon geometries.
    """
    return json.dumps(coords, ensure_ascii=False)

def geojson_to_csv(input_geojson, output_csv):
    input_geojson = Path(input_geojson)
    output_csv = Path(output_csv)

    # Load GeoJSON
    with input_geojson.open("r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])

    if not features:
        raise ValueError("No features found in GeoJSON file")

    # CSV columns
    fieldnames = [
        "feature_id",
        "geometry_type",
        "coordinates",
        "geometry_format"
    ]

    # Write CSV
    with output_csv.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for feature in features:
            row = {}

            # Feature ID
            row["feature_id"] = feature.get("id")

            # Geometry
            geometry = feature.get("geometry", {})
            row["geometry_type"] = geometry.get("type")
            row["coordinates"] = flatten_coordinates(
                geometry.get("coordinates")
            )
            row["geometry_format"] = coords_to_wkt_linestring(row["coordinates"])

            writer.writerow(row)

    print(f"CSV saved to: {output_csv}")


if __name__ == "__main__":
    input_file = "Pypline/raw_roads_data/RoadsEKB.geojson"
    output_file = "Pypline/prepared_roads_data/RoadsEKB.csv"

    geojson_to_csv(input_file, output_file)