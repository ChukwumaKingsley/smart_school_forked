import os
import cloudinary.uploader
from fastapi import FastAPI, File, Response, UploadFile, status, HTTPException, Depends, APIRouter
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from typing import List, Optional
import re

from sqlalchemy import func
from sqlalchemy import exc
# from sqlalchemy.sql.functions import func
from .. import models, schemas, oauth2
from ..database import get_db
from app import config, utils


router = APIRouter(
    prefix="/users",
    tags=['Users']
)


@router.post("/", response_model=schemas.UserOut, status_code=201)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):

    # hash the password - user.password
    hashed_password = utils.hash(user.password)
    user.password = hashed_password

    existing_student_email = db.query(models.Student).filter(models.Student.email == user.email).first()
    existing_instructor_email = db.query(models.Instructor).filter(models.Instructor.email == user.email).first()
    existing_regno = db.query(models.Student).filter(models.Student.id == user.id).first()

    if user.id == None:
        if not existing_instructor_email and not existing_student_email:
            new_user = models.Instructor(**user.dict())
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account with this email already exists.")
    else:
        if not existing_student_email and not existing_student_email:
            if not existing_regno:
                if (re.match(r'^20\d{9}$', str(user.id))):
                    new_user = models.Student(**user.dict())
                else:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid registration number!")
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account with this registration number already exists.")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account with this email already exists.")
              
    try:
                
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except exc.IntegrityError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="user with email already exists")

    return new_user


@router.get('/{id}', response_model=schemas.UserOut)
def get_user(id: int, db: Session = Depends(get_db), user: schemas.TokenUser = Depends(oauth2.get_current_user)):
    user = db.query(models.Instructor).filter(
        models.Instructor.id == id).first()
    if not user:
        user = db.query(models.Student).filter(models.Student.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"User with id: {id} does not exist")

    return user


@router.put('/{id}', response_model=schemas.UserOut)
def update_user(id: int, user_data: schemas.User,  db: Session = Depends(get_db), user_token: schemas.TokenUser = Depends(oauth2.get_current_user)):
    user_query = db.query(models.Instructor).filter(models.Instructor.id == id)
    if not user_query.first():
        user_query = db.query(models.Student).filter(models.Student.id == id)
        if not user_query.first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"User with id: {id} does not exist.")
    if user_query.first().id != user_token.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized to perform this action.")
    user_query.update(user_data.dict(), synchronize_session=False)
    db.commit()
    return user_query.first()


@router.put('/{id}/password', response_model=schemas.UserOut)
def update_password(id: int, user_data: schemas.UserPassword,  db: Session = Depends(get_db), user_token: schemas.TokenUser = Depends(oauth2.get_current_user)):
    user_query = db.query(models.Instructor).filter(models.Instructor.id == id)
    if not user_query.first():
        user_query = db.query(models.Student).filter(models.Student.id == id)
        if not user_query.first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"User with id: {id} does not exist")
    if user_query.first().id != user_token.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if not utils.verify(user_data.confirm_password, user_query.first().password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Password not correct")
    hashed_password = utils.hash(user_data.new_password)
    user_data.new_password = hashed_password
    user_query.update({"password": user_data.new_password},
                      synchronize_session=False)
    db.commit()
    return user_query.first()


@router.get('/', response_model=schemas.UserOut)
def get_user(user=Depends(oauth2.get_current_user), db: Session = Depends(get_db), ):
    user_ = db.query(models.Instructor).filter(
        models.Instructor.id == user.id).first()
    if not user_:
        user_ = db.query(models.Student).filter(
            models.Student.id == user.id).first()
    if not user_:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"User with id: {id} does not exist")
    user_ = jsonable_encoder(user_)
    user_['is_instructor'] = user.is_instructor
    return user_


@router.put("/{id}/photo", response_model=schemas.UserOut)
async def upload_photo(id: int, file: UploadFile = File(...),
                       user_token: schemas.TokenData = Depends(oauth2.get_current_user), db: Session = Depends(get_db)):
    user_query = db.query(models.Instructor).filter(models.Instructor.id == id)
    if not user_query.first():
        user_query = db.query(models.Student).filter(models.Student.id == id)
        if not user_query.first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"User with id: {id} does not exist")
    if user_query.first().id != user_token.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    response = cloudinary.uploader.upload(
        file.file,
        public_id="profile_picture"+str(id),
        folder="FUTOAcademia-profile-pics",
        )
    image_url = response.get("secure_url")
    user_query.update({"photo_url": image_url}, synchronize_session=False)
    db.commit()
    return user_query.first()
