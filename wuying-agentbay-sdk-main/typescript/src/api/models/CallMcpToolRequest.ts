// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class CallMcpToolRequest extends $dara.Model {
  args?: string;
  authorization?: string;
  externalUserId?: string;
  imageId?: string;
  name?: string;
  server?: string;
  sessionId?: string;
  tool?: string;
  static names(): { [key: string]: string } {
    return {
      args: 'Args',
      authorization: 'Authorization',
      externalUserId: 'ExternalUserId',
      imageId: 'ImageId',
      name: 'Name',
      server: 'Server',
      sessionId: 'SessionId',
      tool: 'Tool',
    };
  }

  static types(): { [key: string]: any } {
    return {
      args: 'string',
      authorization: 'string',
      externalUserId: 'string',
      imageId: 'string',
      name: 'string',
      server: 'string',
      sessionId: 'string',
      tool: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

