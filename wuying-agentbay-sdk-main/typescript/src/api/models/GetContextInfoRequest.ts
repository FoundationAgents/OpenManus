// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class GetContextInfoRequest extends $dara.Model {
  authorization?: string;
  contextId?: string;
  path?: string;
  sessionId?: string;
  taskType?: string;
  static names(): { [key: string]: string } {
    return {
      authorization: 'Authorization',
      contextId: 'ContextId',
      path: 'Path',
      sessionId: 'SessionId',
      taskType: 'TaskType',
    };
  }

  static types(): { [key: string]: any } {
    return {
      authorization: 'string',
      contextId: 'string',
      path: 'string',
      sessionId: 'string',
      taskType: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

