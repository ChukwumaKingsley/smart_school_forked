from typing import List, Optional

from pydantic import BaseModel, EmailStr, StrictInt
from datetime import datetime


class Course(BaseModel):
    course_code: str
    title: str
    description: str
    units: int

    class Config:
        orm_mode = True

class User(BaseModel):
    name: str
    email : EmailStr

class UserCreate(User):
    password : str
    id : Optional[int] = None

class UserOut(User):
    id : int

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: Optional[str] = None
    is_instructor : bool

class TokenUser(BaseModel):
    id: int
    is_instructor : bool

class EnrollInstructor(BaseModel):
    course_code: str
    instructor_id : int
    is_coordinator : bool
    is_accepted: bool

    class Config:
        orm_mode = True

class EnrollStudent(BaseModel):
    course_code: str
    reg_num : Optional[int]
    accepted : Optional[bool] = False

class EnrollStudentOut(EnrollStudent):
    id : int
    class Config:
        orm_mode = True

class Assessment(BaseModel):

    title:str
    start_date:datetime
    duration:int
    total_mark:int
    course_id:str

class AssessmentOut(Assessment):
    id:int

    class Config:
        orm_mode = True

class Instruction(BaseModel):
    instruction : str

class Instructions(BaseModel):
    assessment_id:int
    instructions: List[str] 

class InstructionOut(Instruction):
    id: int
    assessment_id: int

    class Config:
        orm_mode = True

class Question(BaseModel):
    question:str
    mark:int
    is_multi_choice:bool
    assessment_id:int

class QuestionUpdate(BaseModel):
    question:str
    mark:int
    is_multi_choice:bool

class QuestionOut(Question):
    id:int

    class Config:
        orm_mode = True

class Option(BaseModel):
    option:str
    is_correct:bool

class OptionOut(Option):
    id:int

    class Config:
        orm_mode = True

class Options(BaseModel):
    question_id:int
    options : List[Option]

class Submission(BaseModel):
    question_id:int
    stu_answer:Optional[str] = None
    stu_answer_id: Optional[StrictInt]

class Submissions(BaseModel):
    assessment_id:int
    submissions: List[Submission] 

class QuestionAnswer(QuestionOut):
    answers : Optional[List[OptionOut]] = None

class AssessmentReview(Assessment):
    id:int
    questions: Optional[List[QuestionAnswer]] = None
    instructions : Optional[List[InstructionOut]] = None

    class Config:
        orm_mode = True

class AssessmentQuestion(Assessment):
    id:int
    questions: Optional[List[QuestionOut]] = None
    instructions : Optional[List[InstructionOut]] = None

    class Config:
        orm_mode = True



