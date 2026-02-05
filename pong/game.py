"""Main game composition and loop."""

from __future__ import annotations

import pygame

from pong.config import BALL, DISPLAY, MATCH, PADDLE
from pong.entities import Ball, Paddle
from pong.events import BallHitPaddle, EventBus, PointScored, RoundReset
from pong.powerups import PowerupManager

BG = (15, 20, 32)
FG = (230, 230, 230)
MID = (120, 125, 145)


class PongGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((DISPLAY.width, DISPLAY.height))
        pygame.display.set_caption(DISPLAY.title)
        self.clock = pygame.time.Clock()
        self.running = True

        self.bus = EventBus()

        self.left_paddle = Paddle(
            paddle_id="left",
            x=PADDLE.margin_x,
            y=(DISPLAY.height - PADDLE.height) / 2,
            up_key=pygame.K_w,
            down_key=pygame.K_s,
        )
        self.right_paddle = Paddle(
            paddle_id="right",
            x=DISPLAY.width - PADDLE.margin_x - PADDLE.width,
            y=(DISPLAY.height - PADDLE.height) / 2,
            up_key=pygame.K_UP,
            down_key=pygame.K_DOWN,
        )
        self.ball = Ball(
            x=(DISPLAY.width - BALL.size) / 2,
            y=(DISPLAY.height - BALL.size) / 2,
            velocity_x=BALL.speed,
            velocity_y=BALL.speed * 0.33,
        )

        self.score = {"left": 0, "right": 0}

        self.font_ui = pygame.font.SysFont("consolas", 28)
        self.font_big = pygame.font.SysFont("consolas", 42, bold=True)

        self.powerups = PowerupManager.with_default_template(self.bus, self.left_paddle, self.right_paddle)

        self.bus.subscribe(PointScored, self._on_point_scored)

    def _on_point_scored(self, event: PointScored) -> None:
        self.score[event.scorer_id] += 1
        self._reset_round()

    def _reset_round(self) -> None:
        self.left_paddle.y = (DISPLAY.height - PADDLE.height) / 2
        self.right_paddle.y = (DISPLAY.height - PADDLE.height) / 2
        direction = -1 if self.score["left"] > self.score["right"] else 1
        self.ball.x = (DISPLAY.width - BALL.size) / 2
        self.ball.y = (DISPLAY.height - BALL.size) / 2
        self.ball.velocity_x = BALL.speed * direction
        self.ball.velocity_y = BALL.speed * 0.33 * direction
        self.bus.publish(RoundReset())

    def _handle_collisions(self) -> None:
        if self.ball.y <= 0 and self.ball.velocity_y < 0:
            self.ball.y = 0
            self.ball.bounce_vertical()
        elif self.ball.y + BALL.size >= DISPLAY.height and self.ball.velocity_y > 0:
            self.ball.y = DISPLAY.height - BALL.size
            self.ball.bounce_vertical()

        for paddle in (self.left_paddle, self.right_paddle):
            if self.ball.rect.colliderect(paddle.rect):
                self.ball.bounce_from_paddle(paddle)
                self.bus.publish(BallHitPaddle(paddle_id=paddle.paddle_id))

        if self.ball.x < -BALL.size:
            self.bus.publish(PointScored(scorer_id="right"))
        elif self.ball.x > DISPLAY.width + BALL.size:
            self.bus.publish(PointScored(scorer_id="left"))

    def _draw_ui(self) -> None:
        pygame.draw.line(self.screen, MID, (DISPLAY.width // 2, 0), (DISPLAY.width // 2, DISPLAY.height), 2)

        left_score = self.font_big.render(str(self.score["left"]), True, FG)
        right_score = self.font_big.render(str(self.score["right"]), True, FG)
        self.screen.blit(left_score, (DISPLAY.width // 2 - 70, 24))
        self.screen.blit(right_score, (DISPLAY.width // 2 + 40, 24))

        hint = self.font_ui.render("W/S vs Pfeiltasten", True, MID)
        self.screen.blit(hint, (DISPLAY.width // 2 - hint.get_width() // 2, DISPLAY.height - 40))

        if max(self.score.values()) >= MATCH.win_score:
            winner = "Links" if self.score["left"] > self.score["right"] else "Rechts"
            msg = self.font_big.render(f"{winner} gewinnt! [R] Restart", True, (255, 190, 110))
            self.screen.blit(msg, (DISPLAY.width // 2 - msg.get_width() // 2, DISPLAY.height // 2 - 24))

    def _restart(self) -> None:
        self.score = {"left": 0, "right": 0}
        self._reset_round()

    def update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        if max(self.score.values()) < MATCH.win_score:
            self.left_paddle.update(dt, keys)
            self.right_paddle.update(dt, keys)
            self.ball.update(dt)
            self._handle_collisions()
            self.powerups.update(dt)
        elif keys[pygame.K_r]:
            self._restart()

    def draw(self) -> None:
        self.screen.fill(BG)
        self.left_paddle.draw(self.screen)
        self.right_paddle.draw(self.screen)
        self.ball.draw(self.screen)
        self.powerups.draw(self.screen)
        self._draw_ui()
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(DISPLAY.fps) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            self.update(dt)
            self.draw()

        pygame.quit()


def run() -> None:
    PongGame().run()
