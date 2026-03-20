# signals.py - Enhanced version with improved error handling and logging

from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction
import logging

from .models import (
    Course, UserCourseEnrollment, CourseForum, 
    ForumMember, Teacher, User, ForumNotification,
    ForumMessage
)

# Set up logging
logger = logging.getLogger(__name__)


# signals.py - Update to handle both user and teacher

@receiver(post_save, sender=Course)
def create_course_forum(sender, instance, created, **kwargs):
    """Create forum and add teacher as member"""
    if created:
        try:
            with transaction.atomic():
                forum = CourseForum.objects.create(
                    course=instance,
                    name=f"{instance.title} Discussion Group",
                    description=f"Welcome to the {instance.title} course discussion forum!",
                    is_active=True,
                    allow_student_messages=True,
                    allow_file_sharing=True,
                    require_approval=False
                )
                
                # Add teacher as member
                if instance.teacher:
                    ForumMember.objects.create(
                        forum=forum,
                        teacher=instance.teacher,
                        role='teacher',
                        is_admin=True
                    )
                    logger.info(f"Added teacher {instance.teacher.full_name} to forum")
                    
        except Exception as e:
            logger.error(f"Error creating forum: {str(e)}")


@receiver(post_save, sender=UserCourseEnrollment)
def add_student_to_forum(sender, instance, created, **kwargs):
    """Add student to forum when they enroll"""
    if created:
        try:
            with transaction.atomic():
                forum, _ = CourseForum.objects.get_or_create(course=instance.course)
                
                ForumMember.objects.get_or_create(
                    forum=forum,
                    user=instance.user,
                    defaults={'role': 'student', 'is_admin': False}
                )
                
                logger.info(f"Added student {instance.user.full_name} to forum")
                
        except Exception as e:
            logger.error(f"Error adding student to forum: {str(e)}")

@receiver(post_save, sender=UserCourseEnrollment)
def add_student_to_forum(sender, instance, created, **kwargs):
    """
    Automatically add student to course forum when they enroll.
    If forum doesn't exist, create it first.
    """
    if created:
        try:
            with transaction.atomic():
                # Get or create the forum for this course
                forum, forum_created = CourseForum.objects.get_or_create(
                    course=instance.course,
                    defaults={
                        'name': f"{instance.course.title} Discussion Group",
                        'description': f"Discussion forum for {instance.course.title} course. "
                                      f"Connect with your instructor and classmates.",
                        'is_active': True,
                        'allow_student_messages': True,
                        'allow_file_sharing': True,
                        'require_approval': False
                    }
                )
                
                if forum_created:
                    logger.info(f"Created forum during enrollment for course: {instance.course.title}")
                    
                    # If we just created the forum, add the teacher as admin
                    if instance.course.teacher:
                        try:
                            teacher_user = User.objects.filter(
                                email=instance.course.teacher.email
                            ).first()
                            if teacher_user:
                                ForumMember.objects.get_or_create(
                                    forum=forum,
                                    user=teacher_user,
                                    defaults={
                                        'role': 'teacher',
                                        'is_admin': True
                                    }
                                )
                        except Exception as e:
                            logger.error(f"Error adding teacher during enrollment: {str(e)}")
                
                # Add the student to the forum
                member, member_created = ForumMember.objects.get_or_create(
                    forum=forum,
                    user=instance.user,
                    defaults={
                        'role': 'student',
                        'is_admin': False
                    }
                )
                
                if member_created:
                    logger.info(
                        f"Added student {instance.user.full_name} to forum for {instance.course.title}"
                    )
                    
                    # Create welcome notification for the student
                    try:
                        ForumNotification.objects.create(
                            recipient=instance.user,
                            notification_type='member_joined',
                            title=f'Welcome to {instance.course.title} Discussion',
                            content=f"You've been added to the course discussion forum. "
                                   f"Say hello and connect with your classmates and instructor!",
                            is_read=False
                        )
                    except Exception as e:
                        logger.error(f"Error creating student welcome notification: {str(e)}")
                    
                    # Notify teacher about new student joining
                    if instance.course.teacher:
                        try:
                            teacher_user = User.objects.filter(
                                email=instance.course.teacher.email
                            ).first()
                            if teacher_user and teacher_user.id != instance.user.id:
                                ForumNotification.objects.create(
                                    recipient=teacher_user,
                                    notification_type='member_joined',
                                    title='New Student Joined Forum',
                                    content=f'{instance.user.full_name} has enrolled in '
                                           f'{instance.course.title} and joined the discussion forum.',
                                    is_read=False
                                )
                        except Exception as e:
                            logger.error(f"Error creating teacher notification: {str(e)}")
                else:
                    logger.info(
                        f"Student {instance.user.full_name} already a member of forum "
                        f"for {instance.course.title}"
                    )
                    
        except Exception as e:
            logger.error(
                f"Error adding student {instance.user.id} to forum for "
                f"course {instance.course.id}: {str(e)}"
            )


@receiver(post_delete, sender=UserCourseEnrollment)
def remove_student_from_forum(sender, instance, **kwargs):
    """
    Remove student from forum when they unenroll from a course.
    Also delete their messages and notifications.
    """
    try:
        with transaction.atomic():
            forum = CourseForum.objects.filter(course=instance.course).first()
            if forum:
                # Get the forum member record
                member = ForumMember.objects.filter(
                    forum=forum,
                    user=instance.user
                ).first()
                
                if member:
                    # Optional: Soft delete user's messages instead of hard delete
                    # ForumMessage.objects.filter(
                    #     forum=forum,
                    #     sender=instance.user
                    # ).update(is_deleted=True, content="[Message from removed user]")
                    
                    # Remove the member
                    member.delete()
                    logger.info(
                        f"Removed student {instance.user.full_name} from forum "
                        f"for {instance.course.title}"
                    )
                    
                    # Notify teacher about student leaving
                    if instance.course.teacher:
                        try:
                            teacher_user = User.objects.filter(
                                email=instance.course.teacher.email
                            ).first()
                            if teacher_user:
                                ForumNotification.objects.create(
                                    recipient=teacher_user,
                                    notification_type='member_joined',
                                    title='Student Left Forum',
                                    content=f'{instance.user.full_name} has unenrolled from '
                                           f'{instance.course.title} and left the discussion forum.',
                                    is_read=False
                                )
                        except Exception as e:
                            logger.error(f"Error creating teacher notification for unenrollment: {str(e)}")
                            
    except Exception as e:
        logger.error(
            f"Error removing student {instance.user.id} from forum: {str(e)}"
        )


@receiver(pre_delete, sender=Course)
def cleanup_course_forum(sender, instance, **kwargs):
    """
    Clean up forum when a course is deleted.
    Note: This is optional as CASCADE delete should handle it,
    but included for explicit cleanup and logging.
    """
    try:
        forum = CourseForum.objects.filter(course=instance).first()
        if forum:
            member_count = forum.members.count()
            message_count = forum.messages.count()
            logger.info(
                f"Deleting forum for course {instance.title}. "
                f"Members: {member_count}, Messages: {message_count}"
            )
    except Exception as e:
        logger.error(f"Error in cleanup_course_forum: {str(e)}")


# Optional: Signal to update forum name when course title changes
@receiver(post_save, sender=Course)
def update_forum_name(sender, instance, created, **kwargs):
    """
    Update forum name and description when course title changes.
    Only runs on updates, not creation.
    """
    if not created:
        try:
            forum = CourseForum.objects.filter(course=instance).first()
            if forum:
                new_name = f"{instance.title} Discussion Group"
                if forum.name != new_name:
                    forum.name = new_name
                    forum.description = (
                        f"Discussion forum for {instance.title} course. "
                        f"Connect with your instructor and classmates."
                    )
                    forum.save(update_fields=['name', 'description'])
                    logger.info(f"Updated forum name for course: {instance.title}")
        except Exception as e:
            logger.error(f"Error updating forum name: {str(e)}")