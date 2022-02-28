# Imports
from datetime import date, datetime

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask_restful import Api, Resource
from marshmallow import Schema, fields, ValidationError


# Config
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)
api = Api(app)


# Models
class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return '<Class %r>' % self.id

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)

    in_class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    in_class = db.relationship('Class', backref=db.backref('student', cascade="all,delete", lazy=True))

    def __repr__(self):
        return '<Student %r>' % self.id

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    present = db.Column(db.Boolean, default=False, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=date.today)

    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    student = db.relationship('Student', backref=db.backref('attendance', cascade="all,delete", lazy=True))

    __table_args__ = (db.UniqueConstraint('date', 'student_id', name='daily_attendance'),)

    def __repr__(self):
        return '<Attendance %r>' % self.id


# Schemas
def must_not_be_blank(data):
    if not data:
        raise ValidationError("Data not provided.")

class ClassSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(validate=must_not_be_blank)
    student = fields.List(fields.Nested(lambda: StudentSchema(only=('id', 'name'))))

class StudentSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(validate=must_not_be_blank)
    in_class = fields.Nested(ClassSchema, validate=must_not_be_blank)

class AttendanceSchema(Schema):
    id = fields.Int(dump_only=True)
    present = fields.Bool()
    date = fields.Date(validate=must_not_be_blank)
    student = fields.Nested(StudentSchema, validate=must_not_be_blank)

class_schema = ClassSchema()
classes_schema = ClassSchema(many=True)
student_schema = StudentSchema()
students_schema = StudentSchema(many=True)
attendance_schema = AttendanceSchema()
attendances_schema = AttendanceSchema(many=True)


# APIs
class ClassListResource(Resource):
    def get(self):
        classes = Class.query.all()
        return classes_schema.dump(classes)

    def post(self):
        new_class = Class(name=request.json['name'])
        db.session.add(new_class)
        db.session.commit()
        return class_schema.dump(new_class)

class ClassResource(Resource):
    def get(self, id):
        _class = Class.query.get_or_404(id)
        return class_schema.dump(_class)
    
    def patch(self, id):
        _class = Class.query.get_or_404(id)
        if 'name' in request.json:
            _class.name = request.json['name']
        db.session.commit()
        return class_schema.dump(_class)
    
    def delete(self, id):
        _class = Class.query.get_or_404(id)
        db.session.delete(_class)
        db.session.commit()
        return '', 204

class StudentListResource(Resource):
    def get(self):
        students = Student.query.all()
        return students_schema.dump(students)

    def post(self):
        in_class = Class.query.get_or_404(request.json['in_class'])
        new_student = Student(name=request.json['name'], in_class=in_class)
        db.session.add(new_student)
        db.session.commit()
        return student_schema.dump(new_student)

class StudentResource(Resource):
    def get(self, id):
        student = Student.query.get_or_404(id)
        return student_schema.dump(student)
    
    def patch(self, id):
        student = Student.query.get_or_404(id)
        if 'name' in request.json:
            student.name = request.json['name']
        if 'in_class' in request.json:
            student.in_class = Class.query.get_or_404(request.json['in_class'])
        db.session.commit()
        return student_schema.dump(student)
    
    def delete(self, id):
        student = Student.query.get_or_404(id)
        db.session.delete(student)
        db.session.commit()
        return '', 204

class AttendanceListResource(Resource):
    def get(self):
        attendance = Attendance.query.all()
        return attendances_schema.dump(attendance)

    def post(self):
        student = Student.query.get_or_404(request.json['student'])
        _date = datetime.strptime(request.json['date'], '%d/%m/%Y')
        attendance = Attendance(present=request.json['present'], date=_date.date(), student=student)
        try:
            db.session.add(attendance)
            db.session.commit()
        except IntegrityError:
            return "Attendence already created"
        return attendance_schema.dump(attendance)

class AttendanceResource(Resource):
    def get(self, id):
        attendance = Attendance.query.get_or_404(id)
        return attendance_schema.dump(attendance)

    def patch(self, id):
        attendance = Attendance.query.get_or_404(id)
        if 'present' in request.json:
            attendance.present = request.json['present']
        db.session.commit()
        return attendance_schema.dump(attendance)

    def delete(self, id):
        attendance = Attendance.query.get_or_404(id)
        db.session.delete(attendance)
        db.session.commit()
        return '', 204


api.add_resource(ClassListResource, '/class')
api.add_resource(ClassResource, '/class/<int:id>')
api.add_resource(StudentListResource, '/student')
api.add_resource(StudentResource, '/student/<int:id>')
api.add_resource(AttendanceListResource, '/attendance')
api.add_resource(AttendanceResource, '/attendance/<int:id>')


if __name__ == "__main__":
    app.run(debug=True)