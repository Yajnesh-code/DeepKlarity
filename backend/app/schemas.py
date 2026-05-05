from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ExtractRequest(BaseModel):
    url: HttpUrl


class Ingredient(BaseModel):
    quantity: str = ""
    unit: str = ""
    item: str


class NutritionEstimate(BaseModel):
    calories: int | None = None
    protein: str = ""
    carbs: str = ""
    fat: str = ""


class RecipeBase(BaseModel):
    url: str
    title: str
    cuisine: str = "Unknown"
    prep_time: str = ""
    cook_time: str = ""
    total_time: str = ""
    servings: int = Field(default=1, ge=1)
    difficulty: str = "medium"
    ingredients: list[Ingredient] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)
    nutrition_estimate: NutritionEstimate = Field(default_factory=NutritionEstimate)
    substitutions: list[str] = Field(default_factory=list)
    shopping_list: dict[str, list[str]] = Field(default_factory=dict)
    related_recipes: list[str] = Field(default_factory=list)


class RecipeResponse(RecipeBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RecipeHistoryItem(BaseModel):
    id: int
    url: str
    title: str
    cuisine: str
    difficulty: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MealPlanRequest(BaseModel):
    recipe_ids: list[int] = Field(min_length=3, max_length=5)

    @field_validator("recipe_ids")
    @classmethod
    def recipe_ids_must_be_unique(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("Select 3-5 different saved recipes.")
        return value


class MealPlanResponse(BaseModel):
    recipe_ids: list[int]
    combined_shopping_list: dict[str, list[str]]
    notes: list[str] = Field(default_factory=list)
    recipes: list[dict[str, Any]] = Field(default_factory=list)
