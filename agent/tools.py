"""Fachada al adapter activo (configurable por robot)."""
from __future__ import annotations

from .context import get_adapter, get_profile


def bridge_url() -> str:
    return get_adapter()._config.base_url


def get_limits():
    return get_profile().limits


def get_joint_names():
    return get_profile().joint_names


def get_state():
    return get_adapter().get_state()


def health():
    return get_adapter().health()


def move_joints(q, seconds=4.0):
    return get_adapter().move_joints(list(q), seconds)


def home():
    return get_adapter().home()


def init():
    return get_adapter().init()


def gripper(open01, seconds=2.0):
    return get_adapter().gripper(open01, seconds)


def torque(on: bool):
    return get_adapter().torque(on)


def read_arm_positions(state: dict | None = None) -> list[float]:
    st = state if state is not None else get_state()
    key = get_profile().state_arm_key
    arm = st.get(key, st.get('arm'))
    if arm is None:
        raise KeyError(f'estado sin clave "{key}" ni "arm"')
    return list(arm)


def read_gripper(state: dict | None = None) -> float:
    st = state if state is not None else get_state()
    key = get_profile().state_gripper_key
    return float(st.get(key, st.get('gripper', 0.0)))


def validate(q):
    names = get_joint_names()
    limits = get_limits()
    bad = []
    for n, v in zip(names, q):
        lo, hi = limits[n]
        if not (lo <= v <= hi):
            bad.append(f'{n}={v} fuera de [{lo},{hi}]')
    return bad
