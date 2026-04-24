from functools import wraps


def is_authenticated(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.auth
        if not user:
            return {"error": "Unauthorized"}
        return func(request, *args, **kwargs)
    return wrapper


def is_instructor(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.auth
        if not user or user.role != "instructor":
            return {"error": "Instructor only"}
        return func(request, *args, **kwargs)
    return wrapper


def is_admin(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.auth
        if not user or user.role != "admin":
            return {"error": "Admin only"}
        return func(request, *args, **kwargs)
    return wrapper