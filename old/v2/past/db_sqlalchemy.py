# past/db_sqlalchemy.py

from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from strategy.core import Strategy

Base = declarative_base()
DB_URI = os.environ.get('QORE_DB_URI', 'postgresql://username:password@localhost:5432/qore')
engine = create_engine(DB_URI)
SessionLocal = sessionmaker(bind=engine)

class StrategyModel(Base):
    __tablename__ = 'strategies'
    id = Column(String, primary_key=True)
    strategy_id = Column(String, unique=True, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    freeze_timestamp = Column(DateTime, nullable=True)
    type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    assets = Column(JSON, nullable=False)
    note = Column(Text)
    research = Column(JSON)
    tags = Column(ARRAY(Text))
    challenger_strategies = Column(JSON)

def fetch_all_frozen_strategies():
    session = SessionLocal()
    query = session.query(StrategyModel).filter(
        StrategyModel.status == 'frozen'
    ).order_by(StrategyModel.timestamp)
    rows = query.all()
    frozen_strategies = [Strategy.from_dict(row.__dict__) for row in rows]
    session.close()
    return frozen_strategies

def fetch_frozen_strategies_for_dates(start_date, end_date):
    session = SessionLocal()
    query = session.query(StrategyModel).filter(
        StrategyModel.status == 'frozen',
        StrategyModel.timestamp >= start_date,
        StrategyModel.timestamp <= end_date
    ).order_by(StrategyModel.timestamp)
    rows = query.all()
    frozen_strategies = [Strategy.from_dict(row.__dict__) for row in rows]
    session.close()
    return frozen_strategies
