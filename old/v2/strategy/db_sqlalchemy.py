# strategy/db_sqlalchemy.py

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

def fetch_strategies_for_date(target_date):
    session = SessionLocal()
    # Fetch all frozen strategies for or before target_date
    frozen_orm = session.query(StrategyModel).filter(
        StrategyModel.status == 'frozen',
        StrategyModel.timestamp <= target_date
    ).order_by(StrategyModel.timestamp).all()
    frozen = [Strategy.from_dict(obj.__dict__) for obj in frozen_orm]
    # Fetch current strategy for target_date
    current_orm = session.query(StrategyModel).filter(
        StrategyModel.status == 'current',
        StrategyModel.timestamp.cast(DateTime).cast(DateTime).op('::date')() == target_date
    ).first()
    current = Strategy.from_dict(current_orm.__dict__) if current_orm else None
    session.close()
    return frozen, current

def insert_strategy(strategy_obj):
    session = SessionLocal()
    model = StrategyModel(**strategy_obj.to_dict())
    session.add(model)
    session.commit()
    session.close()

def update_strategy(strategy_obj):
    session = SessionLocal()
    db_obj = session.query(StrategyModel).get(strategy_obj.id)
    if db_obj:
        for key, value in strategy_obj.to_dict().items():
            setattr(db_obj, key, value)
        session.commit()
    session.close()
