import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE = (
  import.meta.env.VITE_API_BASE || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "")
).replace(/\/+$/, "");
const pageParams = new URLSearchParams(window.location.search);

function App() {
  const [activeTab, setActiveTab] = useState(pageParams.get("tab") === "history" ? "history" : "extract");
  const [url, setUrl] = useState("");
  const [recipe, setRecipe] = useState(null);
  const [history, setHistory] = useState([]);
  const [selectedRecipe, setSelectedRecipe] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const [mealPlan, setMealPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadHistory();
    const recipeId = Number(pageParams.get("recipeId"));
    const detailsId = Number(pageParams.get("detailsId"));
    if (recipeId) {
      loadRecipeIntoExtract(recipeId);
    }
    if (detailsId) {
      openDetails(detailsId);
    }
  }, []);

  async function request(path, options) {
    if (!API_BASE) {
      throw new Error("Missing VITE_API_BASE. Set it to your deployed backend URL in Vercel and redeploy the frontend.");
    }
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(formatApiError(payload.detail));
    }
    return payload;
  }

  async function loadHistory() {
    try {
      const rows = await request("/recipes");
      setHistory(rows);
    } catch (err) {
      setError(err.message);
    }
  }

  async function extractRecipe(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setRecipe(null);
    try {
      const payload = await request("/recipes/extract", {
        method: "POST",
        body: JSON.stringify({ url }),
      });
      setRecipe(payload);
      await loadHistory();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function openDetails(id) {
    setError("");
    try {
      const payload = await request(`/recipes/${id}`);
      setSelectedRecipe(payload);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadRecipeIntoExtract(id) {
    setError("");
    try {
      const payload = await request(`/recipes/${id}`);
      setRecipe(payload);
    } catch (err) {
      setError(err.message);
    }
  }

  async function createMealPlan() {
    setLoading(true);
    setError("");
    try {
      const payload = await request("/meal-plan", {
        method: "POST",
        body: JSON.stringify({ recipe_ids: selectedIds }),
      });
      setMealPlan(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function toggleRecipe(id) {
    setMealPlan(null);
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id]
    );
  }

  const canPlan = selectedIds.length >= 3 && selectedIds.length <= 5;

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Recipe Blog URL to Structured Data</p>
          <h1>Recipe Extractor & Meal Planner</h1>
          <p className="subtitle">Scrape recipe pages, generate structured insights, and save every result to PostgreSQL.</p>
        </div>
        <div className="tabs" role="tablist" aria-label="Recipe workflow tabs">
          <button className={activeTab === "extract" ? "active" : ""} onClick={() => setActiveTab("extract")}>
            Extract Recipe
          </button>
          <button className={activeTab === "history" ? "active" : ""} onClick={() => setActiveTab("history")}>
            Saved Recipes
          </button>
        </div>
      </header>

      {error && <div className="alert">{error}</div>}

      {activeTab === "extract" ? (
        <section className="panel">
          <form className="extract-form" onSubmit={extractRecipe}>
            <label htmlFor="recipe-url">Recipe blog URL</label>
            <div className="input-row">
              <input
                id="recipe-url"
                type="url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://example.com/recipe"
                required
              />
              <button type="submit" disabled={loading}>{loading ? "Extracting" : "Extract Recipe"}</button>
            </div>
            {loading && <div className="progress-line" aria-label="Extraction in progress" />}
          </form>
          {recipe ? <RecipeDetails recipe={recipe} /> : <EmptyState />}
        </section>
      ) : (
        <section className="panel">
          <HistoryTable
            history={history}
            selectedIds={selectedIds}
            onToggle={toggleRecipe}
            onDetails={openDetails}
          />
          <MealPlanner
            selectedCount={selectedIds.length}
            canPlan={canPlan}
            loading={loading}
            mealPlan={mealPlan}
            onCreate={createMealPlan}
          />
        </section>
      )}

      {selectedRecipe && (
        <DetailsModal recipe={selectedRecipe} onClose={() => setSelectedRecipe(null)} />
      )}
    </main>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <h2>Recipe output appears here after extraction</h2>
      <p>The result is stored in the database and added to Saved Recipes automatically.</p>
    </div>
  );
}

function formatApiError(detail) {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const path = Array.isArray(item.loc) ? item.loc.join(".") : "request";
        return item.msg ? `${path}: ${item.msg}` : JSON.stringify(item);
      })
      .join(" ");
  }
  return "Request failed";
}

function HistoryTable({ history, selectedIds, onToggle, onDetails }) {
  return (
    <div className="history-block">
      <div className="section-heading">
        <div>
          <h2>Saved Recipes</h2>
          <p>Previously extracted URLs stored in the database.</p>
        </div>
        <span>{history.length} total</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Plan</th>
              <th>Title</th>
              <th>Cuisine</th>
              <th>Difficulty</th>
              <th>Date extracted</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {history.map((item) => (
              <tr key={item.id}>
                <td>
                  <input
                    className="plan-check"
                    type="checkbox"
                    checked={selectedIds.includes(item.id)}
                    onChange={() => onToggle(item.id)}
                    aria-label={`Select ${item.title}`}
                  />
                </td>
                <td className="title-cell">{item.title}</td>
                <td>{item.cuisine}</td>
                <td><span className="pill">{item.difficulty}</span></td>
                <td>{new Date(item.created_at).toLocaleString()}</td>
                <td><button className="ghost" onClick={() => onDetails(item.id)}>Details</button></td>
              </tr>
            ))}
            {!history.length && (
              <tr>
                <td colSpan="6" className="muted-cell">No recipes saved yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MealPlanner({ selectedCount, canPlan, loading, mealPlan, onCreate }) {
  return (
    <div className="meal-planner">
      <div>
        <h2>Meal Planner</h2>
        <p>Select 3-5 saved recipes to generate a combined shopping list.</p>
      </div>
      <button disabled={!canPlan || loading} onClick={onCreate}>
        Generate List ({selectedCount})
      </button>
      {mealPlan && (
        <div className="shopping-grid">
          {Object.entries(mealPlan.combined_shopping_list).map(([category, items]) => (
            <InfoCard key={category} title={category}>
              <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul>
            </InfoCard>
          ))}
        </div>
      )}
    </div>
  );
}

function DetailsModal({ recipe, onClose }) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal">
        <div className="modal-head">
          <h2>{recipe.title}</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close details">Close</button>
        </div>
        <RecipeDetails recipe={recipe} compact />
      </div>
    </div>
  );
}

function RecipeDetails({ recipe, compact = false }) {
  const meta = useMemo(
    () => [
      ["Cuisine", recipe.cuisine],
      ["Prep", recipe.prep_time || "N/A"],
      ["Cook", recipe.cook_time || "N/A"],
      ["Total", recipe.total_time || "N/A"],
      ["Servings", recipe.servings],
      ["Difficulty", recipe.difficulty],
    ],
    [recipe]
  );

  return (
    <div className={compact ? "recipe-details compact" : "recipe-details"}>
      <section className="recipe-hero">
        <div>
          <p className="eyebrow">Stored recipe #{recipe.id}</p>
          <h2>{recipe.title}</h2>
          <a href={recipe.url} target="_blank" rel="noreferrer">{recipe.url}</a>
        </div>
        <div className="meta-grid">
          {meta.map(([label, value]) => (
            <div className="meta-item" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
      </section>

      <div className="details-grid">
        <InfoCard title="Ingredients">
          <ul>
            {recipe.ingredients.map((ingredient, index) => (
              <li key={`${ingredient.item}-${index}`}>
                {[ingredient.quantity, ingredient.unit, ingredient.item].filter(Boolean).join(" ")}
              </li>
            ))}
          </ul>
        </InfoCard>
        <InfoCard title="Instructions">
          <ol>{recipe.instructions.map((step, index) => <li key={index}>{step}</li>)}</ol>
        </InfoCard>
        <InfoCard title="Nutrition per serving">
          <div className="nutrition">
            <span>Calories <strong>{recipe.nutrition_estimate.calories ?? "N/A"}</strong></span>
            <span>Protein <strong>{recipe.nutrition_estimate.protein || "N/A"}</strong></span>
            <span>Carbs <strong>{recipe.nutrition_estimate.carbs || "N/A"}</strong></span>
            <span>Fat <strong>{recipe.nutrition_estimate.fat || "N/A"}</strong></span>
          </div>
        </InfoCard>
        <InfoCard title="Substitutions">
          <ul>{recipe.substitutions.map((item) => <li key={item}>{item}</li>)}</ul>
        </InfoCard>
        <InfoCard title="Shopping list">
          {Object.entries(recipe.shopping_list).map(([category, items]) => (
            <div className="category" key={category}>
              <h3>{category}</h3>
              <p>{items.join(", ")}</p>
            </div>
          ))}
        </InfoCard>
        <InfoCard title="Related recipes">
          <ul>{recipe.related_recipes.map((item) => <li key={item}>{item}</li>)}</ul>
        </InfoCard>
      </div>
    </div>
  );
}

function InfoCard({ title, children }) {
  return (
    <article className="card">
      <h2>{title}</h2>
      {children}
    </article>
  );
}

createRoot(document.getElementById("root")).render(<App />);
