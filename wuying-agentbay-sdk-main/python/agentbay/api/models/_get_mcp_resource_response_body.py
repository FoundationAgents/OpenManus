# -*- coding: utf-8 -*-
# This file is auto-generated, don't edit it. Thanks.
from __future__ import annotations
from darabonba.model import DaraModel 
from agentbay.api import models as main_models 


class GetMcpResourceResponseBody(DaraModel):
    def __init__(
        self,
        code: str = None,
        data: main_models.GetMcpResourceResponseBodyData = None,
        http_status_code: int = None,
        message: str = None,
        request_id: str = None,
        success: bool = None,
    ):
        self.code = code
        self.data = data
        self.http_status_code = http_status_code
        self.message = message
        self.request_id = request_id
        self.success = success

    def validate(self):
        if self.data:
            self.data.validate()

    def to_map(self):
        result = dict()
        _map = super().to_map()
        if _map is not None:
            result = _map
        if self.code is not None:
            result['Code'] = self.code

        if self.data is not None:
            result['Data'] = self.data.to_map()

        if self.http_status_code is not None:
            result['HttpStatusCode'] = self.http_status_code

        if self.message is not None:
            result['Message'] = self.message

        if self.request_id is not None:
            result['RequestId'] = self.request_id

        if self.success is not None:
            result['Success'] = self.success

        return result

    def from_map(self, m: dict = None):
        m = m or dict()
        if m.get('Code') is not None:
            self.code = m.get('Code')

        if m.get('Data') is not None:
            temp_model = main_models.GetMcpResourceResponseBodyData()
            self.data = temp_model.from_map(m.get('Data'))

        if m.get('HttpStatusCode') is not None:
            self.http_status_code = m.get('HttpStatusCode')

        if m.get('Message') is not None:
            self.message = m.get('Message')

        if m.get('RequestId') is not None:
            self.request_id = m.get('RequestId')

        if m.get('Success') is not None:
            self.success = m.get('Success')

        return self

class GetMcpResourceResponseBodyData(DaraModel):
    def __init__(
        self,
        desktop_info: main_models.GetMcpResourceResponseBodyDataDesktopInfo = None,
        resource_url: str = None,
        session_id: str = None,
    ):
        self.desktop_info = desktop_info
        self.resource_url = resource_url
        self.session_id = session_id

    def validate(self):
        if self.desktop_info:
            self.desktop_info.validate()

    def to_map(self):
        result = dict()
        _map = super().to_map()
        if _map is not None:
            result = _map
        if self.desktop_info is not None:
            result['DesktopInfo'] = self.desktop_info.to_map()

        if self.resource_url is not None:
            result['ResourceUrl'] = self.resource_url

        if self.session_id is not None:
            result['SessionId'] = self.session_id

        return result

    def from_map(self, m: dict = None):
        m = m or dict()
        if m.get('DesktopInfo') is not None:
            temp_model = main_models.GetMcpResourceResponseBodyDataDesktopInfo()
            self.desktop_info = temp_model.from_map(m.get('DesktopInfo'))

        if m.get('ResourceUrl') is not None:
            self.resource_url = m.get('ResourceUrl')

        if m.get('SessionId') is not None:
            self.session_id = m.get('SessionId')

        return self

class GetMcpResourceResponseBodyDataDesktopInfo(DaraModel):
    def __init__(
        self,
        app_id: str = None,
        auth_code: str = None,
        connection_properties: str = None,
        resource_id: str = None,
        resource_type: str = None,
        ticket: str = None,
    ):
        self.app_id = app_id
        self.auth_code = auth_code
        self.connection_properties = connection_properties
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.ticket = ticket

    def validate(self):
        pass

    def to_map(self):
        result = dict()
        _map = super().to_map()
        if _map is not None:
            result = _map
        if self.app_id is not None:
            result['AppId'] = self.app_id

        if self.auth_code is not None:
            result['AuthCode'] = self.auth_code

        if self.connection_properties is not None:
            result['ConnectionProperties'] = self.connection_properties

        if self.resource_id is not None:
            result['ResourceId'] = self.resource_id

        if self.resource_type is not None:
            result['ResourceType'] = self.resource_type

        if self.ticket is not None:
            result['Ticket'] = self.ticket

        return result

    def from_map(self, m: dict = None):
        m = m or dict()
        if m.get('AppId') is not None:
            self.app_id = m.get('AppId')

        if m.get('AuthCode') is not None:
            self.auth_code = m.get('AuthCode')

        if m.get('ConnectionProperties') is not None:
            self.connection_properties = m.get('ConnectionProperties')

        if m.get('ResourceId') is not None:
            self.resource_id = m.get('ResourceId')

        if m.get('ResourceType') is not None:
            self.resource_type = m.get('ResourceType')

        if m.get('Ticket') is not None:
            self.ticket = m.get('Ticket')

        return self

