from sqlalchemy.orm import Session

from . import models, schemas
from .llm import generate_meal_plan_payload, generate_recipe_data
from .scraper import scrape_recipe_page


def extract_and_store_recipe(db: Session, url: str) -> models.Recipe:
    scraped = scrape_recipe_page(url)
    generated = generate_recipe_data(scraped)
    payload = schemas.RecipeBase(url=url, **generated)
    recipe = models.Recipe(
        **payload.model_dump(),
        scraped_text=scraped["text"],
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


def list_recipes(db: Session) -> list[models.Recipe]:
    return db.query(models.Recipe).order_by(models.Recipe.created_at.desc()).all()


def get_recipe(db: Session, recipe_id: int) -> models.Recipe | None:
    return db.get(models.Recipe, recipe_id)


def build_meal_plan(db: Session, ids: list[int]) -> dict:
    recipes = db.query(models.Recipe).filter(models.Recipe.id.in_(ids)).all()
    if len(recipes) != len(ids):
        found_ids = {recipe.id for recipe in recipes}
        missing_ids = [str(recipe_id) for recipe_id in ids if recipe_id not in found_ids]
        raise ValueError(f"Saved recipe IDs not found: {', '.join(missing_ids)}")

    recipes_by_id = {recipe.id: recipe for recipe in recipes}
    ordered_recipes = [recipes_by_id[recipe_id] for recipe_id in ids]
    recipe_payloads = [
        {
            "id": recipe.id,
            "title": recipe.title,
            "shopping_list": recipe.shopping_list,
        }
        for recipe in ordered_recipes
    ]
    return generate_meal_plan_payload(recipe_payloads)
