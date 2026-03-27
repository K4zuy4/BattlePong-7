from __future__ import annotations

import logging
import math
import random

import pygame

try:
    from .base import Scene, SceneManager
except ImportError:  # fallback when run as script
    from pong.scenes.base import Scene, SceneManager

from pong.core.input import Action
from pong.effects.base import EffectContext
from pong.effects.manager import EffectManager
from pong.events import BallBouncePaddle, BallBounceWall, PointScored, RoundReset

logger = logging.getLogger(__name__)


class PlayScene(Scene):
    """Single-match scene with one equipped paddle ability and effect hooks."""

    def __init__(self, manager: SceneManager, font, font_small) -> None:
        self.manager = manager
        self.font = font
        self.font_small = font_small
        self.time = 0.0
        play_area = manager.app_ctx.get("play_area", (1280, 720)) if hasattr(manager, "app_ctx") else (1280, 720)
        self.width, self.height = play_area
        self.play_top = 64
        self.play_height = 0
        self.play_bottom = 0
        self._refresh_playfield_bounds()

        pad_w, pad_h = 14, 100
        margin = 32
        self.ball = {
            "x": self.width / 2 - 11,
            "y": self.play_top + self.play_height / 2 - 11,
            "vx": 320.0,
            "vy": 200.0,
            "size": 22,
            "angle": 0.0,
            "spin": 120.0,
        }
        self.ball_id = "main"
        self.margin = margin
        self.pad_w = pad_w
        self.pad_h = pad_h
        self.paddles = {
            "left": {
                "x": margin,
                "y": self.play_top + (self.play_height - pad_h) / 2,
                "w": pad_w,
                "h": pad_h,
                "base_speed": 320.0,
                "speed_multiplier": 1.0,
                "speed": 320.0,
            },
            "right": {
                "x": self.width - margin - pad_w,
                "y": self.play_top + (self.play_height - pad_h) / 2,
                "w": pad_w,
                "h": pad_h,
                "base_speed": 320.0,
                "speed_multiplier": 1.0,
                "speed": 320.0,
            },
        }
        self.left_score = 0
        self.right_score = 0
        self.player_move_dir = 0
        self.last_player_move_dir = 1
        self.left_dash_velocity = 0.0
        self.left_dash_time_left = 0.0

        self.managers: dict[str, EffectManager] = {}
        self._init_effects()
        self.equipped_ability_id: str | None = None

    def on_enter(self, payload=None) -> None:
        self.time = 0.0
        self.left_score = 0
        self.right_score = 0
        self._refresh_playfield_bounds()
        self._center_paddles()
        self._center_ball(direction=1)
        self._reset_runtime_state()
        self._sync_equipped_ability()
        self._publish_ability_ctx()

    def handle_event(self, event: pygame.event.Event) -> None:
        return

    def update(self, dt: float) -> None:
        self.time += dt
        self._refresh_playfield_bounds()
        for manager in self.managers.values():
            manager.on_tick(dt)
        self._handle_ability_input()
        self._update_paddles(dt)
        self._update_ball(dt)
        self._publish_ability_ctx()

    def draw(self, screen: pygame.Surface) -> None:
        self._refresh_playfield_bounds()
        self._draw_background(screen)
        self._draw_world(screen)
        self._draw_ui(screen)
        self._draw_effect_overlays(screen)

    def _draw_background(self, screen: pygame.Surface) -> None:
        ctx = self.manager.app_ctx if hasattr(self.manager, "app_ctx") else {}
        palette = ctx.get("palette")
        bg_image = ctx.get("bg_image")
        if bg_image:
            screen.blit(bg_image, (0, 0))
        else:
            bg = (12, 16, 26) if not palette else _hex_to_rgb(palette.background)
            screen.fill(bg)
        play_rect = pygame.Rect(0, self.play_top, self.width, self.play_height)
        mask = pygame.Surface((self.width, self.play_height), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 40))
        screen.blit(mask, play_rect.topleft)

    def _draw_world(self, screen: pygame.Surface) -> None:
        ctx = self.manager.app_ctx if hasattr(self.manager, "app_ctx") else {}
        palette = ctx.get("palette")
        accent = (90, 140, 255) if not palette else _hex_to_rgb(palette.accent)

        ball_img = ctx.get("ball_image")
        paddle_img = ctx.get("paddle_image")
        for key in ("left", "right"):
            paddle = self.paddles[key]
            rect = pygame.Rect(int(paddle["x"]), int(paddle["y"]), paddle["w"], paddle["h"])
            if paddle_img:
                scaled = pygame.transform.smoothscale(paddle_img, rect.size)
                screen.blit(scaled, rect)
            else:
                pygame.draw.rect(screen, accent, rect, border_radius=4)

        ball = self.ball
        ball_rect = pygame.Rect(int(ball["x"]), int(ball["y"]), ball["size"], ball["size"])
        if ball_img:
            scaled_ball = pygame.transform.smoothscale(ball_img, ball_rect.size)
            rotated = pygame.transform.rotate(scaled_ball, ball.get("angle", 0.0))
            rotated_rect = rotated.get_rect(center=ball_rect.center)
            screen.blit(rotated, rotated_rect)
        else:
            pygame.draw.ellipse(screen, accent, ball_rect)

    def _draw_ui(self, screen: pygame.Surface) -> None:
        palette = self.manager.app_ctx.get("palette") if hasattr(self.manager, "app_ctx") else None
        fg = (240, 220, 180) if not palette else _hex_to_rgb(palette.foreground)
        accent = (120, 180, 255) if not palette else _hex_to_rgb(palette.accent)

        pygame.draw.rect(screen, (20, 24, 32), pygame.Rect(0, 0, screen.get_width(), 64))
        pygame.draw.line(screen, accent, (0, 64), (screen.get_width(), 64), width=2)

        score_txt = f"{self.left_score}   |   {self.right_score}"
        score = self.font.render(score_txt, True, fg)
        screen.blit(score, (screen.get_width() // 2 - score.get_width() // 2, 14))

        ability_name = self._ability_name()
        ability_status = self._ability_status_text()
        name_text = self.font_small.render(f"Ability: {ability_name}", True, accent)
        status_text = self.font_small.render(ability_status, True, fg)
        screen.blit(name_text, (40, 10))
        screen.blit(status_text, (40, 34))

        hint = self.font_small.render("[Esc/P] Pause   [Space] Ability", True, fg)
        screen.blit(hint, (screen.get_width() - hint.get_width() - 40, 20))

    def _draw_effect_overlays(self, screen: pygame.Surface) -> None:
        for manager in self.managers.values():
            for eff in manager.active.values():
                draw = getattr(eff, "draw_overlay", None)
                if draw:
                    try:
                        draw(self._effect_context(), screen)
                    except Exception:
                        logger.exception("Effect overlay draw failed", extra={"id": getattr(eff, "id", "?")})

    def _active_goal_shield(self):
        abilities = self.managers.get("abilities")
        if not abilities:
            return None
        for eff in abilities.active.values():
            if getattr(eff, "active", False) and getattr(eff, "id", "") == "goal_shield":
                return eff
        return None

    def _update_ball(self, dt: float) -> None:
        ball = self.ball
        ball["x"] += ball["vx"] * dt
        ball["y"] += ball["vy"] * dt
        size = ball["size"]
        top = self.play_top
        bottom = self.play_bottom

        if ball["y"] <= top:
            ball["y"] = top
            ball["vy"] *= -1
            ball["vx"], ball["vy"] = _offset_angle(ball["vx"], ball["vy"], 8.0 if ball["vx"] >= 0 else -8.0)
            ball["spin"] *= -0.9
            angle = math.degrees(math.atan2(ball["vy"], ball["vx"]))
            self._emit(
                BallBounceWall(
                    ball_id=self.ball_id,
                    wall="top",
                    speed=math.hypot(ball["vx"], ball["vy"]),
                    spin=ball["spin"],
                    vx=ball["vx"],
                    vy=ball["vy"],
                    angle_deg=angle,
                )
            )

        if ball["y"] + size >= bottom:
            ball["y"] = bottom - size
            ball["vy"] *= -1
            ball["vx"], ball["vy"] = _offset_angle(ball["vx"], ball["vy"], -8.0 if ball["vx"] >= 0 else 8.0)
            ball["spin"] *= -0.9
            angle = math.degrees(math.atan2(ball["vy"], ball["vx"]))
            self._emit(
                BallBounceWall(
                    ball_id=self.ball_id,
                    wall="bottom",
                    speed=math.hypot(ball["vx"], ball["vy"]),
                    spin=ball["spin"],
                    vx=ball["vx"],
                    vy=ball["vy"],
                    angle_deg=angle,
                )
            )

        for key in ("left", "right"):
            paddle = self.paddles[key]
            rect = pygame.Rect(int(paddle["x"]), int(paddle["y"]), paddle["w"], paddle["h"])
            ball_rect = pygame.Rect(int(ball["x"]), int(ball["y"]), size, size)
            if not rect.colliderect(ball_rect):
                continue
            hit_pos = (ball_rect.centery - rect.centery) / (paddle["h"] / 2)
            hit_pos = max(-1.0, min(1.0, hit_pos))
            speed = max(320.0, (abs(ball["vx"]) + abs(ball["vy"])) * 0.55)
            dir_x = 1 if key == "left" else -1
            new_vx = dir_x * speed
            new_vy = hit_pos * speed * 0.75
            magnitude = math.hypot(new_vx, new_vy)
            target = max(340.0, magnitude)
            new_vx = new_vx / magnitude * target
            new_vy = new_vy / magnitude * target
            deflect = -10.0 if hit_pos < 0 else 10.0
            ball["vx"], ball["vy"] = _offset_angle(new_vx, new_vy, deflect)
            ball["spin"] = hit_pos * 720.0
            if key == "left":
                ball["x"] = paddle["x"] + paddle["w"]
            else:
                ball["x"] = paddle["x"] - size
            angle_deg = math.degrees(math.atan2(ball["vy"], ball["vx"]))
            self._emit(
                BallBouncePaddle(
                    ball_id=self.ball_id,
                    paddle_id=key,
                    hit_pos=hit_pos,
                    speed=target,
                    spin=ball["spin"],
                    vx=ball["vx"],
                    vy=ball["vy"],
                    angle_deg=angle_deg,
                )
            )

        shield = self._active_goal_shield()
        if shield and ball["x"] <= self.margin:
            ball["x"] = self.margin
            ball["vx"] = abs(ball["vx"])
            ball["vy"] *= 0.9
            ball["spin"] *= 0.7
            return

        if ball["x"] + size < 0:
            self._score_point("right")
            return
        if ball["x"] > self.width:
            self._score_point("left")
            return

        self._orient_spin(dt)
        ball["angle"] = (ball.get("angle", 0.0) + ball.get("spin", 0.0) * dt) % 360

    def _update_paddles(self, dt: float) -> None:
        input_state = self.manager.app.input if hasattr(self.manager, "app") else None
        up_held = bool(input_state and input_state.is_held(Action.UP))
        down_held = bool(input_state and input_state.is_held(Action.DOWN))

        move_dir = 0
        if up_held and not down_held:
            move_dir = -1
        elif down_held and not up_held:
            move_dir = 1
        self.player_move_dir = move_dir
        if move_dir != 0:
            self.last_player_move_dir = move_dir

        left = self.paddles["left"]
        right = self.paddles["right"]
        left["y"] += move_dir * left["speed"] * dt

        if self.left_dash_time_left > 0.0:
            left["y"] += self.left_dash_velocity * dt
            self.left_dash_time_left = max(0.0, self.left_dash_time_left - dt)
            if self.left_dash_time_left <= 0.0:
                self.stop_left_paddle_dash()

        ball = self.ball
        target = ball["y"] - right["h"] / 2
        if ball["vx"] > 0:
            if right["y"] + right["h"] / 2 < target:
                right["y"] += right["speed"] * dt
            elif right["y"] > target:
                right["y"] -= right["speed"] * dt

        top = self.play_top
        bottom = self.play_bottom
        for key in ("left", "right"):
            paddle = self.paddles[key]
            paddle["y"] = max(top, min(bottom - paddle["h"], paddle["y"]))

    def on_event(self, event) -> None:
        from pong.events import ResolutionChanged

        if isinstance(event, ResolutionChanged):
            return
        for manager in self.managers.values():
            manager.on_event(event)

    def _emit(self, event) -> None:
        app = getattr(self.manager, "app", None)
        if app and hasattr(app, "bus"):
            app.bus.publish(event)

    def _init_effects(self) -> None:
        app = getattr(self.manager, "app", None)
        if not app:
            return
        ctx = self._effect_context()
        self.managers = {
            "modifiers": EffectManager("modifiers", ["pong/effects/modifiers"], ctx),
            "chaos": EffectManager("chaos", ["pong/effects/chaos"], ctx),
            "abilities": EffectManager("abilities", ["pong/effects/abilities"], ctx),
        }

    def _effect_context(self) -> EffectContext:
        return EffectContext(app=self.manager.app, play_scene=self, bus=self.manager.app.bus, logger=logger, rng=random.Random())

    def _reset_runtime_state(self) -> None:
        self.stop_left_paddle_dash()
        self.set_left_speed_multiplier(1.0)
        for manager in self.managers.values():
            manager.reset()

    def _refresh_playfield_bounds(self) -> None:
        self.play_height = self.height - self.play_top
        self.play_bottom = self.play_top + self.play_height

    def _center_paddles(self) -> None:
        self.paddles["left"]["x"] = self.margin
        self.paddles["right"]["x"] = self.width - self.margin - self.pad_w
        self.paddles["left"]["y"] = self.play_top + (self.play_height - self.pad_h) / 2
        self.paddles["right"]["y"] = self.play_top + (self.play_height - self.pad_h) / 2
        self._refresh_paddle_speed("left")
        self._refresh_paddle_speed("right")

    def _center_ball(self, direction: int = 1) -> None:
        self.ball["x"] = self.width / 2 - self.ball["size"] / 2
        self.ball["y"] = self.play_top + self.play_height / 2 - self.ball["size"] / 2
        speed = 320.0
        self.ball["vx"] = speed * direction
        self.ball["vy"] = 120.0 * (-1 if direction < 0 else 1)
        self.ball["spin"] = 80.0 * direction
        self.ball["angle"] = 0.0

    def _score_point(self, scorer: str) -> None:
        if scorer == "left":
            self.left_score += 1
            direction = -1
        else:
            self.right_score += 1
            direction = 1
        self._emit(
            PointScored(
                scorer_id=scorer,
                left_score=self.left_score,
                right_score=self.right_score,
            )
        )
        self._center_ball(direction=direction)
        self._emit(RoundReset())

    def _handle_ability_input(self) -> None:
        app = getattr(self.manager, "app", None)
        if not app or not self.equipped_ability_id:
            return
        if app.input.consume(Action.BOOST):
            abilities = self.managers.get("abilities")
            if abilities:
                abilities.activate(self.equipped_ability_id)

    def _sync_equipped_ability(self) -> None:
        app = getattr(self.manager, "app", None)
        ability_id = getattr(app, "loadout", {}).get("ability") if app else None
        abilities = self.managers.get("abilities")
        if abilities and ability_id in abilities.registry:
            self.equipped_ability_id = ability_id
        elif abilities and abilities.registry:
            self.equipped_ability_id = next(iter(abilities.registry.keys()))
        else:
            self.equipped_ability_id = None

    def _current_ability(self):
        abilities = self.managers.get("abilities")
        if not abilities or not self.equipped_ability_id:
            return None
        return abilities.registry.get(self.equipped_ability_id)

    def _ability_name(self) -> str:
        ctx = self.manager.app_ctx if hasattr(self.manager, "app_ctx") else {}
        ability_id = self.equipped_ability_id
        if not ability_id:
            return "None"
        specs = ctx.get("ability_specs", {})
        if ability_id in specs:
            return specs[ability_id].name
        ability = self._current_ability()
        return ability.meta.get("name", ability_id) if ability else ability_id

    def _ability_status_text(self) -> str:
        ability = self._current_ability()
        if not ability:
            return "Unavailable"
        if getattr(ability, "active", False):
            return f"Active: {getattr(ability, 'time_left', 0.0):.1f}s"
        cooldown = float(getattr(ability, "cooldown_remaining", 0.0) or 0.0)
        if cooldown > 0.05:
            return f"Cooldown: {cooldown:.1f}s"
        return "Ready"

    def _publish_ability_ctx(self) -> None:
        if not hasattr(self.manager, "app_ctx"):
            return
        ability = self._current_ability()
        self.manager.app_ctx["equipped_ability_id"] = self.equipped_ability_id
        self.manager.app_ctx["equipped_ability_name"] = self._ability_name()
        self.manager.app_ctx["ability_cooldown_remaining"] = (
            float(getattr(ability, "cooldown_remaining", 0.0) or 0.0) if ability else 0.0
        )
        self.manager.app_ctx["ability_active_remaining"] = (
            float(getattr(ability, "time_left", 0.0) or 0.0) if ability and getattr(ability, "active", False) else 0.0
        )

    def _refresh_paddle_speed(self, paddle_id: str) -> None:
        paddle = self.paddles[paddle_id]
        paddle["speed"] = paddle["base_speed"] * paddle.get("speed_multiplier", 1.0)

    def set_left_speed_multiplier(self, multiplier: float) -> None:
        self.paddles["left"]["speed_multiplier"] = max(0.1, float(multiplier))
        self._refresh_paddle_speed("left")

    def resolve_dash_direction(self) -> int:
        if self.player_move_dir != 0:
            return self.player_move_dir
        if self.last_player_move_dir != 0:
            return self.last_player_move_dir
        paddle_center = self.paddles["left"]["y"] + self.paddles["left"]["h"] / 2
        return -1 if self.ball["y"] < paddle_center else 1

    def start_left_paddle_dash(self, direction: int, speed: float, duration: float) -> None:
        direction = -1 if direction < 0 else 1
        self.left_dash_velocity = direction * abs(speed)
        self.left_dash_time_left = max(0.0, duration)

    def stop_left_paddle_dash(self) -> None:
        self.left_dash_velocity = 0.0
        self.left_dash_time_left = 0.0

    def _orient_spin(self, dt: float) -> None:
        ball = self.ball
        vx, vy = ball.get("vx", 0.0), ball.get("vy", 0.0)
        speed = math.hypot(vx, vy)
        if speed < 1e-3:
            return
        sign_dir = -1 if vx > 0 else 1
        target = sign_dir * speed * 0.4
        spin = ball.get("spin", 0.0)
        spin += (target - spin) * min(1.0, dt * 6.0)
        spin *= 0.995
        ball["spin"] = max(-720.0, min(720.0, spin))


def _hex_to_rgb(hexstr: str) -> tuple[int, int, int]:
    hs = hexstr.lstrip("#")
    if len(hs) == 3:
        hs = "".join([c * 2 for c in hs])
    return tuple(int(hs[i : i + 2], 16) for i in (0, 2, 4))


def _offset_angle(vx: float, vy: float, deg: float) -> tuple[float, float]:
    speed = math.hypot(vx, vy)
    if speed == 0:
        return vx, vy
    angle = math.atan2(vy, vx) + math.radians(deg)
    return math.cos(angle) * speed, math.sin(angle) * speed
