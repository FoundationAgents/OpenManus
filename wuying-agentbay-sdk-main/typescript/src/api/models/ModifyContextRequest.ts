// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class ModifyContextRequest extends $dara.Model {
  authorization?: string;
  id?: string;
  name?: string;
  static names(): { [key: string]: string } {
    return {
      authorization: 'Authorization',
      id: 'Id',
      name: 'Name',
    };
  }

  static types(): { [key: string]: any } {
    return {
      authorization: 'string',
      id: 'string',
      name: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

