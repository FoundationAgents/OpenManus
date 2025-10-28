// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';

export class GetContextFileUploadUrlRequest extends $dara.Model {
  authorization?: string;
  contextId?: string;
  filePath?: string;
  static names(): { [key: string]: string } {
    return {
      authorization: 'Authorization',
      contextId: 'ContextId',
      filePath: 'FilePath',
    };
  }

  static types(): { [key: string]: any } {
    return {
      authorization: 'string',
      contextId: 'string',
      filePath: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
} 