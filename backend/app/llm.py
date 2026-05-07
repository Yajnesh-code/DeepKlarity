import json
import os
import re
from pathlib import Path
from typing import Any

import requests


PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def generate_recipe_data(scraped: dict[str, Any]) -> dict[str, Any]:
    prompt = _render_prompt("recipe_extraction_prompt.txt", scraped)
    if os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY"):
        try:
            recipe = _call_llm_json(prompt)
            recipe["nutrition_estimate"] = _call_llm_json(
                _render_recipe_prompt("nutrition_prompt.txt", recipe)
            )
            recipe["substitutions"] = _call_llm_json(
                _render_recipe_prompt("substitution_prompt.txt", recipe)
            )
            return _normalize_recipe(recipe, scraped)
        except Exception:
            pass
    return _normalize_recipe(_fallback_recipe(scraped), scraped)


def generate_meal_plan_payload(recipes: list[dict[str, Any]]) -> dict[str, Any]:
    if os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY"):
        try:
            prompt = (PROMPT_DIR / "meal_planning_prompt.txt").read_text(encoding="utf-8")
            combined = _call_llm_json(
                prompt.replace("{recipes_json}", json.dumps(recipes, ensure_ascii=False))
            )
            return {
                "recipe_ids": [recipe["id"] for recipe in recipes],
                "combined_shopping_list": combined,
                "notes": ["Generated from selected saved recipes."],
                "recipes": [{"id": recipe["id"], "title": recipe["title"]} for recipe in recipes],
            }
        except Exception:
            pass

    combined: dict[str, list[str]] = {}
    for recipe in recipes:
        for category, items in (recipe.get("shopping_list") or {}).items():
            combined.setdefault(category, [])
            for item in items:
                if item not in combined[category]:
                    combined[category].append(item)

    return {
        "recipe_ids": [recipe["id"] for recipe in recipes],
        "combined_shopping_list": combined,
        "notes": [
            "Quantities are merged by ingredient name where available.",
            "Review package sizes before shopping because source recipes may use different serving counts.",
        ],
        "recipes": [{"id": recipe["id"], "title": recipe["title"]} for recipe in recipes],
    }


def _render_prompt(filename: str, scraped: dict[str, Any]) -> str:
    template = (PROMPT_DIR / filename).read_text(encoding="utf-8")
    replacements = {
        "{url}": scraped["url"],
        "{title_hint}": scraped["title_hint"],
        "{json_ld}": json.dumps(scraped.get("json_ld", {}), ensure_ascii=False),
        "{scraped_text}": scraped["text"],
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def _render_recipe_prompt(filename: str, recipe: dict[str, Any]) -> str:
    template = (PROMPT_DIR / filename).read_text(encoding="utf-8")
    return template.replace("{recipe_json}", json.dumps(recipe, ensure_ascii=False))


def _call_llm_json(prompt: str) -> Any:
    if os.getenv("GROQ_API_KEY"):
        return _call_langchain_groq(prompt)
    try:
        return _call_langchain_gemini(prompt)
    except ImportError:
        return _call_gemini_rest(prompt, os.environ["GEMINI_API_KEY"])


def _call_langchain_gemini(prompt: str) -> Any:
    from langchain_google_genai import ChatGoogleGenerativeAI

    model = ChatGoogleGenerativeAI(model=DEFAULT_MODEL, temperature=0.2)
    response = model.invoke(prompt)
    return _coerce_recipe_json(response.content)


def _call_langchain_groq(prompt: str) -> Any:
    from langchain_groq import ChatGroq

    model = ChatGroq(model=DEFAULT_GROQ_MODEL, temperature=0.2)
    response = model.invoke(prompt)
    return _coerce_recipe_json(response.content)


def _call_gemini_rest(prompt: str, api_key: str) -> Any:
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{DEFAULT_MODEL}:generateContent?key={api_key}"
    )
    response = requests.post(
        endpoint,
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "response_mime_type": "application/json"},
        },
        timeout=45,
    )
    response.raise_for_status()
    text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    return _coerce_recipe_json(text)


def _coerce_recipe_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    if text.startswith("["):
        match = re.search(r"\[.*\]", text, re.DOTALL)
        return json.loads(match.group(0) if match else text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("LLM did not return a JSON object.")
    return json.loads(match.group(0))


def _normalize_recipe(recipe: dict[str, Any], scraped: dict[str, Any]) -> dict[str, Any]:
    ingredients = recipe.get("ingredients") or []
    normalized_ingredients = []
    for ingredient in ingredients:
        if isinstance(ingredient, str):
            normalized_ingredients.append(_split_ingredient(ingredient))
        elif isinstance(ingredient, dict):
            item = str(ingredient.get("item") or ingredient.get("name") or "").strip()
            if item:
                quantity, unit = _clean_ingredient_parts(
                    ingredient.get("quantity"),
                    ingredient.get("unit"),
                )
                normalized_ingredients.append(
                    {
                        "quantity": quantity,
                        "unit": unit,
                        "item": item,
                    }
                )

    nutrition = recipe.get("nutrition_estimate") or {}
    if not isinstance(nutrition, dict):
        nutrition = {}

    return {
        "title": str(recipe.get("title") or scraped["title_hint"]),
        "cuisine": str(recipe.get("cuisine") or "Unknown"),
        "prep_time": str(recipe.get("prep_time") or ""),
        "cook_time": str(recipe.get("cook_time") or ""),
        "total_time": str(recipe.get("total_time") or ""),
        "servings": _servings(recipe.get("servings")),
        "difficulty": str(recipe.get("difficulty") or "medium").lower(),
        "ingredients": normalized_ingredients
        or [{"quantity": "", "unit": "", "item": "Ingredients unavailable"}],
        "instructions": [str(step) for step in recipe.get("instructions") or [] if str(step).strip()]
        or ["Review the source page for detailed preparation steps."],
        "nutrition_estimate": {
            "calories": _calories(nutrition.get("calories")),
            "protein": _macro(nutrition.get("protein")),
            "carbs": _macro(nutrition.get("carbs")),
            "fat": _macro(nutrition.get("fat")),
        },
        "substitutions": [str(item) for item in recipe.get("substitutions") or []][:3],
        "shopping_list": _normalize_shopping_list(
            recipe.get("shopping_list") or _shopping_list(normalized_ingredients)
        ),
        "related_recipes": [str(item) for item in recipe.get("related_recipes") or []][:3],
    }


def _calories(value: Any) -> int | None:
    if value is None:
        return None
    match = re.search(r"\d+", str(value))
    return int(match.group(0)) if match else None


def _macro(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, (int, float)):
        return f"{value:g}g"
    text = str(value).strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return f"{text}g"
    return text


def _clean_ingredient_parts(quantity: Any, unit: Any) -> tuple[str, str]:
    quantity_text = str(quantity or "").strip()
    unit_text = str(unit or "").strip()
    if unit_text and quantity_text.lower().endswith(f" {unit_text.lower()}"):
        quantity_text = quantity_text[: -len(unit_text)].strip()
    return quantity_text, unit_text


def _normalize_shopping_list(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    normalized = {}
    for category, items in value.items():
        if isinstance(items, str):
            items = [items]
        cleaned_items = [str(item).strip() for item in items or [] if str(item).strip()]
        if cleaned_items:
            normalized[str(category).lower()] = cleaned_items
    return normalized


def _fallback_recipe(scraped: dict[str, Any]) -> dict[str, Any]:
    data = scraped.get("json_ld") or {}
    ingredients = [_split_ingredient(item) for item in data.get("recipeIngredient", [])]
    instructions = data.get("recipeInstructions", [])
    if instructions and isinstance(instructions[0], dict):
        instructions = [item.get("text", "") for item in instructions if item.get("text")]

    text_lines = [line.strip() for line in scraped["text"].splitlines() if line.strip()]
    if not ingredients:
        ingredients = [_split_ingredient(line) for line in text_lines if _looks_like_ingredient(line)][:12]
    if not instructions:
        instructions = [line for line in text_lines if _looks_like_step(line)][:10]

    title = data.get("name") or scraped["title_hint"]
    cuisine = _string_or_unknown(data.get("recipeCuisine"))
    return {
        "title": title,
        "cuisine": cuisine,
        "prep_time": _duration(data.get("prepTime")),
        "cook_time": _duration(data.get("cookTime")),
        "total_time": _duration(data.get("totalTime")),
        "servings": _servings(data.get("recipeYield")),
        "difficulty": "easy" if len(instructions) <= 6 else "medium",
        "ingredients": ingredients or [{"quantity": "", "unit": "", "item": "Ingredients unavailable"}],
        "instructions": instructions or ["Review the source page for detailed preparation steps."],
        "nutrition_estimate": {"calories": None, "protein": "", "carbs": "", "fat": ""},
        "substitutions": [
            "Use olive oil instead of butter where suitable.",
            "Choose whole-grain alternatives for added fiber.",
            "Adjust salt and spice levels to taste.",
        ],
        "shopping_list": _shopping_list(ingredients),
        "related_recipes": ["Simple green salad", "Roasted vegetables", "Soup pairing"],
    }


def _split_ingredient(text: str) -> dict[str, str]:
    match = re.match(r"^([\d./\s]+)?\s*([a-zA-Z]+)?\s*(.+)$", text.strip())
    if not match:
        return {"quantity": "", "unit": "", "item": text.strip()}
    quantity, unit, item = match.groups()
    return {"quantity": (quantity or "").strip(), "unit": (unit or "").strip(), "item": item.strip()}


def _looks_like_ingredient(line: str) -> bool:
    return bool(re.match(r"^(\d|[¼½¾⅓⅔])", line)) and len(line.split()) <= 12


def _looks_like_step(line: str) -> bool:
    verbs = ("heat", "mix", "stir", "cook", "bake", "add", "serve", "combine", "place", "whisk")
    return line[:1].isdigit() or line.lower().startswith(verbs)


def _duration(value: Any) -> str:
    if not value:
        return ""
    value = str(value)
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", value)
    if not match:
        return value
    hours, mins = match.groups()
    parts = []
    if hours:
        parts.append(f"{hours} hr")
    if mins:
        parts.append(f"{mins} mins")
    return " ".join(parts)


def _servings(value: Any) -> int:
    if isinstance(value, list):
        value = value[0] if value else 1
    match = re.search(r"\d+", str(value or "1"))
    return int(match.group(0)) if match else 1


def _string_or_unknown(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "Unknown"
    return str(value or "Unknown")


def _shopping_list(ingredients: list[dict[str, str]]) -> dict[str, list[str]]:
    pantry_words = ("salt", "pepper", "oil", "flour", "sugar", "spice", "rice", "pasta")
    dairy_words = ("milk", "cheese", "butter", "cream", "yogurt")
    produce_words = ("onion", "tomato", "garlic", "lettuce", "lemon", "potato", "carrot")
    shopping = {"pantry": [], "dairy": [], "produce": [], "other": []}
    for ingredient in ingredients:
        item = ingredient["item"]
        lowered = item.lower()
        if any(word in lowered for word in dairy_words):
            category = "dairy"
        elif any(word in lowered for word in produce_words):
            category = "produce"
        elif any(word in lowered for word in pantry_words):
            category = "pantry"
        else:
            category = "other"
        shopping[category].append(item)
    return {key: value for key, value in shopping.items() if value}
