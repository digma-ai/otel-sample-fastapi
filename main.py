import os
from typing import List
from typing import Optional

import git
import uvicorn as uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from opentelemetry.instrumentation.digma import DigmaConfiguration
from opentelemetry.instrumentation.digma.fastapi import DigmaFastAPIInstrumentor
from opentelemetry.instrumentation.digma import digma_opentelemetry_boostrap
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from database_validation import DomainValidator
from database_validation import Permisson
from opentelemetry import trace
from root_api_response import RootApiResponse
from user.user_service import UserService
from user_validation import UserValidator

load_dotenv()

try:
    repo = git.Repo(search_parent_directories=True)
    os.environ['GIT_COMMIT_ID'] = repo.head.object.hexsha
except:
    pass

app = FastAPI()

FastAPIInstrumentor.instrument_app(app)
DigmaFastAPIInstrumentor.instrument_app(app)

RequestsInstrumentor().instrument()
LoggingInstrumentor().instrument(set_logging_format=True)
tracer = trace.get_tracer(__name__)

digma_opentelemetry_boostrap(service_name='server-ms', digma_backend="http://localhost:5050",
                             configuration=DigmaConfiguration().trace_this_package())
user_service = UserService()

@app.get("/")
async def root():
    try:
        with tracer.start_as_current_span("root"):

            await DomainValidator().validate_permissions()

            return RootApiResponse().render()

    except Exception as ex:
        raise Exception(f'error occurred : {str(ex)}')


@app.get("/validate/")
async def validate(user_ids: Optional[List[str]] = Query(None)):
    ids = str.split(user_ids[0], ',')

    await DomainValidator().validate_permissions()

    await DomainValidator().validate_group_exists(["admins"])

    with tracer.start_as_current_span("user validation"):
        await UserValidator().validate_user(ids)

    return "okay"


@app.get("/process")
async def process():
    with tracer.start_as_current_span("process validation"):
        await DomainValidator().validate_permissions()


@app.get("/login")
async def login():
    try:
        with tracer.start_as_current_span("login validation"):
            await user_service.validate(Permisson.current_context)
    except Exception as ex:
        raise Exception(f'error occurred : {str(ex)}')


@app.get("/validateuser/{user_id}")
async def validate_user(user_id: str):
    await user_service.validate(user_id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
