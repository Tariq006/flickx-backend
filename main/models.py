from django.db import models
from django.utils import timezone
import uuid

# teacher model
class Teacher(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    qualification = models.CharField(max_length=200)
    mobile_no = models.CharField(max_length=20)
    skills = models.TextField()
    profile_img = models.ImageField(upload_to='teacher_profile_imgs/', null=True, blank=True)

    class Meta:
        verbose_name_plural = "1. Teachers"

    def __str__(self):
        return self.full_name
    
    def skill_list(self):
        if self.skills:
            return [skill.strip() for skill in self.skills.split(',')]
        return []
# mentorship 
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User  # Add this import

class MentorshipSession(models.Model):
    SESSION_TYPE_CHOICES = [
        ('live_qna', 'Live Q&A'),
        ('workshop', 'Workshop'),
        ('office_hours', 'Office Hours'),
        ('group_study', 'Group Study'),
        ('one_on_one', 'One-on-One'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live', 'Live Now'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic info
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    session_link = models.URLField(max_length=500)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES, default='live_qna')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Relationships
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE, related_name='mentorship_sessions')
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='mentorship_sessions')
    
    # Scheduling
    scheduled_date = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_date']
        verbose_name = "Mentorship Session"
        verbose_name_plural = "Mentorship Sessions"
    
    def __str__(self):
        return f"{self.title} ({self.course.title})"
    
    @property
    def is_upcoming(self):
        return self.scheduled_date > timezone.now() and self.status == 'scheduled'
    
    @property
    def is_live_now(self):
        now = timezone.now()
        end_time = self.scheduled_date + timezone.timedelta(minutes=self.duration_minutes)
        return self.scheduled_date <= now <= end_time and self.status in ['scheduled', 'live']
    
    @property
    def registered_count(self):
        return self.registrations.count()
    
    @property
    def is_full(self):
        if self.max_participants:
            return self.registered_count >= self.max_participants
        return False


class MentorshipRegistration(models.Model):
    # FIXED: Use 'User' (capitalized) instead of 'user' (lowercase)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mentorship_registrations')
    session = models.ForeignKey(MentorshipSession, on_delete=models.CASCADE, related_name='registrations')
    registered_at = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'session']
        ordering = ['-registered_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.session.title}"
    
    @property
    def attendance_duration(self):
        if self.joined_at and self.left_at:
            duration = self.left_at - self.joined_at
            return duration.total_seconds() / 60  # Convert to minutes
        return 0


# course category model
class CourseCategory(models.Model):
    title = models.CharField(max_length=150, unique=True)
    description = models.TextField()

    class Meta:
        verbose_name_plural = "2. Course Categories"

    def __str__(self):
        return self.title


# course model
class Course(models.Model):
    category = models.ForeignKey(CourseCategory, on_delete=models.CASCADE, null=True, blank=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, null=True, blank=True, related_name='teacher_courses')
    title = models.CharField(max_length=150)
    description = models.TextField()
    featured_img = models.ImageField(upload_to='course_img/', null=True, blank=True)
    techs = models.TextField(null=True, blank=True)
    views = models.IntegerField(default=0)  # NEW FIELD
    created_at = models.DateTimeField(auto_now_add=True)  # NEW FIELD

    class Meta:
        verbose_name_plural = "3. Courses"

    def __str__(self):
        return self.title
    
    def related_videos(self):
        if self.techs:
            return Course.objects.filter(techs__icontains=self.techs).exclude(id=self.id)[:5]
        return Course.objects.none()
    
    def tech_list(self):
        if self.techs:
            return [tech.strip() for tech in self.techs.split(',')]
        return []
    
    @property
    def total_enrolled_students(self):
        return self.enrolled_students.count()
    
    @property
    def average_rating(self):
        """Calculate average rating for the course"""
        from django.db.models import Avg
        avg = self.course_ratings.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 2) if avg else 0
    
    @property
    def total_ratings(self):
        """Get total number of ratings"""
        return self.course_ratings.count()
    
    def increment_views(self):
        """Increment view count"""
        self.views += 1
        self.save(update_fields=['views'])

# chapter model
class Chapter(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=150)
    description = models.TextField()
    video = models.FileField(upload_to='chapter_videos/', null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "4. Chapters"
        ordering = ['id']

    def __str__(self):
        return f"{self.course.title} - {self.title}"


# user model
class User(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.CharField(max_length=100, unique=True)
    username = models.CharField(max_length=100, unique=True, null=True, blank=True)
    password = models.CharField(max_length=255)
    interested_categories = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='active')
    profile_pic = models.ImageField(upload_to='user_profile_pics/', null=True, blank=True)

    class Meta:
        verbose_name_plural = "5. Users"

    def __str__(self):
        return self.full_name
    


# user course enrollment model
class UserCourseEnrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrolled_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrolled_students')
    enrolled_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "6. User Course Enrollments"
        unique_together = ('user', 'course')
        ordering = ['-enrolled_date']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.course.title}"


# Rating model
class CourseRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_ratings')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='course_ratings')
    rating = models.IntegerField(choices=[(1, '1 Star'), (2, '2 Stars'), (3, '3 Stars'), (4, '4 Stars'), (5, '5 Stars')])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "7. Course Ratings"
        unique_together = ('user', 'course')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.course.title} - {self.rating} Stars"


# Favorite Course model
class FavoriteCourse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='favorited_by')
    added_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "8. Favorite Courses"
        unique_together = ('user', 'course')
        ordering = ['-added_date']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.course.title}"


# Assignment model
class Assignment(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='assignments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    total_marks = models.IntegerField(default=100)
    due_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "9. Assignments"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"
    
    @property
    def total_submissions(self):
        return self.submissions.count()
    
    @property
    def submitted_students(self):
        return User.objects.filter(
            id__in=self.submissions.values_list('student_id', flat=True)
        ).distinct()


# Assignment Submission model
class AssignmentSubmission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
        ('late', 'Submitted Late'),
        ('missing', 'Missing'),
    ]
    
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignment_submissions')
    submission_text = models.TextField(blank=True, null=True)
    submission_file = models.FileField(upload_to='assignment_submissions/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    marks_obtained = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    is_late = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "10. Assignment Submissions"
        unique_together = ('assignment', 'student')
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.student.full_name} - {self.assignment.title}"
    
    def save(self, *args, **kwargs):
        # Check if submission is late
        if self.assignment.due_date and self.submitted_at:
            if self.submitted_at > self.assignment.due_date:
                self.is_late = True
                self.status = 'late'
        
        # If marks are given, mark as graded
        if self.marks_obtained is not None:
            self.status = 'graded'
            if not self.graded_at:
                self.graded_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def grade_percentage(self):
        if self.marks_obtained and self.assignment.total_marks:
            return (self.marks_obtained / self.assignment.total_marks) * 100
        return 0
    

# Quiz model - UPDATED WITH MISSING FIELDS
class Quiz(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='quizzes')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField()
    total_marks = models.IntegerField(default=100)
    time_limit = models.IntegerField(default=30, help_text="Time limit in minutes")
    attempt_limit = models.IntegerField(default=1, help_text="Number of attempts allowed (0 = unlimited)")
    show_answers = models.BooleanField(default=False, help_text="Show answers after submission")
    due_date = models.DateTimeField(null=True, blank=True, help_text="Due date for the quiz")
    is_active = models.BooleanField(default=True)
    is_quiz = models.BooleanField(default=True, help_text="Flag to identify as quiz")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "11. Quizzes"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"
    
    @property
    def total_questions(self):
        return self.questions.count()
    
    @property
    def total_submissions(self):
        return self.quiz_submissions.count()


# Quiz Question model with 4 options
class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    option1 = models.CharField(max_length=500)
    option2 = models.CharField(max_length=500)
    option3 = models.CharField(max_length=500)
    option4 = models.CharField(max_length=500)
    correct_option = models.IntegerField(
        choices=[(1, 'Option 1'), (2, 'Option 2'), (3, 'Option 3'), (4, 'Option 4')],
        help_text="Select which option is correct"
    )
    marks = models.IntegerField(default=10)
    explanation = models.TextField(blank=True, null=True, help_text="Explanation of the correct answer")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "12. Quiz Questions"
        ordering = ['id']
    
    def __str__(self):
        return f"{self.quiz.title} - Q{self.id}"
    
    def get_correct_answer(self):
        """Return the correct answer text"""
        options = {
            1: self.option1,
            2: self.option2,
            3: self.option3,
            4: self.option4
        }
        return options.get(self.correct_option, '')


# Quiz Submission model
class QuizSubmission(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='quiz_submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_submissions')
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    time_taken = models.IntegerField(default=0, help_text="Time taken in minutes")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    total_questions_attempted = models.IntegerField(default=0)
    total_correct_answers = models.IntegerField(default=0)
    total_marks_obtained = models.IntegerField(default=0)
    percentage = models.FloatField(default=0.0)
    is_passed = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "13. Quiz Submissions"
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.student.full_name} - {self.quiz.title}"
    
    def save(self, *args, **kwargs):
        # Calculate percentage if we have marks
        if self.total_marks_obtained and self.quiz.total_marks:
            self.percentage = (self.total_marks_obtained / self.quiz.total_marks) * 100
            
            # Check if passed (assuming passing is 40% or more)
            self.is_passed = self.percentage >= 40
        
        super().save(*args, **kwargs)


# Quiz Answer model
class QuizAnswer(models.Model):
    submission = models.ForeignKey(QuizSubmission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    selected_option = models.IntegerField(
        choices=[(1, 'Option 1'), (2, 'Option 2'), (3, 'Option 3'), (4, 'Option 4')],
        null=True, blank=True
    )
    is_correct = models.BooleanField(default=False)
    marks_obtained = models.IntegerField(default=0)
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "14. Quiz Answers"
        unique_together = ('submission', 'question')
        ordering = ['answered_at']
    
    def __str__(self):
        return f"{self.submission.student.full_name} - Q{self.question.id}"
    
    def save(self, *args, **kwargs):
        # Check if the answer is correct
        if self.selected_option == self.question.correct_option:
            self.is_correct = True
            self.marks_obtained = self.question.marks
        else:
            self.is_correct = False
            self.marks_obtained = 0
            
        super().save(*args, **kwargs)




# Quiz StudyMaterial model
class StudyMaterial(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='study_materials')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='materials', null=True)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    upload = models.FileField(upload_to='study_materials/', null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    file_type = models.CharField(max_length=20, default='pdf')
    is_public = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    uploaded_at = models.DateTimeField(default=timezone.now)  
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "15. Course Study Materials"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.course.title} - {self.title}"
    

class Admin(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.CharField(max_length=100, unique=True)
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=50, default='admin')
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_pic = models.ImageField(upload_to='admin_profile_pics/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_super_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "16. Admins"

    def __str__(self):
        return f"{self.full_name} ({self.role})"

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])

# Add these models to your models.py file

# ==================== DISCUSSION FORUM MODELS ====================

class CourseForum(models.Model):
    """
    Forum group for each course - automatically created when course is created
    Similar to a WhatsApp group for the course
    """
    course = models.OneToOneField('Course', on_delete=models.CASCADE, related_name='forum')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    group_icon = models.ImageField(upload_to='forum_icons/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Group settings
    allow_student_messages = models.BooleanField(default=True, help_text="Allow students to send messages")
    allow_file_sharing = models.BooleanField(default=True, help_text="Allow sharing files/images")
    require_approval = models.BooleanField(default=False, help_text="Require admin/teacher approval for messages")
    
    class Meta:
        verbose_name_plural = "Course Forums"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Forum: {self.course.title}"
    
    @property
    def total_members(self):
        """Get total number of members in the forum"""
        return self.members.count()
    
    @property
    def total_messages(self):
        """Get total number of messages in the forum"""
        return self.messages.count()
    
    @property
    def last_message(self):
        """Get the last message in the forum"""
        return self.messages.order_by('-timestamp').first()


# models.py - Update ForumMember model

class ForumMember(models.Model):
    """
    Members of a course forum (teacher and enrolled students)
    Can be either a User (student) or a Teacher (teacher)
    """
    ROLE_CHOICES = [
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('admin', 'Admin'),
    ]
    
    forum = models.ForeignKey(CourseForum, on_delete=models.CASCADE, related_name='members')
    
    # Make both nullable but ensure at least one is set
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_memberships', null=True, blank=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='forum_memberships', null=True, blank=True)
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    is_muted = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "Forum Members"
        # Update unique constraint
        constraints = [
            models.UniqueConstraint(
                fields=['forum', 'user'],
                name='unique_forum_user'
            ),
            models.UniqueConstraint(
                fields=['forum', 'teacher'],
                name='unique_forum_teacher'
            )
        ]
        ordering = ['joined_at']
    
    def __str__(self):
        if self.user:
            return f"{self.user.full_name} - {self.forum.course.title} ({self.role})"
        elif self.teacher:
            return f"{self.teacher.full_name} - {self.forum.course.title} ({self.role})"
        return f"Unknown - {self.forum.course.title}"
    
    def get_name(self):
        """Get the name of the member regardless of type"""
        if self.user:
            return self.user.full_name
        elif self.teacher:
            return self.teacher.full_name
        return "Unknown"
    
    def get_email(self):
        """Get the email of the member regardless of type"""
        if self.user:
            return self.user.email
        elif self.teacher:
            return self.teacher.email
        return None
    
    def update_last_seen(self):
        """Update user's last seen timestamp"""
        self.last_seen_at = timezone.now()
        self.save(update_fields=['last_seen_at'])

# models.py - Update ForumMessage model

class ForumMessage(models.Model):
    """
    Messages in the course forum
    Supports text, images, files, and replies
    """
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('announcement', 'Announcement'),
    ]
    
    forum = models.ForeignKey(CourseForum, on_delete=models.CASCADE, related_name='messages')
    
    # Make both nullable but ensure at least one is set
    sender_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_messages', null=True, blank=True)
    sender_teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='forum_messages', null=True, blank=True)
    
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    # Message content
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    content = models.TextField(blank=True, null=True)
    
    # Media attachments
    image = models.ImageField(upload_to='forum_images/', null=True, blank=True)
    file = models.FileField(upload_to='forum_files/', null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_size = models.IntegerField(default=0, help_text="File size in bytes")
    
    # Message metadata
    is_edited = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    is_announcement = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Forum Messages"
        ordering = ['timestamp']
    
    def __str__(self):
        sender_name = self.get_sender_name()
        content_preview = self.content[:50] if self.content else "[Media]"
        return f"{sender_name}: {content_preview}"
    
    def get_sender(self):
        """Get the sender object regardless of type"""
        return self.sender_user or self.sender_teacher
    
    def get_sender_name(self):
        """Get sender's name regardless of type"""
        if self.sender_user:
            return self.sender_user.full_name
        elif self.sender_teacher:
            return self.sender_teacher.full_name
        return "Unknown"
    
    def get_sender_email(self):
        """Get sender's email regardless of type"""
        if self.sender_user:
            return self.sender_user.email
        elif self.sender_teacher:
            return self.sender_teacher.email
        return None
    
    def get_sender_role(self):
        """Get sender's role in the forum"""
        if self.sender_user:
            try:
                member = ForumMember.objects.get(forum=self.forum, user=self.sender_user)
                return member.role
            except ForumMember.DoesNotExist:
                return 'student'
        elif self.sender_teacher:
            try:
                member = ForumMember.objects.get(forum=self.forum, teacher=self.sender_teacher)
                return member.role
            except ForumMember.DoesNotExist:
                return 'teacher'
        return None
    
    def soft_delete(self):
        """Soft delete a message"""
        self.is_deleted = True
        self.content = "[Message deleted]"
        self.save(update_fields=['is_deleted', 'content'])
    
    @property
    def reply_count(self):
        """Get number of replies to this message"""
        return self.replies.count()
    
    @property
    def reaction_count(self):
        """Get total number of reactions"""
        return self.reactions.count()

# models.py - Update MessageReaction model

class MessageReaction(models.Model):
    """
    Reactions to messages (like emoji reactions in WhatsApp)
    """
    REACTION_CHOICES = [
        ('👍', 'Thumbs Up'),
        ('❤️', 'Heart'),
        ('😂', 'Laugh'),
        ('😮', 'Surprise'),
        ('😢', 'Sad'),
        ('🙏', 'Pray'),
        ('👏', 'Clap'),
        ('🔥', 'Fire'),
    ]
    
    message = models.ForeignKey(ForumMessage, on_delete=models.CASCADE, related_name='reactions')
    
    # Make both nullable but ensure at least one is set
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_reactions', null=True, blank=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='message_reactions', null=True, blank=True)
    
    reaction = models.CharField(max_length=10, choices=REACTION_CHOICES, default='👍')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Message Reactions"
        # Update constraints
        constraints = [
            models.UniqueConstraint(
                fields=['message', 'user', 'reaction'],
                name='unique_message_user_reaction'
            ),
            models.UniqueConstraint(
                fields=['message', 'teacher', 'reaction'],
                name='unique_message_teacher_reaction'
            )
        ]
        ordering = ['created_at']
    
    def __str__(self):
        if self.user:
            return f"{self.user.full_name} reacted {self.reaction}"
        elif self.teacher:
            return f"{self.teacher.full_name} reacted {self.reaction}"
        return f"Unknown reacted {self.reaction}"
    
    def get_reactor_name(self):
        """Get the name of the person who reacted"""
        if self.user:
            return self.user.full_name
        elif self.teacher:
            return self.teacher.full_name
        return "Unknown"

class MessageReadReceipt(models.Model):
    """
    Track which users have read which messages (like WhatsApp blue ticks)
    """
    message = models.ForeignKey(ForumMessage, on_delete=models.CASCADE, related_name='read_receipts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_read_receipts')
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Message Read Receipts"
        unique_together = ['message', 'user']
        ordering = ['read_at']
    
    def __str__(self):
        return f"{self.user.full_name} read message {self.message.id}"


class ForumNotification(models.Model):
    """
    Push notifications for forum activities
    """
    NOTIFICATION_TYPE_CHOICES = [
        ('new_message', 'New Message'),
        ('reply', 'Reply to your message'),
        ('reaction', 'Reaction to your message'),
        ('mention', 'You were mentioned'),
        ('announcement', 'New Announcement'),
        ('member_joined', 'New Member Joined'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_notifications')
    message = models.ForeignKey(ForumMessage, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Forum Notifications"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recipient.full_name} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.save(update_fields=['is_read'])

class PasswordResetToken(models.Model):
    USER_TYPE_CHOICES = [
        ('user', 'User'),
        ('teacher', 'Teacher'),
    ]
    
    email = models.CharField(max_length=100)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Password Reset Tokens"

    def is_expired(self):
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() > self.created_at + timedelta(hours=1)  # Token valid for 1 hour

    def __str__(self):
        return f"{self.email} ({self.user_type}) - {'used' if self.is_used else 'active'}"