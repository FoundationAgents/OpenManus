# -*- coding: utf-8 -*-
# This file is auto-generated, don't edit it. Thanks.
from __future__ import annotations
from darabonba.model import DaraModel 


class GetContextInfoRequest(DaraModel):
    def __init__(
        self,
        authorization: str = None,
        context_id: str = None,
        path: str = None,
        session_id: str = None,
        task_type: str = None,
    ):
        self.authorization = authorization
        self.context_id = context_id
        self.path = path
        self.session_id = session_id
        self.task_type = task_type

    def validate(self):
        pass

    def to_map(self):
        result = dict()
        _map = super().to_map()
        if _map is not None:
            result = _map
        if self.authorization is not None:
            result['Authorization'] = self.authorization

        if self.context_id is not None:
            result['ContextId'] = self.context_id

        if self.path is not None:
            result['Path'] = self.path

        if self.session_id is not None:
            result['SessionId'] = self.session_id

        if self.task_type is not None:
            result['TaskType'] = self.task_type

        return result

    def from_map(self, m: dict = None):
        m = m or dict()
        if m.get('Authorization') is not None:
            self.authorization = m.get('Authorization')

        if m.get('ContextId') is not None:
            self.context_id = m.get('ContextId')

        if m.get('Path') is not None:
            self.path = m.get('Path')

        if m.get('SessionId') is not None:
            self.session_id = m.get('SessionId')

        if m.get('TaskType') is not None:
            self.task_type = m.get('TaskType')

        return self

