from django.db import models
from django.contrib.auth.models import User

# Add this new model
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    last_location_update = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.user.username}'s Profile"

class Restroom(models.Model):
    STATUS_CHOICES = [
        ('Operational', 'Operational'),
        ('Maintenance', 'Maintenance'),
        ('Cleaning', 'Cleaning'),
        ('Inactive', 'Inactive'),
    ]

    restroom_id = models.CharField(max_length=50, unique=True, help_text="Unique Identifier for the restroom")
    name = models.CharField(max_length=100)
    latitude = models.FloatField(help_text="Latitude for map location")
    longitude = models.FloatField(help_text="Longitude for map location")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Operational')
    capacity = models.IntegerField(help_text="Maximum capacity of the restroom")
    last_cleaned = models.DateTimeField(null=True, blank=True)
    chat_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='restrooms')

    def __str__(self):
        return f"{self.name} ({self.restroom_id})"

class Sensor(models.Model):
    SENSOR_STATUS = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Calibration', 'Calibration'),
    ]

    sensor_id = models.CharField(max_length=50, unique=True, help_text="Unique Identifier for the sensor")
    restroom = models.ForeignKey(Restroom, on_delete=models.CASCADE, null=True, blank=True, related_name='sensors')
    sensor_type = models.CharField(max_length=50, help_text="Type of sensor (e.g. Ammonia,Footfall)")
    threshold_max = models.FloatField(null=True, blank=True, help_text="Maximum threshold value")
    status = models.CharField(max_length=20, choices=SENSOR_STATUS, default='Active')
    installed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        restroom_name = self.restroom.name if self.restroom else "Unassigned"
        return f"{self.sensor_type} ({self.sensor_id}) - {restroom_name}"

class SensorReading(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='readings')
    value = models.FloatField(help_text="Reading value")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sensor.sensor_id} - {self.value} at {self.timestamp}"

class Staff(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    shift_start = models.TimeField()
    shift_end = models.TimeField()
    role = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    restroom = models.ForeignKey(Restroom, on_delete=models.CASCADE, related_name='staff')

    def __str__(self):
        return f"{self.name} - {self.role} ({self.restroom.name if self.restroom else 'Unassigned'})"




class Alert(models.Model):
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    restroom = models.ForeignKey('Restroom', on_delete=models.CASCADE, related_name='alerts')
    sensor_reading = models.ForeignKey('SensorReading', on_delete=models.CASCADE, related_name='alerts', null=True, blank=True)

    def __str__(self):
        return f"Alert for {self.restroom.name} at {self.timestamp}"


class Feedback(models.Model):
    RATING_CHOICES = [
        (1, '1 - Very Poor'),
        (2, '2 - Poor'),
        (3, '3 - Average'),
        (4, '4 - Good'),
        (5, '5 - Excellent'),
    ]

    rating = models.IntegerField(choices=RATING_CHOICES, help_text="Rating from 1 (Very Poor) to 5 (Excellent)")
    comment = models.TextField(blank=True, null=True, help_text="Optional feedback comment")
    timestamp = models.DateTimeField(auto_now_add=True, help_text="Time when feedback was submitted")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    restroom = models.ForeignKey(Restroom, on_delete=models.CASCADE, related_name='feedbacks')

    def __str__(self):
        return f"Feedback by {self.user.username} for {self.restroom.name} - Rating: {self.rating}"

