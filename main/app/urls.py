from django.urls import path
from app import views

urlpatterns = [
    path('', views.home, name='home'),
    path('create-user/', views.create_user, name='create_user'),
    path('attendance/', views.view_attendance, name='view_attendance'),
    path('record-attendance/', views.record_attendance, name='record_attendance'),
]
