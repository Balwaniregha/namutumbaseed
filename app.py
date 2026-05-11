import base64
import os
from datetime import date, datetime
from functools import wraps
from io import BytesIO

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash

# ------------------------------------------------------------
# App and database setup
# ------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///sms.sqlite3")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

TERMS = ["TERM ONE", "TERM TWO", "TERM THREE"]
YEARS = list(range(2026, 2031))
O_CLASSES = ["S1", "S2", "S3", "S4"]
A_CLASSES = ["S5", "S6"]
STREAMS = ["A", "B", "C"]
DEPARTMENTS = ["Arts", "Sciences"]

O_SUBJECTS = [
    ("MATHEMATICS", "MTC"), ("ENGLISH", "ENG"), ("HISTORY", "HIST"),
    ("GEOGRAPHY", "GEO"), ("PHYSICS", "PHY"), ("CHEMISTRY", "CHE"),
    ("BIOLOGY", "BIO"), ("ENT EDUC", "ENT"), ("KISWAHILI", "KIS"),
    ("PHYSICAL EDUC", "PE"), ("CHRISTIAN R.E", "CRE"), ("LIT IN ENG.", "LIT"),
    ("ICT", "ICT"), ("AGRICULTURE", "AGR"), ("ART & DESIGN", "ART"),
    ("LANG", "LANG"), ("TECH & DESIGN", "TD"),
]

A_SUBJECTS = [
    ("MATHEMATICS", "M"), ("LITERATURE", "LIT"), ("HISTORY", "H"),
    ("GEOGRAPHY", "G"), ("PHYSICS", "P"), ("CHEMISTRY", "C"),
    ("BIOLOGY", "B"), ("AGRICULTURE", "AGR"), ("CHRISTIAN R.E", "CRE"),
    ("FINE ART", "ART"), ("ENT EDUC", "Ent"), ("SUB ICT", "ICT"),
    ("SUB MATH", "SM"), ("GP", "GP"),
]

A_COMBINATION_IGNORE = {"GP"}

# ------------------------------------------------------------
# Models
# ------------------------------------------------------------
class SchoolInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), default="NAMUTUMBA SEED SECONDARY SCHOOL")
    address = db.Column(db.String(200), default="P. O. Box, 53 Busembatia")
    email = db.Column(db.String(120), default="namutumbaseedss@gmail.com")
    phone = db.Column(db.String(120), default="+256 774428462 | +256 757684877")
    motto = db.Column(db.String(120), default="Yes we Can")
    next_term_begins = db.Column(db.String(50), default="25th May 2026")
    headteacher_name = db.Column(db.String(120), default="Ms. Apoo Barbra")
    logo_data = db.Column(db.Text)  # base64 data URL

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default="teacher")  # admin or teacher
    full_name = db.Column(db.String(150))
    initials = db.Column(db.String(20))
    active = db.Column(db.Boolean, default=True)
    assignments = db.relationship("TeacherAssignment", backref="teacher", cascade="all, delete-orphan")

class TeacherAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    section = db.Column(db.String(10), nullable=False)  # O or A
    class_name = db.Column(db.String(10), nullable=False)
    stream = db.Column(db.String(10))
    department = db.Column(db.String(30))
    subject = db.relationship("Subject")

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(30), nullable=False)
    section = db.Column(db.String(10), nullable=False)  # O, A, Both
    is_active = db.Column(db.Boolean, default=True)
    __table_args__ = (UniqueConstraint("name", "section", name="uq_subject_section"),)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lin = db.Column(db.String(80))
    name = db.Column(db.String(150), nullable=False)
    section = db.Column(db.String(10), nullable=False, default="O")  # O or A
    class_name = db.Column(db.String(10), nullable=False, default="S1")
    stream = db.Column(db.String(10))       # only S1-S4
    department = db.Column(db.String(30))   # only S5-S6: Arts/Sciences
    sex = db.Column(db.String(20))
    house = db.Column(db.String(80))
    pay_code = db.Column(db.String(80))
    guardian = db.Column(db.String(150))
    contact = db.Column(db.String(80))
    address = db.Column(db.String(200))
    status = db.Column(db.String(50), default="Active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    subjects = db.relationship("StudentSubject", backref="student", cascade="all, delete-orphan")

class StudentSubject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    subject = db.relationship("Subject")
    __table_args__ = (UniqueConstraint("student_id", "subject_id", name="uq_student_subject"),)

class House(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class TermSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    term = db.Column(db.String(30), nullable=False)
    start_date = db.Column(db.String(30))
    end_date = db.Column(db.String(30))
    next_term_begins = db.Column(db.String(60))
    is_active = db.Column(db.Boolean, default=False)

class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(100))
    phone = db.Column(db.String(80))
    email = db.Column(db.String(120))
    initials = db.Column(db.String(20))

class FeeStructure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(10), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    term = db.Column(db.String(30), nullable=False)
    amount = db.Column(db.Float, default=0)
    __table_args__ = (UniqueConstraint("class_name", "year", "term", name="uq_fee_structure"),)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    term = db.Column(db.String(30), nullable=False)
    pay_date = db.Column(db.String(30), default=lambda: date.today().isoformat())
    amount = db.Column(db.Float, default=0)
    method = db.Column(db.String(60))
    reference = db.Column(db.String(100))
    note = db.Column(db.String(200))
    student = db.relationship("Student")

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    term = db.Column(db.String(30), nullable=False)
    days_present = db.Column(db.Integer, default=0)
    days_absent = db.Column(db.Integer, default=0)
    total_days = db.Column(db.Integer, default=0)
    student = db.relationship("Student")
    __table_args__ = (UniqueConstraint("student_id", "year", "term", name="uq_attendance"),)

class Mark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    term = db.Column(db.String(30), nullable=False)
    # O-Level raw score and marked-out-of for T1-T5
    t1_raw = db.Column(db.String(20)); t1_outof = db.Column(db.String(20))
    t2_raw = db.Column(db.String(20)); t2_outof = db.Column(db.String(20))
    t3_raw = db.Column(db.String(20)); t3_outof = db.Column(db.String(20))
    t4_raw = db.Column(db.String(20)); t4_outof = db.Column(db.String(20))
    t5_raw = db.Column(db.String(20)); t5_outof = db.Column(db.String(20))
    # A-Level construct scores C1-C5; can be 8/20, 3, X, or -
    c1 = db.Column(db.String(30)); c2 = db.Column(db.String(30)); c3 = db.Column(db.String(30)); c4 = db.Column(db.String(30)); c5 = db.Column(db.String(30))
    teacher_initials = db.Column(db.String(20))
    student = db.relationship("Student")
    subject = db.relationship("Subject")
    __table_args__ = (UniqueConstraint("student_id", "subject_id", "year", "term", name="uq_mark"),)

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def school():
    info = SchoolInfo.query.first()
    if not info:
        info = SchoolInfo()
        db.session.add(info)
        db.session.commit()
    return info

@app.context_processor
def inject_globals():
    return {
        "school": school(), "years": YEARS, "terms": TERMS,
        "o_classes": O_CLASSES, "a_classes": A_CLASSES,
        "streams": STREAMS, "departments": DEPARTMENTS,
        "current_user": current_user(), "today": date.today()
    }

def current_user():
    if "user_id" not in session:
        return None
    return User.query.get(session["user_id"])

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user.role != "admin":
            flash("Only the administrator can open that page.", "danger")
            return redirect(url_for("teacher_marks"))
        return fn(*args, **kwargs)
    return wrapper

def is_missing_marker(value):
    if value is None:
        return False
    return str(value).strip().upper() in {"X", "-"}

def is_blank(value):
    return value is None or str(value).strip() == ""

def safe_float(value):
    if is_blank(value) or is_missing_marker(value):
        return None
    try:
        return float(str(value).strip())
    except Exception:
        return None

def fmt_num(value, digits=2):
    if value is None:
        return ""
    try:
        value = float(value)
    except Exception:
        return str(value)
    if abs(value - round(value)) < 0.005:
        return str(int(round(value)))
    return (f"{value:.{digits}f}").rstrip("0").rstrip(".")

def get_mark(student_id, subject_id, year, term):
    return Mark.query.filter_by(student_id=student_id, subject_id=subject_id, year=year, term=term).first()

def student_subject_ids(student):
    return [ss.subject_id for ss in student.subjects]

def combination_for_student(student):
    # S1-S4 have no combinations.
    if student.section != "A":
        return ""
    codes = []
    for ss in sorted(student.subjects, key=lambda x: x.subject.name):
        code = ss.subject.code
        if code not in A_COMBINATION_IGNORE:
            codes.append(code)
    return "/".join(codes) if codes else "Not assigned"

@app.template_filter("combination")
def combination_filter(student):
    return combination_for_student(student)

def o_descriptor(identifier):
    if identifier is None:
        return ""
    if identifier >= 2.5:
        return "Outstanding"
    if identifier >= 1.5:
        return "Moderate"
    if identifier >= 0.9:
        return "Basic"
    return "Elementary"

def o_remark(formative):
    if formative is None:
        return ""
    if formative >= 18:
        return "Outstanding in most or all areas of the topics covered."
    if formative >= 16:
        return "Excellent in most or all areas of the topics covered."
    if formative >= 14:
        return "Very good in several areas of the topics covered."
    if formative >= 12:
        return "Achieved a good number of competencies in the topics covered."
    if formative >= 10:
        return "Achieved a basic number of competencies in the topics covered."
    if formative >= 8:
        return "Achieved the minimal competencies in the topics, just enough to exhibit the required knowledge and skills."
    if formative >= 6:
        return "Achieved some competencies but not enough to make him/her competent across the topics."
    return "Achieved very few or no competencies."

def calc_o_subject(mark):
    displays = []
    values = []
    missed = False
    if not mark:
        return {"scores": ["", "", "", "", ""], "formative": "", "identifier": "", "descriptor": "", "remark": "", "missed": False}
    for i in range(1, 6):
        raw = getattr(mark, f"t{i}_raw")
        outof = getattr(mark, f"t{i}_outof")
        if is_blank(raw) and is_blank(outof):
            displays.append("")
            continue
        if is_missing_marker(raw) or is_missing_marker(outof):
            displays.append("X")
            missed = True
            continue
        raw_f = safe_float(raw)
        out_f = safe_float(outof)
        if raw_f is None or out_f is None or out_f <= 0:
            displays.append("")
            continue
        val = max(0, min(3, raw_f / out_f * 3))
        values.append(val)
        displays.append(fmt_num(val, 2))
    if missed:
        return {"scores": displays, "formative": "X", "identifier": "X", "descriptor": "X", "remark": "Missed Assessment.", "missed": True}
    if not values:
        return {"scores": displays, "formative": "", "identifier": "", "descriptor": "", "remark": "", "missed": False}
    identifier = sum(values) / len(values)
    formative = identifier * 20 / 3
    return {"scores": displays, "formative": fmt_num(formative, 1), "identifier": fmt_num(identifier, 2), "descriptor": o_descriptor(identifier), "remark": o_remark(formative), "missed": False, "formative_num": formative, "identifier_num": identifier}

def a_level_weight_from_entry(value):
    if is_blank(value):
        return None
    if is_missing_marker(value):
        return "MISS"
    s = str(value).strip()
    if "/" in s:
        try:
            a, b = s.split("/", 1)
            a = float(a); b = float(b)
            if b <= 0: return None
            return max(0, min(5, a / b * 5))
        except Exception:
            return None
    try:
        return max(0, min(5, float(s)))
    except Exception:
        return None

def a_grade(weight):
    if weight >= 4.6:
        return "A", "Exceptional"
    if weight >= 3.7:
        return "B", "Outstanding"
    if weight >= 2.8:
        return "C", "Satisfactory"
    if weight >= 1.9:
        return "D", "Basic"
    return "E", "Elementary"

def a_remark(weight):
    if weight >= 4.6:
        return "The learner achieved most or all competencies exceptionally well and is outstanding in most or all areas of the subject."
    if weight >= 3.7:
        return "The learner achieved most or all competencies exceedingly well."
    if weight >= 2.8:
        return "The learner achieved most but not all competencies well and performs very well in a number of areas."
    if weight >= 1.9:
        return "The learner achieved a good number of competencies across the subject."
    return "The learner achieved the bare minimum competencies, just enough to exhibit the required knowledge and skills."

def calc_a_subject(mark):
    if not mark:
        return {"scores": ["", "", "", "", ""], "avg_weight": "", "grade": "", "level": "", "remark": "", "missed": False}
    raw_values = [mark.c1, mark.c2, mark.c3, mark.c4, mark.c5]
    displays = []
    weights = []
    missed = False
    for v in raw_values:
        if is_blank(v):
            displays.append("")
            continue
        if is_missing_marker(v):
            displays.append("-")
            missed = True
            continue
        displays.append(str(v))
        w = a_level_weight_from_entry(v)
        if isinstance(w, (int, float)):
            weights.append(w)
    if missed:
        return {"scores": displays, "avg_weight": "Missed", "grade": "-", "level": "-", "remark": "Learner missed assessment.", "missed": True}
    if not weights:
        return {"scores": displays, "avg_weight": "", "grade": "", "level": "", "remark": "", "missed": False}
    avg = sum(weights) / len(weights)
    grade, level = a_grade(avg)
    return {"scores": displays, "avg_weight": fmt_num(avg, 1), "grade": grade, "level": level, "remark": a_remark(avg), "missed": False, "avg_num": avg, "points": {"A":5, "B":4, "C":3, "D":2, "E":1}[grade]}

def teacher_name_for(subject, section, class_name, stream=None, department=None):
    q = TeacherAssignment.query.filter_by(subject_id=subject.id, section=section, class_name=class_name)
    if section == "O":
        q = q.filter_by(stream=stream)
    else:
        q = q.filter_by(department=department)
    ass = q.first()
    if ass and ass.teacher:
        return ass.teacher.full_name or ass.teacher.username
    return ""

def teacher_initials_for(subject, section, class_name, stream=None, department=None):
    q = TeacherAssignment.query.filter_by(subject_id=subject.id, section=section, class_name=class_name)
    if section == "O":
        q = q.filter_by(stream=stream)
    else:
        q = q.filter_by(department=department)
    ass = q.first()
    if ass and ass.teacher:
        return ass.teacher.initials or ""
    return ""

def subjects_for_report(student):
    if student.section == "O":
        return Subject.query.filter_by(section="O", is_active=True).order_by(Subject.id).all()
    # A-Level: show assigned subjects first, but keep all active A subjects for blank rows when needed
    assigned = [ss.subject for ss in student.subjects if ss.subject.section == "A" and ss.subject.is_active]
    return assigned or Subject.query.filter_by(section="A", is_active=True).order_by(Subject.id).all()

def fee_required(student, year, term):
    fs = FeeStructure.query.filter_by(class_name=student.class_name, year=int(year), term=term).first()
    return fs.amount if fs else 0

def fee_paid(student, year, term):
    total = db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).filter_by(student_id=student.id, year=int(year), term=term).scalar()
    return float(total or 0)

def attendance_for(student, year, term):
    return Attendance.query.filter_by(student_id=student.id, year=int(year), term=term).first()

def students_filter(section=None, class_name=None, stream=None, department=None):
    q = Student.query
    if section: q = q.filter_by(section=section)
    if class_name: q = q.filter_by(class_name=class_name)
    if stream: q = q.filter_by(stream=stream)
    if department: q = q.filter_by(department=department)
    return q.order_by(Student.name).all()

# ------------------------------------------------------------
# Auth and dashboard
# ------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username", "").strip()).first()
        if user and user.active and check_password_hash(user.password_hash, request.form.get("password", "")):
            session["user_id"] = user.id
            if user.role == "teacher":
                return redirect(url_for("teacher_marks"))
            return redirect(url_for("dashboard"))
        flash("Wrong username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    user = current_user()
    if user.role == "teacher":
        return redirect(url_for("teacher_marks"))
    stats = {
        "students": Student.query.count(), "teachers": User.query.filter_by(role="teacher").count(),
        "subjects": Subject.query.filter_by(is_active=True).count(), "payments": Payment.query.count()
    }
    return render_template("dashboard.html", stats=stats)

# ------------------------------------------------------------
# School setup
# ------------------------------------------------------------
@app.route("/school", methods=["GET", "POST"])
@login_required
@admin_required
def school_info():
    info = school()
    if request.method == "POST":
        for field in ["name", "address", "email", "phone", "motto", "next_term_begins", "headteacher_name"]:
            setattr(info, field, request.form.get(field, ""))
        logo = request.files.get("logo")
        if logo and logo.filename:
            data = logo.read()
            mime = logo.mimetype or "image/png"
            info.logo_data = "data:%s;base64,%s" % (mime, base64.b64encode(data).decode("ascii"))
        if request.form.get("clear_logo") == "1":
            info.logo_data = None
        db.session.commit()
        flash("School information saved.", "success")
        return redirect(url_for("school_info"))
    return render_template("school_info.html", info=info)

@app.route("/settings", methods=["GET", "POST"])
@login_required
@admin_required
def settings():
    if request.method == "POST":
        kind = request.form.get("kind")
        if kind == "house":
            name = request.form.get("name", "").strip()
            if name:
                db.session.add(House(name=name))
        elif kind == "term":
            if request.form.get("is_active"):
                TermSetting.query.update({"is_active": False})
            db.session.add(TermSetting(
                year=int(request.form.get("year")), term=request.form.get("term"),
                start_date=request.form.get("start_date"), end_date=request.form.get("end_date"),
                next_term_begins=request.form.get("next_term_begins"),
                is_active=bool(request.form.get("is_active"))
            ))
        elif kind == "fee":
            class_name = request.form.get("class_name")
            year = int(request.form.get("year"))
            term = request.form.get("term")
            amount = safe_float(request.form.get("amount")) or 0
            fs = FeeStructure.query.filter_by(class_name=class_name, year=year, term=term).first()
            if not fs:
                fs = FeeStructure(class_name=class_name, year=year, term=term)
                db.session.add(fs)
            fs.amount = amount
        db.session.commit()
        flash("Setting saved.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", houses=House.query.order_by(House.name).all(), terms_list=TermSetting.query.order_by(TermSetting.year.desc()).all(), fees=FeeStructure.query.order_by(FeeStructure.year.desc(), FeeStructure.class_name).all())

@app.route("/delete/<model>/<int:item_id>", methods=["POST"])
@login_required
@admin_required
def delete_item(model, item_id):
    mapping = {"house": House, "term": TermSetting, "subject": Subject, "staff": Staff, "user": User, "student": Student, "payment": Payment, "fee": FeeStructure, "assignment": TeacherAssignment, "attendance": Attendance}
    cls = mapping.get(model)
    if not cls:
        abort(404)
    obj = cls.query.get_or_404(item_id)
    if model == "user" and obj.username == "admin":
        flash("The main admin account cannot be deleted.", "warning")
    else:
        db.session.delete(obj)
        db.session.commit()
        flash("Deleted successfully.", "success")
    return redirect(request.referrer or url_for("dashboard"))

@app.route("/subjects", methods=["GET", "POST"])
@login_required
@admin_required
def subjects():
    if request.method == "POST":
        db.session.add(Subject(name=request.form.get("name", "").strip().upper(), code=request.form.get("code", "").strip(), section=request.form.get("section"), is_active=True))
        db.session.commit()
        flash("Subject added.", "success")
        return redirect(url_for("subjects"))
    return render_template("subjects.html", subjects=Subject.query.order_by(Subject.section, Subject.id).all())

# ------------------------------------------------------------
# Users and staff
# ------------------------------------------------------------
@app.route("/users", methods=["GET", "POST"])
@login_required
@admin_required
def users():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "user":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip() or "teacher123"
            if username:
                db.session.add(User(username=username, password_hash=generate_password_hash(password), role=request.form.get("role", "teacher"), full_name=request.form.get("full_name"), initials=request.form.get("initials")))
        elif action == "assignment":
            user_id = int(request.form.get("user_id"))
            section = request.form.get("section")
            db.session.add(TeacherAssignment(
                user_id=user_id, subject_id=int(request.form.get("subject_id")), section=section,
                class_name=request.form.get("class_name"), stream=request.form.get("stream") if section == "O" else None,
                department=request.form.get("department") if section == "A" else None
            ))
        db.session.commit()
        flash("Saved.", "success")
        return redirect(url_for("users"))
    return render_template("users.html", users=User.query.order_by(User.role, User.full_name).all(), subjects=Subject.query.filter_by(is_active=True).order_by(Subject.section, Subject.name).all(), assignments=TeacherAssignment.query.all())

@app.route("/staff", methods=["GET", "POST"])
@login_required
@admin_required
def staff():
    if request.method == "POST":
        db.session.add(Staff(name=request.form.get("name"), role=request.form.get("role"), phone=request.form.get("phone"), email=request.form.get("email"), initials=request.form.get("initials")))
        db.session.commit()
        flash("Staff member saved.", "success")
        return redirect(url_for("staff"))
    return render_template("staff.html", staff=Staff.query.order_by(Staff.name).all())

# ------------------------------------------------------------
# Students and admissions
# ------------------------------------------------------------
@app.route("/students")
@login_required
@admin_required
def students():
    section = request.args.get("section", "")
    class_name = request.args.get("class_name", "")
    stream = request.args.get("stream", "")
    department = request.args.get("department", "")
    q = Student.query
    if section: q = q.filter_by(section=section)
    if class_name: q = q.filter_by(class_name=class_name)
    if stream: q = q.filter_by(stream=stream)
    if department: q = q.filter_by(department=department)
    return render_template("students.html", students=q.order_by(Student.class_name, Student.name).all())

@app.route("/student/new", methods=["GET", "POST"])
@app.route("/student/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def student_form(student_id=None):
    student = Student.query.get(student_id) if student_id else Student(section="O", class_name="S1", stream="A")
    if request.method == "POST":
        student.name = request.form.get("name", "").strip()
        student.lin = request.form.get("lin")
        student.section = request.form.get("section")
        student.class_name = request.form.get("class_name")
        if student.section == "O":
            student.stream = request.form.get("stream")
            student.department = None
        else:
            student.department = request.form.get("department")
            student.stream = None
        student.sex = request.form.get("sex")
        student.house = request.form.get("house")
        student.pay_code = request.form.get("pay_code")
        student.guardian = request.form.get("guardian")
        student.contact = request.form.get("contact")
        student.address = request.form.get("address")
        student.status = request.form.get("status") or "Active"
        if not student_id:
            db.session.add(student)
        db.session.commit()
        flash("Learner saved and reflected in the correct class/section.", "success")
        return redirect(url_for("students", section=student.section, class_name=student.class_name, stream=student.stream or "", department=student.department or ""))
    return render_template("student_form.html", student=student, houses=House.query.order_by(House.name).all())

@app.route("/student/<int:student_id>/subjects", methods=["GET", "POST"])
@login_required
@admin_required
def student_subjects(student_id):
    student = Student.query.get_or_404(student_id)
    subjects = Subject.query.filter_by(section=student.section, is_active=True).order_by(Subject.name).all()
    if request.method == "POST":
        StudentSubject.query.filter_by(student_id=student.id).delete()
        for sid in request.form.getlist("subject_ids"):
            db.session.add(StudentSubject(student_id=student.id, subject_id=int(sid)))
        db.session.commit()
        flash("Subjects saved. Combination is generated only for S5/S6.", "success")
        return redirect(url_for("students", section=student.section, class_name=student.class_name))
    selected = {ss.subject_id for ss in student.subjects}
    return render_template("student_subjects.html", student=student, subjects=subjects, selected=selected, combination=combination_for_student(student))

# ------------------------------------------------------------
# Fees and attendance
# ------------------------------------------------------------
@app.route("/fees", methods=["GET", "POST"])
@login_required
@admin_required
def fees():
    year = int(request.args.get("year", datetime.now().year if datetime.now().year in YEARS else 2026))
    term = request.args.get("term", "TERM ONE")
    if request.method == "POST":
        db.session.add(Payment(student_id=int(request.form.get("student_id")), year=int(request.form.get("year")), term=request.form.get("term"), pay_date=request.form.get("pay_date") or date.today().isoformat(), amount=safe_float(request.form.get("amount")) or 0, method=request.form.get("method"), reference=request.form.get("reference"), note=request.form.get("note")))
        db.session.commit()
        flash("Payment recorded. Partial payments and installments are allowed.", "success")
        return redirect(url_for("fees", year=year, term=term))
    students_list = Student.query.order_by(Student.class_name, Student.name).all()
    payments = Payment.query.filter_by(year=year, term=term).order_by(Payment.pay_date.desc()).all()
    return render_template("fees.html", students=students_list, payments=payments, year=year, term=term, fee_required=fee_required, fee_paid=fee_paid)

@app.route("/attendance", methods=["GET", "POST"])
@login_required
@admin_required
def attendance():
    year = int(request.args.get("year", 2026))
    term = request.args.get("term", "TERM ONE")
    section = request.args.get("section", "O")
    class_name = request.args.get("class_name", "S1")
    stream = request.args.get("stream", "A") if section == "O" else None
    department = request.args.get("department", "Arts") if section == "A" else None
    if request.method == "POST":
        for student in students_filter(section, class_name, stream, department):
            att = Attendance.query.filter_by(student_id=student.id, year=year, term=term).first()
            if not att:
                att = Attendance(student_id=student.id, year=year, term=term)
                db.session.add(att)
            att.days_present = int(request.form.get(f"present_{student.id}") or 0)
            att.days_absent = int(request.form.get(f"absent_{student.id}") or 0)
            att.total_days = int(request.form.get(f"total_{student.id}") or (att.days_present + att.days_absent))
        db.session.commit()
        flash("Attendance saved.", "success")
        return redirect(request.url)
    students_list = students_filter(section, class_name, stream, department)
    return render_template("attendance.html", students=students_list, year=year, term=term, section=section, class_name=class_name, stream=stream, department=department, attendance_for=attendance_for)

# ------------------------------------------------------------
# Marks entry
# ------------------------------------------------------------
def assignment_from_request_or_teacher(user):
    if user.role == "teacher":
        ass_id = request.args.get("assignment_id") or request.form.get("assignment_id")
        assignments = TeacherAssignment.query.filter_by(user_id=user.id).all()
        if not assignments:
            return None, []
        if ass_id:
            ass = TeacherAssignment.query.filter_by(id=int(ass_id), user_id=user.id).first()
        else:
            ass = assignments[0]
        return ass, assignments
    return None, []

@app.route("/teacher-marks", methods=["GET", "POST"])
@login_required
def teacher_marks():
    user = current_user()
    year = int(request.args.get("year") or request.form.get("year") or 2026)
    term = request.args.get("term") or request.form.get("term") or "TERM ONE"
    assignment, assignments = assignment_from_request_or_teacher(user)

    if user.role == "teacher":
        if not assignment:
            return render_template("marks.html", no_assignment=True, assignments=[], rows=[], subjects=[])
        section, class_name, stream, department, subject_id = assignment.section, assignment.class_name, assignment.stream, assignment.department, assignment.subject_id
    else:
        section = request.args.get("section") or request.form.get("section") or "O"
        class_name = request.args.get("class_name") or request.form.get("class_name") or ("S1" if section == "O" else "S5")
        stream = (request.args.get("stream") or request.form.get("stream") or "A") if section == "O" else None
        department = (request.args.get("department") or request.form.get("department") or "Arts") if section == "A" else None
        subject_id = int(request.args.get("subject_id") or request.form.get("subject_id") or (Subject.query.filter_by(section=section).first().id if Subject.query.filter_by(section=section).first() else 0))

    subject = Subject.query.get(subject_id) if subject_id else None
    students_list = students_filter(section, class_name, stream, department)
    if section == "A" and subject:
        students_list = [s for s in students_list if subject.id in student_subject_ids(s)]

    if request.method == "POST":
        for st in students_list:
            mark = get_mark(st.id, subject_id, year, term)
            if not mark:
                mark = Mark(student_id=st.id, subject_id=subject_id, year=year, term=term)
                db.session.add(mark)
            if section == "O":
                for i in range(1, 6):
                    setattr(mark, f"t{i}_raw", request.form.get(f"t{i}_raw_{st.id}", ""))
                    setattr(mark, f"t{i}_outof", request.form.get(f"t{i}_outof_{st.id}", ""))
            else:
                for i in range(1, 6):
                    setattr(mark, f"c{i}", request.form.get(f"c{i}_{st.id}", ""))
            mark.teacher_initials = user.initials or "" if user.role == "teacher" else request.form.get(f"initials_{st.id}", "")
        db.session.commit()
        flash("Marks saved successfully.", "success")
        return redirect(url_for("teacher_marks", assignment_id=assignment.id if assignment else None, year=year, term=term, section=section, class_name=class_name, stream=stream or "", department=department or "", subject_id=subject_id))

    rows = []
    for st in students_list:
        mark = get_mark(st.id, subject_id, year, term) if subject else None
        rows.append((st, mark))
    return render_template("marks.html", no_assignment=False, assignments=assignments, assignment=assignment, rows=rows, subjects=Subject.query.filter_by(section=section, is_active=True).order_by(Subject.name).all(), subject=subject, section=section, class_name=class_name, stream=stream, department=department, year=year, term=term)

# ------------------------------------------------------------
# Report cards
# ------------------------------------------------------------
@app.route("/reports")
@login_required
@admin_required
def reports():
    return render_template("reports.html", students=Student.query.order_by(Student.class_name, Student.name).all())

@app.route("/report/<int:student_id>")
@login_required
@admin_required
def report_card(student_id):
    student = Student.query.get_or_404(student_id)
    year = int(request.args.get("year", 2026))
    term = request.args.get("term", "TERM ONE")
    return render_report(student, year, term, single=True)

@app.route("/reports/print")
@login_required
@admin_required
def print_group():
    year = int(request.args.get("year", 2026))
    term = request.args.get("term", "TERM ONE")
    section = request.args.get("section", "O")
    class_name = request.args.get("class_name", "S1" if section == "O" else "S5")
    stream = request.args.get("stream") if section == "O" else None
    department = request.args.get("department") if section == "A" else None
    students_list = students_filter(section, class_name, stream, department)
    cards = [report_context(st, year, term) for st in students_list]
    return render_template("print_group.html", cards=cards, year=year, term=term)

def report_context(student, year, term):
    subjects = subjects_for_report(student)
    rows = []
    any_missed = False
    o_formative_nums = []
    a_weights = []
    a_points = []
    for sub in subjects:
        mark = get_mark(student.id, sub.id, year, term)
        if student.section == "O":
            calc = calc_o_subject(mark)
            if calc.get("missed"):
                any_missed = True
            elif calc.get("formative_num") is not None:
                o_formative_nums.append(calc["formative_num"])
            rows.append({"subject": sub, "mark": mark, "calc": calc, "teacher": teacher_name_for(sub, "O", student.class_name, stream=student.stream)})
        else:
            calc = calc_a_subject(mark)
            if calc.get("missed"):
                any_missed = True
            elif calc.get("avg_num") is not None:
                a_weights.append(calc["avg_num"])
                a_points.append(calc.get("points", 0))
            rows.append({"subject": sub, "mark": mark, "calc": calc, "teacher_initials": (mark.teacher_initials if mark and mark.teacher_initials else teacher_initials_for(sub, "A", student.class_name, department=student.department))})
    att = attendance_for(student, year, term)
    required = fee_required(student, year, term)
    paid = fee_paid(student, year, term)
    balance = required - paid
    if student.section == "O":
        if any_missed:
            overall = {"formative": "X", "identifier": "X", "descriptor": "X"}
            class_comment = f"{student.name}, you have some missing assessment."
            head_comment = f"{student.name}, you have some missing assessment."
        elif o_formative_nums:
            avg_f = sum(o_formative_nums) / len(o_formative_nums)
            ident = avg_f * 3 / 20
            desc = o_descriptor(ident)
            overall = {"formative": fmt_num(avg_f, 1), "identifier": fmt_num(ident, 2), "descriptor": desc}
            if ident >= 2.5:
                class_comment = f"{student.name}, excellent work. Keep aiming higher."
                head_comment = f"{student.name}, your achievement is commendable. Maintain the effort."
            elif ident >= 1.5:
                class_comment = f"{student.name} will achieve higher marks by improving on weaker areas."
                head_comment = f"{student.name}, your strengths are evident. Focus on improving weaker areas."
            else:
                class_comment = f"{student.name}, this performance does not meet our expectations."
                head_comment = f"{student.name}, your progress is important to us, and we are here to support you."
        else:
            overall = {"formative": "", "identifier": "", "descriptor": ""}
            class_comment = ""
            head_comment = ""
    else:
        if any_missed:
            overall = {"points": "-", "avg_weight": "Missed", "level": "-", "result": "2"}
            class_comment = f"{student.name}, you have some missing assessment."
            head_comment = f"{student.name}, you have some missing assessment."
        elif a_weights:
            avg_w = sum(a_weights) / len(a_weights)
            _, level = a_grade(avg_w)
            overall = {"points": sum(a_points), "avg_weight": fmt_num(avg_w, 1), "level": level, "result": "1"}
            class_comment = f"{student.name}, your commitment to learning is commendable. Continue working hard."
            head_comment = f"{student.name} will get better grades if weak areas are improved."
        else:
            overall = {"points": "", "avg_weight": "", "level": "", "result": ""}
            class_comment = ""
            head_comment = ""
    return {"student": student, "rows": rows, "year": year, "term": term, "attendance": att, "required": required, "paid": paid, "balance": balance, "overall": overall, "class_comment": class_comment, "head_comment": head_comment, "combination": combination_for_student(student)}

def render_report(student, year, term, single=False):
    ctx = report_context(student, year, term)
    if student.section == "O":
        return render_template("report_o.html", **ctx, single=single)
    return render_template("report_a.html", **ctx, single=single)

# ------------------------------------------------------------
# Seed data
# ------------------------------------------------------------
def seed_defaults():
    if not SchoolInfo.query.first():
        info = SchoolInfo()
        badge_path = os.path.join(BASE_DIR, "static", "default_badge.png")
        if os.path.exists(badge_path):
            with open(badge_path, "rb") as f:
                info.logo_data = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
        db.session.add(info)
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin", password_hash=generate_password_hash("admin123"), role="admin", full_name="System Administrator", initials="ADM"))
    if not User.query.filter_by(username="teacher").first():
        db.session.add(User(username="teacher", password_hash=generate_password_hash("teacher123"), role="teacher", full_name="Sample Teacher", initials="TR"))
    for name, code in O_SUBJECTS:
        if not Subject.query.filter_by(name=name, section="O").first():
            db.session.add(Subject(name=name, code=code, section="O"))
    for name, code in A_SUBJECTS:
        if not Subject.query.filter_by(name=name, section="A").first():
            db.session.add(Subject(name=name, code=code, section="A"))
    for h in ["Blue", "White", "Green", "Red"]:
        if not House.query.filter_by(name=h).first():
            db.session.add(House(name=h))
    db.session.commit()
    sample_teacher = User.query.filter_by(username="teacher").first()
    sample_subject = Subject.query.filter_by(section="O", name="MATHEMATICS").first()
    if sample_teacher and sample_subject and not TeacherAssignment.query.filter_by(user_id=sample_teacher.id).first():
        db.session.add(TeacherAssignment(user_id=sample_teacher.id, subject_id=sample_subject.id, section="O", class_name="S1", stream="A"))
    db.session.commit()

with app.app_context():
    db.create_all()
    seed_defaults()

if __name__ == "__main__":
    app.run(debug=True)
