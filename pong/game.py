"""Main game composition and loop."""

from __future__ import annotations

import random
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
        self._ball_seq = 0
        self._spawn_balls(self.settings.ball.count_on_reset)

    def _apply_display_settings(self) -> None:
        disp = self.settings.display
        self.screen = pygame.display.set_mode((disp.width, disp.height))
        pygame.display.set_caption(disp.title)

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

    def _on_spawn_request(self, event: SpawnBallRequested) -> None:
        self._spawn_balls(event.count, speed=event.speed, size=event.size)

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

    def _remove_ball(self, ball: Ball) -> None:
        if ball in self.balls:
            self.balls.remove(ball)
            self.bus.publish(BallRemoved(ball_id=ball.ball_id))

    def _on_point_scored(self, event: PointScored) -> None:
        self.score[event.scorer_id] += 1

    def _reset_round(self) -> None:
        pad_cfg = self.settings.paddle
        disp = self.settings.display
        self.left_paddle.y = (disp.height - pad_cfg.height) / 2
        self.right_paddle.y = (disp.height - pad_cfg.height) / 2
        self.balls.clear()
        self._spawn_balls(self.settings.ball.count_on_reset)
        self.bus.publish(RoundReset())

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
            self.powerups.update(dt)
            self.particles.update(dt)
            if keys[pygame.K_SPACE]:
                self.bus.publish(SpawnBallRequested(count=1))
        elif keys[pygame.K_r]:
            self._restart()

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
