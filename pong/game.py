"""Main game composition and loop."""

from __future__ import annotations

import random
import logging
import math
import pygame

from pong.entities import Ball, Paddle
from pong.events import (
    BallHitPaddle,
    BallRemoved,
    BallSpawned,
    EventBus,
    PointScored,
    RoundReset,
    SettingsChanged,
    SettingsChangeRequested,
    SpawnBallRequested,
)
from pong.particles import ParticleSystem
from pong.powerups import PowerupManager
from pong.settings import RuntimeSettings
from pong.systems import ChaosSystem
from pong.skins import SkinManager

logger = logging.getLogger(__name__)

BG = (15, 20, 32)
FG = (230, 230, 230)
MID = (120, 125, 145)


class PongGame:
    def __init__(
        self,
        bus: EventBus | None = None,
        settings: RuntimeSettings | None = None,
        screen: pygame.Surface | None = None,
        bot_mode: str | None = None,
    ) -> None:
        pygame.init()
        pygame.font.init()

        self.bus = bus or EventBus()
        self.settings = settings or RuntimeSettings()

        self.screen: pygame.Surface | None = screen
        self.clock = pygame.time.Clock()
        self.running = True
        self.bot_mode = bot_mode

        self.bus.subscribe(PointScored, self._on_point_scored)
        self.bus.subscribe(SettingsChangeRequested, self._on_settings_change_requested)
        self.bus.subscribe(SpawnBallRequested, self._on_spawn_request)

        if self.screen is None:
            self._apply_display_settings()
        self.skins = SkinManager(self.bus, self.settings)
        self.particles = ParticleSystem(self.settings)

        pad_cfg = self.settings.paddle
        disp = self.settings.display
        self.left_paddle = Paddle(
            paddle_id="left",
            x=pad_cfg.margin_x,
            y=(disp.height - pad_cfg.height) / 2,
            up_key=pygame.K_w,
            down_key=pygame.K_s,
            settings=self.settings,
        )
        self.right_paddle = Paddle(
            paddle_id="right",
            x=disp.width - pad_cfg.margin_x - pad_cfg.width,
            y=(disp.height - pad_cfg.height) / 2,
            up_key=pygame.K_UP,
            down_key=pygame.K_DOWN,
            settings=self.settings,
        )

        self.score = {"left": 0, "right": 0}

        self.font_ui = pygame.font.SysFont("consolas", 28)
        self.font_big = pygame.font.SysFont("consolas", 42, bold=True)

        self.powerups = PowerupManager.with_default_template(self.bus, self.left_paddle, self.right_paddle)
        self.chaos_system = ChaosSystem(self.bus, self.settings)

        self.balls: list[Ball] = []
        self.trails: dict[str, list[tuple[float, float]]] = {}
        self.trail_particles: dict[str, list[dict]] = {}
        self.trail_active: dict[str, bool] = {}
        self._ball_seq = 0
        self._time = 0.0
        self._spawn_balls(self.settings.ball.count_on_reset)

    def _apply_display_settings(self) -> None:
        disp = self.settings.display
        self.screen = pygame.display.set_mode((disp.width, disp.height))
        pygame.display.set_caption(disp.title)
        logger.info("Display applied", extra={"width": disp.width, "height": disp.height})

    def _ai_keys(self):
        class _Keys:
            def __init__(self, up: bool, down: bool) -> None:
                self.up = up
                self.down = down

            def __getitem__(self, key: int) -> bool:
                if key == pygame.K_UP:
                    return self.up
                if key == pygame.K_DOWN:
                    return self.down
                return False

        factor = {
            "easy": 0.7,
            "medium": 1.0,
            "hard": 1.15,
            "ai": 1.25,
        }.get(self.bot_mode, 1.0)
        self.right_paddle.speed_multiplier = factor

        if not self.balls:
            return _Keys(False, False)
        # choose nearest ball in x distance
        paddle_center = self.right_paddle.y + self.settings.paddle.height / 2
        target_ball = min(self.balls, key=lambda b: abs(b.x - self.right_paddle.x))
        target_y = target_ball.y + self.settings.ball.size / 2
        margin = 6
        if abs(target_y - paddle_center) <= margin:
            return _Keys(False, False)
        return _Keys(target_y < paddle_center, target_y > paddle_center)

    def _on_settings_change_requested(self, event: SettingsChangeRequested) -> None:
        applied = self.settings.patch(event.section, **event.values)
        if event.section == "display":
            self._apply_display_settings()
        self.bus.publish(SettingsChanged(section=event.section, values=applied))
        logger.info("Settings change requested", extra={"section": event.section, "applied": applied})

    def _on_spawn_request(self, event: SpawnBallRequested) -> None:
        self._spawn_balls(event.count, speed=event.speed, size=event.size)
        logger.info("Spawn request", extra={"count": event.count, "speed": event.speed, "size": event.size})

    def _spawn_balls(self, count: int = 1, speed: float | None = None, size: int | None = None) -> None:
        cfg_ball = self.settings.ball
        disp = self.settings.display
        for _ in range(count):
            self._ball_seq += 1
            direction = random.choice([-1, 1])
            use_speed = speed if speed is not None else cfg_ball.speed
            use_size = size if size is not None else cfg_ball.size
            ball = Ball(
                ball_id=f"ball-{self._ball_seq}",
                x=(disp.width - use_size) / 2,
                y=(disp.height - use_size) / 2,
                velocity_x=use_speed * direction,
                velocity_y=use_speed * 0.33 * direction,
                settings=self.settings,
            )
            self.balls.append(ball)
            self.bus.publish(BallSpawned(ball_id=ball.ball_id))
            logger.debug("Ball spawned", extra={"ball_id": ball.ball_id, "speed": use_speed, "size": use_size})
            self.trails[ball.ball_id] = []
            self.trail_particles[ball.ball_id] = []
            self.trail_active[ball.ball_id] = False

    def _remove_ball(self, ball: Ball) -> None:
        if ball in self.balls:
            self.balls.remove(ball)
            self.bus.publish(BallRemoved(ball_id=ball.ball_id))
            logger.debug("Ball removed", extra={"ball_id": ball.ball_id, "remaining": len(self.balls)})
            self.trails.pop(ball.ball_id, None)
            self.trail_particles.pop(ball.ball_id, None)
            self.trail_active.pop(ball.ball_id, None)

    def _update_trails(self) -> None:
        effect = self.settings.trail.effect
        if effect == "trail_none":
            return
        for ball in self.balls:
            if not self.trail_active.get(ball.ball_id, False):
                continue
            speed = math.hypot(ball.velocity_x, ball.velocity_y)
            max_len = int(max(12, min(40, speed / 12)))
            trail = self.trails.setdefault(ball.ball_id, [])
            trail.insert(0, (ball.x, ball.y))
            if len(trail) > max_len:
                trail.pop()
            self._spawn_trail_particles(ball, speed)
        # update particles
        for ball_id, plist in self.trail_particles.items():
            for p in list(plist):
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["vy"] += 20 * 0.016  # light gravity
                p["life"] -= 0.016
                p["alpha"] = max(0, p["alpha"] - 8)
                if p["life"] <= 0:
                    plist.remove(p)

    def _spawn_trail_particles(self, ball: Ball, speed: float) -> None:
        effect = self.settings.trail.effect
        if effect == "trail_none":
            return
        plist = self.trail_particles.setdefault(ball.ball_id, [])
        spawn_count = 2 if speed < 250 else 4
        for _ in range(spawn_count):
            col = self._trail_color()
            size = random.uniform(3, 8)
            life = random.uniform(0.25, 0.6)
            vx = random.uniform(-40, 40) * 0.016
            vy = random.uniform(-30, 10) * 0.016
            if effect == "trail_fire":
                col = (255, random.randint(100, 160), random.randint(40, 90))
                vy -= 0.1
            elif effect == "trail_neon":
                col = (random.randint(60, 120), random.randint(180, 255), 255)
            elif effect == "trail_spark":
                col = (255, 230, random.randint(140, 200))
                size = random.uniform(2, 5)
                vx *= 2
            elif effect == "trail_pixel":
                col = (180, 180, 255)
                size = random.uniform(2, 4)
                vx = 0
                vy = 0
            elif effect == "trail_rainbow":
                col = self._rainbow_color(self._time + random.random())
            elif effect == "trail_smoke":
                col = (160, 160, 160)
                vy = -abs(vy) * 0.5
            particle = {
                "x": ball.x,
                "y": ball.y,
                "vx": vx,
                "vy": vy,
                "life": life,
                "alpha": 255,
                "size": size,
                "color": col,
            }
            plist.append(particle)

    def _trail_color(self) -> tuple[int, int, int]:
        match self.settings.trail.effect:
            case "trail_fire":
                return (255, 140, 80)
            case "trail_neon":
                return (80, 200, 255)
            case "trail_spark":
                return (255, 230, 160)
            case "trail_pixel":
                return (180, 180, 255)
            case "trail_rainbow":
                return self._rainbow_color(self._time)
            case "trail_smoke":
                return (170, 170, 170)
            case _:
                return (200, 200, 200)

    def _rainbow_color(self, t: float) -> tuple[int, int, int]:
        import math

        freq = 1.6
        r = int(127 * math.sin(freq * t) + 128)
        g = int(127 * math.sin(freq * t + 2) + 128)
        b = int(127 * math.sin(freq * t + 4) + 128)
        return (r, g, b)

    def _draw_trail_for_ball(self, ball: Ball) -> None:
        effect = self.settings.trail.effect
        if effect == "trail_none":
            return
        points = self.trails.get(ball.ball_id, [])
        for i, (x, y) in enumerate(points):
            alpha = max(20, 255 - i * 20)
            size = max(3, self.settings.ball.size // 2 - i // 2)
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            if effect == "trail_fire":
                col = (255, 140 - i * 4, 60)
                pygame.draw.circle(surf, (*col, alpha), (size, size), size)
            elif effect == "trail_neon":
                glow = (80, 200, 255, alpha)
                pygame.draw.circle(surf, glow, (size, size), size)
                pygame.draw.circle(surf, (255, 255, 255, alpha), (size, size), max(1, size // 2))
            elif effect == "trail_spark":
                col = (255, 230, 160, alpha)
                pygame.draw.line(surf, col, (0, size), (size * 2, size), width=2)
                pygame.draw.line(surf, col, (size, 0), (size, size * 2), width=2)
            elif effect == "trail_pixel":
                col = (180, 180, 255, alpha)
                pygame.draw.rect(surf, col, pygame.Rect(size // 2, size // 2, size, size))
            elif effect == "trail_rainbow":
                col = (*self._rainbow_color(self._time + i * 0.05), alpha)
                pygame.draw.circle(surf, col, (size, size), size)
            elif effect == "trail_smoke":
                col = (160, 160, 160, alpha)
                pygame.draw.circle(surf, col, (size, size), size)
            else:
                col = (*self._trail_color(), alpha)
                pygame.draw.circle(surf, col, (size, size), size)
            self.screen.blit(surf, (x - size, y - size))
        # draw particles on top
        for p in list(self.trail_particles.get(ball.ball_id, [])):
            size = max(2, int(p["size"]))
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            color = (*p["color"][:3], int(p["alpha"]))
            pygame.draw.circle(surf, color, (size, size), size)
            self.screen.blit(surf, (p["x"] - size, p["y"] - size))

    def _on_point_scored(self, event: PointScored) -> None:
        self.score[event.scorer_id] += 1
        logger.info("Point scored", extra={"scorer": event.scorer_id, "score": self.score})

    def _reset_round(self) -> None:
        pad_cfg = self.settings.paddle
        disp = self.settings.display
        self.left_paddle.y = (disp.height - pad_cfg.height) / 2
        self.right_paddle.y = (disp.height - pad_cfg.height) / 2
        self.balls.clear()
        self._spawn_balls(self.settings.ball.count_on_reset)
        self.bus.publish(RoundReset())
        logger.debug("Round reset", extra={"score": self.score})
        self.trails.clear()
        self.trail_particles.clear()
        self.trail_active.clear()

    def _handle_collisions(self) -> None:
        disp = self.settings.display
        for ball in list(self.balls):
            ball_size = ball.rect.width
            if ball.y <= 0 and ball.velocity_y < 0:
                ball.y = 0
                ball.bounce_vertical()
            elif ball.y + ball_size >= disp.height and ball.velocity_y > 0:
                ball.y = disp.height - ball_size
                ball.bounce_vertical()

            for paddle in (self.left_paddle, self.right_paddle):
                if ball.rect.colliderect(paddle.rect):
                    ball.bounce_from_paddle(paddle)
                    self.trail_active[ball.ball_id] = True
                    self.bus.publish(BallHitPaddle(paddle_id=paddle.paddle_id))
                    self.particles.spawn_burst(
                        ball.x + ball_size / 2, ball.y + ball_size / 2, color=ball.color, amount=10
                    )

            if ball.x < -ball_size:
                self.particles.spawn_burst(0, ball.y + ball_size / 2, color=ball.color, amount=16)
                self.bus.publish(PointScored(scorer_id="right"))
                self._remove_ball(ball)
            elif ball.x > disp.width + ball_size:
                self.particles.spawn_burst(disp.width, ball.y + ball_size / 2, color=ball.color, amount=16)
                self.bus.publish(PointScored(scorer_id="left"))
                self._remove_ball(ball)

        if not self.balls and max(self.score.values()) < self.settings.match.win_score:
            self._reset_round()

    def _draw_ui(self) -> None:
        disp = self.settings.display
        pygame.draw.line(self.screen, MID, (disp.width // 2, 0), (disp.width // 2, disp.height), 2)

        left_score = self.font_big.render(str(self.score["left"]), True, FG)
        right_score = self.font_big.render(str(self.score["right"]), True, FG)
        self.screen.blit(left_score, (disp.width // 2 - 70, 24))
        self.screen.blit(right_score, (disp.width // 2 + 40, 24))

        hint = self.font_ui.render("W/S vs Pfeiltasten | [Space] Ball+", True, MID)
        self.screen.blit(hint, (disp.width // 2 - hint.get_width() // 2, disp.height - 40))

        if max(self.score.values()) >= self.settings.match.win_score:
            winner = "Links" if self.score["left"] > self.score["right"] else "Rechts"
            msg = self.font_big.render(f"{winner} gewinnt! [R] Restart", True, (255, 190, 110))
            self.screen.blit(msg, (disp.width // 2 - msg.get_width() // 2, disp.height // 2 - 24))

    def _restart(self) -> None:
        self.score = {"left": 0, "right": 0}
        self._reset_round()

    def update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        if max(self.score.values()) < self.settings.match.win_score:
            self.left_paddle.update(dt, keys)
            if self.bot_mode:
                ai_keys = self._ai_keys()
                self.right_paddle.update(dt, ai_keys)
            else:
                self.right_paddle.update(dt, keys)
            for ball in self.balls:
                ball.rotation_angle = (ball.rotation_angle + self.settings.sprites.ball_rotation_speed * dt) % 360
                ball.update(dt)
            self.chaos_system.update(dt)
            self._handle_collisions()
            self._update_trails()
            self.powerups.update(dt)
            self.particles.update(dt)
            if keys[pygame.K_SPACE]:
                self.bus.publish(SpawnBallRequested(count=1))
        elif keys[pygame.K_r]:
            self._restart()
        self._time += dt

    def draw(self) -> None:
        if not self.skins.draw_background(self.screen):
            self.screen.fill(BG)

        if not self.skins.draw_paddle(self.left_paddle, self.screen):
            self.left_paddle.draw(self.screen)
        if not self.skins.draw_paddle(self.right_paddle, self.screen):
            self.right_paddle.draw(self.screen)

        for ball in self.balls:
            if not self.skins.draw_ball(ball, self.screen):
                ball.draw(self.screen)
            self._draw_trail_for_ball(ball)

        self.particles.draw(self.screen)
        self.powerups.draw(self.screen)
        self._draw_ui()

    def run(self) -> None:
        disp = self.settings.display
        while self.running:
            dt = self.clock.tick(disp.fps) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            self.update(dt)
            self.draw()
            pygame.display.flip()

        pygame.quit()


def run() -> None:
    PongGame().run()
