from fastapi import FastAPI, Form, Response, status, HTTPException, Depends, APIRouter,  File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import codecs

from sqlalchemy import case, func, literal
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

@router.post("/enroll_request", status_code=status.HTTP_201_CREATED)
def make_enrollment_request(enrollment: schemas.EnrollInstructor,
                       db:Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):
    
    enrollment_status_query = db.query(models.CourseInstructor).filter(models.CourseInstructor.instructor_id == user.id, models.CourseInstructor.course_code == enrollment.course_code)
    
    enrollment_status = enrollment_status_query.first()

    if enrollment_status:
        enrollment_status_query.delete(synchronize_session=False)
        db.commit()
        return "Successfully cancelled enrollment."
    else:
        new_enroll = models.CourseInstructor(**enrollment.dict(), instructor_id=user.id)
        db.add(new_enroll)
        db.commit()
        db.refresh(new_enroll)
        return "Successfully requested enrollment."

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

@router.get("/coordinators/{course_code}", response_model=List[schemas.CourseInstructorEnrolledOut])
def get_course_coordinators(course_code: str, db: Session = Depends(get_db), user: schemas.TokenData = Depends(oauth2.get_current_user)):

    # Get all coordinators for the specified course with a join to the Instructor table
    coordinators = db.query(
        models.CourseInstructor.instructor_id,
        models.Instructor.department,
        models.Instructor.title,
        models.Instructor.name,
        models.Instructor.photo_url,
        case((models.CourseInstructor.instructor_id == user.id, literal(True)), else_=literal(False)).label("is_current_user")
        ).filter(
        models.CourseInstructor.course_code == course_code,
        models.CourseInstructor.is_coordinator == True
    ).outerjoin(models.Instructor).all()

    def serialize_coordinator(coordinator):
        coordinator_dict = {
        'instructor_id': coordinator.instructor_id,
        'name': coordinator.name,
        'department': coordinator.department,
        'title': coordinator.title,
        'photo_url': coordinator.photo_url,
        'is_current_user': coordinator.is_current_user,
    }
        return coordinator_dict
    
    serialized_coordinators = [serialize_coordinator(coordinator) for coordinator in coordinators]
    return JSONResponse(content=serialized_coordinators)

@router.get("/{course_code}", response_model=List[schemas.CourseInstructorEnrolledOut])
def get_course_instructors(course_code: str, db: Session = Depends(get_db), user: schemas.TokenData = Depends(oauth2.get_current_user)):

    # Get all coordinators for the specified course with a join to the Instructor table
    instructors = db.query(
        models.CourseInstructor.instructor_id,
        models.Instructor.department,
        models.Instructor.title,
        models.Instructor.name,
        models.Instructor.photo_url,
        case((models.CourseInstructor.instructor_id == user.id, literal(True)), else_=literal(False)).label("is_current_user")
        ).filter(
        models.CourseInstructor.course_code == course_code,
        models.CourseInstructor.is_coordinator == False,
        models.CourseInstructor.is_accepted == True
    ).outerjoin(models.Instructor).all()

    def serialize_instructor(instructor):
        instructor_dict = {
        'instructor_id': instructor.instructor_id,
        'name': instructor.name,
        'department': instructor.department,
        'title': instructor.title,
        'photo_url': instructor.photo_url,
        'is_current_user': instructor.is_current_user,
    }
        return instructor_dict
    
    serialized_instructors = [serialize_instructor(instructor) for instructor in instructors]
    return JSONResponse(content=serialized_instructors)

@router.get("/requests/{course_code}", response_model=List[schemas.CourseInstructorEnrolledOut])
def get_course_instructors_join_request(course_code: str, db: Session = Depends(get_db), user: schemas.TokenData = Depends(oauth2.get_current_user)):

    # Get all coordinators for the specified course with a join to the Instructor table
    instructors = db.query(
        models.CourseInstructor.instructor_id,
        models.Instructor.department,
        models.Instructor.title,
        models.Instructor.name,
        models.Instructor.photo_url,
        case((models.CourseInstructor.instructor_id == user.id, literal(True)), else_=literal(False)).label("is_current_user")
        ).filter(
        models.CourseInstructor.course_code == course_code,
        models.CourseInstructor.is_coordinator == False,
        models.CourseInstructor.is_accepted == False
    ).outerjoin(models.Instructor).all()

    def serialize_instructor(instructor):
        instructor_dict = {
        'instructor_id': instructor.instructor_id,
        'name': instructor.name,
        'department': instructor.department,
        'title': instructor.title,
        'photo_url': instructor.photo_url,
        'is_current_user': instructor.is_current_user,
    }
        return instructor_dict
    
    serialized_instructors = [serialize_instructor(instructor) for instructor in instructors]
    return JSONResponse(content=serialized_instructors)

@router.put("/{id}", status_code=status.HTTP_201_CREATED, response_model=schemas.EnrollInstructor)
def update_instructor(id: str, course_code: str = Form(),
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

@router.delete("/{id}/{course_code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instructor(id: str, course_code:str, db:Session = Depends(get_db), user:schemas.TokenData = Depends(oauth2.get_current_user)):
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course instructor not found")
    instructor_query.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

