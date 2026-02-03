from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

# Import the logic from main.py
from main import run_cogito_debate

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool for running blocking debate logic
executor = ThreadPoolExecutor(max_workers=2)

# Track active debates for cancellation
active_debates = {}
debate_lock = threading.Lock()

class RequestModel(BaseModel):
    topic: str

# === TIMEOUT CONFIGURATION ===
DEBATE_TIMEOUT_SECONDS = 300  # 5 minutes max per debate


def extract_json_from_response(response_str: str) -> dict:
    """
    Extract valid JSON from LLM response that may contain extra text.
    Handles cases like:
    - JSON wrapped in ```json ... ```
    - JSON with preamble text
    - Multiple JSON objects (takes the last complete one)
    """
    
    # Clean up the response
    clean_str = str(response_str)
    
    # Remove markdown code blocks
    clean_str = re.sub(r'```json\s*', '', clean_str)
    clean_str = re.sub(r'```\s*', '', clean_str)
    
    # Try to find all JSON objects in the response
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    
    # More robust: find JSON that starts with {"thesis"
    thesis_pattern = r'\{\s*"thesis"\s*:\s*\{.*'
    match = re.search(thesis_pattern, clean_str, re.DOTALL)
    
    if match:
        json_candidate = match.group(0)
        
        # Find the matching closing brace
        brace_count = 0
        end_pos = 0
        
        for i, char in enumerate(json_candidate):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i + 1
                    break
        
        if end_pos > 0:
            json_str = json_candidate[:end_pos]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
    
    # Fallback: try to find any valid JSON object
    matches = re.findall(r'\{[^{}]*(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}[^{}]*)*\}', clean_str)
    
    # Try each match, starting from the longest (most likely to be complete)
    matches.sort(key=len, reverse=True)
    
    for match in matches:
        try:
            data = json.loads(match)
            # Check if it has the expected structure
            if 'thesis' in data or 'synthesis' in data:
                return data
        except json.JSONDecodeError:
            continue
    
    # Last resort: try the whole string
    try:
        return json.loads(clean_str)
    except:
        pass
    
    # Return error structure if nothing works
    return None


def run_debate_with_timeout(topic: str, debate_id: str):
    """Wrapper to run debate and check for cancellation."""
    try:
        # Check if cancelled before starting
        with debate_lock:
            if debate_id not in active_debates:
                return None
        
        result = run_cogito_debate(topic)
        return result
    except Exception as e:
        print(f"Debate error: {e}")
        raise


@app.post("/api/debate")
async def start_debate(request: RequestModel):
    """Start a debate with timeout protection."""
    import uuid
    debate_id = str(uuid.uuid4())
    
    print(f"\n[Debate {debate_id[:8]}] Starting: '{request.topic}'")
    
    # Register this debate as active
    with debate_lock:
        active_debates[debate_id] = True
    
    try:
        # Run the debate in a thread pool with timeout
        loop = asyncio.get_event_loop()
        
        try:
            raw_result = await asyncio.wait_for(
                loop.run_in_executor(
                    executor, 
                    run_debate_with_timeout, 
                    request.topic,
                    debate_id
                ),
                timeout=DEBATE_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            print(f"[Debate {debate_id[:8]}] TIMEOUT after {DEBATE_TIMEOUT_SECONDS}s")
            return {
                "thesis": {"title": "Timeout", "points": ["The AI agents took too long to respond."]},
                "antithesis": {"title": "Timeout", "points": ["Consider simplifying your question or trying again."]},
                "synthesis": {
                    "recommendation": "Timed Out", 
                    "summary": f"The debate exceeded the {DEBATE_TIMEOUT_SECONDS} second limit. Try rephrasing your question.", 
                    "confidence": 0
                },
                "risks": [{"severity": "medium", "title": "Processing Limit", "desc": "AI agents may loop on complex queries."}]
            }
        
        # Check if cancelled
        if raw_result is None:
            return {
                "thesis": {"title": "Cancelled", "points": ["Debate was cancelled by user."]},
                "antithesis": {"title": "Cancelled", "points": ["No arguments generated."]},
                "synthesis": {"recommendation": "Cancelled", "summary": "The debate was stopped before completion.", "confidence": 0},
                "risks": []
            }
        
        # Extract JSON from the response
        result_str = str(raw_result)
        print(f"\n[Debate {debate_id[:8]}] Raw result length: {len(result_str)} chars")
        
        # Try to extract JSON
        data = extract_json_from_response(result_str)
        
        if data:
            print(f"[Debate {debate_id[:8]}] ✅ JSON extracted successfully")
            return data
        else:
            print(f"[Debate {debate_id[:8]}] ⚠️ Could not extract JSON, returning raw text")
            # Return a structured response with the raw text
            return {
                "thesis": {"title": "Arguments For", "points": ["See raw output below"]},
                "antithesis": {"title": "Arguments Against", "points": ["See raw output below"]},
                "synthesis": {
                    "recommendation": "Review Output", 
                    "summary": result_str[:500] + "..." if len(result_str) > 500 else result_str, 
                    "confidence": 50
                },
                "risks": [{"severity": "low", "title": "Parse Issue", "desc": "Could not parse structured output, showing raw text."}]
            }

    except Exception as e:
        print(f"[Debate {debate_id[:8]}] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "thesis": {"title": "Error", "points": ["An error occurred during debate"]},
            "antithesis": {"title": "Error", "points": [str(e)[:200]]},
            "synthesis": {"recommendation": "Failed", "summary": "Check the terminal for error details.", "confidence": 0},
            "risks": [{"severity": "high", "title": "System Error", "desc": str(e)[:200]}]
        }
    finally:
        # Clean up
        with debate_lock:
            active_debates.pop(debate_id, None)


@app.post("/api/cancel")
async def cancel_debate():
    """Cancel all active debates."""
    with debate_lock:
        count = len(active_debates)
        active_debates.clear()
    print(f"[Cancel] Cleared {count} active debate(s)")
    return {"status": "cancelled", "cleared": count}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    with debate_lock:
        active = len(active_debates)
    return {"status": "ok", "active_debates": active}


if __name__ == "__main__":
    print("=" * 60)
    print("  COGITO REQUIEM API SERVER")
    print("=" * 60)
    print(f"  Timeout: {DEBATE_TIMEOUT_SECONDS} seconds per debate")
    print(f"  Endpoints:")
    print(f"    POST /api/debate  - Start a debate")
    print(f"    POST /api/cancel  - Cancel active debates")
    print(f"    GET  /api/health  - Health check")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)