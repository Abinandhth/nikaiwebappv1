from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('landing/index.html', views.index, name='index_redirect'),
    path('admin-register/', views.admin_register, name='admin_register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('activate/', views.activation, name='activation'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/data/', views.dashboard_data, name='dashboard_data'),
    path('dashboard/<str:restroom_id>/', views.dashboard, name='dashboard_with_id'),
    path('dashboard/<str:restroom_id>/data/', views.dashboard_data, name='dashboard_data_with_id'),
    path('restrooms/', views.restroom_list, name='restroom_list'),
    path('restrooms/update/<str:restroom_id>/', views.activation, name='update_restroom'),
    path('restrooms/delete/<str:restroom_id>/', views.delete_restroom, name='delete_restroom'),
    path('settings/', views.settings_view, name='settings'),
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/<str:restroom_id>/', views.staff_list, name='staff_list_with_id'),
    path('staff/add/', views.add_staff, name='add_staff'),
    path('staff/add/<str:restroom_id>/', views.add_staff, name='add_staff_to_restroom'),
    path('staff/add/<str:restroom_id>/', views.add_staff, name='add_staff_linked'),
    path('staff/edit/<int:staff_id>/', views.add_staff, name='edit_staff'),
    path('staff/delete/<int:staff_id>/', views.delete_staff, name='delete_staff'),
    # path('staff/logs/<int:staff_id>/', views.staff_logs, name='staff_logs'),
    path('alerts/', views.alerts_list, name='alerts_list'),
    path('alerts/resolve/<int:alert_id>/', views.resolve_alert, name='resolve_alert'),
    path('sensor/data/', views.sensor_data, name='sensor_data'),
    path('webhook/telegram/', views.telegram_webhook, name="telegram_webhook"),



]
