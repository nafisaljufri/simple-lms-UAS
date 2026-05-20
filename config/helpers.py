from ninja.errors import HttpError

def get_authenticated_user(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.get(pk=request.user.id)

def check_course_owner(course, user):
    if course.instructor != user:
        raise HttpError(403, "Hanya pemilik course yang dapat melakukan aksi ini")

def check_owner_or_superadmin(obj_owner, user):
    if obj_owner != user and not user.is_superuser:
        raise HttpError(403, "Anda tidak memiliki izin untuk melakukan aksi ini")