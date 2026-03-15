from os import stat

from django.contrib import admin
from django.urls import path, include

from project import settings
from . import views

urlpatterns = [
    # الصفحة الرئيسية
    path('', views.index, name="index"),

    
    
    path('project/<int:project_id>/complete/', views.complete_project, name='complete_project'),
    path('supervisor/finish/<int:project_id>/', views.supervisor_finish, name='supervisor_finish'),
    
    
    # تسجيل الدخول
    path('login/', views.login, name="login"),
    path('loginAdmin/', views.loginForAdmin, name="LoginForAdmin"),
    path('logout/', views.logout, name="logout"),

    # تفاصيل المشروع
    path('ProjectDetail/<int:id>/', views.projectDetails, name="projectDetails"),

    # رفع / إرسال طلب مشروع (النسخة المعدلة)
    path('UploadProject/', views.UploadProject, name="UploadProject"),

    # تصفح المشاريع
    path('BrowseProjects/', views.BrowseProjects, name="BrowseProjects"),
    path('BrowseProjects/<str:type>/', views.BrowseProjects, name="BrowseProjects"),
    path('supervisor/finish/<int:project_id>/', views.supervisor_finish, name='supervisor_finish'),
    path('complete_project/<int:project_id>/', views.complete_project, name='complete_project'),  # إذا بتجعل complete_project يأخذ id

    # مشاريعي
    path('MyProject/', views.MyProject, name="MyProject"),
    path('MyProject/<int:id>/', views.MyProject, name="MyProject"),

    # لوحة الأدمن
    path('adminDashboard/', views.AdminDashboard, name="AdminDashboard"),
    path('adminDashboard/<str:emailDEl>/', views.AdminDashboard, name="AdminDashboard"),

    # بروفايل الطالب
    path('profile/', views.studentProfile, name="studentProfile"),

    # لوحة المشرف
    path('supervisor/', views.supervisorDashboard, name="supervisorDashboard"),

    # ✅ طلبات المشرف (موحّدة)
    path('student-requests/', views.supervisor_requests, name='student_requests'),
    path('supervisor/requests/', views.supervisor_requests, name='supervisor_requests'),

    # قبول / رفض طلب
    path('supervisor/decide/<int:project_id>/', views.supervisor_decide, name="supervisor_decide"),

    # مشاريع المشرف
    path('supervisor-projects/', views.supervisor_projects, name='supervisor_projects'),

    # تقييم المشروع
    path('ProjectEvaluationForm/<int:id>/', views.ProjectEvaluationForm, name="ProjectEvaluationForm"),

    # إكمال المشروع

    # صفحات إضافية
    path('error/', views.error_404, name="error"),
    path('hello/', views.hello_world, name="hello_world"),
]