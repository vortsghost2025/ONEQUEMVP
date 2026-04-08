import sys, os

sys.path.append(os.path.abspath("."))

from app.main import on_startup, engine
from sqlmodel import Session, select
from app.models import Settings, Task

# Run startup logic manually
on_startup()

with Session(engine) as session:
    s = session.get(Settings, 1)
    print("Settings row:", s)
    task_count = session.exec(select(Task)).count()
    print("Task count:", task_count)
