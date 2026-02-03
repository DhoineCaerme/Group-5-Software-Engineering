import time
from crewai import Task, Crew, Process
from agents import synthesist_agent, thesis_agent, antithesis_agent
from database import (
    get_session, DecisionRequest, DebateReport, DebateLog,
    store_evidence
)
from cogito_rag import get_evidence_log, clear_evidence_log


def run_cogito_debate(topic: str):
    """
    Run a full dialectical debate on the given topic.
    
    Process:
    1. Initialize database records
    2. Run 2 rounds of Thesis vs Antithesis
    3. Each agent uses RAG to find evidence
    4. Store all evidence in database
    5. Synthesist creates final Decision Matrix
    
    Args:
        topic: The architectural decision to debate
        
    Returns:
        Final JSON decision matrix
    """
    
    print(f"\n{'='*60}")
    print(f"🎭 COGITO REQUIEM: Dialectical Debate System")
    print(f"{'='*60}")
    print(f"📋 Topic: {topic}")
    print(f"{'='*60}\n")
    
    # ===============================================
    # 1. DATABASE INITIALIZATION
    # ===============================================
    session = get_session()
    
    # Create request record
    req = DecisionRequest(user_prompt=topic)
    session.add(req)
    session.commit()
    
    # Create report record
    report = DebateReport(request_id=req.request_id)
    session.add(report)
    session.commit()
    
    print(f"[Database]: Created request {req.request_id[:8]}...")
    
    # Track evidence count for confidence calculation
    thesis_evidence_count = 0
    antithesis_evidence_count = 0
    
    # ===============================================
    # 2. TWO-ROUND DEBATE
    # ===============================================
    
    debate_history = ""
    
    for round_num in range(1, 3):  # Rounds 1 and 2
        
        print(f"\n{'='*50}")
        print(f"📢 ROUND {round_num} OF 2")
        print(f"{'='*50}")
        
        # -------------------------------------------
        # THESIS AGENT (Pro)
        # -------------------------------------------
        print(f"\n🟢 THESIS AGENT - Arguing FOR...")
        
        # Clear evidence log before this agent's turn
        clear_evidence_log()
        
        task_thesis = Task(
            description=f"""
            DEBATE TOPIC: "{topic}"
            ROUND: {round_num} of 2
            YOUR ROLE: Argue IN FAVOR of this topic
            
            PREVIOUS ARGUMENTS:
            {debate_history[-1000:] if debate_history else "This is the opening round."}
            
            YOUR TASK:
            1. Search the knowledge base ONCE for supporting evidence
            2. Write exactly 3 sentences supporting this topic
            3. Include specific facts or citations from your search
            
            CONSTRAINTS:
            - Maximum 3 sentences
            - Use the Architecture Search Tool only ONCE
            - Focus on benefits, advantages, and success cases
            """,
            expected_output="3 concise sentences supporting the topic with evidence.",
            agent=thesis_agent
        )
        
        crew_thesis = Crew(
            agents=[thesis_agent], 
            tasks=[task_thesis], 
            verbose=True,
            process=Process.sequential
        )
        
        result_thesis = crew_thesis.kickoff()
        thesis_text = str(result_thesis)
        
        # Log to database
        thesis_log = DebateLog(
            report_id=report.report_id, 
            agent_name="Thesis", 
            round_number=round_num, 
            argument_text=thesis_text, 
            agent_role="Pro"
        )
        session.add(thesis_log)
        session.commit()
        
        # Store RAG evidence
        evidence_entries = get_evidence_log()
        if evidence_entries:
            store_evidence(session, thesis_log.log_id, evidence_entries)
            thesis_evidence_count += len(evidence_entries)
            print(f"  📚 Stored {len(evidence_entries)} evidence citations")
        
        debate_history += f"\n[Round {round_num} - THESIS]: {thesis_text}\n"
        
        # -------------------------------------------
        # ANTITHESIS AGENT (Con)
        # -------------------------------------------
        print(f"\n🔴 ANTITHESIS AGENT - Arguing AGAINST...")
        
        # Clear evidence log before this agent's turn
        clear_evidence_log()
        
        task_antithesis = Task(
            description=f"""
            DEBATE TOPIC: "{topic}"
            ROUND: {round_num} of 2
            YOUR ROLE: Argue AGAINST and find RISKS
            
            THESIS ARGUMENT TO COUNTER:
            "{thesis_text[:500]}"
            
            YOUR TASK:
            1. Search the knowledge base ONCE for counter-evidence
            2. Write exactly 3 sentences criticizing the thesis
            3. Focus on risks, challenges, and failure cases
            
            CONSTRAINTS:
            - Maximum 3 sentences
            - Use the Architecture Search Tool only ONCE
            - Be specific about risks and drawbacks
            """,
            expected_output="3 concise sentences opposing the topic with evidence.",
            agent=antithesis_agent
        )
        
        crew_antithesis = Crew(
            agents=[antithesis_agent], 
            tasks=[task_antithesis], 
            verbose=True,
            process=Process.sequential
        )
        
        result_antithesis = crew_antithesis.kickoff()
        antithesis_text = str(result_antithesis)
        
        # Log to database
        antithesis_log = DebateLog(
            report_id=report.report_id, 
            agent_name="Antithesis", 
            round_number=round_num, 
            argument_text=antithesis_text, 
            agent_role="Con"
        )
        session.add(antithesis_log)
        session.commit()
        
        # Store RAG evidence
        evidence_entries = get_evidence_log()
        if evidence_entries:
            store_evidence(session, antithesis_log.log_id, evidence_entries)
            antithesis_evidence_count += len(evidence_entries)
            print(f"  📚 Stored {len(evidence_entries)} evidence citations")
        
        debate_history += f"[Round {round_num} - ANTITHESIS]: {antithesis_text}\n"
    
    # ===============================================
    # 3. SYNTHESIS PHASE - Create Decision Matrix
    # ===============================================
    
    print(f"\n{'='*50}")
    print(f"⚖️ SYNTHESIS PHASE - Creating Decision Matrix")
    print(f"{'='*50}\n")
    
    # Calculate evidence stats for confidence
    total_evidence = thesis_evidence_count + antithesis_evidence_count
    evidence_balance = min(thesis_evidence_count, antithesis_evidence_count) / max(thesis_evidence_count, 1)
    
    print(f"[Stats] Thesis evidence: {thesis_evidence_count}, Antithesis evidence: {antithesis_evidence_count}")
    
    task_synthesis = Task(
        description=f"""
        You are the SYNTHESIST AGENT (Manager/CTO).
        
        Analyze this complete debate and create a DECISION MATRIX:
        
        TOPIC: {topic}
        
        FULL DEBATE TRANSCRIPT:
        {debate_history}
        
        EVIDENCE STATISTICS:
        - Thesis (Pro) citations found: {thesis_evidence_count}
        - Antithesis (Con) citations found: {antithesis_evidence_count}
        - Total evidence pieces: {total_evidence}
        
        Create a JSON response with this EXACT structure:
        {{
            "thesis": {{ 
                "title": "Arguments For", 
                "points": ["point 1", "point 2", "point 3"] 
            }},
            "antithesis": {{ 
                "title": "Arguments Against", 
                "points": ["point 1", "point 2", "point 3"] 
            }},
            "synthesis": {{ 
                "recommendation": "Your verdict (5 words max)", 
                "summary": "One sentence explaining the best path forward.", 
                "confidence": <CALCULATE_USING_RULES_BELOW>
            }},
            "risks": [ 
                {{ "severity": "high", "title": "Risk Title", "desc": "Description" }},
                {{ "severity": "medium", "title": "Risk Title", "desc": "Description" }}
            ]
        }}
        
        ===== CONFIDENCE CALCULATION RULES =====
        You MUST calculate confidence using this formula:
        
        1. Start at 50 (neutral baseline)
        
        2. EVIDENCE QUALITY (add points):
           - If thesis has 3+ evidence citations: +10
           - If antithesis has 3+ evidence citations: +10
           - If both sides have equal evidence (balanced debate): +5
        
        3. ARGUMENT STRENGTH (add points):
           - If arguments are specific with facts: +10
           - If arguments directly address the topic: +5
        
        4. RISK PENALTY (subtract points):
           - For each HIGH severity risk you identify: -10
           - For each MEDIUM severity risk you identify: -5
        
        5. CLARITY BONUS (add points):
           - If there's a clear winner/recommendation: +10
           - If the decision is nuanced/context-dependent: +5
        
        EXAMPLE CALCULATION:
        - Base: 50
        - Thesis has 6 citations (+10) = 60
        - Antithesis has 6 citations (+10) = 70
        - Balanced evidence (+5) = 75
        - 2 HIGH risks (-20) = 55
        - 1 MEDIUM risk (-5) = 50
        - Clear recommendation (+10) = 60
        - Final confidence: 60
        
        The confidence should reflect how RELIABLE your recommendation is,
        NOT how good the winning option is.
        
        Final score must be between 0-100.
        =========================================
        
        RULES:
        - Return ONLY valid JSON, no other text
        - No markdown code blocks
        - Show your confidence calculation in your thinking, but only output the final number
        - severity must be "high", "medium", or "low"
        - Base your synthesis on the actual debate arguments
        """,
        expected_output="Valid JSON decision matrix with calculated confidence score",
        agent=synthesist_agent
    )
    
    crew_synthesis = Crew(
        agents=[synthesist_agent], 
        tasks=[task_synthesis], 
        verbose=True,
        process=Process.sequential
    )
    
    final_output = crew_synthesis.kickoff()
    
    # Log synthesis to database
    synthesis_log = DebateLog(
        report_id=report.report_id, 
        agent_name="Synthesist", 
        round_number=3,  # Final round
        argument_text=str(final_output), 
        agent_role="Manager"
    )
    session.add(synthesis_log)
    
    # Store final decision matrix
    report.final_decision_matrix = str(final_output)
    session.commit()
    
    print(f"\n{'='*60}")
    print(f"✅ DEBATE COMPLETE")
    print(f"{'='*60}")
    print(f"Report ID: {report.report_id[:8]}...")
    print(f"Evidence - Thesis: {thesis_evidence_count}, Antithesis: {antithesis_evidence_count}")
    print(f"{'='*60}\n")
    
    session.close()
    
    return final_output


# For testing directly
if __name__ == "__main__":
    test_topic = "Should we use Microservices or Monolith architecture for a startup MVP?"
    result = run_cogito_debate(test_topic)
    print("\n=== FINAL DECISION MATRIX ===")
    print(result)