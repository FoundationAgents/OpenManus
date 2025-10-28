// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class GetLinkRequest extends $dara.Model {
  authorization?: string;
  port?: number;
  protocolType?: string;
  sessionId?: string;
  static names(): { [key: string]: string } {
    return {
      authorization: 'Authorization',
      port: 'Port',
      protocolType: 'ProtocolType',
      sessionId: 'SessionId',
    };
  }

  static types(): { [key: string]: any } {
    return {
      authorization: 'string',
      port: 'number',
      protocolType: 'string',
      sessionId: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

