from fastapi import FastAPI, Form, Response, status, HTTPException, Depends, APIRouter,  File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi.encoders import jsonable_encoder
from datetime import datetime


from sqlalchemy import func
# from sqlalchemy.sql.functions import func
from .. import models, schemas, oauth2
from ..database import get_db
import pandas as pd
import numpy as np


router = APIRouter(
    prefix="/submissions",
    tags=['Submission']
)


@router.post("/", status_code=status.HTTP_201_CREATED)
def make_submission(submissions: schemas.Submissions,
                    user: schemas.TokenUser = Depends(oauth2.get_current_user),
                    db: Session = Depends(get_db)):
    is_eligible = db.query(models.Assessment).join(
        models.Enrollment, models.Assessment.course_id == models.Enrollment.course_code
    ).filter(models.Assessment.id == submissions.assessment_id, models.Enrollment.reg_num == user.id).count() > 0
    if not is_eligible:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    # assessment_questions = db.query(models.Assessment.id, models.Question.id, models.Option.id).join(
    #     models.Question, models.Assessment.id == models.Question.assessment_id).join(
    #     models.Option, models.Question.id == models.Option.question_id).filter(
    #     models.Option.is_correct == True, models.Assessment.id == submissions.assessment_id).all()
    # assessment_df = pd.DataFrame.from_records(assessment_questions,
    #                                             columns=['assessment_id', 'question_id', 'Option_id'])

    # print(assessment_df.shape)
    # stu_ans_df: pd.DataFrame= pd.DataFrame(jsonable_encoder(submissions.submissions),)
    # print(stu_ans_df.shape)
    print("health check")
    sub_query = db.query(models.Submission).filter(models.Submission.assessment_id == submissions.assessment_id,
                                                   models.Submission.student_id == user.id)
    if sub_query.first() != None:
        return Response(status_code=status.HTTP_201_CREATED)
    
    submission_df: pd.DataFrame = pd.DataFrame(
        jsonable_encoder(submissions.submissions),)
    print(submission_df)
    # submission_df.rename(columns={"Option_id":"ref_answer_id"}, inplace=True)
    submission_df['stu_answer_id'].replace(
        np.NaN, -1, inplace=True)  # to change column back to int
    submission_df['stu_answer_id'] = submission_df['stu_answer_id'].astype(int)
    print(submission_df.shape)
    print("here")
    print(submission_df.stu_answer_id.values)
    responses = submission_df.to_dict('records')
    print(len(responses))
    stu_subs = []
    for response in responses:
        # print(response['stu_answer_id'])
        submission = models.Submission(
            **response, student_id=user.id, assessment_id=submissions.assessment_id)
        stu_subs.append(submission)

    assessment_times = db.query(models.AssessmentTimeRecords).filter(models.AssessmentTimeRecords.assessment_id == submissions.assessment_id, models.AssessmentTimeRecords.student_id == user.id).first()

    assessment_times.end_datetime = datetime.now()

    db.add_all(stu_subs)
    db.commit()
    db.refresh(assessment_times)
    return Response(status_code=status.HTTP_201_CREATED)
