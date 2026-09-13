from celery import Celery

app = Celery(
    "ai_survival",
    broker="redis://localhost:6379/1",
    backend="redis://localhost:6379/2",
)

app.conf.task_routes = {
    "backend.execution.engine.*": {"queue": "gpu"},
    "backend.agents.orchestrator.*": {"queue": "orchestration"},
}

app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.task_track_started = True
app.conf.task_time_limit = 3600
app.conf.task_soft_time_limit = 3500
