// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class GetMcpResourceResponseBodyDataDesktopInfo extends $dara.Model {
  appId?: string;
  authCode?: string;
  connectionProperties?: string;
  resourceId?: string;
  resourceType?: string;
  ticket?: string;
  static names(): { [key: string]: string } {
    return {
      appId: 'AppId',
      authCode: 'AuthCode',
      connectionProperties: 'ConnectionProperties',
      resourceId: 'ResourceId',
      resourceType: 'ResourceType',
      ticket: 'Ticket',
    };
  }

  static types(): { [key: string]: any } {
    return {
      appId: 'string',
      authCode: 'string',
      connectionProperties: 'string',
      resourceId: 'string',
      resourceType: 'string',
      ticket: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

