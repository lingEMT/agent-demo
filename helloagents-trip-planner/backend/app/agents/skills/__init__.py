"""技能模块 - 多智能体系统中的专业Agent技能"""
from .attraction_skill import AttractionSkill
from .weather_skill import WeatherSkill
from .hotel_skill import HotelSkill
from .planner_skill import PlannerSkill

__all__ = ["AttractionSkill", "WeatherSkill", "HotelSkill", "PlannerSkill"]
