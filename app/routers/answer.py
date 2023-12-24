from fastapi import FastAPI, Form, Response, status, HTTPException, Depends, APIRouter,  File, UploadFile
from nanoid import generate
from sqlalchemy.orm import Session
from typing import List, Optional

from sqlalchemy import func
# from sqlalchemy.sql.functions import func
from .. import models, schemas, oauth2
from ..database import get_db


router = APIRouter(
    prefix="/answers",
    tags=['Answers']
)

@router.post("/",)
def create_options(answers:schemas.Options, user:schemas.TokenUser=Depends(oauth2.get_current_user),
                    db:Session=Depends(get_db)):
    question = db.query(models.Question).filter(models.Question.id == answers.question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="question not found")
    instructor = db.query(models.Question).join(
        models.Assessment, models.Question.assessment_id == models.Assessment.id).join(
        models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code
    ).filter(models.Question.id == answers.question_id, 
             models.CourseInstructor.instructor_id == user.id,
             models.CourseInstructor.is_accepted == True).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    options = []
    for option in answers.options:
        new_option = models.Option(**option.dict(), id=generate(size=15), question_id=answers.question_id)
        options.append(new_option)
    db.add_all(options)
    db.commit()
    return Response(status_code=status.HTTP_201_CREATED)

@router.put("/{id}",)
def update_option(id: int,option:schemas.Option, user:schemas.TokenUser=Depends(oauth2.get_current_user),
                    db:Session=Depends(get_db)):
    answer_query = db.query(models.Option).filter(models.Option.id == id)
    if not answer_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="answer not found")
    instructor = db.query(models.rOption).join(
        models.Question,models.Option.question_id == models.Question.id).join(
        models.Assessment, models.Question.assessment_id == models.Assessment.id).join(
        models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code
    ).filter(models.Option.id == id, 
             models.CourseInstructor.instructor_id == user.id,
             models.CourseInstructor.is_accepted == True).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    answer_query.update(option.dict(), synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_201_CREATED)

@router.delete("/{id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_option(id: int, user:schemas.TokenUser=Depends(oauth2.get_current_user),
                    db:Session=Depends(get_db)):
    answer_query = db.query(models.Option).filter(models.Option.id == id)
    if not answer_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="answer not found")
    instructor = db.query(models.Option).join(
        models.Question,models.Option.question_id == models.Question.id).join(
        models.Assessment, models.Question.assessment_id == models.Assessment.id).join(
        models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code
    ).filter(models.Option.id == id, 
             models.CourseInstructor.instructor_id == user.id,
             models.CourseInstructor.is_accepted == True).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    answer_query.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)