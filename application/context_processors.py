from .models import Projects, Supervisor


def navbar_context(request):
    email = request.session.get('email')
    user_type = request.session.get('userType')
    pending_supervisor_requests_count = 0

    if email and user_type == 'supervisor':
        supervisor = Supervisor.objects.filter(email=email).first()
        if supervisor:
            pending_supervisor_requests_count = Projects.objects.filter(
                supervisor=supervisor,
                status='pending',
                is_completed=False
            ).count()

    return {
        'pending_supervisor_requests_count': pending_supervisor_requests_count,
    }
