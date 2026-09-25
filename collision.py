"""Collision geometry and DELTARUNE-style overworld movement.

The module deliberately separates three concerns:

* :class:`CollisionShape` stores geometry.
* :class:`Collider` adds behavior and source information.
* :class:`CollisionWorld` performs spatial queries and movement resolution.

Room data should normally contain already-resolved world-space geometry.  In
particular, importers should apply GameMaker sprite scaling before creating a
``CollisionShape``.  ``source_scale_x`` and ``source_scale_y`` are retained
only as optional debugging information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, radians, sin
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence


Point = tuple[float, float]
DEFAULT_SOLID_CATEGORIES = frozenset({"solid", "interactable_solid"})
_EPSILON = 1e-9


@dataclass(frozen=True, slots=True)
class Rect:
    """An axis-aligned rectangle using half-open edges.

    Consequently, two rectangles that merely touch at an edge are not
    considered overlapping.  This makes an actor able to rest flush against a
    wall without continuously reporting a collision.
    """

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError("Rect width and height must be non-negative")

    @property
    def left(self) -> float:
        return self.x

    @property
    def top(self) -> float:
        return self.y

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def moved(self, dx: float = 0.0, dy: float = 0.0) -> Rect:
        return Rect(self.x + dx, self.y + dy, self.width, self.height)

    def intersects(self, other: Rect) -> bool:
        return (
            self.left < other.right
            and self.right > other.left
            and self.top < other.bottom
            and self.bottom > other.top
        )

    def as_polygon(self) -> tuple[Point, Point, Point, Point]:
        return (
            (self.left, self.top),
            (self.right, self.top),
            (self.right, self.bottom),
            (self.left, self.bottom),
        )

    def as_edges(self) -> tuple[float, float, float, float]:
        """Return ``(left, top, right, bottom)`` bounds."""

        return self.left, self.top, self.right, self.bottom


def as_rect(value: Any) -> Rect:
    """Convert a common hitbox representation into :class:`Rect`.

    Accepted values are ``Rect`` itself, ``(x, y, width, height)``, an object
    exposing ``left/top/right/bottom``, or an object exposing GameMaker-style
    ``bbox_left/bbox_top/bbox_right/bbox_bottom`` attributes.
    """

    if isinstance(value, Rect):
        return value

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if len(value) != 4:
            raise TypeError("A sequence hitbox must be (x, y, width, height)")
        x, y, width, height = value
        return Rect(float(x), float(y), float(width), float(height))

    if all(hasattr(value, name) for name in ("left", "top", "right", "bottom")):
        left = float(value.left)
        top = float(value.top)
        return Rect(left, top, float(value.right) - left, float(value.bottom) - top)

    if all(
        hasattr(value, name)
        for name in ("bbox_left", "bbox_top", "bbox_right", "bbox_bottom")
    ):
        left = float(value.bbox_left)
        top = float(value.bbox_top)
        return Rect(
            left,
            top,
            float(value.bbox_right) - left,
            float(value.bbox_bottom) - top,
        )

    raise TypeError(f"Cannot convert {type(value).__name__} to Rect")


@dataclass(slots=True)
class CollisionShape:
    """World-space collision geometry.

    ``kind`` may be ``rect``, ``sul``, ``sur``, ``sdl``, ``sdr``, or
    ``polygon``.  The four ``s*`` kinds are the triangular DELTARUNE collision
    primitives.  Polygon points are world-space points and must describe a
    convex polygon.

    Rotation is clockwise in degrees and is applied around the shape's center.
    For imported GameMaker instances, it is usually preferable for the
    extractor to emit the final polygon directly.
    """

    x: float
    y: float
    width: float
    height: float
    kind: str = "rect"
    points: tuple[Point, ...] | list[Point] | None = None
    rotation: float = 0.0

    def __post_init__(self) -> None:
        self.x = float(self.x)
        self.y = float(self.y)
        self.width = float(self.width)
        self.height = float(self.height)
        self.kind = self.kind.lower()

        valid_kinds = {"rect", "sul", "sur", "sdl", "sdr", "polygon"}
        if self.kind not in valid_kinds:
            raise ValueError(f"Unknown collision shape kind: {self.kind!r}")
        if self.width < 0 or self.height < 0:
            raise ValueError("Collision width and height must be non-negative")
        if self.kind == "polygon":
            if self.points is None or len(self.points) < 3:
                raise ValueError("A polygon collision needs at least three points")
            self.points = tuple((float(px), float(py)) for px, py in self.points)
        elif self.points is not None:
            self.points = tuple((float(px), float(py)) for px, py in self.points)

    @classmethod
    def rectangle(cls, x: float, y: float, width: float, height: float) -> CollisionShape:
        return cls(x=x, y=y, width=width, height=height, kind="rect")

    @classmethod
    def polygon(cls, points: Sequence[Point]) -> CollisionShape:
        if len(points) < 3:
            raise ValueError("A polygon collision needs at least three points")
        normalized = tuple((float(x), float(y)) for x, y in points)
        xs = [point[0] for point in normalized]
        ys = [point[1] for point in normalized]
        return cls(
            x=min(xs),
            y=min(ys),
            width=max(xs) - min(xs),
            height=max(ys) - min(ys),
            kind="polygon",
            points=normalized,
        )

    @property
    def bounds(self) -> Rect:
        points = self.as_polygon()
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        return Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    def moved(self, dx: float = 0.0, dy: float = 0.0) -> CollisionShape:
        points = None
        if self.points is not None:
            points = tuple((x + dx, y + dy) for x, y in self.points)
        return CollisionShape(
            x=self.x + dx,
            y=self.y + dy,
            width=self.width,
            height=self.height,
            kind=self.kind,
            points=points,
            rotation=self.rotation,
        )

    def as_polygon(self) -> tuple[Point, ...]:
        left = self.x
        top = self.y
        right = self.x + self.width
        bottom = self.y + self.height

        if self.kind == "polygon":
            assert self.points is not None
            points = tuple(self.points)
        elif self.kind == "rect":
            points = ((left, top), (right, top), (right, bottom), (left, bottom))
        elif self.kind == "sul":
            points = ((left, top), (right, top), (left, bottom))
        elif self.kind == "sur":
            points = ((left, top), (right, top), (right, bottom))
        elif self.kind == "sdl":
            points = ((left, top), (right, bottom), (left, bottom))
        else:  # sdr
            points = ((right, top), (right, bottom), (left, bottom))

        if abs(self.rotation) <= _EPSILON:
            return points

        center_x = self.x + self.width / 2.0
        center_y = self.y + self.height / 2.0
        angle = radians(self.rotation)
        cosine = cos(angle)
        sine = sin(angle)
        rotated: list[Point] = []
        for point_x, point_y in points:
            relative_x = point_x - center_x
            relative_y = point_y - center_y
            rotated.append(
                (
                    center_x + relative_x * cosine - relative_y * sine,
                    center_y + relative_x * sine + relative_y * cosine,
                )
            )
        return tuple(rotated)

    def intersects_rect(self, rect: Rect) -> bool:
        if not self.bounds.intersects(rect):
            return False
        if self.kind == "rect" and abs(self.rotation) <= _EPSILON:
            return self.bounds.intersects(rect)
        return _convex_polygons_intersect(self.as_polygon(), rect.as_polygon())


@dataclass(slots=True)
class Collider:
    """Geometry plus the behavior needed by a collision query."""

    shape: CollisionShape
    category: str = "solid"
    source_object: str | None = None
    owner: object | None = None
    blocks_player: bool = True
    active: bool = True
    source_scale_x: float | None = None
    source_scale_y: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    shape_provider: Callable[[], CollisionShape | Rect | Sequence[float]] | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def current_shape(self) -> CollisionShape:
        if self.shape_provider is not None:
            return _shape_from_value(self.shape_provider())

        if self.owner is not None:
            get_shape = getattr(self.owner, "get_collision_shape", None)
            if callable(get_shape):
                return _shape_from_value(get_shape())

        return self.shape

    @property
    def bounds(self) -> Rect:
        return self.current_shape().bounds

    def intersects(self, hitbox: Rect | Sequence[float] | object) -> bool:
        return self.active and self.current_shape().intersects_rect(as_rect(hitbox))

    def as_edges(self) -> tuple[float, float, float, float]:
        """Return this collider's current ``left, top, right, bottom`` bounds.

        This also forms the compatibility bridge for pre-collision-system code
        that represented every room wall as a four-value bounds tuple.
        """

        return self.bounds.as_edges()

    def __iter__(self) -> Iterator[float]:
        """Allow legacy ``left, top, right, bottom = collider`` unpacking."""

        return iter(self.as_edges())

    def __len__(self) -> int:
        return 4

    def __getitem__(self, index: int | slice) -> float | tuple[float, ...]:
        return self.as_edges()[index]


def _shape_from_value(value: Any) -> CollisionShape:
    if isinstance(value, CollisionShape):
        return value
    rect = as_rect(value)
    return CollisionShape.rectangle(rect.x, rect.y, rect.width, rect.height)


def coerce_collider(value: Any) -> Collider:
    """Convert convenient room-data forms into a :class:`Collider`.

    Besides existing ``Collider`` and ``CollisionShape`` instances, this
    accepts legacy ``(left, top, right, bottom)`` tuples and mappings such as::

        {"x": 20, "y": 40, "width": 100, "height": 20,
         "kind": "rect", "source_object": "obj_solidblock"}
    """

    if isinstance(value, Collider):
        return value
    if isinstance(value, CollisionShape):
        return Collider(shape=value)
    if isinstance(value, Mapping):
        data = dict(value)
        shape_value = data.pop("shape", None)
        collider_fields = {
            key: data.pop(key)
            for key in tuple(data)
            if key
            in {
                "category",
                "source_object",
                "owner",
                "blocks_player",
                "active",
                "source_scale_x",
                "source_scale_y",
                "metadata",
                "shape_provider",
            }
        }
        if shape_value is None:
            shape_value = CollisionShape(**data)
        return Collider(shape=_shape_from_value(shape_value), **collider_fields)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if len(value) != 4:
            raise TypeError(
                "A legacy room collision must be "
                "(left, top, right, bottom)"
            )
        left, top, right, bottom = (float(component) for component in value)
        if right < left or bottom < top:
            raise ValueError(
                "Legacy collision bounds require right >= left and "
                "bottom >= top"
            )
        return Collider(
            shape=CollisionShape.rectangle(
                left,
                top,
                right - left,
                bottom - top,
            )
        )
    raise TypeError(f"Cannot convert {type(value).__name__} to Collider")


@dataclass(frozen=True, slots=True)
class MovementResult:
    """Resolved actor motion, including automatic corner-slide nudges."""

    dx: float
    dy: float
    nudge_x: float = 0.0
    nudge_y: float = 0.0
    blocked_x: bool = False
    blocked_y: bool = False

    @property
    def total_dx(self) -> float:
        return self.dx + self.nudge_x

    @property
    def total_dy(self) -> float:
        return self.dy + self.nudge_y

    @property
    def moved_distance_squared(self) -> float:
        return self.total_dx**2 + self.total_dy**2


class CollisionWorld:
    """Static/dynamic collider storage and GameMaker-like spatial queries."""

    def __init__(
        self,
        colliders: Iterable[Any] | None = None,
        dynamic_colliders: Iterable[Any] | None = None,
    ) -> None:
        self.colliders: list[Collider] = [
            coerce_collider(collider) for collider in (colliders or [])
        ]
        self.dynamic_colliders: list[Collider] = [
            coerce_collider(collider) for collider in (dynamic_colliders or [])
        ]

    def _all_colliders(self) -> Iterator[Collider]:
        yield from self.colliders
        yield from self.dynamic_colliders

    def add(self, collider: Any, *, dynamic: bool = False) -> Collider:
        normalized = coerce_collider(collider)
        target = self.dynamic_colliders if dynamic else self.colliders
        target.append(normalized)
        return normalized

    def remove(self, collider: Collider) -> None:
        if collider in self.colliders:
            self.colliders.remove(collider)
        elif collider in self.dynamic_colliders:
            self.dynamic_colliders.remove(collider)

    def collisions_in_rect(
        self,
        rect: Rect | Sequence[float] | object,
        *,
        categories: Iterable[str] | None = None,
        blocking_only: bool = False,
    ) -> list[Collider]:
        hitbox = as_rect(rect)
        allowed = set(categories) if categories is not None else None
        results: list[Collider] = []
        for collider in self._all_colliders():
            if not collider.active:
                continue
            if allowed is not None and collider.category not in allowed:
                continue
            if blocking_only and not collider.blocks_player:
                continue
            if collider.intersects(hitbox):
                results.append(collider)
        return results

    def place_meeting(
        self,
        hitbox: Rect | Sequence[float] | object,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        *,
        categories: Iterable[str] | None = DEFAULT_SOLID_CATEGORIES,
    ) -> bool:
        moved = as_rect(hitbox).moved(offset_x, offset_y)
        allowed = set(categories) if categories is not None else None
        for collider in self._all_colliders():
            if not collider.active or not collider.blocks_player:
                continue
            if allowed is not None and collider.category not in allowed:
                continue
            if collider.intersects(moved):
                return True
        return False

    def resolve_movement(
        self,
        hitbox: Rect | Sequence[float] | object,
        dx: float,
        dy: float,
        move_speed: float,
        *,
        pressing_left: bool = False,
        pressing_right: bool = False,
        pressing_up: bool = False,
        pressing_down: bool = False,
        categories: Iterable[str] | None = DEFAULT_SOLID_CATEGORIES,
    ) -> MovementResult:
        """Resolve Kris-style movement against blocking colliders.

        The order follows ``obj_mainchara``: horizontal collision and corner
        slide, horizontal partial movement, vertical collision and corner
        slide, vertical partial movement, then a final diagonal safety pass.
        The method is pure; callers apply ``result.total_dx`` and
        ``result.total_dy`` to their actor.
        """

        original_dx = float(dx)
        original_dy = float(dy)
        resolved_dx = original_dx
        resolved_dy = original_dy
        speed = abs(float(move_speed))
        nudge_x = 0.0
        nudge_y = 0.0

        def meeting(test_dx: float, test_dy: float) -> bool:
            return self.place_meeting(
                hitbox,
                test_dx,
                test_dy,
                categories=categories,
            )

        # Horizontal pass.  DELTARUNE first tries to slip vertically around a
        # corner, unless the player is deliberately pressing that direction.
        if abs(resolved_dx) > _EPSILON and meeting(nudge_x + resolved_dx, nudge_y):
            for amount in _descending_amounts(speed):
                if not pressing_down and not meeting(
                    nudge_x + resolved_dx,
                    nudge_y - amount,
                ):
                    nudge_y -= amount
                    resolved_dy = 0.0
                    break
                if not pressing_up and not meeting(
                    nudge_x + resolved_dx,
                    nudge_y + amount,
                ):
                    nudge_y += amount
                    resolved_dy = 0.0
                    break

            resolved_dx = _largest_free_component(
                resolved_dx,
                lambda candidate: not meeting(nudge_x + candidate, nudge_y),
            )

        # Vertical pass, mirroring the horizontal pass.
        if abs(resolved_dy) > _EPSILON and meeting(nudge_x, nudge_y + resolved_dy):
            for amount in _descending_amounts(speed):
                if not pressing_right and not meeting(
                    nudge_x - amount,
                    nudge_y + resolved_dy,
                ):
                    nudge_x -= amount
                    resolved_dx = 0.0
                    break
                if not pressing_left and not meeting(
                    nudge_x + amount,
                    nudge_y + resolved_dy,
                ):
                    nudge_x += amount
                    resolved_dx = 0.0
                    break

            resolved_dy = _largest_free_component(
                resolved_dy,
                lambda candidate: not meeting(nudge_x, nudge_y + candidate),
            )

        # Axis checks can both pass while the combined diagonal still clips a
        # corner.  Contract both components together until the result is free.
        if meeting(nudge_x + resolved_dx, nudge_y + resolved_dy):
            resolved_dx, resolved_dy = _shrink_vector_until_free(
                resolved_dx,
                resolved_dy,
                lambda candidate_x, candidate_y: not meeting(
                    nudge_x + candidate_x,
                    nudge_y + candidate_y,
                ),
            )

        return MovementResult(
            dx=resolved_dx,
            dy=resolved_dy,
            nudge_x=nudge_x,
            nudge_y=nudge_y,
            blocked_x=abs((nudge_x + resolved_dx) - original_dx) > _EPSILON,
            blocked_y=abs((nudge_y + resolved_dy) - original_dy) > _EPSILON,
        )


def move_actor(
    actor: object,
    collision_world: CollisionWorld,
    dx: float,
    dy: float,
    move_speed: float,
    **input_state: bool,
) -> MovementResult:
    """Resolve and apply movement to an actor with ``x``, ``y``, and a hitbox."""

    hitbox = _actor_hitbox(actor)
    result = collision_world.resolve_movement(
        hitbox,
        dx,
        dy,
        move_speed,
        **input_state,
    )
    actor.x += result.total_dx
    actor.y += result.total_dy
    return result


def move_step_solids_direction(
    actor: object,
    amount: float,
    direction: float,
    collision_world: CollisionWorld,
    *,
    apply: bool = True,
) -> MovementResult:
    """Reproduce ``scr_move_step_solids_direction`` for NPCs/cutscene actors.

    GameMaker directions use 0 degrees for right and 90 degrees for up.
    """

    angle = radians(direction)
    dx = cos(angle) * amount
    dy = -sin(angle) * amount
    hitbox = _actor_hitbox(actor)

    if collision_world.place_meeting(hitbox, dx, dy):
        if not collision_world.place_meeting(hitbox, dx, 0.0):
            dy = 0.0
        elif not collision_world.place_meeting(hitbox, 0.0, dy):
            dx = 0.0

    result = MovementResult(dx=dx, dy=dy)
    if apply:
        actor.x += dx
        actor.y += dy
    return result


def create_hitbox_solid(
    hitbox_or_actor: Rect | Sequence[float] | object,
    *,
    source_object: str | None = None,
    owner: object | None = None,
    category: str = "solid",
) -> Collider:
    """Create a rectangular solid matching a hitbox.

    This is the Python equivalent of ``scr_create_hitbox_solid``; no sprite or
    40x40 GameMaker scaling intermediary is necessary.
    """

    try:
        rect = as_rect(hitbox_or_actor)
    except TypeError:
        rect = _actor_hitbox(hitbox_or_actor)
    return Collider(
        shape=CollisionShape.rectangle(rect.x, rect.y, rect.width, rect.height),
        category=category,
        source_object=source_object,
        owner=owner,
    )


def _actor_hitbox(actor: object) -> Rect:
    getter = getattr(actor, "get_hitbox", None)
    if callable(getter):
        return as_rect(getter())

    hitbox = getattr(actor, "hitbox", None)
    if hitbox is not None:
        return as_rect(hitbox)

    return as_rect(actor)


def _descending_amounts(amount: float) -> Iterator[float]:
    candidate = max(0.0, amount)
    while candidate > _EPSILON:
        yield candidate
        candidate -= 1.0


def _toward_zero(value: float) -> float:
    if value > 0.0:
        return max(0.0, value - 1.0)
    if value < 0.0:
        return min(0.0, value + 1.0)
    return 0.0


def _largest_free_component(
    component: float,
    is_free: Callable[[float], bool],
) -> float:
    candidate = component
    while True:
        if is_free(candidate):
            return candidate
        if abs(candidate) <= _EPSILON:
            return 0.0
        candidate = _toward_zero(candidate)


def _shrink_vector_until_free(
    dx: float,
    dy: float,
    is_free: Callable[[float, float], bool],
) -> tuple[float, float]:
    candidate_x = dx
    candidate_y = dy
    while abs(candidate_x) > _EPSILON or abs(candidate_y) > _EPSILON:
        candidate_x = _toward_zero(candidate_x)
        candidate_y = _toward_zero(candidate_y)
        if is_free(candidate_x, candidate_y):
            return candidate_x, candidate_y
    return 0.0, 0.0


def _convex_polygons_intersect(first: Sequence[Point], second: Sequence[Point]) -> bool:
    """Separating-axis test for two convex polygons."""

    for polygon in (first, second):
        for index, point in enumerate(polygon):
            next_point = polygon[(index + 1) % len(polygon)]
            edge_x = next_point[0] - point[0]
            edge_y = next_point[1] - point[1]
            axis = (-edge_y, edge_x)
            first_min, first_max = _project_polygon(first, axis)
            second_min, second_max = _project_polygon(second, axis)
            if first_max <= second_min + _EPSILON or second_max <= first_min + _EPSILON:
                return False
    return True


def _project_polygon(points: Sequence[Point], axis: Point) -> tuple[float, float]:
    projections = [point[0] * axis[0] + point[1] * axis[1] for point in points]
    return min(projections), max(projections)


__all__ = [
    "Collider",
    "CollisionShape",
    "CollisionWorld",
    "DEFAULT_SOLID_CATEGORIES",
    "MovementResult",
    "Rect",
    "as_rect",
    "coerce_collider",
    "create_hitbox_solid",
    "move_actor",
    "move_step_solids_direction",
]
