from pathlib import Path

from adk_chatkit import ADKContext
from chatkit.widgets import Card, ListView, WidgetRoot


def make_widget() -> WidgetRoot:
    serialized_widget_path = Path(__file__).parent / "tasks" / "_01.json"
    return ListView.model_validate_json(serialized_widget_path.read_text())


def make_tasks_list_widget() -> WidgetRoot:
    serialized_widget_path = Path(__file__).parent / "tasks" / "_02.json"
    return Card.model_validate_json(serialized_widget_path.read_text())
