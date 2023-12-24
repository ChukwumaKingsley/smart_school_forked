from fastapi import FastAPI, Form, Response, status, HTTPException, Depends, APIRouter,  File, UploadFile
from nanoid import generate
from sqlalchemy.orm import Session
from typing import List, Optional

from sqlalchemy import func
# from sqlalchemy.sql.functions import func
from .. import models, schemas, oauth2
from ..database import get_db
from datetime import timedelta, datetime


router = APIRouter(
    prefix="/questions",
    tags=['Questions']
)

@router.post("/", response_model=schemas.QuestionOut)
def create_question(question:schemas.Question, user:schemas.TokenUser=Depends(oauth2.get_current_user),
                    db:Session=Depends(get_db)):
    instructor = db.query(models.Assessment).join(
        models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code
    ).filter(models.Assessment.id == question.assessment_id, 
             models.CourseInstructor.instructor_id == user.id,
             models.CourseInstructor.is_accepted == True).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    assessment = db.query(models.Assessment).filter(models.Assessment.id == question.assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="assessment not found")
    current_time = datetime.now()
    # if (assessment.start_date <= current_time):
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
    #                         detail="cannot add questions to already started assessment")
    new_question = models.Question(**question.dict(), id=generate(size=15))
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    return new_question

@router.put("/{id}", response_model=schemas.QuestionOut)
def update_question(id:int, updated_question:schemas.QuestionUpdate, user:schemas.TokenUser=Depends(oauth2.get_current_user),
                    db:Session=Depends(get_db)):
    instructor = db.query(models.Question).join(
        models.Assessment, models.Question.assessment_id == models.Assessment.id).join(
        models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code
    ).filter(models.Question.id == id, 
             models.CourseInstructor.instructor_id == user.id,
             models.CourseInstructor.is_accepted == True).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    question_query = db.query(models.Question).filter(models.Question.id==id)
    question = question_query.first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="question not found")
    assessment = db.query(models.Assessment).filter(models.Assessment.id == question.assessment_id).first()
    current_time = datetime.now()
    # if (assessment.start_date <= current_time):
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
    #                         detail="cannot add questions to already started assessment")
    question_query.update(updated_question.dict(), synchronize_session=False)
    db.commit()
    db.refresh(question_query.first())
    return question_query.first()

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(id:int,user:schemas.TokenUser=Depends(oauth2.get_current_user),
                    db:Session=Depends(get_db)):
    instructor = db.query(models.Question).join(
        models.Assessment, models.Question.assessment_id == models.Assessment.id).join(
        models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code
    ).filter(models.Question.id == id, 
             models.CourseInstructor.instructor_id == user.id,
             models.CourseInstructor.is_accepted == True).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    question_query = db.query(models.Question).filter(models.Question.id==id)
    question = question_query.first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="question not found")
    assessment = db.query(models.Assessment).filter(models.Assessment.id == question.assessment_id).first()
    current_time = datetime.now()
    if (assessment.start_date <= current_time):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="cannot delete questions to already started assessment")
    question_query.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)