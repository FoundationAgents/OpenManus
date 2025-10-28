# -*- coding: utf-8 -*-
# This file is auto-generated, don't edit it. Thanks.
from __future__ import annotations
from darabonba.model import DaraModel 
from agentbay.api import models as main_models 
from typing import Optional


class CreateMcpSessionResponseBody(DaraModel):
    def __init__(
        self,
        code: Optional[str] = None,
        data: Optional[main_models.CreateMcpSessionResponseBodyData] = None,
        http_status_code: Optional[int] = None,
        message: Optional[str] = None,
        request_id: Optional[str] = None,
        success: Optional[bool] = None,
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

    def from_map(self, m: Optional[dict] = None):
        m = m or dict()
        if m.get('Code') is not None:
            self.code = m.get('Code')

        if m.get('Data') is not None:
            temp_model = main_models.CreateMcpSessionResponseBodyData()
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

class CreateMcpSessionResponseBodyData(DaraModel):
    def __init__(
        self,
        app_instance_id: Optional[str] = None,
        err_msg: Optional[str] = None,
        http_port: Optional[str] = None,
        network_interface_ip: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_url: Optional[str] = None,
        session_id: Optional[str] = None,
        success: Optional[bool] = None,
        token: Optional[str] = None,
        vpc_resource: Optional[bool] = None,
    ):
        self.app_instance_id = app_instance_id
        self.err_msg = err_msg
        self.http_port = http_port
        self.network_interface_ip = network_interface_ip
        self.resource_id = resource_id
        self.resource_url = resource_url
        self.session_id = session_id
        self.success = success
        self.token = token
        self.vpc_resource = vpc_resource

    def validate(self):
        pass

    def to_map(self):
        result = dict()
        _map = super().to_map()
        if _map is not None:
            result = _map
        if self.app_instance_id is not None:
            result['AppInstanceId'] = self.app_instance_id

        if self.err_msg is not None:
            result['ErrMsg'] = self.err_msg

        if self.http_port is not None:
            result['HttpPort'] = self.http_port

        if self.network_interface_ip is not None:
            result['NetworkInterfaceIp'] = self.network_interface_ip

        if self.resource_id is not None:
            result['ResourceId'] = self.resource_id

        if self.resource_url is not None:
            result['ResourceUrl'] = self.resource_url

        if self.session_id is not None:
            result['SessionId'] = self.session_id

        if self.success is not None:
            result['Success'] = self.success

        if self.token is not None:
            result['Token'] = self.token

        if self.vpc_resource is not None:
            result['VpcResource'] = self.vpc_resource

        return result

    def from_map(self, m: Optional[dict] = None):
        m = m or dict()
        if m.get('AppInstanceId') is not None:
            self.app_instance_id = m.get('AppInstanceId')

        if m.get('ErrMsg') is not None:
            self.err_msg = m.get('ErrMsg')

        if m.get('HttpPort') is not None:
            self.http_port = m.get('HttpPort')

        if m.get('NetworkInterfaceIp') is not None:
            self.network_interface_ip = m.get('NetworkInterfaceIp')

        if m.get('ResourceId') is not None:
            self.resource_id = m.get('ResourceId')

        if m.get('ResourceUrl') is not None:
            self.resource_url = m.get('ResourceUrl')

        if m.get('SessionId') is not None:
            self.session_id = m.get('SessionId')

        if m.get('Success') is not None:
            self.success = m.get('Success')

        if m.get('Token') is not None:
            self.token = m.get('Token')

        if m.get('VpcResource') is not None:
            self.vpc_resource = m.get('VpcResource')

        return self

