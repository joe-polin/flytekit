import importlib
from typing import Optional

import grpc
import msgpack
from airflow.utils.context import Context
from flyteidl.admin.agent_pb2 import (
    PERMANENT_FAILURE,
    RUNNING,
    SUCCEEDED,
    CreateTaskResponse,
    DeleteTaskResponse,
    GetTaskResponse,
    Resource,
)
from flytekitplugins.airflow.task import AirflowConfig

from flytekit import FlyteContextManager, logger
from flytekit.extend.backend.base_agent import AgentBase, AgentRegistry
from flytekit.models.literals import LiteralMap
from flytekit.models.task import TaskTemplate


class AirflowAgent(AgentBase):
    def __init__(self):
        super().__init__(task_type="airflow")

    def create(
        self,
        context: grpc.ServicerContext,
        output_prefix: str,
        task_template: TaskTemplate,
        inputs: Optional[LiteralMap] = None,
    ) -> CreateTaskResponse:
        return CreateTaskResponse(resource_meta=msgpack.packb(task_template.custom))

    def get(self, context: grpc.ServicerContext, resource_meta: bytes) -> GetTaskResponse:
        cfg = AirflowConfig(**msgpack.unpackb(resource_meta))
        task_module = importlib.import_module(name=cfg.task_module)
        task_def = getattr(task_module, cfg.task_name)
        ctx = FlyteContextManager.current_context()
        ctx.user_space_params._attrs["GET_ORIGINAL_TASK"] = True
        sensor = task_def(**cfg.task_config)
        try:
            res = sensor.poke(context=Context())
            if res:
                cur_state = SUCCEEDED
            else:
                cur_state = RUNNING
        except Exception as e:
            logger.error(e.__str__())
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(e.__str__())
            return GetTaskResponse(resource=Resource(state=PERMANENT_FAILURE))
        return GetTaskResponse(resource=Resource(state=cur_state, outputs=None))

    def delete(self, context: grpc.ServicerContext, resource_meta: bytes) -> DeleteTaskResponse:
        # Do Nothing
        return DeleteTaskResponse()


AgentRegistry.register(AirflowAgent())
