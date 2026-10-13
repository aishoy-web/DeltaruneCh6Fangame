"""Temporary Tk Canvas adapter for the GML battle-entry controller.

This view intentionally uses shape/text stand-ins where the original sprite
sheets and obj_battlecontroller's Draw events have not yet been ported.
GameMaker stage coordinates (640x480) are halved for Game's 320x240 viewport.
"""
from __future__ import annotations


class BattleCanvasView:
    TAG = "battle_preview"

    def __init__(self, game):
        self.game = game
        self.layout = None
        self.afterimages = []

    def start(self, layout):
        self.layout = layout
        self.afterimages.clear()

    def add_afterimage(self, marker, battle_state):
        self.afterimages.append((
            marker.x, marker.y, marker.sprite, battle_state.elapsed_frames,
        ))
        self.afterimages = self.afterimages[-30:]

    def _pos(self, x, y):
        ox, oy = self.layout.camera_origin
        return self.game.ui_to_screen((x - ox) / 2, (y - oy) / 2)

    def render(self, state, combat=None):
        if self.layout is None:
            return
        c = self.game.canvas
        scale = self.game.scale
        c.delete(self.TAG)
        w = max(c.winfo_width(), 320)
        h = max(c.winfo_height(), 240)
        c.create_rectangle(0, 0, w, h, fill="black", outline="black", tags=self.TAG)

        # On the handoff, GML creates the actual enemy battle instances.
        # We only have their metadata so far, not their Draw events.
        if state.controller_started:
            # Use instantiated monster lifecycles rather than unconditionally
            # drawing every original encounter definition after a KO/spare.
            live_enemies = (combat.state.enemies if combat is not None
                            else self.layout.enemy_definitions)
            for enemy in live_enemies:
                if getattr(enemy, "active", True):
                    self._draw_actor(enemy.x, enemy.y, enemy.object_name.replace('obj_', ''), enemy=True)
            if combat is not None:
                for actor in combat.state.actors:
                    if not getattr(actor, "visible", True):
                        continue
                    # The recovered parent object supplies a symbolic sprite/pose.
                    # Sprite sheets aren't available in this source-only build.
                    pose = {0: 'READY', 1: 'ATTACK', 2: 'SPELL', 4: 'ITEM',
                            6: 'ACT', 7: 'VICTORY', 8: 'SPECIAL'}.get(actor.state, '')
                    if actor.hp is not None and actor.hp <= 0:
                        pose = 'DOWN'
                    elif actor.hero_animation is not None and actor.hero_animation.hurt:
                        pose = 'HURT'
                    self._draw_actor(actor.x, actor.y, self._party_name(actor.character_id),
                                     pose=pose)
            else:
                for i, (x, y) in enumerate(self.layout.hero_positions):
                    if i < len(state.party_markers):
                        self._draw_actor(x, y, self._party_name(state.party_markers[i].character_id))
        else:
            for marker in state.markers:
                if marker is not None and marker.alive:
                    self._draw_actor(marker.x, marker.y,
                                     marker.sprite.replace('obj_', '').replace('spr_', ''), enemy=True)
            self.afterimages = [entry for entry in self.afterimages
                                if state.elapsed_frames - entry[3] < 9]
            for x, y, sprite, frame in self.afterimages:
                if state.elapsed_frames - frame < 7:
                    px, py = self._pos(x, y)
                    size = max(2, scale * 2)
                    c.create_rectangle(px-size, py-size, px+size, py+size,
                                       fill='#454545', outline='', tags=self.TAG)
            for marker in state.party_markers:
                if marker.alive:
                    self._draw_actor(marker.x, marker.y,
                                     self._party_name(marker.character_id))

        if state.controller_started and combat is not None:
            self._combat_spells = getattr(combat, "spells", {})
            self._combat_items = getattr(combat, "items", {})
            self._combat_acts = getattr(combat, "acts", {})
            self._draw_combat_ui(combat.state if hasattr(combat, "state") else combat)
            for anim in getattr(combat, 'rudebuster_animations', ()):
                if anim.alive:
                    px, py = self._pos(anim.x + 40, anim.y + 30)
                    c.create_text(px, py, text=('RED BUSTER' if anim.red else 'RUDE BUSTER'),
                                  fill='#ff5555' if anim.red else '#eecaff',
                                  font=('TkFixedFont', max(7, round(8 * scale))),
                                  tags=self.TAG)
            self._draw_resolution_overlay(combat)
            self._draw_rudebuster_bolts(combat)
        elif state.controller_started:
            message = self.layout.battle_message.replace('&', '\n')
            px, py = self.game.ui_to_screen(10, 195)
            c.create_text(px, py, anchor='nw', text=message,
                          fill='white', font=('Determination Mono Web', max(9, round(9*scale))),
                          width=max(1, round(295*scale)), tags=self.TAG)
            px, py = self.game.ui_to_screen(10, 228)
            c.create_text(px, py, anchor='nw',
                          text='Battle actions pending obj_battlecontroller port — X: exit preview',
                          fill='#aaaaaa', font=('TkFixedFont', max(7, round(6*scale))),
                          tags=self.TAG)
        c.tag_raise(self.TAG)

    def _draw_rudebuster_bolts(self, combat):
        """Read-only shape preview of obj_rudebuster_bolt Draw/self + afterimages.

        The exact spr_rudebuster_beam sprites and scr_afterimage visuals are
        not included in the source bundle. The positions and lifetimes come
        from the original projectile Step logic, never from draw calls.
        """
        from math import cos, sin, radians
        canvas = self.game.canvas
        scale = self.game.scale
        for bolt in getattr(combat, 'rudebuster_bolts', ()):
            for trail in bolt.trails[-24:]:
                x, y = self._pos(trail.x, trail.y)
                radius = max(1.0, scale * max(0.2, trail.yscale))
                canvas.create_oval(x-radius, y-radius, x+radius, y+radius,
                                   fill='#c75a6b' if bolt.red else '#ad69e3',
                                   outline='', tags=self.TAG)
            if bolt.visible and bolt.alive:
                x, y = self._pos(bolt.x, bolt.y)
                rad = radians(bolt.image_angle)
                length = 13 * scale * bolt.image_xscale / 2
                vx, vy = cos(rad) * length, -sin(rad) * length
                canvas.create_line(x-vx, y-vy, x+vx, y+vy,
                                   fill='#ff565a' if bolt.red else '#d68dff',
                                   width=max(2, round(scale * bolt.image_yscale)),
                                   tags=self.TAG)
                canvas.create_oval(x-3*scale, y-3*scale, x+3*scale, y+3*scale,
                                   fill='#fff4ff', outline='', tags=self.TAG)
            if bolt.explode:
                x, y = self._pos(bolt.cx, bolt.cy)
                for burst in bolt.bursts:
                    radius = min(25, max(0, (bolt.t - 1) * burst.speed * 0.06)) * scale
                    angle = radians(burst.angle)
                    px, py = x + cos(angle) * radius, y - sin(angle) * radius
                    size = max(1, scale * burst.xscale)
                    canvas.create_oval(px-size, py-size, px+size, py+size,
                                       fill='#ffdf72' if bolt.bonus_anim else '#ddaaff',
                                       outline='', tags=self.TAG)

    def _draw_combat_ui(self, battle):
        """Scalable provisional version of obj_battlecontroller Draw[0].

        The GML uses coordinates in a 640x480 viewport. These UI elements
        are authored in Game's 320x240 logical coordinates, then scaled via
        ui_to_screen. Battle sprite-specific HUD work belongs to scr_charbox.
        """
        c = self.game.canvas
        scale = self.game.scale
        tag = self.TAG

        def coords(x, y):
            return self.game.ui_to_screen(x, y)

        def rect(x0, y0, x1, y1, color, outline=""):
            a, b = coords(x0, y0)
            x, y = coords(x1, y1)
            c.create_rectangle(a, b, x, y, fill=color, outline=outline, tags=tag)

        def text(x, y, label, color="#ffffff", size=9, anchor="nw", width=None):
            px, py = coords(x, y)
            opts = {"text": str(label), "fill": color, "anchor": anchor,
                    "font": ("Determination Mono Web", max(7, round(size*scale))),
                    "tags": tag}
            if width is not None:
                opts["width"] = max(1, round(width * scale))
            c.create_text(px, py, **opts)

        def clean(message):
            from battle_spelltext import battle_text_to_display
            return battle_text_to_display(str(message))

        panel_top = (480 - battle.bp) / 2
        rect(0, panel_top, 320, 240, "#050505")
        rect(0, panel_top, 320, panel_top + 1, "#4b3656")
        rect(0, panel_top + 17, 320, panel_top + 18, "#4b3656")

        # Temporary party status: actual status sprites come from scr_charbox.
        party = battle.actors
        if party:
            width = 320 / len(party)
            for i, actor in enumerate(party):
                x = i * width + 4
                color = {1: "#00ffff", 2: "#ff00ff", 3: "#00ff00", 4: "#ffff00"}.get(actor.character_id, "white")
                hp = (f"{actor.hp}/{actor.max_hp}" if actor.hp is not None and actor.max_hp is not None else "--/--")
                text(x, panel_top + 2, f"{actor.name}  {hp}", color, 8)
        text(316, panel_top + 1, f"TP {int(battle.tension / battle.maxtension * 100) if battle.maxtension else 0}%", "#ff9b50", 7, anchor="ne")

        if battle.phase == "victory":
            text(12, panel_top + 24, clean(battle.victory_message), size=10, width=290)
            text(12, 229, "Z: continue", "#aaaaaa", 7)
            return
        if battle.phase in ("awaiting_resolution", "enemy_turn", "awaiting_wincombat", "chained_encounter"):
            labels = {
                "awaiting_resolution": "Party actions selected.",
                "enemy_turn": "Enemy attack phase",
                "awaiting_wincombat": "Battle victory pending",
                "chained_encounter": "A new enemy wave approaches!",
            }
            if battle.phase == "awaiting_resolution":
                labels.update({
                    "awaiting_resolution": {
                        "attack_press": "FIGHT — Attack timing",
                        "spell_phase": "Spell / item resolution",
                        "act": "Kris ACT",
                        "next_act": "Sequential ACT",
                        "act_simul": "Simultaneous ACT",
                    }.get(battle.resolution_stage, "Party actions selected.")
                })
            text(12, panel_top + 24, labels[battle.phase], size=10)
            source_text = (battle.spell_messages[0] if battle.resolution_stage == "spell_phase"
                           and battle.spell_messages else None)
            text(12, panel_top + 42, clean(source_text) if source_text else
                 (battle.feedback or "Waiting for combat scripts."),
                 "#aaaaaa", 8, width=290)
            if battle.hero_attack_events:
                last = battle.hero_attack_events[-1]
                label = (f"HIT {last.damage}" if last.resolved else
                         "HIT: enemy/party stats or target unavailable")
                text(174, panel_top + 24, label, "#ffda75", 8, width=142)
            return
        if battle.phase == "done":
            return

        turn = battle.charturn
        menu = battle.bmenuno
        text(7, panel_top + 19, clean(battle.battle_message), size=9, width=305)
        if menu == 0:
            # Source five-icon command row: left/right wraps; Z confirms.
            names = ("FIGHT", "ACT", "ITEM", "SPARE", "DEFEND")
            for idx, name in enumerate(names):
                x = 5 + idx * 63
                selected = idx == battle.bmenucoord[0][turn]
                rect(x, 217, x + 59, 238, "#292036" if selected else "#0c0c0c",
                     "#ffffff" if selected else "#555555")
                text(x + 30, 222, name, "#ffff66" if selected else "#dddddd", 8, anchor="n")
        elif menu in (1, 3, 11, 12, 13, 7, 8):
            enemy_menu = menu in (1, 3, 11, 12, 13)
            members = ([(e.slot, e.name, e) for e in battle.enemies if e.active]
                       if enemy_menu else [(a.slot, a.name, a) for a in battle.actors if a.can_target])
            for row, (slot, label, actor) in enumerate(members[:3]):
                y = 190 + row*16
                active = battle.bmenucoord[menu][turn] == slot
                text(11, y, "♥" if active else " ", "#ff3333", 9)
                text(27, y, label, "#ffff66" if active else "white", 9)
                if enemy_menu:
                    if actor.hp is not None and actor.max_hp:
                        text(206, y, f"HP {max(0, actor.hp)*100/actor.max_hp:.0f}%", "#98ff81", 7)
                    if actor.mercy is not None:
                        text(273, y, f"{min(100, actor.mercy):.0f}%", "#ffff50", 7)
            if menu == 11:
                text(160, 180, "ACT target", "#aaaaaa", 7)
        elif menu in (2, 4, 9):
            options = []
            if menu == 2:
                options = list(enumerate(getattr(self, "_combat_spells", {}).get(turn, [])))
            elif menu == 4:
                options = list(enumerate([None] * 13))
                options = [(i, getattr(self, "_combat_items", {}).get(battle.tempitem[i][turn]))
                           for i in range(13) if battle.tempitem[i][turn] in getattr(self, "_combat_items", {})]
            elif menu == 9:
                selected_enemy = battle.bmenucoord[11][turn]
                options = list(enumerate(getattr(self, "_combat_acts", {}).get((selected_enemy, battle.party_ids[turn]), [])))
            selection = battle.bmenucoord[menu][turn]
            page = selection // 6
            visible = [(i, o) for i, o in options if i // 6 == page and o is not None]
            for index, option in visible:
                ix = index % 6
                x, y = (16 if ix % 2 == 0 else 150), 188 + (ix // 2)*17
                text(x, y, ("♥ " if selection == index else "  ") + option.name,
                     "#ffff66" if selection == index else "#ffffff", 8, width=160)
            if not visible:
                text(16, 191, "No entries loaded for this menu.", "#aaaaaa", 8)
        if battle.feedback:
            text(7, 207 if menu == 0 else 233, battle.feedback, "#ffc387", 7, width=300)

    def _draw_resolution_overlay(self, combat):
        """Temporary sprite-free rendering for attackpress and spellphase.

        GML's attackpress Draw event changes timer state; it is intentionally
        performed in battle_phases.advance() rather than inside this method.
        """
        battle = combat.state
        canvas = self.game.canvas
        phase = getattr(combat, "attack_press", None)
        if battle.resolution_stage == "attack_press" and phase is not None:
            for slot in range(3):
                if not phase.havechar[slot] or not battle.party_ids[slot]:
                    continue
                y = (365 + slot * 38) / 2
                x0, top = self.game.ui_to_screen(41, y)
                x1, bottom = self.game.ui_to_screen(102, y + 18)
                color = {1: "#3046a0", 2: "#913e99", 3: "#367d57", 4: "#bfae3f"}.get(
                    battle.party_ids[slot], "#777777")
                canvas.create_rectangle(x0, top, x1, bottom, outline=color,
                                        width=max(1, round(self.game.scale)), tags=self.TAG)
                ix, iy = self.game.ui_to_screen(41, y + 9)
                canvas.create_line(ix, top, ix, bottom, fill="#ffffff",
                                   width=max(1, round(self.game.scale)), tags=self.TAG)
                label = "Z" if combat.flags.get(13, 0) == 0 else ("Z", "X", "C")[slot]
                tx, ty = self.game.ui_to_screen(6, y + 4)
                canvas.create_text(tx, ty, anchor="nw", text=f"{label}: {battle.party_ids[slot]}",
                                   fill="#eeeeee", font=("TkFixedFont", max(7, round(8 * self.game.scale))),
                                   tags=self.TAG)
            for burst in phase.bursts[-6:]:
                bx, by = self.game.ui_to_screen(
                    (burst.x - (self.layout.camera_origin[0])) / 2,
                    (burst.y - (self.layout.camera_origin[1])) / 2 + 9)
                color = "#ffe04a" if burst.color == "yellow" else "#ddddff"
                r = max(2, 5 * self.game.scale)
                canvas.create_oval(bx-r, by-r, bx+r, by+r, outline=color,
                                   width=max(1, round(self.game.scale)), tags=self.TAG)
            for bolt in phase.bolts:
                if bolt.alive:
                    # Attack spot at GML x+80+(boltframe-boltx)*boltspeed.
                    px, py = self.game.ui_to_screen(
                        (82 + (bolt.frame - phase.boltx) * phase.boltspeed) / 2,
                        (365 + bolt.party_slot * 38) / 2 + 9)
                    radius = max(2, 3 * self.game.scale)
                    canvas.create_oval(px-radius, py-radius, px+radius, py+radius,
                                       fill="#ffff65" if bolt.red else "#ffffff",
                                       outline="", tags=self.TAG)
        spell = getattr(combat, "spell_phase", None)
        if battle.resolution_stage == "spell_phase" and spell is not None:
            x, y = self.game.ui_to_screen(16, 193)
            if spell.cast_history:
                slot, kind = spell.cast_history[-1]
                label = f"{battle.actors[slot].name if slot < len(battle.actors) else 'Party'}: {kind.upper()}"
            else:
                label = "Preparing spell and item actions..."
            canvas.create_text(x, y, anchor="nw", text=label,
                               fill="#ffffff", font=("TkFixedFont", max(7, round(9*self.game.scale))),
                               tags=self.TAG)

    def _draw_actor(self, x, y, label, *, enemy=False, pose=""):
        c = self.game.canvas
        px, py = self._pos(x, y)
        s = self.game.scale
        width = max(9, round(11*s))
        height = max(9, round(13*s))
        outline = '#bbbbbb' if enemy else '#bba3e5'
        c.create_rectangle(px-width/2, py-height, px+width/2, py,
                           fill='#161616', outline=outline,
                           width=max(1, round(s)), tags=self.TAG)
        c.create_text(px, py + 2*s, anchor='n', text=label[:19],
                      fill=outline,
                      font=('TkFixedFont', max(6, round(7*s))), tags=self.TAG)
        if pose:
            c.create_text(px, py + 10*s, anchor='n', text=pose,
                          fill='#aaa6a6',
                          font=('TkFixedFont', max(6, round(6*s))), tags=self.TAG)

    @staticmethod
    def _party_name(character_id):
        return {1:'Kris', 2:'Susie', 3:'Ralsei', 4:'Noelle'}.get(character_id, 'Party')

    def hide(self):
        self.game.canvas.delete(self.TAG)
        self.afterimages.clear()
        self.layout = None
