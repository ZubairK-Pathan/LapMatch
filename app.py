import json

import ollama
import uvicorn
from ddgs import DDGS
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from models.recommender import run_lapmatch

app = FastAPI()


app.mount("/static", StaticFiles(directory="static"), name="static")


class PromptRequest(BaseModel):
    prompt: str


class LaptopRequirements(BaseModel):
    budget: int = Field(description="Maximum budget in INR (₹). Default is 80000.")
    q_perf: str = Field(
        description="Extract 'A' for Basic, 'B' for Coding/Light Gaming/Moderate, 'C' for Heavy 3D/Hardcore Gaming."
    )
    q_port: str = Field(
        description="Extract 'A' for Desk-bound heavy laptop, 'B' for Occasional Travel, "
        "'C' for Everyday Carry ultra-light."
    )
    q_batt: str = Field(description="Extract 'A' for plugged in, 'B' for 4-5 hours, 'C' for all-day battery.")


system_extraction_prompt = """
You are a brilliant intent-extraction AI. The user will state their laptop needs.
Your job is to strictly extract variables from their text and route them into the JSON schema.
Respond ONLY with raw JSON matching this schema. No markdown wrapping.
"""


def get_batch_engineer_reviews(user_prompt, laptops_data):
    lap_info = "\n".join(
        [
            f"Option {i + 1}: {lap['name']}, Price: ₹{lap['price']}, Match: {lap['score']}%"
            for i, lap in enumerate(laptops_data)
        ]
    )
    review_prompt = (
        f"User Request: '{user_prompt}'. Matches:\n{lap_info}\n"
        "Provide a brutally technical, 1-sentence rationale for EACH option. Return ONLY a JSON schema."
    )

    schema = {
        "type": "object",
        "properties": {
            "reviews": {"type": "array", "items": {"type": "string", "description": "1 sentence technical rationale"}}
        },
        "required": ["reviews"],
    }

    try:
        response = ollama.chat(
            model="llama3:8b",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Senior Hardware Engineer. "
                    "Reply strictly with the requested JSON schema array of rationales.",
                },
                {"role": "user", "content": review_prompt},
            ],
            stream=False,
            format=schema,
        )
        content = response["message"]["content"].replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        return data.get("reviews", [])
    except Exception as e:
        print(f"Batch LLM error: {e}")
        return ["Mathematical proximity map optimized."] * len(laptops_data)


@app.get("/")
async def root():
    return FileResponse("static/index.html")


def get_laptop_image(name: str):
    # used duck duck go here
    import time

    # e.g. "Acer Swift Go 14 SFG14-41" -> "Acer Swift Go 14 laptop product"
    clean_name = " ".join(name.split()[:4]) + " laptop product"

    try:
        time.sleep(0.5)  # Prevent DuckDuckGo API Rate limiting
        results = DDGS().images(clean_name, max_results=1)
        if results and len(results) > 0:
            return results[0]["image"]
    except Exception as e:
        print(f"Image Scrape failed for {name}: {e}")
    return "https://placehold.co/400x250/111827/3b82f6?text=No+Image+Found"


@app.post("/api/recommend")
async def recommend(request: PromptRequest):
    # 1. Extract Intent
    try:
        response = ollama.chat(
            model="llama3:8b",
            messages=[
                {"role": "system", "content": system_extraction_prompt},
                {"role": "user", "content": request.prompt},
            ],
            format=LaptopRequirements.model_json_schema(),
        )
        raw_json = response["message"]["content"]
        cleaned_json = raw_json.replace("```json", "").replace("```", "").strip()
        extracted_data = json.loads(cleaned_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Extraction failed: {str(e)}")

    # 2. Run TOPSIS Math
    budget = int(extracted_data.get("budget", 80000))
    q_perf = extracted_data.get("q_perf", "B")
    q_port = extracted_data.get("q_port", "B")
    q_batt = extracted_data.get("q_batt", "B")

    recommendations = run_lapmatch(budget, q_perf, q_port, q_batt, flex=0.3)

    if recommendations.empty:
        return {"error": "No laptops found under that budget."}

    # 3. Generate Engineer rationale in BATCH
    batch_input = []
    for i, row in recommendations.reset_index().iterrows():
        batch_input.append({"name": row["name"], "price": row["price"], "score": round(row["Match_Score"] * 100, 1)})

    rationales = get_batch_engineer_reviews(request.prompt, batch_input)

    results = []
    for i, row in recommendations.reset_index().iterrows():
        if i < len(rationales):
            raw_rat = rationales[i]
            if isinstance(raw_rat, dict):
                rationale = raw_rat.get("rationale", raw_rat.get("reason", raw_rat.get("review", "")))
                if not rationale and len(raw_rat) > 0:
                    rationale = str(list(raw_rat.values())[0])
            elif isinstance(raw_rat, str) and raw_rat.strip().startswith("{"):
                try:
                    inner_dict = json.loads(raw_rat)
                    rationale = inner_dict.get("rationale", inner_dict.get("reason", inner_dict.get("review", "")))
                    if not rationale and len(inner_dict) > 0:
                        rationale = str(list(inner_dict.values())[0])
                except Exception:
                    rationale = raw_rat
            else:
                rationale = str(raw_rat)
        else:
            rationale = "Algorithm determined optimal vector proximity."

        results.append(
            {
                "name": row["name"],
                "price": row["price"],
                "match_score": row["Match_Score"],
                "weight": row["Weight_Proxy"],
                "battery": row["Battery_Proxy"],
                "pitch": rationale,
                "image_url": get_laptop_image(row["name"]),
            }
        )

    return {"results": results, "calculations": {"extracted_intent": extracted_data}}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
