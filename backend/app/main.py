import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models, schemas, services
from .database import Base, engine, get_db
from .scraper import ScrapeError


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Recipe Extractor & Meal Planner", version="1.0.0")

configured_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        os.getenv("FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173"),
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/recipes/extract", response_model=schemas.RecipeResponse)
def extract_recipe(request: schemas.ExtractRequest, db: Session = Depends(get_db)):
    try:
        return services.extract_and_store_recipe(db, str(request.url))
    except ScrapeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/recipes", response_model=list[schemas.RecipeHistoryItem])
def recipe_history(db: Session = Depends(get_db)):
    return services.list_recipes(db)


@app.get("/recipes/{recipe_id}", response_model=schemas.RecipeResponse)
def recipe_details(recipe_id: int, db: Session = Depends(get_db)):
    recipe = services.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@app.post("/meal-plan", response_model=schemas.MealPlanResponse)
def meal_plan(request: schemas.MealPlanRequest, db: Session = Depends(get_db)):
    try:
        return services.build_meal_plan(db, request.recipe_ids)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
