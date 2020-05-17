# imports & application set-up
#-----------------
from flask import Flask, redirect, render_template, request, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy.orm import joinedload
from flask_login import login_required, login_user, LoginManager, logout_user, UserMixin
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.config["DEBUG"] = True

# Database connection configuration
#---------------------------------

SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
    username="ubtechy1",
    password="AlmostH0me#",
    hostname="ubtechy1.mysql.pythonanywhere-services.com",
    databasename="ubtechy1$gradebook"
)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


app.secret_key = "TheAlpha&0mega#1"
login_manager = LoginManager()
login_manager.init_app(app)

# Database Model Definitions
#-------------------------------

class Users(db.Model, UserMixin):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique = True, nullable=False)
    password_hash = db.Column(db.String(128))

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


    def get_id(self):
        return self.username

@login_manager.user_loader
def load_user(user_id):
    return Users.query.filter_by(username=user_id).first()

class Students(db.Model):

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    firstName = db.Column(db.String(128), nullable=False)
    lastName = db.Column(db.String(128), nullable=False)
    major = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=False)

    grades = relationship("Grades", cascade="all, delete-orphan", lazy='joined')

class Assignments(db.Model):

    __tablename__ = "assignments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(128), nullable=False)

    grades = relationship("Grades", cascade="all, delete-orphan", lazy='joined')

class Grades(db.Model):

    __tablename__ = "grades"

    id = db.Column(db.Integer, primary_key=True)
    assignment_id =db.Column(db.Integer, db.ForeignKey("assignments.id", ondelete="CASCADE"))
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"))
    percentage = db.Column(db.Float)

    students = relationship("Students", lazy='joined')
    assignments = relationship("Assignments", lazy='joined')


# Template App Routes
# -------------------------------------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    user = Users.query.filter_by(username=username).first()

    if not user:
        flash('Your login information is incorrect. Please try again.', 'danger')
        return redirect(url_for("login"))

    if not check_password_hash(user.password_hash, password):
        flash('Your login information is incorrect. Please try again.', 'danger')
        return redirect(url_for("login"))

    login_user(user)
    return redirect(url_for("index"))

@app.route("/index")
@login_required
def index ():
    return render_template("index.html")

@app.route("/students", methods=["GET", "POST"])
@login_required
def students():
    if request.method == "GET":
        query = db.session.query(Students).order_by(Students.id.asc())
        return render_template("students.html", students=query)
    if request.method == "POST":
        student = Students(firstName=request.form["firstName"],lastName=request.form["lastName"],major=request.form["major"],email=request.form["email"])
        db.session.add(student)
        for assignment in db.session.query(Assignments).distinct():
            db.session.add(Grades(assignment_id = assignment.id, student_id = student.id, percentage = None))
        db.session.commit()
        return redirect(url_for('students'))

@app.route("/sort", methods=["GET","POST"])
@login_required
def sort():
    if request.method == "GET":
        query = db.session.query(Students).order_by(Students.firstName.asc())
        return render_template("students.html", students=query)
    if request.method == "POST":
        student = Students(firstName=request.form["firstName"],lastName=request.form["lastName"],major=request.form["major"],email=request.form["email"])
        db.session.add(student)
        for assignment in db.session.query(Assignments).distinct():
            db.session.add(Grades(assignment_id = assignment.id, student_id = student.id, percentage = None))
        db.session.commit()
        return redirect(url_for('sort'))

@app.route("/editstudent", methods=["GET","POST"])
def editStudent():

    if request.method == "GET":
        studentID = request.args.get('studentid')
        student = db.session.query(Students).get(studentID)
        grades = db.session.query(Grades).filter(Grades.student_id == studentID)
        grades = grades.options(
            joinedload(Grades.assignments)
        )
        aggregate = db.session.query(db.func.avg(Grades.percentage)).filter(Grades.student_id == studentID).scalar()
        return render_template("editstudent.html", student = student, grades = grades, aggregate = aggregate)

    if request.method == "POST":
        studentID = request.form['studentid']
        student = db.session.query(Students).get(studentID);
        grades = db.session.query(Grades).filter(Grades.student_id == studentID).all();

        student.firstName = request.form["firstName"]
        student.lastName = request.form["lastName"]
        student.major = request.form["major"]
        student.email = request.form["email"]

        # for index, grade in grades:
        #     grade.percentage = request.form["grades"][index]

        index = 0
        newGrades = request.form.getlist("grades")
        for grade in grades:
            if grade.percentage == ' ':
                grade.percentage = None;
            else:
                grade.percentage = newGrades[index]
            index += 1

        db.session.commit()
        return redirect(url_for("students"))


@app.route("/deletestudent", methods=["POST"])
def deleteStudent():
    student = Students.query.get(request.form["deleteId"])
    db.session.delete(student)
    db.session.commit()
    return redirect(url_for('students'))


@app.route("/grades", methods=["GET", "POST"])
@login_required
def grades():
    if request.method == "GET":

        query = db.session.query(Grades).order_by(Grades.student_id.asc(),Grades.assignment_id.asc())
        query = query.options(
            joinedload(Grades.students),
            joinedload(Grades.assignments)
        )
        query2 = db.session.query(Assignments)

        return render_template("grades.html", grades=query, assignments = query2)

@app.route("/assignments", methods=["GET", "POST"])
@login_required
def assignments():
    if request.method == "GET":
        return render_template("assignments.html", assignments=Assignments.query.all())

    assignment = Assignments(name=request.form["name"],description=request.form["description"])
    db.session.add(assignment)
    db.session.commit()

    for student in db.session.query(Students).distinct():
        db.session.add(Grades(assignment_id = assignment.id, student_id = student.id, percentage = None))

    db.session.commit()
    return redirect (url_for('assignments'))

@app.route("/editassignment", methods=["GET","POST"])
def editAssignment():

    if request.method == "GET":
        assignmentID = request.args.get('assignmentid')
        assignment = db.session.query(Assignments).get(assignmentID);
        grades = db.session.query(Grades).filter(Grades.assignment_id == assignmentID);
        grades = grades.options(
            joinedload(Grades.students)
        )
        return render_template("editassignment.html", assignment = assignment, grades = grades)

    if request.method == "POST":
        assignmentID = request.form['assignmentid']
        assignment = db.session.query(Assignments).get(assignmentID);
        grades = db.session.query(Grades).filter(Grades.assignment_id == assignmentID).all();

        assignment.name = request.form["name"]
        assignment.description = request.form["description"]

        index = 0
        newGrades = request.form.getlist("grades")
        for grade in grades:
            grade.percentage = newGrades[index]
            index += 1

        db.session.commit()
        return redirect(url_for("assignments"))

@app.route("/deleteassignment", methods=["POST"])
def deleteAssignment():
    assignment = Assignments.query.get(request.form["deleteassignmentID"])
    db.session.delete(assignment)
    db.session.commit()
    return redirect(url_for('assignments'))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))
