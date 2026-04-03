from django.contrib import admin
from .models import *


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'category')
    search_fields = ('title',)
    list_filter = ('category',)
    inlines = [LessonInline]


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'role')


admin.site.register(Category)
admin.site.register(Enrollment)
admin.site.register(Progress)