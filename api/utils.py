import json
from math import atan2, cos, radians, sin, sqrt

import requests


def haversine(lat1, lon1, lat2, lon2):
    lat1 = float(lat1)
    lon1 = float(lon1)
    lat2 = float(lat2)
    lon2 = float(lon2)
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance


def get_current_location(location_input):
    try:
        response = requests.get(
            f"https://us1.locationiq.com/v1/search?key=pk.b31d430a9f9daaf38d972aa195a016ed&q={location_input}&format=json&"
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            print("No results found for the given location.")
            return None, None, None

        first_item = data[0]
        latitude = first_item.get("lat")
        longitude = first_item.get("lon")
        display_name = first_item.get("display_name")

        if latitude and longitude:
            return latitude, longitude, display_name
        else:
            print("Latitude and/or longitude not found.")
            return None, None, None
    except Exception as err:
        print(f"An error occurred: {err}")
        return None, None, None


def find_nearest_driver(pickup_lat, pickup_long):
    drivers = Driver.objects.filter(available=True)
    nearest_driver = None
    min_distance = float("inf")

    for driver in drivers:
        driver_lat = driver.current_location["latitude"]
        driver_long = driver.current_location["longitude"]
        distance = haversine(pickup_lat, pickup_long, driver_lat, driver_long)

        if distance < min_distance:
            min_distance = distance
            nearest_driver = driver

    return nearest_driver


def get_user_id_from_json():
    try:
        with open("rider_tokens.json", "r") as file:
            data = json.load(file)
        return list(data.values())[0]["user_id"]
    except Exception as e:
        print(e)
