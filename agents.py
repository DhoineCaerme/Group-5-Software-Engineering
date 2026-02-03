import os
from crewai import Agent, LLM
from cogito_rag import rag_tool 
from dotenv import load_dotenv

load_dotenv()

MY_KEY = "AIzaSyBpHRCgUK4zOJhC8watW9H9Ym9KkQpBMyg"

os.environ["GEMINI_API_KEY"] = MY_KEY
os.environ["GOOGLE_API_KEY"] = MY_KEY

# Configure the Brain (Flash Model)
my_llm = LLM(
    model="gemini/gemini-2.5-flash-lite", 
    api_key=MY_KEY  
)

# === AGENT DEFINITIONS WITH STRICT LIMITS ===

# Manager/Synthesist Agent (NO tools - just analyzes)
synthesist_agent = Agent(
    role='Lead Software Architect',
    goal='Analyze the debate and create a final JSON decision matrix.',
    backstory="""You are a CTO who synthesizes arguments into decisions. 
    You DO NOT search for information - you only analyze what is given to you.
    Always respond with valid JSON only.""",
    verbose=True,
    allow_delegation=False,  # Prevent delegation loops
    max_iter=3,  # Maximum iterations
    max_rpm=10,  # Rate limit
    llm=my_llm
)

# Thesis Agent (Limited tool use)
thesis_agent = Agent(
    role='Proponent Architect',
    goal='Make exactly 3 SHORT points supporting the topic. Use the search tool only ONCE if needed.',
    backstory="""You argue IN FAVOR of the topic. 
    RULES:
    - Search the database AT MOST ONCE for supporting facts
    - Write exactly 3 concise sentences
    - Do NOT keep searching - one search is enough
    - If you don't find perfect evidence, make your argument anyway""",
    verbose=True,
    allow_delegation=False,
    max_iter=5,  # Limit iterations to prevent loops
    max_rpm=10,
    tools=[rag_tool], 
    llm=my_llm
)

# Antithesis Agent (Limited tool use)
antithesis_agent = Agent(
    role='Skeptical Architect',
    goal='Make exactly 3 SHORT points criticizing the topic. Use the search tool only ONCE if needed.',
    backstory="""You argue AGAINST the topic and find risks.
    RULES:
    - Search the database AT MOST ONCE for counter-evidence
    - Write exactly 3 concise sentences about risks/flaws
    - Do NOT keep searching - one search is enough
    - If you don't find perfect evidence, make your argument anyway""",
    verbose=True,
    allow_delegation=False,
    max_iter=5,  # Limit iterations to prevent loops
    max_rpm=10,
    tools=[rag_tool],
    llm=my_llm
)