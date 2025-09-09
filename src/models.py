# src/models.py

from sqlalchemy import (
    Table, Column, Integer, String, Date, Boolean, Float, ForeignKey, UniqueConstraint
)
from src.db import metadata

# -------------------------
# BRONZE: raw scraped rows
# -------------------------
matches_raw = Table(
    "matches_raw",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("date", Date,      nullable=False),
    Column("show", String,    nullable=False),
    Column("ple", Boolean,    nullable=True),      # Premium Live Event flag
    Column("match_type", String, nullable=True),
    Column("winners", String,  nullable=False),    # comma-separated raw names
    Column("losers",  String,  nullable=False),    # comma-separated raw names
    Column("time",    String,  nullable=True),
    Column("finish",  String,  nullable=False),
    Column("title_change", Boolean, nullable=False, default=False),
    Column("multi_man",    Boolean, nullable=False, default=False),
    Column("stipulation",  Boolean, nullable=False, default=False),
    Column("category",     String,  nullable=True),
    UniqueConstraint(
        "date", "show", "match_type", "winners", "losers",
        name="uq_matches__date_show_type_winners_losers",
    ),
    schema="bronze",
)

# Back-compat alias: existing code importing `matches` keeps working
matches = matches_raw


# ----------------------------------------
# SILVER: cleaned / normalized structures
# ----------------------------------------

# 1) Wrestlers dimension (one row per canonical name)
wrestlers_dim = Table(
    "wrestlers_dim",
    metadata,
    Column("wrestler_id", Integer, primary_key=True, autoincrement=True),
    Column("name",        String,  nullable=False, unique=True),  # canonical display name
    Column("brand",       String,  nullable=True),                # optional (RAW/SmackDown/NXT/…)
    Column("active",      Boolean, nullable=False, default=True), # maintained by transforms
    Column("first_seen",  Date,    nullable=True),
    Column("last_seen",   Date,    nullable=True),
    schema="silver",
)

# 2) Matches (deduped, typed, keyed) — one row per match
#    Use bronze ID as the match_id (simple & stable).
matches_clean = Table(
    "matches",
    metadata,
    Column("match_id", Integer, primary_key=True),  # = bronze.matches_raw.id
    Column("date",      Date,    nullable=False),
    Column("show",      String,  nullable=False),
    Column("ple",       Boolean, nullable=True),
    Column("match_type", String, nullable=True),
    Column("category",   String, nullable=True),
    Column("stipulation", Boolean, nullable=False, default=False),
    Column("multi_man",   Boolean, nullable=False, default=False),
    Column("finish",      String,  nullable=False),
    Column("title_change", Boolean, nullable=False, default=False),
    Column("time",        String,  nullable=True),
    # FK to bronze to keep lineage explicit
    Column("bronze_id", Integer, ForeignKey("bronze.matches_raw.id", ondelete="CASCADE"), nullable=False, unique=True),
    schema="silver",
)

# 3) Match participants (normalized winners/losers into rows)
#    One row per (match_id, wrestler_id). `result`: 'W','L','D'
match_participants = Table(
    "match_participants",
    metadata,
    Column("id",          Integer, primary_key=True, autoincrement=True),
    Column("match_id",    Integer, ForeignKey("silver.matches.match_id", ondelete="CASCADE"), nullable=False, index=True),
    Column("wrestler_id", Integer, ForeignKey("silver.wrestlers_dim.wrestler_id", ondelete="RESTRICT"), nullable=False, index=True),
    Column("result",      String(1), nullable=False),      # 'W','L','D'
    Column("fall_method", String,    nullable=True),       # pin/sub/dq/nc/etc.
    Column("is_title_match", Boolean, nullable=False, default=False),
    Column("team_slot",   Integer,   nullable=True),       # optional ordering within sides
    UniqueConstraint("match_id", "wrestler_id", name="uq_participants_match_wrestler"),
    schema="silver",
)


# ------------------------------------------------
# GOLD: analytics / products (Elo-ready surfaces)
# ------------------------------------------------
elo_history = Table(
    "elo_history",
    metadata,
    Column("id",         Integer, primary_key=True, autoincrement=True),
    Column("match_id",   Integer, ForeignKey("bronze.matches_raw.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("wrestler",   String,  nullable=False),   # keep string for v1; can migrate to wrestler_id later
    Column("opponents",  String,  nullable=False),
    Column("elo_before", Float,   nullable=False),
    Column("elo_change", Float,   nullable=False),
    Column("elo_after",  Float,   nullable=False),
    Column("result",     String,  nullable=False),   # 'Win' or 'Loss' (or 'Draw')
    schema="gold",
)
