// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class SyncContextRequest extends $dara.Model {
  authorization?: string;
  contextId?: string;
  mode?: string;
  path?: string;
  sessionId?: string;
  static names(): { [key: string]: string } {
    return {
      authorization: 'Authorization',
      contextId: 'ContextId',
      mode: 'Mode',
      path: 'Path',
      sessionId: 'SessionId',
    };
  }

  static types(): { [key: string]: any } {
    return {
      authorization: 'string',
      contextId: 'string',
      mode: 'string',
      path: 'string',
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

