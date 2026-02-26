from __future__ import annotations

import pygame
import logging
import math
import random

try:
    from .base import Scene, SceneManager
except ImportError:  # fallback when run as script
    from pong.scenes.base import Scene, SceneManager
from pong.core.input import Action
from pong.events import BallBouncePaddle, BallBounceWall, PointScored, RoundReset
from pong.effects.base import EffectContext
from pong.effects.manager import EffectManager

logger = logging.getLogger(__name__)


class PlayScene(Scene):
    """Stub play scene with clear layer hooks (bg/world/ui)."""

    def __init__(self, manager: SceneManager, font, font_small) -> None:
        self.manager = manager
        self.font = font
        self.font_small = font_small
        self.time = 0.0
        play_area = manager.app_ctx.get("play_area", (1280, 720)) if hasattr(manager, "app_ctx") else (1280, 720)
        self.width, self.height = play_area
        self.play_top = 64
        self.play_height = self.height - self.play_top
        self.play_bottom = self.play_top + self.play_height
        pad_w, pad_h = 14, 100
        margin = 32
        self.ball = {
            "x": self.width / 2 - 11,
            "y": self.play_top + self.play_height / 2 - 11,
            "vx": 320.0,
            "vy": 200.0,
            "size": 22,
            "angle": 0.0,
            "spin": 120.0,  # deg/sec
        }
        self.ball_id = "main"
        self.margin = margin
        self.pad_w = pad_w
        self.pad_h = pad_h
        self.paddles = {
            "left": {"x": margin, "y": self.play_top + (self.play_height - pad_h) / 2, "w": pad_w, "h": pad_h, "speed": 320.0},
            "right": {"x": self.width - margin - pad_w, "y": self.play_top + (self.play_height - pad_h) / 2, "w": pad_w, "h": pad_h, "speed": 320.0},
        }
        self.left_score = 0
        self.right_score = 0
        # effects
        self.managers = {}
        self._init_effects()
        self.equipped_boost_id: str | None = None

    def on_enter(self, payload=None) -> None:
        self.left_score = 0
        self.right_score = 0
        self._center_ball(direction=1)
        # select first boost, but do not activate yet
        boosts = self.managers.get("boosts")
        if boosts and boosts.registry:
            self.equipped_boost_id = next(iter(boosts.registry.keys()))

    # Event handling ----------------------------------------------------- #
    def handle_event(self, event: pygame.event.Event) -> None:
        # ESC/P handled globally in app loop
        return

    # Simulation --------------------------------------------------------- #
    def update(self, dt: float) -> None:
        self.time += dt
        for m in self.managers.values():
            m.on_tick(dt)
        self._update_ball(dt)
        self._update_paddles(dt)
        self._handle_boost_input()

    # Rendering layers --------------------------------------------------- #
    def draw(self, screen: pygame.Surface) -> None:
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
        # mask play area so bar is distinct (optional darken)
        play_rect = pygame.Rect(0, self.play_top, self.width, self.play_height)
        mask = pygame.Surface((self.width, self.play_height), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 40))
        screen.blit(mask, play_rect.topleft)

    def _draw_world(self, screen: pygame.Surface) -> None:
        ctx = self.manager.app_ctx if hasattr(self.manager, "app_ctx") else {}
        palette = ctx.get("palette")
        accent = (90, 140, 255) if not palette else _hex_to_rgb(palette.accent)

        # paddles
        ball_img = ctx.get("ball_image")
        paddle_img = ctx.get("paddle_image")
        for key in ("left", "right"):
            p = self.paddles[key]
            rect = pygame.Rect(int(p["x"]), int(p["y"]), p["w"], p["h"])
            if paddle_img:
                scaled = pygame.transform.smoothscale(paddle_img, rect.size)
                screen.blit(scaled, rect)
            else:
                pygame.draw.rect(screen, accent, rect, border_radius=4)

        # ball
        b = self.ball
        brect = pygame.Rect(int(b["x"]), int(b["y"]), b["size"], b["size"])
        if ball_img:
            scaled_ball = pygame.transform.smoothscale(ball_img, brect.size)
            rotated = pygame.transform.rotate(scaled_ball, b.get("angle", 0.0))
            rrect = rotated.get_rect(center=brect.center)
            screen.blit(rotated, rrect)
        else:
            pygame.draw.ellipse(screen, accent, brect)

    def _draw_ui(self, screen: pygame.Surface) -> None:
        palette = self.manager.app_ctx.get("palette") if hasattr(self.manager, "app_ctx") else None
        fg = (240, 220, 180) if not palette else _hex_to_rgb(palette.foreground)
        accent = (120, 180, 255) if not palette else _hex_to_rgb(palette.accent)
        # top bar background
        bar_height = 64
        pygame.draw.rect(screen, (20, 24, 32), pygame.Rect(0, 0, screen.get_width(), bar_height))
        pygame.draw.line(screen, accent, (0, bar_height), (screen.get_width(), bar_height), width=2)
        # scores centered
        score_txt = f"{self.left_score}   |   {self.right_score}"
        score = self.font.render(score_txt, True, fg)
        screen.blit(score, (screen.get_width() // 2 - score.get_width() // 2, 14))
        # equipped boost
        boost_label = "Boost: "
        if self.equipped_boost_id:
            boost_label += self.equipped_boost_id
        else:
            boost_label += "None"
        boost_txt = self.font_small.render(boost_label, True, accent)
        screen.blit(boost_txt, (40, 20))
        hint = self.font_small.render("[Esc/P] Pause   [Space] Boost", True, fg)
        screen.blit(hint, (screen.get_width() - hint.get_width() - 40, 20))

    def _draw_effect_overlays(self, screen: pygame.Surface) -> None:
        boosts = self.managers.get("boosts")
        if not boosts:
            return
        for eff in boosts.active.values():
            draw = getattr(eff, "draw_overlay", None)
            if draw:
                try:
                    draw(EffectContext(app=self.manager.app, play_scene=self, bus=self.manager.app.bus, logger=logger, rng=random.Random()), screen)
                except Exception:
                    logger.exception("Effect overlay draw failed", extra={"id": getattr(eff, 'id', '?')})

    def _active_shield(self):
        boosts = self.managers.get("boosts")
        if not boosts:
            return None
        for eff in boosts.active.values():
            if getattr(eff, "active", False) and getattr(eff, "id", "") == "shield_once":
                return eff
        return None

    def _update_ball(self, dt: float) -> None:
        b = self.ball
        b["x"] += b["vx"] * dt
        b["y"] += b["vy"] * dt
        w, h = self.width, self.height
        size = b["size"]
        top = self.play_top
        bottom = self.play_bottom
        if b["y"] <= top:
            b["y"] = top
            b["vy"] *= -1
            b["vx"], b["vy"] = _offset_angle(b["vx"], b["vy"], 8.0 if b["vx"] >= 0 else -8.0)
            b["spin"] *= 0.9
            b["spin"] *= -1  # flip spin on vertical wall bounce
            ang = math.degrees(math.atan2(b["vy"], b["vx"]))
            self._emit(
                BallBounceWall(
                    ball_id=self.ball_id,
                    wall="top",
                    speed=math.hypot(b["vx"], b["vy"]),
                    spin=b["spin"],
                    vx=b["vx"],
                    vy=b["vy"],
                    angle_deg=ang,
                )
            )
        if b["y"] + size >= bottom:
            b["y"] = bottom - size
            b["vy"] *= -1
            b["vx"], b["vy"] = _offset_angle(b["vx"], b["vy"], -8.0 if b["vx"] >= 0 else 8.0)
            b["spin"] *= 0.9
            b["spin"] *= -1  # flip spin on vertical wall bounce
            ang = math.degrees(math.atan2(b["vy"], b["vx"]))
            self._emit(
                BallBounceWall(
                    ball_id=self.ball_id,
                    wall="bottom",
                    speed=math.hypot(b["vx"], b["vy"]),
                    spin=b["spin"],
                    vx=b["vx"],
                    vy=b["vy"],
                    angle_deg=ang,
                )
            )
        # paddle collisions
        for key in ("left", "right"):
            p = self.paddles[key]
            rect = pygame.Rect(int(p["x"]), int(p["y"]), p["w"], p["h"])
            brect = pygame.Rect(int(b["x"]), int(b["y"]), size, size)
            if rect.colliderect(brect):
                hit_pos = (brect.centery - rect.centery) / (p["h"] / 2)
                hit_pos = max(-1.0, min(1.0, hit_pos))
                speed = max(320.0, (abs(b["vx"]) + abs(b["vy"])) * 0.55)
                dir_x = 1 if key == "left" else -1
                new_vx = dir_x * speed
                new_vy = hit_pos * speed * 0.75
                # keep total speed consistent
                mag = (new_vx ** 2 + new_vy ** 2) ** 0.5
                target = max(340.0, mag)
                new_vx = new_vx / mag * target
                new_vy = new_vy / mag * target
                # apply fixed deflection so bounce isn't perfectly mirrored
                deflect = 10.0
                if hit_pos < 0:
                    deflect = -deflect
                b["vx"], b["vy"] = _offset_angle(new_vx, new_vy, deflect)
                b["spin"] = hit_pos * 720.0
                # nudge out of paddle to avoid sticking
                if key == "left":
                    b["x"] = p["x"] + p["w"]
                else:
                    b["x"] = p["x"] - size
                angle_deg = math.degrees(math.atan2(b["vy"], b["vx"]))
                self._emit(
                    BallBouncePaddle(
                        ball_id=self.ball_id,
                        paddle_id=key,
                        hit_pos=hit_pos,
                        speed=target,
                        spin=b["spin"],
                        vx=b["vx"],
                        vy=b["vy"],
                        angle_deg=angle_deg,
                    )
                )
        # shield check (left side)
        shield = self._active_shield()
        if shield and b["x"] <= self.margin:
            b["x"] = self.margin
            b["vx"] = abs(b["vx"])  # bounce right
            b["vy"] *= 0.9
            b["spin"] *= 0.7
            return

        # out of bounds -> score
        if b["x"] + size < 0:
            self._score_point("right")
            return
        if b["x"] > w:
            self._score_point("left")
            return
        # orient spin to flight direction
        self._orient_spin(dt)
        b["angle"] = (b.get("angle", 0.0) + b.get("spin", 0.0) * dt) % 360

    def _update_paddles(self, dt: float) -> None:
        # simple follow ball AI for right; left player via keyboard
        input_state = self.manager.app.input if hasattr(self.manager, "app") else None
        if input_state and input_state.is_held(Action.UP):
            self.paddles["left"]["y"] -= self.paddles["left"]["speed"] * dt
        if input_state and input_state.is_held(Action.DOWN):
            self.paddles["left"]["y"] += self.paddles["left"]["speed"] * dt
        # clamp
        top = self.play_top
        bottom = self.play_bottom
        for key in ("left", "right"):
            p = self.paddles[key]
            p["y"] = max(top, min(bottom - p["h"], p["y"]))
        # simple AI right
        b = self.ball
        target = b["y"] - self.paddles["right"]["h"] / 2
        if b["vx"] > 0:
            if self.paddles["right"]["y"] + self.paddles["right"]["h"] / 2 < target:
                self.paddles["right"]["y"] += self.paddles["right"]["speed"] * dt
            elif self.paddles["right"]["y"] > target:
                self.paddles["right"]["y"] -= self.paddles["right"]["speed"] * dt

    def on_event(self, event) -> None:
        from pong.events import ResolutionChanged
        if isinstance(event, ResolutionChanged):
            return  # resolution fixed; ignore
        for m in self.managers.values():
            m.on_event(event)

    def _emit(self, event) -> None:
        app = getattr(self.manager, "app", None)
        if app and hasattr(app, "bus"):
            app.bus.publish(event)

    # Effects ----------------------------------------------------------- #
    def _init_effects(self) -> None:
        app = getattr(self.manager, "app", None)
        if not app:
            return
        ctx = EffectContext(app=app, play_scene=self, bus=app.bus, logger=logger, rng=random.Random())
        self.managers = {
            "modifiers": EffectManager("modifiers", ["pong/effects/modifiers"], ctx),
            "chaos": EffectManager("chaos", ["pong/effects/chaos"], ctx),
            "boosts": EffectManager("boosts", ["pong/effects/boosts"], ctx),
        }

    def _center_ball(self, direction: int = 1) -> None:
        """Place ball in center; direction 1 -> to right, -1 -> to left."""
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

    def _handle_boost_input(self) -> None:
        app = getattr(self.manager, "app", None)
        if not app:
            return
        if app.input.consume(Action.BOOST):
            boosts = self.managers.get("boosts")
            if boosts and self.equipped_boost_id:
                boosts.activate(self.equipped_boost_id)
            elif boosts and boosts.registry:
                self.equipped_boost_id = next(iter(boosts.registry.keys()))
                boosts.activate(self.equipped_boost_id)

    def _orient_spin(self, dt: float) -> None:
        """Smoothly steer spin toward direction-derived target with damping."""
        b = self.ball
        vx, vy = b.get("vx", 0.0), b.get("vy", 0.0)
        speed = math.hypot(vx, vy)
        if speed < 1e-3:
            return
        # base: clockwise when moving right, counter-clockwise when moving left
        sign_dir = -1 if vx > 0 else 1
        target = sign_dir * speed * 0.4  # k factor
        # add paddle-induced bias captured via current spin magnitude
        # smoothly approach target
        spin = b.get("spin", 0.0)
        spin += (target - spin) * min(1.0, dt * 6.0)
        # damping
        spin *= 0.995
        # clamp
        spin = max(-720.0, min(720.0, spin))
        b["spin"] = spin


def _hex_to_rgb(hexstr: str) -> tuple[int, int, int]:
    hs = hexstr.lstrip("#")
    if len(hs) == 3:
        hs = "".join([c * 2 for c in hs])
    return tuple(int(hs[i : i + 2], 16) for i in (0, 2, 4))


def _offset_angle(vx: float, vy: float, deg: float) -> tuple[float, float]:
    """Rotate velocity vector by deg while preserving speed."""
    speed = math.hypot(vx, vy)
    if speed == 0:
        return vx, vy
    ang = math.atan2(vy, vx)
    ang += math.radians(deg)
    return math.cos(ang) * speed, math.sin(ang) * speed
