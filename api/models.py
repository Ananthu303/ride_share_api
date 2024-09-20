from django.db import models
from django.contrib.auth.models import User

class Rider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=255)
    def __str__(self):
        return f'Rider: {self.user.username} with ID {self.id}'

class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    license_number = models.CharField(max_length=255)
    vehicle_number = models.CharField(max_length=255)
    available = models.BooleanField(default=True)
    current_location = models.JSONField()

    def __str__(self):
        return f'Driver: {self.user.username} with ID {self.id}'

class Ride(models.Model):
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('started', 'Started'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    rider = models.ForeignKey(Rider, related_name='rides', on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, related_name='rides', on_delete=models.CASCADE, null=True, blank=True)
    pickup_location = models.JSONField()
    dropoff_location = models.JSONField()
    gps_location = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"USER : {self.rider.user.username}'s Ride from :{self.pickup_location} to {self.dropoff_location} ID :{self.id}"
