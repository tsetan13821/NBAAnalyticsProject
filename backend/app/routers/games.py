from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.db import DbConn
from app.routers import NOT_FOUND
from app.schemas.games import Prediction, PredictionRequest
from app.services import games as games_service
from app.services.tree_model import TreeEnsemble

router = APIRouter(prefix="/games", tags=["games"])


def get_model(request: Request) -> TreeEnsemble:
    return request.app.state.next_game_model


@router.post("/predict", response_model=Prediction, responses=NOT_FOUND, summary="Predict a game's winner")
def predict_game(conn: DbConn, model: Annotated[TreeEnsemble, Depends(get_model)], body: PredictionRequest):
    return games_service.predict_game(conn, model, body)
