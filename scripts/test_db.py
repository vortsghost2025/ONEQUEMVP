import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlmodel import SQLModel, create_engine, Session
from app.models import Task, Settings, TaskStatus

engine = create_engine("sqlite:///test_onequeue.db")
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    # Ensure Settings singleton exists
    if not session.get(Settings, 1):
        session.add(Settings())
        session.commit()
    # Insert a task
    task = Task(name="sample", prompt="test")
    session.add(task)
    session.commit()
    print("Inserted task id:", task.id)
    settings = session.get(Settings, 1)
    print("Settings row:", settings)
