import modal
import os

app = modal.App("ai-survival-gpu")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install(
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "asyncpg",
        "python-dotenv",
        "openai",
        "anthropic",
        "httpx",
        "pandas",
        "numpy",
        "plotly",
        "tenacity",
        "beautifulsoup4",
        "lxml",
    )
)

volume = modal.Volume.from_name("ai-survival-data", create_if_missing=True)


@app.function(
    image=image,
    gpu="A10G",
    volumes={"/data": volume},
    timeout=3600,
    retries=modal.Retries(max_retries=3, backoff_factor=2),
)
@modal.asgi_app()
def fastapi_app():
    import sys
    sys.path.insert(0, "/app")
    from backend.main import app as fastapi_app_instance
    return fastapi_app_instance


@app.function(
    image=image,
    gpu="A10G",
    volumes={"/data": volume},
    timeout=3600,
)
async def run_agent_task(agent_type: str, task_data: dict) -> dict:
    import httpx
    from datetime import datetime, timezone

    task_id = task_data.get("task_id", "unknown")
    prompt = task_data.get("prompt", "")

    start_time = datetime.now(timezone.utc)
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"status": "failed", "error": "OPENAI_API_KEY not configured", "task_id": task_id}

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2000,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            result = response.json()
            output = result["choices"][0]["message"]["content"]

        end_time = datetime.now(timezone.utc)

        return {
            "status": "success",
            "task_id": task_id,
            "agent_type": agent_type,
            "output": output,
            "execution_time": (end_time - start_time).total_seconds(),
            "completed_at": end_time.isoformat(),
        }
    except Exception as e:
        end_time = datetime.now(timezone.utc)
        return {
            "status": "failed",
            "task_id": task_id,
            "agent_type": agent_type,
            "error": str(e),
            "completed_at": end_time.isoformat(),
        }


@app.function(
    image=image,
    gpu="A10G",
    volumes={"/data": volume},
    timeout=3600,
)
async def generate_content(content_type: str, prompt_data: dict) -> dict:
    task_id = prompt_data.get("task_id", "unknown")
    title = prompt_data.get("title", "")
    description = prompt_data.get("description", "")

    full_prompt = f"Generate {content_type} content.\nTitle: {title}\nDescription: {description}\n\nReturn structured JSON with 'title', 'body', 'cta', and 'tags' fields."

    result = await run_agent_task.remote("content", {"task_id": task_id, "prompt": full_prompt})
    return result


@app.function(
    image=image,
    gpu="A10G",
    volumes={"/data": volume},
    timeout=3600,
)
async def analyze_market(analysis_type: str, data: dict) -> dict:
    task_id = data.get("task_id", "unknown")
    symbol = data.get("symbol", "")
    timeframe = data.get("timeframe", "1d")

    prompt = f"Provide market analysis for {symbol} on {timeframe} timeframe. Include: trend direction, support/resistance levels, key indicators, risk assessment, and confidence score. Return structured JSON."

    result = await run_agent_task.remote("market", {"task_id": task_id, "prompt": prompt})
    return result


@app.function(
    image=image,
    gpu="A10G",
    volumes={"/data": volume},
    timeout=3600,
)
async def generate_outreach(lead_data: dict) -> dict:
    task_id = lead_data.get("task_id", "unknown")
    company = lead_data.get("company", "")
    contact = lead_data.get("contact", "")
    product = lead_data.get("product", "")

    prompt = f"Generate personalized sales outreach for {contact} at {company} about {product}. Include subject line, email body, and CTA. Return structured JSON."

    result = await run_agent_task.remote("sales", {"task_id": task_id, "prompt": prompt})
    return result
