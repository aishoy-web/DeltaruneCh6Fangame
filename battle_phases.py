"""Frame-by-frame ports of obj_attackpress and obj_spellphase.

The source's Draw event *advances* attack timing, so advance() runs exactly
once per game frame; renderers must not mutate this state. The recovered bolt checks are built in; monster damage events are hooks.
"""
from __future__ import annotations

from dataclasses import dataclass
import random
from collections.abc import Callable, Mapping


def gml_choose(rng, *values):
    return rng.choice(values)


@dataclass(slots=True)
class AttackBolt:
    party_slot: int
    frame: float
    red: bool = False
    alive: bool = True
    pressed: bool = False


@dataclass(frozen=True, slots=True)
class BoltBurst:
    party_slot: int
    x: float
    y: float
    score: int
    color: str = "white"
    magnitude: float = 1.0


class AttackPressPhase:
    """Create/Draw/Other[11] port of obj_attackpress, 60-frame timing clock.

    A button press executes scr_boltcheck or scr_boltcheck_onebutton and
    notifies an optional post-check hook. Hero damage is a separate callback.
    """

    def __init__(self, state, flags: Mapping[int, int], party_auto: Mapping[int, int], *,
                 rng=None, equipped_weapons: Mapping[int, int] | None = None,
                 on_bolt_check: Callable | None = None,
                 on_attack_trigger: Callable | None = None,
                 on_finish: Callable | None = None):
        self.state = state
        self.flags = flags
        self.party_auto = party_auto
        self.rng = rng if rng is not None else random.Random()
        self.equipped_weapons = dict(equipped_weapons or {})
        self.on_bolt_check = on_bolt_check
        self.on_attack_trigger = on_attack_trigger
        self.on_finish = on_finish
        self.active = True  # fastmode=1 forces active=1
        self.fastmode = 1
        self.goahead = 0
        self.linespeed = 2
        self.linex = -10
        self.spelluse = 0
        self.spelldelay = [10, 10, 10]
        self.maxdelay = 0
        self.maxdelaytimer = 0
        self.havechar = [int(action == 1) for action in state.charaction]
        self.charitem = [int(action == 4) for action in state.charaction]
        self.charspell = [int(action == 2) for action in state.charaction]
        for action in state.charaction:
            if action in (2, 4):
                self.maxdelay += 40 if self.maxdelay == 0 else 15
        # Original Create resets spelluse to 0 after counting actions.
        self.fade = self.fadeamt = self.fakefade = 0
        self.target = 0
        state.hittarget[:] = state.chartarget[:]
        self.imagetimer = self.posttimer = 0
        self.timermax = 50 if any(self.havechar) else 3
        self.boltgap, self.boltspeed, self.boltx = 20, 8, 0
        self.points = [0, 0, 0]
        self.bursts: list[BoltBurst] = []
        self.bolt_hits: list[tuple[int, int, int]] = []  # (bolt_index, party_slot, score)
        self.pressbuffer = [0, 0, 0, 0]
        self.charbolt = self.havechar[:]
        self.attacked = [0, 0, 0]
        self.bolttotal = sum(self.charbolt)
        self.boltxoff = 0
        self.my_method = 1
        self.boltnum = 1
        self.diff = 10 + (2 if flags.get(13, 0) == 0 else 0)
        self.bolts: list[AttackBolt] = []
        eligible = [i for i in range(3) if self.havechar[i]]
        # Source chooses each remaining party slot exactly once.
        self.rng.shuffle(eligible)
        lastbolt = -1
        for i, slot in enumerate(eligible):
            self.boltxoff += lastbolt
            frame = 30 + self.boltxoff
            red = False
            if i < len(eligible) - 1:
                if lastbolt != 0 and slot != eligible[i + 1]:
                    lastbolt = gml_choose(self.rng, 0, self.diff, self.diff * 1.5)
                    red = True
                else:
                    lastbolt = gml_choose(self.rng, self.diff, self.diff * 1.5)
            else:
                lastbolt = gml_choose(self.rng, self.diff, self.diff * 1.5)
            self.bolts.append(AttackBolt(slot, frame, red))
        self.haveauto = False
        self.autoed = False
        self.susie_slot = None
        if party_auto.get(2, 0) == 1:
            self.susie_slot = next((i for i, cid in enumerate(state.party_ids) if cid == 2), None)
            if self.susie_slot is not None:
                actor = next((a for a in state.actors if a.slot == self.susie_slot), None)
                if actor is not None and actor.hp is not None and actor.hp >= 0 and actor.can_move:
                    self.haveauto = True
                    if self.timermax == 3:
                        self.timermax = 50
        self.finished = False
        self.button_events: list[tuple[int, int | None]] = []

    def button(self, key: str) -> bool:
        """Route keyboard input to the recovered GML timing checks."""
        if self.finished or not self.active or not any(e.active for e in self.state.enemies):
            return False
        normalized = key.lower()
        if self.flags.get(13, 0) == 1:
            slot = {'z': 0, 'return': 0, 'space': 0, 'x': 1, 'c': 2}.get(normalized)
            if slot is None or not self.havechar[slot]:
                return False
        else:
            if normalized not in ('z', 'return', 'space'):
                return False
            slot = None
        self.button_events.append((self.boltx, slot))
        if slot is None:
            self.boltcheck_onebutton()
        else:
            self.boltcheck(slot)
        # Optional existing integration hook now observes the post-check state.
        if self.on_bolt_check is not None:
            self.on_bolt_check(self, slot)
        return True

    def _flash(self, slot: int | None) -> None:
        """Original three-button indexes by char ID; one-button flashes all."""
        if slot is None:
            for i in range(4):
                self.pressbuffer[i] = 5
        else:
            char_id = self.state.party_ids[slot]
            # GameMaker can grow an array when Noelle (ID 4) is used.
            if char_id >= len(self.pressbuffer):
                self.pressbuffer.extend([0] * (char_id + 1 - len(self.pressbuffer)))
            self.pressbuffer[char_id] = 5

    def _score_bolt(self, index: int, offset: float, *, special_weapon=False) -> int:
        """The original per-bolt score table, including its special one-button rule."""
        bolt = self.bolts[index]
        if not bolt.alive:
            return 0
        slot = bolt.party_slot
        delta = abs(offset)
        perfect = delta == 0 or (special_weapon and offset == 1)
        if perfect:
            score, color, mag = 150, "yellow", 0.2
        elif delta == 1:
            score, color, mag = 120, "white", 1.0
        elif delta == 2:
            score, color, mag = 110, "white", 1.0
        else:
            score, color, mag = int(100 - delta * 2), "party", 1.0
        bolt.alive = False
        bolt.pressed = True
        self.points[slot] += score  # GML += ; multiple bolts accumulate.
        self.bolt_hits.append((index, slot, score))
        ox, oy = self.state.attack_press_position or (2.0, 365.0)
        bx = ox + 80 + (bolt.frame - self.boltx) * self.boltspeed
        by = oy + 38 * slot
        self.bursts.append(BoltBurst(slot, bx, by, score, color, mag))
        return score

    def boltcheck(self, slot: int) -> int:
        """scr_boltcheck(arg0); earliest signed offset among eligible live bolts."""
        if not 0 <= slot < 3:
            raise IndexError(slot)
        self._flash(slot)
        chosen, best = -1, 99.0
        for i, bolt in enumerate(self.bolts):
            delta = bolt.frame - self.boltx
            if bolt.party_slot == slot and bolt.alive and -5 < delta < 15 and delta < best:
                chosen, best = i, delta
        return self._score_bolt(chosen, best) if chosen != -1 else 0

    def boltcheck_onebutton(self) -> int:
        """scr_boltcheck_onebutton: earliest bolt plus source's last equal-offset tie."""
        self._flash(None)
        chosen, second, best = -1, -1, 999.0
        for i, bolt in enumerate(self.bolts):
            delta = bolt.frame - self.boltx
            if not bolt.alive or not (-5 < delta < 15):
                continue
            if delta == best:
                second = i
            if delta < best:
                best, chosen = delta, i
                # The original does not reset dualbolt here: preserved.
        if chosen == -1:
            return 0
        score = self._score_bolt(chosen, best,
                                 special_weapon=(self.equipped_weapons.get(1) == 33))
        if second != -1 and second != chosen:
            score += self._score_bolt(second, best)
        return score

    def set_bolt_result(self, bolt_index: int, points: int) -> None:
        """Compatibility API for explicit scoring overrides from other events.

        A supplied value is the new total (as in the earlier adapter), while
        scr_boltcheck uses _score_bolt for the source's additive totals.
        """
        bolt = self.bolts[bolt_index]
        if not bolt.alive:
            return
        bolt.pressed = True
        bolt.alive = False
        self.points[bolt.party_slot] = int(points)
        self._flash(bolt.party_slot)

    def _trigger(self, slot: int, *, automated=False):
        actor = next((a for a in self.state.actors if a.slot == slot), None)
        if actor is not None and any(enemy.active for enemy in self.state.enemies):
            actor.points = self.points[slot]
            actor.state = 1
            actor.attacktimer = 0
            if automated:
                actor.is_auto_susie = True
            if self.on_attack_trigger is not None:
                self.on_attack_trigger(self.state, actor, slot)

    def advance(self):
        if self.finished:
            return
        self.maxdelaytimer += 1
        self.active = self.active or self.maxdelaytimer >= self.maxdelay
        if not self.active:
            return
        # Source draws/updates all bolt positions on the same frame.
        for bolt in self.bolts:
            if bolt.alive and bolt.frame - self.boltx < -5:
                bolt.alive = False
        for slot in range(3):
            if self.havechar[slot] and not self.attacked[slot] and not any(
                    bolt.alive and bolt.party_slot == slot for bolt in self.bolts):
                self.attacked[slot] = 1
                self.target = slot
                self._trigger(slot)  # obj_attackpress Other[11] / User[1]
        if not any(enemy.active for enemy in self.state.enemies):
            self.fakefade = 1
            self.posttimer = max(self.posttimer, self.timermax - 34)
        self.imagetimer = (self.imagetimer + 1) % 2
        self.boltx += 1
        self.pressbuffer = [n - 1 for n in self.pressbuffer]
        self.goahead = int(all(not self.havechar[i] or self.attacked[i] for i in range(3))
                           or not any(e.active for e in self.state.enemies))
        if self.goahead:
            self.posttimer += 1
            if (self.posttimer > self.timermax - 35 and self.haveauto and not self.autoed
                    and any(e.active for e in self.state.enemies)):
                slot = self.susie_slot
                if slot is not None:
                    self.points[slot] = 0 if self.state.automiss[self.state.chartarget[slot]] else 160
                    self._trigger(slot, automated=True)
                    self.posttimer -= 25
                    self.autoed = True
            if self.posttimer > self.timermax:
                self.fade = 1
                self.finished = True
                for actor in self.state.actors:
                    if actor.state == 1:
                        actor.state = 0
                if self.on_finish is not None:
                    self.on_finish(self)


class SpellPhase:
    """obj_spellphase Create, Alarm[0] and Step, including ordered casters."""

    def __init__(self, state, *, on_cast: Callable | None = None,
                 on_finish: Callable | None = None):
        self.state = state
        self.on_cast = on_cast
        self.on_finish = on_finish
        self.spelltimer = 0
        self.spellmax = 40
        self.spelltotal = 0
        self.char = 0
        self.castyet = 0
        self.re_castyet = 0
        self.active = 0
        self.alarm0 = 5
        self.using = [0] * 3
        self.gotspell = [0] * 3
        self.gotitem = [0] * 3
        self.writer_alive = False
        self.finished = False
        self.cast_history: list[tuple[int, str]] = []

    def dismiss_text(self):
        """The future battle-text writer signals it no longer exists."""
        self.writer_alive = False

    def _cast(self, slot: int):
        is_item = bool(self.gotitem[slot])
        actor = next((a for a in self.state.actors if a.slot == slot), None)
        if actor is not None:
            actor.state = 4 if is_item else 2
            actor.attacktimer = 0
        kind = "item" if is_item else "spell"
        self.cast_history.append((slot, kind))
        # scr_spelltext is invoked by the controller's on_cast adapter.
        # The unprovided scr_battletext_default writer remains external;
        # returning truthy means its text is still on screen.
        self.writer_alive = bool(self.on_cast(self.state, slot, kind)
                                 if self.on_cast is not None else False)

    def _alarm(self):
        s = self.state
        for slot in range(3):
            action = s.charaction[slot]
            queued = s.queued[slot]
            # Temporary adapter until scr_itemconsumeb and scr_spellconsumeb
            # set original numeric action IDs; do not alter charaction[].
            if action not in (2, 4) and queued is not None:
                action = {'spell': 2, 'item': 4}.get(queued.kind, action)
            if action == 2:
                self.spelltotal += 1
                self.using[slot] = self.gotspell[slot] = 1
            if action == 4:
                self.spelltotal += 1
                self.using[slot] = self.gotitem[slot] = 1
            if action in (2, 4) and not self.castyet:
                self.castyet = 1
                self.char = slot + 1
                self._cast(slot)
        self.active = 1
        s.spelldelay = 90

    def _finish(self):
        self.finished = True
        if self.on_finish is not None:
            self.on_finish(self)

    def advance(self):
        if self.finished:
            return
        if self.alarm0 > 0:
            self.alarm0 -= 1
            if self.alarm0 == 0:
                self._alarm()
        if not self.active:
            return
        self.spelltimer += 1
        if self.spelltimer < self.state.spelldelay or self.writer_alive:
            return
        # GML checks 'char >= 3 || spelltotal == 1'. Zero casters is an
        # adapter-only path from unsupported ACT codes; it must not deadlock.
        if self.char >= 3 or self.spelltotal <= 1 or not any(e.active for e in self.state.enemies):
            self._finish()
            return
        # Source looks at the current char cursor BEFORE advancing it. If
        # no cast exists at that slot, spelldelay becomes 1 for the next check.
        self.re_castyet = int(bool(self.gotitem[self.char] or self.gotspell[self.char]))
        if self.re_castyet:
            self._cast(self.char)
        self.state.spelldelay = 90 if self.re_castyet else 1
        self.char += 1
        # GML repeat(2): skip at most two unused remaining party slots.
        for _ in range(2):
            if self.char < 3 and not self.using[self.char]:
                self.char += 1
        self.spelltimer = 0
        self.re_castyet = 0
