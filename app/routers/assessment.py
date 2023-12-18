from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy.orm import joinedload, subqueryload, contains_eager

from sqlalchemy import func
# from sqlalchemy.sql.functions import func
from .. import models, schemas, oauth2
from datetime import timedelta, datetime
from ..database import get_db
from ..config import settings
from datetime import datetime
from fastapi import BackgroundTasks


router = APIRouter(
    prefix="/assessments",
    tags=['Assessments']
)

@router.post("/", response_model=schemas.AssessmentOut)
def create_assessment(assessment: schemas.Assessment, db: Session = Depends(get_db),
                      user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    instructor = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == assessment.course_id,
        models.CourseInstructor.is_accepted == True,
        models.CourseInstructor.instructor_id == user.id).first()
    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access denied")

    # only create assessment two hours into the future
    current_time = datetime.now()
    if assessment.start_date < current_time:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="Start date/time should be in the future.")
    
    if assessment.start_date >= assessment.end_date:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="End date/time should be later than start date/time.")

    new_assessment = models.Assessment(**assessment.dict())
    db.add(new_assessment)
    db.commit()
    db.refresh(new_assessment)
    return new_assessment


@router.put("/{id}", response_model=schemas.AssessmentOut)
def update_assessment(updated_assessment: schemas.Assessment, id: int, db: Session = Depends(get_db),
                      user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    instructor = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == updated_assessment.course_id,
        models.CourseInstructor.is_accepted == True,
        models.CourseInstructor.instructor_id == user.id).first()
    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access denied")
    assessment_query = db.query(models.Assessment).filter(
        models.Assessment.id == id)
    assessment_detail = assessment_query.first()
    if not assessment_detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"assessment not found")
    
    assessment_query.update(updated_assessment.dict(),
                            synchronize_session=False)
    db.commit()
    db.refresh(assessment_query.first())
    return assessment_query.first()


@router.put("/edit-schedule/{id}", response_model=schemas.AssessmentOut)
def edit_schedule(updated_assessment: schemas.AssessmentSchedule, id: int, db: Session = Depends(get_db),
                      user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    instructor = db.query(models.CourseInstructor).filter(
        models.CourseInstructor.course_code == updated_assessment.course_id,
        models.CourseInstructor.is_accepted == True,
        models.CourseInstructor.instructor_id == user.id).first()
    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access denied")
    assessment_query = db.query(models.Assessment).filter(
        models.Assessment.id == id)
    assessment_detail = assessment_query.first()
    if not assessment_detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"assessment with not found")

    current_time = datetime.now()

    if (updated_assessment.start_date < current_time):
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="Start date/time must be in the future.")
    
    if assessment_detail.is_active and (assessment_detail.start_date < current_time):
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="Cannot edit schedule of live assessment.")
    
    if (assessment_detail.is_completed or assessment_detail.is_marked):
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="Cannot edit schedule of ended assessment.")
    
    if (updated_assessment.start_date >= updated_assessment.end_date):
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="End date/time should be later than start date/time.")
    
    assessment_query.update(updated_assessment.dict(), synchronize_session=False)
    db.commit()
    db.refresh(assessment_query.first())
    return assessment_query.first()

@router.put("/{id}/activate", status_code=status.HTTP_201_CREATED)
def activate_assessment(id: int, db: Session = Depends(get_db),
                      user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    instructor = db.query(models.Assessment).join(
        models.CourseInstructor, models.CourseInstructor.course_code == models.Assessment.course_id
    ).filter(models.CourseInstructor.is_accepted == True,
             models.CourseInstructor.instructor_id == user.id, models.Assessment.id == id).first()
    
    questions = db.query(models.Question).filter(models.Question.assessment_id == id).all()

    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access denied")
    assessment_query = db.query(models.Assessment).filter(
        models.Assessment.id == id)
    assessment_detail = assessment_query.first()
    if not assessment_detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"assessment not found")
    current_time = datetime.now()
    if not questions:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="Assessment must have at least one question")
    if assessment_detail.start_date < (current_time):
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                            detail="Update start date/time to a later date/time")
    assessment_query.update({"is_active": True},
                            synchronize_session=False)
    db.commit()
    return

@router.put("/{id}/deactivate", status_code=status.HTTP_201_CREATED)
def deactivate_assessment(id: int, db: Session = Depends(get_db),
                      user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    
    assessment_query = db.query(models.Assessment).filter(
        models.Assessment.id == id).first()
    assessment_query.update({"is_active": False},
                            synchronize_session=False)
    db.commit()
    return

@router.put("/{id}/end-automatic", status_code=status.HTTP_201_CREATED)
def end_assessment_automatic(id: int, db: Session = Depends(get_db),
                      user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    
    assessment_query = db.query(models.Assessment).filter(
        models.Assessment.id == id)
    
    if not assessment_query.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")
    current_time = datetime.now()
    if current_time >= assessment_query.first().end_date:
        assessment_query.update({"is_active": False, "is_completed": True}, synchronize_session=False)

    db.commit()
    return

@router.put("/{id}/end-manual", status_code=status.HTTP_201_CREATED)
def end_assessment_automatic(id: int, db: Session = Depends(get_db),
                      user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    
    assessment_query = db.query(models.Assessment).filter(
        models.Assessment.id == id)
    
    assessment_query.update({"is_active": False, "is_completed": True},
                            synchronize_session=False)
    db.commit()
    return

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assessment(id: int, db: Session = Depends(get_db),
                      user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    assessment_query = db.query(models.Assessment).filter(
        models.Assessment.id == id)
    assessment_detail = assessment_query.first()
    if not assessment_detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"assessment with id -> {id} not found")
    instructor = db.query(models.Assessment).join(
        models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code).filter(
        models.Assessment.id == id,
        models.CourseInstructor.instructor_id == user.id,
        models.CourseInstructor.is_accepted == True).first()
    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access denied")
    assessment_query.delete(synchronize_session=False)
    db.commit()


@router.get("/{id}/review", response_model=schemas.AssessmentReview)
def review_assessment(id: int, db: Session = Depends(get_db),
                      user: schemas.TokenUser = Depends(oauth2.get_current_user)):    
    assessment_query = db.query(models.Assessment).filter(
        models.Assessment.id == id)
    assessment_detail = assessment_query.first()
    if not assessment_detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"assessment with id -> {id} not found")
    if user.is_instructor:
        instructor = db.query(models.Assessment).join(
            models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code
        ).filter(models.CourseInstructor.instructor_id == user.id, models.Assessment.id == id,
                 models.CourseInstructor.is_accepted == True).first()
        if not instructor:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if not user.is_instructor:
        student = db.query(models.Assessment).join(
            models.Enrollment, models.Assessment.course_id == models.Enrollment.course_code
        ).filter(models.Enrollment.reg_num == user.id, models.Assessment.id == id).first()
        if not student:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        # only review after some hours
        current_time = datetime.now()
        review_after = assessment_detail.start_date + \
            assessment_detail.duration + timedelta(hours=settings.review_after)
        if review_after < current_time:
            raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                                detail="can only create an assignment to start at a time 1 hour ahead of {current_time}")
    assessment = db.query(models.Assessment).options(
        joinedload(models.Assessment.instructions)).options(
        joinedload(models.Assessment.questions)).options(
        joinedload(models.Assessment.questions, models.Question.answers)).filter(
        models.Assessment.id == id).first()
    print(assessment)
    assessment_dict = jsonable_encoder(assessment)
    return assessment_dict


@router.get("/{id}/assessment_questions", response_model=schemas.AssessmentReview)
def get_assessment_questions(id: int, db: Session = Depends(get_db),
                             user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    assessment_query = db.query(models.Assessment).filter(
        models.Assessment.id == id)
    assessment_detail = assessment_query.first()
    if not assessment_detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"assessment with id -> {id} not found")
    if user.is_instructor:
        instructor = db.query(models.Assessment).join(
            models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code
        ).filter(models.CourseInstructor.instructor_id == user.id, models.Assessment.id == id,
                 models.CourseInstructor.is_accepted == True).first()
        if not instructor:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if not user.is_instructor:
        student = db.query(models.Assessment).join(
            models.Enrollment, models.Assessment.course_id == models.Enrollment.course_code
        ).filter(models.Enrollment.reg_num == user.id, models.Assessment.id == id).first()
        if not student:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        # # only view question in period of exam
        current_time = datetime.now()
        # if not ((current_time <= assessment_detail.end_date) and (current_time > assessment_detail.start_date)):
        #     raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        #                         detail=f"test has either ended or not started at this time:{current_time}")
        # if assessment_detail.start_date > current_time:
        #     raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        #                         detail=f"test is yet to start")
        # if current_time > assessment_detail.end_date:
        #     raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        #                         detail=f"test is has ended")
        submission = db.query(models.Submission).filter(models.Submission
                                                        .assessment_id == id, models.Submission.student_id == user.id).first()
        if submission:
            assessment = db.query(models.Assessment).options(
                joinedload(models.Assessment.instructions)).filter(
                models.Assessment.id == id).first()
            assessment.questions = []
            assessment_dict = jsonable_encoder(assessment)

            return assessment_dict
            
    assessment = db.query(models.Assessment).options(
        joinedload(models.Assessment.instructions)).options(
        joinedload(models.Assessment.questions)).options(
        joinedload(models.Assessment.questions, models.Question.answers)).filter(
        models.Assessment.id == id).first()
    print(assessment)
    assessment_dict = jsonable_encoder(assessment)
    for i, question in enumerate(assessment_dict['questions']):
        if not question['question_type'] == 'obj':
            assessment_dict['questions'][i]['answers'] = []
    return assessment_dict


@router.get("/{id}/questions", response_model=schemas.AssessmentQuestion)
def get_assessment_questions(id: int, db: Session = Depends(get_db),
                             user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    
    assessment_query = db.query(models.Assessment).filter(
        models.Assessment.id == id)
    assessment_detail = assessment_query.first()
    if not assessment_detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"assessment with id -> {id} not found")
    if user.is_instructor:
        instructor = db.query(models.Assessment).join(
            models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code
        ).filter(models.CourseInstructor.instructor_id == user.id, models.Assessment.id == id,
                 models.CourseInstructor.is_accepted == True).first()
        if not instructor:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if not user.is_instructor:
        student = db.query(models.Assessment).join(
            models.Enrollment, models.Assessment.course_id == models.Enrollment.course_code
        ).filter(models.Enrollment.reg_num == user.id, models.Assessment.id == id).first()
        if not student:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        # access questions only within assessment time frame
        current_time = datetime.now()
        end_time = assessment_detail.start_date + assessment_detail.duration
        if (assessment_detail.start_date < current_time) or (current_time > end_time):
            raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                                detail="can only create an assignment to start at a time 1 hour ahead of {current_time}")

    assessment = db.query(models.Assessment).options(
        joinedload(models.Assessment.instructions)).options(
        joinedload(models.Assessment.questions)).filter(
        models.Assessment.id == id).first()
    print(assessment)

    return assessment


@router.get("/{id}", response_model=schemas.AssessmentOut)
def get_assessment(id: int, db: Session = Depends(get_db),
                   user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    
    if user.is_instructor:
        instructor = db.query(models.Assessment).join(
            models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code
        ).filter(models.CourseInstructor.instructor_id == user.id, models.Assessment.id == id,
                 models.CourseInstructor.is_accepted == True).first()
        if not instructor:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if not user.is_instructor:
        student = db.query(models.Assessment).join(
            models.Enrollment, models.Assessment.course_id == models.Enrollment.course_code
        ).filter(models.Enrollment.reg_num == user.id, models.Assessment.id == id).first()
        if not student:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    assessment = db.query(models.Assessment).filter(
        models.Assessment.id == id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"assessment with id -> {id} not found")
    return assessment


@router.get("/{id}/results", response_model=List[schemas.AssessmentResults])
def get_assessment_results(id: int, name: Optional[str] = None, db: Session = Depends(get_db),
                           user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    
    if user.is_instructor:
        instructor = db.query(models.Assessment).join(
            models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code
        ).filter(models.CourseInstructor.instructor_id == user.id, models.Assessment.id == id,
                 models.CourseInstructor.is_accepted == True).first()
        if not instructor:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if not user.is_instructor:
        student = db.query(models.Assessment).join(
            models.Enrollment, models.Assessment.course_id == models.Enrollment.course_code
        ).filter(models.Enrollment.reg_num == user.id, models.Assessment.id == id).first()
        if not student:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    total_query = db.query(models.Enrollment.reg_num, models.Total.total, models.Student.name,
                           models.Student.photo_url).join(
        models.Total, models.Enrollment.reg_num == models.Total.student_id,).join(models.Student,
                                                                                  models.Total.student_id == models.Student.id).filter(
        models.Total.assessment_id == id
    ).order_by(models.Total.total.desc())
    if name != None:
        total_query = total_query.filter(
            models.Student.name.contains(name))
    return total_query.all()


@router.get("/{id}/stu_results", response_model=schemas.StuAssessmentReview)
def get_assessment_results(id: int, db: Session = Depends(get_db),
                           user: schemas.TokenUser = Depends(oauth2.get_current_user)):

    if user.is_instructor:
        instructor = db.query(models.Assessment).join(
            models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code
        ).filter(models.CourseInstructor.instructor_id == user.id, models.Assessment.id == id,
                 models.CourseInstructor.is_accepted == True).first()
        if not instructor:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if not user.is_instructor:
        student = db.query(models.Assessment).join(
            models.Enrollment, models.Assessment.course_id == models.Enrollment.course_code
        ).filter(models.Enrollment.reg_num == user.id, models.Assessment.id == id).first()
        if not student:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    # total = db.query(models.Enrollment.reg_num, models.Total.total, models.Student.name,
    #                  models.Student.photo_url).join(
    #     models.Total, models.Enrollment.reg_num == models.Total.student_id).join(models.Student,
    #                                                                               models.Total.student_id == models.Student.id).filter(
    #     models.Total.assessment_id == id, models.Total.student_id == user.id
    # ).all()
    total = db.query(models.Total).filter(models.Total.assessment_id == id,
                                          models.Total.student_id == user.id).first()
    submissions = db.query(models.Submission).filter(models.Submission.assessment_id == id,
                                                     models.Submission.student_id == user.id).all()
    scores = db.query(models.Score).filter(models.Score.assessment_id == id,
                                           models.Score.student_id == user.id).all()
    assessment = db.query(models.Assessment).options(
        joinedload(models.Assessment.instructions)).options(
        joinedload(models.Assessment.questions)).options(
        joinedload(models.Assessment.questions, models.Question.answers)).filter(
        models.Assessment.id == id).first()
    total_dict = jsonable_encoder(total)
    submissions_dict = jsonable_encoder(submissions)
    score_dict = jsonable_encoder(scores)
    assessment_dict = jsonable_encoder(assessment)
    # # print(submissions_dict)
    print(score_dict)
    print(submissions_dict)
    for i, question in enumerate(assessment_dict['questions']):
        answer_dic = {"stu_answer": 0, "stu_answer_id": 0}
        for sub in submissions_dict:
            if sub['question_id'] == question['id']:
                if not question['question_type'] == 'obj':
                    answer_dic['stu_answer'] = sub['stu_answer']
                else:
                    answer_dic['stu_answer_id'] = sub['stu_answer_id']
                assessment_dict['questions'][i]['stu_answers'] = answer_dic
        for score in score_dict:
            if score['question_id'] == question['id']:
                assessment_dict['questions'][i]['stu_mark'] = score['score']
    assessment_dict['total'] = total_dict['total']
    return assessment_dict
