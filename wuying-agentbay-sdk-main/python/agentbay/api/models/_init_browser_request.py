# -*- coding: utf-8 -*-
# This file is auto-generated, don't edit it. Thanks.
from __future__ import annotations
from darabonba.model import DaraModel

class InitBrowserRequest(DaraModel):
    def __init__(
        self,
        authorization: str = None,
        persistent_path: str = None,
        session_id: str = None,
        browser_option: dict = None,
    ):
        self.authorization = authorization
        self.persistent_path = persistent_path
        self.session_id = session_id
        self.browser_option = browser_option

    def validate(self):
        pass

    def to_map(self):
        result = dict()
        _map = super().to_map()
        if _map is not None:
            result = _map
        if self.authorization is not None:
            result['Authorization'] = self.authorization

        if self.persistent_path is not None:
            result['PersistentPath'] = self.persistent_path

        if self.session_id is not None:
            result['SessionId'] = self.session_id

        if self.browser_option is not None:
            result['BrowserOption'] = self.browser_option

        return result

    def from_map(self, m: dict = None):
        m = m or dict()
        if m.get('Authorization') is not None:
            self.authorization = m.get('Authorization')

        if m.get('PersistentPath') is not None:
            self.persistent_path = m.get('PersistentPath')

        if m.get('SessionId') is not None:
            self.session_id = m.get('SessionId')

        return self

