from django.contrib import admin
from django.urls import path , include
from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('login/', views.login, name="login"),
    path('ProjectDetail/<int:id>', views.projectDetails, name="projectDetails"),
    path('UploadProject/', views.UploadProject, name="UploadProject"),
    path('BrowseProjects/<str:type>', views.BrowseProjects, name="BrowseProjects"),
    path('BrowseProjects/', views.BrowseProjects, name="BrowseProjects"),
    path('MyProject/', views.MyProject, name="MyProject"),
    path('MyProject/<int:id>', views.MyProject, name="MyProject"),
    path('adminDashboard/<str:emailDEl>', views.AdminDashboard, name="AdminDashboard"),
    path('adminDashboard/', views.AdminDashboard, name="AdminDashboard"),
    path('loginAdmin/', views.loginForAdmin, name="LoginForAdmin"),
    path('profile/', views.studentProfile, name="studentProfile"),
    path('supervisor/', views.supervisorDashboard, name="supervisorDashboard"),
    path('supervisor/requests/', views.supervisor_requests, name="supervisor_requests"),  # NEW: طلبات المشرف المعلقة
    path('supervisor/decide/<int:project_id>/', views.supervisor_decide, name="supervisor_decide"),  # NEW: قبول/رفض مشروع
    path('ProjectEvaluationForm/<int:id>', views.ProjectEvaluationForm, name="ProjectEvaluationForm"),
    path('logout/', views.logout, name="logout"),
    path('error/', views.error_404, name="error"),
    path('hello/', views.hello_world, name="hello_world"),
    path('student-requests/', views.student_requests, name='student_requests'),
]


"""



from django.contrib import admin
 from django.urls import path , include from .
   import views urlpatterns = [ path('' , views.index, name="index"),
     path('login/' , views.login , name="login"),
       path('ProjectDetail/<int:id>' , views.projectDetails , name="projectDetails"), 
       path('UploadProject/' , views.UploadProject , name="UploadProject"), path('BrowseProjects/<str:type>' , views.BrowseProjects , name="BrowseProjects"),
         path('BrowseProjects/' , views.BrowseProjects , name="BrowseProjects"), path('MyProject/' , views.MyProject , name="MyProject"), path('MyProject/<int:id>' , views.MyProject , name="MyProject"), 
         path('adminDashboard/<str:emailDEl>' , views.AdminDashboard , name="AdminDashboard"), path('adminDashboard/' , views.AdminDashboard , name="AdminDashboard"), path('loginAdmin/' , views.loginForAdmin , name="LoginForAdmin") , 
         path('profile/' , views.studentProfile , name = "studentProfile" ), path('supervisor/' , views.supervisorDashboard , name="supervisorDashboard"),
           path('ProjectEvaluationForm/<int:id>' , views.ProjectEvaluationForm , name="ProjectEvaluationForm"), path('logout/' , views.logout , name="logout") ,
             path('error/' , views.error_404 , name="error"), path('hello/', views.hello_world, name="hello_world"),
               path('student-requests/', views.student_requests, name='student_requests'), ]













"""