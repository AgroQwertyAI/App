from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class MessagePending(Base):
    __tablename__ = "messages_pending"
    
    message_id = Column(Integer, primary_key=True)
    sender_phone_number = Column(String, nullable=False)
    sender_name = Column(String, nullable=False)
    sender_id = Column(String, nullable=False)
    
    setting_id = Column(Integer, ForeignKey("settings.setting_id"), nullable=False)
    
    original_message_text = Column(Text, nullable=False)
    formatted_message_text = Column(JSON, nullable=False)
    
    timedata = Column(DateTime, nullable=False)
    
    extra = Column(JSON, nullable=True)

    setting = relationship("Setting", back_populates="messages")


class Setting(Base):
    __tablename__ = "settings"
    
    setting_id = Column(Integer, primary_key=True)
    setting_name = Column(String, nullable=False)
    setting_description = Column(Text, nullable=False)
    format_report = Column(String, nullable=False)
    type = Column(String, nullable=False)
    
    send_to = Column(JSON, nullable=False)
    
    minute = Column(String, nullable=False)
    hour = Column(String, nullable=False)
    day_of_month = Column(String, nullable=False)
    month = Column(String, nullable=False)
    day_of_week = Column(String, nullable=False)
    
    deleted = Column(Boolean, default=False, nullable=False)
    
    extra = Column(JSON, nullable=True)
    
    messages = relationship("MessagePending", back_populates="setting")
    reports = relationship("Report", back_populates="setting")
    message_reports = relationship("MessageReport", back_populates="setting")


class Report(Base):
    __tablename__ = "reports"
    
    report_id = Column(Integer, primary_key=True)
    setting_id = Column(Integer, ForeignKey("settings.setting_id"), nullable=False)
    
    timedata = Column(DateTime, nullable=False)
    file = Column(Text, nullable=False)
    
    extra = Column(JSON, nullable=True)
    
    setting = relationship("Setting", back_populates="reports")
    message_reports = relationship("MessageReport", back_populates="report")


class MessageReport(Base):
    __tablename__ = "messages_reports"
    
    message_id = Column(Integer, primary_key=True)
    
    sender_phone_number = Column(String, nullable=False)
    sender_name = Column(String, nullable=False)
    sender_id = Column(String, nullable=False)
    
    setting_id = Column(Integer, ForeignKey("settings.setting_id"), nullable=False)
    report_id = Column(Integer, ForeignKey("reports.report_id"), nullable=False)
    
    timedata = Column(DateTime, nullable=False)
    original_message_text = Column(Text, nullable=False)
    formatted_message_text = Column(JSON, nullable=False)
    
    extra = Column(JSON, nullable=True)
    
    setting = relationship("Setting", back_populates="message_reports")
    report = relationship("Report", back_populates="message_reports")
