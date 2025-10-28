// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class CreateMcpSessionRequestPersistenceDataList extends $dara.Model {
  contextId?: string;
  path?: string;
  policy?: string;
  static names(): { [key: string]: string } {
    return {
      contextId: 'ContextId',
      path: 'Path',
      policy: 'Policy',
    };
  }

  static types(): { [key: string]: any } {
    return {
      contextId: 'string',
      path: 'string',
      policy: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

