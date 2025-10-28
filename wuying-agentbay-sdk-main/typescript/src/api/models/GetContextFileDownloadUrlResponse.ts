// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';
import { GetContextFileDownloadUrlResponseBody } from './GetContextFileDownloadUrlResponseBody';

export class GetContextFileDownloadUrlResponse extends $dara.Model {
  headers?: { [key: string]: string };
  statusCode?: number;
  body?: GetContextFileDownloadUrlResponseBody;
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
      body: GetContextFileDownloadUrlResponseBody,
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
} 