from fastapi import FastAPI, Form, Response, status, HTTPException, Depends, APIRouter,  File, UploadFile
from nanoid import generate
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi.encoders import jsonable_encoder

from sqlalchemy import func
# from sqlalchemy.sql.functions import func
from .. import models, schemas, oauth2
from ..database import get_db
import pandas as pd
import numpy as np


router = APIRouter(
    prefix="/instructions",
    tags=['Instruction']
)

@router.post("/")
def create_instructions(instructions:schemas.Instructions, user:schemas.TokenUser=Depends(oauth2.get_current_user),
                    db:Session=Depends(get_db)):
    assessment = db.query(models.Assessment).filter(models.Assessment.id == instructions.assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="assessment not found")
    instructor = db.query(models.Assessment).join(
        models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code
    ).filter(models.Assessment.id == instructions.assessment_id, 
             models.CourseInstructor.instructor_id == user.id,
             models.CourseInstructor.is_accepted == True).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    new_instructions = []
    for instruction in instructions.instructions:
        instruction.id = generate(size=15)
        new_instruction = models.Instruction(instruction=instruction, assessment_id=instructions.assessment_id)
        new_instructions.append(new_instruction)
    db.add_all(new_instructions)
    db.commit()
    return Response(status_code=status.HTTP_201_CREATED)


@router.get("/{assessment_id}", response_model=List[schemas.InstructionOut])
def get_instructions(assessment_id: int, db: Session = Depends(get_db), user:schemas.TokenUser=Depends(oauth2.get_current_user)):
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    instructions = db.query(models.Instruction).filter(models.Instruction.assessment_id == assessment_id).all()

    return instructions

@router.put("/{id}",)
def update_instruction(id: int, instruction:schemas.Instruction, user:schemas.TokenUser=Depends(oauth2.get_current_user),
                    db:Session=Depends(get_db)):
    instruction_query = db.query(models.Instruction).filter(models.Instruction.id == id)
    if not instruction_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Instruction not found")
    instructor = instructor = db.query(models.Instruction).join(
        models.Assessment, models.Instruction.assessment_id == models.Assessment.id).join(
        models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code).filter(
        models.Instruction.id == id,
        models.CourseInstructor.instructor_id == user.id,
        models.CourseInstructor.is_accepted == True).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    instruction_query.update(instruction.dict(), synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_201_CREATED)

@router.delete("/{id}",)
def delete_instruction(id: int, user:schemas.TokenUser=Depends(oauth2.get_current_user),
                    db:Session=Depends(get_db)):
    instruction_query = db.query(models.Instruction).filter(models.Instruction.id == id)
    if not instruction_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="answer not found")
    instructor = instructor = db.query(models.Instruction).join(
        models.Assessment, models.Instruction.assessment_id == models.Assessment.id).join(
        models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code).filter(
        models.Instruction.id == id,
        models.CourseInstructor.instructor_id == user.id,
        models.CourseInstructor.is_accepted == True).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    instruction_query.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)