# -*- coding: utf-8 -*-
# This file is auto-generated, don't edit it. Thanks.
from __future__ import annotations
from darabonba.model import DaraModel 


class CallMcpToolRequest(DaraModel):
    def __init__(
        self,
        args: str = None,
        authorization: str = None,
        external_user_id: str = None,
        image_id: str = None,
        name: str = None,
        server: str = None,
        session_id: str = None,
        tool: str = None,
    ):
        self.args = args
        self.authorization = authorization
        self.external_user_id = external_user_id
        self.image_id = image_id
        self.name = name
        self.server = server
        self.session_id = session_id
        self.tool = tool

    def validate(self):
        pass

    def to_map(self):
        result = dict()
        _map = super().to_map()
        if _map is not None:
            result = _map
        if self.args is not None:
            result['Args'] = self.args

        if self.authorization is not None:
            result['Authorization'] = self.authorization

        if self.external_user_id is not None:
            result['ExternalUserId'] = self.external_user_id

        if self.image_id is not None:
            result['ImageId'] = self.image_id

        if self.name is not None:
            result['Name'] = self.name

        if self.server is not None:
            result['Server'] = self.server

        if self.session_id is not None:
            result['SessionId'] = self.session_id

        if self.tool is not None:
            result['Tool'] = self.tool

        return result

    def from_map(self, m: dict = None):
        m = m or dict()
        if m.get('Args') is not None:
            self.args = m.get('Args')

        if m.get('Authorization') is not None:
            self.authorization = m.get('Authorization')

        if m.get('ExternalUserId') is not None:
            self.external_user_id = m.get('ExternalUserId')

        if m.get('ImageId') is not None:
            self.image_id = m.get('ImageId')

        if m.get('Name') is not None:
            self.name = m.get('Name')

        if m.get('Server') is not None:
            self.server = m.get('Server')

        if m.get('SessionId') is not None:
            self.session_id = m.get('SessionId')

        if m.get('Tool') is not None:
            self.tool = m.get('Tool')

        return self

