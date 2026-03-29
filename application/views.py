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
        if request.POST.get('loginBtn') is not None:
            email = request.POST.get('email')
            password = request.POST.get('password')

            student = Student.objects.filter(email=email).first()
            if student:
                if not student.is_active:
                    return render(request, 'pages/login.html', {'msg': 'تم تعطيل هذا الحساب من قبل الإدارة.', 'unvs': universities, 'majors': majors})
                if student.password == password:
                    request.session['email'] = email
                    request.session['fullname'] = student.fullname
                    request.session['userType'] = 'student'
                    return redirect('/')
                return render(request, 'pages/login.html', {'msg': 'كلمة المرور غير صحيحة للطالب', 'unvs': universities, 'majors': majors})

            supervisor = Supervisor.objects.filter(email=email).first()
            if supervisor:
                if supervisor.approval_status == 'pending':
                    return render(request, 'pages/login.html', {'msg': 'طلب إنشاء هذا الحساب ما زال قيد المراجعة من المسؤول العام.', 'unvs': universities, 'majors': majors})
                if supervisor.approval_status == 'rejected':
                    return render(request, 'pages/login.html', {'msg': 'تم رفض طلب إنشاء حساب المشرف. يرجى مراجعة المسؤول العام.', 'unvs': universities, 'majors': majors})
                if not supervisor.is_active:
                    return render(request, 'pages/login.html', {'msg': 'تم تعطيل هذا الحساب من قبل الإدارة.', 'unvs': universities, 'majors': majors})
                if supervisor.password == password:
                    request.session['email'] = email
                    request.session['fullname'] = supervisor.fullname
                    request.session['userType'] = 'supervisor'
                    return redirect('/')
                return render(request, 'pages/login.html', {'msg': 'كلمة المرور غير صحيحة للمشرف', 'unvs': universities, 'majors': majors})

            admin_user = AdminUser.objects.filter(email=email).first()
            if admin_user:
                if admin_user.password == password:
                    request.session['email'] = email
                    request.session['fullname'] = admin_user.fullname
                    request.session['userType'] = 'admin'
                    return redirect('/adminDashboard/')
                return render(request, 'pages/login.html', {'msg': 'كلمة المرور غير صحيحة للمسؤول العام', 'unvs': universities, 'majors': majors})

            return render(request, 'pages/login.html', {'msg': 'هذا الإيميل غير مسجل في النظام', 'unvs': universities, 'majors': majors})

        elif request.POST.get('createAccount') is not None:
            userType = request.POST.get('type')
            email = request.POST.get('email')
            password = request.POST.get('password')
            rpassword = request.POST.get('rpassword')

            if password != rpassword:
                return render(request, 'pages/login.html', {'msg': 'كلمات المرور غير متطابقة', 'unvs': universities, 'majors': majors})

            existing_rejected_supervisor = Supervisor.objects.filter(email=email, approval_status='rejected').first()
            if Student.objects.filter(email=email).exists() or AdminUser.objects.filter(email=email).exists() or Supervisor.objects.filter(email=email).exclude(approval_status='rejected').exists():
                return render(request, 'pages/login.html', {'msg': 'الإيميل مسجل مسبقاً، حاول الدخول', 'unvs': universities, 'majors': majors})

            if userType == 'student':
                try:
                    mj_obj = Major.objects.get(id=int(request.POST.get('StudentMajor')))
                    student_id_value = (request.POST.get('studentID') or '').strip()
                    if Student.objects.filter(student_id=student_id_value).exists():
                        return render(request, 'pages/login.html', {'msg': 'الرقم الجامعي مستخدم مسبقاً، يرجى إدخال رقم جامعي مختلف.', 'unvs': universities, 'majors': majors})
                    unv_obj = University.objects.get(id=int(request.POST.get('StudentUniversity')))
                    student = Student.objects.create(
                        fullname=request.POST.get('StudentFullName'),
                        password=password,
                        email=email,
                        student_id=student_id_value,
                        grade_year=request.POST.get('graduationYear'),
                        department=mj_obj,
                        university=unv_obj,
                        is_active=True,
                    )
                    StudentDetails.objects.create(studentID=student)
                    request.session['email'] = email
                    request.session['fullname'] = student.fullname
                    request.session['userType'] = 'student'
                    return redirect('/')
                except Exception:
                    return render(request, 'pages/login.html', {'msg': 'تأكد من اختيار الجامعة والتخصص وملء كافة الحقول', 'unvs': universities, 'majors': majors})

            elif userType == 'supervisor':
                try:
                    university = University.objects.get(id=int(request.POST.get('supervisorUniversity')))
                    department = Major.objects.get(id=int(request.POST.get('supervisordepartment')))
                    supervisor_id_card = request.FILES.get('supervisorUniversityCard')
                    if existing_rejected_supervisor:
                        existing_rejected_supervisor.fullname = request.POST.get('supervisorName')
                        existing_rejected_supervisor.password = password
                        existing_rejected_supervisor.position = 'Supervisor'
                        existing_rejected_supervisor.department = department
                        existing_rejected_supervisor.university = university
                        if supervisor_id_card:
                            existing_rejected_supervisor.university_id_card = supervisor_id_card
                        existing_rejected_supervisor.approval_status = 'pending'
                        existing_rejected_supervisor.is_active = True
                        existing_rejected_supervisor.save()
                        messages.success(request, 'تم تحديث طلب المشرف وإعادة إرساله بنجاح، وهو الآن بانتظار موافقة المسؤول العام.')
                    else:
                        Supervisor.objects.create(
                            fullname=request.POST.get('supervisorName'),
                            email=email,
                            password=password,
                            position='Supervisor',
                            department=department,
                            university=university,
                            university_id_card=supervisor_id_card,
                            approval_status='pending',
                            is_active=True,
                        )
                        messages.success(request, 'تم إرسال طلب إنشاء حساب المشرف بنجاح، وهو الآن بانتظار موافقة المسؤول العام.')
                    return redirect('login')
                except Exception:
                    return render(request, 'pages/login.html', {'msg': 'خطأ في إنشاء حساب المشرف. تأكد من البيانات ورفع البطاقة الجامعية.', 'unvs': universities, 'majors': majors})

        return render(request, 'pages/login.html', {'unvs': universities, 'majors': majors})

    return render(request, 'pages/login.html', {'unvs': universities, 'majors': majors})
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
    has_final_submission = bool(
        project.final_word_file or project.final_zip_file or project.pdf_file or
        pictures.exists() or videos.exists()
    )

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
        'selected_stars': selected_stars,
        'can_manage_final_score': can_manage_final_score,
        'final_word_file': project.final_word_file,
        'final_zip_file': project.final_zip_file,
        'has_final_submission': has_final_submission,
    }

    return render(request, 'pages/Project Details.html', data)
@csrf_protect
def UploadProject(request):
    if 'email' not in request.session or request.session.get('userType') != 'student':
        return redirect('login')

    student_obj = Student.objects.get(email=request.session['email'])
    edit_project = None
    edit_id = request.GET.get('edit') or request.POST.get('project_id')
    if edit_id:
        candidate_project = Projects.objects.filter(id=edit_id, status='rejected', is_completed=False).first()
        if candidate_project and _is_project_participant(candidate_project, student_obj):
            edit_project = candidate_project

    if request.method == "POST":
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
            collab_ids = [cid for cid in request.POST.getlist('collaborator') if cid]

            try:
                project_year_value = int(project_year)
            except (TypeError, ValueError):
                messages.error(request, 'يرجى اختيار سنة مشروع صحيحة.')
                return redirect('UploadProject')

            current_year = timezone.now().year
            if project_year_value < 2000 or project_year_value > current_year + 1:
                messages.error(request, 'سنة المشروع غير منطقية. اختر سنة صحيحة من القائمة.')
                return redirect('UploadProject')

            if project_type == 'حلقة بحث' and collab_ids:
                messages.error(request, 'في حلقة البحث يجب أن يكون الطلب لطالب واحد فقط دون إضافة زملاء.')
                return redirect('UploadProject')

            if project_type != 'حلقة بحث' and len(collab_ids) > 2:
                messages.error(request, 'يمكن إضافة طالبين فقط مع الطالب الأساسي، ليصبح العدد الإجمالي 3 طلاب كحد أقصى.')
                return redirect('UploadProject')

            major = None
            try:
                if major_id:
                    major = Major.objects.get(id=int(major_id))
            except Exception:
                major = None

            sup = None
            try:
                if supervisor_id:
                    sup = Supervisor.objects.get(id=int(supervisor_id))
            except Exception:
                sup = None

            if edit_project:
                project = edit_project
                project.ProjectName = title_ar or title_en or 'مشروع بدون عنوان'
                project.UniversityID = project.Student_id.university if project.Student_id else student_obj.university
                project.MajorID = major if major else (Major.objects.first() if Major.objects.exists() else None)
                project.yearOfProject = project_year_value
                project.Description = idea or ''
                project.FullDescription = (what or '') + '\n\nMILESTONES:\n' + (stages or '')
                project.ProjectType = project_type or ''
                project.status = 'pending'
                project.requested_at = timezone.now()
                project.rejection_reason = None
                project.resubmitted_at = timezone.now()
                project.supervisor = sup
                project.edits_approved = False
                project.save()
                project.collaborators.clear()
                success_message = 'تم تعديل بيانات الطلب وإعادة إرساله بنجاح.'
            else:
                project = Projects.objects.create(
                    ProjectName=title_ar or title_en or 'مشروع بدون عنوان',
                    UniversityID=student_obj.university,
                    MajorID=major if major else (Major.objects.first() if Major.objects.exists() else None),
                    Student_id=student_obj,
                    yearOfProject=project_year_value,
                    Description=idea or '',
                    FullDescription=(what or '') + '\n\nMILESTONES:\n' + (stages or ''),
                    ProjectType=project_type or '',
                    status='pending',
                    requested_at=timezone.now(),
                    supervisor=sup
                )
                success_message = 'تم إرسال الطلب بنجاح.'

            for cid in collab_ids:
                try:
                    s = Student.objects.get(id=int(cid))
                    project.collaborators.add(s)
                except Exception:
                    pass

            messages.success(request, success_message)
            return redirect('MyProject')

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

    supervisors = Supervisor.objects.filter(is_active=True, approval_status='approved')
    all_students = Student.objects.filter(is_active=True).exclude(email=student_obj.email)
    majors = Major.objects.all()
    years = [year for year in range(datetime.now().year + 1, datetime.now().year - 6, -1)]
    selected_collaborator_ids = []
    request_data = {
        'department': '',
        'projectType': '',
        'projectYear': '',
        'title_ar': '',
        'title_en': '',
        'supervisor': '',
        'idea_summary': '',
        'what_will_be_done': '',
        'project_stages': '',
    }

    if edit_project:
        selected_collaborator_ids = list(edit_project.collaborators.values_list('id', flat=True))
        what_will_be_done = edit_project.FullDescription or ''
        project_stages = ''
        if 'MILESTONES:\n' in what_will_be_done:
            what_will_be_done, project_stages = what_will_be_done.split('MILESTONES:\n', 1)
        request_data = {
            'department': str(edit_project.MajorID_id or ''),
            'projectType': edit_project.ProjectType or '',
            'projectYear': str(edit_project.yearOfProject or ''),
            'title_ar': edit_project.ProjectName or '',
            'title_en': edit_project.ProjectName or '',
            'supervisor': str(edit_project.supervisor_id or ''),
            'idea_summary': edit_project.Description or '',
            'what_will_be_done': what_will_be_done.strip(),
            'project_stages': project_stages.strip(),
        }

    return render(request, 'pages/Upload -project.html', {
        'user': student_obj.fullname,
        'supervisors': supervisors,
        'all_students': all_students,
        'majors': majors,
        'years': years,
        'fullname': request.session.get('fullname'),
        'email': request.session.get('email'),
        'userType': request.session.get('userType'),
        'edit_project': edit_project,
        'request_data': request_data,
        'selected_collaborator_ids': selected_collaborator_ids,
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
                messages.success(request, 'تم قبول الطلب ونقله إلى المشاريع الإشرافية.')
                return redirect('supervisor_projects')
            elif action == 'reject':
                rejection_reason = (request.POST.get('rejection_reason') or '').strip()
                if not rejection_reason:
                    messages.error(request, 'يجب كتابة سبب الرفض قبل إرسال القرار.')
                    return redirect('projectDetails', id=project.id)
                project.status = 'rejected'
                project.edits_approved = False
                project.is_completed = False
                project.rejection_reason = rejection_reason
                project.save(update_fields=['status', 'edits_approved', 'is_completed', 'rejection_reason'])
                messages.warning(request, 'تم رفض الطلب مع حفظ سبب الرفض للطلاب.')
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
        project.can_leave = bool(project.Student_id_id != student.id and project.collaborators.filter(id=student.id).exists() and not project.is_completed)
        project.can_resubmit = bool(_is_project_participant(project, student) and project.status == 'rejected' and not project.is_completed)

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
def leave_project(request, project_id):
    if request.session.get('userType') != 'student' or not request.session.get('email'):
        return redirect('login')

    student = Student.objects.get(email=request.session['email'])
    project = get_object_or_404(Projects, id=project_id)

    if project.Student_id_id == student.id:
        messages.error(request, 'الطالب الأساسي الذي أرسل الطلب لا يمكنه الانسحاب من المشروع.')
        return redirect('MyProject')

    if project.is_completed:
        messages.error(request, 'لا يمكن الانسحاب بعد اكتمال المشروع.')
        return redirect('MyProject')

    if not project.collaborators.filter(id=student.id).exists():
        messages.error(request, 'الانسحاب متاح فقط للطلاب المشاركين المدعوين في هذا المشروع.')
        return redirect('MyProject')

    project.collaborators.remove(student)
    messages.success(request, 'تم إلغاء مشاركتك في هذا المشروع.')
    return redirect('MyProject')

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
    if request.session.get('userType') != 'admin' or not request.session.get('email'):
        return redirect('/login/')

    role_filter = (request.GET.get('role') or 'all').strip()
    search_query = (request.GET.get('q') or '').strip()

    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')

        if action == 'approve_supervisor' and user_id:
            supervisor = get_object_or_404(Supervisor, id=user_id)
            supervisor.approval_status = 'approved'
            supervisor.is_active = True
            supervisor.save(update_fields=['approval_status', 'is_active'])
            messages.success(request, 'تمت الموافقة على حساب المشرف بنجاح.')
            return redirect('AdminDashboard')

        if action == 'reject_supervisor' and user_id:
            supervisor = get_object_or_404(Supervisor, id=user_id)
            supervisor.approval_status = 'rejected'
            supervisor.save(update_fields=['approval_status'])
            messages.success(request, 'تم رفض طلب المشرف.')
            return redirect('AdminDashboard')

        if action == 'toggle_student' and user_id:
            student = get_object_or_404(Student, id=user_id)
            student.is_active = not student.is_active
            student.save(update_fields=['is_active'])
            messages.success(request, 'تم تحديث حالة حساب الطالب.')
            return redirect(f"/adminDashboard/?role={role_filter}&q={search_query}")

        if action == 'toggle_supervisor' and user_id:
            supervisor = get_object_or_404(Supervisor, id=user_id)
            supervisor.is_active = not supervisor.is_active
            supervisor.save(update_fields=['is_active'])
            messages.success(request, 'تم تحديث حالة حساب المشرف.')
            return redirect(f"/adminDashboard/?role={role_filter}&q={search_query}")

    students_qs = Student.objects.select_related('university', 'department').all().order_by('-created_at')
    supervisors_qs = Supervisor.objects.select_related('university', 'department').all().order_by('-created_at')
    pending_supervisor_requests = supervisors_qs.filter(approval_status='pending')

    if search_query:
        students_qs = students_qs.filter(Q(fullname__icontains=search_query) | Q(email__icontains=search_query))
        supervisors_qs = supervisors_qs.filter(Q(fullname__icontains=search_query) | Q(email__icontains=search_query))

    users = []
    if role_filter in ('all', 'student'):
        for student in students_qs:
            student.role_label = 'طالب'
            student.role_key = 'student'
            users.append(student)
    if role_filter in ('all', 'supervisor'):
        for supervisor in supervisors_qs:
            supervisor.role_label = 'مشرف'
            supervisor.role_key = 'supervisor'
            users.append(supervisor)

    users = sorted(users, key=lambda item: item.created_at, reverse=True)

    data = {
        'countOfUsers': Student.objects.count() + Supervisor.objects.count() + AdminUser.objects.count(),
        'countOfStudents': Student.objects.count(),
        'countOfSupervisor': Supervisor.objects.count(),
        'countOfAdmins': AdminUser.objects.count(),
        'countOfProjects': Projects.objects.count(),
        'countOfRatings': Ratings.objects.count(),
        'countOfUniversities': University.objects.count(),
        'pending_supervisors_count': Supervisor.objects.filter(approval_status='pending').count(),
        'disabled_students_count': Student.objects.filter(is_active=False).count(),
        'disabled_supervisors_count': Supervisor.objects.filter(is_active=False).count(),
    }

    context = {
        'data': data,
        'users': users,
        'pending_supervisor_requests': pending_supervisor_requests,
        'role_filter': role_filter,
        'search_query': search_query,
        'fullname': request.session.get('fullname'),
        'email': request.session.get('email'),
        'userType': request.session.get('userType'),
    }
    return render(request, 'pages/Admin Dashboard.html', context)
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
        project.can_leave = bool(project.Student_id_id != student.id and project.collaborators.filter(id=student.id).exists() and not project.is_completed)
        project.can_resubmit = bool(_is_project_participant(project, student) and project.status == 'rejected' and not project.is_completed)
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
    supervisors = Supervisor.objects.filter(is_active=True, approval_status='approved')
    all_students = Student.objects.filter(is_active=True).exclude(email=student.email)
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
    has_final_submission = bool(
        project.final_word_file or project.final_zip_file or project.pdf_file or
        ProjectMedia.objects.filter(ProjectID=project).exists() or
        ProjectPictures.objects.filter(ProjectID=project).exists()
    )

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
            text_message = request.POST.get('update_message_text', '').strip()
            file = request.FILES.get('update_file')

            if not text_message and not file:
                messages.warning(request, 'Cannot send an empty message.')
                return redirect('complete_project', project_id=project.id)

            if file and not _is_word_document(file):
                messages.error(request, 'Message attachments must be Word files only (.doc or .docx).')
                return redirect('complete_project', project_id=project.id)

            msg = ProjectConversationMessage(project=project, text=text_message)
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
            if not has_final_submission:
                messages.error(request, 'لا يمكن إنهاء المشروع قبل أن يرفع الطلاب البيانات النهائية للمشروع.')
                return redirect('complete_project', project_id=project.id)

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
        'has_final_submission': has_final_submission,
    }
    return render(request, 'pages/complete_project.html', context)








