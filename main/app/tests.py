import json

from django.test import TestCase
from django.urls import reverse

from app.models import Attendance, User


class FingerprintScanTests(TestCase):
    def test_scan_with_known_fingerprint_creates_attendance(self):
        user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            fingerprint_data=101,
            first_name='Alice',
            last_name='Ng'
        )
        user.set_unusable_password()
        user.save()

        response = self.client.post(
            reverse('fingerprint_scan'),
            data=json.dumps({'fingerprint_data': 101}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Attendance.objects.filter(user=user).exists())
        attendance = Attendance.objects.get(user=user)
        self.assertIsNone(attendance.timeout)
