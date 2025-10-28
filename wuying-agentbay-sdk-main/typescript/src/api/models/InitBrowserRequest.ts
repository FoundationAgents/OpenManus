// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';

export class InitBrowserRequest extends $dara.Model {
  authorization?: string;
  persistentPath?: string;
  sessionId?: string;
  browserOption?: { [key: string]: any };
  
  static names(): { [key: string]: string } {
    return {
      authorization: 'Authorization',
      persistentPath: 'PersistentPath',
      sessionId: 'SessionId',
      browserOption: 'BrowserOption',
    };
  }

  static types(): { [key: string]: any } {
    return {
      authorization: 'string',
      persistentPath: 'string',
      sessionId: 'string',
      browserOption: { 'type': 'map', 'keyType': 'string', 'valueType': 'any' },
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }

  static fromMap(m: { [key: string]: any }): InitBrowserRequest {
    return $dara.cast<InitBrowserRequest>(m, new InitBrowserRequest());
  }
} 