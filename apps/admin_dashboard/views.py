from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_POST
from datetime import timedelta
import json
import csv
from .models import UserActivity, SearchHistory, PredictionRequest, UserPreferences, Notification
from apps.authentication.models import CustomUser, MoleculeViewHistory
from apps.molecules.models import Molecule
from .forms import AdminPasswordChangeForm, UserPreferencesForm, DataExportForm


@staff_member_required
def dashboard(request):
    """Main admin dashboard"""
    from .models import SupportTicket
    
    total_users = CustomUser.objects.count()
    active_users = CustomUser.objects.filter(
        last_activity__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    today = timezone.now().date()
    activities_today = UserActivity.objects.filter(
        timestamp__date=today
    ).count()
    
    recent_activities = UserActivity.objects.select_related('user').order_by(
        '-timestamp'
    )[:5]
    
    pending_tickets = SupportTicket.objects.filter(status='pending').count()
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'activities_today': activities_today,
        'recent_activities': recent_activities,
        'pending_tickets': pending_tickets,
    }
    
    return render(request, 'admin_dashboard/dashboard.html', context)


@staff_member_required
def user_list(request):
    """List all users"""
    users = CustomUser.objects.all().order_by('-date_joined')
    return render(request, 'admin_dashboard/user_list.html', {
        'users': users
    })


@staff_member_required
def user_detail(request, user_id):
    """Detailed view of a specific user's activities"""
    user = get_object_or_404(CustomUser, id=user_id)
    activities = UserActivity.objects.filter(user=user).order_by('-timestamp')
    
    return render(request, 'admin_dashboard/user_detail.html', {
        'target_user': user,
        'activities': activities
    })


@staff_member_required
def activity_logs(request):
    """View all activity logs"""
    activities = UserActivity.objects.select_related('user').order_by('-timestamp')[:100]
    return render(request, 'admin_dashboard/activity_logs.html', {
        'activities': activities
    })


@staff_member_required
def search_analytics(request):
    """Search analytics and patterns"""
    from django.db.models import Count
    
    popular_terms = SearchHistory.objects.values('query').annotate(
        count=Count('id')
    ).order_by('-count')[:20]
    
    return render(request, 'admin_dashboard/search_analytics.html', {
        'popular_terms': popular_terms
    })


@login_required
def admin_settings(request):
    """Admin settings page with password change, 2FA, theme, and notifications"""
    user = request.user
    
    # Get or create user preferences
    preferences, created = UserPreferences.objects.get_or_create(
        user=user,
        defaults={
            'theme': 'light',
            'email_notifications': True,
            'activity_notifications': True,
            'weekly_reports': False,
        }
    )
    
    password_form = AdminPasswordChangeForm(user=user)
    preferences_form = UserPreferencesForm(initial={
        'theme': preferences.theme,
        'email_notifications': preferences.email_notifications,
        'activity_notifications': preferences.activity_notifications,
        'weekly_reports': preferences.weekly_reports,
        'two_factor_enabled': user.two_factor_enabled,
    })
    
    context = {
        'password_form': password_form,
        'preferences_form': preferences_form,
        'user': user,
        'preferences': preferences,
    }
    
    return render(request, 'admin_dashboard/settings.html', context)


@login_required
def change_password(request):
    """Handle password change"""
    if request.method == 'POST':
        form = AdminPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your password has been changed successfully!')
            
            # Log the activity
            UserActivity.objects.create(
                user=request.user,
                action_type='page_view',
                ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_id=request.session.session_key or '',
            )
            
            return redirect('admin_dashboard:settings')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    return redirect('admin_dashboard:settings')


@login_required
def update_preferences(request):
    """Update user preferences"""
    if request.method == 'POST':
        preferences, created = UserPreferences.objects.get_or_create(user=request.user)
        form = UserPreferencesForm(request.POST)
        
        if form.is_valid():
            preferences.theme = form.cleaned_data['theme']
            preferences.email_notifications = form.cleaned_data['email_notifications']
            preferences.activity_notifications = form.cleaned_data['activity_notifications']
            preferences.weekly_reports = form.cleaned_data['weekly_reports']
            preferences.save()
            
            # Update 2FA setting on user model
            request.user.two_factor_enabled = form.cleaned_data['two_factor_enabled']
            request.user.save()
            
            messages.success(request, 'Your preferences have been updated successfully!')
        else:
            messages.error(request, 'There was an error updating your preferences.')
    
    return redirect('admin_dashboard:settings')


@login_required
def search_history(request):
    """View and search through user's history"""
    user = request.user
    query = request.GET.get('q', '')
    
    # Get all history types
    activities = UserActivity.objects.filter(user=user)
    searches = SearchHistory.objects.filter(user=user)
    predictions = PredictionRequest.objects.filter(user=user)
    molecule_views = MoleculeViewHistory.objects.filter(user=user)
    
    # Apply search filter
    if query:
        activities = activities.filter(
            Q(action_type__icontains=query) | 
            Q(search_query__icontains=query)
        )
        searches = searches.filter(query__icontains=query)
    
    context = {
        'activities': activities[:100],
        'searches': searches[:100],
        'predictions': predictions[:100],
        'molecule_views': molecule_views[:100],
        'query': query,
    }
    
    return render(request, 'admin_dashboard/history.html', context)


@login_required
def export_data(request):
    """Export user data in various formats"""
    if request.method == 'POST':
        form = DataExportForm(request.POST)
        
        if form.is_valid():
            data_type = form.cleaned_data['data_type']
            export_format = form.cleaned_data['export_format']
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            
            # Determine which user's data to export
            target_user = request.user
            user_id = request.POST.get('user_id')
            
            # If admin and user_id provided, export that user's data
            if request.user.is_staff and user_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    target_user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    target_user = request.user
            
            # Collect data based on type
            data = []
            
            if data_type in ['all', 'activities']:
                activities = UserActivity.objects.filter(user=target_user)
                if start_date:
                    activities = activities.filter(timestamp__gte=start_date)
                if end_date:
                    activities = activities.filter(timestamp__lte=end_date)
                
                for activity in activities:
                    activity_data = {
                        'type': 'activity',
                        'action': activity.action_type,
                        'page_function': activity.get_action_type_display(),
                        'page_url': activity.page_url or '',
                        'ip_address': activity.ip_address,
                        'timestamp': activity.timestamp.isoformat(),
                    }
                    
                    # Add compound info if activity involved a molecule
                    if activity.target_molecule:
                        activity_data['compound_id'] = activity.target_molecule.pdb_id or str(activity.target_molecule.id)
                        activity_data['compound_name'] = activity.target_molecule.name
                    
                    # Add search query if available
                    if activity.search_query:
                        activity_data['search_query'] = activity.search_query
                    
                    data.append(activity_data)
            
            if data_type in ['all', 'searches']:
                searches = SearchHistory.objects.filter(user=target_user)
                if start_date:
                    searches = searches.filter(timestamp__gte=start_date)
                if end_date:
                    searches = searches.filter(timestamp__lte=end_date)
                
                for search in searches:
                    data.append({
                        'type': 'search',
                        'query': search.query,
                        'search_type': search.search_type,
                        'results_count': search.results_count,
                        'timestamp': search.timestamp.isoformat(),
                    })
            
            if data_type in ['all', 'predictions']:
                predictions = PredictionRequest.objects.filter(user=target_user)
                if start_date:
                    predictions = predictions.filter(timestamp__gte=start_date)
                if end_date:
                    predictions = predictions.filter(timestamp__lte=end_date)
                
                for prediction in predictions:
                    data.append({
                        'type': 'prediction',
                        'compound_id': prediction.molecule.pdb_id or str(prediction.molecule.id),
                        'compound_name': prediction.molecule.name,
                        'molecular_formula': prediction.molecule.molecular_formula or '',
                        'smiles': prediction.molecule.smiles,
                        'prediction_type': prediction.prediction_type,
                        'result': prediction.result,
                        'processing_time': prediction.processing_time,
                        'timestamp': prediction.timestamp.isoformat(),
                    })
            
            if data_type in ['all', 'molecules']:
                views = MoleculeViewHistory.objects.filter(user=target_user)
                if start_date:
                    views = views.filter(viewed_at__gte=start_date)
                if end_date:
                    views = views.filter(viewed_at__lte=end_date)
                
                for view in views:
                    data.append({
                        'type': 'molecule_view',
                        'compound_id': view.molecule.pdb_id or str(view.molecule.id),
                        'compound_name': view.molecule.name,
                        'molecular_formula': view.molecule.molecular_formula or '',
                        'smiles': view.molecule.smiles,
                        'view_count': view.view_count,
                        'viewed_at': view.viewed_at.isoformat(),
                    })
            
            # Generate response based on format
            if export_format == 'json':
                response = HttpResponse(
                    json.dumps(data, indent=2),
                    content_type='application/json'
                )
                response['Content-Disposition'] = f'attachment; filename="user_data_{target_user.username}.json"'
            
            elif export_format == 'csv':
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="user_data_{target_user.username}.csv"'
                
                if data:
                    # Collect all unique field names from all data rows
                    all_fieldnames = set()
                    for row in data:
                        all_fieldnames.update(row.keys())
                    fieldnames = sorted(list(all_fieldnames))
                    
                    writer = csv.DictWriter(response, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(data)
            
            elif export_format == 'excel':
                try:
                    import openpyxl
                    from openpyxl import Workbook
                    
                    wb = Workbook()
                    ws = wb.active
                    ws.title = "User Data"
                    
                    if data:
                        # Collect all unique field names from all data rows
                        all_fieldnames = set()
                        for row in data:
                            all_fieldnames.update(row.keys())
                        headers = sorted(list(all_fieldnames))
                        ws.append(headers)
                        
                        # Write data
                        for row in data:
                            ws.append([row.get(h, '') for h in headers])
                    
                    response = HttpResponse(
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = f'attachment; filename="user_data_{target_user.username}.xlsx"'
                    wb.save(response)
                    
                except ImportError:
                    messages.error(request, 'Excel export requires openpyxl. Please install it.')
                    return redirect('admin_dashboard:export_page')
            
            return response
        else:
            messages.error(request, 'Invalid export form data.')
    
    return redirect('admin_dashboard:export_page')


@login_required
def change_password_page(request):
    """Separate page for changing password"""
    if request.method == 'POST':
        form = AdminPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed successfully!')
            return redirect('authentication:profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    return render(request, 'admin_dashboard/change_password.html')


@login_required
def notifications_page(request):
    """Separate page for notification settings"""
    preferences, created = UserPreferences.objects.get_or_create(
        user=request.user,
        defaults={
            'theme': 'light',
            'email_notifications': True,
            'activity_notifications': True,
            'weekly_reports': False,
        }
    )
    
    if request.method == 'POST':
        # Update preferences from POST data
        # Checkboxes send 'on' when checked, nothing when unchecked
        preferences.email_notifications = 'email_notifications' in request.POST
        preferences.activity_notifications = 'activity_notifications' in request.POST
        preferences.weekly_reports = 'weekly_reports' in request.POST
        preferences.save()
        
        messages.success(request, '✓ Notification preferences saved successfully!')
        
        # Redirect back to notifications page to show updated state
        return redirect('admin_dashboard:notifications_page')
    
    return render(request, 'admin_dashboard/notifications.html', {
        'preferences': preferences
    })


@login_required
def theme_page(request):
    """Separate page for theme settings"""
    preferences, created = UserPreferences.objects.get_or_create(
        user=request.user,
        defaults={
            'theme': 'recomended',
            'email_notifications': True,
            'activity_notifications': True,
            'weekly_reports': False,
        }
    )
    
    if request.method == 'POST':
        theme = request.POST.get('theme', 'recomended')
        preferences.theme = theme
        preferences.save()
        messages.success(request, f'Theme changed to {theme.title()} successfully!')
        return redirect('admin_dashboard:theme_page')
    
    return render(request, 'admin_dashboard/theme.html', {
        'preferences': preferences
    })


@login_required
def export_page(request):
    """Separate page for exporting data"""
    if request.method == 'POST':
        # Reuse the existing export_data logic
        return export_data(request)
    
    return render(request, 'admin_dashboard/export.html')


@staff_member_required
def support_tickets(request):
    """View all support tickets"""
    from .models import SupportTicket
    
    # Filter parameters
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    search_query = request.GET.get('q', '')
    
    tickets = SupportTicket.objects.all().order_by('-created_at')
    
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if priority_filter:
        tickets = tickets.filter(priority=priority_filter)
    if search_query:
        tickets = tickets.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(message__icontains=search_query) |
            Q(subject__icontains=search_query)
        )
    
    # Statistics
    total_tickets = SupportTicket.objects.count()
    pending_tickets = SupportTicket.objects.filter(status='pending').count()
    in_progress_tickets = SupportTicket.objects.filter(status='in_progress').count()
    resolved_tickets = SupportTicket.objects.filter(status='resolved').count()
    
    return render(request, 'admin_dashboard/support_tickets.html', {
        'tickets': tickets,
        'total_tickets': total_tickets,
        'pending_tickets': pending_tickets,
        'in_progress_tickets': in_progress_tickets,
        'resolved_tickets': resolved_tickets,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'search_query': search_query,
    })


@staff_member_required
def support_ticket_detail(request, ticket_id):
    """View detailed support ticket"""
    from .models import SupportTicket
    
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    
    return render(request, 'admin_dashboard/support_ticket_detail.html', {
        'ticket': ticket
    })


@staff_member_required
def respond_ticket(request, ticket_id):
    """Respond to a support ticket"""
    from .models import SupportTicket
    
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    
    if request.method == 'POST':
        response_text = request.POST.get('response', '').strip()
        new_status = request.POST.get('status', ticket.status)
        priority = request.POST.get('priority', ticket.priority)
        
        if response_text:
            ticket.admin_response = response_text
            ticket.admin_responder = request.user
            ticket.status = new_status
            ticket.priority = priority
            
            if new_status == 'resolved':
                ticket.resolved_at = timezone.now()
            
            ticket.save()
            
            messages.success(request, 'Response sent successfully!')
            
            # Log activity
            UserActivity.objects.create(
                user=request.user,
                action_type='page_view',
                page_url=f'/admin-dashboard/support-tickets/{ticket_id}/',
                ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_id=request.session.session_key or '',
            )
        else:
            messages.error(request, 'Response cannot be empty.')
    
    return redirect('admin_dashboard:support_ticket_detail', ticket_id=ticket_id)


@login_required
def get_notifications(request):
    """API endpoint to get user notifications"""
    notifications = Notification.objects.filter(user=request.user, is_read=False)[:5]
    
    data = {
        'count': notifications.count(),
        'notifications': [
            {
                'id': n.id,
                'type': n.type,
                'title': n.title,
                'message': n.message,
                'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for n in notifications
        ]
    }
    
    return JsonResponse(data)


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """API endpoint to mark a notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.mark_as_read()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)


@login_required
@require_POST
def mark_all_notifications_read(request):
    """API endpoint to mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


@staff_member_required
def add_user(request):
    """Add a new user in admin dashboard"""
    from .user_forms import AddUserForm
    
    if request.method == 'POST':
        form = AddUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" created successfully!')
            
            # Log activity
            UserActivity.objects.create(
                user=request.user,
                action_type='page_view',
                page_url=f'/admin-dashboard/users/add/',
                ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_id=request.session.session_key or '',
            )
            
            return redirect('admin_dashboard:user_detail', user_id=user.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = AddUserForm()
    
    return render(request, 'admin_dashboard/add_user.html', {
        'form': form
    })


@staff_member_required
def edit_user(request, user_id):
    """Edit an existing user in admin dashboard"""
    from .user_forms import EditUserForm
    
    user_to_edit = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        form = EditUserForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" updated successfully!')
            
            # Log activity
            UserActivity.objects.create(
                user=request.user,
                action_type='page_view',
                page_url=f'/admin-dashboard/users/{user_id}/edit/',
                ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_id=request.session.session_key or '',
            )
            
            return redirect('admin_dashboard:user_detail', user_id=user.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = EditUserForm(instance=user_to_edit)
    
    return render(request, 'admin_dashboard/edit_user.html', {
        'form': form,
        'user_to_edit': user_to_edit
    })
