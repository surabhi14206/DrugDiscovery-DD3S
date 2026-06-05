from django.utils.deprecation import MiddlewareMixin
from .models import UserActivity
from django.utils import timezone


class ActivityLoggingMiddleware(MiddlewareMixin):
    """Log all user activities"""
    
    def process_response(self, request, response):
        # Only log for authenticated users
        if not request.user.is_authenticated:
            return response
        
        # Skip static files and media
        if '/static/' in request.path or '/media/' in request.path:
            return response
        
        # Skip admin media
        if request.path.startswith('/admin/jsi18n/'):
            return response
        
        # Determine action type
        action_type = self.get_action_type(request)
        
        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        # Create activity log
        try:
            UserActivity.objects.create(
                user=request.user,
                action_type=action_type,
                page_url=request.path,
                search_query=request.GET.get('q', None),
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                session_id=request.session.session_key or 'no-session'
            )
        except Exception as e:
            # Don't break the request if logging fails
            pass
        
        return response
    
    def get_action_type(self, request):
        """Determine the action type from the request"""
        path = request.path
        
        if 'search' in path:
            return 'search'
        elif 'molecule' in path and request.method == 'GET':
            return 'view_molecule'
        elif 'predict' in path:
            return 'predict'
        elif 'download' in path:
            return 'download'
        else:
            return 'page_view'
