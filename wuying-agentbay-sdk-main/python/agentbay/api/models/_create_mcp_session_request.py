# -*- coding: utf-8 -*-
# This file is auto-generated, don't edit it. Thanks.
from __future__ import annotations
from darabonba.model import DaraModel 
from agentbay.api import models as main_models 
from typing import List, Optional


class CreateMcpSessionRequest(DaraModel):
    def __init__(
        self,
        authorization: Optional[str] = None,
        context_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
        image_id: Optional[str] = None,
        labels: Optional[str] = None,
        mcp_policy_id: Optional[str] = None,
        persistence_data_list: Optional[List[main_models.CreateMcpSessionRequestPersistenceDataList]] = None,
        session_id: Optional[str] = None,
        vpc_resource: Optional[bool] = None,
        extra_configs: Optional[main_models.ExtraConfigs] = None,
    ):
        self.authorization = authorization
        self.context_id = context_id
        self.external_user_id = external_user_id
        self.image_id = image_id
        self.labels = labels
        self.mcp_policy_id = mcp_policy_id
        self.persistence_data_list = persistence_data_list
        self.session_id = session_id
        self.vpc_resource = vpc_resource
        self.extra_configs = extra_configs

    def validate(self):
        if self.persistence_data_list:
            for v1 in self.persistence_data_list:
                 if v1:
                    v1.validate()
        if self.extra_configs:
            self.extra_configs.validate()

    def to_map(self):
        result = dict()
        _map = super().to_map()
        if _map is not None:
            result = _map
        if self.authorization is not None:
            result['Authorization'] = self.authorization

        if self.context_id is not None:
            result['ContextId'] = self.context_id

        if self.external_user_id is not None:
            result['ExternalUserId'] = self.external_user_id

        if self.image_id is not None:
            result['ImageId'] = self.image_id

        if self.labels is not None:
            result['Labels'] = self.labels

        if self.mcp_policy_id is not None:
            result['McpPolicyId'] = self.mcp_policy_id

        result['PersistenceDataList'] = []
        if self.persistence_data_list is not None:
            for k1 in self.persistence_data_list:
                result['PersistenceDataList'].append(k1.to_map() if k1 else None)

        if self.session_id is not None:
            result['SessionId'] = self.session_id

        if self.vpc_resource is not None:
            result['VpcResource'] = self.vpc_resource

        if self.extra_configs is not None:
            result['ExtraConfigs'] = self.extra_configs.to_map()

        return result

    def from_map(self, m: Optional[dict] = None):
        m = m or dict()
        if m.get('Authorization') is not None:
            self.authorization = m.get('Authorization')

        if m.get('ContextId') is not None:
            self.context_id = m.get('ContextId')

        if m.get('ExternalUserId') is not None:
            self.external_user_id = m.get('ExternalUserId')

        if m.get('ImageId') is not None:
            self.image_id = m.get('ImageId')

        if m.get('Labels') is not None:
            self.labels = m.get('Labels')

        if m.get('McpPolicyId') is not None:
            self.mcp_policy_id = m.get('McpPolicyId')

        self.persistence_data_list = []
        if m.get('PersistenceDataList') is not None:
            for k1 in m.get('PersistenceDataList', []):
                temp_model = main_models.CreateMcpSessionRequestPersistenceDataList()
                self.persistence_data_list.append(temp_model.from_map(k1))

        if m.get('SessionId') is not None:
            self.session_id = m.get('SessionId')

        if m.get('VpcResource') is not None:
            self.vpc_resource = m.get('VpcResource')

        if m.get('ExtraConfigs') is not None:
            temp_model = main_models.ExtraConfigs()
            self.extra_configs = temp_model.from_map(m.get('ExtraConfigs'))

        return self

class CreateMcpSessionRequestPersistenceDataList(DaraModel):
    def __init__(
        self,
        context_id: Optional[str] = None,
        path: Optional[str] = None,
        policy: Optional[str] = None,
    ):
        self.context_id = context_id
        self.path = path
        self.policy = policy

    def validate(self):
        pass

    def to_map(self):
        result = dict()
        _map = super().to_map()
        if _map is not None:
            result = _map
        if self.context_id is not None:
            result['ContextId'] = self.context_id

        if self.path is not None:
            result['Path'] = self.path

        if self.policy is not None:
            result['Policy'] = self.policy

        return result

    def from_map(self, m: Optional[dict] = None):
        m = m or dict()
        if m.get('ContextId') is not None:
            self.context_id = m.get('ContextId')

        if m.get('Path') is not None:
            self.path = m.get('Path')

        if m.get('Policy') is not None:
            self.policy = m.get('Policy')

        return self

class AppManagerRule(DaraModel):    
    def __init__(
        self,
        rule_type: Optional[str] = None,
        app_package_name_list: Optional[List[str]] = None,
    ):
        self.rule_type = rule_type
        self.app_package_name_list = app_package_name_list

    def validate(self):
        if self.app_package_name_list:
            for v1 in self.app_package_name_list:
                if v1 and not isinstance(v1, str):
                    raise ValueError("app_package_name_list items must be strings")

    def to_map(self):
        result = dict()
        _map = super().to_map()
        if _map is not None:
            result = _map
        
        if self.rule_type is not None:
            result['RuleType'] = self.rule_type
        
        result['AppPackageNameList'] = []
        if self.app_package_name_list is not None:
            result['AppPackageNameList'] = self.app_package_name_list
        
        return result

    def from_map(self, m: Optional[dict] = None):
        m = m or dict()
        if m.get('RuleType') is not None:
            self.rule_type = m.get('RuleType')
        
        if m.get('AppPackageNameList') is not None:
            self.app_package_name_list = m.get('AppPackageNameList', [])
        
        return self


class MobileExtraConfig(DaraModel):
    def __init__(
        self,
        lock_resolution: Optional[bool] = None,
        app_manager_rule: Optional[AppManagerRule] = None,
    ):
        self.lock_resolution = lock_resolution
        self.app_manager_rule = app_manager_rule

    def validate(self):
        if self.app_manager_rule:
            self.app_manager_rule.validate()

    def to_map(self):
        result = dict()
        _map = super().to_map()
        if _map is not None:
            result = _map
        
        if self.lock_resolution is not None:
            result['LockResolution'] = self.lock_resolution
        
        if self.app_manager_rule is not None:
            result['AppManagerRule'] = self.app_manager_rule.to_map()
        
        return result

    def from_map(self, m: Optional[dict] = None):
        m = m or dict()
        if m.get('LockResolution') is not None:
            self.lock_resolution = m.get('LockResolution')
        
        if m.get('AppManagerRule') is not None:
            temp_model = AppManagerRule()
            self.app_manager_rule = temp_model.from_map(m.get('AppManagerRule'))
        
        return self


class ExtraConfigs(DaraModel):
    def __init__(
        self,
        mobile: Optional[MobileExtraConfig] = None,
    ):
        self.mobile = mobile

    def validate(self):
        if self.mobile:
            self.mobile.validate()

    def to_map(self):
        result = dict()
        _map = super().to_map()
        if _map is not None:
            result = _map
        
        if self.mobile is not None:
            result['Mobile'] = self.mobile.to_map()
        
        return result

    def from_map(self, m: Optional[dict] = None):
        m = m or dict()
        if m.get('Mobile') is not None:
            temp_model = MobileExtraConfig()
            self.mobile = temp_model.from_map(m.get('Mobile'))
        
        return self

