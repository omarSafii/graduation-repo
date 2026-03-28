from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_protect
from .models import *
from django.db.models import Sum, Q, Avg
from django.utils import timezone
from datetime import timedelta, datetime
from itertools import chain
from operator import attrgetter
from os.path import splitext
from django.contrib import messages


def _project_students(project):
    students = []
    seen_ids = set()

    if project.Student_id and project.Student_id.id not in seen_ids:
        students.append(project.Student_id)
        seen_ids.add(project.Student_id.id)

    for collaborator in project.collaborators.all():
        if collaborator.id not in seen_ids:
            students.append(collaborator)
            seen_ids.add(collaborator.id)

    return students


def _average_rating_value(rating):
    return (rating.Creativity + rating.Implementation + rating.Functionality + rating.Interface) / 4


def _rating_css_class(avg_rating):
    if avg_rating >= 4:
        return 'text-warning'
    if avg_rating >= 3:
        return 'text-success'
    if avg_rating >= 2:
        return 'text-info'
    if avg_rating > 0:
        return 'text-secondary'
    return 'text-muted'


def _project_rating_summary(project, supervisor=None):
    ratings_qs = Ratings.objects.filter(ProjectID=project)
    if supervisor is not None:
        ratings_qs = ratings_qs.filter(SupervisorID=supervisor)

    ratings = list(ratings_qs)
    if not ratings:
        return {
            'avg_percent': 0,
            'avg_rating': 0,
            'rating_count': 0,
            'rounded_stars': 0,
            'has_ratings': False,
            'star_css_class': 'text-muted',
        }

    avg_percent = sum(_average_rating_value(rating) for rating in ratings) / len(ratings)
    avg_rating = avg_percent / 20

    return {
        'avg_percent': avg_percent,
        'avg_rating': avg_rating,
        'rating_count': len(ratings),
        'rounded_stars': max(0, min(5, round(avg_rating))),
        'has_ratings': True,
        'star_css_class': _rating_css_class(avg_rating),
    }


def _can_manage_final_score(project, supervisor):
    return bool(project.supervisor_id and supervisor and project.supervisor_id == supervisor.id)


def _is_word_document(uploaded_file):
    return splitext(uploaded_file.name)[1].lower() in {'.doc', '.docx'}


def _is_zip_document(uploaded_file):
    return splitext(uploaded_file.name)[1].lower() == '.zip'


def _is_image_file(uploaded_file):
    return splitext(uploaded_file.name)[1].lower() in {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}


def _is_video_file(uploaded_file):
    return splitext(uploaded_file.name)[1].lower() in {'.mp4', '.mov', '.avi', '.mkv', '.webm'}


def _is_project_participant(project, student):
    if not student:
        return False
    return any(member.id == student.id for member in _project_students(project))


def _can_view_grade(project, request):
    if project.degree is None:
        return False

    user_type = request.session.get('userType')
    email = request.session.get('email')

    if not email:
        return False

    if user_type == 'supervisor':
        supervisor = Supervisor.objects.filter(email=email).first()
        if not supervisor:
            return False
        if project.supervisor_id == supervisor.id:
            return True
        return bool(project.final_score_visible)

    if user_type == 'student':
        student = Student.objects.filter(email=email).first()
        if not student:
            return False
        if _is_project_participant(project, student):
            return True
        return bool(project.final_score_visible)

    return bool(project.final_score_visible)


def _parse_request_submission(project):
    full_description = (project.FullDescription or '').strip()
    what_will_be_done = ''
    project_stages = ''

    if 'MILESTONES:\n' in full_description:
        what_will_be_done, project_stages = full_description.split('MILESTONES:\n', 1)
    else:
        what_will_be_done = full_description

    return {
        'title': project.ProjectName,
        'major': project.MajorID.major_name if project.MajorID else '',
        'project_type': project.ProjectType or '',
        'project_year': project.yearOfProject,
        'supervisor_name': project.supervisor.fullname if project.supervisor else 'غير محدد',
        'idea_summary': (project.Description or '').strip(),
        'what_will_be_done': what_will_be_done.strip(),
        'project_stages': project_stages.strip(),
    }
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
            
            # â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡â¬‡
            # ⭐⭐ هذا القسم اللي ناقص: إنشاء حساب المشرف ⭐⭐
            # â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†â¬†
            
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
                        position='Supervisor',
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
    if 'email' not in request.session or request.session.get('userType') != 'supervisor':
        messages.error(request, "You are not allowed to access this page.")
        return redirect('login')

    try:
        supervisor = Supervisor.objects.get(email=request.session['email'])
    except Supervisor.DoesNotExist:
        messages.error(request, "Supervisor account was not found.")
        return redirect('login')

    try:
        project = Projects.objects.get(id=project_id, supervisor=supervisor)
    except Projects.DoesNotExist:
        messages.error(request, "Project not found or you are not assigned to it.")
        return redirect('supervisor_projects')

    if request.method == 'POST':
        project.is_published = True
        project.status = 'accepted'
        project.edits_approved = True
        project.is_completed = True
        project.save(update_fields=['is_published', 'status', 'edits_approved', 'is_completed'])
        messages.success(request, f'Project "{project.ProjectName}" was completed and published successfully.')
        return redirect('supervisor_projects')

    messages.warning(request, "Invalid request.")
    return redirect('supervisor_projects')

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
    project = get_object_or_404(Projects, id=id)
    ratings_qs = Ratings.objects.filter(ProjectID=project)
    criteria = ratings_qs.aggregate(
        avg_creativity=Avg('Creativity'),
        avg_implementation=Avg('Implementation'),
        avg_functionality=Avg('Functionality'),
        avg_interface=Avg('Interface')
    )
    rating_summary = _project_rating_summary(project)

    project.rates = rating_summary['avg_rating']
    pictures = ProjectPictures.objects.filter(ProjectID=project)
    videos = ProjectMedia.objects.filter(ProjectID=project)
    participant_students = _project_students(project)
    request_submission = _parse_request_submission(project)

    session_email = request.session.get('email')
    session_user_type = request.session.get('userType')
    current_supervisor = Supervisor.objects.filter(email=session_email).first() if session_user_type == 'supervisor' and session_email else None
    can_open_evaluation = bool(session_user_type == 'supervisor' and project.is_completed)
    is_supervisor_reviewing_request = bool(session_user_type == 'supervisor' and project.status == 'pending')
    selected_stars = 0
    can_manage_final_score = False
    if current_supervisor:
        can_manage_final_score = _can_manage_final_score(project, current_supervisor)
        supervisor_rating = Ratings.objects.filter(ProjectID=project, SupervisorID=current_supervisor).first()
        if supervisor_rating:
            selected_stars = round(_average_rating_value(supervisor_rating) / 20)

    data = {
        'project': project,
        'Creativity': criteria['avg_creativity'] or 0,
        'Implementation': criteria['avg_implementation'] or 0,
        'Functionality': criteria['avg_functionality'] or 0,
        'Interface': criteria['avg_interface'] or 0,
        'pics': pictures,
        'videos': videos,
        'user': session_email,
        'userType': session_user_type,
        'email': session_email,
        'fullname': request.session.get('fullname'),
        'participant_students': participant_students,
        'rating_summary': rating_summary,
        'show_final_score': _can_view_grade(project, request) and project.degree is not None,
        'request_submission': request_submission,
        'can_open_evaluation': can_open_evaluation,
        'is_supervisor_reviewing_request': is_supervisor_reviewing_request,
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
    projects = Projects.objects.filter(supervisor=supervisor, status__in=['pending', 'rejected'], is_completed=False).order_by('-requested_at')

    for project in projects:
        project.participant_students = _project_students(project)

    # إحصائيات حسب الحالة (مفيدة للـ sidebar)
    pending_count = Projects.objects.filter(supervisor=supervisor, status='pending', is_completed=False).count()
    accepted_count = Projects.objects.filter(supervisor=supervisor, status='accepted', is_completed=False).count()
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
            action = request.POST.get('action')
            if action == 'accept':
                project.status = 'accepted'
                project.edits_approved = False
                project.is_completed = False
                project.save(update_fields=['status', 'edits_approved', 'is_completed'])
                request.session.flush()
                return redirect('login')
            elif action == 'reject':
                project.status = 'rejected'
                project.edits_approved = False
                project.is_completed = False
                project.save(update_fields=['status', 'edits_approved', 'is_completed'])
        return redirect('supervisor_requests')
    return redirect('/login/')

@csrf_protect
def BrowseProjects(request, type=None):
    universities = University.objects.all()
    majors = Major.objects.all()
    years = [year for year in range(datetime.now().year, datetime.now().year - 6, -1)]

    projects_qs = Projects.objects.filter(status='accepted', is_published=True)

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

    if project_type_get:
        projects_qs = projects_qs.filter(ProjectType=project_type_get)

    projects_list = []
    for project in projects_qs:
        rating_summary = _project_rating_summary(project)
        project.avg_rating = rating_summary['avg_rating']
        project.avg_percent = rating_summary['avg_percent']
        project.rating_count = rating_summary['rating_count']
        project.rounded_stars = rating_summary['rounded_stars']
        project.has_ratings = rating_summary['has_ratings']
        project.star_css_class = rating_summary['star_css_class']
        project.participant_students = _project_students(project)
        project.visible_degree = project.degree if _can_view_grade(project, request) else None
        projects_list.append(project)

    sort = sort_get or type or 'newest'
    if sort in ('new', 'newest'):
        projects_list = sorted(projects_list, key=lambda item: item.UploadDate, reverse=True)
    elif sort in ('old', 'oldest'):
        projects_list = sorted(projects_list, key=lambda item: item.UploadDate)
    elif sort == 'rating':
        projects_list = sorted(projects_list, key=lambda item: item.avg_rating, reverse=True)

    data = {
        'univs': universities,
        'majors': majors,
        'years': years,
        'email': request.session.get('email'),
        'fullname': request.session.get('fullname'),
        'userType': request.session.get('userType'),
        'projects': projects_list,
        'universities_count': universities.count(),
        'majors_count': majors.count(),
        'supervisors_count': Supervisor.objects.count(),
        'projects_count': len(projects_list),
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
    if 'email' not in request.session or request.session.get('email') is None:
        return redirect('/error/')
    if request.session.get('userType') != 'student':
        return redirect('/error/')

    student = Student.objects.get(email=request.session['email'])
    projects = Projects.objects.filter(Q(Student_id=student) | Q(collaborators=student)).distinct().order_by('-UploadDate')

    if id is not None:
        project_to_delete = get_object_or_404(projects, id=id)
        project_to_delete.delete()
        return redirect('MyProject')

    count_of_projects = projects.count()
    rating_projects = projects.filter(rates__gt=0).count()
    max_rate = projects.order_by('-rates').first()
    average_rating = (projects.aggregate(total=Sum('rates'))['total'] or 0) / count_of_projects if count_of_projects else 0

    for project in projects:
        project.participant_students = _project_students(project)

    data = {
        'projects': projects,
        'maxRate': max_rate,
        'ava': average_rating,
        'ratingProj': rating_projects,
        'notRating': count_of_projects - rating_projects,
        'countOfprojs': count_of_projects,
        'email': request.session.get('email'),
        'fullname': request.session.get('fullname'),
        'userType': request.session.get('userType'),
    }
    return render(request, 'pages/myproject.html', data)

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
    if request.session.get('userType') != 'student' or not request.session.get('email'):
        return redirect('/login/')

    student = get_object_or_404(Student, email=request.session['email'])
    projects = Projects.objects.filter(Q(Student_id=student) | Q(collaborators=student)).distinct().order_by('-UploadDate')

    details, _ = StudentDetails.objects.get_or_create(studentID=student)

    if request.method == 'POST':
        note = (request.POST.get('note') or '').strip()
        skills_value = (request.POST.get('skills') or '').strip()
        current_password = (request.POST.get('currentPassword') or '').strip()
        new_password = (request.POST.get('newPassword') or '').strip()
        confirm_password = (request.POST.get('sure') or '').strip()

        if note:
            details.notes = note
            details.save(update_fields=['notes'])

        if skills_value:
            existing_skills = set(Skills.objects.filter(StudentDetail=details).values_list('skill', flat=True))
            for item in [skill.strip() for skill in skills_value.split(',') if skill.strip()]:
                if item not in existing_skills:
                    Skills.objects.create(StudentDetail=details, skill=item)

        if current_password and new_password and confirm_password:
            if student.password == current_password and new_password == confirm_password:
                student.password = new_password
                student.save(update_fields=['password'])
                messages.success(request, 'تم تحديث كلمة المرور بنجاح.')
            else:
                messages.error(request, 'تعذر تحديث كلمة المرور. تأكد من البيانات المدخلة.')

        return redirect('studentProfile')

    for project in projects:
        project.participant_students = _project_students(project)
        project.rating_summary = _project_rating_summary(project)
        project.visible_degree = project.degree if _can_view_grade(project, request) else None

    data = {
        'user': student,
        'projects': projects,
        'notes': details.notes,
        'skills': Skills.objects.filter(StudentDetail=details),
        'countOfProjects': projects.count(),
        'fullname': request.session.get('fullname'),
        'email': request.session.get('email'),
        'userType': request.session.get('userType'),
    }

    return render(request, 'pages/Student Profile.html', data)

@csrf_protect
def supervisorDashboard(request):
    if request.session.get('userType') != 'supervisor' or not request.session.get('email'):
        return redirect('/login/')

    user = get_object_or_404(Supervisor, email=request.session['email'])
    years = [year for year in range(datetime.now().year, datetime.now().year - 6, -1)]
    supervised_projects = Projects.objects.filter(supervisor=user).order_by('-requested_at')
    active_projects = supervised_projects.filter(status='accepted', is_completed=False)
    completed_projects = supervised_projects.filter(is_completed=True)
    pending_requests = supervised_projects.filter(status='pending', is_completed=False)

    avg_rating = supervised_projects.aggregate(avg=Avg('rates'))['avg'] or 0

    featured_projects = []
    for project in active_projects[:6]:
        project.participant_students = _project_students(project)
        project.rating_summary = _project_rating_summary(project)
        featured_projects.append(project)

    data = {
        'majors': Major.objects.all(),
        'years': years,
        'projects': featured_projects,
        'total_projects': supervised_projects.count(),
        'pending_projects': pending_requests.count(),
        'accepted_projects': active_projects.count(),
        'rejected_projects': supervised_projects.filter(status='rejected').count(),
        'completed_projects': completed_projects.count(),
        'incoming_requests_count': pending_requests.count(),
        'avg_rating': round(avg_rating, 2),
        'fullname': request.session.get('fullname'),
        'email': request.session.get('email'),
        'userType': request.session.get('userType')
    }

    return render(request, 'pages/Supervisor Dashboard.html', data)

@csrf_protect
def ProjectEvaluationForm(request, id):
    if 'email' not in request.session or request.session.get('userType') != 'supervisor':
        return redirect('/login/')

    project = get_object_or_404(Projects, id=id)
    supervisor = Supervisor.objects.get(email=request.session['email'])
    can_manage_final_score = _can_manage_final_score(project, supervisor)

    if request.method == 'POST' and request.POST.get('saveRating') is not None:
        try:
            star_rating = int(request.POST.get('star_rating') or 0)
        except ValueError:
            star_rating = 0

        if star_rating < 1 or star_rating > 5:
            messages.error(request, 'Please choose a star rating before saving.')
            next_url = request.POST.get('next') or ''
            if next_url:
                return redirect(next_url)
            return redirect('ProjectEvaluationForm', id=project.id)

        score_value = star_rating * 20
        Ratings.objects.update_or_create(
            ProjectID=project,
            SupervisorID=supervisor,
            defaults={
                'Creativity': score_value,
                'Implementation': score_value,
                'Functionality': score_value,
                'Interface': score_value,
                'notes': None,
            }
        )

        if can_manage_final_score:
            degree_value = request.POST.get('degree', '').strip()
            if degree_value:
                try:
                    project.degree = float(degree_value)
                except ValueError:
                    messages.error(request, 'Final score must be a valid number.')
                    next_url = request.POST.get('next') or ''
                    if next_url:
                        return redirect(next_url)
                    return redirect('ProjectEvaluationForm', id=project.id)
            project.final_score_visible = request.POST.get('final_score_visible') == 'on'
            project.save(update_fields=['degree', 'final_score_visible'])

        messages.success(request, 'Rating saved successfully.')
        next_url = request.POST.get('next') or ''
        if next_url:
            return redirect(next_url)
        return redirect('ProjectEvaluationForm', id=project.id)

    supervisor_rating = Ratings.objects.filter(ProjectID=project, SupervisorID=supervisor).first()
    selected_stars = 0
    if supervisor_rating:
        selected_stars = round(_average_rating_value(supervisor_rating) / 20)

    project_rating_summary = _project_rating_summary(project)

    context = {
        'project': project,
        'participant_students': _project_students(project),
        'selected_stars': selected_stars,
        'project_rating_summary': project_rating_summary,
        'can_manage_final_score': can_manage_final_score,
        'show_final_score': _can_view_grade(project, request) and project.degree is not None,
        'is_popup': request.GET.get('popup') == '1',
        'email': request.session.get('email'),
        'fullname': request.session.get('fullname'),
        'userType': request.session.get('userType'),
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
    projects = Projects.objects.filter(supervisor=supervisor, status='accepted', is_completed=False).order_by('-requested_at')
    # او لو تريد رؤية كل الحالات: Projects.objects.filter(supervisor=supervisor).order_by('-requested_at')

    for project in projects:
        project.participant_students = _project_students(project)

    context = {'projects': projects, 'userType': 'supervisor', 'email': request.session.get('email'), 'fullname': request.session.get('fullname')}
    return render(request, "pages/supervisor_projects.html", context)




def student_requests(request):
    if 'email' not in request.session or request.session.get('userType') != 'supervisor':
        return redirect('/login/')

    supervisor = Supervisor.objects.get(email=request.session['email'])
    all_supervisor_projects = Projects.objects.filter(supervisor=supervisor)
    projects = all_supervisor_projects.filter(status__in=['pending', 'rejected'], is_completed=False).order_by('-requested_at')

    for project in projects:
        project.participant_students = _project_students(project)
        project.request_submission = _parse_request_submission(project)

    context = {
        'projects': projects,
        'supervisor': supervisor,
        'total_projects_count': all_supervisor_projects.count(),
        'pending_projects_count': all_supervisor_projects.filter(status='pending', is_completed=False).count(),
        'accepted_projects_count': all_supervisor_projects.filter(status='accepted', is_completed=False).count(),
        'rejected_projects_count': all_supervisor_projects.filter(status='rejected', is_completed=False).count(),
        'fullname': request.session.get('fullname'),
        'email': request.session.get('email'),
        'userType': request.session.get('userType'),
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
@csrf_protect
def complete_project(request, project_id):
    project = get_object_or_404(Projects, id=project_id)
    user_email = request.session.get('email')
    user_type = request.session.get('userType')

    student_user = None
    supervisor_user = None
    allowed = False

    if user_email and user_type == 'student':
        try:
            student_user = Student.objects.get(email=user_email)
            allowed = _is_project_participant(project, student_user)
        except Student.DoesNotExist:
            student_user = None

    if user_email and user_type == 'supervisor':
        try:
            supervisor_user = Supervisor.objects.get(email=user_email)
            allowed = bool(project.supervisor_id and project.supervisor_id == supervisor_user.id)
        except Supervisor.DoesNotExist:
            supervisor_user = None

    if not allowed:
        return redirect('/error/')

    can_unlock_final_stage = bool(user_type == 'supervisor' and _can_manage_final_score(project, supervisor_user) and not project.is_completed)
    can_upload_final_data = bool(user_type == 'student' and _is_project_participant(project, student_user) and project.edits_approved and not project.is_completed)
    can_send_updates = not project.is_completed
    is_read_only_participant = bool(user_type == 'student' and project.is_completed)

    if request.method == 'POST':
        if request.POST.get('approve_edits') is not None:
            if not can_unlock_final_stage:
                messages.error(request, 'You do not have permission to unlock final submission.')
            else:
                project.edits_approved = True
                project.save(update_fields=['edits_approved'])
                messages.success(request, 'Final submission stage has been unlocked for students.')
            return redirect('complete_project', project_id=project.id)

        if project.is_completed:
            messages.warning(request, 'This project is finished, so no more messages or uploads are allowed.')
            return redirect('complete_project', project_id=project.id)

        if request.POST.get('send_update') is not None:
            text = request.POST.get('update_message_text', '').strip()
            file = request.FILES.get('update_file')

            if not text and not file:
                messages.warning(request, 'Cannot send an empty message.')
                return redirect('complete_project', project_id=project.id)

            if file and not _is_word_document(file):
                messages.error(request, 'Message attachments must be Word files only (.doc or .docx).')
                return redirect('complete_project', project_id=project.id)

            msg = ProjectConversationMessage(project=project, text=text)
            if user_type == 'student' and student_user:
                msg.sender_student = student_user
            elif user_type == 'supervisor' and supervisor_user:
                msg.sender_supervisor = supervisor_user
            if file:
                msg.attachment = file
            msg.save()
            messages.success(request, 'Message sent successfully.')
            return redirect('complete_project', project_id=project.id)

        if request.POST.get('save_data') is not None:
            if not can_upload_final_data:
                messages.warning(request, 'Final files can only be uploaded by participating students after supervisor approval.')
                return redirect('complete_project', project_id=project.id)

            word_file = request.FILES.get('finalWordFile')
            zip_file = request.FILES.get('finalZipFile')
            video_file = request.FILES.get('videoFile')
            image_files = request.FILES.getlist('ImageFile')

            if word_file and not _is_word_document(word_file):
                messages.error(request, 'Final document must be a Word file.')
                return redirect('complete_project', project_id=project.id)
            if zip_file and not _is_zip_document(zip_file):
                messages.error(request, 'Project code file must be a ZIP archive.')
                return redirect('complete_project', project_id=project.id)
            if video_file and not _is_video_file(video_file):
                messages.error(request, 'Uploaded video type is not supported.')
                return redirect('complete_project', project_id=project.id)
            for img in image_files:
                if not _is_image_file(img):
                    messages.error(request, 'One of the uploaded images is not supported.')
                    return redirect('complete_project', project_id=project.id)

            if word_file:
                project.final_word_file = word_file
            if zip_file:
                project.final_zip_file = zip_file
            if word_file or zip_file:
                project.save(update_fields=['final_word_file', 'final_zip_file'])

            if video_file:
                ProjectMedia.objects.create(ProjectID=project, vedio=video_file)
            for img in image_files:
                ProjectPictures.objects.create(ProjectID=project, image=img)

            messages.success(request, 'Final submission files were saved successfully.')
            return redirect('complete_project', project_id=project.id)

        if request.POST.get('finish_project') is not None and user_type == 'supervisor' and supervisor_user:
            project.is_published = True
            project.status = 'accepted'
            project.edits_approved = True
            project.is_completed = True
            project.UploadDate = timezone.now()
            project.save()
            messages.success(request, 'Project was fully completed and published successfully.')
            return redirect('BrowseProjects')

    messages_qs = project.messages.all().order_by('created_at')
    pics = ProjectPictures.objects.filter(ProjectID=project)
    videos = ProjectMedia.objects.filter(ProjectID=project)

    context = {
        'project': project,
        'messages': messages_qs,
        'videos': videos,
        'pics': pics,
        'user_type': user_type,
        'fullname': request.session.get('fullname'),
        'email': user_email,
        'participant_students': _project_students(project),
        'can_send_updates': can_send_updates,
        'can_upload_final_data': can_upload_final_data,
        'can_unlock_final_stage': can_unlock_final_stage,
        'is_read_only_participant': is_read_only_participant,
        'show_final_score': _can_view_grade(project, request) and project.degree is not None,
        'final_word_file': project.final_word_file,
        'final_zip_file': project.final_zip_file,
        'pdf': project.pdf_file,
    }
    return render(request, 'pages/complete_project.html', context)












