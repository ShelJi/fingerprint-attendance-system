from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, time, timedelta
from app.models import User, Attendance
from django.db.models import Q


# ══════════════════════════════════════════════════════
# VIEW 1 — DASHBOARD (home page)
# Shows today's attendance summary and recent scan logs.
# ══════════════════════════════════════════════════════
def home(request):

    # Build the time range for "today" using the server's local date.
    # time.min = 00:00:00  |  time.max = 23:59:59
    today_start = timezone.make_aware(datetime.combine(timezone.localdate(), time.min))
    today_end   = timezone.make_aware(datetime.combine(timezone.localdate(), time.max))

    # Get all attendance records that fall within today's range
    today_attendance = Attendance.objects.filter(
        timein__range=(today_start, today_end)
    ).order_by('-timein')

    # Count total registered employees
    total_users = User.objects.count()

    # Count how many distinct employees checked in today
    present_today = today_attendance.values('user').distinct().count()

    # Calculate what percentage of employees are present today
    attendance_rate = 0
    if total_users > 0:
        attendance_rate = int((present_today / total_users) * 100)

    # Get the 5 most recent scans across all time (for the live log panel)
    recent_logs = Attendance.objects.order_by('-timein')[:5]

    # Pass all data to the dashboard template
    context = {
        'total_users': total_users,
        'present_today': present_today,
        'attendance_rate': attendance_rate,
        'today_attendance': today_attendance,
        'recent_logs': recent_logs
    }
    return render(request, 'app/dashboard.html', context)


# ══════════════════════════════════════════════════════
# VIEW 2 — CREATE USER
# Handles the form that registers a new employee.
# ══════════════════════════════════════════════════════
def create_user(request):

    if request.method == 'POST':

        # Read the submitted form fields
        username         = request.POST.get('username')
        email            = request.POST.get('email')
        first_name       = request.POST.get('first_name')
        last_name        = request.POST.get('last_name')
        phone            = request.POST.get('phone', '')       # optional field
        fingerprint_data = request.POST.get('fingerprint_data')

        # ── Validation 1: username must be unique ──
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
            return render(request, 'app/create_user.html')

        # ── Validation 2: fingerprint ID must be unique ──
        if User.objects.filter(fingerprint_data=fingerprint_data).exists():
            messages.error(request, f"Biometric Fingerprint ID #{fingerprint_data} is already assigned to another user.")
            return render(request, 'app/create_user.html')

        try:
            # Create the new employee record in the database
            new_user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                fingerprint_data=int(fingerprint_data)
            )

            # Employees don't log in themselves — disable password login
            new_user.set_unusable_password()
            new_user.save()

            messages.success(request, f"User {first_name} {last_name} successfully enrolled under Fingerprint ID #{fingerprint_data}!")
            return redirect('home')

        except Exception as e:
            # Show the error if something unexpected goes wrong
            messages.error(request, f"Registration failed: {str(e)}")
            return render(request, 'app/create_user.html')

    # If not a POST request, just show the blank form
    return render(request, 'app/create_user.html')


# ══════════════════════════════════════════════════════
# VIEW 3 — VIEW ATTENDANCE
# Shows every registered employee with their attendance
# status for the selected date range.
# ══════════════════════════════════════════════════════
def view_attendance(request):

    # Read filter values from the URL query string
    # e.g. /attendance/?days=7&q=John
    days_filter  = request.GET.get('days', 'today')   # default: show today
    search_query = request.GET.get('q', '')

    # ── Build the date range based on the chosen filter ──
    date_start = None
    date_end   = None

    if days_filter == '1' or days_filter == 'today':
        # Today only: from 00:00:00 to 23:59:59 of the server's current date
        date_start = timezone.make_aware(datetime.combine(timezone.localdate(), time.min))
        date_end   = timezone.make_aware(datetime.combine(timezone.localdate(), time.max))

    elif days_filter == '7':
        # Last 7 days: from exactly 7 days ago until now
        date_start = timezone.now() - timedelta(days=7)

    elif days_filter == '30':
        # Last 30 days: from exactly 30 days ago until now
        date_start = timezone.now() - timedelta(days=30)

    # If days_filter == 'all', date_start and date_end stay None
    # which means no date restriction — show all records ever

    # ── Get all employees, with optional search filtering ──
    all_users = User.objects.all().order_by('first_name', 'last_name', 'username')

    if search_query:
        if search_query.isdigit():
            # If the search text is a number, search by fingerprint ID too
            all_users = all_users.filter(
                Q(fingerprint_data=int(search_query)) |
                Q(username__icontains=search_query)   |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        else:
            # Otherwise search by name or email
            all_users = all_users.filter(
                Q(username__icontains=search_query)   |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)  |
                Q(email__icontains=search_query)
            )

    # ── Build one row per employee ──
    # Each row contains the employee + their most recent attendance record
    # (or None if they haven't checked in during the selected period).
    user_attendance_rows = []

    for user in all_users:

        # Start with all records for this employee
        qs = Attendance.objects.filter(user=user)

        # Narrow down to the selected date range
        if date_start:
            qs = qs.filter(timein__gte=date_start)
        if date_end:
            qs = qs.filter(timein__lte=date_end)

        # Sort so the most recent record comes first
        qs = qs.order_by('-timein')

        # Take only the latest record (or None if there are no records)
        attendance_record = qs.first()

        # ── Determine the display status ──
        if attendance_record:
            if attendance_record.timeout:
                status = 'completed'       # checked in AND checked out
            else:
                status = 'active'          # currently checked in (no check-out yet)
        else:
            # No record found for this period
            if days_filter == '1' or days_filter == 'today':
                status = 'not_checked_in'  # hasn't scanned yet today
            else:
                status = 'absent'          # no record in the chosen past range

        # Add this employee's data to the list
        user_attendance_rows.append({
            'user':       user,
            'attendance': attendance_record,
            'status':     status,
        })

    # Pass the list and filter state to the template
    context = {
        'user_attendance_rows': user_attendance_rows,
        'days_filter':          days_filter,
        'search_query':         search_query,
    }
    return render(request, 'app/view_attendance.html', context)


# ══════════════════════════════════════════════════════
# VIEW 4 — RECORD ATTENDANCE
# Manual console for admins to record check-in / check-out
# on behalf of an employee (e.g. if the scanner is offline).
# ══════════════════════════════════════════════════════
def record_attendance(request):

    # Load all employees for the dropdown selector
    users = User.objects.all().order_by('first_name')

    # Read which employee the admin selected (passed in the URL as ?user_id=...)
    selected_user_id = request.GET.get('user_id')
    selected_user    = None
    active_attendance = None   # current open check-in session (no check-out yet)
    last_attendance   = None   # most recent completed session

    if selected_user_id:
        try:
            selected_user = User.objects.get(id=selected_user_id)

            # Look for an open session (checked in but not yet checked out)
            active_attendance = Attendance.objects.filter(
                user=selected_user,
                timeout__isnull=True    # timeout is empty → still active
            ).first()

            if not active_attendance:
                # No open session — find the most recent completed one
                last_attendance = Attendance.objects.filter(
                    user=selected_user,
                    timeout__isnull=False   # has a check-out time
                ).order_by('-timeout').first()

        except User.DoesNotExist:
            pass  # invalid user_id in URL — silently ignore

    # ── Handle form submission (check-in or check-out button pressed) ──
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action  = request.POST.get('action')   # either 'check_in' or 'check_out'

        try:
            user      = User.objects.get(id=user_id)
            full_name = f"{user.first_name} {user.last_name}" if user.first_name else user.username

            # ── CHECK-IN ──────────────────────────────────────
            if action == 'check_in':

                # Safety check: don't allow double check-in
                already_active = Attendance.objects.filter(user=user, timeout__isnull=True).exists()

                if already_active:
                    messages.error(request, f"User {full_name} is already checked in.")
                else:
                    # Create a new attendance record.
                    # The 'timein' field is set automatically by the SERVER
                    # (auto_now_add=True in the model) — browser time is never used.
                    Attendance.objects.create(user=user)
                    messages.success(
                        request,
                        f"Check-in successfully recorded for {full_name} at "
                        f"{timezone.now().strftime('%d-%m-%Y %H:%M:%S')}."
                    )

            # ── CHECK-OUT ─────────────────────────────────────
            elif action == 'check_out':

                # Find the employee's currently open session
                active_session = Attendance.objects.filter(user=user, timeout__isnull=True).first()

                if active_session:
                    # Capture the server time ONCE so the saved value and the
                    # confirmation message both show the exact same timestamp.
                    now = timezone.now()

                    active_session.timeout = now   # save check-out time to the database
                    active_session.save()

                    messages.success(
                        request,
                        f"Check-out successfully recorded for {full_name} at "
                        f"{now.strftime('%d-%m-%Y %H:%M:%S')}."
                    )
                else:
                    messages.error(request, f"No active check-in session found for {full_name}.")

        except User.DoesNotExist:
            messages.error(request, "Selected user does not exist.")

        # After processing, reload the same page with the same employee selected
        return redirect(f'/record-attendance/?user_id={user_id}' if user_id else '/record-attendance/')

    # If not a POST request, just show the page with the selected employee's status
    context = {
        'users':            users,
        'selected_user':    selected_user,
        'active_attendance': active_attendance,
        'last_attendance':  last_attendance
    }
    return render(request, 'app/record_attendance.html', context)