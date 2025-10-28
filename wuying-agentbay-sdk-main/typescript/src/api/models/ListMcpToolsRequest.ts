// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class ListMcpToolsRequest extends $dara.Model {
  authorization?: string;
  imageId?: string;
  static names(): { [key: string]: string } {
    return {
      authorization: 'Authorization',
      imageId: 'ImageId',
    };
  }

  static types(): { [key: string]: any } {
    return {
      authorization: 'string',
      imageId: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

