from django.db import models
from datetime import datetime
from django.utils import timezone
# Create your models here.

class University(models.Model):
    univ_name = models.CharField(max_length=50)
    
    def __str__(self):
        return self.univ_name

class Major(models.Model):
    major_name = models.CharField(max_length=50)
    def __str__(self):
        return self.major_name

class BaseUser(models.Model):
    fullname = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True  # هذا لن ينشئ جدولاً لهذا الموديل
        verbose_name = 'User'
        verbose_name_plural = 'Users'

class Student(BaseUser):
    student_id = models.CharField(max_length=20)
    grade_year = models.IntegerField()
    department = models.ForeignKey(Major , on_delete=models.CASCADE)
    university = models.ForeignKey(University , on_delete=models.CASCADE)

    def __str__(self):
        return self.fullname
    
    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'

class Supervisor(BaseUser):
    position = models.CharField(max_length=100)
    department = models.ForeignKey(Major , on_delete=models.CASCADE)
    university = models.ForeignKey(University , on_delete=models.CASCADE , blank=True , null=True)

    def __str__(self):
        return self.fullname
    
    class Meta:
        verbose_name = 'Supervisor'
        verbose_name_plural = 'Supervisors'

class Projects(models.Model):
    ProjectName = models.CharField(max_length=150)
    UniversityID = models.ForeignKey(University , on_delete=models.CASCADE)
    MajorID = models.ForeignKey(Major , on_delete= models.CASCADE)
    
    # الحقل القديم: صاحب المشروع الأساسي (محفوظ كما كان) — احتفظنا به لأجل التوافق
    Student_id = models.ForeignKey(Student , on_delete=models.CASCADE , blank=True , null=True)

    # ======= إضافات جديدة (لتمكين اختيار زميل/مشرف وطلبات معلقة) =======
    # collaborators: يسمح للطالب باختيار زميل مشروع (اختياري، يمكن أن يحتوي على صفر أو أكثر)
    collaborators = models.ManyToManyField(Student, blank=True, related_name='collaborations')
    # تعليق: هذا حقل جديد؛ لا يلغي Student_id الموجود (الذي يبقى كـ "الرافع/المالك" الافتراضي).

    # supervisor: إمكانية تعيين مشرف إلى المشروع (قد يختاره الطالب عند الرفع)
    supervisor = models.ForeignKey(Supervisor, on_delete=models.SET_NULL, null=True, blank=True, related_name='supervised_projects')
    # تعليق: حقل جديد؛ إذا حُذف المشرف، نبقي المشروع (SET_NULL) بدلاً من حذفه.

    # وقت/سنة المشروع والتفاصيل والملفات كما كانت
    yearOfProject = models.IntegerField()
    Description = models.TextField(blank=True , null=True)
    FullDescription = models.TextField(blank=True , null=True)
    pdf_file = models.FileField(upload_to='PDF/',blank=True , null=True)
    UploadDate = models.DateTimeField(auto_now_add=True)
    rates = models.FloatField( default=0.0 , blank=True , null=True)
    ProjectType = models.CharField( max_length=50 , blank=True , null=True)
    degree = models.FloatField(null = True , blank=True)
    
    # status: حالة المشروع (pending, accepted, rejected) — أضفت قيمة افتراضية 'pending'
    status = models.CharField(max_length=50, null=True, blank=True, default='pending')
    # تعليق: تم إضافة default='pending' حتى تظهر المشاريع كـ "قيد الانتظار" تلقائياً عند الرفع.

    # classification: أصلحت المكان والاسم داخل الكلاس (كان خارج الكلاس سابقاً)
    classification = models.CharField(max_length=50, null=True, blank=True)
    # تعليق: هذا نفس الحقل السابق لكن مصحح مكانه وإملاؤه (كان "classfication" خارج الكلاس).

    # requested_at: وقت طلب أو رفع المشروع (مفيد لآلة "تجاهل بعد X أيام")
    requested_at = models.DateTimeField(default=timezone.now)

    # تعليق: تم إضافة هذا الحقل لتحديد زمن الطلب حتى نقدر نطبق منطق التجاهل التلقائي حسب الدرجة الزمنية.

    def __str__(self):
        return self.ProjectName

class Ratings(models.Model):
    Creativity = models.IntegerField() # الإبداع
    Implementation = models.IntegerField() # التنفيذ
    Functionality = models.IntegerField() # الوظائف
    Interface = models.IntegerField()
    ProjectID = models.ForeignKey(Projects, on_delete=models.CASCADE)
    SupervisorID  = models.ForeignKey(Supervisor , on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True , blank=True , null=True)
    notes = models.TextField(blank=True , null=True)
    
class Comments(models.Model):
    comment = models.TextField()
    projectID = models.ForeignKey(Projects, on_delete=models.CASCADE)
    SupervisorID = models.ForeignKey(Supervisor , on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, blank=True , null=True)

class ProjectPictures(models.Model):
    ProjectID = models.ForeignKey(Projects, on_delete=models.CASCADE)
    image = models.FileField(upload_to='images/')

class ProjectMedia(models.Model):
    ProjectID = models.ForeignKey(Projects, on_delete=models.CASCADE)
    vedio = models.FileField(upload_to='videos/')

class AdminUser(BaseUser):
    def __str__(self):
        return self.fullname
    
class StudentDetails(models.Model):
    studentID = models.OneToOneField(Student , on_delete=models.CASCADE)
    notes = models.TextField(null= True , blank=True)

class Skills(models.Model):
    StudentDetail = models.ForeignKey(StudentDetails, on_delete=models.CASCADE)
    skill = models.CharField(max_length=50 , null= True , blank=True)
