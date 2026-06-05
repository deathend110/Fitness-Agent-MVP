from __future__ import annotations

from copy import deepcopy

from backend.schemas import CyclePresetSchema


_PRESET_REGISTRY: dict[str, CyclePresetSchema] = {
    "candito_6week": CyclePresetSchema(
        key="candito_6week",
        label="Candito 6 Week Strength",
        summary="6 周力量导向模板，按周切换容量、强度与峰值训练重心。",
        supportedWeeks=[1, 2, 3, 4, 5, 6],
        supportsTm=True,
        repeatMode="fixed_length",
    ),
    "madcow_5x5": CyclePresetSchema(
        key="madcow_5x5",
        label="Madcow 5x5",
        summary="经典 5x5 线性推进模板，强调周内爬坡和周末顶组表现。",
        supportedWeeks=list(range(1, 13)),
        supportsTm=True,
        repeatMode="repeating",
    ),
    "texas_method": CyclePresetSchema(
        key="texas_method",
        label="Texas Method",
        summary="固定周结构的 HLM 模板，区分容量日、恢复日和强度日。",
        supportedWeeks=list(range(1, 13)),
        supportsTm=True,
        repeatMode="repeating",
    ),
}


def list_cycle_presets() -> list[CyclePresetSchema]:
    return [preset.model_copy(deep=True) for preset in _PRESET_REGISTRY.values()]


def get_cycle_preset(preset_key: str) -> CyclePresetSchema:
    preset = _PRESET_REGISTRY.get(preset_key)
    if preset is None:
        raise KeyError(f"未注册的周期模板：{preset_key}")
    return preset.model_copy(deep=True)


def get_supported_week_indexes(preset_key: str) -> list[int]:
    return deepcopy(get_cycle_preset(preset_key).supportedWeeks)
