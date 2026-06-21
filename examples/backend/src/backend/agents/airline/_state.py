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

    def to_dict(self) -> dict[str, Any]:
        data = self.model_dump()
        data["segments"] = [seg.model_dump() for seg in self.segments]
        return data

    def format(self) -> str:
        """Return a formatted string for agent context."""
        segment_lines = []
        for segment in self.segments:
            segment_lines.append(
                f"- {segment.flight_number} {segment.origin}->{segment.destination}"
                f" on {segment.date} seat {segment.seat} ({segment.status})"
            )
        summary = "\n".join(segment_lines)
        recent_timeline = self.timeline[:3]
        recent = "\n".join(f"  * {entry['entry']} ({entry['timestamp']})" for entry in recent_timeline)
        return (
            "<CUSTOMER_PROFILE>\n"
            f"Name: {self.name} ({self.loyalty_status})\n"
            f"Loyalty ID: {self.loyalty_id}\n"
            f"Contact: {self.email}, {self.phone}\n"
            f"Checked Bags: {self.bags_checked}\n"
            f"Meal Preference: {self.meal_preference or 'Not set'}\n"
            f"Special Assistance: {self.special_assistance or 'None'}\n"
            "Upcoming Segments:\n"
            f"{summary or '  * No segments scheduled.'}\n"
            "Recent Service Timeline:\n"
            f"{recent or '  * No service actions recorded yet.'}\n"
            "</CUSTOMER_PROFILE>"
        )


class AirlineAgentContext(BaseModel):
    """Context stored in ADK session state for airline support agent."""

    customer_profile: CustomerProfile
    booked_widget_ids: list[str] = []

    @staticmethod
    def create_initial_context() -> AirlineAgentContext:
        """Create a new context with default customer profile."""
        segments = [
            FlightSegment(
                flight_number="OA476",
                date="2025-10-02",
                origin="SFO",
                destination="JFK",
                departure_time="08:05",
                arrival_time="16:35",
                seat="14A",
            ),
            FlightSegment(
                flight_number="OA477",
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

    def record_flight_booking(
        self,
        flight_number: str,
        date: str,
        origin: str,
        destination: str,
        depart_time: str,
        arrival_time: str,
        *,
        seat: str = "TBD",
        status: str = "Scheduled",
    ) -> FlightSegment:
        """Record a new flight booking on the customer's itinerary."""
        segment = FlightSegment(
            flight_number=flight_number,
            date=date,
            origin=origin,
            destination=destination,
            departure_time=depart_time,
            arrival_time=arrival_time,
            seat=seat,
            status=status,
        )
        self.customer_profile.segments.append(segment)
        self.customer_profile.log(
            f"{status}: {flight_number} {origin}->{destination} on {date} {depart_time}-{arrival_time} seat {seat}.",
            kind="success",
        )
        return segment

    def mark_widget_consumed(self, widget_id: str) -> None:
        """Mark a widget as consumed so it can't be reused."""
        if widget_id not in self.booked_widget_ids:
            self.booked_widget_ids.append(widget_id)

    def is_widget_consumed(self, widget_id: str) -> bool:
        """Check if a widget has already been consumed."""
        return widget_id in self.booked_widget_ids

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
