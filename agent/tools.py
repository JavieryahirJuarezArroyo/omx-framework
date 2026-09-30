"""Fachada al adapter ROS 2 activo."""
from __future__ import annotations

from .context import ensure_ros_adapter, get_adapter, get_profile


def adapter_info() -> dict:
    from .context import adapter_public_info

    return adapter_public_info()


def get_state():
    return ensure_ros_adapter().get_state()


def health():
    return ensure_ros_adapter().health()


def move_joints(q, seconds=4.0):
    return ensure_ros_adapter().move_joints(list(q), seconds)


def home():
    return ensure_ros_adapter().home()


def init():
    return ensure_ros_adapter().init()


def gripper(open01, seconds=2.0):
    return ensure_ros_adapter().gripper(open01, seconds)


def torque(on: bool):
    return ensure_ros_adapter().torque(on)


def get_limits():
    return get_profile().limits


def get_joint_names():
    return get_profile().joint_names


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
