"""
Pydantic schema for race config validation.

Catches typos and structural errors at load time instead of failing silently
or with cryptic KeyErrors deep in the pipeline. Validates that:
- Weights sum to ~1.0
- Required sections (race, scoring, weights, etc.) exist
- Numeric fields have valid types and ranges

Usage:
    from race_config import RaceConfig
    cfg = RaceConfig.load(race_slug)   # raises ValidationError on bad config
"""
from __future__ import annotations
import tomllib
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, model_validator

ROOT = Path(__file__).resolve().parent.parent


class RaceMeta(BaseModel):
    name: str
    track: str
    date: str
    distance_furlongs: float = Field(gt=0)
    surface: str
    purse_k: int = Field(ge=0)
    field_cap: int = Field(gt=0)
    exotic_takeout: float = Field(ge=0, le=0.5)


class Scoring(BaseModel):
    temperature: float = Field(gt=0, default=0.075)
    overlay_threshold: float = Field(ge=1.0, default=1.25)
    fair_prob_threshold: float = Field(ge=0, le=1, default=0.04)


class Weights(BaseModel):
    """Feature weights — must sum to ~1.0."""
    model_config = ConfigDict(extra="allow")  # tolerate new feature names

    last_beyer: float = Field(ge=0, le=1)
    top3_beyer: float = Field(ge=0, le=1)
    pace_fit: float = Field(ge=0, le=1)
    class_preps: float = Field(ge=0, le=1)
    how_won: float = Field(ge=0, le=1)
    distance_fit: float = Field(ge=0, le=1)
    connections: float = Field(ge=0, le=1)
    equipment: float = Field(ge=0, le=1)
    post: float = Field(ge=0, le=1)
    preferred_prep: float = Field(ge=0, le=1)
    barn_pick: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "Weights":
        total = sum(getattr(self, k) for k in self.__class__.model_fields)
        if abs(total - 1.0) > 0.02:
            raise ValueError(f"Feature weights sum to {total:.3f}, expected ~1.0 (±0.02)")
        return self


class Pace(BaseModel):
    meltdown_likely: bool = False


class Equipment(BaseModel):
    ft_blinkers: list[str] = []


class PostMultiplier(BaseModel):
    default: float = Field(ge=0, le=2, default=1.0)
    ae_default: float = Field(ge=0, le=2, default=0.5)
    overrides: dict[str, float] = {}


class PrepClassScore(BaseModel):
    default: int = 35
    scores: dict[str, float] = {}


class PreferredPrep(BaseModel):
    race_class: str
    winner_score: float = Field(ge=0, le=100)
    default_score: float = Field(ge=0, le=100)


class BarnPickRule(BaseModel):
    model_config = ConfigDict(extra="allow")
    trainer: Optional[str] = None
    horse: Optional[str] = None
    jockey_contains: Optional[str] = None
    match_score: float = Field(ge=0, le=100, default=90)
    trainer_other_score: float = Field(ge=0, le=100, default=60)


class BarnPick(BaseModel):
    default_score: float = Field(ge=0, le=100, default=60)
    rules: list[BarnPickRule] = []


class TrainerScore(BaseModel):
    default: float = Field(ge=0, le=100, default=50)
    scores: dict[str, float] = {}


class JockeyScore(BaseModel):
    default: float = Field(ge=0, le=100, default=55)
    scores: dict[str, float] = {}


class SireBiasGroup(BaseModel):
    sires: list[str] = []
    bonus: float = 0
    penalty: float = 0


class SireBias(BaseModel):
    stamina: SireBiasGroup = SireBiasGroup()
    speed: SireBiasGroup = SireBiasGroup()


class OddsSource(BaseModel):
    url: str
    format: str
    notes: str = ""


class RaceConfig(BaseModel):
    """Full race configuration. Validated at load time."""
    model_config = ConfigDict(extra="allow")  # tolerate undocumented sections

    race: RaceMeta
    scoring: Scoring = Scoring()
    weights: Weights
    pace: Pace = Pace()
    equipment: Equipment = Equipment()
    post_multiplier: PostMultiplier = PostMultiplier()
    prep_class_score: PrepClassScore = PrepClassScore()
    preferred_prep: PreferredPrep
    barn_pick: BarnPick = BarnPick()
    trainer_score: TrainerScore = TrainerScore()
    jockey_score: JockeyScore = JockeyScore()
    sire_bias: SireBias = SireBias()
    public_overbet: dict[str, float] = {}
    live_odds_source: Optional[OddsSource] = None
    exacta_probables_source: Optional[OddsSource] = None

    @classmethod
    def load(cls, race_slug: str) -> "RaceConfig":
        path = ROOT / "data" / "races" / race_slug / "config.toml"
        if not path.exists():
            raise FileNotFoundError(f"No config at {path}")
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return cls.model_validate(data)

    def race_paths(self, race_slug: str) -> dict:
        base = ROOT / "data" / "races" / race_slug
        return {
            "field":            base / "field.csv",
            "pp":               base / "past_performances.csv",
            "live_odds":        base / "live_odds.csv",
            "exacta_probables": base / "exacta_probables.txt",
            "trifecta_probables": base / "trifecta_probables.txt",
            "overlays_out":     base / "overlays.csv",
        }
