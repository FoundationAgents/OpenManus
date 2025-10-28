# -*- coding: utf-8 -*-
# This file is auto-generated, don't edit it. Thanks.
from __future__ import annotations
from darabonba.model import DaraModel 


class ListMcpToolsRequest(DaraModel):
    def __init__(
        self,
        authorization: str = None,
        image_id: str = None,
    ):
        self.authorization = authorization
        self.image_id = image_id

    def validate(self):
        pass

    def to_map(self):
        result = dict()
        _map = super().to_map()
        if _map is not None:
            result = _map
        if self.authorization is not None:
            result['Authorization'] = self.authorization

        if self.image_id is not None:
            result['ImageId'] = self.image_id

        return result

    def from_map(self, m: dict = None):
        m = m or dict()
        if m.get('Authorization') is not None:
            self.authorization = m.get('Authorization')

        if m.get('ImageId') is not None:
            self.image_id = m.get('ImageId')

        return self

