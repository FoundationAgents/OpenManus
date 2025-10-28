// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';

export class DescribeContextFilesRequest extends $dara.Model {
  authorization?: string;
  pageNumber?: number;
  pageSize?: number;
  parentFolderPath?: string;
  contextId?: string;
  static names(): { [key: string]: string } {
    return {
      authorization: 'Authorization',
      pageNumber: 'PageNumber',
      pageSize: 'PageSize',
      parentFolderPath: 'ParentFolderPath',
      contextId: 'ContextId',
    };
  }

  static types(): { [key: string]: any } {
    return {
      authorization: 'string',
      pageNumber: 'number',
      pageSize: 'number',
      parentFolderPath: 'string',
      contextId: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
} 