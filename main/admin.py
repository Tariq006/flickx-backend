from django.contrib import admin
from . import models

# Register your models here.

@admin.register(models.Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'email', 'qualification', 'mobile_no')
    list_display_links = ('id', 'full_name')
    search_fields = ('full_name', 'email', 'qualification', 'skills')
    list_filter = ('qualification',)
    ordering = ('full_name',)


@admin.register(models.CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'description_preview')
    list_display_links = ('id', 'title')
    search_fields = ('title', 'description')
    ordering = ('title',)
    
    def description_preview(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_preview.short_description = 'Description'


@admin.register(models.Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'teacher', 'total_enrolled_students', 'featured_img_preview')
    list_display_links = ('id', 'title')
    list_filter = ('category', 'teacher')
    search_fields = ('title', 'description', 'techs', 'teacher__full_name')
    ordering = ('-id',)
    raw_id_fields = ('teacher', 'category')
    
    def featured_img_preview(self, obj):
        if obj.featured_img:
            return f'✓ Has Image'
        return 'No Image'
    featured_img_preview.short_description = 'Image'


@admin.register(models.Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'course', 'video_preview')
    list_display_links = ('id', 'title')
    list_filter = ('course',)
    search_fields = ('title', 'description', 'course__title')
    ordering = ('course', 'id')
    raw_id_fields = ('course',)
    
    def video_preview(self, obj):
        if obj.video:
            return f'✓ Has Video'
        return 'No Video'
    video_preview.short_description = 'Video'


@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'email', 'username', 'status')
    list_display_links = ('id', 'full_name')
    search_fields = ('full_name', 'email', 'username')
    list_filter = ('status',)
    ordering = ('full_name',)


@admin.register(models.UserCourseEnrollment)
class UserCourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'enrolled_date')
    list_display_links = ('id',)
    list_filter = ('course', 'enrolled_date')
    search_fields = ('user__full_name', 'user__email', 'course__title')
    ordering = ('-enrolled_date',)
    raw_id_fields = ('user', 'course')


@admin.register(models.CourseRating)
class CourseRatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'rating', 'created_at')
    list_display_links = ('id',)
    list_filter = ('rating', 'created_at')
    search_fields = ('user__full_name', 'course__title', 'comment')
    ordering = ('-created_at',)
    raw_id_fields = ('user', 'course')


@admin.register(models.FavoriteCourse)
class FavoriteCourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'added_date')
    list_display_links = ('id',)
    list_filter = ('added_date',)
    search_fields = ('user__full_name', 'course__title')
    ordering = ('-added_date',)
    raw_id_fields = ('user', 'course')


@admin.register(models.Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'teacher', 'course', 'total_marks', 'due_date', 'is_active', 'created_at')
    list_display_links = ('id', 'title')
    list_filter = ('is_active', 'teacher', 'course', 'created_at')
    search_fields = ('title', 'description', 'teacher__full_name', 'course__title')
    ordering = ('-created_at',)
    raw_id_fields = ('teacher', 'course')
    date_hierarchy = 'due_date'


@admin.register(models.AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'assignment', 'student', 'status', 'marks_obtained', 'is_late', 'submitted_at')
    list_display_links = ('id',)
    list_filter = ('status', 'is_late', 'submitted_at')
    search_fields = ('student__full_name', 'assignment__title', 'feedback')
    ordering = ('-submitted_at',)
    raw_id_fields = ('assignment', 'student')
    date_hierarchy = 'submitted_at'


@admin.register(models.Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'teacher', 'course', 'total_marks', 'time_limit', 'is_active', 'created_at')
    list_display_links = ('id', 'title')
    list_filter = ('is_active', 'teacher', 'course', 'created_at')
    search_fields = ('title', 'description', 'teacher__full_name', 'course__title')
    ordering = ('-created_at',)
    raw_id_fields = ('teacher', 'course')


@admin.register(models.QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'quiz', 'question_preview', 'correct_option', 'marks', 'created_at')
    list_display_links = ('id', 'quiz')
    list_filter = ('quiz', 'marks', 'created_at')
    search_fields = ('question_text', 'option1', 'option2', 'option3', 'option4')
    ordering = ('quiz', 'id')
    raw_id_fields = ('quiz',)
    
    def question_preview(self, obj):
        return obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
    question_preview.short_description = 'Question'


@admin.register(models.QuizSubmission)
class QuizSubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'quiz', 'student', 'status', 'total_marks_obtained', 'percentage', 'is_passed', 'submitted_at')
    list_display_links = ('id',)
    list_filter = ('status', 'is_passed', 'submitted_at')
    search_fields = ('student__full_name', 'quiz__title')
    ordering = ('-submitted_at',)
    raw_id_fields = ('quiz', 'student')


@admin.register(models.QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'submission', 'question', 'selected_option', 'is_correct', 'marks_obtained', 'answered_at')
    list_display_links = ('id',)
    list_filter = ('is_correct', 'answered_at')
    search_fields = ('submission__student__full_name', 'question__question_text')
    ordering = ('-answered_at',)
    raw_id_fields = ('submission', 'question')


@admin.register(models.StudyMaterial)
class StudyMaterialAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'course', 'teacher', 'file_type', 'uploaded_at')
    list_display_links = ('id', 'title')
    list_filter = ('course', 'teacher', 'uploaded_at')
    search_fields = ('title', 'description', 'course__title', 'teacher__full_name')
    ordering = ('-uploaded_at',)
    raw_id_fields = ('course', 'teacher')
    date_hierarchy = 'uploaded_at'
    
    def file_type(self, obj):
        if obj.file:
            return obj.file.name.split('.')[-1].upper()
        return 'N/A'
    file_type.short_description = 'File Type'


@admin.register(models.MentorshipSession)
class MentorshipSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'teacher', 'course', 'scheduled_date', 'status', 'max_participants', 'registered_count', 'created_at')
    list_display_links = ('id', 'title')
    list_filter = ('status', 'teacher', 'course', 'scheduled_date', 'created_at')
    search_fields = ('title', 'description', 'teacher__full_name', 'course__title')
    ordering = ('-scheduled_date',)
    raw_id_fields = ('teacher', 'course')
    date_hierarchy = 'scheduled_date'
    
    def registered_count(self, obj):
        return obj.registrations.count()
    registered_count.short_description = 'Registered Students'


@admin.register(models.MentorshipRegistration)
class MentorshipRegistrationAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'user', 'registered_at')
    list_display_links = ('id',)
    list_filter = ('registered_at',)
    search_fields = ('user__full_name', 'session__title')
    ordering = ('-registered_at',)
    raw_id_fields = ('session', 'user')
    date_hierarchy = 'registered_at'


@admin.register(models.Admin)
class AdminModelAdmin(admin.ModelAdmin):
    """
    Django Admin interface for the custom Admin model.
    Note: This is named AdminModelAdmin to avoid confusion with Django's admin module.
    """
    list_display = ('id', 'username', 'full_name', 'email', 'is_active', 'last_login', 'created_at')
    list_display_links = ('id', 'username')
    search_fields = ('username', 'full_name', 'email')
    list_filter = ('is_active', 'created_at', 'last_login')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    # Fields to display when viewing/editing an admin
    fieldsets = (
        ('Basic Information', {
            'fields': ('username', 'full_name', 'email', 'password')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_login'),
            'classes': ('collapse',)
        }),
    )
    
    # Read-only fields
    readonly_fields = ('created_at', 'last_login')
    
    # Show these fields when creating a new admin
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'full_name', 'email', 'password', 'is_active'),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Override save to hash password if it was changed"""
        if not change or 'password' in form.changed_data:
            from django.contrib.auth.hashers import make_password
            obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)