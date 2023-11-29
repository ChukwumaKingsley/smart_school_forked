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
    prefix="/instructors",
    tags=['EnrollInstructors']
)

@router.get("/count/{course_code}", response_model=int)
def get_instructors_count(course_code: str, db: Session = Depends(get_db)):
    instructors_count = db.query(func.count(models.CourseInstructor.instructor_id)).filter(
        models.CourseInstructor.course_code == course_code,
        (models.CourseInstructor.is_coordinator == True) | (models.CourseInstructor.is_accepted == True)
    ).scalar()
    return instructors_count

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.EnrollInstructor)
def enroll_instructor(course_code: str = Form(),
                       db:Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):
    if not user.is_instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    enrollment = models.CourseInstructor(instructor_id=user.id, course_code=course_code)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment

@router.put("/{id}", status_code=status.HTTP_201_CREATED, response_model=schemas.EnrollInstructor)
def update_instructor(id:int, course_code: str = Form(),
                       db:Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):
    if not user.is_instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    instructor = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == course_code,
        models.CourseInstructor.instructor_id == user.id, models.CourseInstructor.is_coordinator == True).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="This can only be performed by course coordinators")
    instructor_query = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code==course_code, models.CourseInstructor.instructor_id == id
    )
    if not instructor_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    instructor_query.update({"is_accepted":True},synchronize_session=False)
    db.commit()
    db.refresh(instructor_query.first())
    return instructor_query.first()

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instructor(id:int, course_code:str = Form(),
                       db:Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):
    if not user.is_instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    instructor = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == course_code,
        models.CourseInstructor.instructor_id == user.id, models.CourseInstructor.is_coordinator == True).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="This can only be performed by course coordinators")
    instructor_query = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code==course_code, models.CourseInstructor.instructor_id == id
    )
    if not instructor_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    instructor_query.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

