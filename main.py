from pong.app import run
from pong.logging_config import configure_logging, mode_from_env


if __name__ == "__main__":
    configure_logging(mode_from_env())
    import logging

    logging.getLogger(__name__).info("Starting Battle Pong entrypoint")
    run()
