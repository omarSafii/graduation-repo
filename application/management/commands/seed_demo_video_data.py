from io import BytesIO
import zipfile

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from application.models import (
    Major,
    ProjectConversationMessage,
    ProjectPictures,
    Projects,
    Ratings,
    Skills,
    Student,
    StudentDetails,
    Supervisor,
    University,
)


DEMO_PASSWORD = 'Demo@123'


class Command(BaseCommand):
    help = 'Seeds realistic demo data for recording a practical system flow video.'

    def handle(self, *args, **options):
        universities = self._create_universities()
        majors = self._create_majors()
        supervisors = self._create_supervisors(universities, majors)
        students = self._create_students(universities, majors)
        self._create_projects(students, supervisors, universities, majors)

        self.stdout.write(self.style.SUCCESS('Demo video data created successfully.'))
        self.stdout.write('Student/Supervisor demo password: ' + DEMO_PASSWORD)
        self.stdout.write('General admin: admin@graduation.local / Admin@12345')

    def _create_universities(self):
        data = [
            'جامعة دمشق',
            'الجامعة الافتراضية السورية',
            'جامعة حلب',
        ]
        result = {}
        for name in data:
            result[name], _ = University.objects.get_or_create(univ_name=name)
        return result

    def _create_majors(self):
        data = [
            'هندسة المعلوماتية',
            'هندسة البرمجيات',
            'الذكاء الاصطناعي',
            'نظم المعلومات',
        ]
        result = {}
        for name in data:
            result[name], _ = Major.objects.get_or_create(major_name=name)
        return result

    def _create_supervisors(self, universities, majors):
        data = [
            {
                'fullname': 'د. رنا الخطيب',
                'email': 'rana.khatib.demo@graduation.local',
                'department': majors['هندسة البرمجيات'],
                'university': universities['جامعة دمشق'],
            },
            {
                'fullname': 'د. ياسر حمزة',
                'email': 'yasser.hamza.demo@graduation.local',
                'department': majors['نظم المعلومات'],
                'university': universities['الجامعة الافتراضية السورية'],
            },
            {
                'fullname': 'د. مها العبدالله',
                'email': 'maha.abdullah.demo@graduation.local',
                'department': majors['الذكاء الاصطناعي'],
                'university': universities['جامعة حلب'],
            },
        ]
        result = {}
        for item in data:
            supervisor, _ = Supervisor.objects.update_or_create(
                email=item['email'],
                defaults={
                    'fullname': item['fullname'],
                    'password': DEMO_PASSWORD,
                    'position': 'Supervisor',
                    'department': item['department'],
                    'university': item['university'],
                    'approval_status': 'approved',
                    'is_active': True,
                },
            )
            if not supervisor.university_id_card:
                supervisor.university_id_card.save(
                    self._slug(item['fullname']) + '_id.svg',
                    ContentFile(self._id_card_svg(item['fullname'], item['university'].univ_name).encode('utf-8')),
                    save=True,
                )
            result[item['fullname']] = supervisor
        return result

    def _create_students(self, universities, majors):
        data = [
            {
                'fullname': 'أحمد درويش',
                'email': 'ahmad.darwish.demo@graduation.local',
                'student_id': '20201001',
                'grade_year': 5,
                'department': majors['هندسة المعلوماتية'],
                'university': universities['جامعة دمشق'],
                'notes': 'طالب متميز في بناء الأنظمة الطبية وتحليل المتطلبات.',
                'skills': ['Python', 'Django', 'PostgreSQL'],
            },
            {
                'fullname': 'سارة الحسن',
                'email': 'sara.hassan.demo@graduation.local',
                'student_id': '20201002',
                'grade_year': 5,
                'department': majors['هندسة البرمجيات'],
                'university': universities['جامعة دمشق'],
                'notes': 'مهتمة بتجربة المستخدم وتوثيق المشاريع الأكاديمية.',
                'skills': ['UI/UX', 'Figma', 'HTML/CSS'],
            },
            {
                'fullname': 'هادي علي',
                'email': 'hadi.ali.demo@graduation.local',
                'student_id': '20201003',
                'grade_year': 5,
                'department': majors['هندسة المعلوماتية'],
                'university': universities['جامعة دمشق'],
                'notes': 'يركز على البنية الخلفية وأمن البيانات.',
                'skills': ['APIs', 'Security', 'Docker'],
            },
            {
                'fullname': 'نور الخطيب',
                'email': 'nour.khatib.demo@graduation.local',
                'student_id': '20201004',
                'grade_year': 4,
                'department': majors['نظم المعلومات'],
                'university': universities['الجامعة الافتراضية السورية'],
                'notes': 'لديها خبرة جيدة في إنترنت الأشياء ولوحات المتابعة.',
                'skills': ['IoT', 'Dashboards', 'Data Analysis'],
            },
            {
                'fullname': 'لمى عثمان',
                'email': 'lama.othman.demo@graduation.local',
                'student_id': '20201005',
                'grade_year': 4,
                'department': majors['نظم المعلومات'],
                'university': universities['الجامعة الافتراضية السورية'],
                'notes': 'تعمل على جمع البيانات الميدانية وتوثيق الاختبارات.',
                'skills': ['Testing', 'Documentation', 'Presentation'],
            },
            {
                'fullname': 'ريان دياب',
                'email': 'rayan.diab.demo@graduation.local',
                'student_id': '20201006',
                'grade_year': 4,
                'department': majors['الذكاء الاصطناعي'],
                'university': universities['جامعة حلب'],
                'notes': 'مهتم بالنماذج اللغوية العربية وتطبيقاتها التعليمية.',
                'skills': ['NLP', 'LLMs', 'Research'],
            },
            {
                'fullname': 'يزن قاسم',
                'email': 'yazan.qassem.demo@graduation.local',
                'student_id': '20201007',
                'grade_year': 5,
                'department': majors['هندسة البرمجيات'],
                'university': universities['جامعة دمشق'],
                'notes': 'يقود فرق العمل الطلابية ويجيد التخطيط المرحلي.',
                'skills': ['Project Management', 'React', 'Node.js'],
            },
            {
                'fullname': 'دانا المصري',
                'email': 'dana.masri.demo@graduation.local',
                'student_id': '20201008',
                'grade_year': 5,
                'department': majors['هندسة البرمجيات'],
                'university': universities['جامعة دمشق'],
                'notes': 'تركز على الواجهات التفاعلية وتجربة الاستخدام.',
                'skills': ['React', 'Bootstrap', 'Accessibility'],
            },
            {
                'fullname': 'سجى حموي',
                'email': 'saja.hamwi.demo@graduation.local',
                'student_id': '20201009',
                'grade_year': 4,
                'department': majors['نظم المعلومات'],
                'university': universities['الجامعة الافتراضية السورية'],
                'notes': 'تجيد تحويل العمليات الورقية إلى نظم متابعة رقمية.',
                'skills': ['Analysis', 'Wireframing', 'SQL'],
            },
            {
                'fullname': 'عمر نصار',
                'email': 'omar.nassar.demo@graduation.local',
                'student_id': '20201010',
                'grade_year': 4,
                'department': majors['نظم المعلومات'],
                'university': universities['الجامعة الافتراضية السورية'],
                'notes': 'يهتم بتجميع الملاحظات وإدارة بيانات الدعم الفني.',
                'skills': ['Support Systems', 'Excel', 'Reporting'],
            },
            {
                'fullname': 'فرح شهاب',
                'email': 'farah.shehab.demo@graduation.local',
                'student_id': '20201011',
                'grade_year': 5,
                'department': majors['الذكاء الاصطناعي'],
                'university': universities['جامعة حلب'],
                'notes': 'مهتمة بالتنبؤ الأكاديمي وتحليل سلوك الطلاب.',
                'skills': ['Machine Learning', 'Python', 'Pandas'],
            },
            {
                'fullname': 'محمد حلبي',
                'email': 'mohammad.halabi.demo@graduation.local',
                'student_id': '20201012',
                'grade_year': 5,
                'department': majors['الذكاء الاصطناعي'],
                'university': universities['جامعة حلب'],
                'notes': 'متخصص في تجهيز البيانات وبناء النماذج الأولية.',
                'skills': ['Data Prep', 'Scikit-learn', 'Visualization'],
            },
            {
                'fullname': 'مريم مرديني',
                'email': 'mariam.mardini.demo@graduation.local',
                'student_id': '20201013',
                'grade_year': 5,
                'department': majors['هندسة المعلوماتية'],
                'university': universities['جامعة دمشق'],
                'notes': 'تجيد تحليل النصوص العربية وبناء مصنفات مخصصة.',
                'skills': ['Arabic NLP', 'Classification', 'Evaluation'],
            },
        ]

        result = {}
        for item in data:
            student, _ = Student.objects.update_or_create(
                email=item['email'],
                defaults={
                    'fullname': item['fullname'],
                    'password': DEMO_PASSWORD,
                    'student_id': item['student_id'],
                    'grade_year': item['grade_year'],
                    'department': item['department'],
                    'university': item['university'],
                    'is_active': True,
                },
            )
            details, _ = StudentDetails.objects.get_or_create(studentID=student)
            details.notes = item['notes']
            details.save(update_fields=['notes'])
            Skills.objects.filter(StudentDetail=details).delete()
            for skill in item['skills']:
                Skills.objects.create(StudentDetail=details, skill=skill)
            result[item['fullname']] = student
        return result

    def _create_projects(self, students, supervisors, universities, majors):
        now = timezone.now()

        self._upsert_project(
            title='نظام أرشفة السجل الطبي الذكي',
            owner=students['أحمد درويش'],
            collaborators=[students['سارة الحسن'], students['هادي علي']],
            supervisor=supervisors['د. رنا الخطيب'],
            university=universities['جامعة دمشق'],
            major=majors['هندسة المعلوماتية'],
            year=2026,
            project_type='تخرج',
            idea='منصة متكاملة لأرشفة ملفات المرضى مع صلاحيات وصول وتكامل مع العيادات التعليمية.',
            what='بناء نظام ويب لإدارة ملفات المرضى والزيارات والتحاليل والتقارير بشكل رقمي.',
            stages='تحليل المتطلبات\nتصميم قاعدة البيانات\nتنفيذ لوحة التحكم\nاختبارات القبول',
            status='accepted',
            is_published=True,
            is_completed=True,
            edits_approved=True,
            degree=92,
            final_score_visible=True,
            requested_at=now - timezone.timedelta(days=90),
            upload_date=now - timezone.timedelta(days=60),
            final_doc_name='medical_archive_demo.doc',
            final_doc_text='النسخة النهائية لمشروع نظام أرشفة السجل الطبي الذكي.',
            final_zip_name='medical_archive_demo.zip',
            final_zip_files={
                'README.md': '# Smart Medical Archive\nDemo project package.',
                'backend/app.py': 'print("Medical archive demo")\n',
            },
            pictures=[
                ('medical_archive_cover.svg', '#0f6cbd'),
                ('medical_archive_dashboard.svg', '#12a150'),
            ],
            ratings=[
                (supervisors['د. رنا الخطيب'], 95, 90, 94, 93),
                (supervisors['د. ياسر حمزة'], 88, 90, 89, 91),
            ],
        )

        self._upsert_project(
            title='منصة تحليل جودة المياه بالاعتماد على إنترنت الأشياء',
            owner=students['نور الخطيب'],
            collaborators=[students['لمى عثمان']],
            supervisor=supervisors['د. ياسر حمزة'],
            university=universities['الجامعة الافتراضية السورية'],
            major=majors['نظم المعلومات'],
            year=2026,
            project_type='فصلي',
            idea='جمع قراءات الحساسات وعرضها على لوحة متابعة تساعد في كشف التلوث مبكراً.',
            what='ربط بيانات الحساسات بلوحة معلومات تسمح بالمراقبة والتنبيه وإصدار التقارير.',
            stages='تجهيز الحساسات\nتجميع البيانات\nعرض المؤشرات\nالتنبيه وإعداد التقارير',
            status='accepted',
            is_published=True,
            is_completed=True,
            edits_approved=True,
            degree=88,
            final_score_visible=True,
            requested_at=now - timezone.timedelta(days=70),
            upload_date=now - timezone.timedelta(days=40),
            final_doc_name='water_quality_demo.doc',
            final_doc_text='النسخة النهائية لمشروع جودة المياه وإنترنت الأشياء.',
            final_zip_name='water_quality_demo.zip',
            final_zip_files={
                'README.md': '# Water Quality Monitor\nDemo project package.',
                'iot/sensors.txt': 'PH, temperature, turbidity\n',
            },
            pictures=[
                ('water_quality_cover.svg', '#1b9aaa'),
                ('water_quality_metrics.svg', '#f4a261'),
            ],
            ratings=[
                (supervisors['د. ياسر حمزة'], 90, 86, 88, 87),
                (supervisors['د. مها العبدالله'], 84, 85, 83, 86),
            ],
        )

        self._upsert_project(
            title='حلقة بحث حول النماذج اللغوية العربية في التعليم',
            owner=students['ريان دياب'],
            collaborators=[],
            supervisor=supervisors['د. مها العبدالله'],
            university=universities['جامعة حلب'],
            major=majors['الذكاء الاصطناعي'],
            year=2026,
            project_type='حلقة بحث',
            idea='دراسة تطبيقات النماذج اللغوية العربية في التلخيص والتغذية الراجعة التعليمية.',
            what='جمع الأدبيات الحديثة وتحليل النماذج العربية ومقارنة أثرها في دعم التعليم.',
            stages='مراجعة الأدبيات\nتحليل النماذج\nالمقارنة\nصياغة التوصيات',
            status='accepted',
            is_published=True,
            is_completed=True,
            edits_approved=True,
            degree=94,
            final_score_visible=False,
            requested_at=now - timezone.timedelta(days=65),
            upload_date=now - timezone.timedelta(days=30),
            final_doc_name='arabic_llm_research.doc',
            final_doc_text='النسخة النهائية لحلقة البحث حول النماذج اللغوية العربية.',
            final_zip_name='arabic_llm_research.zip',
            final_zip_files={
                'README.md': '# Arabic LLM Research\nResearch notes and references.',
                'notes/references.txt': 'Arabic educational LLM studies\n',
            },
            pictures=[
                ('arabic_llm_cover.svg', '#7b2cbf'),
            ],
            ratings=[
                (supervisors['د. مها العبدالله'], 96, 94, 92, 95),
            ],
        )

        ongoing_project = self._upsert_project(
            title='تطبيق إدارة الأنشطة الطلابية الذكي',
            owner=students['يزن قاسم'],
            collaborators=[students['دانا المصري']],
            supervisor=supervisors['د. رنا الخطيب'],
            university=universities['جامعة دمشق'],
            major=majors['هندسة البرمجيات'],
            year=2026,
            project_type='تخرج',
            idea='تطبيق لإدارة الفعاليات الطلابية والموافقات والحجوزات والتنبيهات.',
            what='إنشاء تجربة استخدام متكاملة لتنظيم الأنشطة ومتابعة الموافقات والإشعارات.',
            stages='تحليل المستخدمين\nتصميم الواجهات\nتطوير الوظائف الأساسية\nاختبار السيناريوهات',
            status='accepted',
            is_published=False,
            is_completed=False,
            edits_approved=False,
            degree=None,
            final_score_visible=True,
            requested_at=now - timezone.timedelta(days=20),
            upload_date=now - timezone.timedelta(days=18),
        )
        self._ensure_message(
            ongoing_project,
            sender_student=students['يزن قاسم'],
            text='قمنا بتحديث شاشة إنشاء النشاط وربطناها بإشعارات القبول والرفض. ننتظر ملاحظاتكم على تجربة الاستخدام.',
            attachment_name='activities_update_1.doc',
        )
        self._ensure_message(
            ongoing_project,
            sender_supervisor=supervisors['د. رنا الخطيب'],
            text='الواجهة جيدة، لكن أريد تبسيط خطوات التسجيل بالنشاط وإضافة حالة انتظار واضحة بعد الإرسال.',
            attachment_name='activities_feedback_1.doc',
        )

        self._upsert_project(
            title='لوحة متابعة الأعطال المخبرية',
            owner=students['سجى حموي'],
            collaborators=[students['عمر نصار']],
            supervisor=supervisors['د. ياسر حمزة'],
            university=universities['الجامعة الافتراضية السورية'],
            major=majors['نظم المعلومات'],
            year=2026,
            project_type='فصلي',
            idea='لوحة تشغيل يومية لمتابعة الأعطال المخبرية وطلبات الصيانة وتحديد أولويات المعالجة.',
            what='تطوير نظام بسيط لتتبع الأعطال المفتوحة وتوزيع المهام وإظهار مؤشرات زمن الحل.',
            stages='جمع السيناريوهات\nتصميم الواجهات\nالتجربة الداخلية\nرفع التسليم النهائي',
            status='accepted',
            is_published=False,
            is_completed=False,
            edits_approved=True,
            degree=None,
            final_score_visible=True,
            requested_at=now - timezone.timedelta(days=14),
            upload_date=now - timezone.timedelta(days=12),
        )

        self._upsert_project(
            title='منصة الإرشاد الأكاديمي التنبؤية',
            owner=students['فرح شهاب'],
            collaborators=[students['محمد حلبي']],
            supervisor=supervisors['د. مها العبدالله'],
            university=universities['جامعة حلب'],
            major=majors['الذكاء الاصطناعي'],
            year=2026,
            project_type='تخرج',
            idea='اقتراح مسارات دعم أكاديمي مبكرة للطلاب عبر مؤشرات الأداء والمخاطر.',
            what='تحليل بيانات الحضور والدرجات وبناء نموذج أولي للتوصيات الأكاديمية.',
            stages='فهم المشكلة\nجمع البيانات\nالنموذج الأولي\nعرض النتائج',
            status='pending',
            is_published=False,
            is_completed=False,
            edits_approved=False,
            degree=None,
            final_score_visible=True,
            requested_at=now - timezone.timedelta(days=5),
            upload_date=now - timezone.timedelta(days=5),
        )

        self._upsert_project(
            title='نظام تصنيف الوثائق القانونية العربية',
            owner=students['مريم مرديني'],
            collaborators=[],
            supervisor=supervisors['د. رنا الخطيب'],
            university=universities['جامعة دمشق'],
            major=majors['هندسة المعلوماتية'],
            year=2026,
            project_type='حلقة بحث',
            idea='تصنيف أولي للمستندات القانونية العربية وفق المجال والجهة ونوع الوثيقة.',
            what='إعداد مجموعة بيانات صغيرة وتجربة خوارزميات تصنيف مناسبة للنصوص العربية.',
            stages='تنظيف البيانات\nالتصنيف الأولي\nمقارنة النماذج\nعرض النتائج',
            status='rejected',
            is_published=False,
            is_completed=False,
            edits_approved=False,
            degree=None,
            final_score_visible=True,
            requested_at=now - timezone.timedelta(days=7),
            upload_date=now - timezone.timedelta(days=7),
            rejection_reason='الفكرة جيدة لكن الوصف الحالي يحتاج إلى توضيح مجموعة البيانات وآلية تقييم النموذج قبل إعادة التقديم.',
        )

    def _upsert_project(self, title, owner, collaborators, supervisor, university, major, year, project_type, idea, what, stages,
                        status, is_published, is_completed, edits_approved, degree, final_score_visible,
                        requested_at, upload_date, rejection_reason=None, final_doc_name=None, final_doc_text=None,
                        final_zip_name=None, final_zip_files=None, pictures=None, ratings=None):
        project, _ = Projects.objects.update_or_create(
            ProjectName=title,
            Student_id=owner,
            defaults={
                'UniversityID': university,
                'MajorID': major,
                'yearOfProject': year,
                'Description': idea,
                'FullDescription': (what or '') + '\n\nMILESTONES:\n' + (stages or ''),
                'ProjectType': project_type,
                'status': status,
                'requested_at': requested_at,
                'supervisor': supervisor,
                'is_published': is_published,
                'is_completed': is_completed,
                'edits_approved': edits_approved,
                'degree': degree,
                'final_score_visible': final_score_visible,
                'rejection_reason': rejection_reason,
                'rates': 4.6 if is_completed else 0,
            },
        )

        project.collaborators.set(collaborators)
        Projects.objects.filter(id=project.id).update(UploadDate=upload_date)

        if final_doc_name and final_doc_text and not project.final_word_file:
            project.final_word_file.save(final_doc_name, ContentFile(final_doc_text.encode('utf-8')), save=False)
        if final_zip_name and final_zip_files and not project.final_zip_file:
            project.final_zip_file.save(final_zip_name, ContentFile(self._build_zip(final_zip_files)), save=False)
        if final_doc_name or final_zip_name:
            project.save()

        if pictures and not ProjectPictures.objects.filter(ProjectID=project).exists():
            for file_name, accent in pictures:
                picture = ProjectPictures(ProjectID=project)
                picture.image.save(file_name, ContentFile(self._project_svg(title, accent).encode('utf-8')), save=True)

        if ratings:
            for supervisor_obj, creativity, implementation, functionality, interface in ratings:
                Ratings.objects.update_or_create(
                    ProjectID=project,
                    SupervisorID=supervisor_obj,
                    defaults={
                        'Creativity': creativity,
                        'Implementation': implementation,
                        'Functionality': functionality,
                        'Interface': interface,
                    },
                )
        return project

    def _ensure_message(self, project, text, attachment_name, sender_student=None, sender_supervisor=None):
        message, created = ProjectConversationMessage.objects.get_or_create(
            project=project,
            text=text,
            sender_student=sender_student,
            sender_supervisor=sender_supervisor,
        )
        if created and not message.attachment:
            message.attachment.save(
                attachment_name,
                ContentFile(('مرفق توضيحي للمحادثة:\n\n' + text).encode('utf-8')),
                save=True,
            )

    def _build_zip(self, files_map):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, content in files_map.items():
                archive.writestr(name, content)
        return buffer.getvalue()

    def _slug(self, value):
        return ''.join(ch.lower() if ch.isalnum() else '_' for ch in value).strip('_') or 'demo'

    def _id_card_svg(self, name, university):
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="700" viewBox="0 0 1200 700">
<rect width="1200" height="700" rx="36" fill="#0f6cbd"/>
<rect x="40" y="40" width="1120" height="620" rx="28" fill="#ffffff"/>
<text x="80" y="150" font-size="54" font-family="Cairo, Arial" fill="#114a7d">بطاقة جامعية تجريبية</text>
<text x="80" y="250" font-size="42" font-family="Cairo, Arial" fill="#15304f">الاسم: {name}</text>
<text x="80" y="330" font-size="38" font-family="Cairo, Arial" fill="#4d647d">الجامعة: {university}</text>
<text x="80" y="410" font-size="34" font-family="Cairo, Arial" fill="#4d647d">الصفة: مشرف أكاديمي</text>
<text x="80" y="560" font-size="30" font-family="Cairo, Arial" fill="#6b7d90">هذه بطاقة تجريبية مخصصة لبيانات العرض العملي.</text>
</svg>'''

    def _project_svg(self, title, accent):
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#0f6cbd"/>
    <stop offset="100%" stop-color="{accent}"/>
  </linearGradient>
</defs>
<rect width="1600" height="900" rx="40" fill="url(#g)"/>
<circle cx="1320" cy="170" r="180" fill="rgba(255,255,255,0.12)"/>
<circle cx="260" cy="760" r="220" fill="rgba(255,255,255,0.08)"/>
<text x="120" y="210" font-size="78" font-family="Cairo, Arial" fill="#ffffff">{title}</text>
<text x="120" y="320" font-size="40" font-family="Cairo, Arial" fill="#e7f3ff">مشروع تجريبي جاهز للعرض العملي داخل المنصة</text>
<rect x="120" y="410" width="520" height="180" rx="28" fill="rgba(255,255,255,0.18)"/>
<text x="160" y="490" font-size="34" font-family="Cairo, Arial" fill="#ffffff">واجهة نهائية</text>
<text x="160" y="545" font-size="28" font-family="Cairo, Arial" fill="#ecf6ff">بطاقات، مؤشرات، وصور مناسبة للتصوير</text>
</svg>'''

