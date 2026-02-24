from __future__ import annotations

import pygame
import logging

from .base import Scene, SceneManager
from pong.core.input import Action

logger = logging.getLogger(__name__)


class PlayScene(Scene):
    """Stub play scene with clear layer hooks (bg/world/ui)."""

    def __init__(self, manager: SceneManager, font, font_small) -> None:
        self.manager = manager
        self.font = font
        self.font_small = font_small
        self.time = 0.0
        self.ball = {
            "x": 200.0,
            "y": 140.0,
            "vx": 220.0,
            "vy": 140.0,
            "size": 22,
        }
        self.paddles = {
            "left": {"x": 40.0, "y": 160.0, "w": 14, "h": 80, "speed": 280.0},
            "right": {"x": 520.0, "y": 160.0, "w": 14, "h": 80, "speed": 280.0},
        }

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
        # Placeholder: oscillating circle to show world layer separation
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
            screen.blit(scaled_ball, brect)
        else:
            pygame.draw.ellipse(screen, accent, brect)

    def _draw_ui(self, screen: pygame.Surface) -> None:
        palette = self.manager.app_ctx.get("palette") if hasattr(self.manager, "app_ctx") else None
        fg = (240, 220, 180) if not palette else _hex_to_rgb(palette.foreground)
        title = self.font.render("Play Stub", True, fg)
        screen.blit(title, (40, 40))
        hint = self.font_small.render("[Esc/P] Pause", True, fg)
        screen.blit(hint, (40, 90))

    def _update_ball(self, dt: float) -> None:
        b = self.ball
        b["x"] += b["vx"] * dt
        b["y"] += b["vy"] * dt
        w, h = self.manager.app_ctx.get("play_area", (self.manager.scenes["play"].__dict__.get('screen_width', 640), 360)) if hasattr(self.manager, "app_ctx") else (640, 360)
        size = b["size"]
        if b["y"] <= 0:
            b["y"] = 0
            b["vy"] *= -1
        if b["y"] + size >= h:
            b["y"] = h - size
            b["vy"] *= -1
        # paddle collisions
        for key in ("left", "right"):
            p = self.paddles[key]
            rect = pygame.Rect(int(p["x"]), int(p["y"]), p["w"], p["h"])
            brect = pygame.Rect(int(b["x"]), int(b["y"]), size, size)
            if rect.colliderect(brect):
                b["vx"] *= -1
                # nudge
                if key == "left":
                    b["x"] = p["x"] + p["w"]
                else:
                    b["x"] = p["x"] - size
        # walls left/right -> bounce
        if b["x"] <= 0 or b["x"] + size >= w:
            b["vx"] *= -1

    def _update_paddles(self, dt: float) -> None:
        # simple follow ball AI for right; left player via keyboard
        input_state = self.manager.app.input if hasattr(self.manager, "app") else None
        if input_state and input_state.is_held(Action.UP):
            self.paddles["left"]["y"] -= self.paddles["left"]["speed"] * dt
        if input_state and input_state.is_held(Action.DOWN):
            self.paddles["left"]["y"] += self.paddles["left"]["speed"] * dt
        # clamp
        h = self.manager.app_ctx.get("play_area", (self.manager.scenes["play"].__dict__.get('screen_width', 640), 360))[1] if hasattr(self.manager, "app_ctx") else 360
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


def _hex_to_rgb(hexstr: str) -> tuple[int, int, int]:
    hs = hexstr.lstrip("#")
    if len(hs) == 3:
        hs = "".join([c * 2 for c in hs])
    return tuple(int(hs[i : i + 2], 16) for i in (0, 2, 4))
