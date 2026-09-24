"""Límites y verificación post-movimiento (desde perfil de robot)."""
from __future__ import annotations

from .context import get_profile
from .env_config import env


def tolerance() -> float:
    return float(env('TOL', '0.15'))


def max_step_rad() -> float:
    return float(env('MAX_STEP', '0.8'))


def home_pose() -> list[float]:
    return list(get_profile().home_pose)


def init_pose() -> list[float]:
    return list(get_profile().init_pose)


def clamp_joints(q):
    """Recorta a límites seguros y reporta qué se ajustó."""
    profile = get_profile()
    out, noted = [], []
    for n, v in zip(profile.joint_names, q):
        lo, hi = profile.limits[n]
        c = min(hi, max(lo, v))
        if abs(c - v) > 1e-9:
            noted.append(f'{n} ajustado a {round(c, 3)} (límite)')
        out.append(c)
    return out, noted


def check_max_step(current: list[float], target: list[float]) -> str | None:
    """Rechaza saltos mayores a max_step_rad respecto al estado actual."""
    limit = max_step_rad()
    for i, (a, b) in enumerate(zip(current, target)):
        if abs(a - b) > limit + 1e-9:
            return (
                f'Rechazado: joint{i + 1} salta {round(abs(a - b), 3)} rad '
                f'(máximo por paso {limit}). Divide en movimientos más pequeños.'
            )
    return None


def joint_hint(joint_index_1based: int) -> str:
    profile = get_profile()
    return profile.known_joint_hints.get(
        joint_index_1based, 'Revisa torque, límites u obstáculo.'
    )


def format_move_verification(
    tool_name: str,
    want: list[float],
    after: list[float] | None,
) -> str:
    """Texto de observación tras home/init/move_joints."""
    if after is None:
        return f'{tool_name} enviado, no pude leer estado final.'
    diffs = [abs(a - b) for a, b in zip(after, want)]
    mx = max(diffs)
    arm_r = [round(x, 3) for x in after]
    tol = tolerance()
    if mx <= tol:
        return f'{tool_name} ok. Ahora: {arm_r}'
    j = diffs.index(mx) + 1
    hint = joint_hint(j)
    return (
        f'{tool_name} enviado pero joint{j} no llego (pedido {round(want[j - 1], 3)}, '
        f'real {round(after[j - 1], 3)}). Ahora: {arm_r}. {hint}'
    )
