from os import stat

from django.contrib import admin
from django.urls import path, include

from project import settings
from . import views

urlpatterns = [
    # ط§ظ„طµظپط­ط© ط§ظ„ط±ط¦ظٹط³ظٹط©
    path('', views.index, name="index"),

    
    
    path('project/<int:project_id>/complete/', views.complete_project, name='complete_project'),
    path('supervisor/finish/<int:project_id>/', views.supervisor_finish, name='supervisor_finish'),
    
    
    # طھط³ط¬ظٹظ„ ط§ظ„ط¯ط®ظˆظ„
    path('login/', views.login, name="login"),
    path('loginAdmin/', views.loginForAdmin, name="LoginForAdmin"),
    path('logout/', views.logout, name="logout"),

    # طھظپط§طµظٹظ„ ط§ظ„ظ…ط´ط±ظˆط¹
    path('ProjectDetail/<int:id>/', views.projectDetails, name="projectDetails"),

    # ط±ظپط¹ / ط¥ط±ط³ط§ظ„ ط·ظ„ط¨ ظ…ط´ط±ظˆط¹ (ط§ظ„ظ†ط³ط®ط© ط§ظ„ظ…ط¹ط¯ظ„ط©)
    path('UploadProject/', views.UploadProject, name="UploadProject"),

    # طھطµظپط­ ط§ظ„ظ…ط´ط§ط±ظٹط¹
    path('BrowseProjects/', views.BrowseProjects, name="BrowseProjects"),
    path('BrowseProjects/<str:type>/', views.BrowseProjects, name="BrowseProjects"),
    path('supervisor/finish/<int:project_id>/', views.supervisor_finish, name='supervisor_finish'),
    path('complete_project/<int:project_id>/', views.complete_project, name='complete_project'),  # ط¥ط°ط§ ط¨طھط¬ط¹ظ„ complete_project ظٹط£ط®ط° id

    # ظ…ط´ط§ط±ظٹط¹ظٹ
    path('MyProject/', views.MyProject, name="MyProject"),
    path('MyProject/<int:id>/', views.MyProject, name="MyProject"),

    # ظ„ظˆط­ط© ط§ظ„ط£ط¯ظ…ظ†
    path('adminDashboard/', views.AdminDashboard, name="AdminDashboard"),
    path('adminDashboard/<str:emailDEl>/', views.AdminDashboard, name="AdminDashboard"),

    # ط¨ط±ظˆظپط§ظٹظ„ ط§ظ„ط·ط§ظ„ط¨
    path('profile/', views.studentProfile, name="studentProfile"),

    # ظ„ظˆط­ط© ط§ظ„ظ…ط´ط±ظپ
    path('supervisor/', views.supervisorDashboard, name="supervisorDashboard"),

    # âœ… ط·ظ„ط¨ط§طھ ط§ظ„ظ…ط´ط±ظپ (ظ…ظˆط­ظ‘ط¯ط©)
    path('student-requests/', views.student_requests, name='student_requests'),
    path('supervisor/requests/', views.student_requests, name='supervisor_requests'),

    # ظ‚ط¨ظˆظ„ / ط±ظپط¶ ط·ظ„ط¨
    path('supervisor/decide/<int:project_id>/', views.supervisor_decide, name="supervisor_decide"),

    # ظ…ط´ط§ط±ظٹط¹ ط§ظ„ظ…ط´ط±ظپ
    path('supervisor-projects/', views.supervisor_projects, name='supervisor_projects'),

    # طھظ‚ظٹظٹظ… ط§ظ„ظ…ط´ط±ظˆط¹
    path('ProjectEvaluationForm/<int:id>/', views.ProjectEvaluationForm, name="ProjectEvaluationForm"),

    # ط¥ظƒظ…ط§ظ„ ط§ظ„ظ…ط´ط±ظˆط¹

    # طµظپط­ط§طھ ط¥ط¶ط§ظپظٹط©
    path('error/', views.error_404, name="error"),
    path('hello/', views.hello_world, name="hello_world"),
]

