"""
Cogito Requiem - Database Models
================================
Implements the ER Diagram from PDF Section 3.3:
- DecisionRequest: The initial user prompt
- DebateReport: The final JSON decision matrix
- DebateLog: Every message from each agent
- Evidence: Links debate entries to RAG citations (NEW)

Uses SQLite for lightweight local persistence.
"""

from sqlalchemy import create_engine, Column, String, Integer, Text, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import uuid

Base = declarative_base()


class DecisionRequest(Base):
    """
    Stores the initial user prompt/question.
    One request can have one debate report.
    """
    __tablename__ = 'decision_requests'
    
    request_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_prompt = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    report = relationship("DebateReport", back_populates="request", uselist=False)
    
    def __repr__(self):
        return f"<DecisionRequest(id={self.request_id[:8]}, prompt='{self.user_prompt[:30]}...')>"


class DebateReport(Base):
    """
    Stores the final JSON/Markdown output (Decision Matrix).
    Links back to the original request.
    """
    __tablename__ = 'debate_reports'
    
    report_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String, ForeignKey('decision_requests.request_id'), nullable=False)
    final_decision_matrix = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    request = relationship("DecisionRequest", back_populates="report")
    logs = relationship("DebateLog", back_populates="report", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DebateReport(id={self.report_id[:8]})>"


class DebateLog(Base):
    """
    Stores every individual message from each agent.
    Allows for transparency and "replayability" of the debate.
    """
    __tablename__ = 'debate_logs'
    
    log_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String, ForeignKey('debate_reports.report_id'), nullable=False)
    agent_name = Column(String, nullable=False)  # "Thesis", "Antithesis", "Synthesist"
    round_number = Column(Integer, nullable=False)
    argument_text = Column(Text, nullable=False)
    agent_role = Column(String)  # "Pro", "Con", "Manager"
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    report = relationship("DebateReport", back_populates="logs")
    evidence = relationship("Evidence", back_populates="log", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DebateLog(agent={self.agent_name}, round={self.round_number})>"


class Evidence(Base):
    """
    Links log entries to specific content chunks retrieved from RAG.
    This is from the PDF ER Diagram (Section 3.3).
    
    Tracks what evidence each agent retrieved to support their arguments.
    """
    __tablename__ = 'evidence'
    
    evidence_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    log_id = Column(String, ForeignKey('debate_logs.log_id'), nullable=True)
    
    # RAG retrieval information
    source_document = Column(String, nullable=False)  # e.g., "microservices_paper.pdf"
    content_chunk = Column(Text, nullable=False)      # The actual retrieved text
    search_query = Column(String)                      # What query was used
    relevance_score = Column(Float)                    # How relevant (0-1)
    
    # Metadata
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    log = relationship("DebateLog", back_populates="evidence")
    
    def __repr__(self):
        return f"<Evidence(source={self.source_document}, relevance={self.relevance_score:.2f})>"


# ============================================
# Database Setup
# ============================================

# This creates a file named 'cogito.db' automatically
engine = create_engine('sqlite:///cogito.db', echo=False)

# Create all tables
Base.metadata.create_all(engine)

# Session factory
Session = sessionmaker(bind=engine)


def get_session():
    """Get a new database session."""
    return Session()


def store_evidence(session, log_id: str, evidence_list: list):
    """
    Store evidence entries retrieved during RAG searches.
    
    Args:
        session: Database session
        log_id: The DebateLog entry to link evidence to
        evidence_list: List of evidence dicts from RAG system
    """
    for ev in evidence_list:
        evidence = Evidence(
            log_id=log_id,
            source_document=ev.get("source_document", "Unknown"),
            content_chunk=ev.get("content_chunk", "")[:1000],  # Limit size
            search_query=ev.get("query", ""),
            relevance_score=ev.get("relevance_score", 0.0)
        )
        session.add(evidence)
    
    session.commit()


def get_debate_with_evidence(report_id: str):
    """
    Retrieve a full debate including all evidence citations.
    
    Args:
        report_id: The debate report ID
        
    Returns:
        Dict with debate logs and their evidence
    """
    session = get_session()
    
    try:
        report = session.query(DebateReport).filter_by(report_id=report_id).first()
        
        if not report:
            return None
        
        result = {
            "report_id": report.report_id,
            "request_prompt": report.request.user_prompt if report.request else None,
            "decision_matrix": report.final_decision_matrix,
            "rounds": []
        }
        
        for log in report.logs:
            log_data = {
                "agent": log.agent_name,
                "role": log.agent_role,
                "round": log.round_number,
                "argument": log.argument_text,
                "evidence": []
            }
            
            for ev in log.evidence:
                log_data["evidence"].append({
                    "source": ev.source_document,
                    "content": ev.content_chunk[:200] + "..." if len(ev.content_chunk) > 200 else ev.content_chunk,
                    "query": ev.search_query,
                    "relevance": ev.relevance_score
                })
            
            result["rounds"].append(log_data)
        
        return result
        
    finally:
        session.close()


def clear_database():
    """Clear all data (for reset functionality)."""
    session = get_session()
    try:
        session.query(Evidence).delete()
        session.query(DebateLog).delete()
        session.query(DebateReport).delete()
        session.query(DecisionRequest).delete()
        session.commit()
        print("[Database]: All data cleared")
    finally:
        session.close()


# Print confirmation
print("[Database]: Cogito Requiem database initialized")
print("  Tables: decision_requests, debate_reports, debate_logs, evidence")