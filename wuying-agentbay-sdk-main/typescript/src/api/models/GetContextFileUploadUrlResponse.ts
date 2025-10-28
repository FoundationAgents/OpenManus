// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';
import { GetContextFileUploadUrlResponseBody } from './GetContextFileUploadUrlResponseBody';

export class GetContextFileUploadUrlResponse extends $dara.Model {
  headers?: { [key: string]: string };
  statusCode?: number;
  body?: GetContextFileUploadUrlResponseBody;
  static names(): { [key: string]: string } {
    return {
      headers: 'headers',
      statusCode: 'statusCode',
      body: 'body',
    };
  }

  static types(): { [key: string]: any } {
    return {
      headers: { type: 'map', keyType: 'string', valueType: 'string' },
      statusCode: 'number',
      body: GetContextFileUploadUrlResponseBody,
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
} 