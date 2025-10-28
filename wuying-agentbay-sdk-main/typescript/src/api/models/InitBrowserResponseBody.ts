// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';
import { InitBrowserResponseBodyData } from './InitBrowserResponseBodyData';

export class InitBrowserResponseBody extends $dara.Model {
  code?: string;
  data?: InitBrowserResponseBodyData;
  httpStatusCode?: number;
  message?: string;
  requestId?: string;
  success?: boolean;
  
  static names(): { [key: string]: string } {
    return {
      code: 'Code',
      data: 'Data',
      httpStatusCode: 'HttpStatusCode',
      message: 'Message',
      requestId: 'RequestId',
      success: 'Success',
    };
  }

  static types(): { [key: string]: any } {
    return {
      code: 'string',
      data: InitBrowserResponseBodyData,
      httpStatusCode: 'number',
      message: 'string',
      requestId: 'string',
      success: 'boolean',
    };
  }

  validate() {
    if(this.data && typeof (this.data as any).validate === 'function') {
      (this.data as any).validate();
    }
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }

  static fromMap(m: { [key: string]: any }): InitBrowserResponseBody {
    return $dara.cast<InitBrowserResponseBody>(m, new InitBrowserResponseBody());
  }
} 