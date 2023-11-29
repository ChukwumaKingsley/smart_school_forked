from fastapi import FastAPI, Form, Response, status, HTTPException, Depends, APIRouter,  File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import String, cast, delete, func, or_
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import codecs

from sqlalchemy import func
# from sqlalchemy.sql.functions import func
from .. import models, schemas, oauth2
from ..database import get_db


router = APIRouter(
    prefix="/students",
    tags=['EnrollStudents']
)


@router.get("/enrolled/{course_code}/count", response_model=int)
def get_enrolled_students_counts(course_code: str, db: Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):

    course_query =  db.query(models.Course).filter(func.lower(models.Course.course_code) == course_code.lower()).first()
    if not course_query:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist")
    students_count = db.query(func.count(models.Enrollment.reg_num)).filter(
        models.Enrollment.course_code == course_code,
        models.Enrollment.accepted == True
    ).scalar()
    return students_count

@router.get("/enrolled/{course_code}", response_model=List[schemas.StudentsEnrolled])
def get_enrolled_students(course_code: str, db: Session = Depends(get_db), user: schemas.TokenData = Depends(oauth2.get_current_user), search: Optional[str] = None, level: Optional[str] = None):

    # Check if the user is an instructor for the course
    instructor_query = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == course_code,
        models.CourseInstructor.instructor_id == user.id,
        models.CourseInstructor.is_accepted == True
    ).first()
    
    if not instructor_query:
        raise HTTPException(status_code=403, detail="Access denied")

    # Fetch all students' information, both accepted and unaccepted
    requests_query = db.query(models.Enrollment).filter(
        models.Enrollment.course_code == course_code, models.Enrollment.accepted == True
    )

    if search:
        requests_query = requests_query.filter(or_(
            func.lower(models.Student.name).contains(search.lower()), 
            cast(models.Student.id, String).contains(search.lower())
            )
            )
    if level:
        requests_query = requests_query.filter(cast(models.Student.level, String) == level)

    requests = requests_query.join(models.Student, models.Enrollment.reg_num == models.Student.id).with_entities(
        models.Student.id.label("reg_num"),
        models.Student.name,
        models.Student.department,
        models.Student.level,
        models.Enrollment.accepted
    ).all()

    def serialize_student(student):
        student_dict = {
        'reg_num': student.reg_num,
        'name': student.name,
        'department': student.department,
        'level': student.level,
        'accepted': student.accepted,
    }
        return student_dict
    
    serialized_students = [serialize_student(student) for student in requests]

    return JSONResponse(content=serialized_students)

@router.get("/enrolled/{course_code}/requests", response_model=List[schemas.StudentsEnrolled])
def get_enrollment_students_requests(course_code: str, db: Session = Depends(get_db), user: schemas.TokenData = Depends(oauth2.get_current_user), search: Optional[str] = None, level: Optional[str] = None):

    # Check if the user is an instructor for the course
    instructor_query = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == course_code,
        models.CourseInstructor.instructor_id == user.id,
        models.CourseInstructor.is_accepted == True
    ).first()
    
    if not instructor_query:
        raise HTTPException(status_code=403, detail="Access denied")

    # Fetch all students' information, both accepted and unaccepted
    requests_query = db.query(models.Enrollment).filter(
        models.Enrollment.course_code == course_code, models.Enrollment.accepted == False
    )

    if search:
        requests_query = requests_query.filter(or_(
            func.lower(models.Student.name).contains(search.lower()), 
            cast(models.Student.id, String).contains(search.lower())
            )
            )
    if level:
        requests_query = requests_query.filter(cast(models.Student.level, String) == level)

    requests = requests_query.join(models.Student, models.Enrollment.reg_num == models.Student.id).with_entities(
        models.Student.id.label("reg_num"),
        models.Student.name,
        models.Student.department,
        models.Student.level,
        models.Enrollment.accepted
    ).all()

    def serialize_student(student):
        student_dict = {
        'reg_num': student.reg_num,
        'name': student.name,
        'department': student.department,
        'level': student.level,
        'accepted': student.accepted,
    }
        return student_dict
    
    serialized_students = [serialize_student(student) for student in requests]

    return JSONResponse(content=serialized_students)


@router.post("/", status_code=status.HTTP_201_CREATED)
def enroll_multiple_students(file: UploadFile, course_code:str = Form(),
                       db:Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):
    instructor = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == course_code,
        models.CourseInstructor.is_accepted == True,
        models.CourseInstructor.instructor_id == user.id).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    print("here")
    
    csvReader = csv.DictReader(codecs.iterdecode(file.file, 'utf-8'))
    enrollments = []
    for rows in csvReader:             
        new_data = {"reg_num":rows['REG. NO.'], "course_code":course_code}
        enrollment = models.Enrollment(**new_data)
        enrollments.append(enrollment)
    
    file.file.close()
    db.add_all(enrollments)
    db.commit()
    return Response(status_code=status.HTTP_201_CREATED, content="Success")

@router.post("/enroll_request", status_code=status.HTTP_201_CREATED)
def make_enrollment_request(enrollment:schemas.EnrollStudent,
                       db:Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):
    
    enrollment_status_query = db.query(models.Enrollment).filter(models.Enrollment.reg_num == enrollment.reg_num, models.Enrollment.course_code == enrollment.course_code)
    
    enrollment_status = enrollment_status_query.first()

    if enrollment_status:
        enrollment_status_query.delete(synchronize_session=False)
        db.commit()
        return "Successfully cancelled enrollment."
    else:
        new_enroll = models.Enrollment(**enrollment.dict())
        db.add(new_enroll)
        db.commit()
        db.refresh(new_enroll)
        return "Successfully requested enrollment."

@router.post("/enroll", status_code=status.HTTP_201_CREATED, response_model=schemas.EnrollStudentOut)
def enroll_one_student(enrollment:schemas.EnrollStudent,
                       db:Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):
    instructor = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == enrollment.course_code,
        models.CourseInstructor.is_accepted == True,
        models.CourseInstructor.instructor_id == user.id).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if enrollment.reg_num == None:
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE)
    new_enroll = models.Enrollment(**enrollment.dict())
    db.add(new_enroll)
    db.commit()
    db.refresh(new_enroll)
    return new_enroll

@router.put("/approve_enrollment/{course_code}/{id}", status_code=status.HTTP_201_CREATED)
def approve_enrollment(course_code: str, id: str, db:Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):
    print(id, course_code)

    instructor = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == course_code,
        models.CourseInstructor.is_accepted == True,
        models.CourseInstructor.instructor_id == user.id).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
    enroll_query = db.query(models.Enrollment).filter(
        models.Enrollment.course_code == course_code, cast(models.Enrollment.reg_num, String) == id)
    
    if not enroll_query.first():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Join course request not found")
    enroll_query.update({"accepted":True}, synchronize_session=False)
    db.commit()
    return "Enrollment approved!"

@router.put("/approve_all_enrollments/{course_code}", status_code=status.HTTP_201_CREATED)
def approve_enrollments(course_code: str, db:Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):
    instructor = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == course_code,
        models.CourseInstructor.is_accepted == True,
        models.CourseInstructor.instructor_id == user.id).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
    enroll_query = db.query(models.Enrollment).filter(
        models.Enrollment.course_code == course_code, models.Enrollment.accepted == False)
    
    if not enroll_query.all():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No Join requests")
    
    requests = enroll_query.all()
    for request in requests:
        request.accepted = True

    db.commit()
    return "Enrollment approved!"

@router.put("/", status_code=status.HTTP_201_CREATED, response_model=schemas.EnrollStudentOut)
def accept_enrollment(course_code:str= Form(),db:Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):
    if user.is_instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    enroll_query = db.query(models.Enrollment).filter(
        models.Enrollment.course_code == course_code, models.Enrollment.reg_num == user.id)
    if not enroll_query.first():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not registered to partake in course")
    enroll_query.update({"accepted":True}, synchronize_session=False)
    db.commit()
    return enroll_query.first()


@router.put("/{id}", status_code=status.HTTP_201_CREATED, response_model=schemas.EnrollStudentOut)
def update_enrollment(id: int, enrollment: schemas.EnrollStudent,db:Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):
    instructor = db.query(models.CourseInstructor).filter(models.CourseInstructor.course_code == enrollment.course_code,
                                                          models.CourseInstructor.is_accepted == True,
                                             models.CourseInstructor.instructor_id == user.id).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    enroll_query = db.query(models.Enrollment).filter(models.Enrollment.id == id)
    if not enroll_query.first():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="details not found")
    enroll_query.update(enrollment.dict(), synchronize_session=False)
    db.commit()
    return enroll_query.first()

@router.delete("/{course_code}/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_enrollment(id: str, course_code:str, db:Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):
    instructor = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == course_code,
        models.CourseInstructor.is_accepted == True,
        models.CourseInstructor.instructor_id == user.id
        ).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    enroll_query = db.query(models.Enrollment).filter(models.Enrollment.course_code == course_code, cast(models.Enrollment.reg_num, String) == id)
    if not enroll_query.first():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="details not found")
    enroll_query.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.delete("/all/{course_code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_enrollment_requests(course_code: str, db: Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):

    instructor = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == course_code,
        models.CourseInstructor.is_accepted == True,
        models.CourseInstructor.instructor_id == user.id
        ).first()
    
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
    enroll_query = db.query(models.Enrollment).filter(models.Enrollment.course_code == course_code, models.Enrollment.accepted == False)

    if not enroll_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No request to delete")
    
    
    delete_statement = delete(models.Enrollment).where(
        models.Enrollment.course_code == course_code,
        models.Enrollment.accepted == False
    )
    
    # Execute the delete statement
    db.execute(delete_statement)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)