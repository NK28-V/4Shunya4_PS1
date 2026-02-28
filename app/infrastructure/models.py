from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SqlEnum, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

Base = declarative_base()

class ScanStatus(str, enum.Enum):
    PENDING = "PENDING"
    INGESTING = "INGESTING"
    SCANNING = "SCANNING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Project(Base):
    __tablename__ = "target_projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    repository_url = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    scans = relationship("Scan", back_populates="project")

class Scan(Base):
    __tablename__ = "scans"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("target_projects.id"))
    status = Column(SqlEnum(ScanStatus), default=ScanStatus.PENDING)
    initiated_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    
    # Ingestion context
    container_id = Column(String(255), nullable=True)
    local_path = Column(String(512), nullable=True)
    
    # Scoring & Routing
    score = Column(Integer, nullable=True)
    grade = Column(String(2), nullable=True)
    
    project = relationship("Project", back_populates="scans")
    vulnerabilities = relationship("Vulnerability", back_populates="scan")
    violations = relationship("ComplianceViolation", back_populates="scan")

class Vulnerability(Base):
    __tablename__ = "identified_vulnerabilities"
    
    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"))
    severity = Column(String(50))
    title = Column(String(255))
    description = Column(Text)
    file_path = Column(String(512))
    line_number = Column(Integer)
    
    remediation_tip = Column(Text, nullable=True)
    
    scan = relationship("Scan", back_populates="vulnerabilities")

class ComplianceViolation(Base):
    __tablename__ = "compliance_violations"
    
    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"))
    rule_id = Column(String(100))
    description = Column(Text)
    severity = Column(String(50))
    
    scan = relationship("Scan", back_populates="violations")
