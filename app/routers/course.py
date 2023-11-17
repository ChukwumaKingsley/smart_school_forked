from operator import or_
import os
import re
import cloudinary.uploader
from fastapi import FastAPI, File, Response, UploadFile, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from typing import List, Optional

from sqlalchemy import func

from app import config
# from sqlalchemy.sql.functions import func
from datetime import timedelta, datetime
from .. import models, schemas, oauth2
from ..database import get_db


router = APIRouter(
    prefix="/courses",
    tags=['Courses']
)


@router.post("/", response_model=schemas.CourseOut, status_code=201)
def create_course(course: schemas.Course, db: Session = Depends(get_db),
                  user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    if not user.is_instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="not unauthorized to perform request")
    exists = db.query(models.Course).filter(
        models.Course.course_code == course.course_code).count() > 0
    if exists:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"course with code {course.course_code} already exists")
    if not re.match(r'^[A-Za-z]{3} \d{3}$', course.course_code):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid course code")
    if (course.semester == 1 and int(course.course_code[-1])%2 == 0) or (course.semester == 2 and int(course.course_code[-1])%2 == 1):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course code last digit does not match semester.")

    new_course = models.Course(**course.dict())

    instructor = schemas.EnrollInstructor(course_code=course.course_code,
                                          instructor_id=user.id, is_coordinator=True, is_accepted=True)
    instructor = models.CourseInstructor(**instructor.dict())
    db.add(instructor)
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course


@router.put("/{code}/photo", response_model=schemas.CourseOut, status_code=201)
async def upload_photo(code: str, file: UploadFile = File(...),
                       user: schemas.TokenData = Depends(oauth2.get_current_user), db: Session = Depends(get_db)):
    instructor = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == code,
        models.CourseInstructor.is_accepted == True,
        models.CourseInstructor.instructor_id == user.id).first()

    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access denied")
    course_query = db.query(models.Course).filter(
        models.Course.course_code == code)
    response = cloudinary.uploader.upload(
        file.file,
        public_id="course-photo-"+code,
        folder="FUTOAcademia-course-photo",
        )
    image_url = response.get("secure_url")
    course_query.update({"course_photo_url": image_url},
                        synchronize_session=False)
    db.commit()
    return course_query.first()


@router.put("/{code}", response_model=schemas.CourseOut, status_code=201)
def update_course(code: str, new_course: schemas.Course,
                  user: schemas.TokenData = Depends(oauth2.get_current_user), db: Session = Depends(get_db)):
    instructor = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == code,
        models.CourseInstructor.is_accepted == True,
        models.CourseInstructor.instructor_id == user.id).first()

    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access denied")
    course_query = db.query(models.Course).filter(
        models.Course.course_code == code)
    course_query.update(new_course.dict(), synchronize_session=False)
    db.commit()
    return course_query.first()


@router.get("/", response_model=List[schemas.CourseOut])
def get_courses(db: Session = Depends(get_db),
                user: schemas.TokenUser = Depends(oauth2.get_current_user), semester: int = 1,
                search: Optional[str] = None, faculty: Optional[str] = None, level: Optional[int] = None,
                skip: int = 0, limit: int = 10):
    courses_query = db.query(models.Course).filter(
        models.Course.semester == semester) 
    if search:
        print(search)
        courses_query = courses_query.filter(func.lower(models.Course.title).contains(search.lower()) | func.lower(models.Course.course_code).contains(search.lower())
        )
    if faculty:
        courses_query = courses_query.filter(models.Course.faculty == faculty)
    if level:
        courses_query = courses_query.filter(models.Course.level == level)
    courses_query.limit(limit).offset(skip*limit)
    return courses_query.all()


@router.get("/enrollments", response_model=List[schemas.CourseOut])
def get_enrollments(db: Session = Depends(get_db),
                    user: schemas.TokenUser = Depends(oauth2.get_current_user), semester: int = 1,
                    title: Optional[str] = None, faculty: Optional[str] = None, level: Optional[int] = None,
                    skip: int = 0, limit: int = 10):
    if user.is_instructor:
        courses_query = db.query(models.Course).join(models.CourseInstructor,
                                                     models.Course.course_code ==
                                                     models.CourseInstructor.course_code).filter(
            models.CourseInstructor.instructor_id == int(user.id), models.Course.semester == semester)
    if not user.is_instructor:
        courses_query = db.query(models.Course).join(models.Enrollment,
                                                     models.Course.course_code ==
                                                     models.Enrollment.course_code).filter(
            models.Enrollment.reg_num == int(user.id), models.Course.semester == semester)
    if title:
        courses_query = courses_query.filter(
            models.Course.title.contains(title))
    if faculty:
        courses_query = courses_query.filter(models.Course.faculty == faculty)
    if level:
        courses_query = courses_query.filter(models.Course.level == level)
    courses_query.limit(limit).offset(skip*limit)
    return courses_query.all()


@router.get("/faculties", response_model=schemas.Faculty)
def get_faculties(db: Session = Depends(get_db), user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    faculties = db.query(models.Course.faculty).distinct().all()
    faculties = [f for (f, ) in faculties]
    faculties = {"faculties": faculties}
    return faculties


@router.get("/{code}", response_model=schemas.CourseOut)
def get_courses(code: str, db: Session = Depends(get_db), user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    course = db.query(models.Course).filter(
        models.Course.course_code == code).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"course with code {code} already exists")
    return course


@router.get("/{code}/assessments", response_model=List[schemas.AssessmentOut])
def get_all_assessment(code: str, is_active: bool = None, is_marked: bool = None, db: Session = Depends(get_db),
                       user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    if user.is_instructor:
        instructor = db.query(models.CourseInstructor).filter(
            models.CourseInstructor.course_code == code,
            models.CourseInstructor.instructor_id == user.id,
            models.CourseInstructor.is_coordinator == True).first()
        if not instructor:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if not user.is_instructor:
        student = db.query(models.Enrollment).filter(
            models.Enrollment.reg_num == user.id, models.Enrollment.course_code == code).first()
        if not student:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    assessment_query = db.query(models.Assessment).filter(
        models.Assessment.course_id == code)
    current_time = datetime.now()
    if is_active != None:
        assessment = assessment_query.filter(
            models.Assessment.is_active == is_active, models.Assessment.end_date < current_time).all()
    if is_marked == True:
        assessment = assessment_query.filter(
            models.Assessment.is_marked == True).all()
    else:
        assessment = assessment_query.all()
    return assessment


@router.delete("/{code}", status_code=204)
def delete_courses(code: str, db: Session = Depends(get_db), user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    instructor = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == code,
        models.CourseInstructor.instructor_id == user.id,
        models.CourseInstructor.is_coordinator == True).first()

    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access denied")
    photo_path = os.path.join(config.PHOTO_DIR, "courses", code)
    if os.path.exists(photo_path):
        os.remove(photo_path)
    course_query = db.query(models.Course).filter(
        models.Course.course_code == code)
    course_query.delete(synchronize_session=False)
    db.commit()
