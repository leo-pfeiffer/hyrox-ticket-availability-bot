import logging

import requests
from bs4 import BeautifulSoup
from requests import request
from enum import Enum, auto
from datetime import datetime

logging.basicConfig(level=logging.INFO)

URLS = {
    "Anaheim": "https://hyrox.com/event/hyrox-anaheim/",
    "Chicago": "https://hyrox.com/event/hyrox-chicago/",
    "Dallas": "https://hyrox.com/event/hyrox-dallas/"
}

SEND_HOUR = 12


class Status(Enum):
    AVAILABLE = auto()
    UNCLEAR = auto()
    NOT_AVAILABLE = auto()


def get_html(url: str):
    cookie_retrieval = request("GET", url)
    cookie = cookie_retrieval.request.headers.get("Cookie")
    response = request("GET", url, headers={"Cookie": cookie})
    return response.text


def get_status(soup: BeautifulSoup) -> Status:
    sale_starts_soon = len(soup.body.find_all(string='Ticket sales start soon!')) > 0
    can_buy_tickets = len(soup.body.find_all(string='Buy Tickets here')) > 0

    if not sale_starts_soon and not can_buy_tickets:
        return Status.UNCLEAR

    if sale_starts_soon and can_buy_tickets:
        return Status.UNCLEAR

    if sale_starts_soon:
        return Status.NOT_AVAILABLE

    if can_buy_tickets:
        return Status.AVAILABLE


def compile_message(event_name: str, status: Status) -> str:
    return f"{event_name}: {status.name}"


def get_message(event_status: dict[str, Status]) -> str:
    messages = [compile_message(event, status) for event, status in event_status.items()]
    return "\n".join(messages)


def events_available(event_status: dict[str, Status]) -> bool:
    return any(list(filter(lambda status: status == Status.AVAILABLE, event_status.values())))


def get_title(event_status: dict[str, Status]):
    message = "No events available!"
    if events_available(event_status):
        message = "Events available!"
    return f"HYROX: {message}"


def get_priority(event_status: dict[str, Status]) -> str:
    if events_available(event_status):
        return "urgent"
    return "low"


def get_tag(event_status: dict[str, Status]) -> str:
    if events_available(event_status):
        return "rotating_light"
    return "information_source"


def send_message(message, title, priority, tag):
    requests.post(
        "https://ntfy.sh/hyrox-sale-is-live",
        data=message,
        headers={
            "Title": title,
            "Priority": priority,
            "Tags": tag
        }
    )
    logging.info(f"Sent message.")


def check_events() -> dict[str, Status]:
    _event_status = {}

    for event, url in URLS.items():
        html = get_html(url)
        soup = BeautifulSoup(html, 'html.parser')
        status = get_status(soup)
        _event_status[event] = status

    return _event_status


def should_send(is_events_available: bool, run_hour: int) -> bool:
    """
    Send if tickets are available or once a day at SEND_HOUR.
    """
    logging.info(f"Run hour {now().hour}")
    if is_events_available:
        return True
    return run_hour == SEND_HOUR



if __name__ == '__main__':
    
    _event_status = check_events()

    run_hour = datetime.now().hour
    is_events_available = events_available(_event_status)

    logging.info(f"Run hour {run_hour=}.")
    logging.info(f"Events available {is_events_available=}.")
    
    if should_send(is_events_available, run_hour):
        send_message(
            get_message(_event_status),
            get_title(_event_status),
            get_priority(_event_status),
            get_tag(_event_status)
        )
