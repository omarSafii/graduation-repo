from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_protect
from .models import *
from django.db.models import Sum, Q, Avg
from django.utils import timezone
from datetime import timedelta, datetime
from itertools import chain

from operator import attrgetter

@csrf_protect
def login(request):
    universities = University.objects.all()
    majors = Major.objects.all()
    
    if request.method == 'POST':
        # --- قسم تسجيل الدخول ---
        if request.POST.get("loginBtn") is not None:
            email = request.POST.get('email')
            password = request.POST.get('password')
            
            print(f"--- محاولة دخول بالإيميل: {email} والباسورد: {password} ---")

            # 1. ابحث عن الطالب بالإيميل أولاً
            student = Student.objects.filter(email=email).first()
            if student:
                print(f"تم إيجاد طالب بهذا الإيميل. الباسورد المخزن هو: {student.password}")
                if student.password == password:
                    request.session['email'] = email 
                    request.session['fullname'] = student.fullname
                    request.session['userType'] = "student"
                    return redirect('/')
                else:
                    return render(request, 'pages/login.html', {'msg': 'كلمة المرور غير صحيحة للطالب', 'unvs': universities, 'majors': majors})
                
            # 2. ابحث في المشرفين بالإيميل
            supervisor = Supervisor.objects.filter(email=email).first()
            if supervisor:
                print(f"تم إيجاد مشرف بهذا الإيميل. الباسورد المخزن هو: '{supervisor.password}'")
                print(f"الباسورد المدخل هو: '{password}'")
                print(f"هل الباسوردين متطابقين؟ {supervisor.password == password}")
                
                # تحقق من تطابق الباسورد بحذر
                if supervisor.password == password:
                    request.session['email'] = email 
                    request.session['fullname'] = supervisor.fullname
                    request.session['userType'] = "supervisor"
                    print("✅ تم تسجيل دخول المشرف بنجاح!")
                    return redirect('/')
                else:
                    print("❌ الباسورد غير متطابق")
                    return render(request, 'pages/login.html', {'msg': 'كلمة المرور غير صحيحة للمشرف', 'unvs': universities, 'majors': majors})
            
            # إذا لم يجد شيئاً أبداً
            print("لم يتم إيجاد أي مستخدم بهذا الإيميل في قاعدة البيانات")
            return render(request, 'pages/login.html', {'msg': 'هذا الإيميل غير مسجل في النظام', 'unvs': universities, 'majors': majors})

        # --- قسم إنشاء الحساب (كما هو مع إصلاح exists) ---
        elif request.POST.get("createAccount") is not None:
            userType = request.POST.get('type')
            email = request.POST.get('email')
            password = request.POST.get('password')
            rpassword = request.POST.get('rpassword')

            if password != rpassword:
                return render(request, 'pages/login.html', {'msg': 'كلمات المرور غير متطابقة', 'unvs': universities, 'majors': majors})

            if Student.objects.filter(email=email).exists() or Supervisor.objects.filter(email=email).exists():
                return render(request, 'pages/login.html', {'msg': 'الإيميل مسجل مسبقاً، حاول الدخول', 'unvs': universities, 'majors': majors})

            if userType == 'student':
                try:
                    mj_obj = Major.objects.get(id=int(request.POST.get('StudentMajor')))
                    unv_obj = University.objects.get(id=int(request.POST.get('StudentUniversity')))
                    
                    student = Student.objects.create(
                        fullname=request.POST.get('StudentFullName'),
                        password=password,
                        email=email,
                        student_id=request.POST.get('studentID'),
                        grade_year=request.POST.get('graduationYear'),
                        department=mj_obj,
                        university=unv_obj
                    )
                    StudentDetails.objects.create(studentID=student)
                    request.session['email'] = email
                    request.session['fullname'] = student.fullname
                    request.session['userType'] = "student"
                    return redirect('/')
                except Exception as e:
                    print(f"خطأ أثناء إنشاء الحساب: {e}")
                    return render(request, 'pages/login.html', {'msg': 'تأكد من اختيار الجامعة والتخصص وملء كافة الحقول', 'unvs': universities, 'majors': majors})
            
            # ⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇⬇
            # ⭐⭐ هذا القسم اللي ناقص: إنشاء حساب المشرف ⭐⭐
            # ⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆⬆
            
            elif userType == 'supervisor':
                try:
                    print(f"⭐ محاولة إنشاء حساب مشرف جديد:")
                    print(f"   📧 الإيميل: {email}")
                    print(f"   🔐 الباسورد: '{password}'")
                    print(f"   🏛️ الجامعة ID: {request.POST.get('supervisorUniversity')}")
                    print(f"   📚 القسم ID: {request.POST.get('supervisordepartment')}")
                    
                    # جلب كائنات الجامعة والقسم
                    university = University.objects.get(id=int(request.POST.get('supervisorUniversity')))
                    department = Major.objects.get(id=int(request.POST.get('supervisordepartment')))
                    
                    # إنشاء حساب المشرف
                    supervisor = Supervisor.objects.create(
                        fullname=request.POST.get('supervisorName'),
                        email=email,
                        password=password,  # ⚠ تأكد الباسورد يخزن نفس اللي دخلت
                        position=request.POST.get('supervisorPosotion'),
                        department=department,
                        university=university
                    )
                    
                    print(f"✅ تم إنشاء حساب المشرف بنجاح!")
                    print(f"   👤 الاسم: {supervisor.fullname}")
                    print(f"   📧 الإيميل: {supervisor.email}")
                    print(f"   🔐 الباسورد المخزن: '{supervisor.password}'")
                    
                    # تسجيل دخول تلقائي
                    request.session['email'] = email
                    request.session['fullname'] = supervisor.fullname
                    request.session['userType'] = "supervisor"
                    print("✅ تم تسجيل دخول المشرف تلقائياً!")
                    
                    return redirect('/')
                    
                except Exception as e:
                    print(f"❌ خطأ في إنشاء حساب المشرف: {e}")
                    return render(request, 'pages/login.html', {'msg': 'خطأ في إنشاء حساب المشرف. تأكد من البيانات', 'unvs': universities, 'majors': majors})

        return render(request, 'pages/login.html', {'unvs': universities, 'majors': majors})
    
    return render(request, 'pages/login.html', {'unvs': universities, 'majors': majors})


@csrf_protect
def index(request):
    # إصلاح شرط التحقق من الجلسة
    if 'email' not in request.session or request.session.get('email') is None:
        request.session['fullname'] = None
        request.session['userType'] = None
        request.session['email'] = None
    
    universities = University.objects.all()
    majors = Major.objects.all()
    years = [year for year in range(datetime.now().year, datetime.now().year - 6, -1)]
    
    data = {
        'majors': majors, 
        'univs': universities,
        'fullname': request.session.get('fullname'), 
        'userType': request.session.get('userType'), 
        'email': request.session.get('email'),
        'years': years,
    }
    
    if request.method == 'POST':
        try:
            majorID = int(request.POST.get('majorID'))
            universityID = int(request.POST.get('universityID'))
            yearID = int(request.POST.get('yearID'))
            projects = Projects.objects.filter(MajorID=majorID, yearOfProject=yearID, UniversityID=universityID)
            data.update({'projects': projects})
        except:
            pass
    else:
        projects = Projects.objects.all().order_by('id')
        data.update({'projects': projects})
        
    return render(request, 'pages/index.html', data)

@csrf_protect
def projectDetails(request, id):
    project = Projects.objects.get(id=id)
    Counter = Ratings.objects.filter(ProjectID=project).count()
    SumCreativity = Ratings.objects.filter(ProjectID=project).aggregate(total=Sum('Creativity'))['total'] or 0
    SumImplementation = Ratings.objects.filter(ProjectID=project).aggregate(total=Sum('Implementation'))['total'] or 0
    SumFunctionality = Ratings.objects.filter(ProjectID=project).aggregate(total=Sum('Functionality'))['total'] or 0
    SumInterface = Ratings.objects.filter(ProjectID=project).aggregate(total=Sum('Interface'))['total'] or 0
    
    try:
        rating = ((SumCreativity / Counter) + (SumImplementation / Counter) + (SumFunctionality / Counter) + (SumInterface / Counter)) / 4
        project.rates = rating
    except ZeroDivisionError:
        project.rates = 0

    pictures = ProjectPictures.objects.filter(ProjectID=project)
    videos = ProjectMedia.objects.filter(ProjectID=project)

    if 'email' in request.session:
        if request.session['userType'] == 'supervisor':
            if request.method == 'POST':
                if request.POST.get('sendcomment') is not None:
                    comment = request.POST.get('comment')
                    Comments(comment=comment, projectID=Projects.objects.get(id=id), SupervisorID=Supervisor.objects.get(email=request.session['email'])).save()

    data = {
        'project': project,
        'Creativity': (SumCreativity / Counter) if SumCreativity != 0 else 0,
        'Implementation': (SumImplementation / Counter) if SumImplementation != 0 else 0,
        'Functionality': (SumFunctionality / Counter) if SumFunctionality != 0 else 0,
        'Interface': (SumInterface / Counter) if SumInterface != 0 else 0,
        'pics': pictures,
        'videos': videos,
        'user': request.session['email'],
        'userType': request.session['userType'],
        'comments': Comments.objects.filter(projectID=Projects.objects.get(id=id))
    }
    
    return render(request, 'pages/Project Details.html', data)



@csrf_protect
def UploadProject(request):
    if 'email' in request.session:
        if request.session['email'] is not None:
            if request.session['userType'] == 'student':
                user = request.session['email']
                student_obj = Student.objects.get(email=user)

                if request.method == "POST":
                    if request.POST.get('uploadTheProject'):
                        ProjectTitle = request.POST.get('ProjectTitle')
                        ProjectType = request.POST.get('ProjectType')
                        graduationYear = request.POST.get('graduationYear')
                        Description = request.POST.get('Description')
                        fullDescription = request.POST.get('fullDescription')
                        videoFile = request.FILES.get('videoFile')
                        ImageFile = request.FILES.getlist('ImageFile')
                        pdfFile = request.FILES.get('PDFFILE')

                        unv = student_obj.university
                        mjr = student_obj.department
                        std = student_obj

                        # حقول جديدة من الفورم (اختياريان)
                        selected_supervisor_id = request.POST.get('supervisor')      # قد تكون '' أو None
                        selected_collab_id = request.POST.get('collaborator')       # قد تكون '' أو None

                        # تحقق من عدم تكرار نفس المشروع بالكامل
                        if not Projects.objects.filter(
                            ProjectName=ProjectTitle,
                            UniversityID=unv,
                            MajorID=mjr,
                            Student_id=std,
                            yearOfProject=graduationYear,
                            Description=Description,
                            FullDescription=fullDescription,
                            ProjectType=ProjectType
                        ).exists():
                            # أنشئ المشروع مع الحالة الافتراضية 'pending'
                            project = Projects.objects.create(
                                ProjectName=ProjectTitle,
                                UniversityID=unv,
                                MajorID=mjr,
                                Student_id=std,
                                yearOfProject=graduationYear,
                                Description=Description,
                                FullDescription=fullDescription,
                                pdf_file=pdfFile,
                                ProjectType=ProjectType,
                                status='pending'
                            )

                            # أضف الرافع كواحد من الطلاب المرتبطين (collaborators قائمة)
                            try:
                                project.collaborators.add(std)
                            except Exception:
                                pass

                            # إذا اختار الطالب زميل مشروع
                            if selected_collab_id:
                                try:
                                    collab = Student.objects.get(id=int(selected_collab_id))
                                    project.collaborators.add(collab)
                                except Exception:
                                    pass

                            # إذا اختار الطالب مشرف
                            if selected_supervisor_id:
                                try:
                                    sup = Supervisor.objects.get(id=int(selected_supervisor_id))
                                    project.supervisor = sup
                                    project.save()
                                except Exception:
                                    pass

                            # حفظ الوسائط كما في السابق
                            ProjectMedia(ProjectID=project, vedio=videoFile).save()
                            for pic in ImageFile:
                                ProjectPictures(ProjectID=project, image=pic).save()

                # عند الـ GET: مرّر القوائم اللازمة للقالب (supervisors و all_students)
                supervisors = Supervisor.objects.all()
                all_students = Student.objects.exclude(email=user)  # استبعد الرافع نفسه إن أردت
                return render(request, 'pages/Upload -project.html', {
                    'user': student_obj.fullname,
                    'supervisors': supervisors,
                    'all_students': all_students
                })
            else:
                return redirect('/error/')
        else:
            return redirect('/error/')
    else:
        return redirect('/login/')















@csrf_protect
def supervisor_requests(request):
    return redirect('/student-requests/')








@csrf_protect
def supervisor_decide(request, project_id):
    if 'email' in request.session and request.session.get('userType') == 'supervisor':
        supervisor = Supervisor.objects.get(email=request.session['email'])
        try:
            project = Projects.objects.get(id=project_id, supervisor=supervisor)
        except Projects.DoesNotExist:
            return redirect('supervisor_requests')

        if request.method == 'POST':
            action = request.POST.get('action')  # 'accept' أو 'reject'
            if action == 'accept':
                project.status = 'accepted'
                project.save()
            elif action == 'reject':
                project.status = 'rejected'
                project.save()
        return redirect('supervisor_requests')
    return redirect('/login/')












@csrf_protect
def BrowseProjects(request, type=None):    
    if 'email' in request.session:
        if request.session['email'] is not None:
            universities = University.objects.all()
            majors = Major.objects.all()
            years = [year for year in range(datetime.now().year, datetime.now().year - 6, -1)]
            
            data = {
                'univs': universities, 
                'majors': majors,
                'years': years,
                'email': request.session['email'],
                'fullname': request.session['fullname'],
                'userType': request.session['userType'],
            }
            
            if request.method == 'POST':
                if request.POST.get('filterSearch') is not None:
                    try:
                        major = request.POST.get('major')
                        university = request.POST.get('university')
                        year = request.POST.get('year')
                        
                        if type is None:
                            projects = Projects.objects.filter(MajorID=Major.objects.get(id=major), yearOfProject=year, UniversityID=University.objects.get(id=university))
                            data['projects'] = projects
                        elif type == 'new': 
                            projects = Projects.objects.filter(MajorID=Major.objects.get(id=major), yearOfProject=year, UniversityID=University.objects.get(id=university)).order_by('UploadDate')
                            data['projects'] = projects
                        elif type == 'old': 
                            projects = Projects.objects.filter(MajorID=Major.objects.get(id=major), yearOfProject=year, UniversityID=University.objects.get(id=university)).order_by('-UploadDate')
                            data['projects'] = projects
                        elif type == 'rating': 
                            projects = Projects.objects.filter(MajorID=Major.objects.get(id=major), yearOfProject=year, UniversityID=University.objects.get(id=university)).order_by('rates')
                            data['projects'] = projects
                    except:
                        pass
            else:
                if type is None:
                    projects = Projects.objects.all()
                    data['projects'] = projects
                elif type == 'new': 
                    projects = Projects.objects.all().order_by('UploadDate')
                    data['projects'] = projects
                elif type == 'old': 
                    projects = Projects.objects.all().order_by('-UploadDate')
                    data['projects'] = projects
                elif type == 'rating': 
                    projects = Projects.objects.all().order_by('rates')
                    data['projects'] = projects
                    
            return render(request, 'pages/Browse Projects.html', data)
        else:
            return redirect('/error/')
    else:
        return redirect('/login/')

def MyProject(request, id=None):
    if 'email' in request.session:
        if request.session['email'] is not None:
            if request.session['userType'] == 'student':
                email = request.session['email']
                data = {}
                
                if Projects.objects.filter(Student_id=Student.objects.get(email=email)).exists():
                    projects = Projects.objects.filter(Student_id=Student.objects.get(email=email))
                    maxRate = projects.order_by('-rates').first()
                    countOfProjects = projects.count()
                    avarageRating = (projects.aggregate(total=Sum('rates'))['total'] or 0) / countOfProjects
                    ratingProjects = Projects.objects.filter(Student_id=Student.objects.get(email=email), rates__gt=0).count()
                    
                    data = {
                        'projects': projects,
                        'maxRate': maxRate,
                        'ava': avarageRating,
                        'ratingProj': ratingProjects, 
                        'notRating': countOfProjects - ratingProjects,
                        'countOfprojs': countOfProjects,
                    }
                    
                    if id is not None:
                        Projects.objects.get(id=id).delete()
                        return redirect('MyProject')
                
                return render(request, 'pages/myproject.html', data)
            else:
                return redirect('/error/')
        else:
            return redirect('/error/')
    else:
        return redirect('/error/')

@csrf_protect
def loginForAdmin(request):
    if request.method == 'POST':
        if request.POST.get("loginBtn") is not None:
            email = request.POST.get('email')
            password = request.POST.get('password')
            
            if AdminUser.objects.filter(email=email).exists():
                if AdminUser.objects.filter(email=email, password=password).exists():
                    request.session['email'] = email 
                    request.session['fullname'] = AdminUser.objects.get(email=email).fullname
                    request.session['userType'] = "admin"
                    return redirect('/adminDashboard/')
                else:
                    return render(request, 'pages/login-admin.html', {'msg': 'the password is not correct'})    
    
    return render(request, 'pages/login-admin.html')

@csrf_protect
def AdminDashboard(request, emailDEl=None):
    if 'email' in request.session:
        if request.session['email'] is not None:
            if request.session['userType'] == "admin":
                data = {}
                one_day_ago = timezone.now() - timedelta(days=1)
                twohoursago = timezone.now() - timedelta(hours=2)
                oneWeekAgo = timezone.now() - timedelta(days=7)
                
                ############## users #############
                countOfUsers = Student.objects.all().count() + Supervisor.objects.all().count() + AdminUser.objects.all().count()
                data['countOfUsers'] = countOfUsers
                countOfStudents = Student.objects.all().count() + Supervisor.objects.all().count()
                data['countOfStudents'] = countOfStudents
                countOfSuperVisors = Supervisor.objects.all().count()
                data['countOfSupervisor'] = countOfSuperVisors 
                countOfAdmins = AdminUser.objects.all().count()
                data['countOfAdmins'] = countOfAdmins    
                
                ############# projects ############           
                countOfProjects = Projects.objects.all().count()
                data['countOfProjects'] = countOfProjects
                countOfNewProjects = Projects.objects.filter(UploadDate__lt=one_day_ago).count()
                data['countOfNewProjects'] = countOfNewProjects
                countOfRatedProjects = Projects.objects.filter(rates__gt=0).count()
                data['countOfRatedProjects'] = countOfRatedProjects
                countOfProjectsStillRating = countOfProjects - countOfRatedProjects
                data['countOfProjectsStillRating'] = countOfProjectsStillRating
                
                ############# universities ########
                countOfUniversities = University.objects.all().count()
                data['countOfUniversities'] = countOfUniversities
                universities_with_projects_count = University.objects.filter(projects__isnull=False).distinct().count()
                data['universities_with_projects_count'] = universities_with_projects_count
                
                ############ ratings ##############
                countOfRatings = Ratings.objects.all().count()
                data['countOfRatings'] = countOfRatings
                averageOfRating = Projects.objects.filter(rates__gt=0).aggregate(total=Sum('rates'))['total'] or 0
                data['averageOfRating'] = averageOfRating / countOfRatedProjects if averageOfRating > 0 else 0
                
                StudentsBeforTwoHours = Student.objects.filter(created_at__gt=twohoursago)
                SupervisorBeforTwoHours = Supervisor.objects.filter(created_at__gt=twohoursago)
                ProjectsBeforTwoHours = Projects.objects.filter(UploadDate__gt=twohoursago)
                RatingsBeforTwoHours = Ratings.objects.filter(created_at__gt=twohoursago)
                commentsBeforTwoHours = Comments.objects.filter(created_at__gt=twohoursago)
                
                for s in StudentsBeforTwoHours:
                    s.type = 'Student'
                for s in SupervisorBeforTwoHours:
                    s.type = "SuperVisor"
                for p in ProjectsBeforTwoHours:
                    p.type = 'Project'
                    p.created_at = p.UploadDate  # توحيد اسم حقل التاريخ
                for r in RatingsBeforTwoHours:
                    r.type = 'Rating'
                for c in commentsBeforTwoHours:
                    c.type = 'Comment'
                
                all_records = list(chain(StudentsBeforTwoHours, SupervisorBeforTwoHours, ProjectsBeforTwoHours, RatingsBeforTwoHours, commentsBeforTwoHours))
                sorted_records = sorted(all_records, key=attrgetter('created_at'), reverse=True)

                students = Student.objects.filter(created_at__gt=one_day_ago)
                supervisor = Supervisor.objects.filter(created_at__gt=one_day_ago)
                
                for s in students:
                    s.type = 'student'
                for s in supervisor:
                    s.type = 'supervisor'                
                
                allUsers = list(chain(students, supervisor))
                
                ########### return ################
                if request.method == 'POST':
                    fullname = request.POST.get('fullname')
                    email = request.POST.get('email')
                    password = request.POST.get('password')
                    rpassword = request.POST.get('rpassword')
                    
                    if fullname is not None and email is not None and password is not None and rpassword is not None:
                        if password == rpassword:
                            if not AdminUser.objects.filter(email=email).exists():
                                AdminUser(fullname=fullname, password=password, email=email).save()
                
                if emailDEl is not None:
                    if Student.objects.filter(email=emailDEl).exists():
                        Student.objects.get(email=emailDEl).delete()
                    elif Supervisor.objects.filter(email=emailDEl).exists():
                        Supervisor.objects.get(email=emailDEl).delete()
                    return redirect('/adminDashboard/')
                
                return render(request, 'pages/Admin Dashboard.html', {'data': data, 'records': sorted_records, 'userRecords': allUsers})
            else:
                return redirect('/error/')
        else: 
            return redirect('/error/')
    else:
        return redirect('/login/')

@csrf_protect
def studentProfile(request):
    if 'email' in request.session:
        if request.session['email'] is not None:
            if request.session['userType'] == 'student':
                user = request.session['email']
                data = {}
                student = Student.objects.get(email=user)
                projects = Projects.objects.filter(Student_id=student)
                
                if request.method == 'POST':
                    skills = request.POST.get('skills')
                    note = request.POST.get('note')
                    currentPassword = request.POST.get('currentPassword')
                    newPassword = request.POST.get('newPassword')
                    sure = request.POST.get('sure')
                    
                    if note is not None:
                        if not StudentDetails.objects.filter(studentID=student).exists():
                            StudentDetails(studentID=student, notes=note).save()
                        else:
                            if note is not None:
                                detail = StudentDetails.objects.get(studentID=student)
                                detail.notes = note
                                detail.save()
                    
                    if skills is not None:
                        if StudentDetails.objects.filter(studentID=student).exists():
                            detail = StudentDetails.objects.get(studentID=student)
                            skill = skills.split(',')
                            for s in skill:
                                if not Skills.objects.filter(skill=s, StudentDetail=detail).exists():
                                    Skills(StudentDetail=detail, skill=s).save()
                        else:
                            StudentDetails(studentID=student, notes=None).save()
                            skill = skills.split(',')
                            for s in skill:
                                Skills(StudentDetail=detail, skill=s).save()
                    
                    if currentPassword is not None and newPassword is not None and sure is not None:
                        if Student.objects.filter(email=user, password=currentPassword).exists():
                            if newPassword == sure:
                                student.password = newPassword
                
                data = {
                    'user': student,
                    'projects': projects,
                    'notes': StudentDetails.objects.get(studentID=student).notes,
                    'skills': Skills.objects.filter(StudentDetail=StudentDetails.objects.get(studentID=student)),
                    'countOfProjects': projects.count()
                }
                
                return render(request, 'pages/Student Profile.html', data)
            else:
                return redirect('/error/')
        else:
            return redirect('/error/')
    else:
        return redirect('/login/')

@csrf_protect
def supervisorDashboard(request):
    # تحقق سريع وموثوق من الجلسة
    if request.session.get('userType') != 'supervisor' or not request.session.get('email'):
        return redirect('/login/')

    # الآن نضمن أن هناك إيميل ونوع المستخدم مشرف
    try:
        user = Supervisor.objects.get(email=request.session['email'])
    except Supervisor.DoesNotExist:
        # لو المشرف غير موجود؛ نظف الجلسة وارجع لتسجيل الدخول
        request.session.flush()
        return redirect('/login/')

    # سنوات للاختيارات (لو لازمة بالصفحة)
    years = [year for year in range(datetime.now().year, datetime.now().year - 6, -1)]

    # جلب مشاريع المشرف الحالي فقط
    supervised_projects = Projects.objects.filter(supervisor=user)

    # إحصائيات للمشرف
    total_projects = supervised_projects.count()
    pending_projects = supervised_projects.filter(status='pending').count()
    accepted_projects = supervised_projects.filter(status='accepted').count()
    rejected_projects = supervised_projects.filter(status='rejected').count()

    # متوسط التقييم (إذا كان موجود)
    from django.db.models import Avg
    avg_rating = supervised_projects.aggregate(avg=Avg('rates'))['avg'] or 0

    # حزم البيانات المرسلة للقالب
    data = {
        'majors': Major.objects.all(),
        'years': years,
        'projects': supervised_projects,
        'total_projects': total_projects,
        'pending_projects': pending_projects,
        'accepted_projects': accepted_projects,
        'rejected_projects': rejected_projects,
        'avg_rating': round(avg_rating, 2),
        'fullname': request.session.get('fullname'),
        'email': request.session.get('email'),
        'userType': request.session.get('userType')
    }

    # POST handling (الحفظ والبحث) — أتركناه كما كان مع استخدام user
    if request.method == 'POST':
        if request.POST.get('saveRating') is not None:
            projectid = request.POST.get('projectid')
            Creativity = request.POST.get('Creativity')
            Implementation = request.POST.get('Implementation')
            Functionality = request.POST.get('Functionality')
            Interface = request.POST.get('Interface')
            notes = request.POST.get('notes')
            degree = request.POST.get('degree')

            Ratings(
                Creativity=Creativity,
                Implementation=Implementation,
                Functionality=Functionality,
                Interface=Interface,
                ProjectID=Projects.objects.get(id=projectid),
                notes=notes,
                SupervisorID=user
            ).save()
            # ضع درجة المشروع
            proj = Projects.objects.get(id=projectid)
            proj.degree = degree
            proj.save()

        # لو عندك بحث (غير مستخدم الآن لأننا حذفنا فلترة) يمكنك ترك هذا الجزء أو إزالته
        elif request.POST.get('search') is not None:
            try:
                major = int(request.POST.get('majorID'))
                year = int(request.POST.get('yearID'))
                projects = Projects.objects.filter(UniversityID=user.university)
                if major:
                    projects = projects.filter(MajorID=Major.objects.get(id=major))
                if year:
                    projects = projects.filter(yearOfProject=year)
                data['projects'] = projects
            except Exception:
                pass

    return render(request, 'pages/Supervisor Dashboard.html', data)

@csrf_protect
def ProjectEvaluationForm(request, id):
    # تأكد أن المستخدم مشرف ومجلس الجلسة صحيح
    if 'email' not in request.session or request.session.get('userType') != 'supervisor':
        return redirect('/login/')

    project = get_object_or_404(Projects, id=id)
    supervisor = Supervisor.objects.get(email=request.session['email'])

    # بيانات موجودة للعرض
    videos = ProjectMedia.objects.filter(ProjectID=project)
    pics = ProjectPictures.objects.filter(ProjectID=project)

    if request.method == 'POST':
        # جمع قيم المعايير
        Creativity = request.POST.get('Creativity') or 0
        Implementation = request.POST.get('Implementation') or 0
        Functionality = request.POST.get('Functionality') or 0
        Interface = request.POST.get('Interface') or 0

        # ملاحظات كل معيار (أضفنا الأسماء في القالب)
        note_creativity = request.POST.get('note_creativity', '').strip()
        note_implementation = request.POST.get('note_implementation', '').strip()
        note_functionality = request.POST.get('note_functionality', '').strip()
        note_interface = request.POST.get('note_interface', '').strip()

        # الملاحظات العامة
        general_notes = request.POST.get('notes', '').strip()

        # دمج الملاحظات بشكل منسق ليشوفها الطالب لاحقًا
        combined_notes = []
        if note_creativity:
            combined_notes.append(f"الإبداع: {note_creativity}")
        if note_implementation:
            combined_notes.append(f"التنفيذ: {note_implementation}")
        if note_functionality:
            combined_notes.append(f"الوظائف: {note_functionality}")
        if note_interface:
            combined_notes.append(f"الواجهة: {note_interface}")
        if general_notes:
            combined_notes.append(f"ملاحظات عامة: {general_notes}")

        notes_text = "\n\n".join(combined_notes) if combined_notes else None

        # خريطة لتحويل الحالة من العربية إلى القيم اللي بالموديل (إذا تستخدم إنجليزي)
        status_ar = request.POST.get('status', '').strip()
        status_map = {
            'مقبول': 'accepted',
            'مرفوض': 'rejected',
            'تحت المراجعة': 'under_review',
            'تحديث مطلوب': 'update_required'
        }
        mapped_status = status_map.get(status_ar, status_ar or project.status)

        # درجة وتصنيف
        degree = request.POST.get('degree')
        classification = request.POST.get('classfication') or None

        # التعامل مع أزرار الفورم
        if request.POST.get('saveRating') is not None:
            # حفظ تقييم نهائي في جدول Ratings
            Ratings.objects.create(
                Creativity=int(Creativity),
                Implementation=int(Implementation),
                Functionality=int(Functionality),
                Interface=int(Interface),
                ProjectID=project,
                notes=notes_text,
                SupervisorID=supervisor
            )
            # تعديل بيانات المشروع
            if degree:
                try:
                    project.degree = int(degree)
                except:
                    pass
            if classification:
                project.classification = classification
            project.status = mapped_status
            project.save()

            return redirect('supervisorDashboard')

        elif request.POST.get('saveDraft') is not None:
            # حفظ مسودة: نحفظ التقييم كـ Ratings مع وسم DRAFT داخل الملاحظات
            draft_notes = "[DRAFT]\n" + (notes_text or '')
            Ratings.objects.create(
                Creativity=int(float(Creativity)),
                Implementation=int(float(Implementation)),
                Functionality=int(float(Functionality)),
                Interface=int(float(Interface)),
                ProjectID=project,
                notes=draft_notes,
                SupervisorID=supervisor
            )
            # لا نغيّر حالة المشروع عند الحفظ كمسودة
            return redirect('ProjectEvaluationForm', id=project.id)

        elif request.POST.get('reject') is not None:
            # رفض المشروع سريعاً (يمكن حفظ ملاحظة الرفض)
            reject_notes = notes_text or "تم رفض المشروع بواسطة المشرف."
            Ratings.objects.create(
                Creativity=0,
                Implementation=0,
                Functionality=0,
                Interface=0,
                ProjectID=project,
                notes="[REJECT]\n" + reject_notes,
                SupervisorID=supervisor
            )
            project.status = 'rejected'
            project.save()
            return redirect('supervisorDashboard')

    # حساب القيم للعرض (مثلاً لملء القيم السابقة)
    # نأخذ آخر تقييم (إن وجد) ليعرض كنموذج مملوء
    last_rating = Ratings.objects.filter(ProjectID=project, SupervisorID=supervisor).order_by('-id').first()
    context = {
        'project': project,
        'videos': videos,
        'pics': pics,
        'comments': Comments.objects.filter(projectID=project),
        'last_rating': last_rating
    }
    return render(request, 'pages/Project Evaluation Form.html', context)
def logout(request):
    request.session.flush()
    return redirect('/')

def error_404(request):
    return render(request, 'pages/error.html')

def hello_world(request):
    return render(request, 'pages/hello_world.html')

def supervisor_projects(request):
    return render(request, "pages/supervisor_projects.html")
def complete_project(request):
    return render(request, "pages/complete_project.html")

def student_requests(request):
    # فقط للمشرفين
    if 'email' not in request.session or request.session.get('userType') != 'supervisor':
        return redirect('/login/')

    supervisor = Supervisor.objects.get(email=request.session['email'])

    # التحويل التلقائي للطلبات "المتجاهلة" بعد مدة (مثال: 7 أيام)
    IGNORE_DAYS = 7
    cutoff = timezone.now() - timedelta(days=IGNORE_DAYS)
    Projects.objects.filter(supervisor=supervisor, status='pending', requested_at__lt=cutoff).update(status='rejected')

    # جلب كل مشاريع هذا المشرف (بترتيب الأحدث أولاً) — تظهر كل الحالات لكن الأزرار مفعلة للـ pending فقط
    projects = Projects.objects.filter(supervisor=supervisor).order_by('-requested_at')

    # احصائيات صحيحة
    total_projects_count = projects.count()
    pending_projects_count = projects.filter(status='pending').count()
    accepted_projects_count = projects.filter(status='accepted').count()
    rejected_projects_count = projects.filter(status='rejected').count()

    context = {
        'projects': projects,
        'supervisor': supervisor,
        'total_projects_count': total_projects_count,
        'pending_projects_count': pending_projects_count,
        'accepted_projects_count': accepted_projects_count,
        'rejected_projects_count': rejected_projects_count,
    }

    return render(request, 'pages/student_requests.html', context)
