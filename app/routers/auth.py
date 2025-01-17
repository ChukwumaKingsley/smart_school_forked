from fastapi import APIRouter, Depends, status, HTTPException, Response
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import database, schemas, models, utils, oauth2

router = APIRouter(tags=['Authentication'])


@router.post('/login', response_model=schemas.Token)
def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    is_instructor = False
    user = db.query(models.Student).filter(
        models.Student.email == user_credentials.username).first()
    if not user:
        user = db.query(models.Instructor).filter(
            models.Instructor.email == user_credentials.username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid username or password!")
        is_instructor = True
    if not utils.verify(user_credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid username or password!")

    # create a token
    # return token

    access_token = oauth2.create_access_token(
        data={"user_id": user.id, "is_instructor": is_instructor})

    return {"access_token": access_token, "token_type": "bearer", "is_instructor": is_instructor}
