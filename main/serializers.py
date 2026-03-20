from rest_framework import serializers
from . import models
from .models import MentorshipSession, MentorshipRegistration
from django.utils import timezone


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Teacher
        fields = ['id', 'full_name', 'email', 'password', 'qualification', 'mobile_no', 'skills', 'profile_img', 'teacher_courses', 'skill_list']
        depth = 1
        extra_kwargs = {
            'password': {'write_only': True},
            'profile_pic': {'required': False, 'allow_null': True}
        }


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CourseCategory
        fields = ['id', 'title', 'description']




class CourseSerializer(serializers.ModelSerializer):
    total_enrolled_students = serializers.SerializerMethodField()
    category_title = serializers.CharField(source='category.title', read_only=True, allow_null=True)
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True, allow_null=True)
    average_rating = serializers.SerializerMethodField()
    total_ratings = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Course
        fields = [
            'id', 
            'title', 
            'category', 
            'category_title',
            'teacher', 
            'teacher_name',
            'description', 
            'featured_img', 
            'techs', 
            'total_enrolled_students',
            'views',
            'average_rating',
            'total_ratings',
            'created_at'
        ]
        extra_kwargs = {
            'category': {'required': False, 'allow_null': True},
            'teacher': {'required': False, 'allow_null': True}
        }
    
    def get_total_enrolled_students(self, obj):
        """Calculate the number of students enrolled in this course"""
        return obj.enrolled_students.count()
    
    def get_average_rating(self, obj):
        """Get average rating for the course"""
        return obj.average_rating
    
    def get_total_ratings(self, obj):
        """Get total number of ratings"""
        return obj.total_ratings

class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Chapter
        fields = ['id', 'course', 'title', 'description', 'video', 'remarks']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.User
        fields = ['id', 'full_name', 'email', 'username', 'password', 'interested_categories', 'status', 'profile_pic']
        extra_kwargs = {
            'password': {'write_only': True},
            'profile_pic': {'required': False, 'allow_null': True}
        }


class UserCourseEnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = models.UserCourseEnrollment
        fields = [
            'id', 
            'user', 
            'user_name', 
            'user_email',
            'user_username',
            'course', 
            'course_title', 
            'enrolled_date'
        ]


class CourseRatingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = models.CourseRating
        fields = ['id', 'user', 'user_name', 'course', 'rating', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['user', 'course', 'created_at', 'updated_at']


class FavoriteCourseSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_description = serializers.CharField(source='course.description', read_only=True)
    course_featured_img = serializers.CharField(source='course.featured_img', read_only=True)
    course_teacher_name = serializers.CharField(source='course.teacher.full_name', read_only=True)
    course_category_title = serializers.CharField(source='course.category.title', read_only=True)
    total_enrolled_students = serializers.SerializerMethodField()
    
    class Meta:
        model = models.FavoriteCourse
        fields = [
            'id',
            'user',
            'course',
            'course_title',
            'course_description',
            'course_featured_img',
            'course_teacher_name',
            'course_category_title',
            'total_enrolled_students',
            'added_date'
        ]
    
    def get_total_enrolled_students(self, obj):
        """Get enrollment count for the course"""
        return obj.course.enrolled_students.count()


class AssignmentSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    total_submissions = serializers.IntegerField(read_only=True)
    total_enrolled = serializers.SerializerMethodField()
    submission_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Assignment
        fields = [
            'id',
            'teacher',
            'teacher_name',
            'course',
            'course_title',
            'title',
            'description',
            'total_marks',
            'due_date',
            'is_active',
            'total_submissions',
            'total_enrolled',
            'submission_rate',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'total_submissions']
    
    def get_total_enrolled(self, obj):
        return obj.course.enrolled_students.count()
    
    def get_submission_rate(self, obj):
        total_enrolled = self.get_total_enrolled(obj)
        if total_enrolled > 0:
            return round((obj.total_submissions / total_enrolled) * 100, 2)
        return 0


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    course_title = serializers.CharField(source='assignment.course.title', read_only=True)
    grade_percentage = serializers.FloatField(read_only=True)
    
    class Meta:
        model = models.AssignmentSubmission
        fields = [
            'id',
            'assignment',
            'assignment_title',
            'course_title',
            'student',
            'student_name',
            'student_email',
            'submission_text',
            'submission_file',
            'status',
            'marks_obtained',
            'feedback',
            'grade_percentage',
            'is_late',
            'submitted_at',
            'graded_at'
        ]
        read_only_fields = ['submitted_at', 'graded_at', 'grade_percentage', 'is_late']


class CreateAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Assignment
        fields = ['course', 'title', 'description', 'total_marks', 'due_date', 'is_active']


class GradeAssignmentSerializer(serializers.Serializer):
    marks_obtained = serializers.IntegerField(required=True)
    feedback = serializers.CharField(required=False, allow_blank=True)


# Quiz Serializers - UPDATED WITH MISSING FIELDS
class QuizSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    total_questions = serializers.IntegerField(read_only=True)
    total_submissions = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = models.Quiz
        fields = [
            'id',
            'teacher',
            'teacher_name',
            'course',
            'course_title',
            'title',
            'description',
            'total_marks',
            'time_limit',
            'attempt_limit',
            'show_answers',
            'due_date',
            'is_active',
            'is_quiz',
            'total_questions',
            'total_submissions',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'total_questions', 'total_submissions', 'is_quiz']


class QuizQuestionSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    
    class Meta:
        model = models.QuizQuestion
        fields = [
            'id',
            'quiz',
            'quiz_title',
            'question_text',
            'option1',
            'option2',
            'option3',
            'option4',
            'correct_option',
            'marks',
            'explanation',
            'created_at'
        ]
        read_only_fields = ['created_at']


class QuizQuestionWithoutAnswerSerializer(serializers.ModelSerializer):
    """Serializer for quiz questions without showing the correct answer"""
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    
    class Meta:
        model = models.QuizQuestion
        fields = [
            'id',
            'quiz',
            'quiz_title',
            'question_text',
            'option1',
            'option2',
            'option3',
            'option4',
            'marks',
            'created_at'
        ]
        read_only_fields = ['created_at']


class QuizAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    student_name = serializers.CharField(source='submission.student.full_name', read_only=True)
    quiz_title = serializers.CharField(source='submission.quiz.title', read_only=True)
    
    class Meta:
        model = models.QuizAnswer
        fields = [
            'id',
            'submission',
            'question',
            'question_text',
            'selected_option',
            'is_correct',
            'marks_obtained',
            'answered_at'
        ]
        read_only_fields = ['answered_at']


class QuizSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    course_title = serializers.CharField(source='quiz.course.title', read_only=True)
    
    class Meta:
        model = models.QuizSubmission
        fields = [
            'id',
            'quiz',
            'quiz_title',
            'course_title',
            'student',
            'student_name',
            'student_email',
            'started_at',
            'submitted_at',
            'time_taken',
            'status',
            'total_questions_attempted',
            'total_correct_answers',
            'total_marks_obtained',
            'percentage',
            'is_passed'
        ]
        read_only_fields = ['started_at', 'submitted_at', 'percentage', 'is_passed']


class SubmitQuizAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(required=True)
    selected_option = serializers.IntegerField(required=True, min_value=1, max_value=4)


class StartQuizSerializer(serializers.Serializer):
    quiz_id = serializers.IntegerField(required=True)
    user_id = serializers.IntegerField(required=True)


class SubmitQuizSerializer(serializers.Serializer):
    submission_id = serializers.IntegerField(required=True)
    # Make answers optional and accept different formats
    answers = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
        default=[]
    )
    
    def validate_answers(self, value):
        """Custom validation for answers field"""
        validated_answers = []
        for answer in value:
            # Extract question_id and selected_option from the answer dictionary
            question_id = answer.get('question_id')
            selected_option = answer.get('selected_option')
            
            if question_id is None or selected_option is None:
                continue  # Skip invalid entries
            
            # Convert to proper types
            try:
                validated_answers.append({
                    'question_id': int(question_id),
                    'selected_option': int(selected_option)
                })
            except (ValueError, TypeError):
                continue  # Skip entries that can't be converted
        
        return validated_answers
    
class StudyMaterialSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    file_size = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    
    class Meta:
        model = models.StudyMaterial
        fields = [
            'id',
            'course',
            'course_title',
            'title',
            'description',
            'upload',
            'file_size',
            'file_name',
            'remarks',
            'uploaded_at',  # We'll add this field to the model
            'is_public'     # We'll add this field to the model
        ]
        read_only_fields = ['uploaded_at']
    
    def get_file_size(self, obj):
        """Get file size in bytes"""
        if obj.upload:
            try:
                return obj.upload.size
            except:
                return 0
        return 0
    
    def get_file_name(self, obj):
        """Get original file name"""
        if obj.upload:
            import os
            return os.path.basename(obj.upload.name)
        return None


class MentorshipSessionSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    is_live_now = serializers.BooleanField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    registered_count = serializers.IntegerField(read_only=True)
    user_registered = serializers.SerializerMethodField()
    user_can_join = serializers.SerializerMethodField()
    
    class Meta:
        model = MentorshipSession
        fields = [
            'id', 'title', 'description', 'session_link', 'session_type', 'status',
            'teacher', 'teacher_name', 'course', 'course_title',
            'scheduled_date', 'duration_minutes', 'max_participants',
            'is_active', 'created_at', 'updated_at',
            'is_upcoming', 'is_live_now', 'is_full',
            'registered_count', 'user_registered', 'user_can_join'
        ]
        read_only_fields = ['teacher', 'created_at', 'updated_at']
    
    def get_user_registered(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.registrations.filter(user=request.user).exists()
        return False
    
    def get_user_can_join(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        # Check if user is enrolled in the course
        from .models import UserCourseEnrollment
        is_enrolled = UserCourseEnrollment.objects.filter(
            user=request.user,
            course=obj.course
        ).exists()
        
        if not is_enrolled:
            return False
        
        # Check if session is live or upcoming
        if not obj.is_live_now and not obj.is_upcoming:
            return False
        
        # Check if user is registered (if registration required)
        if obj.max_participants and not obj.registrations.filter(user=request.user).exists():
            return obj.registered_count < obj.max_participants
        
        return True

class MentorshipRegistrationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True)
    course_title = serializers.CharField(source='session.course.title', read_only=True)
    
    class Meta:
        model = MentorshipRegistration
        fields = [
            'id', 'user', 'user_name', 'user_email',
            'session', 'session_title', 'course_title',
            'registered_at', 'attended', 'joined_at', 'left_at',
            'attendance_duration'
        ]
        read_only_fields = ['user', 'registered_at', 'attended', 'joined_at', 'left_at']

class CreateMentorshipSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipSession
        fields = [
            'title', 'description', 'session_link', 'session_type',
            'course', 'scheduled_date', 'duration_minutes',
            'max_participants'
        ]
    
    def validate(self, data):
        # Teacher must be enrolled in the course they're creating session for
        request = self.context.get('request')
        teacher = request.user.teacher_profile
        
        # Check if teacher teaches this course
        from .models import Course
        if not Course.objects.filter(id=data['course'].id, teacher=teacher).exists():
            raise serializers.ValidationError(
                "You can only create mentorship sessions for your own courses."
            )
        
        # Validate scheduled date is in future
        if data['scheduled_date'] <= timezone.now():
            raise serializers.ValidationError(
                "Scheduled date must be in the future."
            )
        
        return data
    
# Admin Serializer
class AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Admin
        fields = [
            'id', 'full_name', 'email', 'username', 'password', 
            'role', 'phone', 'profile_pic', 'is_active', 
            'is_super_admin', 'created_at', 'last_login'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'profile_pic': {'required': False, 'allow_null': True}
        }


# Admin Dashboard Stats Serializer
class AdminDashboardStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    total_teachers = serializers.IntegerField()
    total_courses = serializers.IntegerField()
    total_enrollments = serializers.IntegerField()
    total_categories = serializers.IntegerField()
    total_quizzes = serializers.IntegerField()
    total_assignments = serializers.IntegerField()
    active_users = serializers.IntegerField()
    inactive_users = serializers.IntegerField()
    recent_enrollments = serializers.IntegerField()
    popular_courses = serializers.ListField()
    recent_users = serializers.ListField()
    recent_teachers = serializers.ListField()

# ==================== FORUM SERIALIZERS ====================

class ForumMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()
    user_profile_pic = serializers.SerializerMethodField()
    
    class Meta:
        model = models.ForumMember
        fields = [
            'id', 'forum', 'user_id', 'user_name', 'user_email', 'user_profile_pic',
            'role', 'joined_at', 'last_seen_at', 'is_muted', 'is_admin'
        ]
        read_only_fields = ['joined_at']
    
    def get_user_name(self, obj):
        if obj.user:
            return obj.user.full_name
        elif obj.teacher:
            return obj.teacher.full_name
        return "Unknown"
    
    def get_user_email(self, obj):
        if obj.user:
            return obj.user.email
        elif obj.teacher:
            return obj.teacher.email
        return None
    
    def get_user_id(self, obj):
        if obj.user:
            return obj.user.id
        elif obj.teacher:
            return obj.teacher.id
        return None
    
    def get_user_profile_pic(self, obj):
        # Return user profile pic URL if exists
        return None


class MessageReactionSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = models.MessageReaction
        fields = ['id', 'message', 'user', 'teacher', 'user_name', 'reaction', 'created_at']
        read_only_fields = ['created_at']
    
    def get_user_name(self, obj):
        if obj.user:
            return obj.user.full_name
        elif obj.teacher:
            return obj.teacher.full_name
        return "Unknown"


class MessageReadReceiptSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = models.MessageReadReceipt
        fields = ['id', 'message', 'user', 'user_name', 'read_at']
        read_only_fields = ['read_at']


class ForumMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_email = serializers.SerializerMethodField()
    sender_role = serializers.SerializerMethodField()
    sender_type = serializers.SerializerMethodField()  # 'user' or 'teacher'
    reply_count = serializers.IntegerField(read_only=True)
    reactions = serializers.SerializerMethodField()
    user_reaction = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = models.ForumMessage
        fields = [
            'id', 'forum', 'sender_name', 'sender_email', 'sender_role', 'sender_type',
            'parent', 'message_type', 'content', 'image', 'file', 'file_name', 'file_size',
            'is_edited', 'is_pinned', 'is_announcement', 'is_deleted',
            'timestamp', 'edited_at', 'reply_count', 'reactions',
            'user_reaction', 'is_read'
        ]
        read_only_fields = ['timestamp', 'edited_at', 'is_deleted']
    
    def get_sender_name(self, obj):
        return obj.get_sender_name()
    
    def get_sender_email(self, obj):
        return obj.get_sender_email()
    
    def get_sender_role(self, obj):
        return obj.get_sender_role()
    
    def get_sender_type(self, obj):
        """Return whether sender is a 'user' or 'teacher'"""
        if obj.sender_user:
            return 'student'
        elif obj.sender_teacher:
            return 'teacher'
        return None
    
    def get_reactions(self, obj):
        reactions = obj.reactions.all()
        return MessageReactionSerializer(reactions, many=True).data
    
    def get_user_reaction(self, obj):
        # Since we don't have authentication, return None
        # The frontend will handle this based on the user's ID
        return None
    
    def get_is_read(self, obj):
        # Since we don't have authentication, return False
        return False
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # Don't show deleted messages content
        if instance.is_deleted:
            data['content'] = "[Message deleted]"
            data['image'] = None
            data['file'] = None
        
        return data


class ForumMessageCreateSerializer(serializers.ModelSerializer):
    # Support both user_id and teacher_id
    user_id = serializers.IntegerField(write_only=True, required=False)
    teacher_id = serializers.IntegerField(write_only=True, required=False)
    user_email = serializers.EmailField(write_only=True, required=False)
    teacher_email = serializers.EmailField(write_only=True, required=False)
    
    class Meta:
        model = models.ForumMessage
        fields = [
            'forum', 'user_id', 'teacher_id', 'user_email', 'teacher_email',
            'parent', 'message_type', 'content', 'image', 'file', 'is_announcement'
        ]
    
    def validate(self, data):
        print("=" * 50)
        print("🔍 Validating message data:")
        
        forum = data.get('forum')
        user_id = data.get('user_id')
        teacher_id = data.get('teacher_id')
        user_email = data.get('user_email')
        teacher_email = data.get('teacher_email')
        
        print(f"   forum_id: {forum.id if forum else 'None'}")
        print(f"   user_id: {user_id}")
        print(f"   teacher_id: {teacher_id}")
        print(f"   user_email: {user_email}")
        print(f"   teacher_email: {teacher_email}")
        
        # Determine sender type
        sender = None
        sender_type = None
        
        # Check user_id
        if user_id:
            try:
                sender = models.User.objects.get(id=user_id)
                sender_type = 'user'
                print(f"   ✅ Found user by ID: {sender.full_name} (ID: {sender.id})")
            except models.User.DoesNotExist:
                raise serializers.ValidationError({"user_id": "User not found"})
        
        # Check teacher_id
        elif teacher_id:
            try:
                sender = models.Teacher.objects.get(id=teacher_id)
                sender_type = 'teacher'
                print(f"   ✅ Found teacher by ID: {sender.full_name} (ID: {sender.id})")
            except models.Teacher.DoesNotExist:
                raise serializers.ValidationError({"teacher_id": "Teacher not found"})
        
        # Check user_email
        elif user_email:
            try:
                sender = models.User.objects.get(email=user_email)
                sender_type = 'user'
                print(f"   ✅ Found user by email: {sender.full_name}")
            except models.User.DoesNotExist:
                raise serializers.ValidationError({"user_email": "User not found"})
        
        # Check teacher_email
        elif teacher_email:
            try:
                sender = models.Teacher.objects.get(email=teacher_email)
                sender_type = 'teacher'
                print(f"   ✅ Found teacher by email: {sender.full_name}")
            except models.Teacher.DoesNotExist:
                raise serializers.ValidationError({"teacher_email": "Teacher not found"})
        
        else:
            raise serializers.ValidationError("Either user_id/email or teacher_id/email is required")
        
        # Check if sender is a member of the forum
        if sender_type == 'user':
            try:
                member = models.ForumMember.objects.get(forum=forum, user=sender)
                print(f"   ✅ User is a member (Role: {member.role})")
                data['member'] = member
            except models.ForumMember.DoesNotExist:
                # Auto-add if this is the course teacher
                if forum.course.teacher and forum.course.teacher.email == sender.email:
                    member = models.ForumMember.objects.create(
                        forum=forum,
                        user=sender,
                        role='teacher',
                        is_admin=True
                    )
                    data['member'] = member
                    print(f"   ✅ Auto-added user as teacher to forum")
                # Auto-add if student is enrolled in the course
                elif models.UserCourseEnrollment.objects.filter(course=forum.course, user=sender).exists():
                    member = models.ForumMember.objects.create(
                        forum=forum,
                        user=sender,
                        role='student',
                        is_admin=False
                    )
                    data['member'] = member
                    print(f"   ✅ Auto-added enrolled student to forum")
                else:
                    raise serializers.ValidationError("User is not enrolled in this course")
        
        elif sender_type == 'teacher':
            try:
                member = models.ForumMember.objects.get(forum=forum, teacher=sender)
                print(f"   ✅ Teacher is a member (Role: {member.role})")
                data['member'] = member
            except models.ForumMember.DoesNotExist:
                # Auto-add if this is the course teacher
                if forum.course.teacher and forum.course.teacher.id == sender.id:
                    member = models.ForumMember.objects.create(
                        forum=forum,
                        teacher=sender,
                        role='teacher',
                        is_admin=True
                    )
                    data['member'] = member
                    print(f"   ✅ Auto-added teacher to forum")
                else:
                    raise serializers.ValidationError("Teacher is not a member of this forum")
        
        # Store sender info
        data['sender_obj'] = sender
        data['sender_type'] = sender_type
        
        print("✅ Validation successful!")
        print("=" * 50)
        return data
    
    def create(self, validated_data):
        print("📝 Creating message with validated data:")
        
        # Remove helper fields
        validated_data.pop('user_id', None)
        validated_data.pop('teacher_id', None)
        validated_data.pop('user_email', None)
        validated_data.pop('teacher_email', None)
        validated_data.pop('member', None)
        
        sender = validated_data.pop('sender_obj')
        sender_type = validated_data.pop('sender_type')
        
        # Set the appropriate sender field
        if sender_type == 'user':
            validated_data['sender_user'] = sender
            print(f"   Sender (User): {sender.full_name} (ID: {sender.id})")
        else:
            validated_data['sender_teacher'] = sender
            print(f"   Sender (Teacher): {sender.full_name} (ID: {sender.id})")
        
        print(f"   Forum ID: {validated_data['forum'].id}")
        print(f"   Message type: {validated_data.get('message_type', 'text')}")
        
        # Handle file uploads
        if 'image' in validated_data and validated_data['image']:
            validated_data['message_type'] = 'image'
            validated_data['file_name'] = validated_data['image'].name
            validated_data['file_size'] = validated_data['image'].size
            print(f"   Image: {validated_data['file_name']} ({validated_data['file_size']} bytes)")
        elif 'file' in validated_data and validated_data['file']:
            validated_data['message_type'] = 'file'
            validated_data['file_name'] = validated_data['file'].name
            validated_data['file_size'] = validated_data['file'].size
            print(f"   File: {validated_data['file_name']} ({validated_data['file_size']} bytes)")
        else:
            print(f"   Content: {validated_data.get('content', '')[:50]}...")
        
        # Check if message requires approval
        forum = validated_data['forum']
        if forum.require_approval:
            if 'member' in validated_data and validated_data['member'].role == 'student':
                validated_data['requires_approval'] = True
                validated_data['is_approved'] = False
                print(f"   Message requires approval")
        
        message = super().create(validated_data)
        print(f"✅ Message created with ID: {message.id}")
        print("=" * 50)
        return message


class CourseForumSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_teacher = serializers.CharField(source='course.teacher.full_name', read_only=True)
    course_thumbnail = serializers.SerializerMethodField()
    total_members = serializers.IntegerField(read_only=True)
    total_messages = serializers.IntegerField(read_only=True)
    last_message = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    member_role = serializers.SerializerMethodField()
    
    class Meta:
        model = models.CourseForum
        fields = [
            'id', 'course', 'course_title', 'course_teacher', 'course_thumbnail',
            'name', 'description', 'group_icon', 'created_at', 'updated_at',
            'is_active', 'allow_student_messages', 'allow_file_sharing',
            'total_members', 'total_messages', 'last_message',
            'is_member', 'member_role'
        ]
    
    def get_course_thumbnail(self, obj):
        if obj.course.featured_img:
            return obj.course.featured_img.url
        return None
    
    def get_last_message(self, obj):
        last_msg = obj.last_message
        if last_msg:
            return ForumMessageSerializer(last_msg).data
        return None
    
    def get_is_member(self, obj):
        # Since we don't have authentication, return False
        # The frontend will determine this based on user data
        return False
    
    def get_member_role(self, obj):
        # Since we don't have authentication, return None
        return None


class ForumNotificationSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    forum_name = serializers.CharField(source='message.forum.name', read_only=True, allow_null=True)
    course_title = serializers.CharField(source='message.forum.course.title', read_only=True, allow_null=True)
    
    class Meta:
        model = models.ForumNotification
        fields = [
            'id', 'recipient', 'message', 'sender_name', 'forum_name', 'course_title',
            'notification_type', 'title', 'content', 'is_read', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_sender_name(self, obj):
        if obj.message:
            return obj.message.get_sender_name()
        return None