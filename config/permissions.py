from ninja.errors import HttpError

def is_instructor(func):
    def wrapper(request, *args, **kwargs):
        user = request.auth
        if not user or user.role != "instructor":
            raise HttpError(403, "Instructor only")
        return func(request, *args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

def is_admin(func):
    def wrapper(request, *args, **kwargs):
        user = request.auth
        if not user or user.role != "admin":
            raise HttpError(403, "Admin only")
        return func(request, *args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper