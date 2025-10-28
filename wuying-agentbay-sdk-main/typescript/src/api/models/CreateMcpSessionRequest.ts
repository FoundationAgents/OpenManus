// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';
import { CreateMcpSessionRequestPersistenceDataList } from "./CreateMcpSessionRequestPersistenceDataList";


export class CreateMcpSessionRequest extends $dara.Model {
  authorization?: string;
  contextId?: string;
  externalUserId?: string;
  imageId?: string;
  labels?: string;
  mcpPolicyId?: string;
  persistenceDataList?: CreateMcpSessionRequestPersistenceDataList[];
  sessionId?: string;
  vpcResource?: boolean;
  static names(): { [key: string]: string } {
    return {
      authorization: 'Authorization',
      contextId: 'ContextId',
      externalUserId: 'ExternalUserId',
      imageId: 'ImageId',
      labels: 'Labels',
      mcpPolicyId: 'McpPolicyId',
      persistenceDataList: 'PersistenceDataList',
      sessionId: 'SessionId',
      vpcResource: 'VpcResource',
    };
  }

  static types(): { [key: string]: any } {
    return {
      authorization: 'string',
      contextId: 'string',
      externalUserId: 'string',
      imageId: 'string',
      labels: 'string',
      mcpPolicyId: 'string',
      persistenceDataList: { 'type': 'array', 'itemType': CreateMcpSessionRequestPersistenceDataList },
      sessionId: 'string',
      vpcResource: 'boolean',
    };
  }

  validate() {
    if(Array.isArray(this.persistenceDataList)) {
      $dara.Model.validateArray(this.persistenceDataList);
    }
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

