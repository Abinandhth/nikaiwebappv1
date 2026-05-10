from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Restroom, Sensor, Staff,Alert
import uuid

def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing/index.html')

@login_required
def activation(request, restroom_id=None):
    # Determine mode: Create or Update
    mode = 'create'
    restroom = None
    ammonia_sensor = None
    smoke_sensor = None
    footfall_sensor = None
    moisture_sensor = None
    
    if restroom_id:
        try:
            restroom = request.user.restrooms.get(restroom_id=restroom_id)
            mode = 'update'
            # Fetch existing sensors for pre-filling
            ammonia_sensor = restroom.sensors.filter(sensor_type='Ammonia').first()
            smoke_sensor = restroom.sensors.filter(sensor_type='Smoke').first()
            footfall_sensor = restroom.sensors.filter(sensor_type='Footfall').first()
            moisture_sensor = restroom.sensors.filter(sensor_type='Moisture').first()
        except Restroom.DoesNotExist:
             return redirect('restroom_list')

    if request.method == 'POST':
        try:
            name = request.POST.get('restroom_name')
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            capacity = request.POST.get('capacity')
            chat_id = request.POST.get('chat_id')
            status = request.POST.get('status')
            
            # Check if sensor IDs already exist before saving
            if mode == 'create':
                sensor_fields = ['sensor_ammonia', 'sensor_smoke', 'sensor_footfall','sensor_moisture']
                for field in sensor_fields:
                    sid = request.POST.get(field)
                    if sid:
                        existing_sensor = Sensor.objects.filter(sensor_id=sid).first()
                        if existing_sensor:
                            raise ValueError(f"Sensor ID '{sid}' is already assigned to another facility.")
            
            if mode == 'create':
                 # Create Restroom
                restroom = Restroom.objects.create(
                    restroom_id=f"R-{str(uuid.uuid4())[:8]}", 
                    name=name,
                    latitude=float(latitude),
                    longitude=float(longitude),
                    capacity=int(capacity),
                    chat_id=int(chat_id),   
                    status=status,
                    admin=request.user
                )
            else:
                 # Update Restroom
                restroom.name = name
                restroom.latitude = float(latitude)
                restroom.longitude = float(longitude)
                restroom.capacity = int(capacity)
                restroom.chat_id = int(chat_id)
                restroom.status = status
                restroom.admin = request.user
                restroom.save()

            # Link/Update Sensors
            if mode == 'create':
                sensor_map = {
                    'sensor_ammonia': 'Ammonia',
                    'sensor_smoke': 'Smoke',
                    'sensor_footfall': 'Footfall',
                    'sensor_moisture': 'Moisture'
                }
                
                for field, type_name in sensor_map.items():
                    sid = request.POST.get(field)
                    if sid:
                        Sensor.objects.create(
                            sensor_id=sid,
                            sensor_type=type_name, 
                            restroom=restroom
                        )
            
            return redirect('restroom_list')

        except Exception as e:
             # helpful for debugging if something goes wrong
             print(f"Error in activation: {e}")
             
             # Retain form values on error
             class DummySensor:
                 def __init__(self, sensor_id):
                     self.sensor_id = sensor_id
                     
             error_ammonia = DummySensor(request.POST.get('sensor_ammonia')) if request.POST.get('sensor_ammonia') else ammonia_sensor
             error_smoke = DummySensor(request.POST.get('sensor_smoke')) if request.POST.get('sensor_smoke') else smoke_sensor
             error_footfall = DummySensor(request.POST.get('sensor_footfall')) if request.POST.get('sensor_footfall') else footfall_sensor
             error_moisture = DummySensor(request.POST.get('sensor_moisture')) if request.POST.get('sensor_moisture') else moisture_sensor
             
             class DummyRestroom:
                 def __init__(self, name, lat, lng, cap, chat_id, stat):
                     self.name = name
                     self.latitude = lat
                     self.longitude = lng
                     self.capacity = cap
                     self.chat_id = chat_id
                     self.status = stat
                     
             error_restroom = DummyRestroom(
                 request.POST.get('restroom_name'),
                 request.POST.get('latitude'),
                 request.POST.get('longitude'),
                 request.POST.get('capacity'),
                 request.POST.get('chat_id'),
                 request.POST.get('status')
             ) if request.POST else restroom
             
             error_msg = str(e)
             if "Error processing request:" in error_msg:
                 error_msg = error_msg.replace("Error processing request: ", "")
                 
             return render(request, 'landing/activation.html', {
                 'error': error_msg,
                 'mode': mode,
                 'restroom': error_restroom,
                 'ammonia_sensor': error_ammonia,
                 'smoke_sensor': error_smoke,
                 'footfall_sensor': error_footfall,
                 'moisture_sensor':error_moisture
             })

    return render(request, 'landing/activation.html', {
        'mode': mode,
        'restroom': restroom,
        'ammonia_sensor': ammonia_sensor,
        'smoke_sensor': smoke_sensor,
        'footfall_sensor': footfall_sensor,
        'moisture_sensor':moisture_sensor
    })

from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Count
from django.db.models.functions import TruncDay, TruncHour

@login_required
def dashboard(request, restroom_id=None):
    try:
        if restroom_id:
            restroom = request.user.restrooms.get(restroom_id=restroom_id)
        else:
            restroom = request.user.restrooms.first()
            
        if not restroom:
            return redirect('activation')
    except Restroom.DoesNotExist:
         # If specific ID not found, fallback to first or list
         return redirect('restroom_list')
    except Exception:
        return redirect('activation')

    # Date Filter
    date_str = request.GET.get('date')
    if date_str:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        selected_date = timezone.now().date()

    # Sensors
    ammonia_sensor = restroom.sensors.filter(sensor_type='Ammonia').first()
    footfall_sensor = restroom.sensors.filter(sensor_type='Footfall').first()
    moisture_sensor = restroom.sensors.filter(sensor_type='Moisture').first()
    smoke_sensor = restroom.sensors.filter(sensor_type='Smoke').first()

    moisture_threshold = moisture_sensor.threshold_max if moisture_sensor else 1000
    smoke_threshold = smoke_sensor.threshold_max if smoke_sensor else 800
    ammonia_threshold = ammonia_sensor.threshold_max if ammonia_sensor else 600
    
    # Moisture Data
    current_moisture = 0
    floor_status = 'Unknown'

    if moisture_sensor:
        latest_reading = moisture_sensor.readings.filter(timestamp__date=selected_date).order_by('-timestamp').first()
        if latest_reading:
            current_moisture = latest_reading.value
            if current_moisture < moisture_threshold:
                floor_status = 'Dry'
            else:
                floor_status = 'Wet'

    # Smoke Data
    current_smoke = 0
    safety_status = 'Unknown'

    if smoke_sensor:
        latest_smoke = smoke_sensor.readings.filter(timestamp__date=selected_date).order_by('-timestamp').first()
        if latest_smoke:
            current_smoke = latest_smoke.value
            if current_smoke > smoke_threshold:
                safety_status = 'Caution'
            else:
                safety_status = 'Safe / Clear'

    # 1. Ammonia Data (Today/Selected Date)
    ammonia_labels = []
    ammonia_data = []
    current_ammonia = 0
    ammonia_status = 'Normal'

    if ammonia_sensor:
        readings = ammonia_sensor.readings.filter(timestamp__date=selected_date).order_by('timestamp')
        ammonia_labels = [r.timestamp.strftime('%H:%M') for r in readings]
        ammonia_data = [r.value for r in readings]
        if readings.exists():
            current_ammonia = round(sum(ammonia_data) / len(ammonia_data), 1)
            if current_ammonia > ammonia_threshold:
                ammonia_status = 'Critical'

    # 2. Footfall Data (Daily - Hourly)
    footfall_daily_labels = []
    footfall_daily_data = []
    total_footfall_today = 0

    if footfall_sensor:
        daily_readings = footfall_sensor.readings.filter(timestamp__date=selected_date).order_by('timestamp')
        
        if daily_readings.exists():
            # Arduino provides the cumulative value, so take the latest reading for total
            latest_reading = daily_readings.last()
            total_footfall_today = int(latest_reading.value)
            
            # Use raw values for the graph
            footfall_daily_labels = [r.timestamp.strftime('%H:%M') for r in daily_readings]
            footfall_daily_data = [int(r.value) for r in daily_readings]

    # 3. Footfall Data (Monthly)
    footfall_monthly_labels = []
    footfall_monthly_data = []
    
    if footfall_sensor:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        monthly_readings = footfall_sensor.readings.filter(timestamp__date__range=[start_date, end_date])
        
        # Aggregate by day
        # Note: SQLite handling of dates can be tricky with Django aggregation sometimes, but works mostly.
        # If this fails with strict database backends, we might need specific DB functions.
        # For simple prototype, let's iterate.
        daily_counts = {}
        for r in monthly_readings:
            day_str = r.timestamp.strftime('%d %b')
            daily_counts[day_str] = daily_counts.get(day_str, 0) + int(r.value)
        
        footfall_monthly_labels = list(daily_counts.keys())
        footfall_monthly_data = list(daily_counts.values())

    return render(request, 'landing/dashboard.html', {
        'restroom': restroom,
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'current_ammonia': current_ammonia,
        'ammonia_status': ammonia_status,
        'ammonia_labels': ammonia_labels,
        'ammonia_data': ammonia_data,
        'total_footfall_today': total_footfall_today,
        'footfall_daily_labels': footfall_daily_labels,
        'footfall_daily_data': footfall_daily_data,
        'footfall_monthly_labels': footfall_monthly_labels,
        'footfall_monthly_data': footfall_monthly_data,
        'current_moisture': current_moisture,
        'floor_status': floor_status,
        'current_smoke': current_smoke,
        'safety_status': safety_status,
        'page': 'overview',
        'ammonia_threshold':ammonia_threshold,
        'smoke_threshold':smoke_threshold,
        'moisture_threshold':moisture_threshold,
    })

@login_required
def dashboard_data(request, restroom_id=None):
    try:
        if restroom_id:
            restroom = request.user.restrooms.get(restroom_id=restroom_id)
        else:
            restroom = request.user.restrooms.first()
            
        if not restroom:
            return JsonResponse({'error': 'No restroom found'}, status=404)
    except Restroom.DoesNotExist:
         return JsonResponse({'error': 'Restroom not found'}, status=404)
    except Exception:
        return JsonResponse({'error': 'Error fetching restroom'}, status=404)

    # Date Filter
    date_str = request.GET.get('date')
    if date_str:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        selected_date = timezone.now().date()

    # Sensors
    ammonia_sensor = restroom.sensors.filter(sensor_type='Ammonia').first()
    footfall_sensor = restroom.sensors.filter(sensor_type='Footfall').first()
    moisture_sensor = restroom.sensors.filter(sensor_type='Moisture').first()
    smoke_sensor = restroom.sensors.filter(sensor_type='Smoke').first()

    moisture_threshold = moisture_sensor.threshold_max if moisture_sensor else 1000
    smoke_threshold = smoke_sensor.threshold_max if smoke_sensor else 800
    ammonia_threshold = ammonia_sensor.threshold_max if ammonia_sensor else 600

    # Moisture Data
    current_moisture = 0
    floor_status = 'Unknown'
    if moisture_sensor:
        latest_reading = moisture_sensor.readings.filter(timestamp__date=selected_date).order_by('-timestamp').first()
        if latest_reading:
            current_moisture = latest_reading.value
            if current_moisture < moisture_threshold:
                floor_status = 'Dry'
            else:
                floor_status = 'Wet'

    # Smoke Data
    current_smoke = 0
    safety_status = 'Unknown'
    if smoke_sensor:
        latest_smoke = smoke_sensor.readings.filter(timestamp__date=selected_date).order_by('-timestamp').first()
        if latest_smoke:
            current_smoke = latest_smoke.value
            if current_smoke > smoke_threshold:
                safety_status = 'Caution'
            else:
                safety_status = 'Safe / Clear'

    # Ammonia Data
    ammonia_labels = []
    ammonia_data = []
    current_ammonia = 0
    ammonia_status = 'Normal'
    if ammonia_sensor:
        readings = ammonia_sensor.readings.filter(timestamp__date=selected_date).order_by('timestamp')
        ammonia_labels = [r.timestamp.strftime('%H:%M') for r in readings]
        ammonia_data = [r.value for r in readings]
        if readings.exists():
            current_ammonia = round(sum(ammonia_data) / len(ammonia_data), 1)
            if current_ammonia > ammonia_threshold:
                ammonia_status = 'Critical'

    # Footfall Data (Daily)
    footfall_daily_labels = []
    footfall_daily_data = []
    total_footfall_today = 0
    if footfall_sensor:
        daily_readings = footfall_sensor.readings.filter(timestamp__date=selected_date).order_by('timestamp')
        if daily_readings.exists():
            # Arduino provides the cumulative value, so take the latest reading for total
            latest_reading = daily_readings.last()
            total_footfall_today = int(latest_reading.value)
            
            # Use raw values for the graph
            footfall_daily_labels = [r.timestamp.strftime('%H:%M') for r in daily_readings]
            footfall_daily_data = [int(r.value) for r in daily_readings]

    return JsonResponse({
        'current_ammonia': current_ammonia,
        'ammonia_status': ammonia_status,
        'ammonia_labels': ammonia_labels,
        'ammonia_data': ammonia_data,
        'total_footfall_today': total_footfall_today,
        'footfall_daily_labels': footfall_daily_labels,
        'footfall_daily_data': footfall_daily_data,
        'current_moisture': current_moisture,
        'floor_status': floor_status,
        'current_smoke': current_smoke,
        'safety_status': safety_status,
        'ammonia_threshold':ammonia_threshold,
        'smoke_threshold':smoke_threshold,
        'moisture_threshold':moisture_threshold,
    })

@login_required
def restroom_list(request):
    restrooms = request.user.restrooms.all()
    if not restrooms.exists():
        return redirect('activation')
        
    return render(request, 'landing/restroom_list.html', {
        'restrooms': restrooms,
        'page': 'restrooms'
    })

@login_required
def settings_view(request):
    restrooms = request.user.restrooms.all()
    
    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('sensor_') and key.endswith('_threshold_max'):
                try:
                    sensor_id = key.split('_')[1] # Extracts ID from sensor_{id}_threshold_max
                    sensor = Sensor.objects.get(id=sensor_id, restroom__admin=request.user)
                    if value:
                        sensor.threshold_max = float(value)
                    else:
                        sensor.threshold_max = None
                    sensor.save()
                except (ValueError, Sensor.DoesNotExist):
                    continue
        messages.success(request, 'Settings have been updated successfully.')
        return redirect('settings')
        
    return render(request, 'landing/settings.html', {
        'page': 'settings',
        'restrooms': restrooms
    })

@login_required
def staff_list(request, restroom_id=None):
    try:
        if restroom_id:
            restroom = request.user.restrooms.get(restroom_id=restroom_id)
        else:
            restroom = request.user.restrooms.first()
            
        if not restroom:
            return redirect('activation')
    except Restroom.DoesNotExist:
         return redirect('restroom_list')

    # Fetch staff
    staff_members = restroom.staff.all().order_by('-created_at')
    
    # Calculate status (mock logic: if within shift hours, they are 'On Duty')
    now_time = timezone.now().time()
    for staff in staff_members:
        # Simple check: start <= now <= end. Does not handle overnight shifts perfectly but sufficient for MVP.
        if staff.shift_start <= now_time <= staff.shift_end:
            staff.status = 'On Duty'
            staff.status_class = 'status-duty'
        else:
            staff.status = 'Offline'
            staff.status_class = 'status-offline'
            
        # Infer Department
        if 'Tech' in staff.role or 'Engineer' in staff.role:
            staff.department = 'Engineering'
        elif 'Admin' in staff.role:
            staff.department = 'Operations'
        elif 'Cleaner' in staff.role or 'Janitor' in staff.role:
            staff.department = 'Services'
        else:
            staff.department = 'General'

    return render(request, 'landing/staff_list.html', {
        'restrooms': request.user.restrooms.all(),
        'restroom': restroom,
        'staff_members': staff_members,
        'page': 'staff'
    })

@login_required
def add_staff(request, staff_id=None, restroom_id=None):
    
    # 1. Setup Defaults
    mode = 'create'
    staff = None
    restrooms = request.user.restrooms.all()
    selected_restroom_id = None

    # 2. Determine Mode: Edit vs Create
    if staff_id:
        # EDIT MODE: We are editing an existing employee
        mode = 'update'
        try:
            staff = Staff.objects.get(id=staff_id)
            selected_restroom_id = staff.restroom.restroom_id
        except Staff.DoesNotExist:
            return redirect('staff_list')
            
    elif restroom_id:
        # CREATE MODE (Pre-selected): We are adding new staff specifically for this restroom
        selected_restroom_id = restroom_id
    
    # (Optional fallback) Check GET parameters if not passed in URL
    if not selected_restroom_id:
        selected_restroom_id = request.GET.get('restroom_id')

    # 3. Handle Form Submission
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            role = request.POST.get('role')
            target_restroom_id = request.POST.get('restroom')
            shift_start = request.POST.get('shift_start')
            shift_end = request.POST.get('shift_end')
            
            # Get the assigned restroom object
            assigned_restroom = restrooms.get(restroom_id=target_restroom_id)

            if mode == 'create':
                # --- CREATE NEW STAFF ---
                nfc_placeholder = f"NFC-{uuid.uuid4().hex[:8].upper()}"
                Staff.objects.create(
                    name=name,
                    email=email,
                    phone=phone,
                    role=role,
                    restroom=assigned_restroom,
                    shift_start=shift_start,
                    shift_end=shift_end,
                    nfc_tag=nfc_placeholder
                )
            else:
                # --- UPDATE EXISTING STAFF ---
                staff.name = name
                staff.email = email
                staff.phone = phone
                staff.role = role
                staff.restroom = assigned_restroom
                staff.shift_start = shift_start
                staff.shift_end = shift_end
                staff.save()
            
            # Redirect to list
            return redirect('staff_list_with_id', restroom_id=assigned_restroom.restroom_id)

        except Exception as e:
            print(f"Error processing staff: {e}")
            return render(request, 'landing/add_staff.html', {
                'mode': mode,
                'staff': staff,
                'restrooms': restrooms,
                'selected_restroom_id': selected_restroom_id,
                'error': f"Error: {e}"
            })

    # 4. Render the Page (GET Request)
    return render(request, 'landing/add_staff.html', {
        'mode': mode,
        'staff': staff,
        'restrooms': restrooms,
        'selected_restroom_id': selected_restroom_id
    })



@login_required
def delete_staff(request, staff_id):
    if request.method == 'POST':
        try:
            staff = Staff.objects.get(id=staff_id)
            # Ensure the staff belongs to a restroom owned by the user
            if staff.restroom.admin == request.user:
                staff.delete()
        except Staff.DoesNotExist:
            pass
    
    # Redirect back to the previous page to maintain context (e.g., filters)
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('staff_list')

@login_required
def delete_restroom(request, restroom_id):
    if request.method == 'POST':
        try:
            restroom = request.user.restrooms.get(restroom_id=restroom_id)
            restroom.delete()
        except Restroom.DoesNotExist:
            pass
    return redirect('restroom_list')

def admin_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            return render(request, 'landing/admin_register.html', {'error': 'Passwords do not match'})

        if User.objects.filter(username=username).exists():
            return render(request, 'landing/admin_register.html', {'error': 'Username already exists'})

        if User.objects.filter(email=email).exists():
            return render(request, 'landing/admin_register.html', {'error': 'Email already exists'})

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.is_staff = True
            user.save()
            # Redirect to login
            return redirect('login') 
        except Exception as e:
             return render(request, 'landing/admin_register.html', {'error': f'Error creating account: {e}'})

    return render(request, 'landing/admin_register.html')

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    
    return render(request, 'landing/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('index')

# @login_required
# def staff_logs(request, staff_id):
#     try:
#         staff = Staff.objects.get(id=staff_id)
#         # Ensure user is admin of the restroom this staff belongs to
#         if staff.restroom.admin != request.user:
#              return redirect('staff_list')
#     except Staff.DoesNotExist:
#         return redirect('staff_list')

#     # Calculate status
#     now_time = timezone.now().time()
#     # Simple check: start <= now <= end.
#     if staff.shift_start <= now_time <= staff.shift_end:
#         staff.status = 'On Duty'
#     else:
#         staff.status = 'Off Duty'

#     # Date Filter
#     date_str = request.GET.get('date')
#     if date_str:
#         selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
#     else:
#         # Default to today or None? Dashboard defaults to today, but logs might be better to default to all or today?
#         # User said "work similar to dashboard", so default to today might be best, OR "Recent logs" implies all recent.
#         # However, to filter by date usually implies showing a specific day.
#         # Let's default to today to match Dashboard behavior exactly as requested.
#         selected_date = timezone.now().date()

#     # Fetch logs
#     logs = CleaningActivity.objects.filter(staff=staff, start_time__date=selected_date).order_by('-start_time')
    
#     # Calculate duration for display
#     for log in logs:
#         if log.end_time:
#             duration = log.end_time - log.start_time
#             log.duration_minutes = int(duration.total_seconds() / 60)
#         else:
#             log.duration_minutes = None

#     return render(request, 'landing/staff_logs.html', {
#         'staff': staff,
#         'logs': logs,
#         'selected_date': selected_date.strftime('%Y-%m-%d')
#     })

@login_required
def alerts_list(request):
    alerts = Alert.objects.filter(restroom__admin=request.user).order_by('-timestamp')
    return render(request, 'landing/alerts.html', {
        'alerts': alerts,
        'page': 'alerts'
    })

@login_required
def resolve_alert(request, alert_id):
    if request.method == 'POST':
        try:
            alert = Alert.objects.get(id=alert_id, restroom__admin=request.user)
            alert.resolved = True
            alert.save()
            return JsonResponse({'status': 'success', 'message': 'Alert marked as resolved.'})
        except Alert.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Alert not found or unauthorized.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)










from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Sensor, SensorReading, Alert
import json
import requests
import time

from django.conf import settings

TELEGRAM_TOKEN = settings.TELEGRAM_BOT_TOKEN
ALERT_DELAY = 300

# stores last alert time for each sensor
last_alert_times = {}

def send_telegram_alert(message, chat_id):
    if not chat_id:
        print("No chat id")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message
    }

    try:
        requests.post(url, data=payload)
        print("Telegram alert sent")
    except Exception as e:
        print(f"Telegram error: {e}")

@csrf_exempt

def sensor_data(request):

    if request.method != 'POST':
        return JsonResponse({
            'error': 'POST request required'
        }, status=400)

    try:
        data = json.loads(request.body)

        sensor_id = data.get('sensor_id')
        value = data.get('value')

        if sensor_id is None or value is None:
             return JsonResponse({
                'error': 'sensor_id and value required'
            }, status=400)

        sensor = Sensor.objects.filter(sensor_id=sensor_id).first()
        if not sensor:
            return JsonResponse({
                'error': 'Sensor not found'
            }, status=404)

        # SAVE READING
        reading = SensorReading.objects.create(
            sensor=sensor,
            value=value
        )

        print(f"Saved reading: {sensor_id} = {value}")

        # THRESHOLD CHECK
        threshold = sensor.threshold_max or 600

        current_time = time.time()

        if float(value) > threshold:

            alert_key = sensor_id
            last_alert_time = last_alert_times.get(alert_key, 0)

            # avoid spam alerts
            if current_time - last_alert_time >= ALERT_DELAY:

                restroom = sensor.restroom

                msg = (
                    f"🚨 ALERT\n"
                    f"Restroom: {restroom.name}\n"
                    f"Sensor: {sensor.sensor_type}\n"
                    f"Value: {value}\n"
                    f"Threshold: {threshold}"
                )

                alert = Alert.objects.create(
                    message=msg,
                    restroom=restroom,
                    sensor_reading=reading
                )

                chat_id = restroom.chat_id

                if chat_id:
                    send_telegram_alert(msg, chat_id)

                last_alert_times[alert_key] = current_time

        return JsonResponse({
            'message': 'Data received successfully'
        })

    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)











from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now

from .models import Restroom, Alert

import json
import requests
import time

# =====================================================
# TELEGRAM CONFIG
# =====================================================

BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# =====================================================
# SEND TELEGRAM MESSAGE
# =====================================================

def send_message(chat_id, text):

    url = f"{BASE_URL}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    try:
        requests.post(url, data=payload)

    except Exception as e:
        print(f"Telegram send error: {e}")

# =====================================================
# TELEGRAM WEBHOOK
# =====================================================

@csrf_exempt
def telegram_webhook(request):

    if request.method != "POST":

        return JsonResponse({
            "error": "POST request required"
        })

    try:

        data = json.loads(request.body)

        print("\nTelegram update received")
        print(data)

        # =============================================
        # CHECK MESSAGE EXISTS
        # =============================================

        if "message" not in data:

            return JsonResponse({
                "message": "No message found"
            })

        message = data["message"]

        chat_id = str(message["chat"]["id"])

        text = message.get(
            "text",
            ""
        ).strip().lower()

        print(f"Chat ID: {chat_id}")
        print(f"Text: {text}")

        # =============================================
        # RESOLVED COMMAND
        # =============================================

        if text == "resolved":

            restroom = Restroom.objects.filter(
                chat_id=chat_id
            ).first()

            if not restroom:

                send_message(
                    chat_id,
                    "❌ No restroom linked to this group."
                )

                return JsonResponse({
                    "message": "No restroom linked"
                })

            today = now().date()

            updated_count = Alert.objects.filter(
                restroom=restroom,
                timestamp__date=today,
                resolved=False
            ).update(resolved=True)

            send_message(
                chat_id,
                (
                    f"✅ {updated_count} alerts "
                    f"marked resolved for today."
                )
            )

        return JsonResponse({
            "message": "Webhook processed"
        })

    except Exception as e:

        print(f"Webhook error: {e}")

        return JsonResponse({
            "error": str(e)
        }, status=500)