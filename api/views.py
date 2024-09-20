import json

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import F
from django.shortcuts import redirect, render
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Driver, Ride, Rider
from .serializers import (
    DriverSerializer,
    RegisterSerializer,
    RideSerializer,
    RideStatusUpdateSerializer,
)
from .utils import find_nearest_driver, get_current_location, haversine


class RegisterView(APIView):

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Register a new user as a rider or driver.
        """
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "success": f"Registration successful ! Welcome {user.username}",
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """
        Log in a user and return access and refresh tokens.
        """
        username = request.data.get("username")
        password = request.data.get("password")
        user_type = request.data.get("type")
        user = authenticate(username=username, password=password)
        if user is not None:
            token = RefreshToken.for_user(user)
            user_id = user.id
            rider = Rider.objects.filter(user=user).first()
            if rider:
                self.save_tokens_to_json(
                    username, user_id, str(token.access_token), str(token)
                )
            return Response(
                {
                    "refresh": str(token),
                    "access": str(token.access_token),
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"error": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED
        )

    def save_tokens_to_json(self, username, user_id, access_token, refresh_token):
        """
        Creates a token file for the rider and saves the tokens as JSON.
        """
        tokens_data = {}

        try:
            with open("rider_tokens.json", "r") as file:
                tokens_data = json.load(file)
        except FileNotFoundError:
            pass
        tokens_data[username] = {
            "user_id": user_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

        with open("rider_tokens.json", "w") as file:
            json.dump(tokens_data, file)


class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        drive = self.get_object()
        try:
            driver = Driver.objects.get(pk=drive.id)
            serializer = DriverSerializer(driver)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Driver.DoesNotExist:
            return Response(
                {"error": "Driver not found"}, status=status.HTTP_404_NOT_FOUND
            )

    def update(self, request, *args, **kwargs):
        """Update the driver's current location using username."""
        drive = self.get_object()

        try:
            driver = Driver.objects.get(pk=drive.id)
            data = request.data.copy()

            username = data.get("user")
            if username:
                try:
                    user = User.objects.get(username=username)
                    data["user"] = user.id
                except User.DoesNotExist:
                    return Response(
                        {"error": "User does not exist"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            location_string = data.get("current_location")
            if location_string:
                driver_lat, driver_long, driver_display_name = get_current_location(
                    location_string
                )
                location_data = {
                    "latitude": driver_lat,
                    "longitude": driver_long,
                    "display_name": driver_display_name,
                }
                data["current_location"] = json.dumps(location_data)

            serializer = DriverSerializer(driver, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Driver.DoesNotExist:
            return Response(
                {"error": "Driver not found"}, status=status.HTTP_404_NOT_FOUND
            )

    def destroy(self, request, *args, **kwargs):
        """Delete Driver"""
        try:
            driver = self.get_object()
            driver.delete()
            return Response(
                {"message": "Driver deleted successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Driver.DoesNotExist:
            return Response(
                {"error": "Driver not found"}, status=status.HTTP_404_NOT_FOUND
            )


class RideViewSet(viewsets.ModelViewSet):
    queryset = Ride.objects.all()
    serializer_class = RideSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        """Returns a list of ride requests for the authenticated user."""
        queryset = self.get_queryset().filter(rider__user=request.user)
        print("Login user", request.user.username)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Creates a new ride request for the authenticated user if they do not
        already have a ride request that is currently requested."""
        print("Login user", request.user.username)
        existing_ride = Ride.objects.filter(
            rider__user=request.user, status="requested"
        ).first()
        if existing_ride:
            return Response(
                {
                    "error": "You already have a ride request that is currently requested. Please cancel it before creating a new one."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = request.data.copy()
        pickup_location = data.get("pickup_location")
        dropoff_location = data.get("dropoff_location")
        ride_status = data.get("status")
        if ride_status:
            return Response(
                {"error": "ride_status setting while creation not allowed"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not pickup_location and not dropoff_location:
            return Response(
                {"error": "pickup_location and dropoff_location is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not pickup_location:
            return Response(
                {"error": "pickup_location is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not dropoff_location:
            return Response(
                {"error": "dropoff_location is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        country = "India"
        pickup_location = f"{pickup_location} {country}"
        dropoff_location = f"{dropoff_location} {country}"
        pickup_lat, pickup_long, pickup_display_name = get_current_location(
            pickup_location
        )
        dropoff_lat, dropoff_long, dropoff_display_name = get_current_location(
            dropoff_location
        )

        if pickup_lat is None or dropoff_lat is None:
            return Response(
                {"error": "Invalid location data"}, status=status.HTTP_400_BAD_REQUEST
            )

        pickup_location_data = {
            "latitude": pickup_lat,
            "longitude": pickup_long,
            "display_name": pickup_display_name,
        }
        data["pickup_location"] = json.dumps(pickup_location_data)

        dropoff_location_data = {
            "latitude": dropoff_lat,
            "longitude": dropoff_long,
            "display_name": dropoff_display_name,
        }
        data["dropoff_location"] = json.dumps(dropoff_location_data)

        print(request.user.username, "<-------------user")
        data["rider"] = request.user.rider.id
        serializer = RideSerializer(data=data)
        if serializer.is_valid():
            serializer.save(rider=request.user.rider)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Cancel a ride request for the authenticated user."""
        ride = self.get_object()
        if ride.rider.user != request.user:
            return Response(
                {"error": "You are not authorized to update this ride."},
                status=status.HTTP_403_FORBIDDEN,
            )
        data = request.data.copy()
        pickup_location = data.get("pickup_location")
        dropoff_location = data.get("dropoff_location")
        if pickup_location:
            return Response(
                {"error": "Unable to edit pick up location once created"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if dropoff_location:
            return Response(
                {"error": "Unable to edit drop location once created"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if "status" not in data:
            return Response(
                {"error": "Only the status field can be updated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_status = data.get("status")
        if new_status != "cancelled":
            return Response(
                {"error": "The status can only be updated to 'cancelled'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = RideSerializer(ride, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        """Fetch a ride request."""
        try:
            ride = self.get_object()
            serializer = RideSerializer(ride)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Driver.DoesNotExist:
            return Response(
                {"error": "Ride not found"}, status=status.HTTP_404_NOT_FOUND
            )

    def destroy(self, request, *args, **kwargs):
        """Delete a ride request"""
        ride = self.get_object()
        ride.delete()
        return Response(
            {"success": "Ride successfully deleted."}, status=status.HTTP_204_NO_CONTENT
        )


def current_gps_location(request):
    return render(request, "gps.html")


class RideRequestViewSet(viewsets.ModelViewSet):
    queryset = Ride.objects.all()
    serializer_class = RideSerializer

    def list(self, request, *args, **kwargs):
        """
        This function is for listing nearby rides up to 40 km for driver.
        """
        try:
            driver = request.user.driver
        except:
            return Response(
                {"error": "User does not have a driver profile."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        driver_lat = driver.current_location["latitude"]
        driver_long = driver.current_location["longitude"]

        nearby_rides = Ride.objects.filter(status="requested")
        nearby_rides_data = []

        for ride in nearby_rides:
            pickup_lat = ride.pickup_location["latitude"]
            pickup_long = ride.pickup_location["longitude"]
            distance = haversine(driver_lat, driver_long, pickup_lat, pickup_long)

            if distance <= 40:
                rounded_distance = round(distance)
                ride_data = RideSerializer(ride).data
                ride_data["distance_to_customer"] = f"{rounded_distance}km"
                nearby_rides_data.append(ride_data)

        return Response(nearby_rides_data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """
        Accept a ride request using the ride_id.
        """
        ride_id = request.data.get("ride_id")
        if not ride_id:
            raise serializers.ValidationError({"ride_id": "This field is required."})
        try:
            ride = Ride.objects.get(id=ride_id, status="requested")
        except Ride.DoesNotExist:
            return Response(
                {"error": "Ride request not found or already accepted."},
                status=status.HTTP_404_NOT_FOUND,
            )
        driver = request.user.driver
        if not driver:
            return Response(
                {"error": "User does not have a driver profile."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if ride.driver == driver:
            return Response(
                {"error": "This Ride is already assigned to you"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if ride.driver:
            return Response(
                {"error": "This Ride request has already been assigned"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ride.driver = driver
        ride.status = "accepted"
        ride.save()

        driver.available = False
        driver.save()

        return Response(
            {"message": "Ride accepted successfully."}, status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        """
        Update the status of a ride assigned to the driver.
        """
        pk = kwargs.get("pk")
        try:
            ride = Ride.objects.get(id=pk, driver=request.user.driver)
        except Ride.DoesNotExist:
            return Response(
                {"error": "Ride not found or you are not assigned to this ride."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RideStatusUpdateSerializer(ride, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Ride status updated successfully.",
                    "ride": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
