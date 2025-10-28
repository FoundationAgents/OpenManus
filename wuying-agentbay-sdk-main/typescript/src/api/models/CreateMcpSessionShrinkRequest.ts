// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class CreateMcpSessionShrinkRequest extends $dara.Model {
  authorization?: string;
  contextId?: string;
  externalUserId?: string;
  imageId?: string;
  labels?: string;
  mcpPolicyId?: string;
  persistenceDataListShrink?: string;
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
      persistenceDataListShrink: 'PersistenceDataList',
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
      persistenceDataListShrink: 'string',
      sessionId: 'string',
      vpcResource: 'boolean',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

