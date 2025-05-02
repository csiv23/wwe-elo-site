# src/models.py

from sqlalchemy import Table, Column, Integer, String, Date, Boolean, Float, ForeignKey
from src.db import metadata

# matches table: one row per match
matches = Table(
    'matches',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('date', Date,      nullable=False),
    Column('show', String,    nullable=False),
    Column('ple', Boolean,    nullable=True),    # Premium Live Event flag
    Column('match_type', String,    nullable=True),
    Column('winners',    String,    nullable=False),
    Column('losers',     String,    nullable=False),
    Column('time',       String,    nullable=True),
    Column('finish',     String,    nullable=False),
    Column('title_change', Boolean, nullable=False, default=False),
    Column('multi_man',    Boolean, nullable=False, default=False),
    Column('stipulation',  Boolean, nullable=False, default=False),
    Column('category',    String,    nullable=True),
)

# elo_history table: one row per wrestler per match
elo_history = Table(
    'elo_history',
    metadata,
    Column('id',        Integer, primary_key=True, autoincrement=True),
    Column('match_id',  Integer, ForeignKey('matches.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('wrestler',  String,  nullable=False),
    Column('opponents', String,  nullable=False),
    Column('elo_before', Float,  nullable=False),
    Column('elo_change', Float,  nullable=False),
    Column('elo_after',  Float,  nullable=False),
    Column('result',     String, nullable=False),  # 'Win' or 'Loss'
)
