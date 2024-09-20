from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from .models import Driver, Ride, Rider
from .utils import get_current_location


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)
    user_type = serializers.ChoiceField(choices=["rider", "driver"], required=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    license_number = serializers.CharField(required=False, allow_blank=True)
    vehicle_number = serializers.CharField(required=False, allow_blank=True)
    current_location = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "user_type",
            "phone_number",
            "license_number",
            "vehicle_number",
            "current_location",
        ]

    def validate(self, data):
        user_type = data.get("user_type")
        errors = {}

        if user_type == "rider" and not data.get("phone_number"):
            errors["phone_number"] = ["Phone number is required for riders."]

        if user_type == "driver":
            if not data.get("license_number"):
                errors["license_number"] = ["License number is required for drivers."]
            if not data.get("vehicle_number"):
                errors["vehicle_number"] = ["Vehicle number is required for drivers."]
            if not data.get("current_location"):
                errors["current_location"] = [
                    "Current location is required for drivers."
                ]

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data["username"],
                email=validated_data["email"],
                password=validated_data["password"],
            )

            user_type = validated_data.pop("user_type")

            if user_type == "rider":
                Rider.objects.create(
                    user=user, phone_number=validated_data.get("phone_number", "")
                )
            elif user_type == "driver":

                current_location = validated_data.get("current_location", None)
                if current_location:
                    driver_lat, driver_long, driver_display_name = get_current_location(
                        current_location
                    )
                    current_location = {
                        "latitude": driver_lat,
                        "longitude": driver_long,
                        "display_name": driver_display_name,
                    }

                Driver.objects.create(
                    user=user,
                    license_number=validated_data["license_number"],
                    vehicle_number=validated_data["vehicle_number"],
                    current_location=current_location,
                )

        return user


class DriverSerializer(serializers.ModelSerializer):
    current_location = serializers.JSONField()

    class Meta:
        model = Driver
        fields = [
            "id",
            "user",
            "license_number",
            "vehicle_number",
            "available",
            "current_location",
        ]


class RideSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ride
        fields = "__all__"


class RideStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ride
        fields = ["status"]

    def validate(self, data):
        if "status" not in data:
            raise serializers.ValidationError({"status": "This field is required."})
        return data
