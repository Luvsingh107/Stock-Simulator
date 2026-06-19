"""Entry point for the Stock Simulator CLI application."""

from __future__ import annotations

import logging
import sys
import threading
import time
import traceback

from stock_simulator.cli.interpreter import CommandResult, handle_command
from stock_simulator.models.user import User
from stock_simulator.services import trading
from stock_simulator.storage.persistence import (
    create_user_file,
    load_user,
    migrate_legacy_save,
    save_user,
    user_file_exists,
)
from stock_simulator.utils.logging_config import setup_logging
from stock_simulator.utils.paths import ensure_runtime_dirs
from stock_simulator.utils.validation import validate_username

logger = logging.getLogger(__name__)

MAX_USERNAME_ATTEMPTS = 3
MAX_BALANCE_ATTEMPTS = 5
ORDER_CHECK_INTERVAL = 3


def prompt_username() -> str:
    """Prompt until a valid username is entered."""
    for attempt in range(MAX_USERNAME_ATTEMPTS):
        username = input("What is your username? ").strip()
        valid, message = validate_username(username)
        if valid:
            return username
        print(message)
        if attempt == MAX_USERNAME_ATTEMPTS - 1:
            print("Too many invalid attempts. Exiting.")
            sys.exit(1)
    raise RuntimeError("Unreachable")


def prompt_starting_balance(user: User) -> None:
    """Prompt for a valid starting balance using a retry loop."""
    for _ in range(MAX_BALANCE_ATTEMPTS):
        try:
            balance_input = input("You're a new user!\nEnter a starting balance: ").strip()
            user.balance = float(balance_input)
            if user.balance < 0:
                print("Balance cannot be negative.")
                continue
            save_user(user)
            return
        except ValueError:
            print("Invalid balance. Please enter a number.")
        except OSError as exc:
            logger.error("Failed to save new user: %s", exc)
            print("Could not save your account. Please try again.")

    print("Too many invalid attempts. Exiting.")
    sys.exit(1)


def check_orders_loop(user: User, lock: threading.Lock, stop_event: threading.Event) -> None:
    """Background thread that periodically checks pending orders."""
    while not stop_event.is_set():
        with lock:
            try:
                trading.check_orders(user)
            except Exception:
                logger.exception("Error checking orders for %s", user.username)
        stop_event.wait(ORDER_CHECK_INTERVAL)


def command_loop(user: User, lock: threading.Lock, stop_event: threading.Event) -> None:
    """Main REPL loop for processing user commands."""
    print(
        "\nWelcome to Stock Simulator!\n"
        "Trade stocks with virtual cash using live Yahoo Finance data.\n"
        "Type 'help' for available commands.\n"
    )

    while not stop_event.is_set():
        try:
            command = input("\n> ")
        except (EOFError, KeyboardInterrupt):
            print("\nSaving and exiting...")
            with lock:
                save_user(user)
            stop_event.set()
            return

        print()
        result = CommandResult()
        with lock:
            try:
                result = handle_command(command, user)
            except (ValueError, IndexError, KeyError) as exc:
                print(f"Invalid input: {exc}")
                logger.warning("Command error for %s: %s", user.username, exc)
            except Exception:
                print("An unexpected error occurred. Check logs for details.")
                logger.exception("Unexpected command error for %s", user.username)
            try:
                save_user(user)
            except OSError as exc:
                print(f"Warning: could not save progress ({exc}).")
                logger.error("Save failed for %s: %s", user.username, exc)

        if result.should_exit:
            print("Goodbye!")
            stop_event.set()
            return


def run() -> None:
    """Start the Stock Simulator application."""
    ensure_runtime_dirs()

    username = prompt_username()
    setup_logging(username)
    user = User(username=username, balance=0.0)

    if user_file_exists(user):
        try:
            migrate_legacy_save(user)
            load_user(user)
            print(f"Welcome back, {user.username}!")
            print(f"Your balance is ${user.balance:.2f}.\n")
            trading.check_orders_retroactive(user)
            save_user(user)
        except (OSError, ValueError) as exc:
            logger.error("Failed to load user %s: %s\n%s", username, exc, traceback.format_exc())
            print(f"Could not load your save file: {exc}")
            sys.exit(1)
    else:
        try:
            create_user_file(user)
            prompt_starting_balance(user)
        except (OSError, FileExistsError) as exc:
            logger.error("Failed to create user %s: %s", username, exc)
            print(f"Could not create your account: {exc}")
            sys.exit(1)

    stop_event = threading.Event()
    lock = threading.Lock()

    orders_thread = threading.Thread(
        target=check_orders_loop,
        args=(user, lock, stop_event),
        daemon=True,
        name="orders",
    )
    commands_thread = threading.Thread(
        target=command_loop,
        args=(user, lock, stop_event),
        daemon=False,
        name="commands",
    )

    orders_thread.start()
    commands_thread.start()

    while commands_thread.is_alive():
        time.sleep(1)
        if not orders_thread.is_alive() and not stop_event.is_set():
            logger.warning("Orders thread died; restarting.")
            orders_thread = threading.Thread(
                target=check_orders_loop,
                args=(user, lock, stop_event),
                daemon=True,
                name="orders",
            )
            orders_thread.start()

    commands_thread.join(timeout=5)


if __name__ == "__main__":
    run()
