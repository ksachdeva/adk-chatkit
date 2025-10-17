from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class FlightSegment(BaseModel):
    flight_number: str
    date: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    seat: str
    status: str = "Scheduled"

    def cancel(self) -> None:
        self.status = "Cancelled"

    def change_seat(self, new_seat: str) -> None:
        self.seat = new_seat


class CustomerProfile(BaseModel):
    customer_id: str
    name: str
    loyalty_status: str
    loyalty_id: str
    email: str
    phone: str
    tier_benefits: list[str]
    segments: list[FlightSegment]
    bags_checked: int = 0
    meal_preference: str | None = None
    special_assistance: str | None = None
    timeline: list[dict[str, Any]] = []

    def log(self, entry: str, kind: str = "info") -> None:
        self.timeline.insert(0, {"timestamp": _now_iso(), "kind": kind, "entry": entry})

    def format(self) -> str:
        segments = []
        for segment in self.segments:
            segments.append(
                f"- {segment.flight_number} {segment.origin}->{segment.destination}"
                f" on {segment.date} seat {segment.seat} ({segment.status})"
            )
        summary = "\n".join(segments)
        timeline = self.timeline[:3]
        recent = "\n".join(f"  * {entry['entry']} ({entry['timestamp']})" for entry in timeline)
        return (
            "Customer Profile\n"
            f"Name: {self.name} ({self.loyalty_status})\n"
            f"Loyalty ID: {self.loyalty_id}\n"
            f"Contact: {self.email}, {self.phone}\n"
            f"Checked Bags: {self.bags_checked}\n"
            f"Meal Preference: {self.meal_preference or 'Not set'}\n"
            f"Special Assistance: {self.special_assistance or 'None'}\n"
            "Upcoming Segments:\n"
            f"{summary}\n"
            "Recent Service Timeline:\n"
            f"{recent or '  * No service actions recorded yet.'}"
        )


class AirlineAgentContext(BaseModel):
    customer_profile: CustomerProfile

    @staticmethod
    def create_initial_context() -> AirlineAgentContext:
        segments = [
            FlightSegment(
                flight_number="0A476",
                date="2025-10-02",
                origin="SFO",
                destination="JFK",
                departure_time="08:05",
                arrival_time="16:35",
                seat="14A",
            ),
            FlightSegment(
                flight_number="0A477",
                date="2025-10-10",
                origin="JFK",
                destination="SFO",
                departure_time="18:50",
                arrival_time="22:15",
                seat="15C",
            ),
        ]
        profile = CustomerProfile(
            customer_id="cus_98421",
            name="Jordan Miles",
            loyalty_status="Aviator Platinum",
            loyalty_id="APL-204981",
            email="jordan.miles@example.com",
            phone="+1 (415) 555-9214",
            tier_benefits=[
                "Complimentary upgrades when available",
                "Unlimited lounge access",
                "Priority boarding group 1",
            ],
            segments=segments,
        )
        profile.log("Itinerary imported from confirmation LL0EZ6.", kind="system")
        return AirlineAgentContext(customer_profile=profile)

    def change_seat(self, flight_number: str, seat: str) -> str:
        if not self._is_valid_seat(seat):
            raise ValueError("Seat must be a row number followed by a letter, for example 12C.")

        segment = self._find_segment(flight_number)
        if segment is None:
            raise ValueError(f"Flight {flight_number} is not on the customer's itinerary.")

        previous = segment.seat
        segment.change_seat(seat.upper())
        self.customer_profile.log(
            f"Seat changed on {segment.flight_number} from {previous} to {segment.seat}.",
            kind="success",
        )
        return f"Seat updated to {segment.seat} on flight {segment.flight_number}."

    def cancel_trip(self) -> str:
        for segment in self.customer_profile.segments:
            segment.cancel()
        self.customer_profile.log("Trip cancelled at customer request.", kind="warning")
        return "The reservation has been cancelled. Refund processing will begin immediately."

    def add_bag(self) -> str:
        self.customer_profile.bags_checked += 1
        self.customer_profile.log(
            f"Added checked bag. Total bags now {self.customer_profile.bags_checked}.", kind="info"
        )
        return f"Checked bag added. You now have {self.customer_profile.bags_checked} bag(s) checked."

    def set_meal(self, meal: str) -> str:
        self.customer_profile.meal_preference = meal
        self.customer_profile.log(f"Meal preference updated to {meal}.", kind="info")
        return f"We'll note {meal} as the meal preference."

    def request_assistance(self, note: str) -> str:
        self.customer_profile.special_assistance = note
        self.customer_profile.log(f"Special assistance noted: {note}.", kind="info")
        return "Assistance request recorded. Airport staff will be notified."

    @staticmethod
    def _is_valid_seat(seat: str) -> bool:
        seat = seat.strip().upper()
        if len(seat) < 2:
            return False
        row = seat[:-1]
        letter = seat[-1]
        return row.isdigit() and letter.isalpha()

    def _find_segment(self, flight_number: str) -> FlightSegment | None:
        flight_number = flight_number.upper().strip()
        for segment in self.customer_profile.segments:
            if segment.flight_number.upper() == flight_number:
                return segment
        return None
