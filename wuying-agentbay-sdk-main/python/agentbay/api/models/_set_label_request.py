# -*- coding: utf-8 -*-
# This file is auto-generated, don't edit it. Thanks.
from __future__ import annotations
from darabonba.model import DaraModel 


class SetLabelRequest(DaraModel):
    def __init__(
        self,
        authorization: str = None,
        labels: str = None,
        session_id: str = None,
    ):
        self.authorization = authorization
        self.labels = labels
        self.session_id = session_id

    def validate(self):
        pass

    def to_map(self):
        result = dict()
        _map = super().to_map()
        if _map is not None:
            result = _map
        if self.authorization is not None:
            result['Authorization'] = self.authorization

        if self.labels is not None:
            result['Labels'] = self.labels

        if self.session_id is not None:
            result['SessionId'] = self.session_id

        return result

    def from_map(self, m: dict = None):
        m = m or dict()
        if m.get('Authorization') is not None:
            self.authorization = m.get('Authorization')

        if m.get('Labels') is not None:
            self.labels = m.get('Labels')

        if m.get('SessionId') is not None:
            self.session_id = m.get('SessionId')

        return self

