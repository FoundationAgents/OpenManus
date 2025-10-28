// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class GetContextInfoResponseBodyData extends $dara.Model {
  contextStatus?: string;
  static names(): { [key: string]: string } {
    return {
      contextStatus: 'ContextStatus',
    };
  }

  static types(): { [key: string]: any } {
    return {
      contextStatus: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

