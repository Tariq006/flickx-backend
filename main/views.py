from django.shortcuts import render
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import User as DjangoUser
from django.db.models import Avg, Sum, Q, Count
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework import permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.authtoken.models import Token
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import secrets
import os

from .serializers import (
    # Existing serializers
    TeacherSerializer, CategorySerializer, CourseSerializer, ChapterSerializer, 
    UserSerializer, UserCourseEnrollmentSerializer, CourseRatingSerializer,
    FavoriteCourseSerializer, AssignmentSerializer, AssignmentSubmissionSerializer,
    GradeAssignmentSerializer, CreateAssignmentSerializer, QuizSerializer, 
    QuizQuestionSerializer, QuizQuestionWithoutAnswerSerializer, QuizSubmissionSerializer,
    StartQuizSerializer, SubmitQuizSerializer, SubmitQuizAnswerSerializer,
    StudyMaterialSerializer, MentorshipSessionSerializer, 
    MentorshipRegistrationSerializer, CreateMentorshipSessionSerializer, AdminSerializer,
    # Forum Serializers - All individually imported
    CourseForumSerializer, 
    ForumMemberSerializer, 
    ForumMessageSerializer,
    ForumMessageCreateSerializer, 
    MessageReactionSerializer, 
    MessageReadReceiptSerializer,
    ForumNotificationSerializer
)
from . import models
from .models import (
    MentorshipSession, MentorshipRegistration, UserCourseEnrollment,
    User, Teacher, PasswordResetToken
)


class TeacherList(generics.ListCreateAPIView):
    queryset = models.Teacher.objects.all()
    serializer_class = TeacherSerializer
    permission_classes = [AllowAny]
    
    def perform_create(self, serializer):
        password = serializer.validated_data.get('password')
        serializer.save(password=make_password(password))


class TeacherDetail(generics.RetrieveUpdateDestroyAPIView):  
    queryset = models.Teacher.objects.all()
    serializer_class = TeacherSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [AllowAny]
    
    def perform_update(self, serializer):
        if 'password' in serializer.validated_data:
            password = serializer.validated_data.get('password')
            serializer.save(password=make_password(password))
        else:
            serializer.save()


@api_view(['POST'])
@permission_classes([AllowAny])
def teacher_login(request):
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')

    if not email or not password:
        return Response({
            'bool': False,
            'error': 'Email and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        teacher = models.Teacher.objects.get(email=email)

        # Check hashed password (normal case)
        password_valid = check_password(password, teacher.password)

        # Fallback: handle legacy plain-text passwords (left by old reset bug)
        if not password_valid and teacher.password == password:
            password_valid = True
            # Auto-fix: re-hash so future logins work correctly
            teacher.password = make_password(password)
            teacher.save(update_fields=['password'])

        if password_valid:
            return Response({
                'bool': True,
                'teacher_id': teacher.id,
                'full_name': teacher.full_name,
                'email': teacher.email,
                'qualification': teacher.qualification,
                'mobile_no': teacher.mobile_no,
                'skills': teacher.skills
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'bool': False,
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)

    except models.Teacher.DoesNotExist:
        return Response({
            'bool': False,
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return Response({
            'bool': False,
            'error': 'An error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryList(generics.ListCreateAPIView):
    queryset = models.CourseCategory.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class CourseList(generics.ListCreateAPIView):
    queryset = models.Course.objects.all().prefetch_related('enrolled_students')
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]


class CourseDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = models.Course.objects.all().prefetch_related('enrolled_students')
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]


class TeacherCourseList(generics.ListCreateAPIView):   
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        teacher_id = self.kwargs['teacher_id']
        teacher = models.Teacher.objects.filter(pk=teacher_id).first()
        
        if not teacher:
            return models.Course.objects.none()
        
        return models.Course.objects.filter(teacher_id=teacher_id).prefetch_related('enrolled_students').order_by('-id')
    
    def perform_create(self, serializer):
        teacher_id = self.kwargs['teacher_id']
        try:
            teacher = models.Teacher.objects.get(pk=teacher_id)
            serializer.save(teacher=teacher)
        except models.Teacher.DoesNotExist:
            raise ValidationError({'teacher': 'Teacher not found'})


class TeacherCourseDetail(generics.RetrieveUpdateDestroyAPIView):  
    queryset = models.Course.objects.all().prefetch_related('enrolled_students')
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]


class ChapterList(generics.ListCreateAPIView):
    queryset = models.Chapter.objects.all()   
    serializer_class = ChapterSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [AllowAny]


class ChapterDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = models.Chapter.objects.all()
    serializer_class = ChapterSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [AllowAny]


class CourseChapterList(generics.ListAPIView):
    serializer_class = ChapterSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        return models.Chapter.objects.filter(course_id=course_id)


class UserList(generics.ListCreateAPIView):
    queryset = models.User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    
    def perform_create(self, serializer):
        email = serializer.validated_data.get('email')
        if models.Teacher.objects.filter(email=email).exists():
            raise ValidationError({'email': 'This email is already registered as a teacher account.'})
        password = serializer.validated_data.get('password')
        serializer.save(password=make_password(password))


class UserDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = models.User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    
    def perform_update(self, serializer):
        if 'password' in serializer.validated_data:
            password = serializer.validated_data.get('password')
            serializer.save(password=make_password(password))
        else:
            serializer.save()


@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')

    if not username or not password:
        return Response({
            'bool': False,
            'error': 'Username and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Support login with either username or email
        user = models.User.objects.filter(
            Q(username=username) | Q(email=username)
        ).first()

        if not user:
            return Response({
                'bool': False,
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Check hashed password (normal case)
        password_valid = check_password(password, user.password)

        # Fallback: handle legacy plain-text passwords left by the old reset bug
        if not password_valid and user.password == password:
            password_valid = True
            # Auto-fix: re-hash so future logins work correctly
            user.password = make_password(password)
            user.save(update_fields=['password'])

        if password_valid:
            return Response({
                'bool': True,
                'user_id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'username': user.username,
                'interested_categories': user.interested_categories,
                'status': user.status
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'bool': False,
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)

    except Exception as e:
        return Response({
            'bool': False,
            'error': 'An error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Enrollment Views
class UserCourseEnrollmentList(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    queryset = models.UserCourseEnrollment.objects.all()
    serializer_class = UserCourseEnrollmentSerializer


class UserCourseEnrollmentDetail(generics.RetrieveDestroyAPIView):
    permission_classes = [AllowAny]
    queryset = models.UserCourseEnrollment.objects.all()
    serializer_class = UserCourseEnrollmentSerializer


class CourseEnrollments(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserCourseEnrollmentSerializer
    
    def get_queryset(self):
        course_id = self.kwargs['course_id']
        return models.UserCourseEnrollment.objects.filter(course_id=course_id)


class UserEnrollments(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserCourseEnrollmentSerializer
    
    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return models.UserCourseEnrollment.objects.filter(user_id=user_id)


@api_view(['POST'])
@permission_classes([AllowAny])
def check_enrollment_status(request):
    user_id = request.data.get('user_id')
    course_id = request.data.get('course_id')
    
    if not user_id or not course_id:
        return Response({
            'bool': False,
            'error': 'User ID and Course ID are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        enrollment = models.UserCourseEnrollment.objects.get(
            user_id=user_id,
            course_id=course_id
        )
        return Response({
            'bool': True,
            'enrollment_id': enrollment.id,
            'enrolled_date': enrollment.enrolled_date
        })
    except models.UserCourseEnrollment.DoesNotExist:
        return Response({
            'bool': False,
            'message': 'User is not enrolled in this course'
        })
    except Exception as e:
        return Response({
            'bool': False,
            'error': 'An error occurred while checking enrollment status'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def enroll_user(request):
    user_id = request.data.get('user_id')
    course_id = request.data.get('course_id')
    
    if not user_id or not course_id:
        return Response({
            'success': False,
            'error': 'User ID and Course ID are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = models.User.objects.get(id=user_id)
        course = models.Course.objects.get(id=course_id)
        
        if models.UserCourseEnrollment.objects.filter(user=user, course=course).exists():
            return Response({
                'success': False,
                'message': 'User is already enrolled in this course'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        enrollment = models.UserCourseEnrollment.objects.create(
            user=user,
            course=course
        )
        
        return Response({
            'success': True,
            'message': 'Successfully enrolled in course',
            'enrollment_id': enrollment.id,
            'enrolled_date': enrollment.enrolled_date
        }, status=status.HTTP_201_CREATED)
        
    except models.User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except models.Course.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': 'An error occurred while enrolling'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Rating Views
class CourseRatingList(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = CourseRatingSerializer
    
    def get_queryset(self):
        course_id = self.kwargs['course_id']
        return models.CourseRating.objects.filter(course_id=course_id)
    
    def perform_create(self, serializer):
        course_id = self.kwargs['course_id']
        user_id = self.request.data.get('user_id')
        
        try:
            course = models.Course.objects.get(id=course_id)
            user = models.User.objects.get(id=user_id)
            
            existing_rating = models.CourseRating.objects.filter(user=user, course=course).first()
            if existing_rating:
                raise ValidationError({'error': 'You have already rated this course'})
            
            serializer.save(user=user, course=course)
        except models.Course.DoesNotExist:
            raise ValidationError({'error': 'Course not found'})
        except models.User.DoesNotExist:
            raise ValidationError({'error': 'User not found'})


class UserCourseRating(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = CourseRatingSerializer
    
    def get_object(self):
        course_id = self.kwargs['course_id']
        user_id = self.kwargs['user_id']
        
        try:
            return models.CourseRating.objects.get(
                course_id=course_id,
                user_id=user_id
            )
        except models.CourseRating.DoesNotExist:
            return None


class CourseRatingStats(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    def get(self, request, *args, **kwargs):
        course_id = self.kwargs['course_id']
        
        ratings = models.CourseRating.objects.filter(course_id=course_id)
        
        if not ratings.exists():
            return Response({
                'average': 0,
                'count': 0,
                'distribution': {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
            })
        
        total_ratings = ratings.count()
        average = ratings.aggregate(Avg('rating'))['rating__avg']
        
        distribution = {
            5: ratings.filter(rating=5).count(),
            4: ratings.filter(rating=4).count(),
            3: ratings.filter(rating=3).count(),
            2: ratings.filter(rating=2).count(),
            1: ratings.filter(rating=1).count(),
        }
        
        return Response({
            'average': round(average, 2),
            'count': total_ratings,
            'distribution': distribution
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_rating(request):
    user_id = request.data.get('user_id')
    course_id = request.data.get('course_id')
    rating = request.data.get('rating')
    comment = request.data.get('comment', '')
    
    if not all([user_id, course_id, rating]):
        return Response({
            'success': False,
            'error': 'User ID, Course ID, and Rating are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = models.User.objects.get(id=user_id)
        course = models.Course.objects.get(id=course_id)
        
        is_enrolled = models.UserCourseEnrollment.objects.filter(user=user, course=course).exists()
        if not is_enrolled:
            return Response({
                'success': False,
                'error': 'You must be enrolled in the course to rate it'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            rating = int(rating)
            if rating not in [1, 2, 3, 4, 5]:
                return Response({
                    'success': False,
                    'error': 'Rating must be between 1 and 5'
                }, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'error': 'Rating must be a valid number'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        existing_rating = models.CourseRating.objects.filter(user=user, course=course).first()
        if existing_rating:
            existing_rating.rating = rating
            existing_rating.comment = comment
            existing_rating.save()
            action = 'updated'
        else:
            models.CourseRating.objects.create(
                user=user,
                course=course,
                rating=rating,
                comment=comment
            )
            action = 'submitted'
        
        ratings = models.CourseRating.objects.filter(course=course)
        average = ratings.aggregate(Avg('rating'))['rating__avg']
        
        return Response({
            'success': True,
            'message': f'Rating {action} successfully',
            'average_rating': round(average, 2) if average else 0,
            'total_ratings': ratings.count()
        }, status=status.HTTP_200_OK)
        
    except models.User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except models.Course.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in submit_rating: {str(e)}")
        return Response({
            'success': False,
            'error': f'An error occurred while submitting rating: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Favorite Course Views
class UserFavoriteCourses(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = FavoriteCourseSerializer
    
    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return models.FavoriteCourse.objects.filter(user_id=user_id).select_related('course', 'course__teacher', 'course__category')


@api_view(['POST'])
@permission_classes([AllowAny])
def check_favorite_status(request):
    user_id = request.data.get('user_id')
    course_id = request.data.get('course_id')
    
    if not user_id or not course_id:
        return Response({
            'bool': False,
            'error': 'User ID and Course ID are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        favorite = models.FavoriteCourse.objects.get(
            user_id=user_id,
            course_id=course_id
        )
        return Response({
            'bool': True,
            'favorite_id': favorite.id,
            'added_date': favorite.added_date
        })
    except models.FavoriteCourse.DoesNotExist:
        return Response({
            'bool': False,
            'message': 'Course is not in favorites'
        })
    except Exception as e:
        return Response({
            'bool': False,
            'error': 'An error occurred while checking favorite status'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def toggle_favorite(request):
    user_id = request.data.get('user_id')
    course_id = request.data.get('course_id')
    
    if not user_id or not course_id:
        return Response({
            'success': False,
            'error': 'User ID and Course ID are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = models.User.objects.get(id=user_id)
        course = models.Course.objects.get(id=course_id)
        
        favorite = models.FavoriteCourse.objects.filter(user=user, course=course).first()
        
        if favorite:
            favorite.delete()
            return Response({
                'success': True,
                'action': 'removed',
                'message': 'Course removed from favorites',
                'is_favorite': False
            }, status=status.HTTP_200_OK)
        else:
            favorite = models.FavoriteCourse.objects.create(
                user=user,
                course=course
            )
            return Response({
                'success': True,
                'action': 'added',
                'message': 'Course added to favorites',
                'is_favorite': True,
                'favorite_id': favorite.id,
                'added_date': favorite.added_date
            }, status=status.HTTP_201_CREATED)
        
    except models.User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except models.Course.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in toggle_favorite: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while updating favorites'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def remove_favorite(request, favorite_id):
    try:
        favorite = models.FavoriteCourse.objects.get(id=favorite_id)
        favorite.delete()
        
        return Response({
            'success': True,
            'message': 'Course removed from favorites'
        }, status=status.HTTP_200_OK)
        
    except models.FavoriteCourse.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Favorite not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': 'An error occurred while removing favorite'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Assignment Views
class TeacherAssignments(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = AssignmentSerializer
    
    def get_queryset(self):
        teacher_id = self.kwargs['teacher_id']
        return models.Assignment.objects.filter(
            teacher_id=teacher_id
        ).select_related('course', 'teacher').order_by('-created_at')
    
    def perform_create(self, serializer):
        teacher_id = self.kwargs['teacher_id']
        try:
            teacher = models.Teacher.objects.get(id=teacher_id)
            serializer.save(teacher=teacher)
        except models.Teacher.DoesNotExist:
            raise ValidationError({'error': 'Teacher not found'})


class CourseAssignments(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateAssignmentSerializer
        return AssignmentSerializer
    
    def get_queryset(self):
        course_id = self.kwargs['course_id']
        return models.Assignment.objects.filter(
            course_id=course_id
        ).select_related('course', 'teacher').order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        course_id = self.kwargs['course_id']
        teacher_id = request.data.get('teacher_id')
        
        print(f"DEBUG - Creating assignment for course: {course_id}")
        print(f"DEBUG - Teacher ID: {teacher_id}")
        print(f"DEBUG - Request data: {request.data}")
        
        if not teacher_id:
            return Response({
                'success': False,
                'error': 'Teacher ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            course = models.Course.objects.get(id=course_id)
            teacher = models.Teacher.objects.get(id=teacher_id)
            
            print(f"DEBUG - Found course: {course.title}")
            print(f"DEBUG - Found teacher: {teacher.full_name}")
            print(f"DEBUG - Course teacher ID: {course.teacher_id}")
            print(f"DEBUG - Request teacher ID: {teacher_id}")
            
            # Check if teacher owns the course
            if course.teacher_id != int(teacher_id):
                return Response({
                    'success': False,
                    'error': f'You can only create assignments for your own courses. This course belongs to teacher ID: {course.teacher_id}'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Create the assignment
            assignment = models.Assignment.objects.create(
                teacher=teacher,
                course=course,
                title=request.data.get('title'),
                description=request.data.get('description'),
                total_marks=request.data.get('total_marks', 100),
                due_date=request.data.get('due_date'),
                is_active=request.data.get('is_active', True)
            )
            
            serializer = AssignmentSerializer(assignment)
            return Response({
                'success': True,
                'message': 'Assignment created successfully',
                'assignment': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except models.Course.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Course not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except models.Teacher.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Teacher not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error in create_assignment: {str(e)}")
            return Response({
                'success': False,
                'error': f'Error creating assignment: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssignmentDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    queryset = models.Assignment.objects.all()
    serializer_class = AssignmentSerializer


class AssignmentSubmissions(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = AssignmentSubmissionSerializer
    
    def get_queryset(self):
        assignment_id = self.kwargs['assignment_id']
        return models.AssignmentSubmission.objects.filter(
            assignment_id=assignment_id
        ).select_related('student', 'assignment', 'assignment__course').order_by('-submitted_at')


class StudentAssignmentSubmissions(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = AssignmentSubmissionSerializer
    
    def get_queryset(self):
        student_id = self.kwargs['student_id']
        return models.AssignmentSubmission.objects.filter(
            student_id=student_id
        ).select_related('assignment', 'assignment__course').order_by('-submitted_at')


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_assignment(request):
    assignment_id = request.data.get('assignment_id')
    student_id = request.data.get('student_id')
    submission_text = request.data.get('submission_text', '')
    submission_file = request.FILES.get('submission_file', None)
    
    if not assignment_id or not student_id:
        return Response({
            'success': False,
            'error': 'Assignment ID and Student ID are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        assignment = models.Assignment.objects.get(id=assignment_id)
        student = models.User.objects.get(id=student_id)
        
        is_enrolled = models.UserCourseEnrollment.objects.filter(
            user=student,
            course=assignment.course
        ).exists()
        
        if not is_enrolled:
            return Response({
                'success': False,
                'error': 'You must be enrolled in the course to submit assignments'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not assignment.is_active:
            return Response({
                'success': False,
                'error': 'This assignment is no longer active'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        existing_submission = models.AssignmentSubmission.objects.filter(
            assignment=assignment,
            student=student
        ).first()
        
        if existing_submission:
            existing_submission.submission_text = submission_text
            if submission_file:
                existing_submission.submission_file = submission_file
            existing_submission.save()
            
            return Response({
                'success': True,
                'message': 'Assignment submission updated',
                'submission_id': existing_submission.id,
                'submitted_at': existing_submission.submitted_at
            })
        else:
            submission = models.AssignmentSubmission.objects.create(
                assignment=assignment,
                student=student,
                submission_text=submission_text,
                submission_file=submission_file
            )
            
            return Response({
                'success': True,
                'message': 'Assignment submitted successfully',
                'submission_id': submission.id,
                'submitted_at': submission.submitted_at
            }, status=status.HTTP_201_CREATED)
        
    except models.Assignment.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Assignment not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except models.User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Student not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in submit_assignment: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while submitting assignment'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def grade_assignment(request, submission_id):
    serializer = GradeAssignmentSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    marks_obtained = serializer.validated_data['marks_obtained']
    feedback = serializer.validated_data.get('feedback', '')
    
    try:
        submission = models.AssignmentSubmission.objects.get(id=submission_id)
        
        if marks_obtained < 0 or marks_obtained > submission.assignment.total_marks:
            return Response({
                'success': False,
                'error': f'Marks must be between 0 and {submission.assignment.total_marks}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        submission.marks_obtained = marks_obtained
        submission.feedback = feedback
        submission.save()
        
        return Response({
            'success': True,
            'message': 'Assignment graded successfully',
            'marks_obtained': marks_obtained,
            'grade_percentage': submission.grade_percentage,
            'graded_at': submission.graded_at
        })
        
    except models.AssignmentSubmission.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Submission not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in grade_assignment: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while grading assignment'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def assignment_stats(request, assignment_id):
    try:
        assignment = models.Assignment.objects.get(id=assignment_id)
        submissions = models.AssignmentSubmission.objects.filter(assignment=assignment)
        
        total_students = assignment.course.enrolled_students.count()
        total_submissions = submissions.count()
        
        if total_submissions > 0:
            graded_count = submissions.filter(status='graded').count()
            late_count = submissions.filter(is_late=True).count()
            
            graded_submissions = submissions.exclude(marks_obtained__isnull=True)
            if graded_submissions.exists():
                avg_marks = graded_submissions.aggregate(Avg('marks_obtained'))['marks_obtained__avg']
                avg_percentage = (avg_marks / assignment.total_marks) * 100
            else:
                avg_marks = 0
                avg_percentage = 0
            
            stats = {
                'assignment_id': assignment.id,
                'assignment_title': assignment.title,
                'total_students': total_students,
                'total_submissions': total_submissions,
                'submission_rate': (total_submissions / total_students * 100) if total_students > 0 else 0,
                'graded_count': graded_count,
                'late_count': late_count,
                'average_marks': round(avg_marks, 2),
                'average_percentage': round(avg_percentage, 2),
                'pending_grading': total_submissions - graded_count
            }
        else:
            stats = {
                'assignment_id': assignment.id,
                'assignment_title': assignment.title,
                'total_students': total_students,
                'total_submissions': 0,
                'submission_rate': 0,
                'graded_count': 0,
                'late_count': 0,
                'average_marks': 0,
                'average_percentage': 0,
                'pending_grading': 0
            }
        
        return Response({
            'success': True,
            'stats': stats
        })
        
    except models.Assignment.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Assignment not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in assignment_stats: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while fetching assignment statistics'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Simple assignment creation endpoint (alternative)
@api_view(['POST'])
@permission_classes([AllowAny])
def create_assignment_simple(request):
    teacher_id = request.data.get('teacher_id')
    course_id = request.data.get('course_id')
    title = request.data.get('title')
    description = request.data.get('description')
    total_marks = request.data.get('total_marks', 100)
    due_date = request.data.get('due_date')
    is_active = request.data.get('is_active', True)
    
    if not all([teacher_id, course_id, title, description]):
        return Response({
            'success': False,
            'error': 'Teacher ID, Course ID, Title, and Description are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        teacher = models.Teacher.objects.get(id=teacher_id)
        course = models.Course.objects.get(id=course_id)
        
        # Check if teacher owns the course
        if course.teacher and course.teacher.id != teacher.id:
            return Response({
                'success': False,
                'error': 'You can only create assignments for your own courses'
            }, status=status.HTTP_403_FORBIDDEN)
        
        assignment = models.Assignment.objects.create(
            teacher=teacher,
            course=course,
            title=title,
            description=description,
            total_marks=total_marks,
            due_date=due_date,
            is_active=is_active
        )
        
        return Response({
            'success': True,
            'message': 'Assignment created successfully',
            'assignment_id': assignment.id,
            'title': assignment.title
        }, status=status.HTTP_201_CREATED)
        
    except models.Teacher.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Teacher not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except models.Course.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in create_assignment_simple: {str(e)}")
        return Response({
            'success': False,
            'error': f'Error creating assignment: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Quiz Views
class TeacherQuizzes(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = QuizSerializer
    
    def get_queryset(self):
        teacher_id = self.kwargs['teacher_id']
        return models.Quiz.objects.filter(
            teacher_id=teacher_id
        ).select_related('course', 'teacher').order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        teacher_id = self.kwargs['teacher_id']
        
        try:
            teacher = models.Teacher.objects.get(id=teacher_id)
            course_id = request.data.get('course_id')
            
            if not course_id:
                return Response({
                    'success': False,
                    'error': 'Course ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            course = models.Course.objects.get(id=course_id)
            
            # Check if teacher owns the course
            if course.teacher_id != teacher.id:
                return Response({
                    'success': False,
                    'error': 'You can only create quizzes for your own courses'
                }, status=status.HTTP_403_FORBIDDEN)
            
            total_marks = request.data.get('total_marks')
            if total_marks is None:
                total_marks = 0
            
            quiz = models.Quiz.objects.create(
                teacher=teacher,
                course=course,
                title=request.data.get('title'),
                description=request.data.get('description'),
                total_marks=total_marks,
                time_limit=request.data.get('time_limit', 60),
                attempt_limit=request.data.get('attempt_limit', 1),
                show_answers=request.data.get('show_answers', False),
                due_date=request.data.get('due_date'),
                is_active=request.data.get('is_active', True)
            )
            
            serializer = QuizSerializer(quiz)
            return Response({
                'success': True,
                'message': 'Quiz created successfully',
                'quiz': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except models.Teacher.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Teacher not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except models.Course.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Course not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error in create_quiz: {str(e)}")
            return Response({
                'success': False,
                'error': f'Error creating quiz: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CourseQuizzes(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = QuizSerializer
    
    def get_queryset(self):
        course_id = self.kwargs['course_id']
        return models.Quiz.objects.filter(
            course_id=course_id
        ).select_related('course', 'teacher').order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        course_id = self.kwargs['course_id']
        teacher_id = request.data.get('teacher_id')
        
        print(f"DEBUG - Creating quiz for course: {course_id}")
        print(f"DEBUG - Teacher ID: {teacher_id}")
        print(f"DEBUG - Request data: {request.data}")
        
        if not teacher_id:
            return Response({
                'error': 'Teacher ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            course = models.Course.objects.get(id=course_id)
            teacher = models.Teacher.objects.get(id=teacher_id)
            
            print(f"DEBUG - Found course: {course.title}")
            print(f"DEBUG - Found teacher: {teacher.full_name}")
            
            # Check if teacher owns the course
            if course.teacher_id != int(teacher_id):
                return Response({
                    'error': 'You can only create quizzes for your own courses'
                }, status=status.HTTP_403_FORBIDDEN)
            
            total_marks = request.data.get('total_marks')
            if total_marks is None:
                total_marks = 0
            
            # Create the quiz
            quiz = models.Quiz.objects.create(
                teacher=teacher,
                course=course,
                title=request.data.get('title'),
                description=request.data.get('description'),
                total_marks=total_marks,
                time_limit=request.data.get('time_limit', 60),
                attempt_limit=request.data.get('attempt_limit', 1),
                show_answers=request.data.get('show_answers', False),
                due_date=request.data.get('due_date'),
                is_active=request.data.get('is_active', True)
            )
            
            serializer = QuizSerializer(quiz)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except models.Course.DoesNotExist:
            return Response({
                'error': 'Course not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except models.Teacher.DoesNotExist:
            return Response({
                'error': 'Teacher not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error in create_quiz: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'error': f'Error creating quiz: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QuizDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    queryset = models.Quiz.objects.all()
    serializer_class = QuizSerializer


class QuizQuestions(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = QuizQuestionSerializer
    
    def get_queryset(self):
        quiz_id = self.kwargs['quiz_id']
        return models.QuizQuestion.objects.filter(quiz_id=quiz_id).order_by('id')
    
    def perform_create(self, serializer):
        quiz_id = self.kwargs['quiz_id']
        try:
            quiz = models.Quiz.objects.get(id=quiz_id)
            question = serializer.save(quiz=quiz)
            
            # Update quiz's total_marks after adding question
            self.update_quiz_total_marks(quiz)
            
        except models.Quiz.DoesNotExist:
            raise ValidationError({'error': 'Quiz not found'})
    
    def update_quiz_total_marks(self, quiz):
        """Helper method to update quiz total marks"""
        total_marks = models.QuizQuestion.objects.filter(quiz=quiz).aggregate(
            total=Sum('marks')
        )['total'] or 0
        
        quiz.total_marks = total_marks
        quiz.save()


class QuizQuestionDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    queryset = models.QuizQuestion.objects.all()
    serializer_class = QuizQuestionSerializer
    
    def perform_update(self, serializer):
        question = self.get_object()
        quiz = question.quiz
        serializer.save()
        
        # Update quiz total marks after updating question
        self.update_quiz_total_marks(quiz)
    
    def perform_destroy(self, instance):
        quiz = instance.quiz
        instance.delete()
        
        # Update quiz total marks after deleting question
        self.update_quiz_total_marks(quiz)
    
    def update_quiz_total_marks(self, quiz):
        """Helper method to update quiz total marks"""
        total_marks = models.QuizQuestion.objects.filter(quiz=quiz).aggregate(
            total=Sum('marks')
        )['total'] or 0
        
        quiz.total_marks = total_marks
        quiz.save()


@api_view(['POST'])
@permission_classes([AllowAny])
def start_quiz(request):
    """Start a new quiz attempt with attempt limit validation"""
    serializer = StartQuizSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    quiz_id = serializer.validated_data['quiz_id']
    user_id = serializer.validated_data['user_id']
    
    try:
        quiz = models.Quiz.objects.get(id=quiz_id)
        student = models.User.objects.get(id=user_id)
        
        # Check if student is enrolled in the course
        is_enrolled = models.UserCourseEnrollment.objects.filter(
            user=student,
            course=quiz.course
        ).exists()
        
        if not is_enrolled:
            return Response({
                'success': False,
                'error': 'You must be enrolled in the course to take this quiz'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if quiz is active
        if not quiz.is_active:
            return Response({
                'success': False,
                'error': 'This quiz is not active'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check due date if set
        if quiz.due_date and timezone.now() > quiz.due_date:
            return Response({
                'success': False,
                'error': 'This quiz has expired'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check attempt limits
        completed_attempts = models.QuizSubmission.objects.filter(
            quiz=quiz,
            student=student,
            status__in=['submitted', 'graded', 'completed']
        ).count()
        
        in_progress_attempts = models.QuizSubmission.objects.filter(
            quiz=quiz,
            student=student,
            status='in_progress'
        ).count()
        
        # Check if user has reached attempt limit
        if quiz.attempt_limit > 0 and completed_attempts >= quiz.attempt_limit:
            return Response({
                'success': False,
                'error': f'You have used all {quiz.attempt_limit} attempts for this quiz',
                'attempts_used': completed_attempts,
                'attempt_limit': quiz.attempt_limit
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if there's already an in-progress submission
        existing_submission = models.QuizSubmission.objects.filter(
            quiz=quiz,
            student=student,
            status='in_progress'
        ).first()
        
        if existing_submission:
            # Return existing in-progress submission
            submission_serializer = QuizSubmissionSerializer(existing_submission)
            return Response({
                'success': True,
                'message': 'Continuing existing quiz attempt',
                'submission': submission_serializer.data,
                'attempts_used': completed_attempts,
                'attempts_remaining': quiz.attempt_limit - completed_attempts if quiz.attempt_limit > 0 else 'unlimited'
            }, status=status.HTTP_200_OK)
        
        # If no in-progress but has completed attempts, check if can start new
        if completed_attempts > 0 and quiz.attempt_limit > 0:
            if completed_attempts < quiz.attempt_limit:
                # Can start new attempt
                pass
            else:
                return Response({
                    'success': False,
                    'error': f'You have used all {quiz.attempt_limit} attempts for this quiz',
                    'attempts_used': completed_attempts,
                    'attempt_limit': quiz.attempt_limit
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create new submission
        submission = models.QuizSubmission.objects.create(
            quiz=quiz,
            student=student,
            status='in_progress',
            started_at=timezone.now()
        )
        
        # Calculate attempt number
        attempt_number = completed_attempts + 1
        
        submission_serializer = QuizSubmissionSerializer(submission)
        return Response({
            'success': True,
            'message': 'Quiz started successfully',
            'submission': submission_serializer.data,
            'attempt_number': attempt_number,
            'attempts_used': completed_attempts,
            'attempts_remaining': quiz.attempt_limit - completed_attempts if quiz.attempt_limit > 0 else 'unlimited',
            'attempt_limit': quiz.attempt_limit
        }, status=status.HTTP_201_CREATED)
        
    except models.Quiz.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Quiz not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except models.User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Student not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in start_quiz: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while starting the quiz'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_quiz_questions(request, quiz_id):
    """Get quiz questions for students taking OR reviewing a quiz.
    
    - in_progress: returns questions without correct answers
    - submitted / graded / completed: returns questions WITH correct answers
      and explanations (review mode), respecting show_answers flag
    """
    user_id = request.query_params.get('user_id')
    submission_id = request.query_params.get('submission_id')
    
    if not user_id or not submission_id:
        return Response({
            'success': False,
            'error': 'user_id and submission_id are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        quiz = models.Quiz.objects.get(id=quiz_id)
        student = models.User.objects.get(id=user_id)
        submission = models.QuizSubmission.objects.get(id=submission_id, quiz=quiz, student=student)
        
        allowed_statuses = ['in_progress', 'completed', 'submitted', 'graded']
        if submission.status not in allowed_statuses:
            return Response({
                'success': False,
                'error': 'Quiz submission not found or invalid status'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        is_review = submission.status in ['submitted', 'graded', 'completed']
        
        questions = models.QuizQuestion.objects.filter(quiz=quiz).order_by('id')
        
        # Get existing answers for this submission
        existing_answers = models.QuizAnswer.objects.filter(
            submission=submission
        ).values_list('question_id', 'selected_option', 'is_correct', 'marks_obtained')
        
        existing_answers_dict = {
            qid: {
                'selected_option': option,
                'is_correct': is_correct,
                'marks_obtained': marks_obtained
            }
            for qid, option, is_correct, marks_obtained in existing_answers
        }
        
        # Check if request is from a teacher (teacher_id param signals teacher view)
        is_teacher_view = bool(request.query_params.get('teacher_id'))

        questions_data = []
        for question in questions:
            if is_review or is_teacher_view:
                # Full data including correct answer and explanation
                question_data = QuizQuestionSerializer(question).data
            else:
                # Hide correct_option and explanation during active quiz
                question_data = QuizQuestionWithoutAnswerSerializer(question).data
            
            answer_info = existing_answers_dict.get(question.id, {})
            question_data['selected_option'] = answer_info.get('selected_option')
            question_data['is_correct'] = answer_info.get('is_correct', False)
            question_data['marks_obtained'] = answer_info.get('marks_obtained', 0)

            # Always expose correct_option and explanation for teachers;
            # for students, only when quiz.show_answers is enabled
            if is_teacher_view or (is_review and quiz.show_answers):
                question_data['correct_option'] = question.correct_option
                question_data['explanation'] = question.explanation
            
            questions_data.append(question_data)
        
        return Response({
            'success': True,
            'quiz': {
                'id': quiz.id,
                'title': quiz.title,
                'description': quiz.description,
                'total_marks': quiz.total_marks,
                'time_limit': quiz.time_limit,
                'total_questions': quiz.total_questions,
                'show_answers': quiz.show_answers,
            },
            'submission': {
                'id': submission.id,
                'status': submission.status,
                'started_at': submission.started_at,
                'submitted_at': submission.submitted_at,
                'total_marks_obtained': submission.total_marks_obtained,
                'percentage': submission.percentage,
                'is_passed': submission.is_passed,
                'total_correct_answers': submission.total_correct_answers,
            },
            'is_review': is_review,
            'questions': questions_data,
            'total_questions': len(questions_data)
        })
        
    except models.Quiz.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Quiz not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except models.User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Student not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except models.QuizSubmission.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Submission not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in get_quiz_questions: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while fetching quiz questions'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_quiz_answer(request):
    """Submit an answer for a quiz question"""
    submission_id = request.data.get('submission_id')
    question_id = request.data.get('question_id')
    selected_option = request.data.get('selected_option')
    
    if not all([submission_id, question_id, selected_option]):
        return Response({
            'success': False,
            'error': 'Submission ID, Question ID, and Selected Option are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        selected_option = int(selected_option)
        if selected_option not in [1, 2, 3, 4]:
            return Response({
                'success': False,
                'error': 'Selected option must be between 1 and 4'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        submission = models.QuizSubmission.objects.get(id=submission_id)
        question = models.QuizQuestion.objects.get(id=question_id)
        
        # Check if the question belongs to the quiz
        if question.quiz_id != submission.quiz_id:
            return Response({
                'success': False,
                'error': 'Question does not belong to this quiz'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if submission is in progress
        if submission.status not in ['in_progress', 'completed']:
            return Response({
                'success': False,
                'error': 'Quiz is not in progress'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Save or update the answer
        answer, created = models.QuizAnswer.objects.update_or_create(
            submission=submission,
            question=question,
            defaults={'selected_option': selected_option}
        )
        
        return Response({
            'success': True,
            'message': 'Answer submitted successfully',
            'answer': {
                'id': answer.id,
                'question_id': question.id,
                'selected_option': answer.selected_option,
                'is_correct': answer.is_correct,
                'marks_obtained': answer.marks_obtained
            },
            'is_new': created
        })
        
    except models.QuizSubmission.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Submission not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except models.QuizQuestion.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Question not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in submit_quiz_answer: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while submitting answer'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def complete_quiz(request):
    """Complete and submit the entire quiz"""
    submission_id = request.data.get('submission_id')
    answers = request.data.get('answers', [])
    
    print(f"DEBUG - Complete quiz request data: {request.data}")
    
    if not submission_id:
        return Response({
            'success': False,
            'error': 'Submission ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        submission = models.QuizSubmission.objects.get(id=submission_id)
        
        # Check if submission is in progress
        if submission.status not in ['in_progress', 'completed']:
            return Response({
                'success': False,
                'error': 'Quiz is not in progress'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # If answers are provided in bulk, save them
        if answers and isinstance(answers, list):
            for answer_data in answers:
                question_id = answer_data.get('question_id')
                selected_option = answer_data.get('selected_option')
                
                if question_id and selected_option:
                    try:
                        question = models.QuizQuestion.objects.get(id=question_id)
                        # Check if the question belongs to the quiz
                        if question.quiz_id == submission.quiz_id:
                            models.QuizAnswer.objects.update_or_create(
                                submission=submission,
                                question=question,
                                defaults={'selected_option': int(selected_option)}
                            )
                    except (models.QuizQuestion.DoesNotExist, ValueError):
                        # Skip invalid questions
                        continue
        
        # Calculate results
        quiz_answers = models.QuizAnswer.objects.filter(submission=submission)
        
        total_questions = submission.quiz.questions.count()
        total_attempted = quiz_answers.count()
        total_correct = quiz_answers.filter(is_correct=True).count()
        total_marks_obtained = quiz_answers.aggregate(total=Sum('marks_obtained'))['total'] or 0
        
        # Calculate the ACTUAL total marks for the quiz based on all questions
        all_questions = models.QuizQuestion.objects.filter(quiz=submission.quiz)
        quiz_actual_total_marks = all_questions.aggregate(total=Sum('marks'))['total'] or 0
        
        # If quiz.total_marks doesn't match the actual sum of question marks, 
        # use the actual sum for calculation
        if quiz_actual_total_marks > 0:
            quiz_total_marks_for_calculation = quiz_actual_total_marks
        else:
            quiz_total_marks_for_calculation = submission.quiz.total_marks
        
        percentage = 0
        if quiz_total_marks_for_calculation > 0:
            percentage = (total_marks_obtained / quiz_total_marks_for_calculation) * 100
        
        # Check if passed (assuming 70% passing score)
        is_passed = percentage >= 70
        
        # Update submission
        submission.submitted_at = timezone.now()
        submission.status = 'submitted'
        submission.total_questions_attempted = total_attempted
        submission.total_correct_answers = total_correct
        submission.total_marks_obtained = total_marks_obtained
        
        # Update percentage and is_passed if not auto-calculated
        if not hasattr(submission, 'percentage') or submission.percentage is None:
            submission.percentage = percentage
        if not hasattr(submission, 'is_passed') or submission.is_passed is None:
            submission.is_passed = is_passed
            
        submission.save()
        
        # Get updated submission data
        submission.refresh_from_db()
        
        submission_serializer = QuizSubmissionSerializer(submission)
        return Response({
            'success': True,
            'message': 'Quiz submitted successfully',
            'results': {
                'total_questions': total_questions,
                'total_attempted': total_attempted,
                'total_correct': total_correct,
                'total_marks_obtained': total_marks_obtained,
                'quiz_total_marks_entered': submission.quiz.total_marks,
                'quiz_actual_total_marks': quiz_actual_total_marks,
                'quiz_total_marks_for_calculation': quiz_total_marks_for_calculation,
                'percentage': submission.percentage,
                'is_passed': submission.is_passed
            },
            'submission': submission_serializer.data
        })
        
    except models.QuizSubmission.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Submission not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in complete_quiz: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'success': False,
            'error': f'An error occurred while completing the quiz: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QuizSubmissions(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = QuizSubmissionSerializer
    
    def get_queryset(self):
        quiz_id = self.kwargs['quiz_id']
        return models.QuizSubmission.objects.filter(
            quiz_id=quiz_id
        ).select_related('student', 'quiz', 'quiz__course').order_by('-submitted_at')


class StudentQuizSubmissions(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = QuizSubmissionSerializer
    
    def get_queryset(self):
        student_id = self.kwargs['student_id']
        return models.QuizSubmission.objects.filter(
            student_id=student_id
        ).select_related('quiz', 'quiz__course').order_by('-submitted_at')


@api_view(['GET'])
@permission_classes([AllowAny])
def quiz_stats(request, quiz_id):
    """Get statistics for a quiz"""
    try:
        quiz = models.Quiz.objects.get(id=quiz_id)
        submissions = models.QuizSubmission.objects.filter(quiz=quiz, status__in=['submitted', 'graded'])
        
        total_students = quiz.course.enrolled_students.count()
        total_submissions = submissions.count()
        
        if total_submissions > 0:
            passed_count = submissions.filter(is_passed=True).count()
            avg_percentage = submissions.aggregate(avg=Avg('percentage'))['avg'] or 0
            avg_marks = submissions.aggregate(avg=Avg('total_marks_obtained'))['avg'] or 0
            
            stats = {
                'quiz_id': quiz.id,
                'quiz_title': quiz.title,
                'total_questions': quiz.total_questions,
                'total_students': total_students,
                'total_submissions': total_submissions,
                'submission_rate': (total_submissions / total_students * 100) if total_students > 0 else 0,
                'passed_count': passed_count,
                'pass_rate': (passed_count / total_submissions * 100) if total_submissions > 0 else 0,
                'average_percentage': round(avg_percentage, 2),
                'average_marks': round(avg_marks, 2),
            }
        else:
            stats = {
                'quiz_id': quiz.id,
                'quiz_title': quiz.title,
                'total_questions': quiz.total_questions,
                'total_students': total_students,
                'total_submissions': 0,
                'submission_rate': 0,
                'passed_count': 0,
                'pass_rate': 0,
                'average_percentage': 0,
                'average_marks': 0,
            }
        
        return Response({
            'success': True,
            'stats': stats
        })
        
    except models.Quiz.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Quiz not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in quiz_stats: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while fetching quiz statistics'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Simple quiz creation endpoint (alternative)
@api_view(['POST'])
@permission_classes([AllowAny])
def create_quiz_simple(request):
    teacher_id = request.data.get('teacher_id')
    course_id = request.data.get('course_id')
    title = request.data.get('title')
    description = request.data.get('description')
    total_marks = request.data.get('total_marks', 100)
    time_limit = request.data.get('time_limit', 60)
    attempt_limit = request.data.get('attempt_limit', 1)
    show_answers = request.data.get('show_answers', False)
    due_date = request.data.get('due_date')
    is_active = request.data.get('is_active', True)
    
    if not all([teacher_id, course_id, title, description]):
        return Response({
            'success': False,
            'error': 'Teacher ID, Course ID, Title, and Description are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        teacher = models.Teacher.objects.get(id=teacher_id)
        course = models.Course.objects.get(id=course_id)
        
        # Check if teacher owns the course
        if course.teacher and course.teacher.id != teacher.id:
            return Response({
                'success': False,
                'error': 'You can only create quizzes for your own courses'
            }, status=status.HTTP_403_FORBIDDEN)
        
        quiz = models.Quiz.objects.create(
            teacher=teacher,
            course=course,
            title=title,
            description=description,
            total_marks=total_marks,
            time_limit=time_limit,
            attempt_limit=attempt_limit,
            show_answers=show_answers,
            due_date=due_date,
            is_active=is_active
        )
        
        return Response({
            'success': True,
            'message': 'Quiz created successfully',
            'quiz_id': quiz.id,
            'title': quiz.title
        }, status=status.HTTP_201_CREATED)
        
    except models.Teacher.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Teacher not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except models.Course.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in create_quiz_simple: {str(e)}")
        return Response({
            'success': False,
            'error': f'Error creating quiz: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_quiz_submission_details(request, quiz_id):
    """Get detailed submission information for teachers (includes correct answers)"""
    submission_id = request.query_params.get('submission_id')
    student_id = request.query_params.get('student_id')
    
    if not submission_id or not student_id:
        return Response({
            'success': False,
            'error': 'Submission ID and Student ID are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        submission = models.QuizSubmission.objects.get(
            id=submission_id,
            quiz_id=quiz_id,
            student_id=student_id
        )
        
        # Get all questions with correct answers (teacher can see these)
        questions = models.QuizQuestion.objects.filter(quiz_id=quiz_id).order_by('id')
        
        # Get student's answers
        student_answers = models.QuizAnswer.objects.filter(
            submission=submission
        ).values_list('question_id', 'selected_option')
        
        student_answers_dict = {qid: option for qid, option in student_answers}
        
        questions_data = []
        for question in questions:
            question_data = QuizQuestionSerializer(question).data  # Use full serializer
            question_data['selected_option'] = student_answers_dict.get(question.id)
            questions_data.append(question_data)
        
        return Response({
            'success': True,
            'quiz': {
                'id': submission.quiz.id,
                'title': submission.quiz.title,
                'total_marks': submission.quiz.total_marks,
                'show_answers': submission.quiz.show_answers
            },
            'submission': QuizSubmissionSerializer(submission).data,
            'questions': questions_data
        })
        
    except models.QuizSubmission.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Submission not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in get_quiz_submission_details: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while fetching submission details'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def update_quiz_total_marks(request, quiz_id):
    """Update quiz total marks based on sum of question marks"""
    try:
        quiz = models.Quiz.objects.get(id=quiz_id)
        
        # Calculate total marks from all questions
        total_marks = models.QuizQuestion.objects.filter(quiz=quiz).aggregate(
            total=Sum('marks')
        )['total'] or 0
        
        quiz.total_marks = total_marks
        quiz.save()
        
        return Response({
            'success': True,
            'message': f'Quiz total marks updated to {total_marks}',
            'quiz_id': quiz.id,
            'total_marks': total_marks
        })
        
    except models.Quiz.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Quiz not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in update_quiz_total_marks: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while updating quiz total marks'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_courses(request):
    """
    Search courses by title, description, teacher name, category, or techs
    Supports pagination
    """
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 12))
    
    if not query:
        return Response({
            'results': [],
            'pagination': {
                'page': 1,
                'pages': 0,
                'total': 0,
                'limit': limit,
                'has_next': False,
                'has_previous': False
            }
        })
    
    try:
        # Search across multiple fields
        courses = models.Course.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(techs__icontains=query) |
            Q(teacher__full_name__icontains=query) |
            Q(category__title__icontains=query)
        ).select_related('teacher', 'category').prefetch_related('enrolled_students').distinct()
        
        # Count total results
        total = courses.count()
        
        # Calculate pagination
        total_pages = (total + limit - 1) // limit
        start = (page - 1) * limit
        end = start + limit
        
        # Get paginated results
        paginated_courses = courses[start:end]
        
        # Serialize results
        results = []
        for course in paginated_courses:
            results.append({
                'id': course.id,
                'title': course.title,
                'description': course.description,
                'thumbnail': course.featured_img.url if course.featured_img else None,
                'price': 0,
                'category': {
                    'name': course.category.title if course.category else 'Uncategorized'
                },
                'tags': course.techs,
                'instructor_name': course.teacher.full_name if course.teacher else 'Unknown',
                'instructor_username': course.teacher.email if course.teacher else '',
                'slug': course.id,
                'enrolled_count': course.enrolled_students.count()
            })
        
        return Response({
            'results': results,
            'pagination': {
                'page': page,
                'pages': total_pages,
                'total': total,
                'limit': limit,
                'has_next': page < total_pages,
                'has_previous': page > 1
            }
        })
        
    except Exception as e:
        print(f"Error in search_courses: {str(e)}")
        return Response({
            'message': 'An error occurred while searching',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_suggestions(request):
    """
    Provide search suggestions as user types
    Returns top 5 matching courses and teachers
    """
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return Response({'suggestions': []})
    
    try:
        suggestions = []
        
        # Search courses
        courses = models.Course.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(techs__icontains=query)
        )[:5]
        
        for course in courses:
            suggestions.append({
                'title': course.title,
                'type': 'Course',
                'url': f'/courses/{course.id}'
            })
        
        # Search teachers
        teachers = models.Teacher.objects.filter(
            Q(full_name__icontains=query) |
            Q(skills__icontains=query)
        )[:3]
        
        for teacher in teachers:
            suggestions.append({
                'title': teacher.full_name,
                'type': 'Teacher',
                'url': f'/teacher/{teacher.id}'
            })
        
        # Search categories
        categories = models.CourseCategory.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )[:2]
        
        for category in categories:
            suggestions.append({
                'title': category.title,
                'type': 'Category',
                'url': f'/category/{category.id}'
            })
        
        return Response({'suggestions': suggestions})
        
    except Exception as e:
        print(f"Error in search_suggestions: {str(e)}")
        return Response({
            'suggestions': [],
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CourseMaterialsList(generics.ListAPIView):
    permission_classes = [AllowAny]
    """Get all study materials for a specific course"""
    serializer_class = StudyMaterialSerializer
    
    def get_queryset(self):
        course_id = self.kwargs['course_id']
        return models.StudyMaterial.objects.filter(
            course_id=course_id
        ).select_related('course', 'teacher').order_by('-uploaded_at')


class StudyMaterialDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    """Retrieve, update or delete a study material"""
    queryset = models.StudyMaterial.objects.all()
    serializer_class = StudyMaterialSerializer
    parser_classes = (MultiPartParser, FormParser)


@api_view(['POST'])
@permission_classes([AllowAny])
def upload_material(request):
    """Upload a new study material"""
    course_id = request.data.get('course_id')
    teacher_id = request.data.get('teacher_id')
    title = request.data.get('title')
    description = request.data.get('description', '')
    file_type = request.data.get('file_type', 'pdf')
    is_public = request.data.get('is_public', 'true').lower() == 'true'
    upload_file = request.FILES.get('file')
    
    # Validation
    if not all([course_id, teacher_id, title]):
        return Response({
            'success': False,
            'error': 'Course ID, Teacher ID, and Title are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not upload_file:
        return Response({
            'success': False,
            'error': 'File is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        course = models.Course.objects.get(id=course_id)
        teacher = models.Teacher.objects.get(id=teacher_id)
        
        # Check if teacher owns the course
        if course.teacher_id != teacher.id:
            return Response({
                'success': False,
                'error': 'You can only upload materials for your own courses'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Validate file size (max 50MB)
        max_file_size = 50 * 1024 * 1024
        if upload_file.size > max_file_size:
            return Response({
                'success': False,
                'error': f'File size exceeds maximum limit of 50MB. Your file is {upload_file.size / (1024*1024):.2f}MB'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file type
        allowed_extensions = [
            'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx',
            'jpg', 'jpeg', 'png', 'gif', 'mp4', 'avi', 'mov',
            'mp3', 'wav', 'zip', 'rar', 'txt'
        ]
        
        file_extension = upload_file.name.split('.')[-1].lower()
        if file_extension not in allowed_extensions:
            return Response({
                'success': False,
                'error': f'File type .{file_extension} is not allowed. Allowed types: {", ".join(allowed_extensions)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create the study material
        material = models.StudyMaterial.objects.create(
            course=course,
            teacher=teacher,
            title=title,
            description=description,
            upload=upload_file,
            file_type=file_type,
            is_public=is_public
        )
        
        # Serialize and return
        serializer = StudyMaterialSerializer(material)
        
        return Response({
            'success': True,
            'message': 'Study material uploaded successfully',
            'material': serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except models.Course.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except models.Teacher.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Teacher not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error uploading material: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'success': False,
            'error': f'An error occurred while uploading: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_material(request, material_id):
    """Delete a study material"""
    try:
        material = models.StudyMaterial.objects.get(id=material_id)
        
        # Optional: Check if requesting teacher owns this material
        teacher_id = request.query_params.get('teacher_id') or request.data.get('teacher_id')
        if teacher_id and material.teacher_id != int(teacher_id):
            return Response({
                'success': False,
                'error': 'You can only delete your own materials'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Delete the file from storage
        if material.upload:
            material.upload.delete(save=False)
        
        # Delete the database record
        material.delete()
        
        return Response({
            'success': True,
            'message': 'Study material deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except models.StudyMaterial.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Study material not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error deleting material: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while deleting the material'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def popular_courses(request):
    """
    Get popular courses based on ratings, views, and enrollments
    Supports pagination
    """
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 8))
    
    try:
        # Get courses with their average ratings
        courses = models.Course.objects.annotate(
            avg_rating=Avg('course_ratings__rating'),
            rating_count=Count('course_ratings'),
            enrollment_count=Count('enrolled_students')
        ).filter(
            rating_count__gt=0
        ).order_by(
            '-avg_rating',
            '-views',
            '-enrollment_count'
        )
        
        # Count total results
        total = courses.count()
        
        # Calculate pagination
        total_pages = (total + limit - 1) // limit
        start = (page - 1) * limit
        end = start + limit
        
        # Get paginated results
        paginated_courses = courses[start:end]
        
        # Serialize results
        serializer = CourseSerializer(paginated_courses, many=True)
        
        return Response({
            'results': serializer.data,
            'pagination': {
                'page': page,
                'pages': total_pages,
                'total': total,
                'limit': limit,
                'has_next': page < total_pages,
                'has_previous': page > 1
            }
        })
        
    except Exception as e:
        print(f"Error in popular_courses: {str(e)}")
        return Response({
            'message': 'An error occurred while fetching popular courses',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def increment_course_views(request, course_id):
    """
    Increment view count for a course
    Call this when a user views a course detail page
    """
    try:
        course = models.Course.objects.get(id=course_id)
        course.increment_views()
        
        return Response({
            'success': True,
            'views': course.views,
            'message': 'View count updated'
        })
        
    except models.Course.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error incrementing views: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while updating view count'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def course_stats(request, course_id):
    """
    Get detailed statistics for a course including views, ratings, enrollments
    """
    try:
        course = models.Course.objects.get(id=course_id)
        
        # Get rating distribution
        ratings = models.CourseRating.objects.filter(course=course)
        rating_distribution = {
            5: ratings.filter(rating=5).count(),
            4: ratings.filter(rating=4).count(),
            3: ratings.filter(rating=3).count(),
            2: ratings.filter(rating=2).count(),
            1: ratings.filter(rating=1).count(),
        }
        
        stats = {
            'course_id': course.id,
            'course_title': course.title,
            'views': course.views,
            'total_enrollments': course.enrolled_students.count(),
            'average_rating': course.average_rating,
            'total_ratings': course.total_ratings,
            'rating_distribution': rating_distribution,
            'created_at': course.created_at
        }
        
        return Response({
            'success': True,
            'stats': stats
        })
        
    except models.Course.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error in course_stats: {str(e)}")
        return Response({
            'success': False,
            'error': 'An error occurred while fetching course statistics'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ========== MENTORSHIP VIEWS ==========

class TeacherMentorshipSessions(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    """
    Teacher can view and create mentorship sessions for their courses
    """
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateMentorshipSessionSerializer
        return MentorshipSessionSerializer
    
    def get_queryset(self):
        teacher_id = self.kwargs['teacher_id']
        return MentorshipSession.objects.filter(
            teacher_id=teacher_id,
            is_active=True
        ).order_by('-scheduled_date')
    
    def perform_create(self, serializer):
        teacher_id = self.kwargs['teacher_id']
        try:
            teacher = models.Teacher.objects.get(id=teacher_id)
            serializer.save(teacher=teacher)
        except models.Teacher.DoesNotExist:
            raise ValidationError({'error': 'Teacher not found'})


class TeacherCourseMentorshipSessions(generics.ListAPIView):
    permission_classes = [AllowAny]
    """
    Get mentorship sessions for a specific course taught by teacher
    """
    serializer_class = MentorshipSessionSerializer
    
    def get_queryset(self):
        teacher_id = self.kwargs['teacher_id']
        course_id = self.kwargs['course_id']
        
        return MentorshipSession.objects.filter(
            teacher_id=teacher_id,
            course_id=course_id,
            is_active=True
        ).order_by('-scheduled_date')


class UpdateMentorshipSession(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    """
    Teacher can update or delete their mentorship sessions
    """
    serializer_class = MentorshipSessionSerializer
    
    def get_queryset(self):
        return MentorshipSession.objects.all()


class StudentAvailableMentorshipSessions(APIView):
    permission_classes = [AllowAny]
    """
    Get all mentorship sessions available to a student
    (Sessions from courses they're enrolled in)
    """
    
    def get(self, request, user_id):
        # Get all courses the student is enrolled in
        enrolled_courses = UserCourseEnrollment.objects.filter(
            user_id=user_id
        ).values_list('course_id', flat=True)
        
        # Get sessions from those courses
        sessions = MentorshipSession.objects.filter(
            course_id__in=enrolled_courses,
            is_active=True
        ).order_by('-scheduled_date')
        
        # Filter based on query parameters
        status_filter = request.query_params.get('status', None)
        if status_filter:
            sessions = sessions.filter(status=status_filter)
        
        upcoming_only = request.query_params.get('upcoming', None)
        if upcoming_only:
            sessions = sessions.filter(
                scheduled_date__gt=timezone.now(),
                status='scheduled'
            )
        
        live_only = request.query_params.get('live', None)
        if live_only:
            now = timezone.now()
            sessions = sessions.filter(
                scheduled_date__lte=now,
                scheduled_date__gte=now - timezone.timedelta(minutes=120),
                status__in=['scheduled', 'live']
            )
        
        serializer = MentorshipSessionSerializer(
            sessions, 
            many=True
        )
        return Response(serializer.data)


class CourseMentorshipSessionsForStudent(generics.ListAPIView):
    permission_classes = [AllowAny]
    """
    Get mentorship sessions for a specific course (student must be enrolled)
    """
    serializer_class = MentorshipSessionSerializer
    
    def get_queryset(self):
        user_id = self.kwargs['user_id']
        course_id = self.kwargs['course_id']
        
        # Check if student is enrolled in this course
        if not UserCourseEnrollment.objects.filter(
            user_id=user_id,
            course_id=course_id
        ).exists():
            return MentorshipSession.objects.none()
        
        return MentorshipSession.objects.filter(
            course_id=course_id,
            is_active=True
        ).order_by('-scheduled_date')
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        
        # Add course info
        from .models import Course
        course = Course.objects.get(id=self.kwargs['course_id'])
        response.data = {
            'course': {
                'id': course.id,
                'title': course.title,
                'teacher': course.teacher.full_name
            },
            'sessions': response.data
        }
        return response


class RegisterForMentorshipSession(APIView):
    permission_classes = [AllowAny]
    """
    Student registers for a mentorship session
    """
    
    def post(self, request):
        user_id = request.data.get('user_id')
        session_id = request.data.get('session_id')
        
        if not user_id or not session_id:
            return Response(
                {'error': 'User ID and Session ID are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = models.User.objects.get(id=user_id)
            session = MentorshipSession.objects.get(id=session_id, is_active=True)
            
            # Check if student is enrolled in the course
            if not UserCourseEnrollment.objects.filter(
                user=user,
                course=session.course
            ).exists():
                return Response(
                    {'error': 'You must be enrolled in this course to register for mentorship sessions'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if session is full
            if session.is_full:
                return Response(
                    {'error': 'This session is already full'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if already registered
            if MentorshipRegistration.objects.filter(user=user, session=session).exists():
                return Response(
                    {'error': 'You are already registered for this session'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create registration
            registration = MentorshipRegistration.objects.create(
                user=user,
                session=session
            )
            
            serializer = MentorshipRegistrationSerializer(registration)
            return Response({
                'message': 'Successfully registered for the mentorship session',
                'registration': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except models.User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except MentorshipSession.DoesNotExist:
            return Response(
                {'error': 'Mentorship session not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UserMentorshipRegistrations(generics.ListAPIView):
    permission_classes = [AllowAny]
    """
    Get all mentorship sessions a user has registered for
    """
    serializer_class = MentorshipRegistrationSerializer
    
    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return MentorshipRegistration.objects.filter(
            user_id=user_id
        ).order_by('-registered_at')


class MentorshipDashboard(APIView):
    permission_classes = [AllowAny]
    """
    Dashboard view showing upcoming and live sessions for a user
    """
    
    def get(self, request, user_id):
        try:
            user = models.User.objects.get(id=user_id)
        except models.User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get enrolled courses
        enrolled_courses = UserCourseEnrollment.objects.filter(
            user=user
        ).values_list('course_id', flat=True)
        
        now = timezone.now()
        
        # Live sessions (happening now)
        live_sessions = MentorshipSession.objects.filter(
            course_id__in=enrolled_courses,
            is_active=True,
            scheduled_date__lte=now,
            scheduled_date__gte=now - timezone.timedelta(minutes=120),
            status__in=['scheduled', 'live']
        ).order_by('scheduled_date')
        
        # Upcoming sessions (next 7 days)
        upcoming_sessions = MentorshipSession.objects.filter(
            course_id__in=enrolled_courses,
            is_active=True,
            scheduled_date__gt=now,
            scheduled_date__lte=now + timezone.timedelta(days=7),
            status='scheduled'
        ).order_by('scheduled_date')
        
        # Recent completed sessions (last 30 days)
        recent_sessions = MentorshipSession.objects.filter(
            course_id__in=enrolled_courses,
            is_active=True,
            status='completed',
            scheduled_date__gte=now - timezone.timedelta(days=30)
        ).order_by('-scheduled_date')[:10]
        
        live_serializer = MentorshipSessionSerializer(live_sessions, many=True)
        upcoming_serializer = MentorshipSessionSerializer(upcoming_sessions, many=True)
        recent_serializer = MentorshipSessionSerializer(recent_sessions, many=True)
        
        return Response({
            'live_sessions': live_serializer.data,
            'upcoming_sessions': upcoming_serializer.data,
            'recent_sessions': recent_serializer.data,
            'stats': {
                'total_live': live_sessions.count(),
                'total_upcoming': upcoming_sessions.count(),
                'total_recent': recent_sessions.count()
            }
        })


class SimpleCreateMentorshipSession(APIView):
    permission_classes = [AllowAny]
    """
    Simple endpoint for teachers to create mentorship sessions
    Just provide link, title, course, and datetime
    """
    
    def post(self, request):
        data = request.data
        
        # Get teacher from request data
        teacher_id = data.get('teacher_id')
        if not teacher_id:
            return Response(
                {'error': 'Teacher ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            teacher = models.Teacher.objects.get(id=teacher_id)
        except models.Teacher.DoesNotExist:
            return Response(
                {'error': 'Teacher not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate teacher teaches the course
        course_id = data.get('course_id')
        try:
            course = models.Course.objects.get(id=course_id, teacher=teacher)
        except models.Course.DoesNotExist:
            return Response(
                {'error': 'You can only create sessions for your own courses'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate and parse scheduled_date
        scheduled_date_str = data.get('scheduled_date')
        if not scheduled_date_str:
            return Response(
                {'error': 'Scheduled date is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse the datetime string
        scheduled_date = parse_datetime(scheduled_date_str)
        if not scheduled_date:
            # Try alternative format parsing
            try:
                from datetime import datetime
                scheduled_date = datetime.fromisoformat(scheduled_date_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return Response(
                    {'error': 'Invalid date format. Use ISO format: YYYY-MM-DDTHH:MM:SS'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Make sure the date is timezone aware
        if timezone.is_naive(scheduled_date):
            scheduled_date = timezone.make_aware(scheduled_date)
        
        # Create session with proper datetime object
        session = MentorshipSession.objects.create(
            title=data.get('title', f'Mentorship Session - {course.title}'),
            description=data.get('description', ''),
            session_link=data['link'],
            session_type=data.get('session_type', 'live_qna'),
            teacher=teacher,
            course=course,
            scheduled_date=scheduled_date,
            duration_minutes=data.get('duration_minutes', 60),
            max_participants=data.get('max_participants'),
            is_active=True
        )
        
        serializer = MentorshipSessionSerializer(session)
        return Response({
            'message': 'Mentorship session created successfully',
            'session': serializer.data,
            'enrolled_students_count': course.enrolled_students.count()
        }, status=status.HTTP_201_CREATED)


class UpdateSessionStatus(APIView):
    permission_classes = [AllowAny]
    """
    Update mentorship session status
    """
    
    def post(self, request, session_id):
        try:
            session = MentorshipSession.objects.get(id=session_id)
            status = request.data.get('status')
            
            if status in ['scheduled', 'live', 'completed', 'cancelled']:
                session.status = status
                session.save()
                return Response({
                    'status': 'success', 
                    'message': f'Session marked as {status}'
                })
            else:
                return Response({
                    'error': 'Invalid status'
                }, status=400)
                
        except MentorshipSession.DoesNotExist:
            return Response({
                'error': 'Session not found'
            }, status=404)
        except Exception as e:
            print(f"Error updating session status: {str(e)}")
            return Response({
                'error': 'An error occurred while updating session status'
            }, status=500)
        
# ==================== ADMIN AUTHENTICATION ====================

@api_view(['POST'])
@permission_classes([AllowAny])
def admin_login(request):
    """Admin login endpoint"""
    identifier = request.data.get('email') or request.data.get('username')
    password = request.data.get('password')
    
    if not identifier or not password:
        return Response({
            'success': False, 
            'error': 'Email/username and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Find admin by email or username
        admin = models.Admin.objects.get(
            Q(email=identifier) | Q(username=identifier)
        )
        
        if not admin.is_active:
            return Response({
                'success': False,
                'error': 'Admin account is deactivated'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if check_password(password, admin.password):
            # Update last login
            admin.update_last_login()
            
            # Create or get Django User for token
            django_user, created = DjangoUser.objects.get_or_create(
                email=admin.email,
                defaults={
                    'username': admin.username,
                    'password': make_password(password),
                    'is_staff': True,
                    'is_superuser': admin.is_super_admin
                }
            )
            
            # Create or get token
            token, created = Token.objects.get_or_create(user=django_user)
            
            return Response({
                'success': True,
                'admin_id': admin.id,
                'full_name': admin.full_name,
                'email': admin.email,
                'username': admin.username,
                'role': admin.role,
                'is_super_admin': admin.is_super_admin,
                'token': token.key
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
    except models.Admin.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return Response({
            'success': False, 
            'error': 'An error occurred during login'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== ADMIN CRUD ====================

@api_view(['POST'])
@permission_classes([AllowAny])
def admin_register(request):
    """Admin registration endpoint"""
    email = request.data.get('email')
    username = request.data.get('username')
    password = request.data.get('password')
    full_name = request.data.get('full_name')
    
    # Validation
    if not email or not username or not password:
        return Response({
            'success': False, 
            'error': 'Email, username, and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if admin with email already exists
    if models.Admin.objects.filter(email=email).exists():
        return Response({
            'success': False,
            'error': 'Admin with this email already exists'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if admin with username already exists
    if models.Admin.objects.filter(username=username).exists():
        return Response({
            'success': False,
            'error': 'Admin with this username already exists'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Create admin
        admin = models.Admin.objects.create(
            email=email,
            username=username,
            password=make_password(password),
            full_name=full_name or username,
            is_active=True
        )
        
        return Response({
            'success': True,
            'admin_id': admin.id,
            'username': admin.username,
            'email': admin.email,
            'full_name': admin.full_name,
            'message': 'Admin registered successfully'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'An error occurred during registration: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminList(generics.ListCreateAPIView):
    """List all admins or create a new admin"""
    queryset = models.Admin.objects.all()
    serializer_class = AdminSerializer
    permission_classes = [AllowAny]
    
    def perform_create(self, serializer):
        password = serializer.validated_data.get('password')
        serializer.save(password=make_password(password))


class AdminDetail(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete an admin"""
    queryset = models.Admin.objects.all()
    serializer_class = AdminSerializer
    permission_classes = [AllowAny]
    
    def perform_update(self, serializer):
        if 'password' in serializer.validated_data:
            password = serializer.validated_data.pop('password')
            admin = serializer.save()
            admin.password = make_password(password)
            admin.save()
        else:
            serializer.save()


# ==================== ADMIN DASHBOARD ====================

class AdminDashboard(APIView):
    """
    Comprehensive admin dashboard with all statistics
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Date ranges
        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        last_7_days = now - timedelta(days=7)
        
        # Basic counts
        total_users = models.User.objects.count()
        total_teachers = models.Teacher.objects.count()
        total_courses = models.Course.objects.count()
        total_enrollments = models.UserCourseEnrollment.objects.count()
        total_categories = models.CourseCategory.objects.count()
        total_quizzes = models.Quiz.objects.count()
        total_assignments = models.Assignment.objects.count()
        
        # User statistics
        active_users = models.User.objects.filter(status='active').count()
        inactive_users = models.User.objects.filter(status='inactive').count()
        
        # Recent enrollments (last 7 days)
        recent_enrollments = models.UserCourseEnrollment.objects.filter(
            enrolled_date__gte=last_7_days
        ).count()
        
        # Popular courses (top 5 by enrollments)
        popular_courses = models.Course.objects.annotate(
            enrollment_count=Count('enrolled_students')
        ).order_by('-enrollment_count')[:5]
        
        popular_courses_data = [{
            'id': course.id,
            'title': course.title,
            'teacher': course.teacher.full_name if course.teacher else 'N/A',
            'enrollments': course.enrollment_count,
            'views': course.views
        } for course in popular_courses]
        
        # Recent users (last 10)
        recent_users = models.User.objects.order_by('-id')[:10]
        recent_users_data = [{
            'id': user.id,
            'full_name': user.full_name,
            'email': user.email,
            'status': user.status
        } for user in recent_users]
        
        # Recent teachers (last 10)
        recent_teachers = models.Teacher.objects.order_by('-id')[:10]
        recent_teachers_data = [{
            'id': teacher.id,
            'full_name': teacher.full_name,
            'email': teacher.email,
            'qualification': teacher.qualification
        } for teacher in recent_teachers]
        
        # Recent courses (last 10)
        recent_courses = models.Course.objects.select_related('teacher').order_by('-id')[:10]
        recent_courses_data = [{
            'id': course.id,
            'title': course.title,
            'teacher': {
                'id': course.teacher.id if course.teacher else None,
                'full_name': course.teacher.full_name if course.teacher else 'N/A'
            },
            'enrolled_students': course.enrolled_students.count(),
            'created_at': course.created_at.isoformat() if hasattr(course, 'created_at') and course.created_at else None
        } for course in recent_courses]
        
        # Course statistics
        courses_by_category = models.Course.objects.values(
            'category__title'
        ).annotate(count=Count('id')).order_by('-count')
        
        # Enrollment trends (last 30 days)
        enrollment_trend = []
        for i in range(30, -1, -1):
            date = (now - timedelta(days=i)).date()
            count = models.UserCourseEnrollment.objects.filter(
                enrolled_date__date=date
            ).count()
            enrollment_trend.append({
                'date': str(date),
                'count': count
            })
        
        # Revenue/Rating statistics
        top_rated_courses = models.Course.objects.annotate(
            avg_rating=Avg('course_ratings__rating'),
            rating_count=Count('course_ratings')
        ).filter(rating_count__gt=0).order_by('-avg_rating')[:5]
        
        top_rated_data = [{
            'id': course.id,
            'title': course.title,
            'average_rating': round(course.avg_rating, 2),
            'total_ratings': course.rating_count
        } for course in top_rated_courses]
        
        return Response({
            'overview': {
                'total_users': total_users,
                'total_teachers': total_teachers,
                'total_courses': total_courses,
                'total_enrollments': total_enrollments,
                'total_categories': total_categories,
                'total_quizzes': total_quizzes,
                'total_assignments': total_assignments,
            },
            'user_stats': {
                'active_users': active_users,
                'inactive_users': inactive_users,
                'recent_enrollments': recent_enrollments,
            },
            'popular_courses': popular_courses_data,
            'top_rated_courses': top_rated_data,
            'recent_users': recent_users_data,
            'recent_teachers': recent_teachers_data,
            'recent_courses': recent_courses_data,
            'courses_by_category': list(courses_by_category),
            'enrollment_trend': enrollment_trend,
        })


# ==================== ADMIN USER MANAGEMENT ====================

class AdminUsersList(generics.ListAPIView):
    """List all users with filtering and search"""
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = models.User.objects.all().order_by('-id')
        
        # Filter by status
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
        
        # Search by name or email
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) | 
                Q(email__icontains=search) |
                Q(username__icontains=search)
            )
        
        return queryset


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_toggle_user_status(request, user_id):
    """Activate or deactivate a user"""
    try:
        user = models.User.objects.get(id=user_id)
        new_status = 'active' if user.status == 'inactive' else 'inactive'
        user.status = new_status
        user.save()
        
        return Response({
            'success': True,
            'message': f'User status changed to {new_status}',
            'user_id': user.id,
            'new_status': new_status
        })
    except models.User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def admin_delete_user(request, user_id):
    """Delete a user"""
    try:
        user = models.User.objects.get(id=user_id)
        user.delete()
        
        return Response({
            'success': True,
            'message': 'User deleted successfully'
        })
    except models.User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)


# ==================== ADMIN TEACHER MANAGEMENT ====================

class AdminTeachersList(generics.ListAPIView):
    """List all teachers with filtering and search"""
    serializer_class = TeacherSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = models.Teacher.objects.all().order_by('-id')
        
        # Search by name, email, or qualification
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) | 
                Q(email__icontains=search) |
                Q(qualification__icontains=search)
            )
        
        return queryset


@api_view(['DELETE'])
@permission_classes([AllowAny])
def admin_delete_teacher(request, teacher_id):
    """Delete a teacher"""
    try:
        teacher = models.Teacher.objects.get(id=teacher_id)
        teacher.delete()
        
        return Response({
            'success': True,
            'message': 'Teacher deleted successfully'
        })
    except models.Teacher.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Teacher not found'
        }, status=status.HTTP_404_NOT_FOUND)


# ==================== ADMIN COURSE MANAGEMENT ====================

class AdminCoursesList(generics.ListAPIView):
    """List all courses with filtering and search"""
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = models.Course.objects.all().order_by('-created_at')
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Filter by teacher
        teacher = self.request.query_params.get('teacher', None)
        if teacher:
            queryset = queryset.filter(teacher_id=teacher)
        
        # Search by title or description
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search)
            )
        
        return queryset


@api_view(['DELETE'])
@permission_classes([AllowAny])
def admin_delete_course(request, course_id):
    """Delete a course"""
    try:
        course = models.Course.objects.get(id=course_id)
        course.delete()
        
        return Response({
            'success': True,
            'message': 'Course deleted successfully'
        })
    except models.Course.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_approve_course(request, course_id):
    """Approve/feature a course (you can add approval status to Course model)"""
    try:
        course = models.Course.objects.get(id=course_id)
        # Add your approval logic here
        # For example: course.is_approved = True
        # course.save()
        
        return Response({
            'success': True,
            'message': 'Course approved successfully',
            'course_id': course.id
        })
    except models.Course.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)


# ==================== ADMIN ANALYTICS ====================

class AdminAnalytics(APIView):
    """Advanced analytics for admin"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Get date range from query params
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # User growth
        user_growth = models.User.objects.filter(
            id__gte=1  # Assuming ID is sequential
        ).count()
        
        # Course performance
        course_performance = models.Course.objects.annotate(
            enrollment_count=Count('enrolled_students'),
            avg_rating=Avg('course_ratings__rating'),
            total_views=Sum('views')
        ).order_by('-enrollment_count')[:10]
        
        performance_data = [{
            'course_id': c.id,
            'title': c.title,
            'enrollments': c.enrollment_count,
            'avg_rating': round(c.avg_rating, 2) if c.avg_rating else 0,
            'views': c.total_views or 0
        } for c in course_performance]
        
        # Teacher performance
        teacher_performance = models.Teacher.objects.annotate(
            course_count=Count('teacher_courses'),
            total_students=Count('teacher_courses__enrolled_students', distinct=True)
        ).order_by('-total_students')[:10]
        
        teacher_data = [{
            'teacher_id': t.id,
            'name': t.full_name,
            'courses': t.course_count,
            'students': t.total_students
        } for t in teacher_performance]
        
        # Category distribution
        category_stats = models.CourseCategory.objects.annotate(
            course_count=Count('course'),
            enrollment_count=Count('course__enrolled_students')
        ).order_by('-course_count')
        
        category_data = [{
            'category': c.title,
            'courses': c.course_count,
            'enrollments': c.enrollment_count
        } for c in category_stats]
        
        return Response({
            'course_performance': performance_data,
            'teacher_performance': teacher_data,
            'category_distribution': category_data,
            'total_revenue': 0,  # Add your revenue calculation
            'user_growth': user_growth
        })


# ==================== ADMIN REPORTS ====================

@api_view(['GET'])
@permission_classes([AllowAny])
def admin_generate_report(request):
    """Generate comprehensive system report"""
    report_type = request.query_params.get('type', 'overview')
    
    if report_type == 'enrollments':
        # Enrollment report
        enrollments = models.UserCourseEnrollment.objects.select_related(
            'user', 'course', 'course__teacher'
        ).order_by('-enrolled_date')[:100]
        
        data = [{
            'id': e.id,
            'student': e.user.full_name,
            'course': e.course.title,
            'teacher': e.course.teacher.full_name if e.course.teacher else 'N/A',
            'date': e.enrolled_date.strftime('%Y-%m-%d %H:%M:%S')
        } for e in enrollments]
        
        return Response({
            'report_type': 'enrollments',
            'total_records': len(data),
            'data': data
        })
    
    elif report_type == 'ratings':
        # Ratings report
        ratings = models.CourseRating.objects.select_related(
            'user', 'course'
        ).order_by('-id')[:100]
        
        data = [{
            'id': r.id,
            'student': r.user.full_name,
            'course': r.course.title,
            'rating': r.rating,
            'comment': r.comment
        } for r in ratings]
        
        return Response({
            'report_type': 'ratings',
            'total_records': len(data),
            'data': data
        })
    
    else:
        # Overview report
        return Response({
            'report_type': 'overview',
            'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'total_users': models.User.objects.count(),
                'total_teachers': models.Teacher.objects.count(),
                'total_courses': models.Course.objects.count(),
                'total_enrollments': models.UserCourseEnrollment.objects.count(),
                'total_ratings': models.CourseRating.objects.count(),
            }
        })


# ==================== ADMIN CATEGORY MANAGEMENT ====================

@api_view(['POST'])
@permission_classes([AllowAny])
def admin_create_category(request):
    """Create a new category"""
    serializer = CategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'success': True,
            'message': 'Category created successfully',
            'category': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([AllowAny])
def admin_update_category(request, category_id):
    """Update a category"""
    try:
        category = models.CourseCategory.objects.get(id=category_id)
        serializer = CategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Category updated successfully',
                'category': serializer.data
            })
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    except models.CourseCategory.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Category not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def admin_delete_category(request, category_id):
    """Delete a category"""
    try:
        category = models.CourseCategory.objects.get(id=category_id)
        category.delete()
        return Response({
            'success': True,
            'message': 'Category deleted successfully'
        })
    except models.CourseCategory.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Category not found'
        }, status=status.HTTP_404_NOT_FOUND)
    

# Add these views to your views.py file

# ==================== FORUM VIEWS ====================
class CourseForumView(generics.RetrieveAPIView):
    """
    Get forum details for a course
    """
    permission_classes = [AllowAny]
    serializer_class = CourseForumSerializer
    
    def get_object(self):
        course_id = self.kwargs['course_id']
        forum, created = models.CourseForum.objects.get_or_create(
            course_id=course_id,
            defaults={
                'name': f"Course Discussion Group",
                'description': "Discussion forum for this course."
            }
        )
        return forum


class ForumMessagesView(generics.ListCreateAPIView):
    """
    List all messages in a forum or create a new message
    """
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ForumMessageCreateSerializer
        return ForumMessageSerializer
    
    def get_queryset(self):
        forum_id = self.kwargs['forum_id']
        return models.ForumMessage.objects.filter(
            forum_id=forum_id,
            parent__isnull=True,
            is_deleted=False
        ).select_related(
            'sender_user', 'sender_teacher', 'forum'
        ).prefetch_related(
            'reactions', 'replies'
        ).order_by('-is_pinned', 'timestamp')
    
    def perform_create(self, serializer):
        print(f"📨 Creating message with data: {self.request.data}")
        serializer.save()


class ForumMessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a specific message
    """
    permission_classes = [AllowAny]
    queryset = models.ForumMessage.objects.all()
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ForumMessageCreateSerializer
        return ForumMessageSerializer
    
    def perform_update(self, serializer):
        instance = self.get_object()
        serializer.save(
            is_edited=True,
            edited_at=timezone.now()
        )
    
    def perform_destroy(self, instance):
        # Soft delete
        instance.soft_delete()
        return Response({"message": "Message deleted successfully"})


class ForumReactionView(APIView):
    """
    Add or remove reaction to a message
    """
    permission_classes = [AllowAny]
    
    def post(self, request, message_id):
        try:
            message = models.ForumMessage.objects.get(id=message_id)
        except models.ForumMessage.DoesNotExist:
            return Response(
                {'error': 'Message not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        reaction = request.data.get('reaction', '👍')
        user_id = request.data.get('user_id')
        teacher_id = request.data.get('teacher_id')
        
        print(f"👍 Reaction request - message_id: {message_id}, reaction: {reaction}, user_id: {user_id}, teacher_id: {teacher_id}")
        
        # Handle reaction based on who is reacting
        if user_id:
            try:
                user = models.User.objects.get(id=user_id)
                
                # Check if user is a member of the forum
                if not models.ForumMember.objects.filter(
                    forum=message.forum,
                    user=user
                ).exists():
                    return Response(
                        {'error': 'You are not a member of this forum'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Toggle reaction
                existing_reaction = models.MessageReaction.objects.filter(
                    message=message,
                    user=user,
                    reaction=reaction
                ).first()
                
                if existing_reaction:
                    existing_reaction.delete()
                    return Response({
                        'success': True,
                        'action': 'removed',
                        'message': 'Reaction removed'
                    })
                else:
                    # Remove any existing reaction from this user
                    models.MessageReaction.objects.filter(
                        message=message,
                        user=user
                    ).delete()
                    
                    # Add new reaction
                    new_reaction = models.MessageReaction.objects.create(
                        message=message,
                        user=user,
                        reaction=reaction
                    )
                    
                    return Response({
                        'success': True,
                        'action': 'added',
                        'reaction': {
                            'id': new_reaction.id,
                            'reaction': new_reaction.reaction,
                            'user_name': user.full_name
                        }
                    })
                    
            except models.User.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        elif teacher_id:
            try:
                teacher = models.Teacher.objects.get(id=teacher_id)
                
                # Check if teacher is a member of the forum
                if not models.ForumMember.objects.filter(
                    forum=message.forum,
                    teacher=teacher
                ).exists():
                    # Auto-add teacher if they're the course teacher
                    if message.forum.course.teacher and message.forum.course.teacher.id == teacher.id:
                        member = models.ForumMember.objects.create(
                            forum=message.forum,
                            teacher=teacher,
                            role='teacher',
                            is_admin=True
                        )
                        print(f"✅ Auto-added teacher {teacher.full_name} to forum")
                    else:
                        return Response(
                            {'error': 'You are not a member of this forum'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                
                # Toggle reaction
                existing_reaction = models.MessageReaction.objects.filter(
                    message=message,
                    teacher=teacher,
                    reaction=reaction
                ).first()
                
                if existing_reaction:
                    existing_reaction.delete()
                    return Response({
                        'success': True,
                        'action': 'removed',
                        'message': 'Reaction removed'
                    })
                else:
                    # Remove any existing reaction from this teacher
                    models.MessageReaction.objects.filter(
                        message=message,
                        teacher=teacher
                    ).delete()
                    
                    # Add new reaction
                    new_reaction = models.MessageReaction.objects.create(
                        message=message,
                        teacher=teacher,
                        reaction=reaction
                    )
                    
                    return Response({
                        'success': True,
                        'action': 'added',
                        'reaction': {
                            'id': new_reaction.id,
                            'reaction': new_reaction.reaction,
                            'teacher_name': teacher.full_name
                        }
                    })
                    
            except models.Teacher.DoesNotExist:
                return Response(
                    {'error': 'Teacher not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(
            {'error': 'Either user_id or teacher_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )


class ForumMembersView(generics.ListAPIView):
    """
    List all members of a forum
    """
    permission_classes = [AllowAny]
    serializer_class = ForumMemberSerializer
    
    def get_queryset(self):
        forum_id = self.kwargs['forum_id']
        return models.ForumMember.objects.filter(
            forum_id=forum_id
        ).select_related('user', 'teacher').order_by('-is_admin', 'role', 'joined_at')


class UserForumsView(generics.ListAPIView):
    """
    Get all forums a user is a member of
    """
    permission_classes = [AllowAny]
    serializer_class = CourseForumSerializer
    
    def get_queryset(self):
        from django.db.models import Max
        
        user_id = self.kwargs['user_id']
        return models.CourseForum.objects.filter(
            members__user_id=user_id,
            is_active=True
        ).select_related('course', 'course__teacher').annotate(
            last_message_time=Max('messages__timestamp')
        ).order_by('-last_message_time')


class ForumUnreadCountView(APIView):
    """
    Get unread message count for a user across all forums
    """
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        # Get all forums user is a member of
        forums = models.CourseForum.objects.filter(
            members__user_id=user_id,
            is_active=True
        )
        
        total_unread = 0
        forum_unread_counts = []
        
        for forum in forums:
            # Get last read timestamp for user in this forum
            try:
                member = models.ForumMember.objects.get(
                    forum=forum,
                    user_id=user_id
                )
                last_seen = member.last_seen_at or member.joined_at
            except:
                last_seen = timezone.now() - timezone.timedelta(days=365)
            
            # Count messages after last_seen that user hasn't read
            unread_count = models.ForumMessage.objects.filter(
                forum=forum,
                timestamp__gt=last_seen,
                is_deleted=False
            ).exclude(
                read_receipts__user_id=user_id
            ).count()
            
            total_unread += unread_count
            forum_unread_counts.append({
                'forum_id': forum.id,
                'course_title': forum.course.title,
                'unread_count': unread_count
            })
        
        return Response({
            'total_unread': total_unread,
            'forums': forum_unread_counts
        })


class ForumNotificationsView(generics.ListAPIView):
    """
    Get notifications for a user
    """
    permission_classes = [AllowAny]
    serializer_class = ForumNotificationSerializer
    
    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return models.ForumNotification.objects.filter(
            recipient_id=user_id
        ).select_related('message', 'message__sender_user', 'message__sender_teacher', 'message__forum', 'message__forum__course'
        ).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        
        # Add unread count
        user_id = self.kwargs['user_id']
        unread_count = models.ForumNotification.objects.filter(
            recipient_id=user_id,
            is_read=False
        ).count()
        
        response.data = {
            'notifications': response.data,
            'unread_count': unread_count
        }
        
        return response


@api_view(['POST'])
@permission_classes([AllowAny])
def mark_notifications_read(request, user_id):
    """
    Mark all notifications as read for a user
    """
    models.ForumNotification.objects.filter(
        recipient_id=user_id,
        is_read=False
    ).update(is_read=True)
    
    return Response({
        'success': True,
        'message': 'All notifications marked as read'
    })


class ForumSearchView(generics.ListAPIView):
    """
    Search messages within a forum
    """
    permission_classes = [AllowAny]
    serializer_class = ForumMessageSerializer
    
    def get_queryset(self):
        forum_id = self.kwargs['forum_id']
        query = self.request.query_params.get('q', '')
        
        if not query:
            return models.ForumMessage.objects.none()
        
        return models.ForumMessage.objects.filter(
            forum_id=forum_id,
            content__icontains=query,
            is_deleted=False,
            parent__isnull=True
        ).select_related('sender_user', 'sender_teacher').order_by('-timestamp')


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    """
    Step 1: User submits their email.
    We check if it exists (for User or Teacher), then send a reset link.
    
    POST body: { "email": "user@example.com", "user_type": "user" }
    user_type is optional - if omitted, we check both User and Teacher tables.
    """
    email = request.data.get('email', '').strip().lower()
    user_type_hint = request.data.get('user_type', None)  # 'user' or 'teacher' (optional)

    if not email:
        return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

    found_type = None

    # Check based on hint or search both tables
    if user_type_hint == 'teacher':
        if Teacher.objects.filter(email__iexact=email).exists():
            found_type = 'teacher'
    elif user_type_hint == 'user':
        if User.objects.filter(email__iexact=email).exists():
            found_type = 'user'
    else:
        # No hint: check User first, then Teacher
        if User.objects.filter(email__iexact=email).exists():
            found_type = 'user'
        elif Teacher.objects.filter(email__iexact=email).exists():
            found_type = 'teacher'

    if not found_type:
        # Return generic message to avoid email enumeration
        return Response({
            'message': 'If this email exists in our system, a password reset link has been sent.'
        }, status=status.HTTP_200_OK)

    # Invalidate any old unused tokens for this email
    PasswordResetToken.objects.filter(email__iexact=email, is_used=False).update(is_used=True)

    # Create a new token
    reset_token = PasswordResetToken.objects.create(
        email=email.lower(),
        user_type=found_type
    )

    # Build the reset link — route based on user_type
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    if found_type == 'teacher':
        reset_link = f"{frontend_url}/teacher/reset-password?token={reset_token.token}"
    else:
        reset_link = f"{frontend_url}/user/reset-password?token={reset_token.token}"

    # Send email
    try:
        send_mail(
            subject='Password Reset Request',
            message=f"""
Hello,

You requested a password reset for your account.

Click the link below to set a new password:
{reset_link}

This link will expire in 1 hour.

If you did not request this, please ignore this email.

Best regards,
The Support Team
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        return Response(
            {'error': 'Failed to send email. Please try again later.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response({
        'message': 'If this email exists in our system, a password reset link has been sent.'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    Step 2: User submits their new password along with the token from the email link.
    
    POST body: {
        "token": "uuid-token-from-email",
        "new_password": "newSecurePassword123",
        "confirm_password": "newSecurePassword123"
    }
    """
    token_str = request.data.get('token', '').strip()
    new_password = request.data.get('new_password', '').strip()
    confirm_password = request.data.get('confirm_password', '').strip()

    # Validate inputs
    if not token_str:
        return Response({'error': 'Reset token is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not new_password or not confirm_password:
        return Response({'error': 'Both password fields are required.'}, status=status.HTTP_400_BAD_REQUEST)
    if new_password != confirm_password:
        return Response({'error': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(new_password) < 6:
        return Response({'error': 'Password must be at least 6 characters long.'}, status=status.HTTP_400_BAD_REQUEST)

    # Look up the token
    try:
        reset_token = PasswordResetToken.objects.get(token=token_str, is_used=False)
    except PasswordResetToken.DoesNotExist:
        return Response({'error': 'Invalid or already used reset link.'}, status=status.HTTP_400_BAD_REQUEST)

    # Check expiry
    if reset_token.is_expired():
        return Response({'error': 'This reset link has expired. Please request a new one.'}, status=status.HTTP_400_BAD_REQUEST)

    # Update the password on the correct model
    try:
        if reset_token.user_type == 'user':
            account = User.objects.get(email__iexact=reset_token.email)
        else:
            account = Teacher.objects.get(email__iexact=reset_token.email)
    except (User.DoesNotExist, Teacher.DoesNotExist):
        return Response({'error': 'Account not found.'}, status=status.HTTP_404_NOT_FOUND)

    account.password = make_password(new_password)
    account.save(update_fields=['password'])

    # Mark token as used
    reset_token.is_used = True
    reset_token.save(update_fields=['is_used'])

    return Response({'message': 'Password reset successfully. You can now log in.'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_reset_token(request):
    """
    Optional: Validate a token before showing the reset password form on the frontend.
    
    GET ?token=uuid-token
    """
    token_str = request.query_params.get('token', '').strip()
    if not token_str:
        return Response({'valid': False, 'error': 'Token is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        reset_token = PasswordResetToken.objects.get(token=token_str, is_used=False)
        if reset_token.is_expired():
            return Response({'valid': False, 'error': 'Token has expired.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'valid': True, 'user_type': reset_token.user_type}, status=status.HTTP_200_OK)
    except PasswordResetToken.DoesNotExist:
        return Response({'valid': False, 'error': 'Invalid or used token.'}, status=status.HTTP_400_BAD_REQUEST)


GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '282926972818-i1b3ea1dfnfg00a3l6dc9actg448lpl2.apps.googleusercontent.com')

@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):
    """
    Handles Google Login & Register.
    Frontend sends: { credential: '<google_id_token>' }
    """
    credential = request.data.get('credential')

    if not credential:
        return Response({'bool': False, 'error': 'Google credential is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        return Response({'bool': False, 'error': 'Invalid Google token', 'detail': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

    email = idinfo.get('email')
    full_name = idinfo.get('name', '')
    profile_picture = idinfo.get('picture', '')

    if not email:
        return Response({'bool': False, 'error': 'Could not retrieve email from Google'}, status=status.HTTP_400_BAD_REQUEST)

    # Block if email is already used as a teacher
    if models.Teacher.objects.filter(email=email).exists():
        return Response({
            'bool': False,
            'error': 'This email is registered as a teacher account. Please use a different email or log in as a teacher.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # LOGIN ONLY — reject if not already registered as a user
    try:
        user = models.User.objects.get(email=email)
    except models.User.DoesNotExist:
        return Response({
            'bool': False,
            'error': 'No account found with this Google email. Please register first.'
        }, status=status.HTTP_404_NOT_FOUND)

    return Response({
        'bool': True,
        'user_id': user.id,
        'full_name': user.full_name,
        'email': user.email,
        'username': user.username,
        'profile_picture': profile_picture,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth_register(request):
    """
    Google Register for Users — creates account if new, logs in if exists.
    Blocks emails already used as teacher accounts.
    """
    credential = request.data.get('credential')

    if not credential:
        return Response({'bool': False, 'error': 'Google credential is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        idinfo = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        return Response({'bool': False, 'error': 'Invalid Google token', 'detail': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

    email = idinfo.get('email')
    full_name = idinfo.get('name', '')
    profile_picture = idinfo.get('picture', '')

    if not email:
        return Response({'bool': False, 'error': 'Could not retrieve email from Google'}, status=status.HTTP_400_BAD_REQUEST)

    # Block if email is already used as a teacher
    if models.Teacher.objects.filter(email=email).exists():
        return Response({
            'bool': False,
            'error': 'This email is registered as a teacher account. Please use a different email or log in as a teacher.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Create account if new, log in if existing
    user, created = models.User.objects.get_or_create(
        email=email,
        defaults={
            'full_name': full_name,
            'username': email.split('@')[0],
            'password': make_password(secrets.token_hex(16)),
            'status': 'active',
        }
    )

    if not created and not user.full_name:
        user.full_name = full_name
        user.save()

    return Response({
        'bool': True,
        'user_id': user.id,
        'full_name': user.full_name,
        'email': user.email,
        'username': user.username,
        'profile_picture': profile_picture,
        'is_new_user': created,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth_teacher(request):
    """
    Google Login for Teachers ONLY — no registration.
    The teacher must already have an account with the same email.
    """
    credential = request.data.get('credential')

    if not credential:
        return Response({'bool': False, 'error': 'Google credential is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        idinfo = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        return Response({'bool': False, 'error': 'Invalid Google token'}, status=status.HTTP_401_UNAUTHORIZED)

    email = idinfo.get('email')

    if not email:
        return Response({'bool': False, 'error': 'Could not retrieve email from Google'}, status=status.HTTP_400_BAD_REQUEST)

    # Only LOGIN — do NOT create a new teacher
    try:
        teacher = models.Teacher.objects.get(email=email)
    except models.Teacher.DoesNotExist:
        return Response({
            'bool': False,
            'error': 'No teacher account found with this Google email. Please register manually first.'
        }, status=status.HTTP_404_NOT_FOUND)

    return Response({
        'bool': True,
        'teacher_id': teacher.id,
        'full_name': teacher.full_name,
        'email': teacher.email,
        'qualification': teacher.qualification,
        'mobile_no': teacher.mobile_no,
        'skills': teacher.skills,
    }, status=status.HTTP_200_OK)