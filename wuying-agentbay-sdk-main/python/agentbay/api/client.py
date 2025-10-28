# -*- coding: utf-8 -*-
# This file is auto-generated, don't edit it. Thanks.
from __future__ import annotations
import json
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import utils_models as open_api_util_models
from darabonba.core import DaraCore as DaraCore
from alibabacloud_tea_openapi.utils import Utils
from agentbay.api import models as main_models
from darabonba.runtime import RuntimeOptions
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import utils_models as open_api_util_models
from darabonba.core import DaraCore as DaraCore
from alibabacloud_tea_openapi.utils import Utils
from agentbay.api import models as main_models
from darabonba.runtime import RuntimeOptions
from typing import Dict


"""
"""




class Client(OpenApiClient):

    def __init__(
        self,
        config: open_api_util_models.Config,
    ):
        super().__init__(config)
        self._signature_algorithm = "v2"
        self._endpoint_rule = ""
        self._signature_algorithm = "v2"
        self._endpoint_rule = ""
        self.check_config(config)
        self._endpoint = self.get_endpoint(
            "wuyingai",
            "",
            self._endpoint_rule,
            self._network,
            self._suffix,
            self._endpoint_map,
            self._endpoint,
        )

    def get_endpoint(
        self,
        product_id: str,
        region_id: str,
        endpoint_rule: str,
        network: str,
        suffix: str,
        endpoint_map: Dict[str, str],
        endpoint: str,
    ) -> str:
        if not DaraCore.is_null(endpoint):
            return endpoint
        if not DaraCore.is_null(endpoint_map) and not DaraCore.is_null(
            endpoint_map.get(region_id)
        ):
            return endpoint_map.get(region_id)
        return Utils.get_endpoint_rules(
            product_id, region_id, endpoint_rule, network, suffix
        )

    def call_mcp_tool_with_options(
        self,
        request: main_models.CallMcpToolRequest,
        runtime: RuntimeOptions,
    ) -> main_models.CallMcpToolResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.args):
            body["Args"] = request.args
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.external_user_id):
            body["ExternalUserId"] = request.external_user_id
        if not DaraCore.is_null(request.image_id):
            body["ImageId"] = request.image_id
        if not DaraCore.is_null(request.name):
            body["Name"] = request.name
        if not DaraCore.is_null(request.server):
            body["Server"] = request.server
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        if not DaraCore.is_null(request.tool):
            body["Tool"] = request.tool
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="CallMcpTool",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.CallMcpToolResponse(), self.call_api(params, req, runtime)
        )

    async def call_mcp_tool_with_options_async(
        self,
        request: main_models.CallMcpToolRequest,
        runtime: RuntimeOptions,
    ) -> main_models.CallMcpToolResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.args):
            body["Args"] = request.args
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.external_user_id):
            body["ExternalUserId"] = request.external_user_id
        if not DaraCore.is_null(request.image_id):
            body["ImageId"] = request.image_id
        if not DaraCore.is_null(request.name):
            body["Name"] = request.name
        if not DaraCore.is_null(request.server):
            body["Server"] = request.server
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        if not DaraCore.is_null(request.tool):
            body["Tool"] = request.tool
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="CallMcpTool",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.CallMcpToolResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def call_mcp_tool(
        self,
        request: main_models.CallMcpToolRequest,
        read_timeout: int = None,
        connect_timeout: int = None,
    ) -> main_models.CallMcpToolResponse:
        runtime = RuntimeOptions(read_timeout=read_timeout, connect_timeout=connect_timeout)
        return self.call_mcp_tool_with_options(request, runtime)

    async def call_mcp_tool_async(
        self,
        request: main_models.CallMcpToolRequest,
        read_timeout: int = None,
        connect_timeout: int = None,
    ) -> main_models.CallMcpToolResponse:
        runtime = RuntimeOptions(read_timeout=read_timeout, connect_timeout=connect_timeout)
        return await self.call_mcp_tool_with_options_async(request, runtime)

    def create_mcp_session_with_options(
        self,
        tmp_req: main_models.CreateMcpSessionRequest,
        runtime: RuntimeOptions,
    ) -> main_models.CreateMcpSessionResponse:
        tmp_req.validate()
        request = main_models.CreateMcpSessionShrinkRequest()
        Utils.convert(tmp_req, request)
        if not DaraCore.is_null(tmp_req.persistence_data_list):
            request.persistence_data_list_shrink = (
                Utils.array_to_string_with_specified_style(
                    tmp_req.persistence_data_list, "PersistenceDataList", "json"
                )
            )
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.context_id):
            body["ContextId"] = request.context_id
        if not DaraCore.is_null(request.external_user_id):
            body["ExternalUserId"] = request.external_user_id
        if not DaraCore.is_null(request.image_id):
            body["ImageId"] = request.image_id
        if not DaraCore.is_null(request.labels):
            body["Labels"] = request.labels
        if not DaraCore.is_null(request.mcp_policy_id):
            body["McpPolicyId"] = request.mcp_policy_id
        if not DaraCore.is_null(request.persistence_data_list_shrink):
            body["PersistenceDataList"] = request.persistence_data_list_shrink
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        if not DaraCore.is_null(request.vpc_resource):
            body["VpcResource"] = request.vpc_resource
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="CreateMcpSession",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.CreateMcpSessionResponse(), self.call_api(params, req, runtime)
        )

    async def create_mcp_session_with_options_async(
        self,
        tmp_req: main_models.CreateMcpSessionRequest,
        runtime: RuntimeOptions,
    ) -> main_models.CreateMcpSessionResponse:
        tmp_req.validate()
        request = main_models.CreateMcpSessionShrinkRequest()
        Utils.convert(tmp_req, request)
        if not DaraCore.is_null(tmp_req.persistence_data_list):
            request.persistence_data_list_shrink = (
                Utils.array_to_string_with_specified_style(
                    tmp_req.persistence_data_list, "PersistenceDataList", "json"
                )
            )
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.context_id):
            body["ContextId"] = request.context_id
        if not DaraCore.is_null(request.external_user_id):
            body["ExternalUserId"] = request.external_user_id
        if not DaraCore.is_null(request.image_id):
            body["ImageId"] = request.image_id
        if not DaraCore.is_null(request.labels):
            body["Labels"] = request.labels
        if not DaraCore.is_null(request.mcp_policy_id):
            body["McpPolicyId"] = request.mcp_policy_id
        if not DaraCore.is_null(request.persistence_data_list_shrink):
            body["PersistenceDataList"] = request.persistence_data_list_shrink
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        if not DaraCore.is_null(request.vpc_resource):
            body["VpcResource"] = request.vpc_resource
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="CreateMcpSession",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.CreateMcpSessionResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def create_mcp_session(
        self,
        request: main_models.CreateMcpSessionRequest,
    ) -> main_models.CreateMcpSessionResponse:
        runtime = RuntimeOptions()
        return self.create_mcp_session_with_options(request, runtime)

    async def create_mcp_session_async(
        self,
        request: main_models.CreateMcpSessionRequest,
    ) -> main_models.CreateMcpSessionResponse:
        runtime = RuntimeOptions()
        return await self.create_mcp_session_with_options_async(request, runtime)

    def delete_context_with_options(
        self,
        request: main_models.DeleteContextRequest,
        runtime: RuntimeOptions,
    ) -> main_models.DeleteContextResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.id):
            body["Id"] = request.id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="DeleteContext",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.DeleteContextResponse(), self.call_api(params, req, runtime)
        )

    async def delete_context_with_options_async(
        self,
        request: main_models.DeleteContextRequest,
        runtime: RuntimeOptions,
    ) -> main_models.DeleteContextResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.id):
            body["Id"] = request.id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="DeleteContext",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.DeleteContextResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def delete_context(
        self,
        request: main_models.DeleteContextRequest,
    ) -> main_models.DeleteContextResponse:
        runtime = RuntimeOptions()
        return self.delete_context_with_options(request, runtime)

    async def delete_context_async(
        self,
        request: main_models.DeleteContextRequest,
    ) -> main_models.DeleteContextResponse:
        runtime = RuntimeOptions()
        return await self.delete_context_with_options_async(request, runtime)

    def get_context_with_options(
        self,
        request: main_models.GetContextRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetContextResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.allow_create):
            body["AllowCreate"] = request.allow_create
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.name):
            body["Name"] = request.name
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetContext",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetContextResponse(), self.call_api(params, req, runtime)
        )

    async def get_context_with_options_async(
        self,
        request: main_models.GetContextRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetContextResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.allow_create):
            body["AllowCreate"] = request.allow_create
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.name):
            body["Name"] = request.name
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetContext",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetContextResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def get_context(
        self,
        request: main_models.GetContextRequest,
    ) -> main_models.GetContextResponse:
        runtime = RuntimeOptions()
        return self.get_context_with_options(request, runtime)

    async def get_context_async(
        self,
        request: main_models.GetContextRequest,
    ) -> main_models.GetContextResponse:
        runtime = RuntimeOptions()
        return await self.get_context_with_options_async(request, runtime)

    def get_context_info_with_options(
        self,
        request: main_models.GetContextInfoRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetContextInfoResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.context_id):
            body["ContextId"] = request.context_id
        if not DaraCore.is_null(request.path):
            body["Path"] = request.path
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        if not DaraCore.is_null(request.task_type):
            body["TaskType"] = request.task_type
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetContextInfo",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetContextInfoResponse(), self.call_api(params, req, runtime)
        )

    async def get_context_info_with_options_async(
        self,
        request: main_models.GetContextInfoRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetContextInfoResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.context_id):
            body["ContextId"] = request.context_id
        if not DaraCore.is_null(request.path):
            body["Path"] = request.path
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        if not DaraCore.is_null(request.task_type):
            body["TaskType"] = request.task_type
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetContextInfo",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetContextInfoResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def get_context_info(
        self,
        request: main_models.GetContextInfoRequest,
    ) -> main_models.GetContextInfoResponse:
        runtime = RuntimeOptions()
        return self.get_context_info_with_options(request, runtime)

    async def get_context_info_async(
        self,
        request: main_models.GetContextInfoRequest,
    ) -> main_models.GetContextInfoResponse:
        runtime = RuntimeOptions()
        return await self.get_context_info_with_options_async(request, runtime)

    def get_label_with_options(
        self,
        request: main_models.GetLabelRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetLabelResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.max_results):
            body["MaxResults"] = request.max_results
        if not DaraCore.is_null(request.next_token):
            body["NextToken"] = request.next_token
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetLabel",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetLabelResponse(), self.call_api(params, req, runtime)
        )

    async def get_label_with_options_async(
        self,
        request: main_models.GetLabelRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetLabelResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.max_results):
            body["MaxResults"] = request.max_results
        if not DaraCore.is_null(request.next_token):
            body["NextToken"] = request.next_token
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetLabel",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetLabelResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def get_label(
        self,
        request: main_models.GetLabelRequest,
    ) -> main_models.GetLabelResponse:
        runtime = RuntimeOptions()
        return self.get_label_with_options(request, runtime)

    async def get_label_async(
        self,
        request: main_models.GetLabelRequest,
    ) -> main_models.GetLabelResponse:
        runtime = RuntimeOptions()
        return await self.get_label_with_options_async(request, runtime)

    def get_session_with_options(
        self,
        request: main_models.GetSessionRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetSessionResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetSession",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetSessionResponse(), self.call_api(params, req, runtime)
        )

    async def get_session_with_options_async(
        self,
        request: main_models.GetSessionRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetSessionResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetSession",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetSessionResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def get_session(
        self,
        request: main_models.GetSessionRequest,
    ) -> main_models.GetSessionResponse:
        runtime = RuntimeOptions()
        return self.get_session_with_options(request, runtime)

    async def get_session_async(
        self,
        request: main_models.GetSessionRequest,
    ) -> main_models.GetSessionResponse:
        runtime = RuntimeOptions()
        return await self.get_session_with_options_async(request, runtime)

    def get_link_with_options(
        self,
        request: main_models.GetLinkRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetLinkResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.port):
            body["Port"] = request.port
        if not DaraCore.is_null(request.protocol_type):
            body["ProtocolType"] = request.protocol_type
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetLink",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetLinkResponse(), self.call_api(params, req, runtime)
        )

    async def get_link_with_options_async(
        self,
        request: main_models.GetLinkRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetLinkResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.port):
            body["Port"] = request.port
        if not DaraCore.is_null(request.protocol_type):
            body["ProtocolType"] = request.protocol_type
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetLink",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetLinkResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def get_link(
        self,
        request: main_models.GetLinkRequest,
    ) -> main_models.GetLinkResponse:
        runtime = RuntimeOptions()
        return self.get_link_with_options(request, runtime)

    async def get_link_async(
        self,
        request: main_models.GetLinkRequest,
    ) -> main_models.GetLinkResponse:
        runtime = RuntimeOptions()
        return await self.get_link_with_options_async(request, runtime)

    def get_mcp_resource_with_options(
        self,
        request: main_models.GetMcpResourceRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetMcpResourceResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetMcpResource",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetMcpResourceResponse(), self.call_api(params, req, runtime)
        )

    async def get_mcp_resource_with_options_async(
        self,
        request: main_models.GetMcpResourceRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetMcpResourceResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetMcpResource",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetMcpResourceResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def get_mcp_resource(
        self,
        request: main_models.GetMcpResourceRequest,
    ) -> main_models.GetMcpResourceResponse:
        runtime = RuntimeOptions()
        return self.get_mcp_resource_with_options(request, runtime)

    async def get_mcp_resource_async(
        self,
        request: main_models.GetMcpResourceRequest,
    ) -> main_models.GetMcpResourceResponse:
        runtime = RuntimeOptions()
        return await self.get_mcp_resource_with_options_async(request, runtime)

    def init_browser_with_options(
        self,
        request: main_models.InitBrowserRequest,
        runtime: RuntimeOptions,
    ) -> main_models.InitBrowserResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body['Authorization'] = request.authorization
        if not DaraCore.is_null(request.persistent_path):
            body['PersistentPath'] = request.persistent_path
        if not DaraCore.is_null(request.session_id):
            body['SessionId'] = request.session_id
        if not DaraCore.is_null(request.browser_option):
            body['BrowserOption'] = json.dumps(request.browser_option)
        req = open_api_util_models.OpenApiRequest(
            body = Utils.parse_to_map(body)
        )
        params = open_api_util_models.Params(
            action = 'InitBrowser',
            version = '2025-05-06',
            protocol = 'HTTPS',
            pathname = '/',
            method = 'POST',
            auth_type = 'Anonymous',
            style = 'RPC',
            req_body_type = 'formData',
            body_type = 'json'
        )
        return DaraCore.from_map(
            main_models.InitBrowserResponse(),
            self.call_api(params, req, runtime)
        )

    async def init_browser_with_options_async(
        self,
        request: main_models.InitBrowserRequest,
        runtime: RuntimeOptions,
    ) -> main_models.InitBrowserResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body['Authorization'] = request.authorization
        if not DaraCore.is_null(request.persistent_path):
            body['PersistentPath'] = request.persistent_path
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        if not DaraCore.is_null(request.browser_option):
            body['BrowserOption'] = json.dumps(request.browser_option)
        body_map = Utils.parse_to_map(body)
        req = open_api_util_models.OpenApiRequest(body=body_map)
        params = open_api_util_models.Params(
            action = 'InitBrowser',
            version = '2025-05-06',
            protocol = 'HTTPS',
            pathname = '/',
            method = 'POST',
            auth_type = 'Anonymous',
            style = 'RPC',
            req_body_type = 'formData',
            body_type = 'json'
        )
        return DaraCore.from_map(
            main_models.InitBrowserResponse(),
            await self.call_api_async(params, req, runtime)
        )

    def init_browser(
        self,
        request: main_models.InitBrowserRequest,
    ) -> main_models.InitBrowserResponse:
        runtime = RuntimeOptions()
        return self.init_browser_with_options(request, runtime)

    async def init_browser_async(
        self,
        request: main_models.InitBrowserRequest,
    ) -> main_models.InitBrowserResponse:
        runtime = RuntimeOptions()
        return await self.init_browser_with_options_async(request, runtime)

    def list_contexts_with_options(
        self,
        request: main_models.ListContextsRequest,
        runtime: RuntimeOptions,
    ) -> main_models.ListContextsResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.max_results):
            body["MaxResults"] = request.max_results
        if not DaraCore.is_null(request.next_token):
            body["NextToken"] = request.next_token
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="ListContexts",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.ListContextsResponse(), self.call_api(params, req, runtime)
        )

    async def list_contexts_with_options_async(
        self,
        request: main_models.ListContextsRequest,
        runtime: RuntimeOptions,
    ) -> main_models.ListContextsResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.max_results):
            body["MaxResults"] = request.max_results
        if not DaraCore.is_null(request.next_token):
            body["NextToken"] = request.next_token
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="ListContexts",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.ListContextsResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def list_contexts(
        self,
        request: main_models.ListContextsRequest,
    ) -> main_models.ListContextsResponse:
        runtime = RuntimeOptions()
        return self.list_contexts_with_options(request, runtime)

    async def list_contexts_async(
        self,
        request: main_models.ListContextsRequest,
    ) -> main_models.ListContextsResponse:
        runtime = RuntimeOptions()
        return await self.list_contexts_with_options_async(request, runtime)

    def list_mcp_tools_with_options(
        self,
        request: main_models.ListMcpToolsRequest,
        runtime: RuntimeOptions,
    ) -> main_models.ListMcpToolsResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.image_id):
            body["ImageId"] = request.image_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="ListMcpTools",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.ListMcpToolsResponse(), self.call_api(params, req, runtime)
        )

    async def list_mcp_tools_with_options_async(
        self,
        request: main_models.ListMcpToolsRequest,
        runtime: RuntimeOptions,
    ) -> main_models.ListMcpToolsResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.image_id):
            body["ImageId"] = request.image_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="ListMcpTools",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.ListMcpToolsResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def list_mcp_tools(
        self,
        request: main_models.ListMcpToolsRequest,
    ) -> main_models.ListMcpToolsResponse:
        runtime = RuntimeOptions()
        return self.list_mcp_tools_with_options(request, runtime)

    async def list_mcp_tools_async(
        self,
        request: main_models.ListMcpToolsRequest,
    ) -> main_models.ListMcpToolsResponse:
        runtime = RuntimeOptions()
        return await self.list_mcp_tools_with_options_async(request, runtime)

    def list_session_with_options(
        self,
        request: main_models.ListSessionRequest,
        runtime: RuntimeOptions,
    ) -> main_models.ListSessionResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.labels):
            body["Labels"] = request.labels
        if not DaraCore.is_null(request.max_results):
            body["MaxResults"] = request.max_results
        if not DaraCore.is_null(request.next_token):
            body["NextToken"] = request.next_token
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="ListSession",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.ListSessionResponse(), self.call_api(params, req, runtime)
        )

    async def list_session_with_options_async(
        self,
        request: main_models.ListSessionRequest,
        runtime: RuntimeOptions,
    ) -> main_models.ListSessionResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.labels):
            body["Labels"] = request.labels
        if not DaraCore.is_null(request.max_results):
            body["MaxResults"] = request.max_results
        if not DaraCore.is_null(request.next_token):
            body["NextToken"] = request.next_token
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="ListSession",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.ListSessionResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def list_session(
        self,
        request: main_models.ListSessionRequest,
    ) -> main_models.ListSessionResponse:
        runtime = RuntimeOptions()
        return self.list_session_with_options(request, runtime)

    async def list_session_async(
        self,
        request: main_models.ListSessionRequest,
    ) -> main_models.ListSessionResponse:
        runtime = RuntimeOptions()
        return await self.list_session_with_options_async(request, runtime)

    def modify_context_with_options(
        self,
        request: main_models.ModifyContextRequest,
        runtime: RuntimeOptions,
    ) -> main_models.ModifyContextResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.id):
            body["Id"] = request.id
        if not DaraCore.is_null(request.name):
            body["Name"] = request.name
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="ModifyContext",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.ModifyContextResponse(), self.call_api(params, req, runtime)
        )

    async def modify_context_with_options_async(
        self,
        request: main_models.ModifyContextRequest,
        runtime: RuntimeOptions,
    ) -> main_models.ModifyContextResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.id):
            body["Id"] = request.id
        if not DaraCore.is_null(request.name):
            body["Name"] = request.name
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="ModifyContext",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.ModifyContextResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def modify_context(
        self,
        request: main_models.ModifyContextRequest,
    ) -> main_models.ModifyContextResponse:
        runtime = RuntimeOptions()
        return self.modify_context_with_options(request, runtime)

    async def modify_context_async(
        self,
        request: main_models.ModifyContextRequest,
    ) -> main_models.ModifyContextResponse:
        runtime = RuntimeOptions()
        return await self.modify_context_with_options_async(request, runtime)

    def release_mcp_session_with_options(
        self,
        request: main_models.ReleaseMcpSessionRequest,
        runtime: RuntimeOptions,
    ) -> main_models.ReleaseMcpSessionResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="ReleaseMcpSession",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.ReleaseMcpSessionResponse(), self.call_api(params, req, runtime)
        )

    async def release_mcp_session_with_options_async(
        self,
        request: main_models.ReleaseMcpSessionRequest,
        runtime: RuntimeOptions,
    ) -> main_models.ReleaseMcpSessionResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="ReleaseMcpSession",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.ReleaseMcpSessionResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def release_mcp_session(
        self,
        request: main_models.ReleaseMcpSessionRequest,
    ) -> main_models.ReleaseMcpSessionResponse:
        runtime = RuntimeOptions()
        return self.release_mcp_session_with_options(request, runtime)

    async def release_mcp_session_async(
        self,
        request: main_models.ReleaseMcpSessionRequest,
    ) -> main_models.ReleaseMcpSessionResponse:
        runtime = RuntimeOptions()
        return await self.release_mcp_session_with_options_async(request, runtime)

    def set_label_with_options(
        self,
        request: main_models.SetLabelRequest,
        runtime: RuntimeOptions,
    ) -> main_models.SetLabelResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.labels):
            body["Labels"] = request.labels
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="SetLabel",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.SetLabelResponse(), self.call_api(params, req, runtime)
        )

    async def set_label_with_options_async(
        self,
        request: main_models.SetLabelRequest,
        runtime: RuntimeOptions,
    ) -> main_models.SetLabelResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.labels):
            body["Labels"] = request.labels
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="SetLabel",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.SetLabelResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def set_label(
        self,
        request: main_models.SetLabelRequest,
    ) -> main_models.SetLabelResponse:
        runtime = RuntimeOptions()
        return self.set_label_with_options(request, runtime)

    async def set_label_async(
        self,
        request: main_models.SetLabelRequest,
    ) -> main_models.SetLabelResponse:
        runtime = RuntimeOptions()
        return await self.set_label_with_options_async(request, runtime)

    def sync_context_with_options(
        self,
        request: main_models.SyncContextRequest,
        runtime: RuntimeOptions,
    ) -> main_models.SyncContextResponse:
        request.validate()
        query = {}
        if not DaraCore.is_null(request.authorization):
            query["Authorization"] = request.authorization
        body = {}
        if not DaraCore.is_null(request.context_id):
            body["ContextId"] = request.context_id
        if not DaraCore.is_null(request.mode):
            body["Mode"] = request.mode
        if not DaraCore.is_null(request.path):
            body["Path"] = request.path
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        req = open_api_util_models.OpenApiRequest(
            query=Utils.query(query), body=Utils.parse_to_map(body)
        )
        params = open_api_util_models.Params(
            action="SyncContext",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.SyncContextResponse(), self.call_api(params, req, runtime)
        )

    async def sync_context_with_options_async(
        self,
        request: main_models.SyncContextRequest,
        runtime: RuntimeOptions,
    ) -> main_models.SyncContextResponse:
        request.validate()
        query = {}
        if not DaraCore.is_null(request.authorization):
            query["Authorization"] = request.authorization
        body = {}
        if not DaraCore.is_null(request.context_id):
            body["ContextId"] = request.context_id
        if not DaraCore.is_null(request.mode):
            body["Mode"] = request.mode
        if not DaraCore.is_null(request.path):
            body["Path"] = request.path
        if not DaraCore.is_null(request.session_id):
            body["SessionId"] = request.session_id
        req = open_api_util_models.OpenApiRequest(
            query=Utils.query(query), body=Utils.parse_to_map(body)
        )
        params = open_api_util_models.Params(
            action="SyncContext",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.SyncContextResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def sync_context(
        self,
        request: main_models.SyncContextRequest,
    ) -> main_models.SyncContextResponse:
        runtime = RuntimeOptions()
        return self.sync_context_with_options(request, runtime)

    async def sync_context_async(
        self,
        request: main_models.SyncContextRequest,
    ) -> main_models.SyncContextResponse:
        runtime = RuntimeOptions()
        return await self.sync_context_with_options_async(request, runtime)

    def delete_context_file_with_options(
        self,
        request: main_models.DeleteContextFileRequest,
        runtime: RuntimeOptions,
    ) -> main_models.DeleteContextFileResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.context_id):
            body["ContextId"] = request.context_id
        if not DaraCore.is_null(request.file_path):
            body["FilePath"] = request.file_path
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="DeleteContextFile",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.DeleteContextFileResponse(), self.call_api(params, req, runtime)
        )

    async def delete_context_file_with_options_async(
        self,
        request: main_models.DeleteContextFileRequest,
        runtime: RuntimeOptions,
    ) -> main_models.DeleteContextFileResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.context_id):
            body["ContextId"] = request.context_id
        if not DaraCore.is_null(request.file_path):
            body["FilePath"] = request.file_path
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="DeleteContextFile",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.DeleteContextFileResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def delete_context_file(
        self,
        request: main_models.DeleteContextFileRequest,
    ) -> main_models.DeleteContextFileResponse:
        runtime = RuntimeOptions()
        return self.delete_context_file_with_options(request, runtime)

    async def delete_context_file_async(
        self,
        request: main_models.DeleteContextFileRequest,
    ) -> main_models.DeleteContextFileResponse:
        runtime = RuntimeOptions()
        return await self.delete_context_file_with_options_async(request, runtime)

    def describe_context_files_with_options(
        self,
        request: main_models.DescribeContextFilesRequest,
        runtime: RuntimeOptions,
    ) -> main_models.DescribeContextFilesResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.page_number):
            body["PageNumber"] = request.page_number
        if not DaraCore.is_null(request.page_size):
            body["PageSize"] = request.page_size
        if not DaraCore.is_null(request.parent_folder_path):
            body["ParentFolderPath"] = request.parent_folder_path
        if not DaraCore.is_null(request.context_id):
            body["ContextId"] = request.context_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="DescribeContextFiles",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.DescribeContextFilesResponse(), self.call_api(params, req, runtime)
        )

    async def describe_context_files_with_options_async(
        self,
        request: main_models.DescribeContextFilesRequest,
        runtime: RuntimeOptions,
    ) -> main_models.DescribeContextFilesResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.page_number):
            body["PageNumber"] = request.page_number
        if not DaraCore.is_null(request.page_size):
            body["PageSize"] = request.page_size
        if not DaraCore.is_null(request.parent_folder_path):
            body["ParentFolderPath"] = request.parent_folder_path
        if not DaraCore.is_null(request.context_id):
            body["ContextId"] = request.context_id
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="DescribeContextFiles",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.DescribeContextFilesResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def describe_context_files(
        self,
        request: main_models.DescribeContextFilesRequest,
    ) -> main_models.DescribeContextFilesResponse:
        runtime = RuntimeOptions()
        return self.describe_context_files_with_options(request, runtime)

    async def describe_context_files_async(
        self,
        request: main_models.DescribeContextFilesRequest,
    ) -> main_models.DescribeContextFilesResponse:
        runtime = RuntimeOptions()
        return await self.describe_context_files_with_options_async(request, runtime)

    def get_context_file_download_url_with_options(
        self,
        request: main_models.GetContextFileDownloadUrlRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetContextFileDownloadUrlResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.context_id):
            body["ContextId"] = request.context_id
        if not DaraCore.is_null(request.file_path):
            body["FilePath"] = request.file_path
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetContextFileDownloadUrl",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetContextFileDownloadUrlResponse(), self.call_api(params, req, runtime)
        )

    async def get_context_file_download_url_with_options_async(
        self,
        request: main_models.GetContextFileDownloadUrlRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetContextFileDownloadUrlResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.context_id):
            body["ContextId"] = request.context_id
        if not DaraCore.is_null(request.file_path):
            body["FilePath"] = request.file_path
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetContextFileDownloadUrl",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetContextFileDownloadUrlResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def get_context_file_download_url(
        self,
        request: main_models.GetContextFileDownloadUrlRequest,
    ) -> main_models.GetContextFileDownloadUrlResponse:
        runtime = RuntimeOptions()
        return self.get_context_file_download_url_with_options(request, runtime)

    async def get_context_file_download_url_async(
        self,
        request: main_models.GetContextFileDownloadUrlRequest,
    ) -> main_models.GetContextFileDownloadUrlResponse:
        runtime = RuntimeOptions()
        return await self.get_context_file_download_url_with_options_async(request, runtime)

    def get_context_file_upload_url_with_options(
        self,
        request: main_models.GetContextFileUploadUrlRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetContextFileUploadUrlResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.context_id):
            body["ContextId"] = request.context_id
        if not DaraCore.is_null(request.file_path):
            body["FilePath"] = request.file_path
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetContextFileUploadUrl",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetContextFileUploadUrlResponse(), self.call_api(params, req, runtime)
        )

    async def get_context_file_upload_url_with_options_async(
        self,
        request: main_models.GetContextFileUploadUrlRequest,
        runtime: RuntimeOptions,
    ) -> main_models.GetContextFileUploadUrlResponse:
        request.validate()
        body = {}
        if not DaraCore.is_null(request.authorization):
            body["Authorization"] = request.authorization
        if not DaraCore.is_null(request.context_id):
            body["ContextId"] = request.context_id
        if not DaraCore.is_null(request.file_path):
            body["FilePath"] = request.file_path
        req = open_api_util_models.OpenApiRequest(body=Utils.parse_to_map(body))
        params = open_api_util_models.Params(
            action="GetContextFileUploadUrl",
            version="2025-05-06",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="Anonymous",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        return DaraCore.from_map(
            main_models.GetContextFileUploadUrlResponse(),
            await self.call_api_async(params, req, runtime),
        )

    def get_context_file_upload_url(
        self,
        request: main_models.GetContextFileUploadUrlRequest,
    ) -> main_models.GetContextFileUploadUrlResponse:
        runtime = RuntimeOptions()
        return self.get_context_file_upload_url_with_options(request, runtime)

    async def get_context_file_upload_url_async(
        self,
        request: main_models.GetContextFileUploadUrlRequest,
    ) -> main_models.GetContextFileUploadUrlResponse:
        runtime = RuntimeOptions()
        return await self.get_context_file_upload_url_with_options_async(request, runtime)
