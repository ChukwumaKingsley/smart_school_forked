from datetime import datetime
from fastapi import FastAPI, Form, Response, status, HTTPException, Depends, APIRouter,  File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi.encoders import jsonable_encoder
from nanoid import generate

from sqlalchemy import func, null
# from sqlalchemy.sql.functions import func
from .. import models, schemas, oauth2
from ..database import get_db
import pandas as pd
import numpy as np


router = APIRouter(
    prefix="/assessment_times",
    tags=['AssessmentTimes']
)

@router.post("/{course_code}/{assessment_id}", status_code=status.HTTP_201_CREATED)
def save_start_time(course_code: str, assessment_id: int, user: schemas.TokenUser = Depends(oauth2.get_current_user), db: Session = Depends(get_db)):

    course = db.query(models.Course).filter(models.Course.course_code == course_code).first()
    student_enrolled = db.query(models.Enrollment).filter(models.Enrollment.course_code == course_code, models.Enrollment.reg_num == user.id).first()

    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{course_code} not found!')
    if user.is_instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f'User must be a student, not instructor!')
    if not student_enrolled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f'Student not enrolled!')
    
    time_record = db.query(models.AssessmentTimeRecords).filter(models.AssessmentTimeRecords.assessment_id == assessment_id, models.AssessmentTimeRecords.student_id == user.id).first()

    if time_record:
        return time_record
    
    new_record = models.AssessmentTimeRecords(
        id = generate(size=15),
        assessment_id = assessment_id,
        student_id = user.id,
        start_datetime = datetime.now(),
        end_datetime = None
    )

    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    return new_record
    
@router.get("/{course_code}/{assessment_id}", status_code=status.HTTP_201_CREATED)
def get_assessment_time_records(course_code: str, assessment_id: int, user: schemas.TokenUser = Depends(oauth2.get_current_user), db: Session = Depends(get_db)):

    course = db.query(models.Course).filter(models.Course.course_code == course_code).first()
    student_enrolled = db.query(models.Enrollment).filter(models.Enrollment.course_code == course_code, models.Enrollment.reg_num == user.id).first()

    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{course_code} not found!')
    if user.is_instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f'User must be a student, not instructor!')
    if not student_enrolled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f'Student not enrolled!')
    
    time_record = db.query(models.AssessmentTimeRecords).filter(models.AssessmentTimeRecords.assessment_id == assessment_id, models.AssessmentTimeRecords.student_id == user.id).first()

    if not time_record:
        new_record = models.AssessmentTimeRecords(
            id = generate(size=15),
            assessment_id = assessment_id,
            student_id = user.id,
            start_datetime = datetime.now(),
            end_datetime = None
    )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        return new_record

    return time_record
    
@router.put("/end_assessment_time/{course_code}/{assessment_id}", status_code=status.HTTP_201_CREATED)
def get_assessment_time_records(course_code: str, assessment_id: int, user: schemas.TokenUser = Depends(oauth2.get_current_user), db: Session = Depends(get_db)):

    course = db.query(models.Course).filter(models.Course.course_code == course_code).first()
    student_enrolled = db.query(models.Enrollment).filter(models.Enrollment.course_code == course_code, models.Enrollment.reg_num == user.id).first()

    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{course_code} not found!')
    if user.is_instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f'User must be a student, not instructor!')
    if not student_enrolled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f'Student not enrolled!')
    
    time_record = db.query(models.AssessmentTimeRecords).filter(models.AssessmentTimeRecords.assessment_id == assessment_id, models.AssessmentTimeRecords.student_id == user.id).first()

    time_record.end_datetime = datetime.now()

    db.commit()
    db.refresh(time_record)
    return time_record   