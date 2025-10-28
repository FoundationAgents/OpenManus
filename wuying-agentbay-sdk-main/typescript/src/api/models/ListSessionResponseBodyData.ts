// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class ListSessionResponseBodyData extends $dara.Model {
  sessionId?: string;
  sessionStatus?: string;
  static names(): { [key: string]: string } {
    return {
      sessionId: 'SessionId',
      sessionStatus: 'SessionStatus',
    };
  }

  static types(): { [key: string]: any } {
    return {
      sessionId: 'string',
      sessionStatus: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

