from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.session import Base

class Chat(Base):
    __tablename__ = "chats"
    
    chat_id = Column(String, primary_key=True)
    chat_name = Column(String, nullable=False)
    messenger = Column(String, nullable=False)
    
    # Relationships
    associations = relationship("Association", back_populates="chat", cascade="all, delete-orphan")

class Association(Base):
    __tablename__ = "associations"
    
    association_id = Column(Integer, primary_key=True)
    chat_id = Column(String, ForeignKey("chats.chat_id", ondelete="CASCADE"), nullable=False)
    setting_id = Column(Integer, nullable=False)
    
    # Relationships
    chat = relationship("Chat", back_populates="associations")

class MessageHistory(Base):
    __tablename__ = "message_history"
    
    message_id = Column(Integer, primary_key=True)
    chat_id = Column(String, nullable=False)
    messenger = Column(String, nullable=False)
    sender_id = Column(String, nullable=False)
    text = Column(String, nullable=False)
    images = Column(String, nullable=False)
    audio = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)

    # Relationships
    llm_answer = relationship("LLMAnswer", back_populates="message")

class LLMAnswer(Base):
    __tablename__ = "llm_answers"
    
    answer_id = Column(Integer, primary_key=True)
    answer = Column(String, nullable=False)
    message_id = Column(Integer, ForeignKey("message_history.message_id", ondelete="CASCADE"), nullable=False)

    # Relationships
    message = relationship("MessageHistory", back_populates="llm_answer")