from fastapi import FastAPI, Form, Response, status, HTTPException, Depends, APIRouter,  File, UploadFile
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

@router.post("/", status_code=status.HTTP_201_CREATED)
def enroll_multiple_students(file: UploadFile, course_code:str = Form(),
                       db:Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):
    instructor = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == course_code,
        models.CourseInstructor.is_accepted == True,
        models.CourseInstructor.instructor_id == user.id).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
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

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_enrollment(id: int,course_code:str = Form(), db:Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):
    instructor = db.query(models.CourseInstructor).filter(models.CourseInstructor.course_code == course_code,
                                                          models.CourseInstructor.is_accepted == True,
                                             models.CourseInstructor.instructor_id == user.id).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    enroll_query = db.query(models.Enrollment).filter(models.Enrollment.id == id)
    if not enroll_query.first():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="details not found")
    enroll_query.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)