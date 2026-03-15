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




from django.contrib import messages  # استيراد الرسائل



@csrf_protect
def supervisor_finish(request, project_id):
    # فقط للمشرف المتصل
    if 'email' not in request.session or request.session.get('userType') != 'supervisor':
        messages.error(request, "❌ ليس لديك صلاحية للوصول إلى هذه الصفحة.")
        return redirect('login')

    try:
        supervisor = Supervisor.objects.get(email=request.session['email'])
    except Supervisor.DoesNotExist:
        messages.error(request, "❌ لم يتم العثور على حساب المشرف.")
        return redirect('login')

    try:
        project = Projects.objects.get(id=project_id, supervisor=supervisor)
    except Projects.DoesNotExist:
        messages.error(request, "❌ المشروع غير موجود أو أنت لست المشرف عليه.")
        return redirect('supervisor_projects')

    if request.method == 'POST':
        # اضغط زر الانتهاء => نعلَن المشروع منشور ليظهر في BrowseProjects
        project.is_published = True
        project.status = 'accepted'  # تأكد من الحالة
        project.save()

        # رسالة نجاح خضراء
        messages.success(request, f"✅ تم إنهاء المشروع «{project.ProjectName}» ونشره بنجاح في صفحة التصفح.")

        return redirect('supervisor_projects')

    # إذا وصل بالـ GET
    messages.warning(request, "⚠️ طلب غير صالح.")
    return redirect('supervisor_projects')







@csrf_protect
def index(request):

    # تجهيز الجلسة إذا لم تكن موجودة
    if 'email' not in request.session:
        request.session['fullname'] = None
        request.session['userType'] = None
        request.session['email'] = None

    universities = University.objects.all()
    majors = Major.objects.all()

    years = [year for year in range(datetime.now().year, datetime.now().year - 11, -1)]  # آخر 10 سنوات

    # المشاريع الافتراضية (آخر المشاريع) - المنشورة والمقبولة فقط
    projects = Projects.objects.filter(
        status='accepted',
        is_published=True
    ).order_by('-id')

    # إذا كان هناك فلترة (POST)
    if request.method == 'POST':
        majorID = request.POST.get('majorID')
        projectType = request.POST.get('projectType')  # نوع المشروع
        yearID = request.POST.get('yearID')  # السنة

        # نبدأ بجميع المشاريع المنشورة والمقبولة
        filtered_projects = Projects.objects.filter(
            status='accepted',
            is_published=True
        )

        # تطبيق فلترة التخصص إذا تم اختياره
        if majorID and majorID.strip():
            filtered_projects = filtered_projects.filter(MajorID=majorID)

        # تطبيق فلترة نوع المشروع إذا تم اختياره
        if projectType and projectType.strip():
            filtered_projects = filtered_projects.filter(ProjectType=projectType)

        # تطبيق فلترة السنة إذا تم اختيارها
        if yearID and yearID.strip():
            filtered_projects = filtered_projects.filter(yearOfProject=yearID)

        # ترتيب النتائج
        projects = filtered_projects.order_by('-id')

    data = {
        'majors': majors,
        'univs': universities,
        'years': years,
        'projects': projects,
        'fullname': request.session.get('fullname'),
        'userType': request.session.get('userType'),
        'email': request.session.get('email'),
        'project_types': ['تخرج', 'فصلي', 'حلقة بحث'],  # لإرسالها للقالب
    }

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
    # لازم المستخدم مسجل وطالب
    if 'email' not in request.session or request.session.get('userType') != 'student':
        return redirect('login')

    student_obj = Student.objects.get(email=request.session['email'])

    if request.method == "POST":
        # ---------------------------
        # 1) ارسال طلب المشروع (الفورم الجديد) -> name="submitRequest"
        # ---------------------------
        if request.POST.get('submitRequest'):
            major_id = request.POST.get('department')
            project_type = request.POST.get('projectType')
            project_year = request.POST.get('projectYear')
            title_ar = request.POST.get('title_ar')
            title_en = request.POST.get('title_en')
            supervisor_id = request.POST.get('supervisor')
            idea = request.POST.get('idea_summary')
            what = request.POST.get('what_will_be_done')
            stages = request.POST.get('project_stages')

            # جلب Major إن وُجد
            major = None
            try:
                if major_id:
                    major = Major.objects.get(id=int(major_id))
            except Exception:
                major = None

            # جلب Supervisor إن وُجد
            sup = None
            try:
                if supervisor_id:
                    sup = Supervisor.objects.get(id=int(supervisor_id))
            except Exception:
                sup = None

            # أنشئ المشروع كسجل pending
            project = Projects.objects.create(
                ProjectName = title_ar or title_en or "مشروع بدون عنوان",
                UniversityID = student_obj.university,
                MajorID = major if major else (Major.objects.first() if Major.objects.exists() else None),
                Student_id = student_obj,
                yearOfProject = int(project_year) if project_year else timezone.now().year,
                Description = idea or "",
                FullDescription = (what or "") + "\n\nMILESTONES:\n" + (stages or ""),
                ProjectType = project_type or "",
                status = 'pending',
                requested_at = timezone.now(),
                supervisor = sup
            )

            # اضف collaborators من hidden inputs (name="collaborator")
            collab_ids = request.POST.getlist('collaborator')
            for cid in collab_ids:
                try:
                    s = Student.objects.get(id=int(cid))
                    project.collaborators.add(s)
                except Exception:
                    pass

            project.save()

            # بعد ارسال الطلب - نوجّه الطالب لمشاريعه
            return redirect('MyProject')

        # ---------------------------
        # 2) رفع ملفات المشروع (الكود القديم) -> name="uploadTheProject"
        # ---------------------------
        elif request.POST.get('uploadTheProject'):
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

                try:
                    project.collaborators.add(std)
                except Exception:
                    pass

                selected_collab_id = request.POST.get('collaborator')
                selected_supervisor_id = request.POST.get('supervisor')

                if selected_collab_id:
                    try:
                        collab = Student.objects.get(id=int(selected_collab_id))
                        project.collaborators.add(collab)
                    except Exception:
                        pass

                if selected_supervisor_id:
                    try:
                        sup = Supervisor.objects.get(id=int(selected_supervisor_id))
                        project.supervisor = sup
                        project.save()
                    except Exception:
                        pass

                if videoFile:
                    ProjectMedia(ProjectID=project, vedio=videoFile).save()
                for pic in ImageFile:
                    ProjectPictures(ProjectID=project, image=pic).save()

            return redirect('MyProject')

    # GET: عرض الفورم
    supervisors = Supervisor.objects.all()
    all_students = Student.objects.exclude(email=student_obj.email)
    majors = Major.objects.all()
    return render(request, 'pages/Upload -project.html', {
        'user': student_obj.fullname,
        'supervisors': supervisors,
        'all_students': all_students,
        'majors': majors
    })



@csrf_protect
def supervisor_requests(request):
    # تأكد إن الجلسة لمشرف
    if 'email' not in request.session or request.session.get('userType') != 'supervisor':
        return redirect('login')

    # جلب كائن المشرف (آمن)
    try:
        supervisor = Supervisor.objects.get(email=request.session['email'])
    except Supervisor.DoesNotExist:
        return redirect('login')

    # إذا تحب تغيير مدة التجاهل غيّر القيمة هنا (أيام)
    IGNORE_DAYS = 7
    cutoff = timezone.now() - timedelta(days=IGNORE_DAYS)

    # حوّل الطلبات القديمة من pending إلى rejected (ميزة التجاهل التلقائي)
    Projects.objects.filter(supervisor=supervisor, status='pending', requested_at__lt=cutoff).update(status='rejected')

    # جلب جميع المشاريع المتعلقة بالمشرف (عرض شامل: pending, accepted, rejected)
    projects = Projects.objects.filter(supervisor=supervisor).order_by('-requested_at')

    # إحصائيات حسب الحالة (مفيدة للـ sidebar)
    pending_count = Projects.objects.filter(supervisor=supervisor, status='pending').count()
    accepted_count = Projects.objects.filter(supervisor=supervisor, status='accepted').count()
    rejected_count = Projects.objects.filter(supervisor=supervisor, status='rejected').count()

    # مرر كل شيء للقالب student_requests.html
    return render(request, 'pages/student_requests.html', {
        'projects': projects,
        'pending_projects_count': pending_count,
        'accepted_projects_count': accepted_count,
        'rejected_projects_count': rejected_count,
        'supervisor': supervisor
    })




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
    # صلاحية الجلسة
    if 'email' not in request.session or request.session.get('email') is None:
        return redirect('/login/')

    universities = University.objects.all()
    majors = Major.objects.all()
    years = [year for year in range(datetime.now().year, datetime.now().year - 6, -1)]

    # الأساس: مشاريع مقبولة ومنشورة فقط
    visible_projects = Projects.objects.filter(status='accepted', is_published=True)
    projects_qs = visible_projects

    # ----- دعم فلترة GET -----
    major_get = request.GET.get('major')
    university_get = request.GET.get('university')
    year_get = request.GET.get('year')
    sort_get = request.GET.get('sort')
    project_type_get = request.GET.get('project_type')

    try:
        if major_get:
            projects_qs = projects_qs.filter(MajorID__id=int(major_get))
    except Exception:
        pass

    try:
        if university_get:
            projects_qs = projects_qs.filter(UniversityID__id=int(university_get))
    except Exception:
        pass

    try:
        if year_get:
            projects_qs = projects_qs.filter(yearOfProject=int(year_get))
    except Exception:
        pass

    # فلترة حسب نوع المشروع
    if project_type_get:
        projects_qs = projects_qs.filter(ProjectType=project_type_get)

    # ========== إضافة متوسط التقييمات لكل مشروع ==========
    # هذا الجزء مهم جداً لإظهار النجوم في الصفحة
    projects_list = []
    for project in projects_qs:
        ratings = Ratings.objects.filter(ProjectID=project)
        if ratings.exists():
            total_avg = 0
            for rating in ratings:
                # حساب متوسط المعايير الأربعة لكل تقييم
                rating_avg = (rating.Creativity + rating.Implementation + 
                             rating.Functionality + rating.Interface) / 4
                total_avg += rating_avg
            # متوسط جميع التقييمات (من 0 إلى 100) ثم تحويله إلى 5 نجوم
            project.avg_rating = (total_avg / ratings.count()) / 20
            project.avg_percent = total_avg / ratings.count()  # النسبة المئوية
        else:
            project.avg_rating = 0
            project.avg_percent = 0
        projects_list.append(project)

    # ترتيب حسب sort
    sort = sort_get or type
    if sort == 'new':
        projects_list = sorted(projects_list, key=lambda x: x.UploadDate, reverse=True)
    elif sort == 'old':
        projects_list = sorted(projects_list, key=lambda x: x.UploadDate)
    elif sort == 'rating':
        projects_list = sorted(projects_list, key=lambda x: x.avg_rating, reverse=True)

    # تجميع البيانات للقالب
    data = {
        'univs': universities,
        'majors': majors,
        'years': years,
        'email': request.session.get('email'),
        'fullname': request.session.get('fullname'),
        'userType': request.session.get('userType'),
        'projects': projects_list,  # الآن تحتوي على avg_rating و avg_percent
        'current_filters': {
            'major': major_get or '',
            'university': university_get or '',
            'year': year_get or '',
            'sort': sort or '',
            'project_type': project_type_get or '',
        }
    }

    return render(request, 'pages/Browse Projects.html', data)

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
    # ========== التحقق من صلاحية المشرف ==========
    if 'email' not in request.session or request.session.get('userType') != 'supervisor':
        return redirect('/login/')

    # ========== جلب بيانات المشروع والمشرف ==========
    project = get_object_or_404(Projects, id=id)
    supervisor = Supervisor.objects.get(email=request.session['email'])

    # ========== جلب الوسائط (فيديو، صور) ==========
    videos = ProjectMedia.objects.filter(ProjectID=project)
    pics = ProjectPictures.objects.filter(ProjectID=project)

    # ========== جميع التقييمات السابقة لهذا المشرف وهذا المشروع (مرتبة تنازلياً) ==========
    all_ratings = Ratings.objects.filter(ProjectID=project, SupervisorID=supervisor).order_by('-id')
    
    # آخر تقييم (لاستخدامه في تعبئة النموذج تلقائياً)
    last_rating = all_ratings.first()

    # ========== معالجة طلب POST (حفظ التقييم الجديد) ==========
    if request.method == 'POST':
        # --- استلام درجات المعايير ---
        Creativity = request.POST.get('Creativity') or 0
        Implementation = request.POST.get('Implementation') or 0
        Functionality = request.POST.get('Functionality') or 0
        Interface = request.POST.get('Interface') or 0

        # --- استلام ملاحظات كل معيار ---
        note_creativity = request.POST.get('note_creativity', '').strip()
        note_implementation = request.POST.get('note_implementation', '').strip()
        note_functionality = request.POST.get('note_functionality', '').strip()
        note_interface = request.POST.get('note_interface', '').strip()
        general_notes = request.POST.get('notes', '').strip()  # ملاحظات عامة

        # --- دمج جميع الملاحظات في نص واحد منسق ---
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

        # --- تحويل حالة المشروع من العربية إلى الإنجليزية (حسب الموديل) ---
        status_ar = request.POST.get('status', '').strip()
        status_map = {
            'مقبول': 'accepted',
            'مرفوض': 'rejected',
            'تحت المراجعة': 'under_review',
            'تحديث مطلوب': 'update_required'
        }
        mapped_status = status_map.get(status_ar, status_ar or project.status)

        # --- الدرجة الكلية والتصنيف ---
        degree = request.POST.get('degree')
        classification = request.POST.get('classfication') or None

        # --- تحديد نوع الزر الذي تم الضغط عليه ---
        if request.POST.get('saveRating') is not None:
            # 1️⃣ حفظ تقييم نهائي
            Ratings.objects.create(
                Creativity=int(Creativity),
                Implementation=int(Implementation),
                Functionality=int(Functionality),
                Interface=int(Interface),
                ProjectID=project,
                notes=notes_text,
                SupervisorID=supervisor
            )
            # تحديث بيانات المشروع
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
            # 2️⃣ حفظ كمسودة (مع وسم DRAFT)
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
            # لا نغير حالة المشروع عند الحفظ كمسودة
            return redirect('ProjectEvaluationForm', id=project.id)

        elif request.POST.get('reject') is not None:
            # 3️⃣ رفض المشروع (مع وسم REJECT)
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

    # ========== تحضير بيانات التقييمات السابقة للعرض (مع متوسطات النقاط والنجوم) ==========
    ratings_with_avg = []
    for rating in all_ratings:
        total = rating.Creativity + rating.Implementation + rating.Functionality + rating.Interface
        avg_percent = total / 4  # متوسط مئوي (من 100)
        stars = round(avg_percent / 20)  # تحويل إلى 5 نجوم (100/20 = 5)
        stars = max(1, min(5, stars))  # ضمان أن القيمة بين 1 و 5

        ratings_with_avg.append({
            'rating': rating,
            'avg_percent': avg_percent,
            'stars': stars,
            'total': total,
            'is_draft': '[DRAFT]' in rating.notes if rating.notes else False,
            'is_reject': '[REJECT]' in rating.notes if rating.notes else False,
        })

    # ========== تجهيز السياق ==========
    context = {
        'project': project,
        'videos': videos,
        'pics': pics,
        'comments': Comments.objects.filter(projectID=project),
        'last_rating': last_rating,
        'all_ratings': all_ratings,          # التقييمات الخام (إذا احتجتها)
        'ratings_with_avg': ratings_with_avg, # تقييمات مع المتوسطات والنجوم (جاهزة للعرض)
        'ratings_count': all_ratings.count(), # عدد التقييمات
    }
    return render(request, 'pages/Project Evaluation Form.html', context)




def logout(request):
    request.session.flush()
    return redirect('/')

def error_404(request):
    return render(request, 'pages/error.html')

def hello_world(request):
    return render(request, 'pages/hello_world.html')

@csrf_protect
def supervisor_projects(request):
    if 'email' not in request.session or request.session.get('userType') != 'supervisor':
        return redirect('login')

    supervisor = Supervisor.objects.get(email=request.session['email'])
    # اعرض المشاريع المقبولة فقط (أو كل المشاريع تحت إشرافه حسب اختيارك)
    projects = Projects.objects.filter(supervisor=supervisor, status='accepted').order_by('-requested_at')
    # او لو تريد رؤية كل الحالات: Projects.objects.filter(supervisor=supervisor).order_by('-requested_at')

    context = {'projects': projects, 'userType': 'supervisor', 'email': request.session.get('email'), 'fullname': request.session.get('fullname')}
    return render(request, "pages/supervisor_projects.html", context)




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



#تعديل صفحة ارسال طلب
@csrf_protect
def submit_request(request):
    # لازم المستخدم مسجل ويكون student
    if 'email' not in request.session or request.session.get('userType') != 'student':
        return redirect('login')

    student = Student.objects.get(email=request.session['email'])

    if request.method == "POST" and request.POST.get('submitRequest'):
        # اجلب القيم من الفورم
        major_id = request.POST.get('department')             # يجب ان تكون id للـ Major
        project_type = request.POST.get('projectType')
        project_year = request.POST.get('projectYear')
        title_ar = request.POST.get('title_ar')
        title_en = request.POST.get('title_en')
        supervisor_id = request.POST.get('supervisor')
        idea = request.POST.get('idea_summary')
        what = request.POST.get('what_will_be_done')
        stages = request.POST.get('project_stages')

        # تحويلات/تحققات بسيطة
        try:
            major = Major.objects.get(id=int(major_id))
        except Exception:
            major = None

        sup = None
        try:
            if supervisor_id:
                sup = Supervisor.objects.get(id=int(supervisor_id))
        except Exception:
            sup = None

        # أنشئ المشروع كـ pending request
        project = Projects.objects.create(
            ProjectName = title_ar or title_en or "مشروع بدون عنوان",
            UniversityID = student.university,
            MajorID = major if major else (Major.objects.first() if Major.objects.exists() else None),
            Student_id = student,
            yearOfProject = int(project_year) if project_year else timezone.now().year,
            Description = idea,
            FullDescription = (what or "") + "\n\nMILESTONES:\n" + (stages or ""),
            ProjectType = project_type,
            status = 'pending',
            requested_at = timezone.now(),
            supervisor = sup
        )

        # اضف collaborators من hidden inputs (name="collaborator")
        collab_ids = request.POST.getlist('collaborator')
        for cid in collab_ids:
            try:
                s = Student.objects.get(id=int(cid))
                project.collaborators.add(s)
            except Exception:
                pass

        project.save()

        # redirect يلي يناسبك - اقترح صفحة تأكيد أو صفحة المشروعات الخاصة بالطالب
        return redirect('MyProject')   # غيرها لو تحب صفحة تأكيد

    # GET: عرض الفورم (اذا نفس التمبلت)
    supervisors = Supervisor.objects.all()
    all_students = Student.objects.exclude(email=student.email)
    majors = Major.objects.all()
    return render(request, 'pages/submit_request.html', {
        'supervisors': supervisors,
        'all_students': all_students,
        'majors': majors,
        'user': student.fullname
    })
    
@csrf_protect
def student_project_conversation(request, project_id):
    # صلاحية: فقط الطالب المالك أو collaborators
    if 'email' not in request.session or request.session.get('userType') != 'student':
        return redirect('login')

    try:
        student = Student.objects.get(email=request.session['email'])
    except Student.DoesNotExist:
        return redirect('login')

    project = get_object_or_404(Projects, id=project_id)
    # تأكد أن الطالب مالك المشروع أو من الcollaborators
    allowed = False
    if project.Student_id and project.Student_id.id == student.id:
        allowed = True
    if project.collaborators.filter(id=student.id).exists():
        allowed = True

    if not allowed:
        return redirect('/error/')

    # POST: إرسال رسالة من الطالب
    if request.method == 'POST' and request.POST.get('send_message') is not None:
        text = request.POST.get('message_text', '').strip()
        file = request.FILES.get('message_file', None)

        msg = ProjectConversationMessage(project=project, text=text, sender_student=student)
        if file:
            msg.attachment = file
        msg.save()
        return redirect('student_project_conversation', project_id=project.id)

    # GET: جلب كل الرسائل المرتبة زمنياً
    messages = project.messages.all().order_by('created_at')

    return render(request, 'pages/student_conversation.html', {
        'project': project,
        'messages': messages,
        'student': student,
        'fullname': request.session.get('fullname'),
        'email': request.session.get('email'),
    })
    
@csrf_protect
def complete_project(request, project_id):
    """
    View واحد ومُحدّث لإدارة صفحة إتمام المشروع:
    - صلاحية: الطالب المالك أو زميل في collaborators أو المشرف المعين
    - يدعم: إرسال تحديثات/رسائل (مشرف/طالب)، رفع وسائط (فيديو، صور، pdf)، وإنهاء المشروع (بواسطة المشرف)
    - عند انتهاء المشرف: يضع is_published=True و status='accepted' ويعيد التوجيه إلى BrowseProjects
    """
    from django.contrib import messages  # استيراد محلي عشان ما نعتمد على مكان الاستيراد في الأعلى

    # جلب المشروع (أو 404)
    project = get_object_or_404(Projects, id=project_id)

    # بيانات الجلسة
    user_email = request.session.get('email')
    user_type = request.session.get('userType')

    # التحقق من هوية المستخدم (طالب أو مشرف)
    student_user = None
    supervisor_user = None
    allowed = False

    if user_email and user_type == 'student':
        try:
            student_user = Student.objects.get(email=user_email)
            # إن كان مالك المشروع
            if project.Student_id and project.Student_id.id == student_user.id:
                allowed = True
            # أو إن كان من collaborators
            if project.collaborators.filter(id=student_user.id).exists():
                allowed = True
        except Student.DoesNotExist:
            student_user = None

    if user_email and user_type == 'supervisor':
        try:
            supervisor_user = Supervisor.objects.get(email=user_email)
            # السماح لو هو المشرف المعين
            if project.supervisor and project.supervisor.id == supervisor_user.id:
                allowed = True
        except Supervisor.DoesNotExist:
            supervisor_user = None

    # لو مش مسموح له بالدخول
    if not allowed:
        return redirect('/error/')

    # POST handling
    if request.method == 'POST':
        # 1) مشرف أو طالب يرسل تحديث/رسالة (زر send_update أو send_message)
        # دعم كلا الاسمين لأن القوالب قد تستعمل أحدهما
        if request.POST.get('send_update') is not None or request.POST.get('send_message') is not None:
            # نص الرسالة قد يأتي من update_message_text أو message_text
            text = request.POST.get('update_message_text', '') or request.POST.get('message_text', '')
            text = text.strip()
            file = request.FILES.get('update_file') or request.FILES.get('message_file')

            # لا تحفظ رسالة فارغة بدون نص وبدون مرفق
            if not text and not file:
                messages.warning(request, "لا يمكن إرسال رسالة فارغة.")
                return redirect('complete_project', project_id=project.id)

            msg = ProjectConversationMessage(project=project, text=text)

            # عيّن المرسل الصحيح
            if user_type == 'student' and student_user:
                msg.sender_student = student_user
            elif user_type == 'supervisor' and supervisor_user:
                msg.sender_supervisor = supervisor_user

            if file:
                msg.attachment = file

            msg.save()
            messages.success(request, "تم إرسال الرسالة بنجاح.")
            return redirect('complete_project', project_id=project.id)

        # 2) حفظ بيانات / رفع وسائط (save_data)
        elif request.POST.get('save_data') is not None:
            # ملفات قد تُرسل: videoFile, ImageFile (multiple), PDFFILE
            video_file = request.FILES.get('videoFile')
            image_files = request.FILES.getlist('ImageFile')
            pdf_file = request.FILES.get('PDFFILE')

            # حفظ الفيديو
            if video_file:
                try:
                    ProjectMedia.objects.create(ProjectID=project, vedio=video_file)
                except Exception as e:
                    messages.error(request, f"خطأ عند حفظ الفيديو: {e}")
                    return redirect('complete_project', project_id=project.id)

            # حفظ الصور
            for img in image_files:
                try:
                    ProjectPictures.objects.create(ProjectID=project, image=img)
                except Exception as e:
                    # لا نوقف العملية للصور المتبقية، فقط نعلم المستخدم
                    messages.warning(request, f"بعض الصور لم تحفظ: {e}")

            # حفظ PDF في حقل المشروع نفسه
            if pdf_file:
                try:
                    project.pdf_file = pdf_file
                    project.save()
                except Exception as e:
                    messages.error(request, f"خطأ عند حفظ ملف الـ PDF: {e}")
                    return redirect('complete_project', project_id=project.id)

            messages.success(request, "تم حفظ الوسائط بنجاح.")
            return redirect('complete_project', project_id=project.id)

        # 3) إنهاء المشروع (للمشرف فقط)
        elif request.POST.get('finish_project') is not None and user_type == 'supervisor' and supervisor_user:
            # نعلّم المشروع منشوراً حتى يظهر في BrowseProjects
            project.is_published = True
            # نضع الحالة accepted ليطابق فلترة BrowseProjects (يمكن تغييرها لاحقاً)
            project.status = 'accepted'
            # نحدّث تاريخ الرفع ليظهر كأحدث (اختياري لكنه مفيد)
            try:
                project.UploadDate = timezone.now()
            except Exception:
                pass
            project.save()

            messages.success(request, "تم إنهاء المشروع ونشره في صفحة التصفح.")
            # نعيد التوجيه لصفحة التصفح ليرى المشرف والطلاب أنه أصبح مرئياً
            return redirect('BrowseProjects')

        # 4) أي زر آخر يمكن إضافته هنا لاحقاً

    # GET: جلب كل البيانات لعرضها في القالب
    messages_qs = project.messages.all().order_by('created_at')
    pics = ProjectPictures.objects.filter(ProjectID=project)
    videos = ProjectMedia.objects.filter(ProjectID=project)
    pdf = project.pdf_file if getattr(project, 'pdf_file', None) else None

    context = {
        'project': project,
        'messages': messages_qs,
        'pdf': pdf,
        'videos': videos,
        'pics': pics,
        'user_type': user_type,
        'fullname': request.session.get('fullname'),
        'email': user_email,
    }
    return render(request, 'pages/complete_project.html', context) 
    
    
