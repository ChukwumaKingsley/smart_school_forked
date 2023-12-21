from fastapi import FastAPI, Form, Response, status, HTTPException, Depends, APIRouter,  File, UploadFile
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from fastapi.encoders import jsonable_encoder

from sqlalchemy import func

# +
# from sqlalchemy.sql.functions import func
from .. import models, schemas, oauth2
from ..database import get_db
from app import utils
import pandas as pd
import numpy as np
from sqlalchemy import exc
from datetime import timedelta, datetime

router = APIRouter(
    prefix="/marks",
    tags=['Mark']
)


def mark_obj(df):
    df['score'] = df.apply(lambda x: x['mark'] if (
        x['ref_answer_id'] == (x['stu_answer_id'])) else 0, axis=1)
    columns = ['assessment_id', 'question_id', 'student_id', 'score']
    return df[columns]


def check_multi_choice_answers(user_answers: Dict[int, List[int]], correct_answers: Dict[int, List[int]]) -> int:
    is_correct = 0

    for question_id, correct_answer in correct_answers.items():
        user_answer = user_answers.get(question_id, [])

        if set(user_answer) == set(correct_answer):
            is_correct = 1

    return is_correct


def mark_multi_obj(df, assessment_id):
    result_df = pd.DataFrame(
        columns=['assessment_id', 'question_id', 'student_id', 'score'])
    questions = df["question_id"].unique().tolist()
    users = df["student_id"].unique().tolist()
    for question in questions:
        correct_answers = df[df['question_id'] ==
                             question]['ref_answer_id'].unique().tolist()
        score = df[df['question_id'] == question]['mark'].iloc[0]
        correct_answers_dict = {question: correct_answers}
        for user in users:
            user_answers = df[(df['question_id'] == question) & (
                df["student_id"] == user)]['stu_answer_id'].unique().tolist()
            user_answers_dict = {question: user_answers}
            is_correct = check_multi_choice_answers(
                user_answers_dict, correct_answers_dict)
            row = {'assessment_id': assessment_id, 'question_id': question,
                   'student_id': user, 'score': is_correct*score}
            new_df = pd.DataFrame([row])
            result_df = pd.concat([result_df, new_df],
                                  axis=0, ignore_index=True)
    return result_df


def text_comparison(ref: str, student_ans: str):
    ref = ref.lower()
    student_ans = student_ans.lower()
    if student_ans in ref:
        return 1
    return 0


def mark_sub_obj(df):
    df['score'] = df.apply(lambda x: text_comparison(
        x['ref_answer'], x['stu_answer']) * x['mark'], axis=1)
    columns = ['assessment_id', 'question_id', 'student_id', 'score']
    return df[columns]


def mark_multiple_sub(df, assessment_id):
    result_df: pd.DataFrame = pd.DataFrame({'assessment_id': pd.Series(dtype='int'),
                                            'question_id': pd.Series(dtype='int'),
                                            'student_id': pd.Series(dtype='int'), 'score': pd.Series(dtype='float')})
    questions = df["question_id"].unique().tolist()
    users = df["student_id"].unique().tolist()
    for question in questions:
        correct_answers = df[df['question_id'] ==
                             question]["ref_answer"].unique().tolist()
        mark = df[df['question_id'] == question]['mark'].iloc[0]
        num_answer = int(df[df['question_id'] == question]
                         ['num_answer'].iloc[0])
        correct_answers_dict = {question: correct_answers}
        for user in users:
            user_answers = df[(df['question_id'] == question) & (
                df["student_id"] == user)]['stu_answer'].unique().tolist()
            user_answers_dict = {question: user_answers}
            sum_score = check_sub_answers(
                user_answers_dict, correct_answers_dict)
            row = {'assessment_id': assessment_id, 'question_id': question,
                   'student_id': user, 'score': sum_score*mark/num_answer}
            new_df = pd.DataFrame([row])
            result_df = pd.concat([result_df, new_df],
                                  axis=0, ignore_index=True)
    return result_df


def check_sub_answers(user_answers: Dict[int, List[str]], correct_answers: Dict[int, List[str]]) -> int:
    sum_score = 0

    for question_id, correct_answer in correct_answers.items():
        user_answer = user_answers.get(question_id, [])
        for answer in correct_answer:
            for stu_answer in user_answer:
                score = text_comparison(answer, stu_answer)
                sum_score += score

    return sum_score


def mark_multiple_nlp(df: pd.DataFrame, assessment_id):
    nlp_df: pd.DataFrame = pd.DataFrame(columns=[
                                        'assessment_id', 'question_id', 'student_id', 'ref_answer', 'stu_answer', 'num_answer', 'mark', 'score'])
    questions = df["question_id"].unique().tolist()
    users = df["student_id"].unique().tolist()
    for question_id in questions:
        ref_answers = df[df['question_id'] ==
                         question_id]["ref_answer"].unique().tolist()
        num_answer = int(df[df['question_id'] == question_id]
                         ['num_answer'].iloc[0])
        student_answers = df[df['question_id'] ==
                             question_id][['stu_answer', 'student_id', 'mark']]
        answers = student_answers['stu_answer'].tolist()
        ids = student_answers['student_id'].tolist()
        marks = student_answers['mark'].tolist()
        for count, answer in enumerate(ref_answers):
            scores = predict_nlp(answer, answers)
            for i, id in enumerate(ids):
                row = {"assessment_id": assessment_id, "question_id": question_id, "student_id": id,
                       'ref_answer': answer, 'stu_answer': answers[i], 'num_answer': num_answer, 'mark': marks[i], "score": scores[i]}
                new_df = pd.DataFrame([row])
                nlp_df = pd.concat([nlp_df, new_df], axis=0, ignore_index=True)
    nlp_df['score'] = nlp_df['score'].map(utils.score_mapping)
    print(nlp_df)
    score_df = process_multi_nlp(nlp_df, assessment_id=assessment_id)
    return score_df


def process_multi_nlp(df: pd.DataFrame, assessment_id):
    score_df: pd.DataFrame = pd.DataFrame(
        columns=['assessment_id', 'question_id', 'student_id', 'score'])

    questions = df["question_id"].unique().tolist()
    users = df["student_id"].unique().tolist()
    for question_id in questions:
        num_answer = df[df['question_id'] == question_id]['num_answer'].iloc[0]
        mark = df[df['question_id'] == question_id]['mark'].iloc[0]
        for user in users:
            score = df[(df['question_id'] == question_id) & (df['student_id'] == user)].sort_values(
                by="score", ascending=False)['score'][:num_answer].sum()
            score = score/num_answer * mark
            row = {"assessment_id": assessment_id, "question_id": question_id,
                   "student_id": user, "score": score}
            new_df = pd.DataFrame([row])
            score_df = pd.concat([score_df, new_df], axis=0, ignore_index=True)

    return score_df


def mark_single_nlpxxxx(df: pd.DataFrame, assessment_id):
    print("marking singe")
    score_df: pd.DataFrame = pd.DataFrame(
        columns=['assessment_id', 'question_id', 'student_id', 'ref_answer', 'stu_answer', 'mark', 'score'])
    questions = df["question_id"].unique().tolist()
    users = df["student_id"].unique().tolist()
    for question_id in questions:
        ref_answer = df[df['question_id'] == question_id]['ref_answer'].iloc[0]
        student_answers = df[df['question_id'] ==
                             question_id][['stu_answer', 'student_id', 'mark']]
        answers = student_answers['stu_answer'].tolist()
        ids = student_answers['student_id'].tolist()
        marks = student_answers['mark'].tolist()
        scores = predict_nlp(ref_answer, answers)
        for i, id in enumerate(ids):
            row = {"assessment_id": assessment_id, "question_id": question_id, "student_id": id,
                   'ref_answer': ref_answer, 'stu_answer': answers[i], 'mark': marks[i], "score": scores[i]}
            new_df = pd.DataFrame([row])
            score_df = pd.concat([score_df, new_df], axis=0, ignore_index=True)
    score_df['score'] = score_df['score'].map(utils.score_mapping)
    score_df['score'] = score_df['score'] * score_df['mark']
    score_df = score_df[['assessment_id',
                         'question_id', 'student_id', 'score']]
    return score_df

def mark_single_nlp(df: pd.DataFrame, assessment_id):
    print("marking singe")
    score_df: pd.DataFrame = pd.DataFrame(
        columns=['assessment_id', 'question_id', 'student_id', 'ref_answer', 'stu_answer', 'mark', 'score'])
    questions = df["question_id"].unique().tolist()
    users = df["student_id"].unique().tolist()
    for question_id in questions:
        ref_answer = df[df['question_id'] == question_id]['ref_answer'].iloc[0]
        student_answers = df[df['question_id'] ==
                             question_id][['stu_answer', 'student_id', 'mark']]
        answers = student_answers['stu_answer'].tolist()
        ids = student_answers['student_id'].tolist()
        marks = student_answers['mark'].tolist()
        scores = predict_nlp(ref_answer, answers)
        print(answers, ids, marks, scores)
        for i, id in enumerate(ids):
            print(i, id)
            row = {"assessment_id": assessment_id, "question_id": question_id, "student_id": id,
                   'ref_answer': ref_answer, 'stu_answer': answers[i], 'mark': marks[i], "score": scores[i]}
            new_df = pd.DataFrame([row])
            score_df = pd.concat([score_df, new_df], axis=0, ignore_index=True)
    score_df['score'] = score_df['score'].map(utils.score_mapping)
    score_df['score'] = score_df['score'] * score_df['mark']
    score_df = score_df[['assessment_id',
                         'question_id', 'student_id', 'score']]
    return score_df




def predict_nlp(ref_answer: str, stu_answers: List[str]):
    payload = {
        "inputs": {
            "source_sentence": ref_answer,
            "sentences": stu_answers
        }
    }
    scores = utils.query(payload=payload)
    return scores


def mark_maths(df: pd.DataFrame, assessment_id: str):
    df['tolerance'] = df['tolerance'].fillna(0)
    columns = ['assessment_id', 'question_id', 'student_id', 'score']
    df['score'] = df.apply(lambda x: x['mark'] if ((float(x['stu_answer']) >= (float(x['ref_answer']) - x['tolerance'])) and
                           (float(x['stu_answer']) <= (float(x['ref_answer']) + x['tolerance']))) else 0, axis=1)
    return df[columns]


@router.post("/{id}")
def mark_assessment(id: int, db: Session = Depends(get_db),
                    user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    if not user.is_instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    instructor = db.query(models.Assessment).join(
        models.CourseInstructor, models.Assessment.course_id == models.CourseInstructor.course_code
    ).filter(models.CourseInstructor.instructor_id == user.id, models.Assessment.id == id,
             models.CourseInstructor.is_accepted == True).first()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    assessment_query = db.query(models.Assessment).filter(
        models.Assessment.id == id)
    assessment_detail = assessment_query.first()
    if not assessment_detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"assessment with id -> {id} not found")
    current_time = datetime.now()
    end_time = assessment_detail.start_date + \
        timedelta(minutes=(assessment_detail.duration + 60))
    # if current_time < end_time:
    #     raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
    # print(db.query(models.Submission.ref_answer_id).filter(
    #     models.Submission.assessment_id == id).all())
    total_question_mark = db.query(func.sum(models.Question.mark)).group_by(
        models.Question.assessment_id).filter(
        models.Question.assessment_id == id).scalar()
    submissions = db.query(models.Assessment.id, models.Question.id,
                           models.Question.mark, models.Question.question_type, models.Question.is_multi_choice,
                           models.Question.tolerance, models.Question.num_answer, models.Option.id, models.Option.option, models.Submission.student_id,
                           models.Submission.stu_answer, models.Submission.stu_answer_id).join(
        models.Question, models.Assessment.id == models.Question.assessment_id).join(
        models.Option, models.Question.id == models.Option.question_id).join(
        models.Submission, models.Submission.question_id == models.Question.id
    ).filter(models.Option.is_correct == True, models.Submission.assessment_id == id).all()
    columns = ['assessment_id', 'question_id', 'mark', 'question_type', 'is_multi_choice', 'tolerance', 'num_answer', 'ref_answer_id', 'ref_answer', 'student_id',
               'stu_answer', 'stu_answer_id',]
    sub_df = pd.DataFrame.from_records(submissions,
                                       columns=columns)
    obj_df: pd.DataFrame = sub_df[(sub_df.question_type == 'obj') &
                                  (sub_df.is_multi_choice == False)]
    multi_obj_df: pd.DataFrame = sub_df[(sub_df.question_type == 'obj')
                                        & (sub_df.is_multi_choice == True)]
    sub_obj_df: pd.DataFrame = sub_df[(sub_df.question_type == 'sub_obj')
                                      & (sub_df.is_multi_choice == False)]
    sub_obj_multi_df: pd.DataFrame = sub_df[(sub_df.question_type == 'sub_obj') & (
        sub_df.is_multi_choice == True)]
    nlp_single_df: pd.DataFrame = sub_df[(sub_df.question_type == 'nlp')
                                         & (sub_df.is_multi_choice == False)]
    nlp_multiple_df: pd.DataFrame = sub_df[(sub_df.question_type == 'nlp') & (
        sub_df.is_multi_choice == True)]
    maths_df: pd.DataFrame = sub_df[(sub_df.question_type == 'maths')]

    empty_df = pd.DataFrame(
        columns=['assessment_id', 'question_id', 'student_id', 'score'])

    obj_score_df = mark_obj(obj_df) if len(obj_df) > 0 else empty_df
    multi_obj_score_df = mark_multi_obj(
        multi_obj_df, assessment_id=id) if len(multi_obj_df) > 0 else empty_df
    sub_obj_score_df = mark_sub_obj(sub_obj_df) if len(
        sub_obj_df) > 0 else empty_df
    sub_obj_multiple_df = mark_multiple_sub(
        sub_obj_multi_df, assessment_id=id) if len(sub_obj_multi_df) > 0 else empty_df
    maths_score_df = mark_maths(maths_df, assessment_id=id) if len(
        maths_df) > 0 else empty_df
    single_nlp_scores = mark_single_nlp(
        nlp_single_df, assessment_id=id) if len(nlp_single_df) > 0 else empty_df
    multiple_nlp_scores = mark_multiple_nlp(
        nlp_multiple_df, assessment_id=id) if len(nlp_multiple_df) > 0 else empty_df
    # print(obj_score_df)
    # print(multi_obj_score_df)
    # print(sub_obj_score_df)
    # print(sub_obj_multiple_df)
    # print(maths_score_df)
    df_list = [obj_score_df, multi_obj_score_df,
               sub_obj_score_df, sub_obj_multiple_df, maths_score_df, single_nlp_scores, multiple_nlp_scores]
    # df_list = [single_nlp_scores]
    score_df = pd.concat(df_list, axis=0)
    print(score_df)
    score_df.to_csv("scores_2", index=False)
    scores = score_df.to_dict('records')
    stu_scores = []
    for score in scores:
        row = models.Score(**score)
        stu_scores.append(row)
    total_df = score_df.groupby(['assessment_id', 'student_id'], as_index=False)[
        'score'].sum()
    assessment_mark = assessment_detail.total_mark
    total_df['total'] = (
        (total_df['score'] * assessment_mark)/total_question_mark).round(2)
    total_df = total_df[['assessment_id', 'student_id', 'total']]
    totals = total_df.to_dict('records')
    stu_totals = []
    for row in totals:
        total = models.Total(**row)
        stu_totals.append(total)
    try:
        db.add_all(stu_scores)
        db.add_all(stu_totals)
        assessment_query.update({"is_marked": True, "is_active": False},
                                synchronize_session=False)
        db.commit()
    except exc.IntegrityError as e:
        pass
    # try:

    #     db.commit()
    # except exc.IntegrityError as e:
    #     pass
