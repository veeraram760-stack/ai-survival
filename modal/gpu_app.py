import modal
import os
from typing import Optional, Dict, Any

app = modal.App("ai-survival-gpu")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install(
        "fastapi",
        "uvicorn",
        "openai",
        "anthropic",
        "httpx",
        "pandas",
        "numpy",
        "plotly",
        "python-dotenv",
        "tenacity",
        "scikit-learn",
        "torch",
        "transformers",
        "accelerate",
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
    retries=modal.Retries(max_retries=3),
)
async def run_agent_task(agent_type: str, task_data: dict) -> dict:
    import httpx
    import os
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
        execution_time = (end_time - start_time).total_seconds()

        return {
            "status": "success",
            "task_id": task_id,
            "agent_type": agent_type,
            "output": output,
            "execution_time": execution_time,
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


@app.function(
    image=image,
    gpu="A10G",
    volumes={"/data": volume},
    timeout=3600,
)
async def train_model(model_config: dict) -> dict:
    """Train a small ML model on GPU"""
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from datetime import datetime, timezone

    task_id = model_config.get("task_id", "unknown")
    model_type = model_config.get("model_type", "simple_nn")
    epochs = model_config.get("epochs", 10)

    start_time = datetime.now(timezone.utc)
    try:
        # Simple example model
        if model_type == "simple_nn":
            model = nn.Sequential(
                nn.Linear(10, 64),
                nn.ReLU(),
                nn.Linear(64, 32),
                nn.ReLU(),
                nn.Linear(32, 1),
            )
        elif model_type == "transformer":
            model = nn.Transformer(d_model=64, nhead=4, num_encoder_layers=2)
        else:
            return {"status": "failed", "error": f"Unknown model type: {model_type}", "task_id": task_id}

        # Mock training data
        x_train = torch.randn(1000, 10)
        y_train = torch.randn(1000, 1)

        criterion = nn.MSELoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)

        for epoch in range(epochs):
            optimizer.zero_grad()
            output = model(x_train)
            loss = criterion(output, y_train)
            loss.backward()
            optimizer.step()

        end_time = datetime.now(timezone.utc)

        return {
            "status": "success",
            "task_id": task_id,
            "model_type": model_type,
            "final_loss": loss.item(),
            "epochs": epochs,
            "execution_time": (end_time - start_time).total_seconds(),
            "completed_at": end_time.isoformat(),
        }
    except Exception as e:
        end_time = datetime.now(timezone.utc)
        return {
            "status": "failed",
            "task_id": task_id,
            "error": str(e),
            "completed_at": end_time.isoformat(),
        }


@app.function(
    image=image,
    gpu="A10G",
    volumes={"/data": volume},
    timeout=3600,
)
async def run_inference(inference_config: dict) -> dict:
    """Run inference with a pre-trained model"""
    import torch
    from datetime import datetime, timezone

    task_id = inference_config.get("task_id", "unknown")
    model_path = inference_config.get("model_path", "/data/model.pt")
    input_data = inference_config.get("input_data", [])

    start_time = datetime.now(timezone.utc)
    try:
        # Load model (mock)
        model = torch.jit.load(model_path) if os.path.exists(model_path) else None

        if model is None:
            # Create a simple model for demo
            model = torch.nn.Sequential(
                torch.nn.Linear(10, 64),
                torch.nn.ReLU(),
                torch.nn.Linear(64, 1),
            )

        # Run inference
        with torch.no_grad():
            input_tensor = torch.tensor(input_data, dtype=torch.float32)
            predictions = model(input_tensor).tolist()

        end_time = datetime.now(timezone.utc)

        return {
            "status": "success",
            "task_id": task_id,
            "predictions": predictions,
            "execution_time": (end_time - start_time).total_seconds(),
            "completed_at": end_time.isoformat(),
        }
    except Exception as e:
        end_time = datetime.now(timezone.utc)
        return {
            "status": "failed",
            "task_id": task_id,
            "error": str(e),
            "completed_at": end_time.isoformat(),
        }


@app.function(
    image=image,
    gpu=None,  # CPU-only for web scraping
    volumes={"/data": volume},
    timeout=300,
)
async def execute_tool(tool_name: str, params: dict) -> dict:
    """Execute a tool on Modal infrastructure"""
    import httpx
    from datetime import datetime, timezone
    from bs4 import BeautifulSoup

    task_id = params.get("task_id", "unknown")
    start_time = datetime.now(timezone.utc)

    try:
        if tool_name == "web_search":
            query = params.get("query", "")
            count = params.get("count", 5)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                )
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                results = []
                for result in soup.find_all("a", class_="result__snippet")[:count]:
                    results.append({
                        "title": result.get_text(strip=True)[:100],
                        "url": result.get("href", ""),
                        "snippet": result.get_text(strip=True),
                    })

                return {
                    "status": "success",
                    "task_id": task_id,
                    "tool": tool_name,
                    "results": results,
                    "execution_time": (datetime.now(timezone.utc) - start_time).total_seconds(),
                }

        elif tool_name == "web_fetch":
            url = params.get("url", "")
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()

                text = soup.get_text(separator="\n", strip=True)
                title = soup.title.string if soup.title else ""

                return {
                    "status": "success",
                    "task_id": task_id,
                    "tool": tool_name,
                    "url": url,
                    "title": title,
                    "content": text[:10000],
                    "execution_time": (datetime.now(timezone.utc) - start_time).total_seconds(),
                }

        elif tool_name == "api_call":
            method = params.get("method", "GET")
            url = params.get("url", "")
            headers = params.get("headers", {})
            json_data = params.get("json_data", {})

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(method, url, headers=headers, json=json_data)

                return {
                    "status": "success",
                    "task_id": task_id,
                    "tool": tool_name,
                    "status_code": response.status_code,
                    "data": response.json() if "json" in response.headers.get("content-type", "") else response.text,
                    "execution_time": (datetime.now(timezone.utc) - start_time).total_seconds(),
                }

        else:
            return {"status": "failed", "error": f"Tool '{tool_name}' not implemented on Modal", "task_id": task_id}

    except Exception as e:
        return {
            "status": "failed",
            "task_id": task_id,
            "tool": tool_name,
            "error": str(e),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }


@app.function(
    image=image,
    gpu=None,
    volumes={"/data": volume},
    timeout=300,
)
async def analyze_data(data_config: dict) -> dict:
    """Analyze data using pandas/numpy"""
    import pandas as pd
    import numpy as np
    from datetime import datetime, timezone

    task_id = data_config.get("task_id", "unknown")
    analysis_type = data_config.get("analysis_type", "summary")
    data = data_config.get("data", [])

    start_time = datetime.now(timezone.utc)
    try:
        df = pd.DataFrame(data)

        if analysis_type == "summary":
            result = {
                "shape": df.shape,
                "columns": list(df.columns),
                "dtypes": df.dtypes.astype(str).to_dict(),
                "missing": df.isnull().sum().to_dict(),
                "numeric_summary": df.describe().to_dict() if len(df.select_dtypes(include=[np.number]).columns) > 0 else {},
            }
        elif analysis_type == "correlation":
            numeric_df = df.select_dtypes(include=[np.number])
            result = {"correlation": numeric_df.corr().to_dict()} if len(numeric_df.columns) > 1 else {"error": "Not enough numeric columns"}
        else:
            result = {"error": f"Unknown analysis type: {analysis_type}"}

        return {
            "status": "success",
            "task_id": task_id,
            "analysis": result,
            "execution_time": (datetime.now(timezone.utc) - start_time).total_seconds(),
        }
    except Exception as e:
        return {
            "status": "failed",
            "task_id": task_id,
            "error": str(e),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
