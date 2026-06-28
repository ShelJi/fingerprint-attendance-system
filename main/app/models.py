from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    phone = models.CharField(max_length=15, blank=True)
    profile_image = models.ImageField(upload_to="profiles/", blank=True, null=True)
    fingerprint_data = models.IntegerField(unique=True)
    
    # FUTURE UPDATES
    # total_attendance = 
    # total_worked_hours = 
    # total_worked_days =

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        
        
class Attendance(models.Model):
    user = models.ForeignKey("app.User", on_delete=models.CASCADE)
    timein = models.DateTimeField(auto_now=False, auto_now_add=True)
    timeout = models.DateTimeField(auto_now=False, auto_now_add=False, null=True, blank=True)
    
    class Meta:
        ordering = ["-time_in"]

    def __str__(self):
        return f"{self.user.username} - {self.time_in}"