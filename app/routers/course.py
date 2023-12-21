import os
import cloudinary.uploader
from fastapi import FastAPI, File, Response, UploadFile, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from typing import List, Optional

from sqlalchemy import func, or_

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
    
    # Trim the title element to keep only the first 60 characters
    trimmed_title = course.title[:60].strip()
    trimmed_description = course.description[:300].strip()

    new_course = models.Course(**course.dict())
    new_course.title = trimmed_title
    new_course.description = trimmed_description

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
    
    transformation = {
        "width": 400,  # Set the desired width
        "height": 400,  # Set the desired height
        "crop": "fill",  # Use 'fill' to fill the entire dimensions, maintaining aspect ratio
    }
    response = cloudinary.uploader.upload(
        file.file,
        public_id="course-photo-"+code,
        folder="FUTOAcademia-course-photo",
        transformation=transformation
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
    
    new_course.title = new_course.title[:60].strip()
    new_course.description = new_course.description[:300].strip()
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

@router.get("/{code}/enrollment_status")
def get_enrollment_status(code: str, db: Session = Depends(get_db),
                       user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    is_course_instructor = False
    is_course_coordinator = False
    is_enrolled = False
    enrollment_pending = False
    instructor_enrollment_pending = False

    if user.is_instructor:
        instructor = db.query(models.CourseInstructor).filter(
            models.CourseInstructor.course_code == code,
            models.CourseInstructor.instructor_id == user.id,
            or_(models.CourseInstructor.is_coordinator == True, models.CourseInstructor.is_accepted == True)).first()
        if db.query(models.CourseInstructor).filter(
            models.CourseInstructor.course_code == code,
            models.CourseInstructor.instructor_id == user.id,
            models.CourseInstructor.is_coordinator == True).first():
            is_course_coordinator = True
        if db.query(models.CourseInstructor).filter(
            models.CourseInstructor.course_code == code,
            models.CourseInstructor.instructor_id == user.id, models.CourseInstructor.is_accepted == True).first():
            is_course_instructor = True
        if db.query(models.CourseInstructor).filter(
            models.CourseInstructor.course_code == code,
            models.CourseInstructor.instructor_id == user.id, models.CourseInstructor.is_accepted == False).first():
            instructor_enrollment_pending = True
        
        if not instructor:
            is_course_instructor = False
            is_course_coordinator = False

    if not user.is_instructor:
        if db.query(models.Enrollment).filter(models.Enrollment.reg_num == user.id, models.Enrollment.course_code == code, models.Enrollment.accepted == True).first():
            is_enrolled = True
        if db.query(models.Enrollment).filter(models.Enrollment.reg_num == user.id, models.Enrollment.course_code == code, models.Enrollment.accepted == False).first():
            enrollment_pending = True

    return {"is_course_instructor": is_course_instructor, "is_course_coordinator": is_course_coordinator, "instructor_enrollment_pending": instructor_enrollment_pending, "is_enrolled": is_enrolled, "enrollment_pending": enrollment_pending}

@router.get("/{code}/assessments", response_model=List[schemas.AssessmentOut])
def get_all_assessment(code: str, is_active: bool = None, is_marked: bool = None, is_completed: bool = None, db: Session = Depends(get_db),
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
        assessment_query = assessment_query.filter(
            models.Assessment.is_active == is_active, models.Assessment.end_date < current_time)
    if is_marked != None:
        assessment_query = assessment_query.filter(
            models.Assessment.is_marked == is_marked)
    if is_completed != None:
        assessment_query = assessment_query.filter(
            models.Assessment.is_completed == is_completed)
        
    assessment = assessment_query.all()
    return assessment

@router.get("/assessments_results_stats/{course_code}")
def get_course_assessment_stats(course_code: str, db: Session = Depends(get_db), user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    if not user.is_instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized.")

    # Check if the course exists
    course = db.query(models.Course).filter(models.Course.course_code == course_code).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # Get all assessments for the course
    assessments = db.query(models.Assessment).filter(models.Assessment.course_id == course_code).all()

    assessment_stats = []
    for assessment in assessments:
        # Calculate statistics for each assessment
        num_students = db.query(models.Score).filter(models.Score.assessment_id == assessment.id).distinct(models.Score.student_id).count()
        avg_score = db.query(func.avg(models.Total.total)).filter(models.Total.assessment_id == assessment.id).scalar()
        avg_time_query = db.query(func.avg(models.AssessmentTimeRecords.end_datetime - models.AssessmentTimeRecords.start_datetime)).filter(models.AssessmentTimeRecords.assessment_id == assessment.id)
        avg_time_seconds = avg_time_query.scalar() if avg_time_query.scalar() else 0
        highest_score = db.query(func.max(models.Total.total)).filter(models.Total.assessment_id == assessment.id).scalar()
        lowest_score = db.query(func.min(models.Total.total)).filter(models.Total.assessment_id == assessment.id).scalar()

        # Additional statistics
        total_mark = assessment.total_mark
        avg_score_percentage = (avg_score / total_mark) * 100 if avg_score is not None else 0

        # Calculate the percentage of students enrolled in the course that made submissions
        num_enrolled_students = db.query(models.Enrollment).filter(models.Enrollment.course_code == course_code, models.Enrollment.accepted.is_(True)).count()
        percentage_submissions = (num_students / num_enrolled_students) * 100 if num_enrolled_students > 0 else 0

        # Note: You need to add logic for calculating the most frequent score based on your data model.

        assessment_stats.append({
            "id": assessment.id,
            "title": assessment.title,
            "type": assessment.assessment_type,
            "num_students": num_students,
            "avg_score": round(avg_score, 1),
            "avg_score_percentage": round(avg_score_percentage, 1),
            "avg_time": round(avg_time_seconds.total_seconds()/60, 1),
            "highest_score": highest_score,
            "lowest_score": lowest_score,
            "percentage_submissions": round(percentage_submissions, 1),
            # Add other statistics as needed
        })

    return assessment_stats

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
