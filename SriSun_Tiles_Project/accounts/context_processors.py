from .permissions import is_admin_user


def admin_permissions(request):
    return {'user_is_admin': is_admin_user(request.user)}