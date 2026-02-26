from __future__ import annotations

import pygame
import logging
import math

try:
    from .base import Scene, SceneManager
except ImportError:  # fallback when run as script
    from pong.scenes.base import Scene, SceneManager
from pong.core.input import Action
from pong.events import BallBouncePaddle, BallBounceWall, PointScored, RoundReset

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
        pad_w, pad_h = 14, 100
        margin = 32
        self.ball = {
            "x": self.width / 2 - 11,
            "y": self.height / 2 - 11,
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
            "left": {"x": margin, "y": (self.height - pad_h) / 2, "w": pad_w, "h": pad_h, "speed": 320.0},
            "right": {"x": self.width - margin - pad_w, "y": (self.height - pad_h) / 2, "w": pad_w, "h": pad_h, "speed": 320.0},
        }
        self.left_score = 0
        self.right_score = 0

    def on_enter(self, payload=None) -> None:
        self.left_score = 0
        self.right_score = 0
        self._center_ball(direction=1)

    # Event handling ----------------------------------------------------- #
    def handle_event(self, event: pygame.event.Event) -> None:
        # ESC/P handled globally in app loop
        return

    # Simulation --------------------------------------------------------- #
    def update(self, dt: float) -> None:
        self.time += dt
        self._update_ball(dt)
        self._update_paddles(dt)

    # Rendering layers --------------------------------------------------- #
    def draw(self, screen: pygame.Surface) -> None:
        self._draw_background(screen)
        self._draw_world(screen)
        self._draw_ui(screen)

    def _draw_background(self, screen: pygame.Surface) -> None:
        ctx = self.manager.app_ctx if hasattr(self.manager, "app_ctx") else {}
        palette = ctx.get("palette")
        bg_image = ctx.get("bg_image")
        if bg_image:
            screen.blit(bg_image, (0, 0))
        else:
            bg = (12, 16, 26) if not palette else _hex_to_rgb(palette.background)
            screen.fill(bg)

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
        # scores centered
        score_txt = f"{self.left_score}   |   {self.right_score}"
        score = self.font.render(score_txt, True, fg)
        screen.blit(score, (screen.get_width() // 2 - score.get_width() // 2, 26))
        hint = self.font_small.render("[Esc/P] Pause", True, accent)
        screen.blit(hint, (40, 30))

    def _update_ball(self, dt: float) -> None:
        b = self.ball
        b["x"] += b["vx"] * dt
        b["y"] += b["vy"] * dt
        b["angle"] = (b.get("angle", 0.0) + b.get("spin", 0.0) * dt) % 360
        w, h = self.width, self.height
        size = b["size"]
        if b["y"] <= 0:
            b["y"] = 0
            b["vy"] *= -1
            b["vx"], b["vy"] = _offset_angle(b["vx"], b["vy"], 8.0 if b["vx"] >= 0 else -8.0)
            b["spin"] *= 0.9
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
        if b["y"] + size >= h:
            b["y"] = h - size
            b["vy"] *= -1
            b["vx"], b["vy"] = _offset_angle(b["vx"], b["vy"], -8.0 if b["vx"] >= 0 else 8.0)
            b["spin"] *= 0.9
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
        # out of bounds -> score
        if b["x"] + size < 0:
            self._score_point("right")
            return
        if b["x"] > w:
            self._score_point("left")
            return

    def _update_paddles(self, dt: float) -> None:
        # simple follow ball AI for right; left player via keyboard
        input_state = self.manager.app.input if hasattr(self.manager, "app") else None
        if input_state and input_state.is_held(Action.UP):
            self.paddles["left"]["y"] -= self.paddles["left"]["speed"] * dt
        if input_state and input_state.is_held(Action.DOWN):
            self.paddles["left"]["y"] += self.paddles["left"]["speed"] * dt
        # clamp
        h = self.height
        for key in ("left", "right"):
            p = self.paddles[key]
            p["y"] = max(0, min(h - p["h"], p["y"]))
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

    def _emit(self, event) -> None:
        app = getattr(self.manager, "app", None)
        if app and hasattr(app, "bus"):
            app.bus.publish(event)

    def _center_ball(self, direction: int = 1) -> None:
        """Place ball in center; direction 1 -> to right, -1 -> to left."""
        self.ball["x"] = self.width / 2 - self.ball["size"] / 2
        self.ball["y"] = self.height / 2 - self.ball["size"] / 2
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
