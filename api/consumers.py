# consumers.py
import json
import os

import django
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from .utils import get_user_id_from_json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rideshare.settings")
django.setup()
import threading

from .models import Ride, Rider
from .utils import get_user_id_from_json

User = get_user_model()


class LocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        location_data = {"latitude": data["latitude"], "longitude": data["longitude"]}

        user_id = get_user_id_from_json()

        thread = threading.Thread(target=self.fetch_ride, args=(user_id, location_data))
        thread.start()

        await self.send(
            text_data=json.dumps(
                {
                    "message": "Location received",
                    "latitude": data["latitude"],
                    "longitude": data["longitude"],
                }
            )
        )

    def fetch_ride(self, user_id, location_data):
        try:
            ride = (
                Ride.objects.exclude(status__in=["completed", "cancelled"])
                .select_related("rider")
                .get(rider__user__id=user_id)
            )
            user = ride.rider.user
            print(ride, "<<--------ride------------>>")
            print(user, "<<----------user--------->>")
            if isinstance(ride.gps_location, list):
                current_location = ride.gps_location
            else:
                current_location = []
            current_location.append(location_data)
            ride.gps_location = current_location
            ride.save()
            with open("location_data.json", "w") as f:
                json.dump(location_data, f)

        except Exception as e:
            pass
