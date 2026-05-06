from django.contrib import admin
from .models import Restroom, Sensor, SensorReading, Staff, Alert

@admin.register(Restroom)
class RestroomAdmin(admin.ModelAdmin):
    list_display = ('restroom_id', 'name', 'status', 'capacity', 'last_cleaned', 'admin')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'restroom_id')

@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ('sensor_id', 'restroom', 'sensor_type', 'status', 'installed_at')
    list_filter = ('status', 'sensor_type', 'restroom')
    search_fields = ('sensor_id', 'sensor_type')

@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'value', 'timestamp')
    list_filter = ('timestamp', 'sensor')
    search_fields = ('sensor__sensor_id',)

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'email', 'phone', 'restroom', 'shift_start', 'shift_end')
    list_filter = ('role', 'restroom', 'created_at')
    search_fields = ('name', 'email')

# @admin.register(CleaningActivity)
# class CleaningActivityAdmin(admin.ModelAdmin):
#     list_display = ('activity_type', 'restroom', 'staff', 'status', 'start_time')
#     list_filter = ('status', 'restroom', 'start_time')
#     search_fields = ('activity_type', 'restroom__name', 'staff__name')

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('restroom', 'message', 'resolved', 'timestamp')
    list_filter = ('resolved', 'timestamp', 'restroom')
    search_fields = ('message', 'restroom__name')
