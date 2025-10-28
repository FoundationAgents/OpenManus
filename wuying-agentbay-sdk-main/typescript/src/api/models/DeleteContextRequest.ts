// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class DeleteContextRequest extends $dara.Model {
  authorization?: string;
  id?: string;
  static names(): { [key: string]: string } {
    return {
      authorization: 'Authorization',
      id: 'Id',
    };
  }

  static types(): { [key: string]: any } {
    return {
      authorization: 'string',
      id: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

