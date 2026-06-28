from django.contrib.auth.models import AbstractUser
from django.db import models


# ─────────────────────────────────────────────
# USER MODEL
# Extends Django's built-in user so we can add
# extra fields like phone and fingerprint ID.
# ─────────────────────────────────────────────
class User(AbstractUser):

    # Employee's phone number (optional)
    phone = models.CharField(max_length=15, blank=True)

    # Employee's profile photo (optional, saved in the "profiles/" folder)
    profile_image = models.ImageField(upload_to="profiles/", blank=True, null=True)

    # The fingerprint slot number assigned to this employee.
    # Must be unique — no two employees can share the same fingerprint ID.
    fingerprint_data = models.IntegerField(unique=True)

    # FUTURE UPDATES
    # total_attendance =
    # total_worked_hours =
    # total_worked_days =

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


# ─────────────────────────────────────────────
# ATTENDANCE MODEL
# Stores one record each time an employee
# checks in or checks out.
# ─────────────────────────────────────────────
class Attendance(models.Model):

    # Links this attendance record to a specific employee.
    # If the employee is deleted, their attendance records are also deleted (CASCADE).
    user = models.ForeignKey("User", on_delete=models.CASCADE)

    # Check-in time — set AUTOMATICALLY by the server when the record is created.
    # auto_now_add=True means:
    #   • It is recorded once (at creation) using the server clock.
    #   • It can NEVER be changed or overwritten afterwards.
    #   • No input from the browser or client is ever used.
    timein = models.DateTimeField(auto_now_add=True)

    # Check-out time — empty (null) until the employee checks out.
    # When check-out happens, the server sets this using timezone.now().
    timeout = models.DateTimeField(null=True, blank=True)

    class Meta:
        # Show the most recent records first by default
        ordering = ["-timein"]

    def __str__(self):
        # Human-readable label shown in the Django admin panel
        return f"{self.user.username} - {self.timein}"