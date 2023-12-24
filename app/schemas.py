from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, StrictInt, ValidationError, conint, validator, constr
from datetime import timedelta, datetime


class Course(BaseModel):
    course_code: str
    title: str
    description: str
    units: int
    faculty: str
    semester: conint(le=2, ge=1)
    level: int

    class Config:
        orm_mode = True


class CourseOut(Course):
    course_photo_url: Optional[str] = None


class Faculty(BaseModel):
    faculties: List[str]

    class Config:
        orm_mode = True


class User(BaseModel):
    title: Optional[str] = None
    name: str
    email: EmailStr
    department: constr(max_length=3, min_length=3)
    faculty: str
    level: Optional[int] = None
    major: Optional[str] = None
    bio: Optional[str] = None


class UserCreate(User):
    password: str
    title: Optional[str] = None
    id: Optional[str] = None


class UserPassword(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('passwords do not match')
        return v


class UserOut(User):
    id: str
    is_instructor: Optional[bool] = None
    title: Optional[str] = None
    photo_url: Optional[str]

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str
    is_instructor: bool


class TokenData(BaseModel):
    id: Optional[str] = None
    is_instructor: bool


class TokenUser(BaseModel):
    id: str
    is_instructor: bool


class EnrollInstructor(BaseModel):
    course_code: str
    instructor_id: str
    is_coordinator: bool
    is_accepted: bool

    class Config:
        orm_mode = True


class EnrollStudent(BaseModel):
    course_code: str
    reg_num: Optional[int]
    accepted: Optional[bool] = False


class EnrollInstructor(BaseModel):
    course_code: str

class EnrollStudentOut(EnrollStudent):
    id: str

    class Config:
        orm_mode = True

class IsEnrolled(BaseModel):
    enrolled: bool

class StudentsEnrolled(BaseModel):
    reg_num: int
    name: str
    department: str
    level: str
    accepted: bool
    photo_url: str

    class Config: 
        orm_mode: True

class CourseInstructorEnrolledOut(BaseModel):
    instructor_id: str
    is_current_user: bool
    department: str
    name: str
    title: str
    photo_url: str

    class Config:
        orm_mode: True

class Assessment(BaseModel):
    title: str
    start_date: datetime
    duration: int
    total_mark: int
    course_id: str
    is_active: bool = False
    is_marked: bool = False
    assessment_type: Literal['Assignment', 'Test', 'Exam']
    end_date: datetime

    # @validator('start_date')
    # def check_start(cls, v):
    #     current_time = datetime.now()
    #     if v < (current_time + timedelta(minutes=20)):
    #             raise ValueError('assessment should be created or updated atleast an hour before the test')
    #     return v

    # @validator('end_date')
    # def dates_check(cls, v, values, **kwargs):
    #     if v != None:
    #         if 'start_date' in values and v <= values['start_date']:
    #             raise ValueError('end_date should be greater than start_date')
    #     return v

class AssessmentSchedule(BaseModel):
    start_date: datetime
    duration: int
    end_date: datetime
    course_id: str


class AssessmentOut(Assessment):
    id: str
    is_completed: bool

    class Config:
        orm_mode = True


class Instruction(BaseModel):
    instruction: str


class Instructions(BaseModel):
    assessment_id: int
    instructions: List[str]


class InstructionOut(Instruction):
    id: str
    assessment_id: str

    class Config:
        orm_mode = True


class Question(BaseModel):
    question: str
    mark: int
    question_type: Literal['obj', 'sub_obj', 'nlp', 'maths']
    tolerance: Optional[float] = None
    is_multi_choice: bool
    num_answer: Optional[int] = None
    assessment_id: str


class QuestionUpdate(BaseModel):
    question: str
    mark: int
    question_type: Literal['obj', 'sub_obj', 'nlp', 'maths']
    tolerance: Optional[float] = None
    num_answer: Optional[int] = None
    is_multi_choice: bool


class QuestionOut(Question):
    id: str

    class Config:
        orm_mode = True


class Option(BaseModel):
    option: str
    is_correct: bool


class OptionOut(Option):
    id: str

    class Config:
        orm_mode = True


class Options(BaseModel):
    question_id: str
    options: List[Option]


class Submission(BaseModel):
    question_id: str
    stu_answer: Optional[str] = None
    stu_answer_id: Optional[str] = None


class SubmissionUpdate(BaseModel):
    stu_answer: Optional[str] = None
    stu_answer_id: Optional[str]


class Submissions(BaseModel):
    assessment_id: str
    submissions: List[Submission]


class QuestionAnswer(QuestionOut):
    answers: Optional[List[OptionOut]] = None


class StuAnswer(BaseModel):
    stu_answer: str = None
    stu_answer_id: int = None


class ReviewQuestionAnswer(QuestionOut):
    answers: Optional[List[OptionOut]] = None
    stu_answers: StuAnswer
    stu_mark: float


class AssessmentReview(Assessment):
    id: str
    questions: Optional[List[QuestionAnswer]] = None
    instructions: Optional[List[InstructionOut]] = None


class StuAssessmentReview(Assessment):
    id: str
    questions: Optional[List[ReviewQuestionAnswer]] = None
    instructions: Optional[List[InstructionOut]] = None
    total: float

    class Config:
        orm_mode = True


class AssessmentQuestion(Assessment):
    id: str
    questions: Optional[List[QuestionOut]] = None
    instructions: Optional[List[InstructionOut]] = None

    class Config:
        orm_mode = True


class AssessmentResultsStats(BaseModel):
    name: str
    reg_num: int
    total: float
    photo_url: str = None
    start_datetime: datetime
    end_datetime: datetime
    assessment_time: float

    class Config:
        orm_mode = True
