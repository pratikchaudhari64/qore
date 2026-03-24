import json
import re
import logging
import os

from google import genai
from google.genai import types
from dotenv import load_dotenv

from . import amcharts_mcp

logger = logging.getLogger(__name__)

_SKILL_DIR = os.path.join(os.path.dirname(__file__), "skill")
_skill_context_cache: str | None = None


def _load_full_skill() -> str:
    global _skill_context_cache
    if _skill_context_cache is not None:
        return _skill_context_cache

    parts = []
    skill_md = os.path.join(_SKILL_DIR, "SKILL.md")
    if os.path.exists(skill_md):
        with open(skill_md) as f:
            parts.append(f.read())

    refs_dir = os.path.join(_SKILL_DIR, "references")
    if os.path.isdir(refs_dir):
        for fname in sorted(os.listdir(refs_dir)):
            if fname.endswith(".md"):
                with open(os.path.join(refs_dir, fname)) as f:
                    parts.append(f.read())

    _skill_context_cache = "\n\n---\n\n".join(parts)
    logger.info(f"Loaded amCharts skill: {len(_skill_context_cache)} chars across {len(parts)} file(s)")
    return _skill_context_cache


SYSTEM_PROMPT = """You are QuantAI, an AI assistant that responds in structured JSON blocks.

You have full amCharts 5 documentation embedded at the end of this prompt — use it directly to build charts.

When the user provides data to visualize:
1. Use the embedded amCharts 5 reference below to select the right chart type and generate correct code — no tool calls needed for chart selection
2. Pick the most appropriate chart type for the data
3. Generate a complete amCharts 5 JavaScript function body with the user's actual data inlined

Your final response must be a valid JSON array of blocks — nothing else, no markdown fences.

Block types:
{"type": "text", "content": "Markdown text with **bold**, *italic*, `code`, bullet lists with - prefix."}
{"type": "chart", "title": "Chart Title", "code": "<amCharts 5 JS function body>"}

The code field rules:
- Valid JavaScript function body (no <script> tags)
- Receives these parameters already in scope: root, am5, am5xy, am5percent, am5map, am5radar, am5flow, am5hierarchy, am5wc, am5stock, am5themes_Animated
- Geodata available in scope: am5geodata_worldLow, am5geodata_indiaLow
- Do NOT call am5.Root.new() — root is already created
- Do NOT call root.setThemes() — already set
- Inline all data directly in the code
- Must call root.container.children.push(...) to create the chart
- End with chart.appear(1000, 100)
- CRITICAL: Never put literal newline characters inside JavaScript string literals (single or double quoted). Use \\n escape sequences or template literals (backticks) instead. Example: use "India\\n10%" not a string that spans two lines.

Decision rules:
- Pure question or topic → TEXT block only
- User gives numeric data → CHART block (after tool calls) + optional TEXT with insight
- "plot/chart/visualize" → CHART + TEXT analysis
- Data + insight requested → CHART first, then TEXT
- Keep text concise, sharp, no filler words
- You may return multiple blocks in sequence

Respond ONLY with the JSON array as your final output."""

AMCHARTS_TOOLS = [
    {
        "name": "get_quick_start",
        "description": "Get a minimal working amCharts 5 code example for a specific chart type. Returns ready-to-use code.",
        "parameters": {
            "type": "object",
            "properties": {
                "chartType": {
                    "type": "string",
                    "description": "Chart type, e.g. 'pie', 'line', 'bar', 'radar', 'sankey', 'treemap'",
                }
            },
            "required": ["chartType"],
        },
    },
    {
        "name": "get_example",
        "description": "Get full source code for a specific amCharts 5 example. Use list_examples or search_all to find the path first.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Example path, e.g. 'examples/pie-donut/donut-chart', 'examples/flow/sankey-diagram'"}
            },
            "required": ["path"],
        },
    },
]

_system_prompt_cache: str | None = None


_ENVIRONMENT_OVERRIDES = """
## CRITICAL ENVIRONMENT OVERRIDES — these override any skill/reference instructions above

This code runs inside a pre-initialised amCharts 5 environment. The following are ABSOLUTE rules:

- DO NOT call `am5.Root.new()` — `root` is already created and passed in scope
- DO NOT call `root.setThemes()` — themes are already applied
- DO NOT call `root.dispose()` — lifecycle is managed externally
- Start directly with `root.container.children.push(...)` to create the chart
- All variables (`root`, `am5`, `am5xy`, `am5percent`, `am5map`, `am5radar`, `am5flow`, `am5hierarchy`, `am5wc`, `am5stock`, `am5themes_Animated`, `am5geodata_worldLow`, `am5geodata_indiaLow`) are already in scope — do not import or redeclare them
- End the code with `chart.appear(1000, 100)`
- NEVER put literal newline characters inside single/double-quoted JS strings — use `\\n` or template literals
"""


def _get_system_prompt() -> str:
    global _system_prompt_cache
    if _system_prompt_cache is None:
        skill = _load_full_skill()
        if skill:
            _system_prompt_cache = (
                SYSTEM_PROMPT
                + "\n\n---\n\n## amCharts 5 Full Reference\n\n"
                + skill
                + "\n\n---\n\n"
                + _ENVIRONMENT_OVERRIDES
            )
        else:
            _system_prompt_cache = SYSTEM_PROMPT
    return _system_prompt_cache


_MODEL_NAME = "gemini-2.5-flash"
# "gemini-2.5-flash"
# "gemini-3-flash-preview"
# "gemini-2.5-flash"
# "gemma-3-27b-it"
# "gemini-3.1-flash-lite-preview"
_client = None

# Example environment loading method for this project across apps
env_path = os.path.join(os.path.dirname(__file__), '..', 'qore', '.env')
load_dotenv(dotenv_path=env_path)


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment")
        _client = genai.Client(api_key=api_key)
        logger.info("Gemini client initialized successfully")
    return _client


def is_client_ready() -> bool:
    try:
        _get_client()
        return True
    except Exception:
        return False


def query_gemini(prompt: str) -> list[dict]:
    client = _get_client()

    tools = [types.Tool(function_declarations=[
        types.FunctionDeclaration(**t) for t in AMCHARTS_TOOLS
    ])]

    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]

    # Agentic loop: keep going until Gemini stops calling tools
    turn = 0
    while True:
        turn += 1
        logger.info(f"[turn {turn}] Sending {len(contents)} content item(s) to Gemini")
        response = client.models.generate_content(
            model=_MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=_get_system_prompt(),
                tools=tools,
            ),
        )

        candidate = response.candidates[0]

        # Collect all tool calls from this turn
        tool_calls = [
            p.function_call
            for p in candidate.content.parts
            if p.function_call is not None
        ]

        if not tool_calls:
            # No more tool calls — extract final text response
            logger.info(f"[turn {turn}] No tool calls — extracting final response")
            break

        # Log a summary of what Gemini wants to call
        call_summary = ", ".join(
            f"{fc.name}({', '.join(f'{k}={v!r}' for k, v in dict(fc.args).items()) or ''})"
            for fc in tool_calls
        )
        logger.info(f"[turn {turn}] Gemini called {len(tool_calls)} tool(s): {call_summary}")

        # Add model's tool-call turn to history
        contents.append(candidate.content)

        # Execute each tool call and add results
        tool_results = []
        for fc in tool_calls:
            try:
                result_text = amcharts_mcp.call_tool(fc.name, dict(fc.args))
                logger.info(f"[turn {turn}] {fc.name} → {len(result_text)} chars returned")
            except Exception as e:
                result_text = f"Tool error: {e}"
                logger.info(f"[turn {turn}] {fc.name} FAILED — {e}")
            tool_results.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": result_text},
                )
            )
        contents.append(types.Content(role="user", parts=tool_results))

    # Parse final JSON response
    raw = response.text.strip()
    raw = re.sub(r"^```json\s*\n?", "", raw)
    raw = re.sub(r"^```\s*\n?", "", raw)
    raw = re.sub(r"\n?```\s*$", "", raw).strip()

    blocks = json.loads(raw)
    if not isinstance(blocks, list):
        blocks = [blocks]

    logger.info(f"Returning {len(blocks)} block(s)")
    return blocks
