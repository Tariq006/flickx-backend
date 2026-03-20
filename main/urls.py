from django.urls import path
from . import views

urlpatterns = [
    # ==================== AUTHENTICATION ROUTES ====================
    # These routes provide alternate paths for frontend compatibility
    # They point to the same views as the original routes
    
    # Teacher Auth (supports both /auth/teacher-login/ and /teacher-login/)
    path('auth/teacher-login/', views.teacher_login, name='auth_teacher_login'),
    
    # User Auth (supports both /auth/user-login/ and /user-login/)
    # Note: Your frontend might be calling this. Add if needed.
    # path('auth/user-login/', views.user_login, name='auth_user_login'),
    
    # Admin Auth
    path('auth/admin-login/', views.admin_login, name='admin_login'),
    path('auth/admin-register/', views.admin_register, name='auth_admin_register'),
    path('admin-register/', views.admin_register, name='admin_register'),
    
    # ==================== ORIGINAL ROUTES ====================
    # Teacher
    path('teacher/', views.TeacherList.as_view()),
    path('teacher/<int:pk>/', views.TeacherDetail.as_view()),
    path('teacher-login/', views.teacher_login),
    
    # Category
    path('category/', views.CategoryList.as_view()),
    
    # Course
    path('course/', views.CourseList.as_view()),
    path('course/<int:pk>/', views.CourseDetail.as_view()),
    
    # Teacher Course
    path('teacher-course/<int:teacher_id>/', views.TeacherCourseList.as_view()),
    path('teacher-course-detail/<int:pk>/', views.TeacherCourseDetail.as_view()),
    
    # Chapter
    path('chapter/', views.ChapterList.as_view()),
    path('chapter/<int:pk>/', views.ChapterDetail.as_view()),
    path('course-chapters/<int:course_id>/', views.CourseChapterList.as_view()),
    
    # User (formerly Student)
    path('user/', views.UserList.as_view()),
    path('user/<int:pk>/', views.UserDetail.as_view()),
    path('user-login/', views.user_login),
    
    # Course Enrollment
    path('enrollments/', views.UserCourseEnrollmentList.as_view()),
    path('enrollments/<int:pk>/', views.UserCourseEnrollmentDetail.as_view()),
    path('course-enrollments/<int:course_id>/', views.CourseEnrollments.as_view()),
    path('user-enrollments/<int:user_id>/', views.UserEnrollments.as_view()),
    path('check-enrollment/', views.check_enrollment_status),
    path('enroll-user/', views.enroll_user),
    
    # Course Ratings
    path('course-ratings/<int:course_id>/', views.CourseRatingList.as_view()),
    path('user-rating/<int:course_id>/<int:user_id>/', views.UserCourseRating.as_view()),
    path('course-rating-stats/<int:course_id>/', views.CourseRatingStats.as_view()),
    path('submit-rating/', views.submit_rating),
    
    # Favorite Courses
    path('user-favorites/<int:user_id>/', views.UserFavoriteCourses.as_view()),
    path('check-favorite/', views.check_favorite_status),
    path('toggle-favorite/', views.toggle_favorite),
    path('remove-favorite/<int:favorite_id>/', views.remove_favorite),
    
    # Assignment URLs
    path('teacher-assignments/<int:teacher_id>/', views.TeacherAssignments.as_view()),
    path('course-assignments/<int:course_id>/', views.CourseAssignments.as_view()),
    path('assignment/<int:pk>/', views.AssignmentDetail.as_view()),
    path('assignment-submissions/<int:assignment_id>/', views.AssignmentSubmissions.as_view()),
    path('student-assignments/<int:student_id>/', views.StudentAssignmentSubmissions.as_view()),
    path('submit-assignment/', views.submit_assignment),
    path('grade-assignment/<int:submission_id>/', views.grade_assignment),
    path('assignment-stats/<int:assignment_id>/', views.assignment_stats),

    # Quiz URLs - FIXED AND ORGANIZED
    # Teacher Quiz Management
    path('teacher-quizzes/<int:teacher_id>/', views.TeacherQuizzes.as_view(), name='teacher_quizzes'),
    path('teacher/<int:teacher_id>/quizzes/', views.TeacherQuizzes.as_view(), name='teacher_quizzes_alt'),
    
    # Course Quizzes
    path('course-quizzes/<int:course_id>/', views.CourseQuizzes.as_view(), name='course_quizzes'),
    
    # Quiz CRUD
    path('quiz/<int:pk>/', views.QuizDetail.as_view(), name='quiz_detail'),
    
    # Quiz Questions Management (for teachers creating questions)
    path('quiz-questions/<int:quiz_id>/', views.QuizQuestions.as_view(), name='quiz_questions'),
    path('quiz-question/<int:pk>/', views.QuizQuestionDetail.as_view(), name='quiz_question_detail'),
    
    # Quiz Taking (for students)
    path('start-quiz/', views.start_quiz, name='start_quiz'),
    path('get-quiz-questions/<int:quiz_id>/', views.get_quiz_questions, name='get_quiz_questions'),
    path('submit-quiz-answer/', views.submit_quiz_answer, name='submit_quiz_answer'),
    path('complete-quiz/', views.complete_quiz, name='complete_quiz'),
    
    # Quiz Review (for students after submission)
    path('quiz-submission-details/<int:quiz_id>/', views.get_quiz_submission_details, name='quiz_submission_details'),
    
    # Quiz Submissions and Stats
    path('quiz-submissions/<int:quiz_id>/', views.QuizSubmissions.as_view(), name='quiz_submissions'),
    path('student-quiz-submissions/<int:student_id>/', views.StudentQuizSubmissions.as_view(), name='student_quiz_submissions'),
    path('quiz-stats/<int:quiz_id>/', views.quiz_stats, name='quiz_stats'),

    # Search
    path('search/', views.search_courses, name='search_courses'),
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),

    # Course Materials
    path('course-materials/<int:course_id>/', views.CourseMaterialsList.as_view(), name='course_materials'),
    path('upload-material/', views.upload_material, name='upload_material'),
    path('material/<int:material_id>/', views.delete_material, name='delete_material'),
    path('material/<int:pk>/', views.StudyMaterialDetail.as_view(), name='material_detail'),

    # Course Stats
    path('popular-courses/', views.popular_courses, name='popular-courses'),
    path('course/<int:course_id>/increment-views/', views.increment_course_views, name='increment-course-views'),
    path('course/<int:course_id>/stats/', views.course_stats, name='course-stats'),

    # Mentorship Sessions
    path('teacher/<int:teacher_id>/mentorship-sessions/', 
         views.TeacherMentorshipSessions.as_view(), 
         name='teacher_mentorship_sessions'),
    
    path('teacher/<int:teacher_id>/courses/<int:course_id>/mentorship-sessions/', 
         views.TeacherCourseMentorshipSessions.as_view(), 
         name='teacher_course_mentorship_sessions'),
    
    path('mentorship-session/<int:pk>/', 
         views.UpdateMentorshipSession.as_view(), 
         name='mentorship_session_detail'),
    
    path('create-mentorship-session/', 
         views.SimpleCreateMentorshipSession.as_view(), 
         name='create_mentorship_session'),
    
    path('user/<int:user_id>/available-mentorship-sessions/', 
         views.StudentAvailableMentorshipSessions.as_view(), 
         name='student_available_sessions'),
    
    path('user/<int:user_id>/courses/<int:course_id>/mentorship-sessions/', 
         views.CourseMentorshipSessionsForStudent.as_view(), 
         name='course_mentorship_for_student'),
    
    path('register-mentorship/', 
         views.RegisterForMentorshipSession.as_view(), 
         name='register_mentorship'),
    
    path('user/<int:user_id>/mentorship-registrations/', 
         views.UserMentorshipRegistrations.as_view(), 
         name='user_mentorship_registrations'),
    
    path('user/<int:user_id>/mentorship-dashboard/', 
         views.MentorshipDashboard.as_view(), 
         name='mentorship_dashboard'),

    path('update-session-status/<int:session_id>/', 
          views.UpdateSessionStatus.as_view(), 
          name='update_session_status'),

    # ==================== ADMIN ENDPOINTS ====================
    # Admin CRUD
    path('admin/', views.AdminList.as_view(), name='admin_list'),
    path('admin/<int:pk>/', views.AdminDetail.as_view(), name='admin_detail'),
    
    # Admin Dashboard & Analytics
    path('admin/dashboard/', views.AdminDashboard.as_view(), name='admin_dashboard'),
    path('admin/analytics/', views.AdminAnalytics.as_view(), name='admin_analytics'),
    path('admin/reports/', views.admin_generate_report, name='admin_reports'),
    
    # Admin User Management
    path('admin/users/', views.AdminUsersList.as_view(), name='admin_users_list'),
    path('admin/users/<int:user_id>/toggle-status/', views.admin_toggle_user_status, name='admin_toggle_user_status'),
    path('admin/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    
    # Admin Teacher Management
    path('admin/teachers/', views.AdminTeachersList.as_view(), name='admin_teachers_list'),
    path('admin/teachers/<int:teacher_id>/delete/', views.admin_delete_teacher, name='admin_delete_teacher'),
    
    # Admin Course Management
    path('admin/courses/', views.AdminCoursesList.as_view(), name='admin_courses_list'),
    path('admin/courses/<int:course_id>/delete/', views.admin_delete_course, name='admin_delete_course'),
    path('admin/courses/<int:course_id>/approve/', views.admin_approve_course, name='admin_approve_course'),
    
    # Admin Category Management
    path('admin/categories/create/', views.admin_create_category, name='admin_create_category'),
    path('admin/categories/<int:category_id>/update/', views.admin_update_category, name='admin_update_category'),
    path('admin/categories/<int:category_id>/delete/', views.admin_delete_category, name='admin_delete_category'),

     #forum
     path('course/<int:course_id>/forum/', views.CourseForumView.as_view(), name='course_forum'),
     path('forum/<int:forum_id>/messages/', views.ForumMessagesView.as_view(), name='forum_messages'),
     path('forum/message/<int:pk>/', views.ForumMessageDetailView.as_view(), name='forum_message_detail'),
     path('forum/message/<int:message_id>/react/', views.ForumReactionView.as_view(), name='forum_message_react'),
     path('forum/<int:forum_id>/members/', views.ForumMembersView.as_view(), name='forum_members'),
     path('user/<int:user_id>/forums/', views.UserForumsView.as_view(), name='user_forums'),
     path('user/<int:user_id>/forum-unread/', views.ForumUnreadCountView.as_view(), name='forum_unread'),
     path('user/<int:user_id>/forum-notifications/', views.ForumNotificationsView.as_view(), name='forum_notifications'),
     path('user/<int:user_id>/mark-notifications-read/', views.mark_notifications_read, name='mark_notifications_read'),
     path('forum/<int:forum_id>/search/', views.ForumSearchView.as_view(), name='forum_search'),


     path('forgot-password/', views.forgot_password, name='forgot_password'),
     path('reset-password/', views.reset_password, name='reset_password'),
     path('verify-reset-token/', views.verify_reset_token, name='verify_reset_token'),
     path('auth/google/', views.google_auth, name='google_auth'),
     path('auth/google-teacher/', views.google_auth_teacher, name='google_auth_teacher'),
     path('auth/google-register/', views.google_auth_register, name='google_auth_register'),

]