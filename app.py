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
    budget: int = Field(
        description="Maximum budget in INR (₹). Extract numeric value only. If no budget is explicitly mentioned, default strictly to 80000."
    )
    
    q_perf: str = Field(
        description="Performance requirement. MUST output exactly 'A', 'B', or 'C'. "
        "'A' = Basic tasks (web browsing, MS Word). "
        "'B' = Moderate tasks (coding, light gaming, student work). "
        "'C' = Heavy tasks (3D rendering, hardcore AAA gaming, 4K video editing). "
        "NEGATIVE CONSTRAINT: Do NOT categorize words like 'portable', 'light', or 'battery' here."
    )
    
    q_port: str = Field(
        description="Portability and weight requirement. MUST output exactly 'A', 'B', or 'C'. "
        "'A' = Heavy, desk-bound laptop (user doesn't care about weight). "
        "'B' = Occasional travel. "
        "'C' = Ultra-light, Everyday Carry. "
        "KEYWORD TRIGGER: If the user mentions 'portable', 'lightweight', 'travel', or 'carry', you MUST output 'C' here."
    )
    
    q_batt: str = Field(
        description="Battery life requirement. MUST output exactly 'A', 'B', or 'C'. "
        "'A' = Always plugged in / desk-bound. "
        "'B' = Moderate battery (4-5 hours). "
        "'C' = All-day battery. "
        "KEYWORD TRIGGER: If the user mentions 'lasts all day', 'good battery', or 'long battery', you MUST output 'C' here."
    )

system_extraction_prompt = """
You are a laptop requirements extraction AI.
Extract values from the user's text and output ONLY a raw JSON object. No markdown.

STRICT RULES — each field MUST be exactly one of the letters A, B, or C:

- budget: integer in INR. Default 80000 if not stated.
- q_perf:
    A = basic (web browsing, MS Office, casual use)
    B = moderate (coding, student work, light gaming)
    C = heavy (3D rendering, AAA gaming, 4K editing)
  Note: words like 'portable', 'light', 'battery', 'travel' do NOT affect q_perf.
- q_port:
    A = desk-bound, weight doesn't matter
    B = occasional travel
    C = daily carry / frequent travel / lightweight needed
  Trigger C if user says: travel, carry, portable, lightweight, on the go.
- q_batt:
    A = always plugged in
    B = 4-5 hours
    C = all day battery / long battery life
  Trigger C if user says: all day, last all day, good battery, long battery.

Output format (example):
{"budget": 80000, "q_perf": "B", "q_port": "C", "q_batt": "C"}
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

    # 2. Normalize LLM output to valid A/B/C values
    def normalize_abc(value: str, default: str = "B") -> str:
        """Map free-text LLM output back to a valid A/B/C grade."""
        if not isinstance(value, str):
            return default
        v = value.strip().upper()
        if v in ("A", "B", "C"):
            return v
        # Common hallucinated values -> best-fit mapping
        perf_map = {"BASIC": "A", "GENERAL": "B", "MODERATE": "B", "HEAVY": "C", "HIGH": "C"}
        port_map = {"DESKBOUND": "A", "DESK-BOUND": "A", "STATIONARY": "A",
                    "OCCASIONAL": "B", "DURABLE": "B",
                    "PORTABLE": "C", "ULTRALIGHT": "C", "EVERYDAY": "C", "DAILY": "C"}
        batt_map = {"PLUGGEDIN": "A", "PLUGGED-IN": "A", "SHORT": "A",
                    "MODERATE": "B", "MEDIUM": "B",
                    "ALLDAY": "C", "ALL-DAY": "C", "LONG": "C", "LONGLASTING": "C", "LONG-LASTING": "C"}
        combined = {**perf_map, **port_map, **batt_map}
        return combined.get(v.replace(" ", ""), default)

    # 3. Run TOPSIS Math
    budget = int(extracted_data.get("budget", 80000))
    q_perf = normalize_abc(extracted_data.get("q_perf", "B"))
    q_port = normalize_abc(extracted_data.get("q_port", "B"))
    q_batt = normalize_abc(extracted_data.get("q_batt", "B"))

    # Update extracted_data so the response reflects normalized values
    extracted_data["q_perf"] = q_perf
    extracted_data["q_port"] = q_port
    extracted_data["q_batt"] = q_batt

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
